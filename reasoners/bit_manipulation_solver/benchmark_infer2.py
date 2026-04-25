"""
Benchmark: bit_solver_infer vs bit_solver_infer2 (VSIDS hot_pos optimization).
Focus: bit-check count reduction, especially at p75/p90/p95 percentiles.
"""

import sys
import time
from pathlib import Path
from statistics import median, mean

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from reasoners.store_types import Problem
import reasoners.bit_manipulation_solver.bit_solver_infer  as infer_mod
import reasoners.bit_manipulation_solver.bit_solver_infer2 as infer2_mod


def _norm(s: str) -> list[int]:
    bits = [c for c in s if c in '01']
    return [int(b) for b in bits] if len(bits) == 8 else []


def main():
    print("Loading problems...")
    all_problems = Problem.load_all()
    problems = [p for p in all_problems if p.category == 'bit_manipulation'][:300]
    print(f"Benchmarking on {len(problems)} problems.\n")

    r1, r2 = [], []

    for p in problems:
        in_arrays   = [_norm(ex.input_value)  for ex in p.examples]
        out_arrays  = [_norm(ex.output_value) for ex in p.examples]
        target_bits = _norm(p.question)
        if any(len(a) != 8 for a in in_arrays + out_arrays) or len(target_bits) != 8:
            continue
        expected = p.answer.strip()

        t0 = time.perf_counter()
        ans1, bc1, ri1 = infer_mod.find_rule(in_arrays, out_arrays, target_bits)
        t1 = time.perf_counter() - t0

        t0 = time.perf_counter()
        ans2, bc2, ri2 = infer2_mod.find_rule(in_arrays, out_arrays, target_bits)
        t2 = time.perf_counter() - t0

        arity1 = ri1[0] if ri1 else None
        arity2 = ri2[0] if ri2 else None

        r1.append({'id': p.id, 'expected': expected, 'answer': ans1,
                   'correct': ans1 == expected, 'bc': bc1, 'time': t1, 'arity': arity1})
        r2.append({'id': p.id, 'expected': expected, 'answer': ans2,
                   'correct': ans2 == expected, 'bc': bc2, 'time': t2, 'arity': arity2})

    def stats(results, label):
        n = len(results)
        correct  = sum(1 for r in results if r['correct'])
        wrong    = sum(1 for r in results if r['answer'] is not None and not r['correct'])
        none_cnt = sum(1 for r in results if r['answer'] is None)
        bcs = sorted(r['bc'] for r in results)

        def pct(p):
            return bcs[min(int(p / 100 * n), n - 1)]

        print(f"=== {label} ===")
        print(f"  Accuracy: {correct}/{n} ({correct/n*100:.1f}%), wrong={wrong}, none={none_cnt}")
        print(f"  Bit-checks: min={min(bcs):,}, mean={mean(bcs):,.0f}, median={median(bcs):,.0f}, max={max(bcs):,}")
        print(f"  Percentiles: p50={pct(50):,}  p75={pct(75):,}  p90={pct(90):,}  p95={pct(95):,}  p99={pct(99):,}")
        print(f"  Mean time: {mean(r['time'] for r in results)*1000:.2f}ms")
        print()
        return {'n': n, 'correct': correct, 'bcs': bcs,
                'p50': pct(50), 'p75': pct(75), 'p90': pct(90), 'p95': pct(95), 'p99': pct(99)}

    s1 = stats(r1, "infer (baseline)")
    s2 = stats(r2, "infer2 (hot_pos VSIDS)")

    print("=== Delta (infer2 - infer) ===")
    for pname in ['p50', 'p75', 'p90', 'p95', 'p99']:
        d = s2[pname] - s1[pname]
        pct_change = (s2[pname] - s1[pname]) / s1[pname] * 100
        sign = "+" if d > 0 else ""
        print(f"  {pname}: {sign}{d:,} ({sign}{pct_change:.1f}%)")

    # Per-arity breakdown
    print()
    for arity in [1, 2, 3]:
        pairs = [(a['bc'], b['bc']) for a, b in zip(r1, r2) if a['arity'] == arity]
        if not pairs:
            continue
        bc1s = sorted(p[0] for p in pairs)
        bc2s = sorted(p[1] for p in pairs)
        n = len(pairs)
        def pa(arr, p):
            return arr[min(int(p/100*n), n-1)]
        savings = [a - b for a, b in pairs]
        print(f"  Arity {arity} ({n} problems): infer p90={pa(bc1s,90):,} vs infer2 p90={pa(bc2s,90):,}  "
              f"median savings={sorted(savings)[n//2]:,}")

    # Regression check: problems where infer2 is WRONG but infer is RIGHT
    regressions = [(a, b) for a, b in zip(r1, r2) if a['correct'] and not b['correct']]
    if regressions:
        print(f"\nWARNING: {len(regressions)} regressions (infer correct, infer2 wrong):")
        for a, b in regressions[:10]:
            print(f"  {a['id']}: expected={a['expected']}, infer={a['answer']}, infer2={b['answer']}")
    else:
        print("\nNo regressions.")

    improvements = [(a, b) for a, b in zip(r1, r2) if not a['correct'] and b['correct']]
    if improvements:
        print(f"\nImprovements: {len(improvements)} problems (infer2 correct, infer wrong):")
        for a, b in improvements[:5]:
            print(f"  {a['id']}: expected={a['expected']}, infer={a['answer']}, infer2={b['answer']}")


if __name__ == '__main__':
    main()
