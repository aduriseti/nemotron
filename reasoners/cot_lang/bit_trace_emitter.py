"""Emit a flat cotl trace for a bit manipulation problem.

The solver (bit_solver_tt) finds the rule; this module transcribes the
winning execution path as a sequence of atomic cotl instructions.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "bit_manipulation_solver"))

from bit_solver_tt import _make_check_order, solve_bit_manipulation  # noqa: E402

_VAR_LETTERS = ["A", "B", "C"]

_RULE_NAMES: dict[tuple[int, int], str] = {
    (2, 0b0110): "XOR",
    (2, 0b1110): "OR",
    (1, 0b10): "identity",
    (2, 0b1000): "AND",
    (2, 0b0010): "NOT_A_AND_B",
    (2, 0b1001): "XNOR",
    (2, 0b0001): "NOR",
    (2, 0b1011): "A_IMPLIES_B",
    (2, 0b0111): "NAND",
    (1, 0b01): "NOT",
    (0, 0): "CONST_0",
    (0, 1): "CONST_1",
}


def _rule_name(arity: int, tt: int) -> str:
    return _RULE_NAMES.get((arity, tt), f"fn_tt{tt}_ar{arity}")


def _transform_expr(ttype: str, k: int, src: str) -> str:
    if ttype == "rot" and k == 0:
        return src
    if ttype == "rot":
        return f"ROT({src}, {k})"
    if ttype == "shl":
        return f"SHL({src}, {k})"
    # shr
    return f"SHR({src}, {k})"


def _tt_lines(
    tt: int,
    arity: int,
    a: str,
    b: str | None,
    c: str | None,
    got: str,
    tmp: str,
    tt_str_var: str = "$tt_str",
) -> list[str]:
    """Return cotl lines that assign ${got} via truth table applied to input bits."""
    if arity == 0:
        return [f'${got} = "{"1" if tt else "0"}"']

    if arity == 1:
        if tt == 0b10:
            return [f"${got} = {a}"]
        if tt == 0b01:
            return [f"${got} = ~{a}"]

    if arity == 2:
        if tt == 0b0110:
            return [f"${got} = {a} ^ {b}"]
        if tt == 0b1110:
            return [f"${got} = {a} | {b}"]
        if tt == 0b1000:
            return [f"${got} = {a} & {b}"]
        if tt == 0b1001:
            return [f"${tmp}x = {a} ^ {b}", f"${got} = ~${tmp}x"]
        if tt == 0b0001:
            return [f"${tmp}o = {a} | {b}", f"${got} = ~${tmp}o"]
        if tt == 0b0010:
            return [f"${tmp}n = ~{a}", f"${got} = ${tmp}n & {b}"]
        if tt == 0b1011:
            return [f"${tmp}n = ~{a}", f"${got} = ${tmp}n | {b}"]
        if tt == 0b0111:
            return [f"${tmp}a = {a} & {b}", f"${got} = ~${tmp}a"]

    # arity-3 (and any arity-2 fallback): INT-based truth table lookup
    lines = [f"${tmp}ia = INT({a})"]
    if arity >= 2:
        lines += [
            f"${tmp}ib = INT({b})",
            f"${tmp}ib2 = ${tmp}ib * 2",
        ]
    if arity == 3:
        lines += [
            f"${tmp}ic = INT({c})",
            f"${tmp}ic4 = ${tmp}ic * 4",
        ]
    if arity == 1:
        lines.append(f"${tmp}idx = ${tmp}ia")
    elif arity == 2:
        lines.append(f"${tmp}idx = ${tmp}ia + ${tmp}ib2")
    else:
        lines += [
            f"${tmp}idx1 = ${tmp}ia + ${tmp}ib2",
            f"${tmp}idx = ${tmp}idx1 + ${tmp}ic4",
        ]
    lines.append(f"${got} = {tt_str_var}[${tmp}idx]")
    return lines


def emit_trace(prompt: str) -> tuple[str, str]:
    """Return (solver_answer, cotl_trace_source).

    Calls bit_solver_tt to find the rule, then unrolls the winning
    execution path as a flat sequence of cotl instructions.
    """
    answer, _, rule_info = solve_bit_manipulation(prompt)
    if rule_info is None:
        return (answer or ""), "# no rule found\n"

    arity, tt, ordered_transforms = rule_info

    ex_matches = re.findall(r"([01]{8})\s*->\s*([01]{8})", prompt)
    qm = re.search(
        r"(?:output for:|determine the output for:)\s*([01]{8})",
        prompt,
        re.IGNORECASE,
    )
    query_str = qm.group(1)
    n_ex = len(ex_matches)

    lines: list[str] = []

    # ── Load examples and query ──────────────────────────────────────────────
    for i, (in_s, out_s) in enumerate(ex_matches):
        lines.append(f'$ex{i}_in  = "{in_s}"')
        lines.append(f'$ex{i}_out = "{out_s}"')
    lines += [f'$query = "{query_str}"', ""]

    # ── Candidate rule name ──────────────────────────────────────────────────
    lines += [f'$candidate = "{_rule_name(arity, tt)}"', ""]

    # ── Truth table string (for arity-3 fallback) ────────────────────────────
    needs_tt_str = arity == 3 or (
        arity == 2
        and (tt, arity)
        not in {
            (k, 2)
            for k in (0b0110, 0b1110, 0b1000, 0b1001, 0b0001, 0b0010, 0b1011, 0b0111)
        }
    )
    if needs_tt_str:
        width = 1 << arity
        tt_chars = "".join(str((tt >> i) & 1) for i in range(width))
        lines += [f'$tt_str = "{tt_chars}"', ""]

    tt_str_var = "$tt_str" if needs_tt_str else "$tt_str"

    # ── Precompute transforms for each example ───────────────────────────────
    for i in range(n_ex):
        for vi in range(arity):
            letter = _VAR_LETTERS[vi]
            ttype, k = ordered_transforms[vi]
            expr = _transform_expr(ttype, k, f"$ex{i}_in")
            lines.append(f"$xfm{letter}_e{i} = {expr}")
    # Transforms for query
    for vi in range(arity):
        letter = _VAR_LETTERS[vi]
        ttype, k = ordered_transforms[vi]
        expr = _transform_expr(ttype, k, "$query")
        lines.append(f"$xfm{letter}_q = {expr}")
    lines.append("")

    # ── Verification steps ───────────────────────────────────────────────────
    check_order = _make_check_order(n_ex)
    for ex, pos in check_order:
        pfx = f"e{ex}p{pos}"

        for vi in range(arity):
            letter = _VAR_LETTERS[vi]
            lines.append(f"${letter.lower()}_{pfx} = $xfm{letter}_e{ex}[{pos}]")

        a = f"${_VAR_LETTERS[0].lower()}_{pfx}"
        b = f"${_VAR_LETTERS[1].lower()}_{pfx}" if arity >= 2 else None
        c = f"${_VAR_LETTERS[2].lower()}_{pfx}" if arity >= 3 else None
        lines.extend(_tt_lines(tt, arity, a, b, c, f"got_{pfx}", pfx, tt_str_var))
        lines.append(f"$want_{pfx} = $ex{ex}_out[{pos}]")
        lines.append(f"$ok_{pfx} = $got_{pfx} == $want_{pfx}")
        lines.append("")

    # ── Apply rule to query ──────────────────────────────────────────────────
    lines.append("# apply rule to query")
    for pos in range(8):
        pfx = f"qp{pos}"
        for vi in range(arity):
            letter = _VAR_LETTERS[vi]
            lines.append(f"${letter.lower()}_{pfx} = $xfm{letter}_q[{pos}]")
        a = f"${_VAR_LETTERS[0].lower()}_{pfx}"
        b = f"${_VAR_LETTERS[1].lower()}_{pfx}" if arity >= 2 else None
        c = f"${_VAR_LETTERS[2].lower()}_{pfx}" if arity >= 3 else None
        lines.extend(_tt_lines(tt, arity, a, b, c, f"out_{pfx}", pfx, tt_str_var))

    lines.append("")

    # ── Assemble answer from 8 output bits ──────────────────────────────────
    lines.append("$ans = $out_qp0")
    for pos in range(1, 8):
        lines.append(f"$ans = $ans + $out_qp{pos}")
    lines.append("ANSWER $ans")

    return (answer or ""), "\n".join(lines) + "\n"
