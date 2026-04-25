"""
Ablation study: accuracy vs. bit_check budget, n_examples, n_bits_per_example.

Each ablation varies one dimension while holding others at maximum.
Results written to ablation_report.md.
"""

import sys
import time
from pathlib import Path
from statistics import mean, median

import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from reasoners.store_types import Problem
import bit_solver_infer as infer_mod


def _norm(s: str) -> list[int]:
    bits = [c for c in s if c in '01']
    return [int(b) for b in bits] if len(bits) == 8 else []


def load_problems():
    all_problems = Problem.load_all()
    problems = [p for p in all_problems if p.category == 'bit_manipulation']
    problems = problems[:300]
    valid = []
    for p in problems:
        in_arrays = [_norm(ex.input_value) for ex in p.examples]
        out_arrays = [_norm(ex.output_value) for ex in p.examples]
        target_bits = _norm(p.question)
        if any(len(a) != 8 for a in in_arrays + out_arrays) or len(target_bits) != 8:
            continue
        valid.append({
            'id': p.id,
            'expected': p.answer.strip(),
            'in_arrays': in_arrays,
            'out_arrays': out_arrays,
            'target_bits': target_bits,
            'n_examples': len(in_arrays),
        })
    return valid


# ── Ablation 1: bit-check budget ─────────────────────────────────────────────
# Run full solver, then simulate budget cutoff post-hoc.

def run_full(problems):
    results = []
    for prob in tqdm.tqdm(problems, desc='Full run'):
        answer, bit_checks, rule_info = infer_mod.find_rule(
            prob['in_arrays'], prob['out_arrays'], prob['target_bits']
        )
        results.append({
            'id': prob['id'],
            'expected': prob['expected'],
            'answer': answer,
            'bit_checks': bit_checks,
            'correct': (answer == prob['expected']),
            'arity': rule_info[0] if rule_info else None,
            'n_examples': prob['n_examples'],
        })
    return results


def ablation_budget(full_results, budgets):
    rows = []
    n = len(full_results)
    for budget in budgets:
        correct = wrong = none_ = 0
        for r in full_results:
            if r['bit_checks'] > budget:
                none_ += 1
            elif r['correct']:
                correct += 1
            else:
                wrong += 1
        rows.append({'budget': budget, 'correct': correct, 'wrong': wrong,
                     'none': none_, 'n': n, 'acc': correct / n * 100})
    return rows


# ── Ablation 2: n_examples ────────────────────────────────────────────────────

def ablation_examples(problems, counts):
    rows = []
    n = len(problems)
    for k in counts:
        correct = wrong = none_ = 0
        for prob in tqdm.tqdm(problems, desc=f'examples={k}', leave=False):
            in_k = prob['in_arrays'][:k]
            out_k = prob['out_arrays'][:k]
            if not in_k:
                none_ += 1
                continue
            answer, _, _ = infer_mod.find_rule(in_k, out_k, prob['target_bits'])
            if answer is None:
                none_ += 1
            elif answer == prob['expected']:
                correct += 1
            else:
                wrong += 1
        rows.append({'k': k, 'correct': correct, 'wrong': wrong,
                     'none': none_, 'n': n, 'acc': correct / n * 100})
    return rows


# ── Ablation 3: n_bits per example ───────────────────────────────────────────
# We expose a limited check_order to find_rule by monkey-patching the
# module-level n_ex × pos iteration. Cleanest approach: inline a restricted
# find_rule that only allows pos < max_bits.

from bit_solver_infer import _TRANS_BYTES, TRANSFORMATIONS, _S_REP, _S_OPTIONS, _apply_inferred


