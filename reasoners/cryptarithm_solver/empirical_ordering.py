"""
Empirical frequency analysis: what digit values, operations, and pipelines appear in correct solutions?

For each problem, find ALL (digit_map, tgt_math_op, pipeline) triples that produce the golden answer.
Weight each triple by 1/N (where N = # correct triples for that problem) so each problem contributes
exactly weight 1.0 total — no double-counting across problems.
"""
import sys, time, random
from collections import defaultdict
sys.path.insert(0, '/workspaces/nemotron')

from tqdm import tqdm
from reasoners.store_types import Problem
import reasoners.cryptarithm_solver.python_solver as _ps

TIMEOUT = 2.0
MAX_SOLUTIONS = 50000


def collect_correct_solutions(problems):
    """
    Returns:
      digit_freq:    {digit_value: float}   — weighted, sums to N_solved
      op_freq:       {math_op_name: float}  — weighted, sums to N_solved
      pipeline_freq: {f_type: float}        — weighted, sums to N_solved
      pos_freq:      {pos: {digit: float}}  — weighted per position, each sums to N_solved
      stats:         {solved, unsolved, no_candidate}
    """
    digit_freq    = defaultdict(float)
    op_freq       = defaultdict(float)
    pipeline_freq = defaultdict(float)
    pos_freq = {p: defaultdict(float) for p in ('A0', 'A1', 'B0', 'B1')}
    stats = {'solved': 0, 'unsolved': 0, 'no_candidate': 0}

    for prob in tqdm(problems, desc='collecting', unit='prob'):
        extraction = _ps.extract_all_examples(prob.prompt)
        if extraction[0] is None:
            stats['no_candidate'] += 1
            continue

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

        # Collect all unique (dm, tgt_math_op, f_type) triples that produce the golden answer.
        correct: list[tuple[dict, str, str]] = []
        seen_keys: set[tuple] = set()

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

            solutions = []
            _ps._search(parsed_examples, 0, {}, set(), {}, plausible_per_ex,
                        f_type, solutions, time.time() + TIMEOUT, max_solutions=MAX_SOLUTIONS)

            tgt_ex = {'A': tA, 'B': tB, 'op': tgt_op_str, 'out': []}
            tA0s, tA1s, tB0s, tB1s = _ps._syms_for_pipeline(tgt_ex, f_type)
            tgt_op_seen = any(ex['op'] == tgt_op_str for ex in parsed_examples)
            op_names = list(_ps.MATH_OPS.keys())

            for digit_map, op_assign in solutions:
                target_syms_4 = (tA0s, tA1s, tB0s, tB1s)
                unique_missing = list(dict.fromkeys(s for s in target_syms_4 if s not in digit_map))
                if unique_missing:
                    avail = [v for v in range(10) if v not in digit_map.values()]
                    if not avail:
                        avail = list(range(10))
                    maps_to_try = [{**digit_map, **dict(zip(unique_missing, c))}
                                   for c in _ps._permutations(avail, len(unique_missing))]
                else:
                    maps_to_try = [digit_map]

                candidate_ops = [op_assign[tgt_op_str]] if tgt_op_seen and tgt_op_str in op_assign else op_names

                for dm in maps_to_try:
                    ta0, ta1, tb0, tb1 = dm[tA0s], dm[tA1s], dm[tB0s], dm[tB1s]
                    L, R = ta0*10+ta1, tb0*10+tb1
                    for tgt_math_op in candidate_ops:
                        try:
                            num = _ps.MATH_OPS[tgt_math_op]['fn'](L, R, 0, 0, 0, 0)
                        except (ZeroDivisionError, ValueError, OverflowError):
                            continue
                        enc = _ps._encode_answer(num, tgt_math_op, tgt_op_str, f_type,
                                                  dm, digit_sym_list, ops_used)
                        if enc == str(prob.answer):
                            key = (frozenset(dm.items()), tgt_math_op, f_type)
                            if key not in seen_keys:
                                seen_keys.add(key)
                                correct.append((dm, tgt_math_op, f_type))

        if not correct:
            stats['unsolved'] += 1
            continue

        # Each problem contributes weight 1.0 total, split evenly across its correct solutions.
        w = 1.0 / len(correct)
        stats['solved'] += 1

        for dm, tgt_math_op, f_type in correct:
            op_freq[tgt_math_op] += w
            pipeline_freq[f_type] += w
            for v in set(dm.values()):
                digit_freq[v] += w
            for ex in parsed_examples:
                A0s, A1s, B0s, B1s = _ps._syms_for_pipeline(ex, f_type)
                for pos, sym in [('A0', A0s), ('A1', A1s), ('B0', B0s), ('B1', B1s)]:
                    if sym in dm:
                        pos_freq[pos][sym_val := dm[sym]] += w

    return digit_freq, op_freq, pipeline_freq, pos_freq, stats


