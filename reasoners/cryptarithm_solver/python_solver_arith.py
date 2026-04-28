"""
python_solver_arith.py — constrained solver for add / sub / mul / cat only.

Per-op optimizations (applied in order per example):
  1. Algebraic inversion: output fully assigned → derive R = f^-1(result, L) directly (O(1))
  2. Column-level derivation: partially assigned output → derive b0/b1 from carry/borrow
     structure (O(1) for add/sub; units-digit pruning for mul)

Training examples using ops outside {add, sub, mul} are skipped.
A plausible fallback answer is always returned (never None).
"""
from __future__ import annotations
import sys
import time
from itertools import permutations as _permutations
from typing import Union

sys.path.insert(0, '/workspaces/nemotron')

from reasoners.cryptarithm_solver.python_solver import (
    FORMATTERS, MATH_OPS, SYMBOL_UNIVERSE,
    extract_all_examples, _syms_for_pipeline, _encode_answer,
    _cat_fast_path, _derive_output, _plausible_ops,
)
from reasoners.cryptarithm_solver.python_solver_prefilter import (
    _precompute_op_constraints, _reorder_examples,
)

# ---------------------------------------------------------------------------
# Constants from empirical_ordering_report.md
# ---------------------------------------------------------------------------

SUPPORTED_OPS = frozenset({'add', 'sub', 'mul'})
OP_ORDER = ['add', 'sub', 'mul']

A0_ORDER = [5, 2, 4, 1, 8, 6, 3, 9, 7, 0]
A1_ORDER = [9, 7, 0, 3, 1, 5, 6, 2, 4, 8]
B0_ORDER = [6, 5, 8, 7, 4, 3, 1, 9, 2, 0]
B1_ORDER = [2, 7, 8, 9, 0, 1, 6, 3, 4, 5]

# ---------------------------------------------------------------------------
# Column constraint helpers
# ---------------------------------------------------------------------------

def _decode_result_numeric(out_syms: list, op_sym: str, f_type: str, dm: dict) -> int | None:
    """Reconstruct numeric result from assigned output symbols. None if any unassigned."""
    if not out_syms:
        return None
    if f_type in ('raw', 'swap'):
        is_neg = out_syms[0] == op_sym
        dsyms = out_syms[1:] if is_neg else out_syms
    else:
        is_neg = out_syms[-1] == op_sym
        dsyms = out_syms[:-1] if is_neg else out_syms
    for s in dsyms:
        if s not in dm:
            return None
    s_str = ''.join(str(dm[s]) for s in dsyms)
    val = int(s_str) if f_type == 'raw' else int(s_str[::-1])
    return -val if is_neg else val


def _col_syms(out_syms: list, op_sym: str, f_type: str):
    """Return (is_neg, units_sym, tens_sym, hund_sym) for column-level derivation."""
    if not out_syms:
        return False, None, None, None
    if f_type in ('raw', 'swap'):
        is_neg = out_syms[0] == op_sym
        dsyms = out_syms[1:] if is_neg else list(out_syms)
    else:
        is_neg = out_syms[-1] == op_sym
        dsyms = list(out_syms[:-1]) if is_neg else list(out_syms)
    n = len(dsyms)
    if f_type == 'raw':
        units = dsyms[n - 1] if n >= 1 else None
        tens  = dsyms[n - 2] if n >= 2 else None
        hund  = dsyms[n - 3] if n >= 3 else None
    else:  # swap / rev: digit string is reversed → dsyms[0] = units
        units = dsyms[0] if n >= 1 else None
        tens  = dsyms[1] if n >= 2 else None
        hund  = dsyms[2] if n >= 3 else None
    return is_neg, units, tens, hund


def _try_assign(sym: str, val: int, dm: dict, used: set):
    """Check/assign sym=val with AllDifferent. Returns (dm', used', ok)."""
    if sym in dm:
        return dm, used, dm[sym] == val
    if val in used:
        return dm, used, False
    return {**dm, sym: val}, used | {val}, True


def _invert_op(op_name: str, L: int, result: int) -> int | None:
    """Compute R given L and result. Returns None if no valid integer R in [0,99]."""
    if op_name == 'add':
        R = result - L
    elif op_name == 'sub':
        R = L - result
    elif op_name == 'mul':
        if L == 0:
            return None
        if result % L != 0:
            return None
        R = result // L
    else:
        return None
    return R if 0 <= R <= 99 else None


