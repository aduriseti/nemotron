"""Find specific exhausted puzzles for each op for targeted debugging."""
from __future__ import annotations
import sys
import json
import time

sys.path.insert(0, '/workspaces/nemotron')

from reasoners.store_types import Problem
from reasoners.cryptarithm_solver.python_solver_arith_full import solve_v8
from reasoners.cryptarithm_solver.python_solver_greedy import solve_baseline_greedy

INDEX_PATH = '/workspaces/nemotron/reasoners/cryptarithm_solver/op_index.json'
SUPPORTED_OPS = ('add', 'sub', 'mul', 'cat', 'add1', 'addm1', 'mul1',
                 'mulm1', 'sub_abs', 'sub_neg_abs', 'max_mod_min')


def main():
    op_index = json.load(open(INDEX_PATH))
    problems = [p for p in Problem.load_all()
                if 'cryptarithm' in p.category
                and op_index.get(p.id, {}).get('target_op') in SUPPORTED_OPS]

    by_op = {op: [] for op in SUPPORTED_OPS}
    for p in problems:
        target = op_index[p.id]['target_op']
        t0 = time.time()
        ans = solve_v8(p.prompt)
        elapsed = time.time() - t0
        if ans is None and elapsed < 1.9:
            by_op[target].append((p, elapsed))

    print('Exhausted puzzles per op (no answer, < 1.9s):')
    for op, entries in by_op.items():
        if not entries:
            continue
        print(f'\n{op}: {len(entries)} exhausted')
        for p, el in entries[:3]:
            base_ans = solve_baseline_greedy(p.prompt)
            base_ok = str(base_ans) == str(p.answer)
            print(f'  {p.id[:12]} expected={str(p.answer)!r:>10} '
                  f'baseline={str(base_ans)!r:>10} base_ok={base_ok} '
                  f'elapsed={el:.2f}s')


if __name__ == '__main__':
    main()