def main():
    problems = [p for p in Problem.load_all() if 'cryptarithm' in p.category]
    random.shuffle(problems)
    problems = problems[:100]
    print(f"Collecting correct solutions from {len(problems)} shuffled problems...", flush=True)
    t0 = time.time()
    digit_freq, op_freq, pipeline_freq, pos_freq, stats = collect_correct_solutions(problems)
    elapsed = time.time() - t0

    n_solved = stats['solved']
    # Each problem contributes weight 1.0 — op_freq and pipeline_freq must both sum to n_solved.
    assert abs(sum(op_freq.values()) - n_solved) < 0.01, \
        f"op_freq sum {sum(op_freq.values()):.2f} != {n_solved}"
    assert abs(sum(pipeline_freq.values()) - n_solved) < 0.01, \
        f"pipeline_freq sum {sum(pipeline_freq.values()):.2f} != {n_solved}"
    assert all(v <= n_solved + 0.01 for v in op_freq.values()), "op value exceeds n_solved"
    assert all(v <= n_solved + 0.01 for v in pipeline_freq.values()), "pipeline value exceeds n_solved"

    print(f"Done in {elapsed:.1f}s")
    print(f"  Solved: {n_solved}, Unsolved: {stats['unsolved']}, No parse: {stats['no_candidate']}")

    total_digit = sum(digit_freq.values())
    sorted_digits = sorted(digit_freq.items(), key=lambda x: -x[1])
    sorted_ops = sorted(op_freq.items(), key=lambda x: -x[1])
    sorted_pipelines = sorted(pipeline_freq.items(), key=lambda x: -x[1])

    lines = []
    lines.append("# Empirical Frequency Analysis\n")
    lines.append(f"- Problems analysed: {len(problems)}")
    lines.append(f"- Problems solved (≥1 correct solution): {n_solved}")
    lines.append(f"- Each problem contributes weight 1.0 total (split evenly across correct solutions)\n")

    lines.append("## Operation Frequencies\n")
    lines.append(f"Weighted sum = {sum(op_freq.values()):.1f} (= n_solved = {n_solved})\n")
    lines.append(f"| {'Operation':>14} | {'Weight':>8} | {'Frequency':>9} | Rank |")
    lines.append(f"|{'-'*16}:|{'-'*10}:|{'-'*11}:|{'-'*6}|")
    for rank, (op, w) in enumerate(sorted_ops):
        lines.append(f"| {op:>14} | {w:>8.2f} | {w/n_solved:>8.1%}  | {rank+1:>4} |")
    lines.append(f"\n**Recommended op order**: `{[op for op, _ in sorted_ops]}`\n")

    lines.append("## Pipeline Frequencies\n")
    lines.append(f"Weighted sum = {sum(pipeline_freq.values()):.1f} (= n_solved = {n_solved})\n")
    lines.append(f"| {'Pipeline':>10} | {'Weight':>8} | {'Frequency':>9} |")
    lines.append(f"|{'-'*12}:|{'-'*10}:|{'-'*11}:|")
    for f_type, w in sorted_pipelines:
        lines.append(f"| {f_type:>10} | {w:>8.2f} | {w/n_solved:>8.1%}  |")
    lines.append(f"\n**Recommended pipeline order**: `{[f for f, _ in sorted_pipelines]}`\n")

    lines.append("## Digit Value Frequencies\n")
    lines.append(f"Weighted sum = {total_digit:.1f} (each problem contributes #unique_digits_used weight)\n")
    lines.append(f"| {'Digit':>5} | {'Weight':>8} | {'% of total':>10} | Rank |")
    lines.append(f"|{'-'*7}:|{'-'*10}:|{'-'*12}:|{'-'*6}|")
    for rank, (d, w) in enumerate(sorted_digits):
        lines.append(f"| {d:>5} | {w:>8.2f} | {w/total_digit:>9.1%}  | {rank+1:>4} |")
    lines.append(f"\n**Recommended digit order**: `{[d for d, _ in sorted_digits]}`\n")

    lines.append("## Per-Position Digit Frequencies\n")
    lines.append("Each position sums to n_solved (weight 1.0 per problem per position).\n")
    header = f"| {'Digit':>5} | {'A0 (tens-L)':>11} | {'A1 (ones-L)':>11} | {'B0 (tens-R)':>11} | {'B1 (ones-R)':>11} |"
    lines.append(header)
    lines.append(f"|{'-'*7}:|{'-'*13}:|{'-'*13}:|{'-'*13}:|{'-'*13}:|")
    for d in range(10):
        row = f"| {d:>5} |"
        for pos in ('A0', 'A1', 'B0', 'B1'):
            total = sum(pos_freq[pos].values())
            c = pos_freq[pos].get(d, 0)
            row += f" {c/total:>10.1%} |" if total else " — |"
        lines.append(row)
    lines.append("\n### Recommended digit order per position")
    for pos in ('A0', 'A1', 'B0', 'B1'):
        order = [d for d, _ in sorted(pos_freq[pos].items(), key=lambda x: -x[1])]
        lines.append(f"- `{pos}`: `{order}`")
    lines.append("")

    report = '\n'.join(lines) + '\n'
    path = '/workspaces/nemotron/reasoners/cryptarithm_solver/empirical_ordering_report.md'
    with open(path, 'w') as f:
        f.write(report)

    print(f"\n{'Operation':>16}  {'Weight':>8}  {'Freq':>7}")
    print('-' * 38)
    for op, w in sorted_ops:
        print(f"{op:>16}  {w:>8.2f}  {w/n_solved:>6.1%}")

    print(f"\n{'Pipeline':>10}  {'Weight':>8}  {'Freq':>7}")
    print('-' * 30)
    for f_type, w in sorted_pipelines:
        print(f"{f_type:>10}  {w:>8.2f}  {w/n_solved:>6.1%}")

    print(f"\n{'Digit':>6}  {'Weight':>8}  {'Freq':>7}")
    print('-' * 28)
    for d, w in sorted_digits:
        print(f"{d:>6}  {w:>8.2f}  {w/total_digit:>6.1%}")

    print(f"\nReport written to {path}")


if __name__ == '__main__':
    main()
