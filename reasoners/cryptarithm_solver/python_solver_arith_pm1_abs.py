"""
python_solver_arith_pm1_abs.py — v6: branched from v5 (python_solver_arith_pm1.py).

Adds support for absolute-value sub variants on top of v5's
{add, sub, mul, cat, add1, addm1, mul1, mulm1}:
  - sub_abs       (|L - R|)
  - sub_neg_abs   (-|L - R|)

Both share a 2-branch column scheme:
  Branch A (L >= R): magnitude = L - R, columns = standard sub
  Branch B (L < R):  magnitude = R - L, columns = sub with operands swapped

sub_abs requires the output to have NO sign symbol; sub_neg_abs requires the
output to ALWAYS have a sign symbol (the L = R → 0 edge is rare and skipped).
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

SUPPORTED_OPS = frozenset({
    'add', 'sub', 'mul', 'add1', 'addm1', 'mul1', 'mulm1',
    'sub_abs', 'sub_neg_abs',
})
# Empirical frequency order (from empirical_ordering_report.md):
# add, sub, mul, sub_abs, addm1, mul1, sub_neg_abs, add1, mulm1
OP_ORDER = ['add', 'sub', 'mul', 'sub_abs', 'addm1', 'mul1',
            'sub_neg_abs', 'add1', 'mulm1']

ADDLIKE_OPS = frozenset({'add', 'sub', 'add1', 'addm1'})
MULLIKE_OPS = frozenset({'mul', 'mul1', 'mulm1'})
ABSLIKE_OPS = frozenset({'sub_abs', 'sub_neg_abs'})

A0_ORDER = [5, 2, 4, 1, 8, 6, 3, 9, 7, 0]
A1_ORDER = [9, 7, 0, 3, 1, 5, 6, 2, 4, 8]
B0_ORDER = [6, 5, 8, 7, 4, 3, 1, 9, 2, 0]
B1_ORDER = [2, 7, 8, 9, 0, 1, 6, 3, 4, 5]


# ---------------------------------------------------------------------------
# Column constraint helpers
# ---------------------------------------------------------------------------

def _decode_result_numeric(out_syms: list, op_sym: str, f_type: str, dm: dict) -> int | None:
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
    if sym in dm:
        return dm, used, dm[sym] == val
    if val in used:
        return dm, used, False
    return {**dm, sym: val}, used | {val}, True


def _invert_op(op_name: str, L: int, result: int) -> int | None:
    if op_name == 'add':
        R = result - L
    elif op_name == 'add1':
        R = result - L - 1
    elif op_name == 'addm1':
        R = result - L + 1
    elif op_name == 'sub':
        R = L - result
    elif op_name == 'mul':
        if L == 0 or result % L != 0:
            return None
        R = result // L
    elif op_name == 'mul1':
        if L == 0 or (result - 1) % L != 0:
            return None
        R = (result - 1) // L
    elif op_name == 'mulm1':
        if L == 0 or (result + 1) % L != 0:
            return None
        R = (result + 1) // L
    else:
        return None
    return R if 0 <= R <= 99 else None


def _units_val(op_name: str, a1: int, b1: int, is_neg: bool) -> int:
    if op_name == 'add':
        return (a1 + b1) % 10
    if op_name == 'add1':
        return (a1 + b1 + 1) % 10
    if op_name == 'addm1':
        return (a1 + b1 - 1 + 10) % 10
    if op_name == 'sub':
        return (a1 - b1 + 10) % 10 if not is_neg else (b1 - a1 + 10) % 10
    return (a1 * b1) % 10  # mul-like


def _carry1(op_name: str, a1: int, b1: int, is_neg: bool) -> int:
    if op_name == 'add':
        return (a1 + b1) // 10
    if op_name == 'add1':
        return (a1 + b1 + 1) // 10
    if op_name == 'addm1':
        # Caller guarantees a1 + b1 >= 1 (column path skips L+R=0 edge).
        return (a1 + b1 - 1) // 10
    if op_name == 'sub':
        return int(a1 < b1) if not is_neg else int(b1 < a1)
    return 0


def _tens_val(op_name: str, a0: int, b0: int, cb1: int, is_neg: bool) -> int:
    if op_name in ('add', 'add1', 'addm1'):
        return (a0 + b0 + cb1) % 10
    if op_name == 'sub':
        return (a0 - cb1 - b0 + 10) % 10 if not is_neg else (b0 - a0 - cb1 + 10) % 10
    return 0


def _carry2(op_name: str, a0: int, b0: int, cb1: int, is_neg: bool) -> int:
    if op_name in ('add', 'add1', 'addm1'):
        return (a0 + b0 + cb1) // 10
    if op_name == 'sub':
        return int((a0 - cb1) < b0) if not is_neg else int((b0 - a0 - cb1) < 0)
    return 0


def _b1_from_units(op_name: str, a1: int, uval: int, is_neg: bool, used: set) -> list:
    if op_name == 'add':
        b1 = (uval - a1 + 10) % 10
        return [b1] if b1 not in used else []
    if op_name == 'add1':
        b1 = (uval - a1 - 1 + 20) % 10
        return [b1] if b1 not in used else []
    if op_name == 'addm1':
        b1 = (uval - a1 + 1 + 10) % 10
        return [b1] if b1 not in used else []
    if op_name == 'sub':
        b1 = (a1 - uval + 10) % 10 if not is_neg else (uval + a1) % 10
        return [b1] if b1 not in used else []
    if op_name == 'mul':
        return [b for b in range(10) if (a1 * b) % 10 == uval and b not in used]
    if op_name == 'mul1':
        target = (uval - 1 + 10) % 10
        return [b for b in range(10) if (a1 * b) % 10 == target and b not in used]
    if op_name == 'mulm1':
        target = (uval + 1) % 10
        return [b for b in range(10) if (a1 * b) % 10 == target and b not in used]
    return []


def _b0_from_tens(op_name: str, a0: int, cb1: int, tval: int, is_neg: bool, used: set) -> list:
    # add / add1 / addm1 share the same tens-carry shape (carry already shifted by ±1).
    if op_name in ('add', 'add1', 'addm1'):
        b0 = (tval - a0 - cb1 + 10) % 10
        return [b0] if b0 not in used else []
    if op_name == 'sub':
        b0 = (a0 - cb1 - tval + 10) % 10 if not is_neg else (tval + a0 + cb1) % 10
        return [b0] if b0 not in used else []
    return []


# ---------------------------------------------------------------------------
# Per-example operation step
# ---------------------------------------------------------------------------

def _step_sub_abs(op_name, L, a0, a1, B0s, B1s, out_syms, op_sym, f_type,
                  dm, used, op_assign, examples, ex_idx, plausible,
                  solutions, deadline, max_solutions):
    """Two-branch column derivation for sub_abs / sub_neg_abs."""
    is_neg, units_sym, tens_sym, hund_sym = _col_syms(out_syms, op_sym, f_type)

    # Output sign must match op
    if op_name == 'sub_abs' and is_neg:
        return
    if op_name == 'sub_neg_abs' and not is_neg:
        return

    # 1. Algebraic inversion when output fully decoded
    result = _decode_result_numeric(out_syms, op_sym, f_type, dm)
    if result is not None:
        if op_name == 'sub_abs' and result < 0:
            return
        if op_name == 'sub_neg_abs' and result > 0:
            return
        mag = abs(result)
        for R in {L - mag, L + mag}:
            if 0 <= R <= 99:
                dm2, used2, ok = _try_assign(B0s, R // 10, dm, used)
                if not ok:
                    continue
                dm3, used3, ok = _try_assign(B1s, R % 10, dm2, used2)
                if not ok:
                    continue
                _search_constrained(examples, ex_idx + 1, dm3, used3,
                                    {**op_assign, op_sym: op_name},
                                    plausible, f_type, solutions, deadline, max_solutions)
                if len(solutions) >= max_solutions:
                    return
        return

    # 2. Column derivation across both branches
    for branch in ('A', 'B'):
        # b1 candidates from units_sym
        if B1s in dm:
            b1_list = [dm[B1s]]
        elif units_sym is not None and units_sym in dm:
            uval = dm[units_sym]
            if branch == 'A':
                b1 = (a1 - uval + 10) % 10
            else:
                b1 = (a1 + uval) % 10
            b1_list = [b1] if b1 not in used else []
        else:
            b1_list = [v for v in B1_ORDER if v not in used]

        for b1 in b1_list:
            dm_b1, used_b1, ok = _try_assign(B1s, b1, dm, used)
            if not ok:
                continue

            if branch == 'A':
                bw1 = int(a1 < b1)
                uv = (a1 - b1 + 10) % 10
            else:
                bw1 = int(b1 < a1)
                uv = (b1 - a1 + 10) % 10

            if units_sym:
                dm_b1, used_b1, ok = _try_assign(units_sym, uv, dm_b1, used_b1)
                if not ok:
                    continue

            # b0 candidates from tens_sym
            if B0s in dm_b1:
                b0_list = [dm_b1[B0s]]
            elif tens_sym is not None and tens_sym in dm_b1:
                tval = dm_b1[tens_sym]
                if branch == 'A':
                    b0 = (a0 - bw1 - tval + 10) % 10
                else:
                    b0 = (tval + a0 + bw1) % 10
                b0_list = [b0] if b0 not in used_b1 else []
            else:
                b0_list = [v for v in B0_ORDER if v not in used_b1]

            for b0 in b0_list:
                dm_b0, used_b0, ok = _try_assign(B0s, b0, dm_b1, used_b1)
                if not ok:
                    continue

                if branch == 'A':
                    tval = (a0 - bw1 - b0 + 10) % 10
                    bw2 = int((a0 - bw1) < b0)
                else:
                    tval = (b0 - bw1 - a0 + 10) % 10
                    bw2 = int((b0 - bw1) < a0)

                # Branch validity: borrow-out must be 0 (i.e., L >= R for A, R > L for B)
                if bw2 != 0:
                    continue

                # Direction check (redundant with bw2 but explicit)
                R = b0 * 10 + b1
                if branch == 'A' and L < R:
                    continue
                if branch == 'B' and L >= R:
                    continue

                dm_f, used_f = dm_b0, used_b0
                if tens_sym:
                    dm_f, used_f, ok = _try_assign(tens_sym, tval, dm_f, used_f)
                    if not ok:
                        continue
                if hund_sym:
                    dm_f, used_f, ok = _try_assign(hund_sym, 0, dm_f, used_f)
                    if not ok:
                        continue

                _search_constrained(examples, ex_idx + 1, dm_f, used_f,
                                    {**op_assign, op_sym: op_name},
                                    plausible, f_type, solutions, deadline, max_solutions)
                if len(solutions) >= max_solutions:
                    return


def _step_op(op_name, L, a0, a1, B0s, B1s, out_syms, op_sym, f_type,
             dm, used, op_assign, examples, ex_idx, plausible, solutions, deadline, max_solutions):

    if op_name in ABSLIKE_OPS:
        _step_sub_abs(op_name, L, a0, a1, B0s, B1s, out_syms, op_sym, f_type,
                      dm, used, op_assign, examples, ex_idx, plausible,
                      solutions, deadline, max_solutions)
        return

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
        return

    # 2. Column-level derivation
    is_neg, units_sym, tens_sym, hund_sym = _col_syms(out_syms, op_sym, f_type)

    # add1 / mul1 cannot produce negative results — reject when output has sign.
    if is_neg and op_name in ('add1', 'mul1'):
        return

    uval_known = units_sym is not None and units_sym in dm

    # b1 candidates
    if B1s in dm:
        b1_list = [dm[B1s]]
    elif uval_known:
        b1_list = _b1_from_units(op_name, a1, dm[units_sym], is_neg, used)
    else:
        b1_list = [v for v in B1_ORDER if v not in used]

    is_addlike = op_name in ADDLIKE_OPS
    is_mullike = op_name in MULLIKE_OPS

    for b1 in b1_list:
        # addm1 column path is undefined when a1 + b1 == 0 (gives -1 carry); skip.
        if op_name == 'addm1' and a1 + b1 == 0:
            continue

        dm_b1, used_b1, ok = _try_assign(B1s, b1, dm, used)
        if not ok:
            continue

        cb1 = _carry1(op_name, a1, b1, is_neg)
        uv = _units_val(op_name, a1, b1, is_neg)

        if is_addlike:
            if units_sym:
                dm_b1, used_b1, ok = _try_assign(units_sym, uv, dm_b1, used_b1)
                if not ok:
                    continue
        else:
            # mul-like: only verify if units_sym pre-assigned
            if units_sym and units_sym in dm_b1 and dm_b1[units_sym] != uv:
                continue

        tval_known = tens_sym is not None and tens_sym in dm_b1

        if B0s in dm_b1:
            b0_list = [dm_b1[B0s]]
        elif is_addlike and tval_known:
            b0_list = _b0_from_tens(op_name, a0, cb1, dm_b1[tens_sym], is_neg, used_b1)
        else:
            b0_list = [v for v in B0_ORDER if v not in used_b1]

        for b0 in b0_list:
            dm_b0, used_b0, ok = _try_assign(B0s, b0, dm_b1, used_b1)
            if not ok:
                continue

            if is_mullike:
                R = b0 * 10 + b1
                if op_name == 'mul':
                    result_val = L * R
                elif op_name == 'mul1':
                    result_val = L * R + 1
                else:  # mulm1
                    result_val = L * R - 1
                new_out, ok = _derive_output(result_val, out_syms, f_type, op_name, op_sym, dm_b0, used_b0)
                if not ok:
                    continue
                dm_f = {**dm_b0, **new_out}
                used_f = used_b0 | set(new_out.values())
            else:
                cb2 = _carry2(op_name, a0, b0, cb1, is_neg)
                tval = _tens_val(op_name, a0, b0, cb1, is_neg)

                # sub validity: borrow-out means crossed sign boundary
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
# Fallback
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

def solve_v6(
    prompt: str,
    mode: str = 'greedy',
    target_answer: str = None,
    log_path: str = None,
) -> Union[str, None]:
    extraction = extract_all_examples(prompt)
    if extraction[0] is None:
        return None

    parsed_examples, tA, tB, tgt_op_str = extraction

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

    filtered = [
        ex for ex in parsed_examples
        if set(_plausible_ops(ex)) & SUPPORTED_OPS
    ]

    op_constraints = _precompute_op_constraints(filtered) if filtered else {}

    default_cands = op_constraints.get(tgt_op_str, OP_ORDER)
    tgt_cands = [o for o in default_cands if o in SUPPORTED_OPS]
    if not tgt_cands:
        tgt_cands = list(OP_ORDER)

    first_answer = None

    for f_type in FORMATTERS:
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
