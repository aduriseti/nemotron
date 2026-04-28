"""
Generate ops-per-puzzle distribution report for baseline / v2 / v3 / v4.
Writes markdown to v4_ops_distribution.md.

v4 adds sub_abs and sub_neg_abs support on top of v3 (add/sub/mul/cat).
"""
from __future__ import annotations
import sys
import json
import time
import math

sys.path.insert(0, '/workspaces/nemotron')

from tqdm import tqdm
from reasoners.store_types import Problem
import reasoners.cryptarithm_solver.python_solver as _ps
import reasoners.cryptarithm_solver.python_solver_prefilter as _ps2
import reasoners.cryptarithm_solver.python_solver_arith as _ps3
import reasoners.cryptarithm_solver.python_solver_arith_abs as _ps4
from reasoners.cryptarithm_solver.python_solver_arith import solve_v3
from reasoners.cryptarithm_solver.python_solver_arith_abs import solve_v4

SUPPORTED_OPS = ('add', 'sub', 'mul', 'cat', 'sub_abs', 'sub_neg_abs')
INDEX_PATH = '/workspaces/nemotron/reasoners/cryptarithm_solver/op_index.json'
OUT_PATH = '/workspaces/nemotron/reasoners/cryptarithm_solver/v4_ops_distribution.md'


