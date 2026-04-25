"""
Ablation: accuracy vs derive_output call budget using first-match (greedy) strategy.

Instead of collecting all candidates and voting, we return the answer from the
very first candidate found across all 3 pipelines. We instrument _derive_output
to count calls, then vary the budget and see what fraction of the dataset is solved.
"""
import sys, time, math
sys.path.insert(0, '/workspaces/nemotron')

from reasoners.store_types import Problem
import reasoners.cryptarithm_solver.python_solver as _ps

TIMEOUT = 2.0


class BudgetExceeded(Exception):
    pass


def solve_first_match(prompt: str, budget: int):
    """
    Return (answer, calls_used) using first-match strategy.
    Stops as soon as any pipeline yields 1 candidate.
    Raises BudgetExceeded if the budget is hit before finding a candidate.
    """
    extraction = _ps.extract_all_examples(prompt)
    if extraction[0] is None:
        return None, 0

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

    # Instrument _derive_output with a counter that enforces the budget
    _orig_derive = _ps._derive_output
    counter = [0]

    def _budgeted_derive(*args, **kwargs):
        counter[0] += 1
        if counter[0] > budget:
            raise BudgetExceeded()
        return _orig_derive(*args, **kwargs)

    _ps._derive_output = _budgeted_derive

    try:
        for f_type in _ps.FORMATTERS:
            plausible_per_ex = []
            skip = False
            for ex in parsed_examples:
                ops = _ps._plausible_ops(ex)
                if not ops:
                    skip = True
                    break
                plausible_per_ex.append(ops)
            if skip:
                continue

            solutions = []
            try:
                _ps._search(parsed_examples, 0, {}, set(), {}, plausible_per_ex,
                            f_type, solutions, time.time() + TIMEOUT, max_solutions=1)
            except BudgetExceeded:
                return None, budget  # budget exhausted

            if not solutions:
                continue  # this pipeline found nothing; try next

            # First match found — compute its answer
            digit_map, op_assign = solutions[0]
            tgt_ex = {'A': tA, 'B': tB, 'op': tgt_op_str, 'out': []}
            tA0s, tA1s, tB0s, tB1s = _ps._syms_for_pipeline(tgt_ex, f_type)
            tgt_op_seen = any(ex['op'] == tgt_op_str for ex in parsed_examples)
            op_names = list(_ps.MATH_OPS.keys())

            target_syms_4 = (tA0s, tA1s, tB0s, tB1s)
            unique_missing = list(dict.fromkeys(s for s in target_syms_4 if s not in digit_map))
            if unique_missing:
                avail = [v for v in range(10) if v not in digit_map.values()]
                if len(avail) < len(unique_missing):
                    return None, counter[0]
                maps_to_try = [
                    {**digit_map, **dict(zip(unique_missing, combo))}
                    for combo in _ps._permutations(avail, len(unique_missing))
                ]
            else:
                maps_to_try = [digit_map]

            candidate_ops = [op_assign[tgt_op_str]] if tgt_op_seen and tgt_op_str in op_assign else op_names

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
                        return encoded, counter[0]

            return None, counter[0]

        return None, counter[0]  # no pipeline found anything

    finally:
        _ps._derive_output = _orig_derive


def profile_all_problems(problems):
    """Run unlimited solve on each problem and record calls-to-first-match + correctness."""
    records = []
    for p in problems:
        ans, calls = solve_first_match(p.prompt, budget=10_000_000)
        correct = str(ans) == str(p.answer)
        records.append({
            'id': p.id,
            'expected': str(p.answer),
            'got': str(ans),
            'correct': correct,
            'calls': calls,
        })
    return records


def budget_accuracy(records, budget):
    solved = sum(1 for r in records if r['correct'] and r['calls'] <= budget)
    attempted = sum(1 for r in records if r['calls'] <= budget)
    return solved, attempted, len(records)


