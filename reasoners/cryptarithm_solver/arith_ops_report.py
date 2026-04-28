"""
Generate ops-per-puzzle distribution report for baseline / prefilter / arith.
Writes markdown to arith_ops_distribution.md.
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
from reasoners.cryptarithm_solver.python_solver_arith import solve_v3

SUPPORTED_OPS = ('add', 'sub', 'mul', 'cat')
INDEX_PATH = '/workspaces/nemotron/reasoners/cryptarithm_solver/op_index.json'
OUT_PATH = '/workspaces/nemotron/reasoners/cryptarithm_solver/arith_ops_distribution.md'


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
        try:
            t0 = time.time()
            ans = solve_fn(p.prompt)
            records[-1]['elapsed'] = time.time() - t0
            records[-1]['correct'] = str(ans) == str(p.answer)
        finally:
            _ps._derive_output = orig
            _ps2._derive_output = orig
            _ps3._derive_output = orig

    return records


def pct(vals, p):
    if not vals:
        return 0
    s = sorted(vals)
    return s[min(int(len(s) * p / 100), len(s) - 1)]


def histogram(vals, buckets):
    """Returns list of (label, count, pct) for log-scale buckets."""
    rows = []
    for lo, hi in buckets:
        count = sum(1 for v in vals if lo <= v < hi)
        rows.append((f'{lo:,}–{hi-1:,}', count, 100 * count / len(vals) if vals else 0))
    # overflow
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
    for p in problems:
        pass  # attach op
    n = len(problems)

    VARIANTS = [
        ('baseline', lambda pr: _ps.solve_cipher_unified(pr, mode='greedy')),
        ('v2',       lambda pr: _ps2.solve_cipher_unified(pr, mode='greedy')),
        ('v3',       solve_v3),
    ]

    all_records = {}
    for label, fn in VARIANTS:
        recs = run_variant(problems, label, fn)
        for r, p in zip(recs, problems):
            r['target_op'] = op_index[p.id]['target_op']
        all_records[label] = recs

    # Build markdown
    lines = ['# Ops-per-Puzzle Distribution Report', '',
             f'Problems: {n} (add/sub/mul/cat targets only)', '',
             f'Date: {time.strftime("%Y-%m-%d")}', '']

    # Summary table
    lines += ['## Summary', '',
              '| Variant | Correct | Total ops | Reduction | Median ops | P95 ops | Time |',
              '|---------|---------|-----------|-----------|------------|---------|------|']
    base_total = sum(r['ops'] for r in all_records['baseline'])
    base_correct = sum(1 for r in all_records['baseline'] if r['correct'])
    for label, _ in VARIANTS:
        recs = all_records[label]
        correct = sum(1 for r in recs if r['correct'])
        ops = [r['ops'] for r in recs]
        total = sum(ops)
        elapsed = sum(r['elapsed'] for r in recs)
        red = base_total / total if total else 0
        delta = correct - base_correct
        delta_str = f' ({delta:+d})' if label != 'baseline' else ''
        lines.append(f'| {label} | {correct}/{n}{delta_str} | {total:,} | {red:.2f}x '
                     f'| {pct(ops,50):,} | {pct(ops,95):,} | {elapsed:.1f}s |')

    lines += ['']

    # Per-variant distribution
    lines += ['## Per-Variant Distribution', '']
    for label, _ in VARIANTS:
        ops = [r['ops'] for r in all_records[label]]
        lines += [f'### {label}', '', dist_table(ops), '']

        # Histogram
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

    # Speedup scatter: per-puzzle ops reduction (v3 vs baseline)
    lines += ['## Per-Puzzle Speedup (v3 vs baseline)', '',
              '| Speedup bucket | Count | % |',
              '|----------------|-------|---|']
    speedups = []
    for r1, r3 in zip(all_records['baseline'], all_records['v3']):
        if r1['ops'] > 0:
            speedups.append(r1['ops'] / max(r3['ops'], 1))
    speedup_buckets = [(0,1), (1,2), (2,5), (5,10), (10,50), (50,200), (200,10_000)]
    for lo, hi in speedup_buckets:
        count = sum(1 for s in speedups if lo <= s < hi)
        pct_val = 100 * count / len(speedups) if speedups else 0
        bar = '█' * max(1, int(pct_val / 2)) if count > 0 else ''
        lines.append(f'| {lo}x–{hi}x | {count} | {pct_val:.1f}% {bar} |')
    lines += ['']

    # Regressions
    regressions = [(r1, r3) for r1, r3 in zip(all_records['baseline'], all_records['v3'])
                   if r1['correct'] and not r3['correct']]
    lines += [f'## Regressions (baseline correct, v3 wrong)', '',
              f'Total: {len(regressions)} of {base_correct} baseline-correct problems', '']
    if regressions:
        lines += ['| Problem ID | Target op | Baseline ops | v3 ops |',
                  '|------------|-----------|-------------|--------|']
        for r1, r3 in regressions[:30]:
            lines.append(f'| {r1["id"][:12]} | {r3["target_op"]} | {r1["ops"]:,} | {r3["ops"]:,} |')
        if len(regressions) > 30:
            lines.append(f'| ... | | | |')

    report = '\n'.join(lines) + '\n'
    with open(OUT_PATH, 'w') as f:
        f.write(report)
    print(f'\nReport written to {OUT_PATH}')


if __name__ == '__main__':
    main()
