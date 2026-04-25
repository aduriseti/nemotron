"""
Analysis: operation count and accuracy with vs without the cat fast-path.

Operations = permutation attempts (cat path) + _derive_output calls (backtracking path).
"""
import sys, time, io
sys.path.insert(0, '/workspaces/nemotron')

from tqdm import tqdm
from reasoners.store_types import Problem
import reasoners.cryptarithm_solver.python_solver as _ps

TIMEOUT = 2.0


def solve_greedy_counted(prompt, use_cat_fast_path=True):
    """
    Returns (answer, ops_count, used_cat_path).
    ops_count = cat permutation attempts + _derive_output calls.
    """
    orig_stdout = sys.__stdout__
    sys.__stdout__ = io.StringIO()

    try:
        extraction = _ps.extract_all_examples(prompt)
        if extraction[0] is None:
            return None, 0, False

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

        ops_counter = [0]

        _orig_derive = _ps._derive_output
        def _counted_derive(*args, **kwargs):
            ops_counter[0] += 1
            return _orig_derive(*args, **kwargs)
        _ps._derive_output = _counted_derive

        try:
            for f_type in _ps.FORMATTERS:
                plausible_per_ex = []
                skip = False
                for ex in parsed_examples:
                    ops = _ps._plausible_ops(ex)
                    if not ops:
                        skip = True; break
                    plausible_per_ex.append(ops)
                if skip:
                    continue

                if use_cat_fast_path:
                    cat_ans = _ps._cat_fast_path(
                        parsed_examples, tA, tB, tgt_op_str, f_type,
                        active_digits, digit_sym_list, ops_used,
                        _ops_counter=ops_counter,
                    )
                    if cat_ans is not None:
                        return cat_ans, ops_counter[0], True

                solutions = []
                _ps._search(parsed_examples, 0, {}, set(), {}, plausible_per_ex,
                            f_type, solutions, time.time() + TIMEOUT, max_solutions=1)

                if not solutions:
                    continue

                tgt_ex = {'A': tA, 'B': tB, 'op': tgt_op_str, 'out': []}
                tA0s, tA1s, tB0s, tB1s = _ps._syms_for_pipeline(tgt_ex, f_type)
                tgt_op_seen = any(ex['op'] == tgt_op_str for ex in parsed_examples)

                digit_map, op_assign = solutions[0]
                candidate_ops = (
                    [op_assign[tgt_op_str]] if tgt_op_seen and tgt_op_str in op_assign
                    else list(_ps.MATH_OPS.keys())
                )

                target_syms_4 = (tA0s, tA1s, tB0s, tB1s)
                unique_missing = list(dict.fromkeys(s for s in target_syms_4 if s not in digit_map))
                if unique_missing:
                    active_used = {digit_map[s] for s in digit_map if s in active_digits}
                    avail = [v for v in range(10) if v not in active_used]
                    if len(avail) < len(unique_missing):
                        avail = list(range(10))
                    from itertools import permutations as _perms
                    maps_to_try = [
                        {**digit_map, **dict(zip(unique_missing, c))}
                        for c in _perms(avail, len(unique_missing))
                    ]
                else:
                    maps_to_try = [digit_map]

                for dm in maps_to_try:
                    ta0, ta1, tb0, tb1 = dm[tA0s], dm[tA1s], dm[tB0s], dm[tB1s]
                    L_tgt = ta0 * 10 + ta1
                    R_tgt = tb0 * 10 + tb1
                    for tgt_math_op in candidate_ops:
                        try:
                            numeric_ans = _ps.MATH_OPS[tgt_math_op]['fn'](L_tgt, R_tgt, 0, 0, 0, 0)
                        except (ZeroDivisionError, ValueError, OverflowError):
                            continue
                        encoded = _ps._encode_answer(
                            numeric_ans, tgt_math_op, tgt_op_str, f_type,
                            dm, digit_sym_list, ops_used,
                        )
                        if encoded is not None:
                            return encoded, ops_counter[0], False

            return None, ops_counter[0], False

        finally:
            _ps._derive_output = _orig_derive
    finally:
        sys.__stdout__ = orig_stdout


def run_all(problems, use_cat_fast_path):
    label = 'with cat' if use_cat_fast_path else 'no cat '
    records = []
    for p in tqdm(problems, desc=label, unit='prob'):
        ans, ops, used_cat = solve_greedy_counted(p.prompt, use_cat_fast_path=use_cat_fast_path)
        records.append({
            'id': p.id,
            'expected': str(p.answer),
            'got': str(ans),
            'correct': str(ans) == str(p.answer),
            'ops': ops,
            'used_cat': used_cat,
        })
    return records


