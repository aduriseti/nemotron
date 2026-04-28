"""
For each puzzle where v4 exhausted the search space (no solution found quickly),
use the baseline solver (all 11 ops) to find the golden cipher and report what ops
the training examples actually use — revealing why v4 can't solve these puzzles.

Output: exhausted_puzzle_analysis.md
"""
from __future__ import annotations
import sys
import json
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, '/workspaces/nemotron')

from tqdm import tqdm
from reasoners.store_types import Problem
import reasoners.cryptarithm_solver.python_solver as _ps
from reasoners.cryptarithm_solver.python_solver import (
    extract_all_examples, _search, _plausible_ops, FORMATTERS,
)
from reasoners.cryptarithm_solver.python_solver_arith_abs import solve_v4

SUPPORTED_OPS_V4 = frozenset({'add', 'sub', 'mul'})
SUPPORTED_OPS_FULL = ('add', 'sub', 'mul', 'cat', 'sub_abs', 'sub_neg_abs')
INDEX_PATH = '/workspaces/nemotron/reasoners/cryptarithm_solver/op_index.json'
OUT_PATH = '/workspaces/nemotron/reasoners/cryptarithm_solver/exhausted_puzzle_analysis.md'
TIMEOUT_THRESHOLD = 1.9
BASELINE_DEADLINE = 5.0


def find_golden_cipher(prompt: str):
    """
    Run baseline search (all ops) across all pipelines.
    Returns (pipeline, op_assign, parsed_examples) on first hit, or None.
    """
    extraction = extract_all_examples(prompt)
    if extraction[0] is None:
        return None
    parsed_examples, tA, tB, tgt_op_str = extraction

    for f_type in FORMATTERS:
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

        solutions: list = []
        _search(parsed_examples, 0, {}, set(), {}, plausible_per_ex,
                f_type, solutions, time.time() + BASELINE_DEADLINE, max_solutions=1)

        if solutions:
            digit_map, op_assign = solutions[0]
            return f_type, op_assign, parsed_examples

    return None


def main():
    with open(INDEX_PATH) as f:
        op_index = json.load(f)

    all_problems = [p for p in Problem.load_all() if 'cryptarithm' in p.category]
    problems = [p for p in all_problems
                if op_index.get(p.id, {}).get('target_op') in SUPPORTED_OPS_FULL]

    # Identify exhausted v4 failures
    print('Running v4 to find exhausted failures...')
    exhausted = []
    for p in tqdm(problems, unit='prob'):
        t0 = time.time()
        ans = solve_v4(p.prompt)
        elapsed = time.time() - t0
        correct = str(ans) == str(p.answer)
        if not correct and ans is None and elapsed < TIMEOUT_THRESHOLD:
            exhausted.append(p)

    print(f'Found {len(exhausted)} exhausted failures')

    # For each exhausted puzzle, use baseline to find the golden cipher
    print('Finding golden ciphers via baseline solver...')
    rows = []
    for p in tqdm(exhausted, unit='prob'):
        target_op = op_index[p.id]['target_op']
        result = find_golden_cipher(p.prompt)

        if result is None:
            rows.append({
                'id': p.id, 'target_op': target_op,
                'pipeline': None, 'example_ops': [], 'unsupported': [],
                'baseline_solved': False,
            })
            continue

        f_type, op_assign, parsed_examples = result
        example_ops = [op_assign.get(ex['op'], '?') for ex in parsed_examples]
        unsupported = [op for op in example_ops if op not in SUPPORTED_OPS_V4 and op != '?']

        rows.append({
            'id': p.id, 'target_op': target_op,
            'pipeline': f_type, 'example_ops': example_ops,
            'unsupported': unsupported, 'baseline_solved': True,
        })

    # Build markdown report
    baseline_solved = sum(1 for r in rows if r['baseline_solved'])
    has_unsupported = sum(1 for r in rows if r['unsupported'])
    clean = sum(1 for r in rows if r['baseline_solved'] and not r['unsupported'])
    baseline_failed = sum(1 for r in rows if not r['baseline_solved'])

    lines = [
        '# Exhausted Puzzle Analysis',
        '',
        f'Puzzles where v4 search exhausted (answer=None, elapsed < {TIMEOUT_THRESHOLD}s).',
        '',
        f'Date: {time.strftime("%Y-%m-%d")}',
        '',
        '## Summary',
        '',
        f'| Metric | Count |',
        f'|--------|-------|',
        f'| Total exhausted | {len(rows)} |',
        f'| Baseline found golden cipher | {baseline_solved} |',
        f'| Have examples with unsupported ops | {has_unsupported} |',
        f'| Baseline solved, all examples use supported ops | {clean} |',
        f'| Baseline also failed | {baseline_failed} |',
        '',
    ]

    # Per target-op breakdown
    lines += [
        '## Per Target-Op Breakdown',
        '',
        '| Target op | Exhausted | Baseline solved | Has unsupported | Unsupported ops seen |',
        '|-----------|-----------|----------------|----------------|---------------------|',
    ]
    for op_name in SUPPORTED_OPS_FULL:
        op_rows = [r for r in rows if r['target_op'] == op_name]
        if not op_rows:
            continue
        bs = sum(1 for r in op_rows if r['baseline_solved'])
        hu = sum(1 for r in op_rows if r['unsupported'])
        all_unsup = sorted({op for r in op_rows for op in r['unsupported']})
        lines.append(f'| {op_name} | {len(op_rows)} | {bs} | {hu} | {", ".join(all_unsup) or "—"} |')
    lines += ['']

    # Unsupported op frequency
    unsup_counter: Counter = Counter()
    for r in rows:
        for op in r['unsupported']:
            unsup_counter[op] += 1

    if unsup_counter:
        lines += [
            '## Unsupported Op Frequency',
            '',
            '(Ops used by training examples in exhausted puzzles that are outside SUPPORTED_OPS={add,sub,mul})',
            '',
            '| Op | Puzzle count |',
            '|----|-------------|',
        ]
        for op, count in unsup_counter.most_common():
            lines.append(f'| {op} | {count} |')
        lines += ['']

    # Per-puzzle detail
    lines += [
        '## Per-Puzzle Detail',
        '',
        '| Problem ID | Target op | Pipeline | Training example ops | Unsupported |',
        '|------------|-----------|----------|---------------------|------------|',
    ]
    for r in rows:
        ex_ops_str = ', '.join(r['example_ops']) if r['example_ops'] else '?'
        unsup_str = ', '.join(r['unsupported']) if r['unsupported'] else '—'
        pipeline = r['pipeline'] or 'none'
        lines.append(
            f'| {r["id"][:12]} | {r["target_op"]} | {pipeline} | {ex_ops_str} | {unsup_str} |'
        )
    lines += ['']

    report = '\n'.join(lines) + '\n'
    Path(OUT_PATH).write_text(report)
    print(f'\nReport written to {OUT_PATH}')
    print(f'\nSummary: {len(rows)} exhausted, {has_unsupported} have unsupported ops, '
          f'{clean} baseline-solved with only supported ops, {baseline_failed} baseline also failed')


if __name__ == '__main__':
    main()
