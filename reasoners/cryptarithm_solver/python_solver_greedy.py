"""Log-free greedy variant of solve_cipher_unified for fair benchmarking."""
from __future__ import annotations
import sys
import time
from typing import Union

sys.path.insert(0, '/workspaces/nemotron')

from reasoners.cryptarithm_solver.python_solver import (
    FORMATTERS, MATH_OPS,
    extract_all_examples, _plausible_ops, _search,
    _syms_for_pipeline, _encode_answer, _cat_fast_path,
    _permutations,
)


def solve_baseline_greedy(prompt: str) -> Union[str, None]:
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

    first_answer = None

    for f_type in FORMATTERS:
        deadline = time.time() + 2.0

        plausible_per_ex = []
        skip = False
        for ex in parsed_examples:
            ops = _plausible_ops(ex)
            if not ops:
                skip = True
                break
            plausible_per_ex.append(ops)
        if skip:
            continue

        cat_ans = _cat_fast_path(
            parsed_examples, tA, tB, tgt_op_str, f_type,
            active_digits, digit_sym_list, ops_used,
        )
        if cat_ans is not None:
            first_answer = cat_ans
            break

        solutions: list = []
        _search(parsed_examples, 0, {}, set(), {}, plausible_per_ex,
                f_type, solutions, deadline, max_solutions=1)
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

        target_syms_4 = (tA0s, tA1s, tB0s, tB1s)
        unique_missing = list(dict.fromkeys(s for s in target_syms_4 if s not in digit_map))

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

    return first_answer