def _pct(vals, p):
    if not vals:
        return 0
    s = sorted(vals)
    return s[min(int(len(s) * p / 100), len(s) - 1)]


def main():
    import random
    problems = [p for p in Problem.load_all() if 'cryptarithm' in p.category]
    random.shuffle(problems)
    problems = problems[:100]
    n = len(problems)
    print(f"Loaded {n} problems\n")

    records_with = run_all(problems, use_cat_fast_path=True)
    records_without = run_all(problems, use_cat_fast_path=False)

    lines = []
    lines.append("# Cat Fast-Path Analysis: Operations and Accuracy\n")
    lines.append(
        "Greedy first-match solver. Operations = cat permutation attempts + `_derive_output` calls.\n"
    )

    for label, records in [("With cat fast-path", records_with), ("Without cat fast-path", records_without)]:
        correct = [r for r in records if r['correct']]
        all_ops = [r['ops'] for r in records]

        lines.append(f"## {label}\n")
        lines.append(f"- Accuracy: **{len(correct)}/{n} ({len(correct)/n:.1%})**")
        if label == "With cat fast-path":
            cat_used = sum(1 for r in records if r['used_cat'])
            lines.append(f"- Cat fast-path triggered: {cat_used}/{n} ({cat_used/n:.1%})")
        lines.append(f"\n### Operation counts (all {n} problems)\n")
        lines.append(f"| Stat | Value |")
        lines.append(f"|------|------:|")
        lines.append(f"| Mean | {sum(all_ops)/n:.1f} |")
        lines.append(f"| Median | {_pct(all_ops, 50):,} |")
        lines.append(f"| p75 | {_pct(all_ops, 75):,} |")
        lines.append(f"| p90 | {_pct(all_ops, 90):,} |")
        lines.append(f"| p99 | {_pct(all_ops, 99):,} |")
        lines.append(f"| Max | {max(all_ops):,} |")
        lines.append(f"| Total | {sum(all_ops):,} |")
        lines.append("")

    # Budget sweep
    budgets = [1, 5, 10, 25, 50, 100, 250, 500, 1_000, 5_000, 10_000, 50_000, 100_000]
    lines.append("## Budget vs Accuracy\n")
    lines.append(f"| {'Budget':>10} | {'With cat':>12} | {'No cat':>12} |")
    lines.append(f"|{'-'*12}:|{'-'*14}:|{'-'*14}:|")
    for b in budgets:
        wc = sum(1 for r in records_with if r['correct'] and r['ops'] <= b)
        nc = sum(1 for r in records_without if r['correct'] and r['ops'] <= b)
        lines.append(f"| {b:>10,} | {wc:>4}/{n} ({wc/n:>5.1%}) | {nc:>4}/{n} ({nc/n:>5.1%}) |")

    # Summary
    wc_total = sum(1 for r in records_with if r['correct'])
    nc_total = sum(1 for r in records_without if r['correct'])
    wc_ops = sum(r['ops'] for r in records_with)
    nc_ops = sum(r['ops'] for r in records_without)
    speedup = nc_ops / wc_ops if wc_ops > 0 else float('inf')
    lines.append("\n## Summary\n")
    lines.append(f"| | With cat fast-path | Without cat fast-path |")
    lines.append(f"|-|-|-|")
    lines.append(f"| Accuracy | {wc_total}/{n} ({wc_total/n:.1%}) | {nc_total}/{n} ({nc_total/n:.1%}) |")
    lines.append(f"| Total ops | {wc_ops:,} | {nc_ops:,} |")
    lines.append(f"| Mean ops/problem | {wc_ops/n:.1f} | {nc_ops/n:.1f} |")
    lines.append(f"| Ops reduction | **{speedup:.1f}x fewer ops** | — |")
    lines.append("")

    report = '\n'.join(lines) + '\n'
    path = '/workspaces/nemotron/reasoners/cryptarithm_solver/cat_fastpath_report.md'
    with open(path, 'w') as f:
        f.write(report)

    print(f"\n{'Mode':<22}  {'Correct':>8}  {'Accuracy':>8}  {'Total ops':>12}  {'Median ops':>10}")
    print('-' * 70)
    for label, records in [("With cat fast-path", records_with), ("Without", records_without)]:
        correct = sum(1 for r in records if r['correct'])
        total_ops = sum(r['ops'] for r in records)
        med = _pct([r['ops'] for r in records], 50)
        print(f"{label:<22}  {correct:>4}/{n:<3}  {correct/n:>7.1%}  {total_ops:>12,}  {med:>10,}")
    print(f"\nOps reduction: {speedup:.1f}x")
    print(f"Report → {path}")


if __name__ == '__main__':
    main()
