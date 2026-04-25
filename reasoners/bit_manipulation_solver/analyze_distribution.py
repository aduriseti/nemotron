"""
Compute the empirical distribution of transform types, k-values, and signed
offsets from correct solver answers. Also checks whether the distribution
could be an artifact of solver enumeration order.
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from reasoners.store_types import Problem
import reasoners.bit_manipulation_solver.bit_solver_v3_freqord as v3
import reasoners.bit_manipulation_solver.bit_solver_v1_base    as v1


def _norm(s: str) -> list[int]:
    bits = [c for c in s if c in '01']
    return [int(b) for b in bits] if len(bits) == 8 else []


def signed_offset(ttype: str, k: int) -> int:
    if ttype == 'rot':
        return 0 if k == 0 else -(8 - k)
    elif ttype == 'shl':
        return k
    else:  # shr
        return -k


def analyze(solver_mod, label, problems):
    arity_counts = Counter()
    type_counts  = Counter()
    k_counts     = Counter()
    s_counts     = Counter()
    correct = 0

    for p in problems:
        in_arrays   = [_norm(ex.input_value)  for ex in p.examples]
        out_arrays  = [_norm(ex.output_value) for ex in p.examples]
        target_bits = _norm(p.question)
        if any(len(a) != 8 for a in in_arrays + out_arrays) or len(target_bits) != 8:
            continue
        expected = p.answer.strip()

        ans, bc, ri = solver_mod.find_rule(in_arrays, out_arrays, target_bits)
        if ans != expected or ri is None:
            continue

        correct += 1
        arity, tt_val, transforms = ri
        arity_counts[arity] += 1

        for ttype, k in transforms:
            type_counts[ttype] += 1
            k_counts[k] += 1
            s = signed_offset(ttype, k)
            s_counts[s] += 1

    print(f"\n{'='*60}")
    print(f"  {label}  ({correct} correct answers)")
    print(f"{'='*60}")

    print(f"\nArity distribution:")
    total = sum(arity_counts.values())
    for ar in sorted(arity_counts):
        n = arity_counts[ar]
        print(f"  arity {ar}: {n:4d}  ({n/correct*100:.1f}% of problems)")

    print(f"\nTransform type (across all transform slots in correct rules):")
    total_t = sum(type_counts.values())
    for t in sorted(type_counts, key=lambda x: -type_counts[x]):
        n = type_counts[t]
        print(f"  {t:4s}: {n:4d}  ({n/total_t*100:.1f}%)")

    print(f"\nSigned offset s distribution (arity-3 problems only):")
    # Re-run just for arity-3
    s3 = Counter()
    for p in problems:
        in_arrays   = [_norm(ex.input_value)  for ex in p.examples]
        out_arrays  = [_norm(ex.output_value) for ex in p.examples]
        target_bits = _norm(p.question)
        if any(len(a) != 8 for a in in_arrays + out_arrays) or len(target_bits) != 8:
            continue
        ans, bc, ri = solver_mod.find_rule(in_arrays, out_arrays, target_bits)
        if ans != p.answer.strip() or ri is None or ri[0] != 3:
            continue
        _, _, transforms = ri
        for ttype, k in transforms:
            s3[signed_offset(ttype, k)] += 1

    total_s3 = sum(s3.values())
    if total_s3:
        print(f"  (total transform slots: {total_s3}, from {sum(1 for p in problems if True)} problems)")
        for s in sorted(s3, key=lambda x: -s3[x]):
            n = s3[s]
            print(f"  s={s:+3d}: {n:3d}  ({n/total_s3*100:.1f}%)")

    print(f"\nk-value distribution (all arities, all types):")
    total_k = sum(k_counts.values())
    for k in sorted(k_counts, key=lambda x: -k_counts[x]):
        n = k_counts[k]
        print(f"  k={k}: {n:4d}  ({n/total_k*100:.1f}%)")

    return s3


def main():
    print("Loading problems...")
    all_problems = Problem.load_all()
    problems = [p for p in all_problems if p.category == 'bit_manipulation'][:300]
    print(f"Analyzing {len(problems)} problems.\n")

    s3_v1 = analyze(v1, "v1_base (unordered enumeration)", problems)
    s3_v3 = analyze(v3, "v3_freqord (frequency-ordered enumeration)", problems)

    print(f"\n{'='*60}")
    print("  Comparison: s-value distribution for arity-3 (v1 vs v3)")
    print(f"{'='*60}")
    all_s = sorted(set(s3_v1) | set(s3_v3))
    t1 = sum(s3_v1.values()) or 1
    t3 = sum(s3_v3.values()) or 1
    print(f"  {'s':>4}  {'v1 count':>10}  {'v1 %':>6}  {'v3 count':>10}  {'v3 %':>6}  {'same?':>6}")
    print(f"  {'-'*4}  {'-'*10}  {'-'*6}  {'-'*10}  {'-'*6}  {'-'*6}")
    for s in all_s:
        n1 = s3_v1.get(s, 0)
        n3 = s3_v3.get(s, 0)
        same = "✓" if n1 == n3 else "≠"
        print(f"  {s:+4d}  {n1:>10}  {n1/t1*100:>5.1f}%  {n3:>10}  {n3/t3*100:>5.1f}%  {same:>6}")

    # How close is the distribution to uniform?
    n_offsets = 14  # _S_ORDER_A3 has 14 values
    uniform_pct = 100.0 / n_offsets
    print(f"\n  Uniform expectation per s-value: {uniform_pct:.1f}%")
    print(f"  Max deviation from uniform (v3): "
          f"{max(abs(s3_v3.get(s,0)/t3*100 - uniform_pct) for s in all_s):.1f}%")


if __name__ == '__main__':
    main()
