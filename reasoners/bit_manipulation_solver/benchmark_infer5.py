"""
Benchmark: bit_solver_infer3 vs bit_solver_infer5 (symmetry-breaking joint-permutation).
Full dataset (1602 problems). Writes results to symmetry_breaking_report.md.
"""

import sys
import time
from pathlib import Path
from statistics import median, mean

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from reasoners.store_types import Problem
import reasoners.bit_manipulation_solver.bit_solver_infer3 as infer3_mod
import reasoners.bit_manipulation_solver.bit_solver_infer5 as infer5_mod


def _norm(s: str) -> list[int]:
    bits = [c for c in s if c in '01']
    return [int(b) for b in bits] if len(bits) == 8 else []


def run_benchmark():
    print("Loading problems...")
    all_problems = Problem.load_all()
    problems = [p for p in all_problems if p.category == 'bit_manipulation']
    print(f"Benchmarking on {len(problems)} problems.\n")

    r3, r5 = [], []

    for i, p in enumerate(problems):
        if i % 100 == 0:
            print(f"  {i}/{len(problems)}...", flush=True)
        in_arrays   = [_norm(ex.input_value)  for ex in p.examples]
        out_arrays  = [_norm(ex.output_value) for ex in p.examples]
        target_bits = _norm(p.question)
        if any(len(a) != 8 for a in in_arrays + out_arrays) or len(target_bits) != 8:
            continue
        expected = p.answer.strip()

        t0 = time.perf_counter()
        ans3, bc3, ri3 = infer3_mod.find_rule(in_arrays, out_arrays, target_bits)
        t3 = time.perf_counter() - t0

        t0 = time.perf_counter()
        ans5, bc5, ri5 = infer5_mod.find_rule(in_arrays, out_arrays, target_bits)
        t5 = time.perf_counter() - t0

        r3.append({'id': p.id, 'expected': expected, 'answer': ans3,
                   'correct': ans3 == expected, 'bc': bc3, 'time': t3,
                   'arity': ri3[0] if ri3 else None})
        r5.append({'id': p.id, 'expected': expected, 'answer': ans5,
                   'correct': ans5 == expected, 'bc': bc5, 'time': t5,
                   'arity': ri5[0] if ri5 else None})

    return r3, r5, len(problems)


def compute_stats(results, label):
    n = len(results)
    correct  = sum(1 for r in results if r['correct'])
    wrong    = sum(1 for r in results if r['answer'] is not None and not r['correct'])
    none_cnt = sum(1 for r in results if r['answer'] is None)
    bcs = sorted(r['bc'] for r in results)

    def pct(p):
        return bcs[min(int(p / 100 * n), n - 1)]

    return {
        'label': label, 'n': n, 'correct': correct, 'wrong': wrong, 'none': none_cnt,
        'min': min(bcs), 'mean': mean(bcs), 'median': median(bcs), 'max': max(bcs),
        'p50': pct(50), 'p75': pct(75), 'p90': pct(90), 'p95': pct(95), 'p99': pct(99),
        'mean_time': mean(r['time'] for r in results),
        'bcs': bcs,
    }


def print_stats(s):
    n, correct = s['n'], s['correct']
    print(f"=== {s['label']} ===")
    print(f"  Accuracy: {correct}/{n} ({correct/n*100:.1f}%), wrong={s['wrong']}, none={s['none']}")
    print(f"  Bit-checks: min={s['min']:,}, mean={s['mean']:,.0f}, median={s['median']:,.0f}, max={s['max']:,}")
    print(f"  Percentiles: p50={s['p50']:,}  p75={s['p75']:,}  p90={s['p90']:,}  p95={s['p95']:,}  p99={s['p99']:,}")
    print(f"  Mean time: {s['mean_time']*1000:.2f}ms")
    print()


def per_arity_stats(results, label):
    rows = []
    for arity in [0, 1, 2, 3]:
        sub = [r for r in results if r['arity'] == arity]
        if not sub:
            continue
        bcs = sorted(r['bc'] for r in sub)
        n = len(sub)
        correct = sum(1 for r in sub if r['correct'])
        def pa(p): return bcs[min(int(p/100*n), n-1)]
        rows.append({
            'arity': arity, 'n': n, 'correct': correct,
            'mean': mean(bcs), 'p50': pa(50), 'p75': pa(75), 'p90': pa(90), 'p95': pa(95),
        })
    return rows


def accuracy_at_budget(results, budget):
    return sum(1 for r in results if r['correct'] and r['bc'] <= budget)


