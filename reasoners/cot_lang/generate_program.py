"""Generate raw (uncompressed) cotl blocks for all bit manipulation candidates.

Exposes iter_blocks() for use by compile_program.py.
Can also be run standalone to inspect raw block output.

    uv run reasoners/cot_lang/generate_program.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterator

sys.path.insert(0, str(Path(__file__).parent.parent / "bit_manipulation_solver"))

from bit_solver_tt import KNOWN_FUNCTIONS, TRANSFORMATIONS, _canonical_perms  # noqa: E402

N_EX = 8

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


def _xfm_expr(ttype: str, k: int, src: str) -> str:
    if ttype == "rot" and k == 0:
        return src
    if ttype == "rot":
        return f"ROT({src}, {k})"
    if ttype == "shl":
        return f"SHL({src}, {k})"
    return f"SHR({src}, {k})"


def _iter_candidates():
    idx = 0
    for arity, tt, _ in KNOWN_FUNCTIONS:
        if arity == 0:
            label = f"cand_{idx:05d}_{_rule_name(arity, tt)}"
            yield label, arity, tt, []
            idx += 1
            continue

        if arity == 1:
            for t0 in TRANSFORMATIONS:
                label = f"cand_{idx:05d}_{_rule_name(arity, tt)}"
                yield label, arity, tt, [t0]
                idx += 1
            continue

        canon_perms = _canonical_perms(tt, arity)

        if arity == 2:
            for t0 in TRANSFORMATIONS:
                for t1 in TRANSFORMATIONS:
                    if t0 == t1:
                        continue
                    for perm in canon_perms:
                        ordered = [[t0, t1][perm[i]] for i in range(2)]
                        label = f"cand_{idx:05d}_{_rule_name(arity, tt)}"
                        yield label, arity, tt, ordered
                        idx += 1
            continue

        if arity == 3:
            continue


def _emit_block_raw(
    label: str,
    arity: int,
    tt: int,
    transforms: list,
    next_label: str | None,
) -> list[str]:
    lines: list[str] = []
    lines.append(f"BLOCK {label}")

    cname = _rule_name(arity, tt)
    lines.append(f'$cname = "{cname}"')

    width = 1 << max(arity, 1)
    tt_chars = "".join(str((tt >> i) & 1) for i in range(width))
    lines.append(f'$tt_str = "{tt_chars}"')

    DUMMY = '"00000000"'

    def xfm(slot: int, src: str) -> str:
        if slot >= arity:
            return DUMMY
        t = transforms[slot]
        return _xfm_expr(t[0], t[1], src)

    for i in range(N_EX):
        src = f"$ex{i}_in"
        lines.append(f"$xfmA_e{i} = {xfm(0, src)}")
        lines.append(f"$xfmB_e{i} = {xfm(1, src)}")
        lines.append(f"$xfmC_e{i} = {xfm(2, src)}")

    lines.append(f"$xfmA_q = {xfm(0, '$query')}")
    lines.append(f"$xfmB_q = {xfm(1, '$query')}")
    lines.append(f"$xfmC_q = {xfm(2, '$query')}")

    for pos in range(8):
        lines.append(f"$pos{pos} = {pos}")
    lines.append("")

    for ex in range(N_EX):
        pfx = f"e{ex}"
        for pos in range(8):
            ppfx = f"{pfx}_p{pos}"
            lines.append(f"$a_{ppfx} = $xfmA_{pfx}[$pos{pos}]")
            lines.append(f"$b_{ppfx} = $xfmB_{pfx}[$pos{pos}]")
            lines.append(f"$c_{ppfx} = $xfmC_{pfx}[$pos{pos}]")
            lines.append(f"$ia_{ppfx} = INT($a_{ppfx})")
            lines.append(f"$ib_{ppfx} = INT($b_{ppfx})")
            lines.append(f"$ib2_{ppfx} = $ib_{ppfx} * 2")
            lines.append(f"$ic_{ppfx} = INT($c_{ppfx})")
            lines.append(f"$ic4_{ppfx} = $ic_{ppfx} * 4")
            lines.append(f"$idx1_{ppfx} = $ia_{ppfx} + $ib2_{ppfx}")
            lines.append(f"$idx_{ppfx} = $idx1_{ppfx} + $ic4_{ppfx}")
            lines.append(f"$got_{ppfx} = $tt_str[$idx_{ppfx}]")
            lines.append("")
        lines.append(f"$pred_{pfx} = $got_{pfx}_p0")
        for pos in range(1, 8):
            lines.append(f"$pred_{pfx} = $pred_{pfx} + $got_{pfx}_p{pos}")
        lines.append(f"$ok_{pfx} = $pred_{pfx} == $ex{ex}_out")
        if next_label:
            lines.append(f"IF NOT $ok_{pfx}: GOTO {next_label}")
        lines.append("")

    lines.append("# apply rule to query")
    for pos in range(8):
        pfx = f"qp{pos}"
        lines.append(f"$a_{pfx} = $xfmA_q[$pos{pos}]")
        lines.append(f"$b_{pfx} = $xfmB_q[$pos{pos}]")
        lines.append(f"$c_{pfx} = $xfmC_q[$pos{pos}]")
        lines.append(f"$ia_{pfx} = INT($a_{pfx})")
        lines.append(f"$ib_{pfx} = INT($b_{pfx})")
        lines.append(f"$ib2_{pfx} = $ib_{pfx} * 2")
        lines.append(f"$ic_{pfx} = INT($c_{pfx})")
        lines.append(f"$ic4_{pfx} = $ic_{pfx} * 4")
        lines.append(f"$idx1_{pfx} = $ia_{pfx} + $ib2_{pfx}")
        lines.append(f"$idx_{pfx} = $idx1_{pfx} + $ic4_{pfx}")
        lines.append(f"$out_{pfx} = $tt_str[$idx_{pfx}]")
        lines.append("")

    lines.append("$ans = $out_qp0")
    for pos in range(1, 8):
        lines.append(f"$ans = $ans + $out_qp{pos}")
    lines.append("ANSWER $ans")
    lines.append("")

    return lines


def iter_blocks() -> Iterator[list[str]]:
    """Yield raw (uncompressed) cotl lines for each candidate block."""
    candidates = list(_iter_candidates())
    total = len(candidates)
    for i, (label, arity, tt, transforms) in enumerate(candidates):
        next_label = candidates[i + 1][0] if i + 1 < total else None
        yield _emit_block_raw(label, arity, tt, transforms, next_label)


def main() -> None:
    total = sum(1 for _ in _iter_candidates())
    n_lines = 0
    for block_lines in iter_blocks():
        n_lines += len(block_lines)
    print(f"Raw program: {total} blocks, {n_lines:,} lines")


if __name__ == "__main__":
    main()
