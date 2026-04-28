"""
Benchmark arith constrained solver against baseline and prefilter on add/sub/mul/cat problems.
"""
from __future__ import annotations
import sys
import json
import time

sys.path.insert(0, '/workspaces/nemotron')

from tqdm import tqdm
from reasoners.store_types import Problem
import reasoners.cryptarithm_solver.python_solver as _ps
import reasoners.cryptarithm_solver.python_solver_prefilter as _ps2
import reasoners.cryptarithm_solver.python_solver_arith as _ps3
from reasoners.cryptarithm_solver.python_solver_arith import solve_v3
from reasoners.cryptarithm_solver.python_solver import (
    MATH_OPS, FORMATTERS, extract_all_examples, _plausible_ops,
    _syms_for_pipeline, _encode_answer, _cat_fast_path, _permutations, _search,
)

SUPPORTED_OPS = ('add', 'sub', 'mul', 'cat')


def _solve_baseline(prompt):
    return _ps.solve_cipher_unified(prompt, mode='greedy')


def _solve_v2(prompt):
    return _ps2.solve_cipher_unified(prompt, mode='greedy')


def run_variant(problems, label, solve_fn):
    records = []
    for p in tqdm(problems, desc=label, unit='prob'):
        ops_counter = [0]
        orig = _ps._derive_output

        def _counted(*args, **kwargs):
            ops_counter[0] += 1
            return orig(*args, **kwargs)

        _ps._derive_output = _counted
        _ps2._derive_output = _counted
        _ps3._derive_output = _counted
        try:
            t0 = time.time()
            ans = solve_fn(p.prompt)
            elapsed = time.time() - t0
        finally:
            _ps._derive_output = orig
            _ps2._derive_output = orig
            _ps3._derive_output = orig

        records.append({
            'id': p.id,
            'expected': str(p.answer),
            'got': str(ans),
            'correct': str(ans) == str(p.answer),
            'ops': ops_counter[0],
            'elapsed': elapsed,
        })
    return records


def _pct(vals, p):
    if not vals:
        return 0
    s = sorted(vals)
    return s[min(int(len(s) * p / 100), len(s) - 1)]


def _build_op_index(problems):
    """Run v2 solver internals to discover target op per problem."""
    from reasoners.cryptarithm_solver.python_solver_v2 import _precompute_op_constraints, _reorder_examples
    from reasoners.cryptarithm_solver.python_solver import (
        extract_all_examples, _cat_fast_path, _search, _syms_for_pipeline,
        FORMATTERS,
    )
    index = {}
    for p in tqdm(problems, desc='building op_index', unit='prob'):
        extraction = extract_all_examples(p.prompt)
        if extraction[0] is None:
            index[p.id] = {'target_op': None, 'correct': False, 'pipeline': None}
            continue
        parsed_examples, tA, tB, tgt_op_str = extraction
        a_b_syms = set(tA + tB)
        for ex in parsed_examples:
            a_b_syms.update(ex['A'] + ex['B'])
        out_syms_set = set()
        for ex in parsed_examples:
            out_syms_set.update(ex['out'])
        active_digits = a_b_syms | out_syms_set
        ops_used = set(ex['op'] for ex in parsed_examples) | {tgt_op_str}
        for op in list(ops_used):
            if op not in a_b_syms and len(active_digits) > 10:
                active_digits.discard(op)
        digit_sym_list = list(active_digits)
        op_constraints = _precompute_op_constraints(parsed_examples)
        if any(len(ops) == 0 for ops in op_constraints.values()):
            index[p.id] = {'target_op': None, 'correct': False, 'pipeline': None}
            continue
        found_op, found_pipeline = None, None
        for f_type in FORMATTERS:
            cat_ans = _cat_fast_path(parsed_examples, tA, tB, tgt_op_str, f_type,
                                     active_digits, digit_sym_list, ops_used)
            if cat_ans is not None:
                if str(cat_ans) == str(p.answer):
                    found_op, found_pipeline = 'cat', f_type
                break
            reordered = _reorder_examples(parsed_examples, f_type)
            plausible_per_ex = [op_constraints[ex['op']] for ex in reordered]
            solutions = []
            _search(reordered, 0, {}, set(), {}, plausible_per_ex, f_type, solutions,
                    time.time() + 2.0, max_solutions=1)
            if solutions:
                _, op_assign = solutions[0]
                found_op = op_assign.get(tgt_op_str)
                found_pipeline = f_type
                break
        index[p.id] = {'target_op': found_op, 'correct': False, 'pipeline': found_pipeline}
    return index