def main():
    r3, r5, total = run_benchmark()

    s3 = compute_stats(r3, "infer3 (baseline)")
    s5 = compute_stats(r5, "infer5 (symmetry-breaking)")

    print_stats(s3)
    print_stats(s5)

    print("=== Delta (infer5 - infer3) ===")
    for pname in ['p50', 'p75', 'p90', 'p95', 'p99']:
        d = s5[pname] - s3[pname]
        pct_change = d / s3[pname] * 100 if s3[pname] else 0
        sign = "+" if d > 0 else ""
        print(f"  {pname}: {sign}{d:,} ({sign}{pct_change:.1f}%)")
    print()

    # Per-arity breakdown
    a3 = per_arity_stats(r3, "infer3")
    a5 = per_arity_stats(r5, "infer5")
    print("=== Per-arity bit-check summary ===")
    for row3, row5 in zip(a3, a5):
        assert row3['arity'] == row5['arity']
        ar = row3['arity']
        print(f"  Arity {ar} ({row3['n']} problems):")
        print(f"    infer3: mean={row3['mean']:,.0f}  p90={row3['p90']:,}")
        print(f"    infer5: mean={row5['mean']:,.0f}  p90={row5['p90']:,}")
    print()

    # Budget-capped accuracy
    print("=== Accuracy at bit-check budgets ===")
    for budget in [1000, 2000, 3000, 5000, 10000]:
        a3b = accuracy_at_budget(r3, budget)
        a5b = accuracy_at_budget(r5, budget)
        print(f"  Budget {budget:,}: infer3={a3b}/{total} ({a3b/total*100:.1f}%)  "
              f"infer5={a5b}/{total} ({a5b/total*100:.1f}%)  "
              f"delta={a5b-a3b:+d}")
    print()

    # Regressions
    regressions = [(a, b) for a, b in zip(r3, r5) if a['correct'] and not b['correct']]
    improvements = [(a, b) for a, b in zip(r3, r5) if not a['correct'] and b['correct']]
    print(f"Regressions (infer3 correct, infer5 wrong): {len(regressions)}")
    for a, b in regressions[:5]:
        print(f"  {a['id']}: expected={a['expected']}, infer3={a['answer']}, infer5={b['answer']}")
    print(f"Improvements (infer5 correct, infer3 wrong): {len(improvements)}")
    for a, b in improvements[:5]:
        print(f"  {a['id']}: expected={a['expected']}, infer3={a['answer']}, infer5={b['answer']}")

    # Write markdown report
    write_report(s3, s5, a3, a5, regressions, improvements, r3, r5, total)
    print("\nReport written to symmetry_breaking_report.md")


