"""Quick comparison of v8 vs baseline python_solver on the 657-puzzle set."""
from __future__ import annotations
import sys
import json
import time

sys.path.insert(0, '/workspaces/nemotron')

from tqdm import tqdm
from reasoners.store_types import Problem
from reasoners.cryptarithm_solver.python_solver import solve_cipher_unified
from reasoners.cryptarithm_solver.python_solver_arith_full import solve_v8

INDEX_PATH = '/workspaces/nemotron/reasoners/cryptarithm_solver/op_index.json'
SUPPORTED_OPS = ('add', 'sub', 'mul', 'cat', 'add1', 'addm1', 'mul1',
                 'mulm1', 'sub_abs', 'sub_neg_abs', 'max_mod_min')


def main():
    with open(INDEX_PATH) as f:
        op_index = json.load(f)

    all_problems = [p for p in Problem.load_all() if 'cryptarithm' in p.category]
    problems = [p for p in all_problems
                if op_index.get(p.id, {}).get('target_op') in SUPPORTED_OPS]
    n = len(problems)
    print(f'Filtered to {n} problems')

    results = {'baseline': [], 'v8': []}
    for label, fn in (('baseline', solve_cipher_unified), ('v8', solve_v8)):
        for p in tqdm(problems, desc=label, unit='prob'):
            t0 = time.time()
            ans = fn(p.prompt)
            elapsed = time.time() - t0
            results[label].append({
                'id': p.id,
                'target_op': op_index[p.id]['target_op'],
                'expected': str(p.answer),
                'got': str(ans),
                'correct': str(ans) == str(p.answer),
                'elapsed': elapsed,
            })

    # Per-op summary
    by_op = {op: {'baseline': 0, 'v8': 0, 'total': 0} for op in SUPPORTED_OPS}
    for r_b, r_v in zip(results['baseline'], results['v8']):
        op = r_b['target_op']
        by_op[op]['total'] += 1
        if r_b['correct']:
            by_op[op]['baseline'] += 1
        if r_v['correct']:
            by_op[op]['v8'] += 1

    print(f'\n{"Op":<14}  {"Baseline":>10}  {"v8":>10}  {"Δ":>5}  {"v8 / base":>10}')
    print('-' * 55)
    for op in SUPPORTED_OPS:
        b, v, t = by_op[op]['baseline'], by_op[op]['v8'], by_op[op]['total']
        if t == 0: continue
        delta = v - b
        ratio = v / b if b > 0 else float('inf')
        print(f'{op:<14}  {b:>4}/{t:<4}  {v:>4}/{t:<4}  {delta:>+5d}  {ratio:>9.2f}x')

    b_total = sum(1 for r in results['baseline'] if r['correct'])
    v_total = sum(1 for r in results['v8'] if r['correct'])
    print('-' * 55)
    print(f'{"TOTAL":<14}  {b_total:>4}/{n:<4}  {v_total:>4}/{n:<4}  {v_total - b_total:>+5d}  {v_total/b_total:>9.2f}x')

    b_time = sum(r['elapsed'] for r in results['baseline'])
    v_time = sum(r['elapsed'] for r in results['v8'])
    print(f'\nElapsed: baseline {b_time:.1f}s  v8 {v_time:.1f}s  speedup {b_time/v_time:.1f}x')

    # Where v8 wins, where baseline wins
    v8_only = [(rb, rv) for rb, rv in zip(results['baseline'], results['v8'])
               if not rb['correct'] and rv['correct']]
    base_only = [(rb, rv) for rb, rv in zip(results['baseline'], results['v8'])
                 if rb['correct'] and not rv['correct']]
    print(f'\nv8 correct, baseline wrong: {len(v8_only)}')
    print(f'baseline correct, v8 wrong: {len(base_only)}')
    if base_only:
        from collections import Counter
        c = Counter(r['target_op'] for _, r in base_only)
        print(f'  baseline-only wins by op: {dict(c)}')


if __name__ == '__main__':
    main()