def main():
    index_path = '/workspaces/nemotron/reasoners/cryptarithm_solver/op_index.json'
    all_problems_for_index = [p for p in Problem.load_all() if 'cryptarithm' in p.category]
    if not __import__('os').path.exists(index_path):
        print("op_index.json not found — building now (~60s)...")
        op_index = _build_op_index(all_problems_for_index)
        with open(index_path, 'w') as f:
            json.dump(op_index, f)
        print(f"Saved {len(op_index)} entries to op_index.json\n")
    else:
        with open(index_path) as f:
            op_index = json.load(f)

    all_problems = [p for p in Problem.load_all() if 'cryptarithm' in p.category]
    problems = [
        p for p in all_problems
        if op_index.get(p.id, {}).get('target_op') in SUPPORTED_OPS
    ]

    n = len(problems)
    counts = {op: sum(1 for p in problems if op_index[p.id]['target_op'] == op)
              for op in SUPPORTED_OPS}
    print(f"Filtered to {n} problems  " + "  ".join(f"{op}={counts[op]}" for op in SUPPORTED_OPS))
    print()

    VARIANTS = [
        ('baseline', _solve_baseline),
        ('v2',       _solve_v2),
        ('v3',       solve_v3),
    ]

    all_records = {}
    for label, fn in VARIANTS:
        all_records[label] = run_variant(problems, label, fn)

    baseline_total = sum(r['ops'] for r in all_records['baseline'])
    baseline_correct = sum(1 for r in all_records['baseline'] if r['correct'])

    print(f"\n{'Variant':<10}  {'Correct':>8}  {'Total ops':>14}  {'Reduction':>10}  {'P50 ops':>10}  {'P95 ops':>10}  {'Time':>6}")
    print('-' * 78)
    for label, _ in VARIANTS:
        recs = all_records[label]
        correct = sum(1 for r in recs if r['correct'])
        ops = [r['ops'] for r in recs]
        total = sum(ops)
        elapsed = sum(r['elapsed'] for r in recs)
        reduction = baseline_total / total if total > 0 else 0
        delta = correct - baseline_correct
        delta_str = f"({delta:+d})" if label != 'baseline' else '     '
        print(f"{label:<10}  {correct:>4}/{n:<3} {delta_str}  {total:>14,}  {reduction:>9.2f}x"
              f"  {_pct(ops,50):>10,}  {_pct(ops,95):>10,}  {elapsed:>5.1f}s")

    print(f"\n{'':=<78}")
    print("Per-op breakdown:\n")
    for op_name in SUPPORTED_OPS:
        op_ids = {p.id for p in problems if op_index[p.id]['target_op'] == op_name}
        if not op_ids:
            continue
        rows = []
        for label, _ in VARIANTS:
            recs = [r for r in all_records[label] if r['id'] in op_ids]
            correct = sum(1 for r in recs if r['correct'])
            total_ops = sum(r['ops'] for r in recs)
            n_op = len(recs)
            rows.append((label, correct, n_op, total_ops))
        base_ops = rows[0][3]
        for label, correct, n_op, total_ops in rows:
            red = base_ops / total_ops if total_ops > 0 else 0
            print(f"  {op_name:<5}  {label:<10}  correct={correct}/{n_op}  "
                  f"total_ops={total_ops:>10,}  reduction={red:.2f}x")
        print()

    regressions = [
        (r1, r2) for r1, r2 in zip(all_records['baseline'], all_records['v3'])
        if r1['correct'] and not r2['correct']
    ]
    if regressions:
        print(f"Regressions vs baseline (baseline correct, v3 wrong): {len(regressions)}")
        for r1, r2 in regressions[:10]:
            print(f"  {r1['id'][:12]}  baseline_ops={r1['ops']:,}  v3_ops={r2['ops']:,}")
    else:
        print("No regressions vs baseline.")


if __name__ == '__main__':
    main()