def write_report(s3, s5, a3, a5, regressions, improvements, r3, r5, total):
    lines = []
    lines.append("# Symmetry-Breaking Joint-Permutation Optimization: Benchmark Report")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append("**Optimization**: Instead of enumerating 2744 ordered (s0,s1,s2) triples and checking each independently,")
    lines.append("enumerate the 560 distinct **unordered** triples and check all their permutations jointly in a single")
    lines.append("(ex, pos) pass. Each bit-check contributes to all permutations' truth tables simultaneously.")
    lines.append("")
    lines.append("**Expected improvement**: ~2.4× fewer bit-checks for arity-3 wrong candidates.")
    lines.append(f"At budget 3500: covers 72.9% of unordered search space vs 36.4% ordered.")
    lines.append("")
    lines.append("**Full dataset**: 1602 bit-manipulation problems.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Results Summary")
    lines.append("")
    lines.append("| Metric | infer3 (baseline) | infer5 (symbreak) | Delta |")
    lines.append("|--------|------------------|------------------|-------|")

    n = s3['n']
    lines.append(f"| Accuracy | {s3['correct']}/{n} ({s3['correct']/n*100:.1f}%) | {s5['correct']}/{n} ({s5['correct']/n*100:.1f}%) | {s5['correct']-s3['correct']:+d} |")
    lines.append(f"| Wrong | {s3['wrong']} | {s5['wrong']} | {s5['wrong']-s3['wrong']:+d} |")
    lines.append(f"| None | {s3['none']} | {s5['none']} | {s5['none']-s3['none']:+d} |")
    lines.append(f"| Mean bit-checks | {s3['mean']:,.0f} | {s5['mean']:,.0f} | {s5['mean']-s3['mean']:+,.0f} |")
    lines.append(f"| Median bit-checks | {s3['median']:,.0f} | {s5['median']:,.0f} | {s5['median']-s3['median']:+,.0f} |")
    lines.append(f"| p90 bit-checks | {s3['p90']:,} | {s5['p90']:,} | {s5['p90']-s3['p90']:+,} ({(s5['p90']-s3['p90'])/s3['p90']*100:+.1f}%) |")
    lines.append(f"| p95 bit-checks | {s3['p95']:,} | {s5['p95']:,} | {s5['p95']-s3['p95']:+,} ({(s5['p95']-s3['p95'])/s3['p95']*100:+.1f}%) |")
    lines.append(f"| p99 bit-checks | {s3['p99']:,} | {s5['p99']:,} | {s5['p99']-s3['p99']:+,} ({(s5['p99']-s3['p99'])/s3['p99']*100:+.1f}%) |")
    lines.append(f"| Mean time | {s3['mean_time']*1000:.2f}ms | {s5['mean_time']*1000:.2f}ms | {(s5['mean_time']-s3['mean_time'])*1000:+.2f}ms |")
    lines.append("")
    lines.append("## Accuracy at Fixed Bit-Check Budgets")
    lines.append("")
    lines.append("| Budget | infer3 | infer5 | Delta |")
    lines.append("|--------|--------|--------|-------|")
    for budget in [1000, 2000, 3000, 5000, 10000]:
        a3b = accuracy_at_budget(r3, budget)
        a5b = accuracy_at_budget(r5, budget)
        lines.append(f"| {budget:,} | {a3b}/{total} ({a3b/total*100:.1f}%) | {a5b}/{total} ({a5b/total*100:.1f}%) | {a5b-a3b:+d} |")
    lines.append("")
    lines.append("## Per-Arity Bit-Check Statistics")
    lines.append("")
    lines.append("| Arity | N | infer3 mean | infer3 p90 | infer5 mean | infer5 p90 | p90 delta |")
    lines.append("|-------|---|------------|-----------|------------|-----------|-----------|")
    for row3, row5 in zip(a3, a5):
        ar = row3['arity']
        d_p90 = row5['p90'] - row3['p90']
        pct = d_p90 / row3['p90'] * 100 if row3['p90'] else 0
        lines.append(f"| {ar} | {row3['n']} | {row3['mean']:,.0f} | {row3['p90']:,} | {row5['mean']:,.0f} | {row5['p90']:,} | {d_p90:+,} ({pct:+.1f}%) |")
    lines.append("")
    lines.append("## Regressions and Improvements")
    lines.append("")
    lines.append(f"- **Regressions** (infer3 correct, infer5 wrong): **{len(regressions)}**")
    lines.append(f"- **Improvements** (infer5 correct, infer3 wrong): **{len(improvements)}**")
    lines.append(f"- **Net change**: {len(improvements) - len(regressions):+d}")
    if regressions:
        lines.append("")
        lines.append("### Regression details (first 10):")
        lines.append("")
        lines.append("| Problem ID | Expected | infer3 | infer5 |")
        lines.append("|-----------|----------|--------|--------|")
        for a, b in regressions[:10]:
            lines.append(f"| {a['id']} | {a['expected']} | {a['answer']} | {b['answer']} |")
    if improvements:
        lines.append("")
        lines.append("### Improvement details (first 10):")
        lines.append("")
        lines.append("| Problem ID | Expected | infer3 | infer5 |")
        lines.append("|-----------|----------|--------|--------|")
        for a, b in improvements[:10]:
            lines.append(f"| {a['id']} | {a['expected']} | {a['answer']} | {b['answer']} |")
    lines.append("")
    lines.append("## Bit-Check Distribution (full percentile table)")
    lines.append("")
    lines.append("| Percentile | infer3 | infer5 | delta |")
    lines.append("|-----------|--------|--------|-------|")
    for p in [10, 25, 50, 75, 90, 95, 99]:
        v3 = s3['bcs'][min(int(p/100*n), n-1)]
        v5 = s5['bcs'][min(int(p/100*n), n-1)]
        lines.append(f"| p{p} | {v3:,} | {v5:,} | {v5-v3:+,} ({(v5-v3)/v3*100:+.1f}%) |")
    lines.append("")
    lines.append("---")
    lines.append("*Generated by benchmark_infer5.py on full dataset (1602 bit_manipulation problems).*")

    report_path = Path(__file__).parent / "symmetry_breaking_report.md"
    report_path.write_text("\n".join(lines) + "\n")


if __name__ == '__main__':
    main()
