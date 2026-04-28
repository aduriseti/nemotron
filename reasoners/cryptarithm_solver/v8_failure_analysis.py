"""Classify v8's failures into:
  - timeout:    no answer + elapsed >= 1.9s (a pipeline hit its 2s deadline)
  - exhausted:  no answer + elapsed < 1.9s (search exited fast without a cipher)
  - wrong:      cipher found but target answer is wrong (cipher ambiguity)

Writes markdown report to v8_failure_analysis.md.
"""
from __future__ import annotations
import sys
import json
import time
from collections import Counter, defaultdict

sys.path.insert(0, '/workspaces/nemotron')

from tqdm import tqdm
from reasoners.store_types import Problem
from reasoners.cryptarithm_solver.python_solver_arith_full import solve_v8

INDEX_PATH = '/workspaces/nemotron/reasoners/cryptarithm_solver/op_index.json'
OUT_PATH = '/workspaces/nemotron/reasoners/cryptarithm_solver/v8_failure_analysis.md'
SUPPORTED_OPS = ('add', 'sub', 'mul', 'cat', 'add1', 'addm1', 'mul1',
                 'mulm1', 'sub_abs', 'sub_neg_abs', 'max_mod_min')
# A v8 puzzle runs up to 3 pipelines × 2s deadline each. If puzzle elapsed >=
# 1.9s, at least one pipeline timed out (otherwise the search would have
# returned faster). Below 1.9s = all pipelines exited via exhaustion (no cipher
# found quickly).
TIMEOUT_THRESHOLD = 1.9