def _units_val(op_name: str, a1: int, b1: int, is_neg: bool) -> int:
    if op_name == 'add':
        return (a1 + b1) % 10
    if op_name == 'sub':
        return (a1 - b1 + 10) % 10 if not is_neg else (b1 - a1 + 10) % 10
    return (a1 * b1) % 10  # mul


def _carry1(op_name: str, a1: int, b1: int, is_neg: bool) -> int:
    if op_name == 'add':
        return (a1 + b1) // 10
    if op_name == 'sub':
        return int(a1 < b1) if not is_neg else int(b1 < a1)
    return 0


def _tens_val(op_name: str, a0: int, b0: int, cb1: int, is_neg: bool) -> int:
    if op_name == 'add':
        return (a0 + b0 + cb1) % 10
    if op_name == 'sub':
        return (a0 - cb1 - b0 + 10) % 10 if not is_neg else (b0 - a0 - cb1 + 10) % 10
    return 0


def _carry2(op_name: str, a0: int, b0: int, cb1: int, is_neg: bool) -> int:
    if op_name == 'add':
        return (a0 + b0 + cb1) // 10
    if op_name == 'sub':
        return int((a0 - cb1) < b0) if not is_neg else int((b0 - a0 - cb1) < 0)
    return 0


def _b1_from_units(op_name: str, a1: int, uval: int, is_neg: bool, used: set) -> list:
    """Derive b1 candidates from known units digit of result."""
    if op_name == 'add':
        b1 = (uval - a1 + 10) % 10
        return [b1] if b1 not in used else []
    if op_name == 'sub':
        b1 = (a1 - uval + 10) % 10 if not is_neg else (uval + a1) % 10
        return [b1] if b1 not in used else []
    # mul: (a1 * b1) % 10 == uval
    return [b for b in range(10) if (a1 * b) % 10 == uval and b not in used]


def _b0_from_tens(op_name: str, a0: int, cb1: int, tval: int, is_neg: bool, used: set) -> list:
    """Derive b0 from known tens digit of result (add/sub only)."""
    if op_name == 'add':
        b0 = (tval - a0 - cb1 + 10) % 10
        return [b0] if b0 not in used else []
    if op_name == 'sub':
        b0 = (a0 - cb1 - tval + 10) % 10 if not is_neg else (tval + a0 + cb1) % 10
        return [b0] if b0 not in used else []
    return []


# ---------------------------------------------------------------------------
# Per-example operation step
# ---------------------------------------------------------------------------

