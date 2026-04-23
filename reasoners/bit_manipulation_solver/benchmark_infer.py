"""
Benchmark: bit_solver_tt  vs  bit_solver_infer

Runs both solvers on all bit_manipulation problems, compares accuracy,
runtime, and bit-check counts, then writes a markdown report.
"""

import sys
import time
from pathlib import Path
from statistics import median, mean

import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from reasoners.store_types import Problem
import bit_solver_tt  as tt_mod
import bit_solver_infer as infer_mod


def _norm(s: str) -> list[int]:
    bits = [c for c in s if c in '01']
    return [int(b) for b in bits] if len(bits) == 8 else []


def run_solver(mod, in_arrays, out_arrays, target_bits):
    t0 = time.perf_counter()
    answer, bit_checks, rule_info = mod.find_rule(in_arrays, out_arrays, target_bits)
    elapsed = time.perf_counter() - t0
    return answer, bit_checks, rule_info, elapsed


def main():
    print("Loading problems...")
    all_problems = Problem.load_all()
    problems = [p for p in all_problems if p.category == 'bit_manipulation']
    problems = problems[:300]
    print(f"Benchmarking on {len(problems)} problems.")

    tt_results    = []
    infer_results = []

    for p in tqdm.tqdm(problems):
        in_arrays   = [_norm(ex.input_value)  for ex in p.examples]
        out_arrays  = [_norm(ex.output_value) for ex in p.examples]
        target_bits = _norm(p.question)

        if any(len(a) != 8 for a in in_arrays + out_arrays) or len(target_bits) != 8:
            continue

        expected = p.answer.strip()

        # TT solver
        ans_tt, bc_tt, ri_tt, t_tt = run_solver(tt_mod, in_arrays, out_arrays, target_bits)
        tt_results.append({
            'id': p.id,
            'expected': expected,
            'answer': ans_tt,
            'correct': (ans_tt == expected),
            'time': t_tt,
            'bit_checks': bc_tt,
            'arity': ri_tt[0] if ri_tt else None,
        })

        # Infer solver
        ans_inf, bc_inf, ri_inf, t_inf = run_solver(infer_mod, in_arrays, out_arrays, target_bits)
        infer_results.append({
            'id': p.id,
            'expected': expected,
            'answer': ans_inf,
            'correct': (ans_inf == expected),
            'time': t_inf,
            'bit_checks': bc_inf,
            'arity': ri_inf[0] if ri_inf else None,
        })

    def stats(results):
        n = len(results)
        correct = sum(1 for r in results if r['correct'])
        wrong   = sum(1 for r in results if r['answer'] is not None and not r['correct'])
        timeout = sum(1 for r in results if r['answer'] is None)
        times   = [r['time'] for r in results]
        bcs     = [r['bit_checks'] for r in results]
        buckets = {'<0.1s': 0, '0.1-0.5s': 0, '0.5-1s': 0, '1-5s': 0, '5-15s': 0, '>=15s': 0}
        for t in times:
            if t < 0.1:     buckets['<0.1s'] += 1
            elif t < 0.5:   buckets['0.1-0.5s'] += 1
            elif t < 1.0:   buckets['0.5-1s'] += 1
            elif t < 5.0:   buckets['1-5s'] += 1
            elif t < 15.0:  buckets['5-15s'] += 1
            else:            buckets['>=15s'] += 1
        return {
            'n': n, 'correct': correct, 'wrong': wrong, 'timeout': timeout,
            'acc': correct / n * 100,
            'min_t': min(times), 'max_t': max(times),
            'mean_t': mean(times), 'median_t': median(times),
            'min_bc': min(bcs), 'max_bc': max(bcs),
            'mean_bc': mean(bcs), 'median_bc': median(bcs),
            'buckets': buckets,
        }

    s_tt    = stats(tt_results)
    s_infer = stats(infer_results)

    # Per-arity breakdown
    def arity_stats(results):
        out = {}
        for r in results:
            ar = r['arity']
            if ar not in out:
                out[ar] = {'n': 0, 'correct': 0, 'times': [], 'bcs': []}
            out[ar]['n'] += 1
            out[ar]['correct'] += r['correct']
            out[ar]['times'].append(r['time'])
            out[ar]['bcs'].append(r['bit_checks'])
        return out

    a_tt    = arity_stats(tt_results)
    a_infer = arity_stats(infer_results)

    # Disagreements
    disagree = [(r_tt, r_inf) for r_tt, r_inf in zip(tt_results, infer_results)
                if r_tt['answer'] != r_inf['answer']]

    # Speed ratio per problem
    speedups = []
    for r_tt, r_inf in zip(tt_results, infer_results):
        if r_inf['time'] > 1e-9:
            speedups.append(r_tt['time'] / r_inf['time'])

    now = time.strftime('%Y-%m-%d %H:%M:%S')
    lines = []

    lines += [
        f"# Benchmark: bit_solver_tt vs bit_solver_infer",
        f"",
        f"Date: {now}  ",
        f"Problems evaluated: {s_tt['n']}",
        f"",
        f"## 1. Accuracy",
        f"| Outcome | tt solver | infer solver |",
        f"|---------|-----------|--------------|",
        f"| Correct        | {s_tt['correct']} ({s_tt['acc']:.1f}%) | {s_infer['correct']} ({s_infer['acc']:.1f}%) |",
        f"| Wrong (solved) | {s_tt['wrong']} | {s_infer['wrong']} |",
        f"| Timed out / None | {s_tt['timeout']} | {s_infer['timeout']} |",
        f"",
        f"## 2. Runtime (seconds)",
        f"| Metric  | tt solver | infer solver | ratio (tt/infer) |",
        f"|---------|-----------|--------------|-----------------|",
        f"| Min     | {s_tt['min_t']:.4f} | {s_infer['min_t']:.4f} | {s_tt['min_t']/(s_infer['min_t']+1e-12):.2f}x |",
        f"| Max     | {s_tt['max_t']:.4f} | {s_infer['max_t']:.4f} | {s_tt['max_t']/(s_infer['max_t']+1e-12):.2f}x |",
        f"| Mean    | {s_tt['mean_t']:.4f} | {s_infer['mean_t']:.4f} | {s_tt['mean_t']/(s_infer['mean_t']+1e-12):.2f}x |",
        f"| Median  | {s_tt['median_t']:.4f} | {s_infer['median_t']:.4f} | {s_tt['median_t']/(s_infer['median_t']+1e-12):.2f}x |",
        f"",
        f"### Runtime distribution",
        f"| Bucket | tt solver | infer solver |",
        f"|--------|-----------|--------------|",
    ]
    for bucket in ['<0.1s', '0.1-0.5s', '0.5-1s', '1-5s', '5-15s', '>=15s']:
        lines.append(f"| {bucket} | {s_tt['buckets'][bucket]} | {s_infer['buckets'][bucket]} |")

    lines += [
        f"",
        f"## 3. Bit Checks",
        f"| Metric  | tt solver | infer solver | ratio (tt/infer) |",
        f"|---------|-----------|--------------|-----------------|",
        f"| Min     | {s_tt['min_bc']:,} | {s_infer['min_bc']:,} | {s_tt['min_bc']/(s_infer['min_bc']+1):.2f}x |",
        f"| Max     | {s_tt['max_bc']:,} | {s_infer['max_bc']:,} | {s_tt['max_bc']/(s_infer['max_bc']+1):.2f}x |",
        f"| Mean    | {s_tt['mean_bc']:,.0f} | {s_infer['mean_bc']:,.0f} | {s_tt['mean_bc']/(s_infer['mean_bc']+1):.2f}x |",
        f"| Median  | {s_tt['median_bc']:,.0f} | {s_infer['median_bc']:,.0f} | {s_tt['median_bc']/(s_infer['median_bc']+1):.2f}x |",
        f"",
        f"## 4. Per-Arity Breakdown",
        f"| Arity | Solver | Count | Acc% | Mean time (s) | Median time (s) | Mean bit_checks |",
        f"|-------|--------|-------|------|---------------|-----------------|-----------------|",
    ]
    for ar in sorted(set(list(a_tt.keys()) + list(a_infer.keys())), key=lambda x: (x is None, x)):
        for label, ad in [('tt', a_tt), ('infer', a_infer)]:
            if ar in ad:
                d = ad[ar]
                acc = d['correct'] / d['n'] * 100
                mt  = mean(d['times'])
                mdt = median(d['times'])
                mbc = mean(d['bcs'])
                lines.append(f"| {ar} | {label} | {d['n']} | {acc:.1f}% | {mt:.4f} | {mdt:.4f} | {mbc:,.0f} |")

    if disagree:
        lines += [
            f"",
            f"## 5. Disagreements Between Solvers ({len(disagree)} problems)",
            f"| Problem ID | Expected | tt answer | infer answer |",
            f"|------------|----------|-----------|--------------|",
        ]
        for r_tt, r_inf in disagree:
            lines.append(f"| {r_tt['id']} | {r_tt['expected']} | {r_tt['answer']} | {r_inf['answer']} |")
    else:
        lines += [f"", f"## 5. Disagreements", f"None — both solvers returned identical answers on all problems."]

    if speedups:
        lines += [
            f"",
            f"## 6. Per-Problem Speedup (tt_time / infer_time)",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Mean speedup   | {mean(speedups):.2f}x |",
            f"| Median speedup | {median(speedups):.2f}x |",
            f"| Max speedup    | {max(speedups):.2f}x |",
            f"| Min speedup    | {min(speedups):.2f}x |",
            f"| Problems where infer is faster | {sum(1 for s in speedups if s > 1)} / {len(speedups)} |",
        ]

    report = "\n".join(lines)

    out_path = Path(__file__).parent / "benchmark_infer_report.md"
    out_path.write_text(report)
    print(f"\nReport written to {out_path}")
    print(f"\nSummary:")
    print(f"  TT solver:    {s_tt['correct']}/{s_tt['n']} correct, mean {s_tt['mean_t']:.4f}s, median {s_tt['median_t']:.4f}s")
    print(f"  Infer solver: {s_infer['correct']}/{s_infer['n']} correct, mean {s_infer['mean_t']:.4f}s, median {s_infer['median_t']:.4f}s")
    if speedups:
        print(f"  Median speedup: {median(speedups):.2f}x, mean: {mean(speedups):.2f}x")


if __name__ == '__main__':
    main()