def find_rule_limited_bits(in_arrays, out_arrays, target_bits, max_bits: int):
    """find_rule with check_order restricted to pos < max_bits."""
    in_bytes = [sum(r[i] << (7 - i) for i in range(8)) for r in in_arrays]
    out_bytes = [sum(r[i] << (7 - i) for i in range(8)) for r in out_arrays]
    target_byte = sum(target_bits[i] << (7 - i) for i in range(8))
    n_ex = len(in_bytes)
    check_order = [(ex, pos) for pos in range(max_bits) for ex in range(n_ex)]
    bit_checks = 0

    # arity 0
    ref = out_bytes[0]
    if all(b == ref for b in out_bytes):
        return format(ref, '08b'), bit_checks, (0, ref, [])

    # arity 1
    for t0_idx in range(len(TRANSFORMATIONS)):
        tb0 = _TRANS_BYTES[t0_idx]
        inferred: list[int] = [-1, -1]
        contradiction = False
        for ex, pos in check_order:
            bit_checks += 1
            slot = (tb0[in_bytes[ex]] >> (7 - pos)) & 1
            expected = (out_bytes[ex] >> (7 - pos)) & 1
            if inferred[slot] == -1:
                inferred[slot] = expected
            elif inferred[slot] != expected:
                contradiction = True
                break
        if contradiction:
            continue
        answer = _apply_inferred(inferred, [tb0], target_byte)
        if answer is not None:
            return answer, bit_checks, (1, 0, [TRANSFORMATIONS[t0_idx]])

    # arity 2 (signed-offset)
    for s0 in range(-7, 8):
        rep0 = _TRANS_BYTES[_S_REP[s0]]
        for s1 in range(-7, 8):
            rep1 = _TRANS_BYTES[_S_REP[s1]]
            lo = max((abs(s) for s in (s0, s1) if s < 0), default=0)
            hi = max((s for s in (s0, s1) if s > 0), default=0)
            p1: list[int] = [-1, -1, -1, -1]
            p1_fail = False
            for pos in range(lo, min(8 - hi, max_bits)):
                if p1_fail:
                    break
                for ex in range(n_ex):
                    a = (rep0[in_bytes[ex]] >> (7 - pos)) & 1
                    b = (rep1[in_bytes[ex]] >> (7 - pos)) & 1
                    slot = a | (b << 1)
                    bit_checks += 1
                    expected = (out_bytes[ex] >> (7 - pos)) & 1
                    if p1[slot] == -1:
                        p1[slot] = expected
                    elif p1[slot] != expected:
                        p1_fail = True
                        break
            if p1_fail:
                continue
            ambig_order = [
                (ex, pos)
                for pos in range(max_bits)
                if pos < lo or pos >= 8 - hi
                for ex in range(n_ex)
            ]
            for i0 in _S_OPTIONS[s0]:
                tb0 = _TRANS_BYTES[i0]
                for i1 in _S_OPTIONS[s1]:
                    if i1 == i0:
                        continue
                    tb1 = _TRANS_BYTES[i1]
                    inferred = list(p1)
                    contradiction = False
                    for ex, pos in ambig_order:
                        bit_checks += 1
                        a = (tb0[in_bytes[ex]] >> (7 - pos)) & 1
                        b = (tb1[in_bytes[ex]] >> (7 - pos)) & 1
                        slot = a | (b << 1)
                        expected = (out_bytes[ex] >> (7 - pos)) & 1
                        if inferred[slot] == -1:
                            inferred[slot] = expected
                        elif inferred[slot] != expected:
                            contradiction = True
                            break
                    if contradiction:
                        continue
                    answer = _apply_inferred(inferred, [tb0, tb1], target_byte)
                    if answer is not None:
                        return answer, bit_checks, (2, 0, [TRANSFORMATIONS[i0], TRANSFORMATIONS[i1]])

    # arity 3 (signed-offset)
    for s0 in range(-7, 8):
        rep0 = _TRANS_BYTES[_S_REP[s0]]
        for s1 in range(-7, 8):
            rep1 = _TRANS_BYTES[_S_REP[s1]]
            for s2 in range(-7, 8):
                rep2 = _TRANS_BYTES[_S_REP[s2]]
                lo = max((abs(s) for s in (s0, s1, s2) if s < 0), default=0)
                hi = max((s for s in (s0, s1, s2) if s > 0), default=0)
                p1 = [-1] * 8
                p1_fail = False
                for pos in range(lo, min(8 - hi, max_bits)):
                    if p1_fail:
                        break
                    for ex in range(n_ex):
                        a = (rep0[in_bytes[ex]] >> (7 - pos)) & 1
                        b = (rep1[in_bytes[ex]] >> (7 - pos)) & 1
                        c = (rep2[in_bytes[ex]] >> (7 - pos)) & 1
                        slot = a | (b << 1) | (c << 2)
                        bit_checks += 1
                        expected = (out_bytes[ex] >> (7 - pos)) & 1
                        if p1[slot] == -1:
                            p1[slot] = expected
                        elif p1[slot] != expected:
                            p1_fail = True
                            break
                if p1_fail:
                    continue
                ambig_order = [
                    (ex, pos)
                    for pos in range(max_bits)
                    if pos < lo or pos >= 8 - hi
                    for ex in range(n_ex)
                ]
                for i0 in _S_OPTIONS[s0]:
                    tb0 = _TRANS_BYTES[i0]
                    for i1 in _S_OPTIONS[s1]:
                        if i1 == i0:
                            continue
                        tb1 = _TRANS_BYTES[i1]
                        for i2 in _S_OPTIONS[s2]:
                            if i2 == i0 or i2 == i1:
                                continue
                            tb2 = _TRANS_BYTES[i2]
                            inferred = list(p1)
                            contradiction = False
                            for ex, pos in ambig_order:
                                bit_checks += 1
                                a = (tb0[in_bytes[ex]] >> (7 - pos)) & 1
                                b = (tb1[in_bytes[ex]] >> (7 - pos)) & 1
                                c = (tb2[in_bytes[ex]] >> (7 - pos)) & 1
                                slot = a | (b << 1) | (c << 2)
                                expected = (out_bytes[ex] >> (7 - pos)) & 1
                                if inferred[slot] == -1:
                                    inferred[slot] = expected
                                elif inferred[slot] != expected:
                                    contradiction = True
                                    break
                            if contradiction:
                                continue
                            answer = _apply_inferred(inferred, [tb0, tb1, tb2], target_byte)
                            if answer is not None:
                                return answer, bit_checks, (3, 0, [TRANSFORMATIONS[i0], TRANSFORMATIONS[i1], TRANSFORMATIONS[i2]])

    return None, bit_checks, None


