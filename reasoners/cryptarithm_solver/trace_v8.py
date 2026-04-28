"""Trace v8's search by pre-assigning the golden cipher and verifying acceptance."""
from __future__ import annotations
import sys
import time

sys.path.insert(0, '/workspaces/nemotron')

from reasoners.store_types import Problem
from reasoners.cryptarithm_solver.python_solver import (
    extract_all_examples, _search, _plausible_ops, FORMATTERS,
    _syms_for_pipeline, MATH_OPS,
)
from reasoners.cryptarithm_solver.python_solver_arith_full import (
    _search_constrained, SUPPORTED_OPS, OP_ORDER,
)
from reasoners.cryptarithm_solver.python_solver_prefilter import (
    _precompute_op_constraints, _reorder_examples,
)


def main():
    target_id = sys.argv[1] if len(sys.argv) > 1 else '1785b35e'
    problem = next(p for p in Problem.load_all() if p.id.startswith(target_id))

    extraction = extract_all_examples(problem.prompt)
    examples, tA, tB, tgt_op = extraction

    # Find golden cipher via baseline
    golden_dm, golden_op_assign, f_type = None, None, None
    for ft in FORMATTERS:
        plausible = [_plausible_ops(ex) for ex in examples]
        sols = []
        _search(examples, 0, {}, set(), {}, plausible, ft, sols,
                time.time() + 5.0, max_solutions=1)
        if sols:
            golden_dm, golden_op_assign = sols[0]
            f_type = ft
            break

    print(f'Golden formatter: {f_type}')
    print(f'Golden op_assign: {golden_op_assign}')
    print(f'Golden digit_map: {sorted(golden_dm.items())}')

    # Filter examples like v8 does
    filtered = [ex for ex in examples
                if set(_plausible_ops(ex)) & SUPPORTED_OPS]
    op_constraints = _precompute_op_constraints(filtered)

    # Build plausible_per_ex like v8
    reordered = _reorder_examples(filtered, f_type)
    print(f'\nReordered example order:')
    for i, ex in enumerate(reordered):
        print(f'  ex{i}: A={ex["A"]} {ex["op"]} B={ex["B"]} = out={ex["out"]}')

    plausible_per_ex = []
    for ex in reordered:
        sym = ex['op']
        cands = [o for o in op_constraints.get(sym, OP_ORDER)
                 if o in SUPPORTED_OPS]
        plausible_per_ex.append(cands)

    print(f'\nPlausible ops per (reordered) example:')
    for i, cands in enumerate(plausible_per_ex):
        op_sym = reordered[i]['op']
        golden_op = golden_op_assign.get(op_sym)
        contains = '✓' if golden_op in cands else '✗'
        print(f'  ex{i} ({op_sym}): {cands}  golden={golden_op} {contains}')

    # Now: starting from golden cipher, run v8's search and see if it accepts.
    print(f'\n=== Running v8 _search_constrained with golden cipher pre-assigned ===')
    sols = []
    _search_constrained(reordered, 0, dict(golden_dm), set(golden_dm.values()),
                        dict(golden_op_assign), plausible_per_ex, f_type,
                        sols, time.time() + 5.0, max_solutions=1)
    print(f'Solutions found: {len(sols)}')
    if sols:
        print('  v8 ACCEPTS the golden cipher when pre-assigned ✓')
    else:
        print('  v8 REJECTS the golden cipher (column-derivation bug)')

    # Run v8 from scratch and see
    print(f'\n=== Running v8 _search_constrained from empty state ===')
    sols2 = []
    _search_constrained(reordered, 0, {}, set(), {}, plausible_per_ex, f_type,
                        sols2, time.time() + 5.0, max_solutions=1)
    print(f'Solutions found: {len(sols2)}')
    if sols2:
        dm, oa = sols2[0]
        print(f'  found op_assign: {oa}')
        print(f'  found digit_map: {sorted(dm.items())}')
    else:
        print('  search exhausted')


if __name__ == '__main__':
    main()
