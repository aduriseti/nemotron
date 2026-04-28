"""
Generate ops-per-puzzle distribution report for v3 / v5 / v6.
Writes markdown to v6_ops_distribution.md.

v6 adds sub_abs and sub_neg_abs support on top of v5
(add/sub/mul/cat/add1/addm1/mul1/mulm1).
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
import reasoners.cryptarithm_solver.python_solver_arith_pm1 as _ps5
import reasoners.cryptarithm_solver.python_solver_arith_pm1_abs as _ps6
from reasoners.cryptarithm_solver.python_solver_arith import solve_v3
from reasoners.cryptarithm_solver.python_solver_arith_pm1 import solve_v5
from reasoners.cryptarithm_solver.python_solver_arith_pm1_abs import solve_v6

SUPPORTED_OPS = ('add', 'sub', 'mul', 'cat',
                 'add1', 'addm1', 'mul1', 'mulm1',
                 'sub_abs', 'sub_neg_abs')
NEW_OPS = ('sub_abs', 'sub_neg_abs')
INDEX_PATH = '/workspaces/nemotron/reasoners/cryptarithm_solver/op_index.json'
OUT_PATH = '/workspaces/nemotron/reasoners/cryptarithm_solver/v6_ops_distribution.md'


def run_variant(problems, label, solve_fn):
    records = []
    orig = _ps._derive_output

    def _counted(*args, **kwargs):
        records[-1]['ops'] += 1
        return orig(*args, **kwargs)

    for p in tqdm(problems, desc=label, unit='prob'):
        records.append({'id': p.id, 'ops': 0, 'correct': False, 'elapsed': 0.0,
                        'target_op': None, 'answer': None})
        _ps._derive_output = _counted
        _ps2._derive_output = _counted
        _ps3._derive_output = _counted
        _ps5._derive_output = _counted
        _ps6._derive_output = _counted
        try:
            t0 = time.time()
            ans = solve_fn(p.prompt)
            records[-1]['elapsed'] = time.time() - t0
            records[-1]['answer'] = str(ans) if ans is not None else None
            records[-1]['correct'] = str(ans) == str(p.answer)
        finally:
            _ps._derive_output = orig
            _ps2._derive_output = orig
            _ps3._derive_output = orig
            _ps5._derive_output = orig
            _ps6._derive_output = orig

    return records


def pct(vals, p):
    if not vals:
        return 0
    s = sorted(vals)
    return s[min(int(len(s) * p / 100), len(s) - 1)]


def histogram(vals, buckets):
    rows = []
    for lo, hi in buckets:
        count = sum(1 for v in vals if lo <= v < hi)
        rows.append((f'{lo:,}–{hi-1:,}', count, 100 * count / len(vals) if vals else 0))
    hi_last = buckets[-1][1]
    count = sum(1 for v in vals if v >= hi_last)
    rows.append((f'≥{hi_last:,}', count, 100 * count / len(vals) if vals else 0))
    return rows


def dist_table(vals):
    if not vals:
        return '(no data)'
    return '\n'.join([
        '| Stat | Value |',
        '|------|-------|',
        f'| min  | {min(vals):,} |',
        f'| p10  | {pct(vals,10):,} |',
        f'| p25  | {pct(vals,25):,} |',
        f'| p50  | {pct(vals,50):,} |',
        f'| p75  | {pct(vals,75):,} |',
        f'| p90  | {pct(vals,90):,} |',
        f'| p95  | {pct(vals,95):,} |',
        f'| p99  | {pct(vals,99):,} |',
        f'| max  | {max(vals):,} |',
        f'| mean | {int(sum(vals)/len(vals)):,} |',
    ])


BUCKETS = [(0,1), (1,10), (10,100), (100,1_000), (1_000,10_000),
           (10_000,100_000), (100_000,1_000_000)]


def main():
    with open(INDEX_PATH) as f:
        op_index = json.load(f)

    all_problems = [p for p in Problem.load_all() if 'cryptarithm' in p.category]
    problems = [p for p in all_problems
                if op_index.get(p.id, {}).get('target_op') in SUPPORTED_OPS]
    n = len(problems)

    VARIANTS = [
        ('v3', solve_v3),
        ('v5', solve_v5),
        ('v6', solve_v6),
    ]

    all_records = {}
    for label, fn in VARIANTS:
        recs = run_variant(problems, label, fn)
        for r, p in zip(recs, problems):
            r['target_op'] = op_index[p.id]['target_op']
        all_records[label] = recs

    lines = [
        '# Ops-per-Puzzle Distribution Report (v6)', '',
        f'Problems: {n} (add/sub/mul/cat/add1/addm1/mul1/mulm1/sub_abs/sub_neg_abs targets)', '',
        f'Date: {time.strftime("%Y-%m-%d")}', '',
    ]

    lines += [
        '## Summary', '',
        '| Variant | Correct | Total ops | Reduction vs v3 | Median ops | P95 ops | Time |',
        '|---------|---------|-----------|-----------------|------------|---------|------|',
    ]
    v3_total = sum(r['ops'] for r in all_records['v3'])
    v3_correct = sum(1 for r in all_records['v3'] if r['correct'])
    for label, _ in VARIANTS:
        recs = all_records[label]
        correct = sum(1 for r in recs if r['correct'])
        ops = [r['ops'] for r in recs]
        total = sum(ops)
        elapsed = sum(r['elapsed'] for r in recs)
        red = v3_total / total if total else 0
        delta = correct - v3_correct
        delta_str = f' ({delta:+d})' if label != 'v3' else ''
        lines.append(
            f'| {label} | {correct}/{n}{delta_str} | {total:,} | {red:.2f}x '
            f'| {pct(ops,50):,} | {pct(ops,95):,} | {elapsed:.1f}s |'
        )

    lines += ['']

    lines += ['## Per-Variant Distribution', '']
    for label, _ in VARIANTS:
        all_ops = [r['ops'] for r in all_records[label]]
        correct_ops = [r['ops'] for r in all_records[label] if r['correct']]
        for subset_label, ops in (('all problems', all_ops),
                                  ('correct only', correct_ops)):
            lines += [f'### {label} — {subset_label} (n={len(ops)})', '',
                      dist_table(ops), '']
            lines += ['**Histogram:**', '',
                      '| Ops range | Count | % |',
                      '|-----------|-------|---|']
            for (row_label, count, pct_val) in histogram(ops, BUCKETS):
                bar = '█' * max(1, int(pct_val / 2)) if count > 0 else ''
                lines.append(f'| {row_label} | {count} | {pct_val:.1f}% {bar} |')
            lines += ['']

    lines += ['## Per-Op Breakdown', '']
    for op_name in SUPPORTED_OPS:
        n_op = sum(1 for r in all_records['v3'] if r['target_op'] == op_name)
        if n_op == 0:
            continue
        lines += [f'### {op_name}', '',
                  'Ops distribution: all problems / correct only',
                  '',
                  '| Variant | Correct | Median (all) | P90 (all) | Total (all) | Median (✓) | P90 (✓) | Total (✓) |',
                  '|---------|---------|--------------|-----------|-------------|------------|---------|-----------|']
        for label, _ in VARIANTS:
            recs = [r for r in all_records[label] if r['target_op'] == op_name]
            ops_all = [r['ops'] for r in recs]
            ops_ok = [r['ops'] for r in recs if r['correct']]
            correct = len(ops_ok)
            lines.append(
                f'| {label} | {correct}/{len(recs)} | '
                f'{pct(ops_all,50):,} | {pct(ops_all,90):,} | {sum(ops_all):,} | '
                f'{pct(ops_ok,50):,} | {pct(ops_ok,90):,} | {sum(ops_ok):,} |'
            )
        lines += ['']

    lines += ['## Per-Puzzle Speedup (v6 vs v5)', '',
              '| Speedup bucket | Count | % |',
              '|----------------|-------|---|']
    speedups = []
    for r5, r6 in zip(all_records['v5'], all_records['v6']):
        if r5['ops'] > 0:
            speedups.append(r5['ops'] / max(r6['ops'], 1))
    speedup_buckets = [(0,1), (1,2), (2,5), (5,10), (10,50), (50,200), (200,10_000)]
    for lo, hi in speedup_buckets:
        count = sum(1 for s in speedups if lo <= s < hi)
        pct_val = 100 * count / len(speedups) if speedups else 0
        bar = '█' * max(1, int(pct_val / 2)) if count > 0 else ''
        lines.append(f'| {lo}x–{hi}x | {count} | {pct_val:.1f}% {bar} |')
    lines += ['']

    lines += ['## v5 → v6 Gains on New Ops', '',
              '| Op | v5 correct | v6 correct | Δ correct | v5 total ops | v6 total ops | Reduction |',
              '|----|-----------|-----------|----------|-------------|-------------|-----------|']
    for op_name in NEW_OPS:
        r5s = [r for r in all_records['v5'] if r['target_op'] == op_name]
        r6s = [r for r in all_records['v6'] if r['target_op'] == op_name]
        if not r5s:
            continue
        c5 = sum(1 for r in r5s if r['correct'])
        c6 = sum(1 for r in r6s if r['correct'])
        t5 = sum(r['ops'] for r in r5s)
        t6 = sum(r['ops'] for r in r6s)
        red = t5 / t6 if t6 else 0
        lines.append(
            f'| {op_name} | {c5}/{len(r5s)} | {c6}/{len(r6s)} | {c6-c5:+d} '
            f'| {t5:,} | {t6:,} | {red:.2f}x |'
        )
    lines += ['']

    regressions_v5_v6 = [(r5, r6) for r5, r6 in zip(all_records['v5'], all_records['v6'])
                         if r5['correct'] and not r6['correct']]
    v5_correct = sum(1 for r in all_records['v5'] if r['correct'])
    lines += [f'## Regressions (v5 correct, v6 wrong)', '',
              f'Total: {len(regressions_v5_v6)} of {v5_correct} v5-correct problems', '']
    if regressions_v5_v6:
        lines += ['| Problem ID | Target op | v5 ops | v6 ops |',
                  '|------------|-----------|--------|--------|']
        for r5, r6 in regressions_v5_v6[:30]:
            lines.append(f'| {r5["id"][:12]} | {r6["target_op"]} | {r5["ops"]:,} | {r6["ops"]:,} |')
        if len(regressions_v5_v6) > 30:
            lines.append(f'| ... | | | |')

    TIMEOUT_THRESHOLD = 1.9
    v6_recs_by_id = {r['id']: r for r in all_records['v6']}

    lines += ['', '## v6 Failure Classification', '',
              'Classifies each incorrect v6 result as one of:',
              '- **timeout**: search hit the 2s deadline, returned no answer',
              '- **exhausted**: search completed quickly, found no valid cipher (pruning too aggressive)',
              '- **wrong_search**: search found a cipher but it produced the wrong answer', '']
    lines += ['| Op | correct | timeout | exhausted | wrong_search | total |',
              '|----|---------|---------|-----------|-------------|-------|']
    for op_name in SUPPORTED_OPS:
        op_probs = [p for p in problems if op_index[p.id]['target_op'] == op_name]
        if not op_probs:
            continue
        correct = sum(1 for p in op_probs if v6_recs_by_id[p.id]['correct'])
        timeout = sum(1 for p in op_probs
                      if not v6_recs_by_id[p.id]['correct']
                      and v6_recs_by_id[p.id]['answer'] is None
                      and v6_recs_by_id[p.id]['elapsed'] >= TIMEOUT_THRESHOLD)
        exhausted = sum(1 for p in op_probs
                        if not v6_recs_by_id[p.id]['correct']
                        and v6_recs_by_id[p.id]['answer'] is None
                        and v6_recs_by_id[p.id]['elapsed'] < TIMEOUT_THRESHOLD)
        wrong_s = sum(1 for p in op_probs
                      if not v6_recs_by_id[p.id]['correct']
                      and v6_recs_by_id[p.id]['answer'] is not None)
        lines.append(f'| {op_name} | {correct} | {timeout} | {exhausted} | {wrong_s} | {len(op_probs)} |')
    lines += ['']

    report = '\n'.join(lines) + '\n'
    with open(OUT_PATH, 'w') as f:
        f.write(report)
    print(f'\nReport written to {OUT_PATH}')

    print(f'\n{"Variant":<10}  {"Correct":>8}  {"Total ops":>14}  {"vs v3":>10}  '
          f'{"P50":>8}  {"P95":>8}  {"Time":>6}')
    print('-' * 75)
    for label, _ in VARIANTS:
        recs = all_records[label]
        correct = sum(1 for r in recs if r['correct'])
        ops = [r['ops'] for r in recs]
        total = sum(ops)
        elapsed = sum(r['elapsed'] for r in recs)
        red = v3_total / total if total else 0
        delta = correct - v3_correct
        delta_str = f'({delta:+d})' if label != 'v3' else '     '
        print(f'{label:<10}  {correct:>4}/{n:<3} {delta_str}  {total:>14,}  {red:>9.2f}x'
              f'  {pct(ops,50):>8,}  {pct(ops,95):>8,}  {elapsed:>5.1f}s')


if __name__ == '__main__':
    main()
