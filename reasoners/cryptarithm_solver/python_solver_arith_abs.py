"""
python_solver_arith_abs.py — extends python_solver_arith with a 4th pipeline.

v3 tries: raw, swap, rev
v4 also tries: rev_swap  (operands A↔B swapped, digits MSB-first)

  raw:      L = A[0]*10+A[1],  R = B[0]*10+B[1]   (MSB-first, A op B)
  swap:     L = A[1]*10+A[0],  R = B[1]*10+B[0]   (LSB-first, A op B)
  rev:      L = B[1]*10+B[0],  R = A[1]*10+A[0]   (LSB-first, B op A)
  rev_swap: L = B[0]*10+B[1],  R = A[0]*10+A[1]   (MSB-first, B op A)  ← new

rev_swap lets `sub` compute B−A (positive when B > A), implicitly covering
sub_abs and sub_neg_abs without adding them as explicit ops.

SUPPORTED_OPS: {add, sub, mul, cat}.
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
# Constants — same as v3 except FORMATTERS_V4 adds rev_swap
# ---------------------------------------------------------------------------

SUPPORTED_OPS = frozenset({'add', 'sub', 'mul'})
# OP_ORDER is the fallback when op_constraints has no data for a symbol.
# cat is excluded here because cat imposes no column constraints — it should
# only be tried when op_constraints explicitly says it's plausible (i.e., the
# example's output shape is consistent with concatenation).
OP_ORDER = ['add', 'sub', 'mul']
FORMATTERS_V4 = ['raw', 'swap', 'rev', 'rev_swap']

A0_ORDER = [5, 2, 4, 1, 8, 6, 3, 9, 7, 0]
A1_ORDER = [9, 7, 0, 3, 1, 5, 6, 2, 4, 8]
B0_ORDER = [6, 5, 8, 7, 4, 3, 1, 9, 2, 0]
B1_ORDER = [2, 7, 8, 9, 0, 1, 6, 3, 4, 5]


def _swap_ab(ex: dict) -> dict:
    """Return example with A and B operands swapped."""
    return {**ex, 'A': ex['B'], 'B': ex['A']}


def _normalize_f_type(f_type: str) -> tuple[str, bool]:
    """Return (canonical_f_type, ab_swapped) for internal use.

    rev_swap is handled as raw with A↔B pre-swapped, so all existing
    column-constraint and output-decoding logic works unchanged.
    """
    if f_type == 'rev_swap':
        return 'raw', True
    return f_type, False


# ---------------------------------------------------------------------------
# Column constraint helpers (identical to v3)
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
    else:
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
    elif op_name == 'sub':
        R = L - result
    elif op_name == 'mul':
        if L == 0:
            return None
        if result % L != 0:
            return None
        R = result // L
    elif op_name == 'cat':
        # cat(L, R) = int(str(L) + str(R)). Recover R as the suffix of str(result)
        # after the str(L) prefix. Returns None for cases where R has a leading
        # zero that gets dropped (e.g. cat(0, 7) = 7), falling back to enumeration.
        s_L, s_result = str(L), str(result)
        if not s_result.startswith(s_L):
            return None
        s_R = s_result[len(s_L):]
        if not s_R:
            return None
        R = int(s_R)
    else:
        return None
    return R if 0 <= R <= 99 else None


def _units_val(op_name: str, a1: int, b1: int, is_neg: bool) -> int:
    if op_name == 'add':
        return (a1 + b1) % 10
    if op_name == 'sub':
        return (a1 - b1 + 10) % 10 if not is_neg else (b1 - a1 + 10) % 10
    return (a1 * b1) % 10


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
    if op_name == 'add':
        b1 = (uval - a1 + 10) % 10
        return [b1] if b1 not in used else []
    if op_name == 'sub':
        b1 = (a1 - uval + 10) % 10 if not is_neg else (uval + a1) % 10
        return [b1] if b1 not in used else []
    return [b for b in range(10) if (a1 * b) % 10 == uval and b not in used]


def _b0_from_tens(op_name: str, a0: int, cb1: int, tval: int, is_neg: bool, used: set) -> list:
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
# Branches per-op at the divergence points: b1 derivation from units, b0
# derivation from tens, and result verification. The b0/b1 enumeration loop
# itself is shared across all ops to avoid duplication.
#
#   add/sub: column carry/borrow constraints (single b1, b0 candidate when
#            units/tens digit is known; otherwise enumerate)
#   mul:     b1 derived from units (a1*b1 mod 10 == uval, ≤2 candidates);
#            verify result via _derive_output
#   cat:     no column constraints (units of cat = b1, but we already get
#            this for free from B1s ∈ dm); verify via _derive_output

def _step_op(op_name, L, a0, a1, B0s, B1s, out_syms, op_sym, f_type,
             dm, used, op_assign, examples, ex_idx, plausible, solutions, deadline, max_solutions):
    # Inversion shortcut: if output is fully assigned, derive R algebraically
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

    is_neg, units_sym, tens_sym, hund_sym = _col_syms(out_syms, op_sym, f_type)
    uval_known = units_sym is not None and units_sym in dm

    # b1 candidates — derived from units column when applicable
    if B1s in dm:
        b1_list = [dm[B1s]]
    elif uval_known and op_name != 'cat':
        b1_list = _b1_from_units(op_name, a1, dm[units_sym], is_neg, used)
    else:
        b1_list = [v for v in B1_ORDER if v not in used]

    for b1 in b1_list:
        dm_b1, used_b1, ok = _try_assign(B1s, b1, dm, used)
        if not ok:
            continue

        cb1 = _carry1(op_name, a1, b1, is_neg)

        # Per-op units constraint
        if op_name in ('add', 'sub'):
            # add/sub: units of result is fully determined → assign it
            uv = _units_val(op_name, a1, b1, is_neg)
            if units_sym:
                dm_b1, used_b1, ok = _try_assign(units_sym, uv, dm_b1, used_b1)
                if not ok:
                    continue
        elif op_name == 'mul':
            # mul: only verify (output has more digits, others come from _derive_output)
            uv = (a1 * b1) % 10
            if units_sym and units_sym in dm_b1 and dm_b1[units_sym] != uv:
                continue
        # cat: units_sym == B1s for raw, already consistent via _try_assign above

        # b0 candidates — derived from tens column for add/sub when applicable
        if B0s in dm_b1:
            b0_list = [dm_b1[B0s]]
        elif op_name in ('add', 'sub') and tens_sym is not None and tens_sym in dm_b1:
            b0_list = _b0_from_tens(op_name, a0, cb1, dm_b1[tens_sym], is_neg, used_b1)
        else:
            b0_list = [v for v in B0_ORDER if v not in used_b1]

        for b0 in b0_list:
            dm_b0, used_b0, ok = _try_assign(B0s, b0, dm_b1, used_b1)
            if not ok:
                continue

            # Per-op result verification
            if op_name in ('add', 'sub'):
                cb2 = _carry2(op_name, a0, b0, cb1, is_neg)
                if op_name == 'sub' and cb2 != 0:
                    continue
                tval = _tens_val(op_name, a0, b0, cb1, is_neg)
                dm_f, used_f = dm_b0, used_b0
                if tens_sym:
                    dm_f, used_f, ok = _try_assign(tens_sym, tval, dm_f, used_f)
                    if not ok:
                        continue
                if hund_sym:
                    dm_f, used_f, ok = _try_assign(hund_sym, cb2, dm_f, used_f)
                    if not ok:
                        continue
            else:  # mul, cat — verify via _derive_output
                try:
                    result_val = MATH_OPS[op_name]['fn'](L, b0 * 10 + b1, 0, 0, 0, 0)
                except (ZeroDivisionError, ValueError, OverflowError):
                    continue
                new_out, ok = _derive_output(result_val, out_syms, f_type, op_name, op_sym, dm_b0, used_b0)
                if not ok:
                    continue
                dm_f = {**dm_b0, **new_out}
                used_f = used_b0 | set(new_out.values())

            _search_constrained(examples, ex_idx + 1, dm_f, used_f,
                                {**op_assign, op_sym: op_name},
                                plausible, f_type, solutions, deadline, max_solutions)
            if len(solutions) >= max_solutions:
                return


# ---------------------------------------------------------------------------
# Main search (identical to v3)
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
# Fallback (identical to v3)
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

def solve_v4(
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

    for f_type in FORMATTERS_V4:
        canonical_f, ab_swapped = _normalize_f_type(f_type)

        # For rev_swap: swap A↔B in every example so existing raw-pipeline
        # logic computes B−A, B+A, B*A instead of A−B, etc.
        if ab_swapped:
            examples_for_search = [_swap_ab(ex) for ex in filtered]
            tgt_ex_base = {'A': tB, 'B': tA, 'op': tgt_op_str, 'out': []}
        else:
            examples_for_search = filtered
            tgt_ex_base = {'A': tA, 'B': tB, 'op': tgt_op_str, 'out': []}

        # Cat fast-path uses parsed_examples (all, not just filtered)
        cat_ans = _cat_fast_path(
            [_swap_ab(ex) for ex in parsed_examples] if ab_swapped else parsed_examples,
            tB if ab_swapped else tA,
            tA if ab_swapped else tB,
            tgt_op_str, canonical_f,
            active_digits, digit_sym_list, ops_used,
        )
        if cat_ans is not None:
            first_answer = cat_ans
            break

        if not tgt_cands:
            continue

        reordered = _reorder_examples(examples_for_search, canonical_f)
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
                            canonical_f, solutions, deadline, max_solutions=1)

        if not solutions:
            continue

        tA0s, tA1s, tB0s, tB1s = _syms_for_pipeline(tgt_ex_base, canonical_f)
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
            # tA0s/tA1s are the TARGET's A-side (may be B's symbols if ab_swapped)
            L_tgt = ta0 * 10 + ta1
            R_tgt = tb0 * 10 + tb1
            try:
                numeric_ans = MATH_OPS[tgt_math_op]['fn'](L_tgt, R_tgt, 0, 0, 0, 0)
            except (ZeroDivisionError, ValueError, OverflowError):
                continue
            encoded = _encode_answer(numeric_ans, tgt_math_op, tgt_op_str, canonical_f,
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


def solve_v4_all_answers(prompt: str, max_solutions_per_pipeline: int = 200,
                         deadline_s: float = 5.0) -> set[str]:
    """Return every distinct target-answer encoding v4 can produce for `prompt`.

    Used by tests to check whether the golden answer is *among* v4's outputs
    when the puzzle is ambiguous (multiple ciphers consistent with examples).
    """
    extraction = extract_all_examples(prompt)
    if extraction[0] is None:
        return set()
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

    filtered = [ex for ex in parsed_examples
                if set(_plausible_ops(ex)) & SUPPORTED_OPS]
    op_constraints = _precompute_op_constraints(filtered) if filtered else {}

    default_cands = op_constraints.get(tgt_op_str, OP_ORDER)
    tgt_cands = [o for o in default_cands if o in SUPPORTED_OPS]
    if not tgt_cands:
        tgt_cands = list(OP_ORDER)

    answers: set[str] = set()

    for f_type in FORMATTERS_V4:
        canonical_f, ab_swapped = _normalize_f_type(f_type)

        if ab_swapped:
            examples_for_search = [_swap_ab(ex) for ex in filtered]
            tgt_ex_base = {'A': tB, 'B': tA, 'op': tgt_op_str, 'out': []}
        else:
            examples_for_search = filtered
            tgt_ex_base = {'A': tA, 'B': tB, 'op': tgt_op_str, 'out': []}

        cat_ans = _cat_fast_path(
            [_swap_ab(ex) for ex in parsed_examples] if ab_swapped else parsed_examples,
            tB if ab_swapped else tA,
            tA if ab_swapped else tB,
            tgt_op_str, canonical_f,
            active_digits, digit_sym_list, ops_used,
        )
        if cat_ans is not None:
            answers.add(cat_ans)

        if not tgt_cands:
            continue

        reordered = _reorder_examples(examples_for_search, canonical_f)
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

        deadline = time.time() + deadline_s
        solutions: list = []
        _search_constrained(reordered, 0, {}, set(), {}, plausible_per_ex,
                            canonical_f, solutions, deadline,
                            max_solutions=max_solutions_per_pipeline)

        if not solutions:
            continue

        tA0s, tA1s, tB0s, tB1s = _syms_for_pipeline(tgt_ex_base, canonical_f)

        for digit_map, op_assign in solutions:
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

            for dm in maps_to_try:
                ta0, ta1, tb0, tb1 = dm[tA0s], dm[tA1s], dm[tB0s], dm[tB1s]
                L_tgt = ta0 * 10 + ta1
                R_tgt = tb0 * 10 + tb1
                try:
                    numeric_ans = MATH_OPS[tgt_math_op]['fn'](L_tgt, R_tgt, 0, 0, 0, 0)
                except (ZeroDivisionError, ValueError, OverflowError):
                    continue
                encoded = _encode_answer(numeric_ans, tgt_math_op, tgt_op_str, canonical_f,
                                          dm, digit_sym_list, ops_used)
                if encoded is not None:
                    answers.add(encoded)

    return answers
