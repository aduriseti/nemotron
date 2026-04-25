"""
Validate the correlation pre-filtering hypothesis:
  - For each problem, compute correlation score for each signed offset
  - Find the rank of the 'true' offsets (from infer's rule_info) in the ranked list
  - Report rank distribution

If true offsets are consistently in top-K, correlation-ranked search
would find the answer much faster.
"""

import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from reasoners.store_types import Problem
import bit_solver_infer as infer_mod

_TRANS_BYTES = infer_mod._TRANS_BYTES
TRANSFORMATIONS = infer_mod.TRANSFORMATIONS


def _norm(s):
    bits = [c for c in s if c in '01']
    return [int(b) for b in bits] if len(bits) == 8 else []


def trans_to_signed_offset(ttype, k):
    """Map a (ttype, k) transform back to its signed offset."""
    if ttype == 'rot':
        return 0 if k == 0 else k - 8   # rot_k (k≥1) → s = k-8
    elif ttype == 'shl':
        return k
    else:  # shr
        return -k


def compute_correlation_scores(in_bytes, out_bytes):
    """
    For each signed offset s in [-7..+7], score = number of (ex, pos) pairs
    where rep_s(input)[pos] == output[pos].
    Uses the representative transform for each s.
    """
    n_ex = len(in_bytes)
    scores = {}
    for s in range(-7, 8):
        rep_idx = infer_mod._S_REP[s]
        tb = _TRANS_BYTES[rep_idx]
        score = 0
        for ex in range(n_ex):
            for pos in range(8):
                inp_bit = (tb[in_bytes[ex]] >> (7 - pos)) & 1
                out_bit = (out_bytes[ex] >> (7 - pos)) & 1
                if inp_bit == out_bit:
                    score += 1
        scores[s] = score
    return scores


def rank_offsets(scores):
    """Return offsets sorted by score descending."""
    return sorted(scores.keys(), key=lambda s: scores[s], reverse=True)


def main():
    print("Loading problems...")
    all_problems = Problem.load_all()
    problems = [p for p in all_problems if p.category == 'bit_manipulation'][:300]
    print(f"Checking on {len(problems)} problems.\n")

    max_rank_by_arity = {1: Counter(), 2: Counter(), 3: Counter()}
    rank_distributions = []  # (arity, max_rank_of_true_offsets)
    problems_analyzed = 0
    no_rule = 0

    for p in problems:
        in_arrays   = [_norm(ex.input_value)  for ex in p.examples]
        out_arrays  = [_norm(ex.output_value) for ex in p.examples]
        target_bits = _norm(p.question)
        if any(len(a) != 8 for a in in_arrays + out_arrays) or len(target_bits) != 8:
            continue

        in_bytes  = [sum(r[i] << (7 - i) for i in range(8)) for r in in_arrays]
        out_bytes = [sum(r[i] << (7 - i) for i in range(8)) for r in out_arrays]

        answer, bit_checks, rule_info = infer_mod.find_rule(in_arrays, out_arrays, target_bits)
        expected = p.answer.strip()

        # Only analyze problems where infer found the correct answer
        if answer != expected or rule_info is None:
            no_rule += 1
            continue

        arity, tt_val, transforms = rule_info
        if arity == 0:
            continue  # No offsets to rank

        # Compute correlation scores
        scores = compute_correlation_scores(in_bytes, out_bytes)
        ranked = rank_offsets(scores)

        # Find ranks of true offsets
        true_offsets = [trans_to_signed_offset(t[0], t[1]) for t in transforms]

        # The "worst rank" among true offsets (determines how large K needs to be)
        ranks = [ranked.index(s) + 1 for s in true_offsets]  # 1-indexed rank
        max_rank = max(ranks)

        max_rank_by_arity[arity][max_rank] += 1
        rank_distributions.append((arity, max_rank, bit_checks))
        problems_analyzed += 1

    print(f"Analyzed: {problems_analyzed} problems (skipped {no_rule} with no/wrong rule)\n")

    # Report: for each arity, what K do you need to cover X% of problems?
    for arity in [1, 2, 3]:
        dist = max_rank_by_arity[arity]
        total = sum(dist.values())
        if total == 0:
            continue
        print(f"=== Arity {arity} ({total} problems) ===")
        print(f"{'Max rank needed':<20} {'Count':>6} {'Cumulative %':>14}")
        cumulative = 0
        for k in range(1, 16):
            count = dist.get(k, 0)
            cumulative += count
            pct = cumulative / total * 100
            print(f"  K={k:<17} {count:>6,}  {pct:>12.1f}%")
            if cumulative == total:
                break
        print()

    # Summary: bit-checks saved if we use top-K filtering
    print("=== Bit-check impact if using top-K filter for arity-3 ===")
    arity3_data = [(bc, mr) for (a, mr, bc) in rank_distributions if a == 3]
    if arity3_data:
        arity3_data.sort()
        for K in [3, 5, 7, 10]:
            covered = sum(1 for bc, mr in arity3_data if mr <= K)
            pct = covered / len(arity3_data) * 100
            # Estimate: problems covered by top-K finish in K^3 / 15^3 fraction of iterations
            ratio = (K**3) / (15**3)
            print(f"  K={K}: covers {covered}/{len(arity3_data)} ({pct:.1f}%) of arity-3 problems, "
                  f"~{ratio*100:.1f}% of full grid iterations")
    else:
        print("  No arity-3 data.")

    # Show score gap: true offset score vs rank-K score
    print("\n=== Sample: correlation scores for first 10 arity-3 problems ===")
    count = 0
    for p in problems:
        in_arrays   = [_norm(ex.input_value)  for ex in p.examples]
        out_arrays  = [_norm(ex.output_value) for ex in p.examples]
        target_bits = _norm(p.question)
        if any(len(a) != 8 for a in in_arrays + out_arrays) or len(target_bits) != 8:
            continue

        in_bytes  = [sum(r[i] << (7 - i) for i in range(8)) for r in in_arrays]
        out_bytes = [sum(r[i] << (7 - i) for i in range(8)) for r in out_arrays]

        answer, _, rule_info = infer_mod.find_rule(in_arrays, out_arrays, target_bits)
        if answer != p.answer.strip() or rule_info is None:
            continue
        arity, tt_val, transforms = rule_info
        if arity != 3:
            continue

        scores = compute_correlation_scores(in_bytes, out_bytes)
        ranked = rank_offsets(scores)
        true_offsets = [trans_to_signed_offset(t[0], t[1]) for t in transforms]
        ranks = [ranked.index(s) + 1 for s in true_offsets]

        score_list = [(s, scores[s]) for s in ranked[:8]]
        print(f"  Problem {p.id}: true offsets={true_offsets} ranks={ranks}")
        print(f"    Top-8 scores: {score_list}")
        count += 1
        if count >= 10:
            break


if __name__ == '__main__':
    main()