def main():
    op_index = json.load(open(INDEX_PATH))
    problems = [p for p in Problem.load_all()
                if 'cryptarithm' in p.category
                and op_index.get(p.id, {}).get('target_op') in SUPPORTED_OPS]
    n = len(problems)
    print(f'Total problems: {n}')

    records = []
    for p in tqdm(problems, desc='v8', unit='prob'):
        t0 = time.time()
        ans = solve_v8(p.prompt)
        elapsed = time.time() - t0
        records.append({
            'id': p.id,
            'category': p.category,
            'target_op': op_index[p.id]['target_op'],
            'expected': str(p.answer),
            'got': str(ans) if ans is not None else None,
            'correct': str(ans) == str(p.answer),
            'elapsed': elapsed,
        })

    correct = [r for r in records if r['correct']]
    failures = [r for r in records if not r['correct']]

    n_correct = len(correct)
    n_no_ans = sum(1 for r in failures if r['got'] is None)
    n_wrong = sum(1 for r in failures if r['got'] is not None)
    n_timeout = sum(1 for r in failures if r['got'] is None and r['elapsed'] >= TIMEOUT_THRESHOLD)
    n_exhausted = n_no_ans - n_timeout

    print(f'\n=== v8 OVERALL ({n} puzzles) ===')
    print(f'  correct       : {n_correct:4d} ({100*n_correct/n:.1f}%)')
    print(f'  failures      : {len(failures):4d} ({100*len(failures)/n:.1f}%)')
    print(f'    no answer   : {n_no_ans:4d} ({100*n_no_ans/n:.1f}%)')
    print(f'      timeout   : {n_timeout:4d}')
    print(f'      exhausted : {n_exhausted:4d}')
    print(f'    wrong answer: {n_wrong:4d} ({100*n_wrong/n:.1f}%)  <-- cipher ambiguity')

    # Per-op breakdown
    print(f'\n=== PER-OP ({n} puzzles) ===')
    print(f'{"op":<14}  {"tot":>4}  {"✓":>3}  {"to":>3}  {"exh":>3}  {"wr":>3}  '
          f'{"%✓":>5}  {"%to":>5}  {"%exh":>5}  {"%wr":>5}')
    print('-' * 75)
    per_op = {}
    for op in SUPPORTED_OPS:
        op_recs = [r for r in records if r['target_op'] == op]
        if not op_recs: continue
        t = len(op_recs)
        c = sum(1 for r in op_recs if r['correct'])
        timeo = sum(1 for r in op_recs
                    if not r['correct'] and r['got'] is None
                    and r['elapsed'] >= TIMEOUT_THRESHOLD)
        exh = sum(1 for r in op_recs
                  if not r['correct'] and r['got'] is None
                  and r['elapsed'] < TIMEOUT_THRESHOLD)
        wrong = sum(1 for r in op_recs if not r['correct'] and r['got'] is not None)
        per_op[op] = {'total': t, 'correct': c, 'timeout': timeo,
                      'exhausted': exh, 'wrong': wrong}
        print(f'{op:<14}  {t:>4}  {c:>3}  {timeo:>3}  {exh:>3}  {wrong:>3}  '
              f'{100*c/t:>5.1f}  {100*timeo/t:>5.1f}  {100*exh/t:>5.1f}  {100*wrong/t:>5.1f}')

    # Split by category (deduce vs guess)
    print(f'\n=== BY CATEGORY ===')
    cat_stats = {}
    for cat in ('cryptarithm_deduce', 'cryptarithm_guess'):
        cat_recs = [r for r in records if r['category'] == cat]
        if not cat_recs:
            cat_stats[cat] = None
            continue
        t = len(cat_recs)
        c = sum(1 for r in cat_recs if r['correct'])
        none = sum(1 for r in cat_recs if not r['correct'] and r['got'] is None)
        wrong = sum(1 for r in cat_recs if not r['correct'] and r['got'] is not None)
        cat_stats[cat] = {'total': t, 'correct': c, 'none': none, 'wrong': wrong}
        print(f'{cat:<22} n={t}  ✓={c} ({100*c/t:.1f}%)  '
              f'none={none} ({100*none/t:.1f}%)  '
              f'wrong={wrong} ({100*wrong/t:.1f}%)')

    # Write markdown report
    lines = [
        '# v8 Failure Analysis', '',
        f'Date: {time.strftime("%Y-%m-%d")}', '',
        f'Solver: `solve_v8` (full 11-op support, 2s deadline per pipeline, greedy)',
        f'Test set: {n} cryptarithm puzzles with target_op in supported set', '',
        '## Outcome categories',
        '',
        '- **correct** — golden answer matches.',
        '- **timeout** — no answer; puzzle elapsed ≥ {TIMEOUT_THRESHOLD}s, so at least one pipeline hit its 2s deadline.'.format(TIMEOUT_THRESHOLD=TIMEOUT_THRESHOLD),
        '- **exhausted** — no answer; puzzle elapsed < {TIMEOUT_THRESHOLD}s, so all pipelines exited fast without finding a cipher (pruning rejected every candidate).'.format(TIMEOUT_THRESHOLD=TIMEOUT_THRESHOLD),
        '- **wrong** — cipher found, but its extrapolation to the target query differs from golden (cipher ambiguity).',
        '',
        '## Overall', '',
        '| Outcome | Count | % |',
        '|---------|------:|---:|',
        f'| Correct | {n_correct} | {100*n_correct/n:.1f}% |',
        f'| Wrong (cipher ambiguity) | {n_wrong} | {100*n_wrong/n:.1f}% |',
        f'| Timeout (≥{TIMEOUT_THRESHOLD}s, no answer) | {n_timeout} | {100*n_timeout/n:.1f}% |',
        f'| Exhausted (<{TIMEOUT_THRESHOLD}s, no answer) | {n_exhausted} | {100*n_exhausted/n:.1f}% |',
        '',
        f'Cipher ambiguity dominates: {n_wrong} wrong-cipher cases vs '
        f'{n_no_ans} no-answer cases (timeout + exhausted).',
        '',
        '## Per-op breakdown', '',
        '| Op | Total | ✓ | Timeout | Exhausted | Wrong | %✓ | %Timeout | %Exhausted | %Wrong |',
        '|----|------:|--:|--------:|----------:|------:|---:|---------:|-----------:|-------:|',
    ]
    for op in SUPPORTED_OPS:
        s = per_op.get(op)
        if s is None:
            continue
        t = s['total']
        lines.append(
            f'| {op} | {t} | {s["correct"]} | {s["timeout"]} | {s["exhausted"]} | {s["wrong"]} | '
            f'{100*s["correct"]/t:.1f}% | {100*s["timeout"]/t:.1f}% | {100*s["exhausted"]/t:.1f}% | {100*s["wrong"]/t:.1f}% |'
        )
    lines.append('')

    lines += ['## By category', '',
              '| Category | n | ✓ | None | Wrong |',
              '|----------|--:|--:|-----:|------:|']
    for cat, s in cat_stats.items():
        if s is None:
            continue
        lines.append(
            f'| {cat} | {s["total"]} | '
            f'{s["correct"]} ({100*s["correct"]/s["total"]:.1f}%) | '
            f'{s["none"]} ({100*s["none"]/s["total"]:.1f}%) | '
            f'{s["wrong"]} ({100*s["wrong"]/s["total"]:.1f}%) |'
        )
    lines.append('')

    lines += ['## Diagnosis', '',
              '### Cipher ambiguity (structural)',
              '',
              f'- {n_wrong}/{n} puzzles ({100*n_wrong/n:.1f}%) — wrong-but-internally-consistent answers.',
              '- The search found a valid cipher (digit_map + op_assign satisfying every example), just not the one used to generate the golden answer.',
              '- Multiple consistent ciphers extrapolate to different target answers when the target uses under-constrained digit symbols.',
              '- Mitigations: enumerate multiple ciphers and aggregate answers (majority vote); add tiebreaker heuristics for free-symbol assignments.',
              '',
              '### Timeouts (search ran out of budget)',
              '',
              f'- {n_timeout}/{n} puzzles ({100*n_timeout/n:.1f}%) — at least one pipeline hit its 2s deadline before finding a cipher.',
              '- Mitigations: longer deadline, better A0/B0/B1 ordering, tighter pruning.',
              '',
              '### Exhausted (no cipher under current pruning)',
              '',
              f'- {n_exhausted}/{n} puzzles ({100*n_exhausted/n:.1f}%) — search exited fast with no candidates.',
              '- Indicates over-pruning in column-derivation: a valid cipher exists (baseline finds it) but our constraints reject every candidate.',
              '- Mitigations: review per-op column logic for edge cases that prune valid ciphers.',
              '']

    with open(OUT_PATH, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'\nReport written to {OUT_PATH}')


if __name__ == '__main__':
    main()