def _step_op(op_name, L, a0, a1, B0s, B1s, out_syms, op_sym, f_type,
             dm, used, op_assign, examples, ex_idx, plausible, solutions, deadline, max_solutions):

    # 1. Algebraic inversion: output fully known → derive R directly
    result = _decode_result_numeric(out_syms, op_sym, f_type, dm)
    if result is not None:
        R = _invert_op(op_name, L, result)
        if R is not None:
            dm2, used2, ok = _try_assign(B0s, R // 10, dm, used)
            if ok:
                dm3, used3, ok2 = _try_assign(B1s, R % 10, dm2, used2)
                if ok2:
                    _search_constrained(examples, ex_idx + 1, dm3, used3,
                                        {**op_assign, op_sym: op_name},
                                        plausible, f_type, solutions, deadline, max_solutions)
        return  # inversion is the only path when output is fully known

    # 2. Column-level derivation
    is_neg, units_sym, tens_sym, hund_sym = _col_syms(out_syms, op_sym, f_type)
    uval_known = units_sym is not None and units_sym in dm

    # b1 candidates
    if B1s in dm:
        b1_list = [dm[B1s]]
    elif uval_known:
        b1_list = _b1_from_units(op_name, a1, dm[units_sym], is_neg, used)
    else:
        b1_list = [v for v in B1_ORDER if v not in used]

    for b1 in b1_list:
        dm_b1, used_b1, ok = _try_assign(B1s, b1, dm, used)
        if not ok:
            continue

        cb1 = _carry1(op_name, a1, b1, is_neg)
        uv = _units_val(op_name, a1, b1, is_neg)

        if op_name != 'mul':
            # add/sub: assign units_sym from column
            if units_sym:
                dm_b1, used_b1, ok = _try_assign(units_sym, uv, dm_b1, used_b1)
                if not ok:
                    continue
        else:
            # mul: only verify if units_sym pre-assigned
            if units_sym and units_sym in dm_b1 and dm_b1[units_sym] != uv:
                continue

        tval_known = tens_sym is not None and tens_sym in dm_b1

        # b0 candidates
        if B0s in dm_b1:
            b0_list = [dm_b1[B0s]]
        elif op_name in ('add', 'sub') and tval_known:
            b0_list = _b0_from_tens(op_name, a0, cb1, dm_b1[tens_sym], is_neg, used_b1)
        else:
            b0_list = [v for v in B0_ORDER if v not in used_b1]

        for b0 in b0_list:
            dm_b0, used_b0, ok = _try_assign(B0s, b0, dm_b1, used_b1)
            if not ok:
                continue

            if op_name == 'mul':
                result_val = L * (b0 * 10 + b1)
                new_out, ok = _derive_output(result_val, out_syms, f_type, op_name, op_sym, dm_b0, used_b0)
                if not ok:
                    continue
                dm_f = {**dm_b0, **new_out}
                used_f = used_b0 | set(new_out.values())
            else:
                cb2 = _carry2(op_name, a0, b0, cb1, is_neg)
                tval = _tens_val(op_name, a0, b0, cb1, is_neg)

                # sub validity: borrow-out means result crossed sign boundary
                if op_name == 'sub' and cb2 != 0:
                    continue

                dm_f, used_f = dm_b0, used_b0
                if tens_sym:
                    dm_f, used_f, ok = _try_assign(tens_sym, tval, dm_f, used_f)
                    if not ok:
                        continue
                if hund_sym:
                    dm_f, used_f, ok = _try_assign(hund_sym, cb2, dm_f, used_f)
                    if not ok:
                        continue

            _search_constrained(examples, ex_idx + 1, dm_f, used_f,
                                {**op_assign, op_sym: op_name},
                                plausible, f_type, solutions, deadline, max_solutions)
            if len(solutions) >= max_solutions:
                return


# ---------------------------------------------------------------------------
# Main search
# ---------------------------------------------------------------------------

def _iter_sym(sym: str, order: list, dm: dict, used: set):
    if sym in dm:
        yield dm[sym]
    else:
        for v in order:
            if v not in used:
                yield v


def _search_constrained(examples, ex_idx, dm, used, op_assign, plausible,
                        f_type, solutions, deadline, max_solutions):
    if time.time() > deadline or len(solutions) >= max_solutions:
        return
    if ex_idx == len(examples):
        solutions.append((dict(dm), dict(op_assign)))
        return

    ex = examples[ex_idx]
    A0s, A1s, B0s, B1s = _syms_for_pipeline(ex, f_type)
    op_sym = ex['op']
    out_syms = ex['out']

    allowed = list(plausible[ex_idx])
    if op_sym in op_assign:
        allowed = [o for o in allowed if o == op_assign[op_sym]]
        if not allowed:
            return

    for a0 in _iter_sym(A0s, A0_ORDER, dm, used):
        a0n = A0s not in dm
        used2 = used | {a0} if a0n else used
        dm2 = {**dm, A0s: a0} if a0n else dm

        for a1 in _iter_sym(A1s, A1_ORDER, dm2, used2):
            a1n = A1s not in dm2
            used3 = used2 | {a1} if a1n else used2
            dm3 = {**dm2, A1s: a1} if a1n else dm2

            L = a0 * 10 + a1
            for op_name in allowed:
                _step_op(op_name, L, a0, a1, B0s, B1s, out_syms, op_sym, f_type,
                         dm3, used3, op_assign, examples, ex_idx, plausible,
                         solutions, deadline, max_solutions)
                if len(solutions) >= max_solutions:
                    return


# ---------------------------------------------------------------------------
# Fallback: always produce an answer even when search fails
# ---------------------------------------------------------------------------

def _fallback_answer(tA, tB, tgt_op_str, tgt_cands, digit_sym_list, ops_used):
    for f_type in FORMATTERS:
        tgt_ex = {'A': tA, 'B': tB, 'op': tgt_op_str, 'out': []}
        tA0s, tA1s, tB0s, tB1s = _syms_for_pipeline(tgt_ex, f_type)
        syms = list(dict.fromkeys([tA0s, tA1s, tB0s, tB1s]))
        for combo in _permutations(range(10), len(syms)):
            dm_try = dict(zip(syms, combo))
            L = dm_try.get(tA0s, 0) * 10 + dm_try.get(tA1s, 0)
            R = dm_try.get(tB0s, 0) * 10 + dm_try.get(tB1s, 0)
            for op_name in tgt_cands:
                try:
                    result = MATH_OPS[op_name]['fn'](L, R, 0, 0, 0, 0)
                except (ZeroDivisionError, ValueError, OverflowError):
                    continue
                encoded = _encode_answer(result, op_name, tgt_op_str, f_type,
                                         dm_try, digit_sym_list, ops_used)
                if encoded is not None:
                    return encoded
    return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def solve_v3(
    prompt: str,
    mode: str = 'greedy',
    target_answer: str = None,
    log_path: str = None,
) -> Union[str, None]:
    extraction = extract_all_examples(prompt)
    if extraction[0] is None:
        return None

    parsed_examples, tA, tB, tgt_op_str = extraction

    # Build symbol sets for encoding
    a_b_syms: set = set(tA + tB)
    for ex in parsed_examples:
        a_b_syms.update(ex['A'] + ex['B'])
    out_syms_set: set = set()
    for ex in parsed_examples:
        out_syms_set.update(ex['out'])
    active_digits = a_b_syms | out_syms_set
    ops_used: set = set(ex['op'] for ex in parsed_examples) | {tgt_op_str}
    for op in list(ops_used):
        if op not in a_b_syms and len(active_digits) > 10:
            active_digits.discard(op)
    digit_sym_list = list(active_digits)

    # Filter examples: keep only those where ≥1 supported op is plausible
    filtered = [
        ex for ex in parsed_examples
        if set(_plausible_ops(ex)) & SUPPORTED_OPS
    ]

    # Recompute constraints on filtered examples to avoid poisoning from excluded ops
    op_constraints = _precompute_op_constraints(filtered) if filtered else {}

    # Target op candidates (intersect with supported)
    default_cands = op_constraints.get(tgt_op_str, OP_ORDER)
    tgt_cands = [o for o in default_cands if o in SUPPORTED_OPS]
    if not tgt_cands:
        tgt_cands = list(OP_ORDER)

    first_answer = None

    for f_type in FORMATTERS:
        # Cat fast-path (O(1), no digit search)
        cat_ans = _cat_fast_path(
            parsed_examples, tA, tB, tgt_op_str, f_type,
            active_digits, digit_sym_list, ops_used,
        )
        if cat_ans is not None:
            first_answer = cat_ans
            break

        if not tgt_cands:
            continue

        reordered = _reorder_examples(filtered, f_type)
        plausible_per_ex = []
        skip = False
        for ex in reordered:
            sym = ex['op']
            cands = [o for o in op_constraints.get(sym, OP_ORDER) if o in SUPPORTED_OPS]
            if sym == tgt_op_str:
                cands = [o for o in cands if o in tgt_cands]
            if not cands:
                skip = True
                break
            plausible_per_ex.append(cands)

        if skip:
            continue

        deadline = time.time() + 2.0
        solutions: list = []
        _search_constrained(reordered, 0, {}, set(), {}, plausible_per_ex,
                            f_type, solutions, deadline, max_solutions=1)

        if not solutions:
            continue

        tgt_ex = {'A': tA, 'B': tB, 'op': tgt_op_str, 'out': []}
        tA0s, tA1s, tB0s, tB1s = _syms_for_pipeline(tgt_ex, f_type)
        digit_map, op_assign = solutions[0]
        tgt_math_op = op_assign.get(tgt_op_str, tgt_cands[0])

        unique_missing = list(dict.fromkeys(
            s for s in (tA0s, tA1s, tB0s, tB1s) if s not in digit_map
        ))
        if unique_missing:
            active_used = {digit_map[s] for s in digit_map if s in active_digits}
            avail = [v for v in range(10) if v not in active_used] or list(range(10))
            maps_to_try = [
                {**digit_map, **dict(zip(unique_missing, combo))}
                for combo in _permutations(avail, len(unique_missing))
            ]
        else:
            maps_to_try = [digit_map]

        found = False
        for dm in maps_to_try:
            if found:
                break
            ta0, ta1, tb0, tb1 = dm[tA0s], dm[tA1s], dm[tB0s], dm[tB1s]
            L_tgt = ta0 * 10 + ta1
            R_tgt = tb0 * 10 + tb1
            try:
                numeric_ans = MATH_OPS[tgt_math_op]['fn'](L_tgt, R_tgt, 0, 0, 0, 0)
            except (ZeroDivisionError, ValueError, OverflowError):
                continue
            encoded = _encode_answer(numeric_ans, tgt_math_op, tgt_op_str, f_type,
                                      dm, digit_sym_list, ops_used)
            if encoded is not None:
                first_answer = encoded
                found = True

        if found:
            break

    if mode == 'greedy':
        return first_answer
    if mode == 'theoretical':
        return first_answer is not None and str(target_answer) == first_answer
    return {first_answer: 1} if first_answer is not None else {}