def ablation_bits(problems, bit_counts):
    rows = []
    n = len(problems)
    for k in bit_counts:
        correct = wrong = none_ = 0
        for prob in tqdm.tqdm(problems, desc=f'bits={k}', leave=False):
            answer, _, _ = find_rule_limited_bits(
                prob['in_arrays'], prob['out_arrays'], prob['target_bits'], max_bits=k
            )
            if answer is None:
                none_ += 1
            elif answer == prob['expected']:
                correct += 1
            else:
                wrong += 1
        rows.append({'k': k, 'correct': correct, 'wrong': wrong,
                     'none': none_, 'n': n, 'acc': correct / n * 100})
    return rows


def fmt_row_budget(r):
    return f"| {r['budget']:>10,} | {r['correct']:>7} | {r['wrong']:>5} | {r['none']:>6} | {r['acc']:>8.1f}% |"


def fmt_row_k(r, key):
    return f"| {r[key]:>6} | {r['correct']:>7} | {r['wrong']:>5} | {r['none']:>6} | {r['acc']:>8.1f}% |"


def main():
    print("Loading problems...")
    problems = load_problems()
    print(f"Loaded {len(problems)} problems.")

    # ── Full run for budget ablation ─────────────────────────────────────────
    print("\nRunning full solver (for budget ablation)...")
    full_results = run_full(problems)

    bc_sorted = sorted(r['bit_checks'] for r in full_results)
    n = len(bc_sorted)
    quantiles = {f'p{int(q*100)}': bc_sorted[min(int(q * n), n-1)]
                 for q in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]}

    budgets = sorted(set([
        50, 100, 200, 500, 1_000, 2_000, 5_000, 10_000,
        20_000, 50_000, 100_000, 999_999_999,
    ]))
    budget_rows = ablation_budget(full_results, budgets)

    # ── Examples ablation ────────────────────────────────────────────────────
    max_ex = max(p['n_examples'] for p in problems)
    example_counts = [c for c in [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, max_ex] if c <= max_ex]
    example_counts = sorted(set(example_counts))
    print("\nRunning examples ablation...")
    example_rows = ablation_examples(problems, example_counts)

    # ── Bits ablation ────────────────────────────────────────────────────────
    bit_counts = [1, 2, 3, 4, 5, 6, 7, 8]
    print("\nRunning bits-per-example ablation...")
    bits_rows = ablation_bits(problems, bit_counts)

    # ── Report ───────────────────────────────────────────────────────────────
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    lines = [
        f"# Ablation Study: bit_solver_infer",
        f"",
        f"Date: {now}  ",
        f"Problems: {n}",
        f"",
        f"## 1. Bit-Check Budget",
        f"",
        f"### Bit-check distribution (full run)",
        f"| Percentile | Bit checks |",
        f"|------------|------------|",
    ]
    for k, v in quantiles.items():
        lines.append(f"| {k:>10} | {v:>10,} |")

    lines += [
        f"",
        f"### Accuracy vs budget",
        f"| Budget     | Correct | Wrong | None  | Accuracy |",
        f"|------------|---------|-------|-------|----------|",
    ]
    for r in budget_rows:
        label = f"{r['budget']:,}" if r['budget'] < 999_999_999 else "unlimited"
        lines.append(f"| {label:>10} | {r['correct']:>7} | {r['wrong']:>5} | {r['none']:>6} | {r['acc']:>8.1f}% |")

    lines += [
        f"",
        f"## 2. Number of Examples",
        f"",
        f"(All 8 bits used per example; bit-check budget unlimited)",
        f"",
        f"| Examples | Correct | Wrong | None  | Accuracy |",
        f"|----------|---------|-------|-------|----------|",
    ]
    for r in example_rows:
        lines.append(fmt_row_k(r, 'k'))

    lines += [
        f"",
        f"## 3. Bits per Example",
        f"",
        f"(All examples used; bit-check budget unlimited; only first k bit positions observed)",
        f"",
        f"| Bits | Correct | Wrong | None  | Accuracy |",
        f"|------|---------|-------|-------|----------|",
    ]
    for r in bits_rows:
        lines.append(fmt_row_k(r, 'k'))

    report = "\n".join(lines)
    out_path = Path(__file__).parent / "ablation_report.md"
    out_path.write_text(report)
    print(f"\nReport written to {out_path}")

    # Print summary
    print(f"\n--- Budget ablation ---")
    for r in budget_rows:
        label = f"{r['budget']:>12,}" if r['budget'] < 999_999_999 else "   unlimited"
        print(f"  budget={label}: {r['correct']}/{r['n']} correct ({r['acc']:.1f}%)")

    print(f"\n--- Examples ablation ---")
    for r in example_rows:
        print(f"  examples={r['k']:2d}: {r['correct']}/{r['n']} correct ({r['acc']:.1f}%)")

    print(f"\n--- Bits ablation ---")
    for r in bits_rows:
        print(f"  bits={r['k']}: {r['correct']}/{r['n']} correct ({r['acc']:.1f}%)")


if __name__ == '__main__':
    main()