def main():
    problems = [p for p in Problem.load_all() if 'cryptarithm' in p.category]
    n = len(problems)
    print(f"Loaded {n} problems (all cryptarithm categories)\n")
    print("Profiling first-match cost per problem...", flush=True)

    records = profile_all_problems(problems)

    # Budget sweep: log-spaced from 1 to max_calls
    max_calls = max(r['calls'] for r in records)
    budgets = sorted(set(
        [1, 5, 10, 25, 50, 100, 250, 500, 1_000, 2_500, 5_000,
         10_000, 25_000, 50_000, 100_000, 250_000, 500_000, 1_000_000]
        + [max_calls]
    ))

    # --- write report ---
    lines = []
    lines.append("# First-Match Ablation: Budget vs. Accuracy\n")
    lines.append("## Methodology\n")
    lines.append(
        "Instead of collecting all consistent candidates and voting, we return the answer "
        "from the **first** candidate found (across all 3 pipelines). "
        "A `_derive_output` call is the atomic unit of work: one digit-tuple × one math "
        "operation tried against the encrypted output.\n"
        "\n"
        "For each problem we record:\n"
        "- `calls`: number of `_derive_output` calls until the first candidate was found\n"
        "- `correct`: whether the first candidate's answer matches the expected answer\n"
        "\n"
        "We then sweep a **budget** (max allowed calls) and report:\n"
        "- **Solved**: first candidate found within budget AND answer correct\n"
        "- **Attempted**: first candidate found within budget (right or wrong)\n"
        "- **Precision**: solved / attempted (answer quality given a match was found)\n"
        "- **Recall**: solved / total problems\n"
    )

    lines.append("## Budget vs. Accuracy\n")
    lines.append(f"| {'Budget':>10} | {'Solved':>8} | {'Attempted':>9} | {'Precision':>9} | {'Recall':>8} |")
    lines.append(f"|{'-'*12}:|{'-'*10}:|{'-'*11}:|{'-'*11}:|{'-'*10}:|")

    for b in budgets:
        solved, attempted, total = budget_accuracy(records, b)
        precision = solved / attempted if attempted > 0 else 0.0
        recall = solved / total
        lines.append(
            f"| {b:>10,} | {solved:>4}/{total:<3} | {attempted:>4}/{total:<3}  | "
            f"{precision:>8.1%} | {recall:>7.1%} |"
        )

    # Max-budget stats
    always_correct = [r for r in records if r['correct']]
    never_correct  = [r for r in records if not r['correct']]
    no_candidate   = [r for r in records if r['calls'] == 0 or (not r['correct'] and r['got'] == 'None')]

    lines.append("\n## Per-Problem Summary\n")
    lines.append(f"- Total problems: {n}")
    lines.append(f"- First-match correct (unlimited): {len(always_correct)}/{n} ({len(always_correct)/n:.1%})")
    lines.append(f"- First-match wrong (unlimited): {len(never_correct)}/{n}")
    lines.append(f"- No candidate found (infinite budget, still None): {sum(1 for r in records if r['got']=='None')}")

    correct_calls = sorted(r['calls'] for r in always_correct)
    if correct_calls:
        lines.append(f"\n### Calls-to-first-correct-match (n={len(correct_calls)})")
        lines.append(f"- Min:    {min(correct_calls):>10,}")
        lines.append(f"- p25:    {correct_calls[len(correct_calls)//4]:>10,}")
        lines.append(f"- Median: {correct_calls[len(correct_calls)//2]:>10,}")
        lines.append(f"- p75:    {correct_calls[3*len(correct_calls)//4]:>10,}")
        lines.append(f"- p90:    {correct_calls[int(len(correct_calls)*0.9)]:>10,}")
        lines.append(f"- Max:    {max(correct_calls):>10,}")

    lines.append("\n## Per-Problem Detail\n")
    lines.append(f"| {'id':12} | {'expected':12} | {'got':12} | {'correct':7} | {'calls':>10} |")
    lines.append(f"|{'-'*14}|{'-'*14}|{'-'*14}|{'-'*9}|{'-'*12}:|")
    for r in sorted(records, key=lambda x: x['calls']):
        ok = '✓' if r['correct'] else '✗'
        lines.append(
            f"| {r['id'][:12]:12} | {r['expected'][:12]:12} | {r['got'][:12]:12} | "
            f"{ok:^7} | {r['calls']:>10,} |"
        )

    report = '\n'.join(lines) + '\n'

    report_path = '/workspaces/nemotron/reasoners/cryptarithm_solver/first_match_report.md'
    with open(report_path, 'w') as f:
        f.write(report)

    # also print summary to stdout
    print(f"\n{'Budget':>12}  {'Solved':>10}  {'Precision':>9}  {'Recall':>8}")
    print('-' * 48)
    for b in budgets:
        solved, attempted, total = budget_accuracy(records, b)
        precision = solved / attempted if attempted > 0 else 0.0
        recall = solved / total
        print(f"{b:>12,}  {solved:>4}/{total:<5}  {precision:>8.1%}  {recall:>7.1%}")

    print(f"\nReport written to {report_path}")


if __name__ == '__main__':
    main()
