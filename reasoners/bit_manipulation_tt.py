"""Reasoning generator for 8-bit bit-manipulation tasks using the truth-table solver.

Uses the frequency-ordered truth-table enumeration solver (bit_solver_tt) to
find the rule, then generates a step-by-step reasoning trace showing:
  1. The examples
  2. The rule found (grammar expression + transform assignments)
  3. Verification against each example
  4. Application to the query input
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent / "bit_manipulation_solver"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from bit_solver_tt import find_rule as _find_rule_tt, _transform_bit, _apply, KNOWN_FUNCTIONS

from reasoners.store_types import Problem

# Map (arity, tt) → grammar expression string (built once at import time).
_EXPR_MAP: dict[tuple[int, int], str] = {}

def _build_expr_map() -> None:
    from bit_solver import generate_grammar_dynamically

    A, B, C = 0b11110000, 0b11001100, 0b10101010

    def expand(arity: int, tt: int) -> int:
        if arity == 0:
            return 0xFF if tt else 0x00
        result = 0
        for k in range(8):
            a_bit = (A >> (7 - k)) & 1
            b_bit = (B >> (7 - k)) & 1
            c_bit = (C >> (7 - k)) & 1
            bits = [a_bit, b_bit, c_bit]
            idx = sum(bits[i] << i for i in range(arity))
            f_val = (tt >> idx) & 1
            result |= f_val << (7 - k)
        return result

    def describe(node) -> str:
        if node[0] == 'C0':  return '0'
        if node[0] == 'C1':  return '1'
        if node[0] == 'VAR': return node[1]
        if node[0] == 'NOT': return f'NOT({describe(node[1])})'
        if node[0] == 'OP':  return f'({describe(node[2])} {node[1]} {describe(node[3])})'
        return '?'

    target = {}
    for arity, tt, _ in KNOWN_FUNCTIONS:
        gtt = expand(arity, tt)
        target[gtt] = (arity, tt)

    found: set[tuple[int, int]] = set()
    for gtt, node in generate_grammar_dynamically():
        if gtt in target:
            key = target[gtt]
            if key not in found:
                _EXPR_MAP[key] = describe(node)
                found.add(key)
        if len(found) == len(target):
            break

_build_expr_map()


def _trans_name(trans: tuple) -> str:
    ttype, k = trans
    if ttype == 'rot' and k == 0:
        return 'identity'
    return f'{ttype}({k})'


def _apply_trans_byte(in_bits: list[int], trans: tuple) -> str:
    """Apply a transform to an 8-bit list and return the 8-bit result string."""
    ttype, k = trans
    result = []
    for pos in range(8):
        result.append(str(_transform_bit(
            sum(in_bits[i] << (7 - i) for i in range(8)),
            ttype, k, pos
        )))
    return ''.join(result)


def reasoning_bit_manipulation_tt(problem: Problem, solver=_find_rule_tt) -> Optional[str]:
    examples = problem.examples
    if not examples:
        return None

    def norm(s: str) -> list[int]:
        bits = [c for c in s if c in '01']
        return [int(b) for b in bits] if len(bits) == 8 else []

    in_arrays  = [norm(ex.input_value)  for ex in examples]
    out_arrays = [norm(ex.output_value) for ex in examples]
    target_bits = norm(problem.question)

    if any(len(a) != 8 for a in in_arrays + out_arrays) or len(target_bits) != 8:
        return None

    answer, bit_checks, rule_info = solver(in_arrays, out_arrays, target_bits)
    if answer is None:
        return None

    arity, tt, ordered_trans = rule_info
    var_names = ['{A}', '{B}', '{C}']
    expr_template = _EXPR_MAP.get((arity, tt), f'tt={tt}')

    # Substitute variable names with actual transform names in expression
    expr_concrete = expr_template
    for i, trans in enumerate(ordered_trans):
        expr_concrete = expr_concrete.replace(var_names[i], _trans_name(trans))

    lines: list[str] = []
    lines.append("We need to deduce the transformation by matching the example outputs.")
    lines.append("I will put my final answer inside \\boxed{}.")
    lines.append("")

    # Show examples
    for i, (inp, out) in enumerate(zip(in_arrays, out_arrays)):
        lines.append(f"Example {i}: {''.join(map(str, inp))} -> {''.join(map(str, out))}")
    lines.append("")

    # Show found rule
    lines.append(f"Searching {len(KNOWN_FUNCTIONS)} known boolean functions in frequency order.")
    lines.append(f"Bit checks used: {bit_checks:,}")
    lines.append("")
    if arity == 0:
        lines.append(f"Rule found: constant {'1' if tt else '0'}")
    else:
        lines.append(f"Rule found: {expr_template}")
        for i, trans in enumerate(ordered_trans):
            lines.append(f"  {var_names[i]} = {_trans_name(trans)}")
        lines.append(f"Instantiated: {expr_concrete}")
    lines.append("")

    # Verify against examples
    lines.append("Verification:")
    for i, (inp, out) in enumerate(zip(in_arrays, out_arrays)):
        inp_str = ''.join(map(str, inp))
        out_str = ''.join(map(str, out))
        if arity == 0:
            pred = '1' * 8 if tt else '0' * 8
            lines.append(f"  Example {i}: {inp_str} -> {pred} (expected {out_str}) {'✓' if pred == out_str else '✗'}")
        else:
            trans_strs = [_apply_trans_byte(inp, t) for t in ordered_trans]
            trans_display = ', '.join(
                f"{_trans_name(t)}={s}" for t, s in zip(ordered_trans, trans_strs)
            )
            pred = _apply(tt, arity, ordered_trans,
                          sum(inp[j] << (7 - j) for j in range(8)))
            lines.append(f"  Example {i}: {trans_display} -> {pred} (expected {out_str}) {'✓' if pred == out_str else '✗'}")
    lines.append("")

    # Apply to query
    query_str = ''.join(map(str, target_bits))
    lines.append(f"Applying to query: {query_str}")
    if arity == 0:
        lines.append(f"  Result: {answer}")
    else:
        trans_strs = [_apply_trans_byte(target_bits, t) for t in ordered_trans]
        for i, (trans, ts) in enumerate(zip(ordered_trans, trans_strs)):
            lines.append(f"  {var_names[i]} = {_trans_name(trans)}({query_str}) = {ts}")
        lines.append(f"  {expr_concrete} = {answer}")
    lines.append("")
    lines.append("I will now return the answer in \\boxed{}")
    lines.append(f"The answer in \\boxed{{-}} is \\boxed{{{answer}}}")

    return "\n".join(lines)
