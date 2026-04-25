"""
Benchmark: bit_solver_perbit vs bit_solver_infer

Runs both solvers on 300 bit_manipulation problems, compares accuracy,
runtime, and bit-check counts, then writes a markdown report.
"""

import sys
import time
from pathlib import Path
from statistics import median, mean

import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from reasoners.store_types import Problem
import bit_solver_infer     as infer_mod
import bit_solver_perbit    as perbit_mod
import bit_solver_perbit_v2 as perbit_v2_mod


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
    problems = [p for p in all_problems if p.category == 'bit_manipulation'][:300]
    print(f"Benchmarking on {len(problems)} problems.")

    infer_results    = []
    perbit_results   = []
    perbit_v2_results = []

    for p in tqdm.tqdm(problems):
        in_arrays   = [_norm(ex.input_value)  for ex in p.examples]
        out_arrays  = [_norm(ex.output_value) for ex in p.examples]
        target_bits = _norm(p.question)
        if any(len(a) != 8 for a in in_arrays + out_arrays) or len(target_bits) != 8:
            continue
        expected = p.answer.strip()

        ans_inf,  bc_inf,  ri_inf,  t_inf  = run_solver(infer_mod,     in_arrays, out_arrays, target_bits)
        ans_pb,   bc_pb,   ri_pb,   t_pb   = run_solver(perbit_mod,    in_arrays, out_arrays, target_bits)
        ans_pb2,  bc_pb2,  ri_pb2,  t_pb2  = run_solver(perbit_v2_mod, in_arrays, out_arrays, target_bits)

        infer_results.append({
            'id': p.id, 'expected': expected, 'answer': ans_inf,
            'correct': ans_inf == expected, 'time': t_inf, 'bit_checks': bc_inf,
            'rule_info': ri_inf,
        })
        perbit_results.append({
            'id': p.id, 'expected': expected, 'answer': ans_pb,
            'correct': ans_pb == expected, 'time': t_pb, 'bit_checks': bc_pb,
            'rule_info': ri_pb,
        })
        perbit_v2_results.append({
            'id': p.id, 'expected': expected, 'answer': ans_pb2,
            'correct': ans_pb2 == expected, 'time': t_pb2, 'bit_checks': bc_pb2,
            'rule_info': ri_pb2,
        })

    def stats(results):
        n = len(results)
        correct  = sum(1 for r in results if r['correct'])
        wrong    = sum(1 for r in results if r['answer'] is not None and not r['correct'])
        none_cnt = sum(1 for r in results if r['answer'] is None)
        times = [r['time'] for r in results]
        bcs   = [r['bit_checks'] for r in results]
        buckets = {'<0.1s': 0, '0.1-1s': 0, '1-5s': 0, '5-15s': 0, '>=15s': 0}
        for t in times:
            if   t < 0.1:   buckets['<0.1s']   += 1
            elif t < 1.0:   buckets['0.1-1s']  += 1
            elif t < 5.0:   buckets['1-5s']    += 1
            elif t < 15.0:  buckets['5-15s']   += 1
            else:           buckets['>=15s']   += 1
        percentiles = {}
        sorted_bcs = sorted(bcs)
        for p_val in [10, 25, 50, 75, 90, 95, 99]:
            idx = int(p_val / 100 * n)
            percentiles[p_val] = sorted_bcs[min(idx, n-1)]
        return {
            'n': n, 'correct': correct, 'wrong': wrong, 'none': none_cnt,
            'acc': correct / n * 100,
            'min_t': min(times), 'max_t': max(times), 'mean_t': mean(times), 'median_t': median(times),
            'min_bc': min(bcs), 'max_bc': max(bcs), 'mean_bc': mean(bcs), 'median_bc': median(bcs),
            'buckets': buckets, 'percentiles': percentiles,
        }

    si  = stats(infer_results)
    sp  = stats(perbit_results)
    sp2 = stats(perbit_v2_results)

    def disagree_table(ra, rb, label_a, label_b):
        d   = [(a, b) for a, b in zip(ra, rb) if a['answer'] != b['answer']]
        a_r = [(a, b) for a, b in d if  a['correct'] and not b['correct']]
        b_r = [(a, b) for a, b in d if not a['correct'] and  b['correct']]
        bw  = [(a, b) for a, b in d if not a['correct'] and not b['correct']]
        return d, a_r, b_r, bw

    d_ip,  ir_pw,  iw_pr,  bw_ip  = disagree_table(infer_results, perbit_results,    'infer', 'perbit_v1')
    d_ip2, ir_pw2, iw_pr2, bw_ip2 = disagree_table(infer_results, perbit_v2_results, 'infer', 'perbit_v2')

    now = time.strftime('%Y-%m-%d %H:%M:%S')
    lines = [
        f"# Benchmark: Per-Bit Solvers vs Infer Solver",
        f"",
        f"Date: {now}  ",
        f"Problems: {si['n']}  ",
        f"",
        f"## 1. Accuracy",
        f"| Outcome | infer | perbit v1 | perbit v2 (evidence-driven) |",
        f"|---------|-------|-----------|------------------------------|",
        f"| Correct | {si['correct']} ({si['acc']:.1f}%) | {sp['correct']} ({sp['acc']:.1f}%) | {sp2['correct']} ({sp2['acc']:.1f}%) |",
        f"| Wrong   | {si['wrong']} | {sp['wrong']} | {sp2['wrong']} |",
        f"| None    | {si['none']} | {sp['none']} | {sp2['none']} |",
        f"",
        f"## 2. Runtime (seconds)",
        f"| Metric | infer | perbit v1 | perbit v2 |",
        f"|--------|-------|-----------|-----------|",
        f"| Min    | {si['min_t']:.4f} | {sp['min_t']:.4f} | {sp2['min_t']:.4f} |",
        f"| Max    | {si['max_t']:.4f} | {sp['max_t']:.4f} | {sp2['max_t']:.4f} |",
        f"| Mean   | {si['mean_t']:.4f} | {sp['mean_t']:.4f} | {sp2['mean_t']:.4f} |",
        f"| Median | {si['median_t']:.4f} | {sp['median_t']:.4f} | {sp2['median_t']:.4f} |",
        f"",
        f"### Runtime distribution",
        f"| Bucket | infer | perbit v1 | perbit v2 |",
        f"|--------|-------|-----------|-----------|",
    ]
    for b in ['<0.1s', '0.1-1s', '1-5s', '5-15s', '>=15s']:
        lines.append(f"| {b} | {si['buckets'][b]} | {sp['buckets'][b]} | {sp2['buckets'][b]} |")

    lines += [
        f"",
        f"## 3. Bit Checks",
        f"| Metric | infer | perbit v1 | perbit v2 |",
        f"|--------|-------|-----------|-----------|",
        f"| Min    | {si['min_bc']:,} | {sp['min_bc']:,} | {sp2['min_bc']:,} |",
        f"| Max    | {si['max_bc']:,} | {sp['max_bc']:,} | {sp2['max_bc']:,} |",
        f"| Mean   | {si['mean_bc']:,.0f} | {sp['mean_bc']:,.0f} | {sp2['mean_bc']:,.0f} |",
        f"| Median | {si['median_bc']:,.0f} | {sp['median_bc']:,.0f} | {sp2['median_bc']:,.0f} |",
        f"",
        f"### Bit-check percentiles",
        f"| Percentile | infer | perbit v1 | perbit v2 |",
        f"|-----------|-------|-----------|-----------|",
    ]
    for pct in [10, 25, 50, 75, 90, 95, 99]:
        lines.append(f"| p{pct} | {si['percentiles'][pct]:,} | {sp['percentiles'][pct]:,} | {sp2['percentiles'][pct]:,} |")

    lines += [
        f"",
        f"## 4. Infer vs Perbit v2 Disagreements (total: {len(d_ip2)})",
        f"",
        f"- Infer correct, perbit v2 wrong: **{len(ir_pw2)}**",
        f"- Infer wrong, perbit v2 correct: **{len(iw_pr2)}**",
        f"- Both wrong: **{len(bw_ip2)}**",
    ]
    if iw_pr2:
        lines += [f"", f"### Infer wrong, perbit v2 correct",
                  f"| Problem ID | Expected | infer | perbit v2 |",
                  f"|------------|----------|-------|-----------|"]
        for r_i, r_p in iw_pr2:
            lines.append(f"| {r_i['id']} | {r_i['expected']} | {r_i['answer']} | {r_p['answer']} |")
    if ir_pw2:
        lines += [f"", f"### Infer correct, perbit v2 wrong",
                  f"| Problem ID | Expected | infer | perbit v2 |",
                  f"|------------|----------|-------|-----------|"]
        for r_i, r_p in ir_pw2[:20]:  # cap at 20 rows
            lines.append(f"| {r_i['id']} | {r_i['expected']} | {r_i['answer']} | {r_p['answer']} |")
        if len(ir_pw2) > 20:
            lines.append(f"| ... | ({len(ir_pw2)-20} more) | | |")
    if bw_ip2:
        lines += [f"", f"### Both solvers wrong",
                  f"| Problem ID | Expected | infer | perbit v2 |",
                  f"|------------|----------|-------|-----------|"]
        for r_i, r_p in bw_ip2:
            lines.append(f"| {r_i['id']} | {r_i['expected']} | {r_i['answer']} | {r_p['answer']} |")

    none_v2 = [r for r in perbit_v2_results if r['answer'] is None]
    if none_v2:
        lines += [f"", f"### Perbit v2 returned None",
                  f"| Problem ID | Expected |", f"|------------|----------|"]
        for r in none_v2:
            lines.append(f"| {r['id']} | {r['expected']} |")

    report = "\n".join(lines)
    out_path = Path(__file__).parent / "benchmark_perbit_report.md"
    out_path.write_text(report)
    print(f"\nReport written to {out_path}")
    print(f"\nSummary:")
    print(f"  Infer:     {si['correct']}/{si['n']} ({si['acc']:.1f}%), mean {si['mean_t']:.4f}s")
    print(f"  Perbit v1: {sp['correct']}/{sp['n']} ({sp['acc']:.1f}%), mean {sp['mean_t']:.4f}s")
    print(f"  Perbit v2: {sp2['correct']}/{sp2['n']} ({sp2['acc']:.1f}%), mean {sp2['mean_t']:.4f}s")
    print(f"  v2 vs infer — infer wins: {len(ir_pw2)}, v2 wins: {len(iw_pr2)}")


if __name__ == '__main__':
    main()
