"""
Ablation benchmark: v1 baseline vs v2 optimizations.

Four variants:
  baseline    — no optimizations
  prefilter   — op pre-intersection only
  reorder     — example reordering only
  both        — op pre-intersection + example reordering
"""
import sys, random, time
sys.path.insert(0, '/workspaces/nemotron')

from tqdm import tqdm
from reasoners.store_types import Problem
import reasoners.cryptarithm_solver.python_solver as _ps
from reasoners.cryptarithm_solver.python_solver_prefilter import (
    _precompute_op_constraints, _reorder_examples,
)
from reasoners.cryptarithm_solver.python_solver import (
    MATH_OPS, FORMATTERS,
    extract_all_examples, _plausible_ops, _search,
    _syms_for_pipeline, _encode_answer, _cat_fast_path,
    _permutations,
)


def _solve(prompt, use_prefilter=False, use_reorder=False):
    extraction = extract_all_examples(prompt)
    if extraction[0] is None:
        return None

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

    op_constraints = _precompute_op_constraints(parsed_examples) if use_prefilter else None
    if op_constraints and any(len(v) == 0 for v in op_constraints.values()):
        return None

    first_answer = None

    for f_type in FORMATTERS:
        cat_ans = _cat_fast_path(
            parsed_examples, tA, tB, tgt_op_str, f_type,
            active_digits, digit_sym_list, ops_used,
        )
        if cat_ans is not None:
            first_answer = cat_ans
            break

        examples = _reorder_examples(parsed_examples, f_type) if use_reorder else parsed_examples

        if op_constraints:
            plausible_per_ex = [op_constraints[ex['op']] for ex in examples]
        else:
            plausible_per_ex = [_plausible_ops(ex) for ex in examples]

        if any(not ops for ops in plausible_per_ex):
            continue

        deadline = time.time() + 2.0
        solutions = []
        _search(examples, 0, {}, set(), {}, plausible_per_ex,
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

    return first_answer


VARIANTS = [
    ('baseline',   dict(use_prefilter=False, use_reorder=False)),
    ('prefilter',  dict(use_prefilter=True,  use_reorder=False)),
    ('reorder',    dict(use_prefilter=False, use_reorder=True)),
    ('both',       dict(use_prefilter=True,  use_reorder=True)),
]


def run_variant(problems, label, kwargs):
    records = []
    for p in tqdm(problems, desc=label, unit='prob'):
        ops_counter = [0]
        orig = _ps._derive_output

        def _counted(*args, **kwargs_inner):
            ops_counter[0] += 1
            return orig(*args, **kwargs_inner)

        _ps._derive_output = _counted
        try:
            t0 = time.time()
            ans = _solve(p.prompt, **kwargs)
            elapsed = time.time() - t0
        finally:
            _ps._derive_output = orig

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


def main():
    problems = [p for p in Problem.load_all() if 'cryptarithm' in p.category]
    n = len(problems)
    print(f"Loaded {n} problems\n")

    all_records = {}
    for label, kwargs in VARIANTS:
        all_records[label] = run_variant(problems, label, kwargs)

    budgets = [1, 5, 10, 25, 50, 100, 250, 500, 1_000, 5_000, 10_000, 50_000, 100_000]

    lines = []
    lines.append("# Solver Ablation Report: v1 vs v2 Optimizations\n")
    lines.append("Four variants run on the same 100 shuffled cryptarithm problems.\n")
    lines.append("Operations = `_derive_output` calls (unit of work in backtracking search).\n")

    # Summary table
    lines.append("## Summary\n")
    header = f"| {'Variant':<12} | {'Accuracy':>10} | {'Mean ops':>10} | {'Median ops':>10} | {'p90 ops':>10} | {'Total ops':>12} | {'Time (s)':>8} |"
    lines.append(header)
    lines.append(f"|{'-'*14}:|{'-'*12}:|{'-'*12}:|{'-'*12}:|{'-'*12}:|{'-'*14}:|{'-'*10}:|")
    baseline_total = sum(r['ops'] for r in all_records['baseline'])
    for label, _ in VARIANTS:
        recs = all_records[label]
        correct = sum(1 for r in recs if r['correct'])
        ops = [r['ops'] for r in recs]
        total = sum(ops)
        ratio = baseline_total / total if total > 0 else 0
        elapsed = sum(r['elapsed'] for r in recs)
        lines.append(
            f"| {label:<12} | {correct:>4}/{n} ({correct/n:>5.1%}) "
            f"| {sum(ops)/n:>10,.0f} | {_pct(ops,50):>10,} "
            f"| {_pct(ops,90):>10,} | {total:>12,} | {elapsed:>8.1f} |"
        )

    # Budget vs accuracy table
    lines.append("\n## Budget vs Accuracy\n")
    variant_labels = [label for label, _ in VARIANTS]
    col_w = 14
    header = f"| {'Budget':>10} |" + "".join(f" {l:>{col_w}} |" for l in variant_labels)
    sep = f"|{'-'*12}:|" + "".join(f"{'-'*(col_w+2)}:|" for _ in variant_labels)
    lines.append(header)
    lines.append(sep)
    for b in budgets:
        row = f"| {b:>10,} |"
        for label, _ in VARIANTS:
            recs = all_records[label]
            c = sum(1 for r in recs if r['correct'] and r['ops'] <= b)
            row += f" {c:>4}/{n} ({c/n:>5.1%}) |"
        lines.append(row)

    # Ops reduction vs baseline
    lines.append("\n## Ops Reduction vs Baseline\n")
    lines.append(f"| {'Variant':<12} | {'Total ops':>12} | {'Reduction':>10} | {'Accuracy Δ':>12} |")
    lines.append(f"|{'-'*14}:|{'-'*14}:|{'-'*12}:|{'-'*14}:|")
    base_correct = sum(1 for r in all_records['baseline'] if r['correct'])
    for label, _ in VARIANTS:
        recs = all_records[label]
        total = sum(r['ops'] for r in recs)
        reduction = baseline_total / total if total > 0 else 0
        correct = sum(1 for r in recs if r['correct'])
        delta = correct - base_correct
        delta_str = f"{delta:+d}" if label != 'baseline' else '—'
        lines.append(
            f"| {label:<12} | {total:>12,} | {reduction:>9.2f}x | {delta_str:>12} |"
        )

    # Per-problem breakdown (top movers)
    lines.append("\n## Top 10 Problems by Ops Saved (both vs baseline)\n")
    lines.append(f"| {'id':>10} | {'baseline':>10} | {'both':>10} | {'saved':>10} | base✓ | both✓ |")
    lines.append(f"|{'-'*12}:|{'-'*12}:|{'-'*12}:|{'-'*12}:|{'-'*7}:|{'-'*7}:|")
    pairs = list(zip(all_records['baseline'], all_records['both']))
    pairs.sort(key=lambda x: -(x[0]['ops'] - x[1]['ops']))
    for r1, r2 in pairs[:10]:
        saved = r1['ops'] - r2['ops']
        lines.append(
            f"| {r1['id'][:8]:>10} | {r1['ops']:>10,} | {r2['ops']:>10,} "
            f"| {saved:>10,} | {'✓' if r1['correct'] else '✗':>5} | {'✓' if r2['correct'] else '✗':>5} |"
        )

    # Regressions: problems correct in baseline but wrong in 'both'
    regressions = [
        (r1, r2) for r1, r2 in zip(all_records['baseline'], all_records['both'])
        if r1['correct'] and not r2['correct']
    ]
    if regressions:
        lines.append(f"\n## Accuracy Regressions (baseline ✓, both ✗)\n")
        lines.append(f"| {'id':>10} | {'baseline ops':>12} | {'both ops':>10} |")
        lines.append(f"|{'-'*12}:|{'-'*14}:|{'-'*12}:|")
        for r1, r2 in regressions:
            lines.append(f"| {r1['id'][:8]:>10} | {r1['ops']:>12,} | {r2['ops']:>10,} |")

    report = '\n'.join(lines) + '\n'
    path = '/workspaces/nemotron/reasoners/cryptarithm_solver/v2_ablation_report.md'
    with open(path, 'w') as f:
        f.write(report)
    print(f"\nReport → {path}")

    # Console summary
    print(f"\n{'Variant':<12}  {'Correct':>8}  {'Total ops':>14}  {'Reduction':>10}  {'Time':>6}")
    print('-' * 60)
    for label, _ in VARIANTS:
        recs = all_records[label]
        correct = sum(1 for r in recs if r['correct'])
        total = sum(r['ops'] for r in recs)
        elapsed = sum(r['elapsed'] for r in recs)
        reduction = baseline_total / total if total > 0 else 0
        print(f"{label:<12}  {correct:>4}/{n:<3}  {total:>14,}  {reduction:>9.2f}x  {elapsed:>5.1f}s")


if __name__ == '__main__':
    main()