def run_variant(problems, label, solve_fn):
    records = []
    orig = _ps._derive_output

    def _counted(*args, **kwargs):
        records[-1]['ops'] += 1
        return orig(*args, **kwargs)

    for p in tqdm(problems, desc=label, unit='prob'):
        records.append({'id': p.id, 'ops': 0, 'correct': False, 'elapsed': 0.0, 'target_op': None})
        _ps._derive_output = _counted
        _ps2._derive_output = _counted
        _ps3._derive_output = _counted
        _ps4._derive_output = _counted
        try:
            t0 = time.time()
            ans = solve_fn(p.prompt)
            records[-1]['elapsed'] = time.time() - t0
            records[-1]['correct'] = str(ans) == str(p.answer)
        finally:
            _ps._derive_output = orig
            _ps2._derive_output = orig
            _ps3._derive_output = orig
            _ps4._derive_output = orig

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
    lines = [
        f'| Stat | Value |',
        f'|------|-------|',
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
    ]
    return '\n'.join(lines)


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
        ('v4', solve_v4),
    ]

    all_records = {}
    for label, fn in VARIANTS:
        recs = run_variant(problems, label, fn)
        for r, p in zip(recs, problems):
            r['target_op'] = op_index[p.id]['target_op']
        all_records[label] = recs

    lines = ['# Ops-per-Puzzle Distribution Report (v4)', '',
             f'Problems: {n} (add/sub/mul/cat/sub_abs/sub_neg_abs targets)', '',
             f'Date: {time.strftime("%Y-%m-%d")}', '']

    # Summary table — reduction vs v3
    lines += ['## Summary', '',
              '| Variant | Correct | Total ops | Reduction vs v3 | Median ops | P95 ops | Time |',
              '|---------|---------|-----------|-----------------|------------|---------|------|']
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
        lines.append(f'| {label} | {correct}/{n}{delta_str} | {total:,} | {red:.2f}x '
                     f'| {pct(ops,50):,} | {pct(ops,95):,} | {elapsed:.1f}s |')

    lines += ['']

    # Per-variant distribution
    lines += ['## Per-Variant Distribution', '']
    for label, _ in VARIANTS:
        ops = [r['ops'] for r in all_records[label]]
        lines += [f'### {label}', '', dist_table(ops), '']
        lines += ['**Histogram:**', '',
                  '| Ops range | Count | % |',
                  '|-----------|-------|---|']
        for (row_label, count, pct_val) in histogram(ops, BUCKETS):
            bar = '█' * max(1, int(pct_val / 2)) if count > 0 else ''
            lines.append(f'| {row_label} | {count} | {pct_val:.1f}% {bar} |')
        lines += ['']

    # Per-op breakdown
    lines += ['## Per-Op Breakdown', '']
    for op_name in SUPPORTED_OPS:
        lines += [f'### {op_name}', '',
                  '| Variant | Correct | Median ops | P90 ops | P99 ops | Total ops |',
                  '|---------|---------|------------|---------|---------|-----------|']
        for label, _ in VARIANTS:
            recs = [r for r in all_records[label] if r['target_op'] == op_name]
            if not recs:
                continue
            ops = [r['ops'] for r in recs]
            correct = sum(1 for r in recs if r['correct'])
            lines.append(f'| {label} | {correct}/{len(recs)} | {pct(ops,50):,} '
                         f'| {pct(ops,90):,} | {pct(ops,99):,} | {sum(ops):,} |')
        lines += ['']

    # Per-puzzle speedup: v4 vs v3
    lines += ['## Per-Puzzle Speedup (v4 vs v3)', '',
              '| Speedup bucket | Count | % |',
              '|----------------|-------|---|']
    speedups = []
    for r1, r4 in zip(all_records['v3'], all_records['v4']):
        if r1['ops'] > 0:
            speedups.append(r1['ops'] / max(r4['ops'], 1))
    speedup_buckets = [(0,1), (1,2), (2,5), (5,10), (10,50), (50,200), (200,10_000)]
    for lo, hi in speedup_buckets:
        count = sum(1 for s in speedups if lo <= s < hi)
        pct_val = 100 * count / len(speedups) if speedups else 0
        bar = '█' * max(1, int(pct_val / 2)) if count > 0 else ''
        lines.append(f'| {lo}x–{hi}x | {count} | {pct_val:.1f}% {bar} |')
    lines += ['']

    # v3 vs v4: new gains on sub_abs / sub_neg_abs
    lines += ['## v3 → v4 Gains on New Ops', '',
              '| Op | v3 correct | v4 correct | Δ correct | v3 total ops | v4 total ops | Reduction |',
              '|----|-----------|-----------|----------|-------------|-------------|-----------|']
    for op_name in ('sub_abs', 'sub_neg_abs'):
        r3s = [r for r in all_records['v3'] if r['target_op'] == op_name]
        r4s = [r for r in all_records['v4'] if r['target_op'] == op_name]
        if not r3s:
            continue
        c3 = sum(1 for r in r3s if r['correct'])
        c4 = sum(1 for r in r4s if r['correct'])
        t3 = sum(r['ops'] for r in r3s)
        t4 = sum(r['ops'] for r in r4s)
        red = t3 / t4 if t4 else 0
        lines.append(f'| {op_name} | {c3}/{len(r3s)} | {c4}/{len(r4s)} | {c4-c3:+d} '
                     f'| {t3:,} | {t4:,} | {red:.2f}x |')
    lines += ['']

    # Regressions: v3 correct, v4 wrong
    regressions = [(r3, r4) for r3, r4 in zip(all_records['v3'], all_records['v4'])
                   if r3['correct'] and not r4['correct']]
    lines += [f'## Regressions (v3 correct, v4 wrong)', '',
              f'Total: {len(regressions)} of {v3_correct} v3-correct problems', '']
    if regressions:
        lines += ['| Problem ID | Target op | v3 ops | v4 ops |',
                  '|------------|-----------|--------|--------|']
        for r3, r4 in regressions[:30]:
            lines.append(f'| {r3["id"][:12]} | {r4["target_op"]} | {r3["ops"]:,} | {r4["ops"]:,} |')
        if len(regressions) > 30:
            lines.append(f'| ... | | | |')

    report = '\n'.join(lines) + '\n'
    with open(OUT_PATH, 'w') as f:
        f.write(report)
    print(f'\nReport written to {OUT_PATH}')

    # Console summary
    print(f'\n{"Variant":<10}  {"Correct":>8}  {"Total ops":>14}  {"vs v3":>10}  {"P50":>8}  {"P95":>8}  {"Time":>6}')
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
