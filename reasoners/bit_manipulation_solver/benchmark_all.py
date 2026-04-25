"""
Benchmark all 5 solvers on the first 300 bit_manipulation problems.
No budget limits. No ablation (n_ex_limit disabled in v4 run here by using
its default, but v4's feature is just noted; v5 uses no example limit).
"""

import sys
import time
from pathlib import Path
from statistics import median, mean

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from reasoners.store_types import Problem
import reasoners.bit_manipulation_solver.bit_solver_v1_base    as v1
import reasoners.bit_manipulation_solver.bit_solver_v2_vsids   as v2
import reasoners.bit_manipulation_solver.bit_solver_v3_freqord as v3
import reasoners.bit_manipulation_solver.bit_solver_v4_exlimit as v4
import reasoners.bit_manipulation_solver.bit_solver_v5_symbreak as v5

SOLVERS = [
    ("v1_base",    v1,  {}),
    ("v2_vsids",   v2,  {}),
    ("v3_freqord", v3,  {}),
    ("v4_exlimit", v4,  {"n_ex_limit": 0}),   # 0 = use all examples (disabled)
    ("v5_symbreak",v5,  {}),
]


def _norm(s: str) -> list[int]:
    bits = [c for c in s if c in '01']
    return [int(b) for b in bits] if len(bits) == 8 else []


def main():
    print("Loading problems...")
    all_problems = Problem.load_all()
    problems = [p for p in all_problems if p.category == 'bit_manipulation'][:300]
    print(f"Running {len(SOLVERS)} solvers on {len(problems)} problems.\n")

    results = {name: [] for name, *_ in SOLVERS}

    for i, p in enumerate(problems):
        if i % 100 == 0:
            print(f"  {i}/{len(problems)}...", flush=True)
        in_arrays   = [_norm(ex.input_value)  for ex in p.examples]
        out_arrays  = [_norm(ex.output_value) for ex in p.examples]
        target_bits = _norm(p.question)
        if any(len(a) != 8 for a in in_arrays + out_arrays) or len(target_bits) != 8:
            continue
        expected = p.answer.strip()

        for name, mod, kwargs in SOLVERS:
            t0 = time.perf_counter()
            ans, bc, ri = mod.find_rule(in_arrays, out_arrays, target_bits, **kwargs)
            elapsed = time.perf_counter() - t0
            results[name].append({
                'id': p.id, 'expected': expected, 'answer': ans,
                'correct': ans == expected, 'bc': bc, 'time': elapsed,
                'arity': ri[0] if ri else None,
            })

    print()
    header = f"{'Solver':<14} {'Acc':>10} {'Wrong':>6} {'None':>5} {'Mean BC':>9} {'p50':>7} {'p90':>7} {'p95':>7} {'p99':>8} {'ms/q':>6}"
    print(header)
    print("-" * len(header))

    for name, _, _ in SOLVERS:
        r = results[name]
        n = len(r)
        correct  = sum(1 for x in r if x['correct'])
        wrong    = sum(1 for x in r if x['answer'] is not None and not x['correct'])
        none_cnt = sum(1 for x in r if x['answer'] is None)
        bcs = sorted(x['bc'] for x in r)
        def pct(p): return bcs[min(int(p/100*n), n-1)]
        ms = mean(x['time'] for x in r) * 1000
        print(f"{name:<14} {correct:>4}/{n:<5} {wrong:>6} {none_cnt:>5} "
              f"{mean(bcs):>9,.0f} {pct(50):>7,} {pct(90):>7,} {pct(95):>7,} {pct(99):>8,} {ms:>6.2f}")

    print()
    print("=== Per-arity p90 bit-checks ===")
    arity_header = f"{'Solver':<14}" + "".join(f"  a{a}-p90" for a in range(4))
    print(arity_header)
    print("-" * len(arity_header))
    for name, _, _ in SOLVERS:
        r = results[name]
        row = f"{name:<14}"
        for arity in range(4):
            sub = sorted(x['bc'] for x in r if x['arity'] == arity)
            if sub:
                n = len(sub)
                p90 = sub[min(int(0.9*n), n-1)]
                row += f"  {p90:>7,}"
            else:
                row += f"  {'—':>7}"
        print(row)

    print()
    print("=== Accuracy at bit-check budgets ===")
    budgets = [1000, 2000, 3000, 5000, 10000]
    bud_header = f"{'Solver':<14}" + "".join(f"  @{b//1000}K" for b in budgets)
    print(bud_header)
    print("-" * len(bud_header))
    for name, _, _ in SOLVERS:
        r = results[name]
        n = len(r)
        row = f"{name:<14}"
        for b in budgets:
            cnt = sum(1 for x in r if x['correct'] and x['bc'] <= b)
            row += f"  {cnt/n*100:>4.1f}%"
        print(row)


if __name__ == '__main__':
    main()
