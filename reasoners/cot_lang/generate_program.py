"""Generate programs/bit_manipulation.cotl — the fixed cotl program for all bit manipulation problems.

BPE compression: generate the full raw program, then iteratively merge the most frequent
adjacent pair of assignment lines into a named function (up to MAX_FUNCTIONS rounds).
Functions compose hierarchically — later functions can call earlier ones.

Run once to regenerate the program:
    uv run reasoners/cot_lang/generate_program.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "bit_manipulation_solver"))

from bit_solver_tt import KNOWN_FUNCTIONS, TRANSFORMATIONS, _canonical_perms  # noqa: E402

OUT = Path(__file__).parent / "programs" / "bit_manipulation.cotl"
OUT.parent.mkdir(exist_ok=True)

N_EX = 8

# ── BPE compression config ────────────────────────────────────────────────────
TRIGGER_LINES = 100_000   # run BPE when buffer reaches this size
MAX_FUNCTIONS = 50        # total BPE rounds across all triggers
MIN_PAIR_COUNT = 100      # minimum occurrences to qualify for extraction

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

_VAR_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")
_ASSIGN_LINE_RE = re.compile(r"^\$([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$")
_FUNC_CALL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\(")


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


# ── Op-name derivation for descriptive function names ─────────────────────────


def _op_name(canonical_rhs: str) -> str:
    """Short human-readable name for the operation in a canonical RHS expression."""
    rhs = canonical_rhs.strip()
    m = _FUNC_CALL_RE.match(rhs)
    if m:
        return m.group(1)  # existing function name — enables chaining
    if re.match(r"^\$\w+\[", rhs):
        return "idx"
    if " == " in rhs:
        return "eq"
    if " + " in rhs:
        return "add"
    if " * 2" in rhs:
        return "mul2"
    if " * 4" in rhs:
        return "mul4"
    if " * " in rhs:
        return "mul"
    return "op"


def _make_fn_name(sig: str, used_names: set[str]) -> str:
    """Derive a descriptive function name from a 2-line canonical signature."""
    lines = sig.splitlines()
    parts = []
    for line in lines:
        rhs = line.split("=", 1)[1].strip()
        parts.append(_op_name(rhs))
    base = "_".join(parts)
    name = base
    suffix = 2
    while name in used_names:
        name = f"{base}_{suffix}"
        suffix += 1
    return name


# ── Pattern normalization ─────────────────────────────────────────────────────


def _normalize(
    lines: list[str],
) -> tuple[str, list[str], str, list[str]] | None:
    """Normalize a window of assignment lines by renaming variables canonically.

    Variables first referenced on the RHS (before any LHS assignment) → IN0, IN1, ...
    Variables first assigned on the LHS → LOC0, LOC1, ...
    Return variable = the LHS of the last line.

    Returns (canonical_signature, concrete_input_var_names, concrete_return_var,
             concrete_intermediate_var_names)
    or None if any line is not a pure assignment (blank, BLOCK, GOTO, comment).
    """
    canon_map: dict[str, str] = {}
    inputs: list[str] = []
    lhs_vars: list[str] = []
    n_locs = 0
    canonical_lines: list[str] = []
    last_lhs_concrete: str | None = None

    for line in lines:
        line = line.strip()
        if not line or not line.startswith("$"):
            return None
        m = _ASSIGN_LINE_RE.match(line)
        if not m:
            return None

        lhs_var = m.group(1)
        rhs_txt = m.group(2).strip()

        def _sub_rhs(match: re.Match) -> str:
            name = match.group(1)
            if name in canon_map:
                return "$" + canon_map[name]
            cname = f"IN{len(inputs)}"
            inputs.append(name)
            canon_map[name] = cname
            return "$" + cname

        canon_rhs = _VAR_RE.sub(_sub_rhs, rhs_txt)

        if lhs_var not in canon_map:
            canon_map[lhs_var] = f"LOC{n_locs}"
            n_locs += 1
        canon_lhs = canon_map[lhs_var]
        lhs_vars.append(lhs_var)
        last_lhs_concrete = lhs_var

        canonical_lines.append(f"${canon_lhs} = {canon_rhs}")

    if last_lhs_concrete is None:
        return None

    intermediates = [v for v in lhs_vars[:-1] if v != last_lhs_concrete]
    return "\n".join(canonical_lines), inputs, last_lhs_concrete, intermediates


# ── BPE pair mining ───────────────────────────────────────────────────────────


def _mine_best_pair(
    lines: list[str],
    known_sigs: set[str],
) -> tuple[str, int, list[str], str] | None:
    """Find the most frequent valid adjacent 2-line pattern not already extracted.

    Returns (signature, 2, canonical_param_names, return_var_canon) or None.
    O(n) scan — always exactly 2 lines.
    """
    counts: dict[str, list] = {}  # sig → [count, n_inputs, ret_canon]

    for start in range(len(lines) - 1):
        window = lines[start : start + 2]
        result = _normalize(window)
        if result is None:
            continue
        sig, conc_inputs, _, intermediates = result
        if sig in known_sigs:
            continue
        # Guard: the intermediate (first LHS) must not appear in the next 2 lines.
        if intermediates:
            lookahead = " ".join(lines[start + 2 : start + 4])
            if any(f"${v}" in lookahead for v in intermediates):
                continue
        n_inputs = len(conc_inputs)
        ret_canon = sig.splitlines()[-1].split("=")[0].strip().lstrip("$")
        if sig not in counts:
            counts[sig] = [0, n_inputs, ret_canon]
        counts[sig][0] += 1

    if not counts:
        return None

    best_sig, best = max(counts.items(), key=lambda kv: kv[1][0])
    count, n_inputs, ret_canon = best

    if count < MIN_PAIR_COUNT:
        return None

    param_names = [f"IN{i}" for i in range(n_inputs)]
    return best_sig, 2, param_names, ret_canon


# ── Rewriting ─────────────────────────────────────────────────────────────────


def _rewrite(
    lines: list[str],
    fn_name: str,
    sig: str,
    pat_len: int,
) -> list[str]:
    """Replace all valid occurrences of the 2-line pattern with a function call."""
    result: list[str] = []
    i = 0
    while i < len(lines):
        if i + pat_len <= len(lines):
            window = lines[i : i + pat_len]
            norm = _normalize(window)
            if (
                norm
                and norm[0] == sig
                and not any(
                    f"${v}" in " ".join(lines[i + pat_len : i + pat_len + 4])
                    for v in norm[3]
                )
            ):
                conc_inputs, ret_var = norm[1], norm[2]
                args_str = ", ".join(f"${v}" for v in conc_inputs)
                result.append(f"${ret_var} = {fn_name}({args_str})")
                i += pat_len
                continue
        result.append(lines[i])
        i += 1
    return result


# ── Block emission ────────────────────────────────────────────────────────────


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
    lines.append("")

    for pos in range(8):
        for ex in range(N_EX):
            pfx = f"e{ex}p{pos}"
            lines.append(f"$a_{pfx} = $xfmA_e{ex}[{pos}]")
            lines.append(f"$b_{pfx} = $xfmB_e{ex}[{pos}]")
            lines.append(f"$c_{pfx} = $xfmC_e{ex}[{pos}]")
            lines.append(f"$ia_{pfx} = INT($a_{pfx})")
            lines.append(f"$ib_{pfx} = INT($b_{pfx})")
            lines.append(f"$ib2_{pfx} = $ib_{pfx} * 2")
            lines.append(f"$ic_{pfx} = INT($c_{pfx})")
            lines.append(f"$ic4_{pfx} = $ic_{pfx} * 4")
            lines.append(f"$idx1_{pfx} = $ia_{pfx} + $ib2_{pfx}")
            lines.append(f"$idx_{pfx} = $idx1_{pfx} + $ic4_{pfx}")
            lines.append(f"$got_{pfx} = $tt_str[$idx_{pfx}]")
            lines.append(f"$want_{pfx} = $ex{ex}_out[{pos}]")
            lines.append(f"$ok_{pfx} = $got_{pfx} == $want_{pfx}")
            if next_label:
                lines.append(f"IF NOT $ok_{pfx}: GOTO {next_label}")
            lines.append("")

    lines.append("# apply rule to query")
    for pos in range(8):
        pfx = f"qp{pos}"
        lines.append(f"$a_{pfx} = $xfmA_q[{pos}]")
        lines.append(f"$b_{pfx} = $xfmB_q[{pos}]")
        lines.append(f"$c_{pfx} = $xfmC_q[{pos}]")
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


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    import time

    from tqdm import tqdm

    candidates = list(_iter_candidates())
    total = len(candidates)

    known_sigs: set[str] = set()
    used_names: set[str] = set()
    extracted: list[tuple[str, str, list[str], str, int]] = []
    buffer: list[str] = []
    above_trigger = False  # track crossing direction

    def _run_one_bpe_round() -> bool:
        """Mine + rewrite the whole buffer for the best pair. Returns True if a round ran."""
        t0 = time.monotonic()
        result = _mine_best_pair(buffer, known_sigs)
        if result is None:
            tqdm.write("  No qualifying pair — BPE exhausted.")
            return False

        sig, pat_len, param_names, ret_canon = result
        fn_name = _make_fn_name(sig, used_names)
        used_names.add(fn_name)

        t_rw = time.monotonic()
        before = len(buffer)
        buffer[:] = _rewrite(buffer, fn_name, sig, pat_len)
        after = len(buffer)
        known_sigs.add(sig)
        extracted.append((fn_name, sig, param_names, ret_canon, pat_len))

        tqdm.write(
            f"  [{len(extracted)}/{MAX_FUNCTIONS}] {fn_name}: "
            f"{before:,} → {after:,} (−{before - after:,})  "
            f"mine={t_rw - t0:.1f}s  rewrite={time.monotonic() - t_rw:.1f}s"
        )
        return True

    # Generate blocks; run one BPE round on the whole buffer each time it crosses TRIGGER_LINES
    pbar = tqdm(candidates, desc="blocks", unit="blk", dynamic_ncols=True)
    for i, (label, arity, tt, transforms) in enumerate(pbar):
        next_label = candidates[i + 1][0] if i + 1 < total else None
        buffer.extend(_emit_block_raw(label, arity, tt, transforms, next_label))

        now_above = len(buffer) >= TRIGGER_LINES
        if now_above and not above_trigger and len(extracted) < MAX_FUNCTIONS:
            _run_one_bpe_round()  # run regardless of result; re-triggers naturally next crossing
        above_trigger = len(buffer) >= TRIGGER_LINES  # recheck after possible rewrite
        pbar.set_postfix(lines=f"{len(buffer):,}", fns=len(extracted))

    pbar.close()

    # Final BPE pass: apply all rounds to the complete buffer
    tqdm.write(f"Final BPE pass on full buffer ({len(buffer):,} lines)...")
    while len(extracted) < MAX_FUNCTIONS:
        if not _run_one_bpe_round():
            break

    print(
        f"Extracted {len(extracted)} function(s) total. Final buffer: {len(buffer):,} lines"
    )

    # Build function definition header
    header: list[str] = []
    for fn_name, sig, param_names, ret_canon, _pat_len in extracted:
        param_str = ", ".join(param_names)
        header.append(f"FUNCTION {fn_name}({param_str}) -> {ret_canon}")
        for body_line in sig.splitlines():
            header.append(f"    {body_line}")
        header.append("END")
        header.append("")

    all_lines = header + buffer
    src = "\n".join(all_lines) + "\n"
    OUT.write_text(src)
    n_lines = src.count("\n")
    print(f"Written {n_lines:,} lines to {OUT}")


if __name__ == "__main__":
    main()
