"""Debug a specific exhausted puzzle: trace v8's column derivation vs baseline's
brute-force search to find what's being incorrectly pruned."""
from __future__ import annotations
import sys
import time

sys.path.insert(0, '/workspaces/nemotron')

from reasoners.store_types import Problem
from reasoners.cryptarithm_solver.python_solver import (
    extract_all_examples, _search, _plausible_ops, FORMATTERS,
    _syms_for_pipeline, MATH_OPS,
)


def main():
    target_id = sys.argv[1] if len(sys.argv) > 1 else '1785b35e'
    print(f'Debugging puzzle: {target_id}')

    problem = next(p for p in Problem.load_all() if p.id.startswith(target_id))

    print('\n=== PROMPT ===')
    print(problem.prompt)
    print()
    print(f'Expected answer: {problem.answer!r}')

    extraction = extract_all_examples(problem.prompt)
    examples, tA, tB, tgt_op = extraction

    print('\n=== EXAMPLES ===')
    for i, ex in enumerate(examples):
        print(f'  ex{i}: A={ex["A"]} {ex["op"]} B={ex["B"]} = out={ex["out"]}')
    print(f'  target: A={tA} {tgt_op} B={tB} = ?')

    print('\n=== PLAUSIBLE OPS PER EXAMPLE ===')
    for i, ex in enumerate(examples):
        ops = _plausible_ops(ex)
        print(f'  ex{i}: {ops}')

    # Find the golden cipher via baseline search
    print('\n=== BASELINE GOLDEN CIPHER ===')
    for f_type in FORMATTERS:
        plausible = [_plausible_ops(ex) for ex in examples]
        if any(not p for p in plausible):
            continue
        sols = []
        _search(examples, 0, {}, set(), {}, plausible, f_type, sols,
                time.time() + 5.0, max_solutions=1)
        if sols:
            dm, op_assign = sols[0]
            print(f'  formatter: {f_type}')
            print(f'  op_assign: {op_assign}')
            print(f'  digit_map ({len(dm)} syms):')
            for sym, dig in sorted(dm.items()):
                print(f'    {sym!r:>6} -> {dig}')

            # Decode each example to verify
            print('\n  Decoded examples:')
            for ex in examples:
                A0s, A1s, B0s, B1s = _syms_for_pipeline(ex, f_type)
                op_name = op_assign.get(ex['op'])
                a0, a1 = dm.get(A0s), dm.get(A1s)
                b0, b1 = dm.get(B0s), dm.get(B1s)
                if None in (a0, a1, b0, b1):
                    print(f'    ex {ex["A"]}{ex["op"]}{ex["B"]}={ex["out"]}: '
                          f'a0={a0} a1={a1} b0={b0} b1={b1} (some unassigned!)')
                    continue
                L = a0 * 10 + a1
                R = b0 * 10 + b1
                result = MATH_OPS[op_name]['fn'](L, R, 0, 0, 0, 0)
                out_decoded = ''.join(str(dm.get(s, '?')) for s in ex['out'])
                print(f'    {L}({A0s}={a0},{A1s}={a1}) {ex["op"]}({op_name}) '
                      f'{R}({B0s}={b0},{B1s}={b1}) = {result}  '
                      f'[out={ex["out"]} decoded={out_decoded}]')
            break


if __name__ == '__main__':
    main()
