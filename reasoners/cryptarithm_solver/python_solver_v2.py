"""
python_solver_v2.py — optimized solver with:
  1. Op pre-intersection: intersect plausible ops per op_symbol across all examples
     before entering the digit search (reduces inner loop from ~11 to 1-3 ops).
  2. Example reordering: greedy most-constrained-first — at each step pick the
     example with the fewest unassigned input symbols to minimize branching.
"""
from __future__ import annotations
import sys
import time
from typing import Union

sys.path.insert(0, '/workspaces/nemotron')

from reasoners.cryptarithm_solver.python_solver import (
    MATH_OPS, FORMATTERS,
    extract_all_examples, _plausible_ops, _search,
    _syms_for_pipeline, _encode_answer, _cat_fast_path,
    _permutations,
)


def _precompute_op_constraints(examples: list[dict]) -> dict[str, list[str]]:
    """Intersect plausible ops per op_symbol across all examples using that symbol."""
    op_sym_ops: dict[str, set[str]] = {}
    for ex in examples:
        sym = ex['op']
        plausible = set(_plausible_ops(ex))
        if sym in op_sym_ops:
            op_sym_ops[sym] &= plausible
        else:
            op_sym_ops[sym] = plausible
    return {sym: list(ops) for sym, ops in op_sym_ops.items()}


def _reorder_examples(examples: list[dict], f_type: str) -> list[dict]:
    """Greedy most-constrained-first: pick example with fewest unassigned input symbols."""
    remaining = list(range(len(examples)))
    assigned: set[str] = set()
    ordered: list[dict] = []

    while remaining:
        best = min(
            remaining,
            key=lambda i: sum(
                1 for s in _syms_for_pipeline(examples[i], f_type) if s not in assigned
            ),
        )
        ex = examples[best]
        ordered.append(ex)
        remaining.remove(best)
        assigned.update(_syms_for_pipeline(ex, f_type))
        assigned.update(ex['out'])

    return ordered


def solve_cipher_unified(
    prompt: str,
    mode: str = 'greedy',
    target_answer: str = None,
    log_path: str = None,
) -> Union[str, dict, bool, None]:
    extraction = extract_all_examples(prompt)
    if extraction[0] is None:
        return False if mode == 'theoretical' else None

    parsed_examples, tA, tB, tgt_op_str = extraction

    a_b_syms: set[str] = set(tA + tB)
    for ex in parsed_examples:
        a_b_syms.update(ex['A'] + ex['B'])
    out_syms_set: set[str] = set()
    for ex in parsed_examples:
        out_syms_set.update(ex['out'])
    active_digits = a_b_syms | out_syms_set
    ops_used: set[str] = set(ex['op'] for ex in parsed_examples) | {tgt_op_str}
    for op in list(ops_used):
        if op not in a_b_syms and len(active_digits) > 10:
            active_digits.discard(op)
    digit_sym_list = list(active_digits)

    # Pre-intersect ops once (pipeline-independent — output length doesn't change)
    op_constraints = _precompute_op_constraints(parsed_examples)
    if any(len(ops) == 0 for ops in op_constraints.values()):
        return False if mode == 'theoretical' else None

    first_answer = None

    for f_type in FORMATTERS:
        cat_ans = _cat_fast_path(
            parsed_examples, tA, tB, tgt_op_str, f_type,
            active_digits, digit_sym_list, ops_used,
        )
        if cat_ans is not None:
            first_answer = cat_ans
            break

        reordered = _reorder_examples(parsed_examples, f_type)
        plausible_per_ex = [op_constraints[ex['op']] for ex in reordered]

        deadline = time.time() + 2.0
        solutions: list[tuple[dict, dict]] = []
        _search(
            reordered, 0, {}, set(), {}, plausible_per_ex,
            f_type, solutions, deadline, max_solutions=1,
        )

        if not solutions:
            continue

        tgt_ex = {'A': tA, 'B': tB, 'op': tgt_op_str, 'out': []}
        tA0s, tA1s, tB0s, tB1s = _syms_for_pipeline(tgt_ex, f_type)
        tgt_op_seen = any(ex['op'] == tgt_op_str for ex in parsed_examples)

        digit_map, op_assign = solutions[0]
        if tgt_op_seen:
            tgt_math_op = op_assign.get(tgt_op_str)
            candidate_ops = [tgt_math_op] if tgt_math_op else []
        else:
            candidate_ops = list(MATH_OPS.keys())

        unique_missing = list(
            dict.fromkeys(s for s in (tA0s, tA1s, tB0s, tB1s) if s not in digit_map)
        )
        if unique_missing:
            active_used = {digit_map[s] for s in digit_map if s in active_digits}
            avail = [v for v in range(10) if v not in active_used]
            if len(avail) < len(unique_missing):
                avail = list(range(10))
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
            for tgt_math_op in candidate_ops:
                try:
                    numeric_ans = MATH_OPS[tgt_math_op]['fn'](L_tgt, R_tgt, 0, 0, 0, 0)
                except (ZeroDivisionError, ValueError, OverflowError):
                    continue
                encoded = _encode_answer(
                    numeric_ans, tgt_math_op, tgt_op_str, f_type,
                    dm, digit_sym_list, ops_used,
                )
                if encoded is not None:
                    first_answer = encoded
                    found = True
                    break

        if found:
            break

    if mode == 'greedy':
        return first_answer
    if mode == 'theoretical':
        return first_answer is not None and str(target_answer) == first_answer
    return {first_answer: 1} if first_answer is not None else {}
