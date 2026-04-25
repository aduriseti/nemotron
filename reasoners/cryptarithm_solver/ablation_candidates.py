"""Ablation: accuracy vs max candidate solutions explored (python_solver)."""
import sys, time
sys.path.insert(0, '/workspaces/nemotron')

from reasoners.store_types import Problem
import reasoners.cryptarithm_solver.python_solver as _ps

CANDIDATE_LIMITS = [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 50000]
N_PROBLEMS = 30
TIMEOUT = 2.0


def solve_with_limit(prompt: str, target_answer: str, max_solutions: int):
    """Clone of solve_cipher_unified with configurable max_solutions."""
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
    possible_answers: dict[str, int] = {}
    total_candidates = 0

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

        solutions: list[tuple[dict, dict]] = []
        deadline = time.time() + TIMEOUT
        _ps._search(parsed_examples, 0, {}, set(), {}, plausible_per_ex,
                    f_type, solutions, deadline, max_solutions=max_solutions)

        total_candidates += len(solutions)

        tgt_ex = {'A': tA, 'B': tB, 'op': tgt_op_str, 'out': []}
        tA0s, tA1s, tB0s, tB1s = _ps._syms_for_pipeline(tgt_ex, f_type)
        tgt_op_seen = any(ex['op'] == tgt_op_str for ex in parsed_examples)
        op_names = list(_ps.MATH_OPS.keys())

        for digit_map, op_assign in solutions:
            if tgt_op_seen:
                tgt_math_op = op_assign.get(tgt_op_str)
                if not tgt_math_op:
                    continue
                candidate_ops = [tgt_math_op]
            else:
                candidate_ops = op_names

            target_syms_4 = (tA0s, tA1s, tB0s, tB1s)
            unique_missing = list(dict.fromkeys(s for s in target_syms_4 if s not in digit_map))
            if unique_missing:
                avail = [v for v in range(10) if v not in digit_map.values()]
                if len(avail) < len(unique_missing):
                    continue
                maps_to_try = [
                    {**digit_map, **dict(zip(unique_missing, combo))}
                    for combo in _ps._permutations(avail, len(unique_missing))
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
                        possible_answers[encoded] = possible_answers.get(encoded, 0) + 1

    greedy = max(possible_answers, key=possible_answers.get) if possible_answers else None
    return greedy, total_candidates


def main():
    problems = [p for p in Problem.load_all() if p.category == 'cryptarithm_deduce'][:N_PROBLEMS]
    print(f"Loaded {len(problems)} problems\n")

    # header
    print(f"{'max_cands':>10}  {'correct':>7}  {'accuracy':>8}  {'avg_cands':>9}  {'avg_time':>9}")
    print('-' * 55)

    for limit in CANDIDATE_LIMITS:
        correct = 0
        total_cands = 0
        total_time = 0.0

        for p in problems:
            t0 = time.time()
            ans, cands = solve_with_limit(p.prompt, str(p.answer), limit)
            elapsed = time.time() - t0
            total_cands += cands
            total_time += elapsed
            if str(ans) == str(p.answer):
                correct += 1

        n = len(problems)
        avg_cands = total_cands / n
        avg_time = total_time / n
        pct = correct / n * 100
        print(f"{limit:>10}  {correct:>4}/{n:<3}  {pct:>7.1f}%  {avg_cands:>9.1f}  {avg_time:>8.2f}s")


if __name__ == '__main__':
    main()
