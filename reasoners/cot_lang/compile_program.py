"""Compile bit_manipulation.cotl by consuming the block generator and applying BPE.

Reads blocks from generate_program.iter_blocks(), accumulates a buffer, runs BPE
compression whenever the buffer crosses TRIGGER_LINES, then writes the final
compressed program to programs/bit_manipulation.cotl.

    uv run reasoners/cot_lang/compile_program.py
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "reasoners" / "bit_manipulation_solver"))

from reasoners.cot_lang.generate_program import iter_blocks  # noqa: E402

OUT = Path(__file__).parent / "programs" / "bit_manipulation.cotl"
OUT.parent.mkdir(exist_ok=True)

# ── BPE config ────────────────────────────────────────────────────────────────
TRIGGER_LINES = 100_000
MAX_FUNCTIONS = 30
MIN_PAIR_COUNT = 100

_VAR_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")
_ASSIGN_LINE_RE = re.compile(r"^\$([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$")
_FUNC_CALL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\(")


# ── Op-name derivation ────────────────────────────────────────────────────────


def _op_name(canonical_rhs: str) -> str:
    rhs = canonical_rhs.strip()
    m = _FUNC_CALL_RE.match(rhs)
    if m:
        return m.group(1)
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


def _next_block_index(lines: list[str]) -> list[int]:
    """For each index i, return the index of the nearest BLOCK line at or after i."""
    n = len(lines)
    result = [n] * n
    nxt = n
    for j in range(n - 1, -1, -1):
        if lines[j].startswith("BLOCK "):
            nxt = j
        result[j] = nxt
    return result


def _mine_best_pair(
    lines: list[str],
    known_sigs: set[str],
) -> tuple[str, int, list[str], str] | None:
    counts: dict[str, list] = {}
    n = len(lines)
    next_block = _next_block_index(lines)

    for start in range(n - 1):
        window = lines[start : start + 2]
        result = _normalize(window)
        if result is None:
            continue
        sig, conc_inputs, _, intermediates = result
        if sig in known_sigs:
            continue
        if intermediates:
            end = next_block[start + 2] if start + 2 < n else n
            lookahead = " ".join(lines[start + 2 : end])
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
    result: list[str] = []
    i = 0
    while i < len(lines):
        if i + pat_len <= len(lines):
            window = lines[i : i + pat_len]
            norm = _normalize(window)
            if norm and norm[0] == sig:
                conc_inputs, ret_var = norm[1], norm[2]
                args_str = ", ".join(f"${v}" for v in conc_inputs)
                result.append(f"${ret_var} = {fn_name}({args_str})")
                i += pat_len
                continue
        result.append(lines[i])
        i += 1
    return result


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    from tqdm import tqdm

    buffer: list[str] = []
    known_sigs: set[str] = set()
    used_names: set[str] = set()
    extracted: list[tuple[str, str, list[str], str, int]] = []

    def _run_one_bpe_round() -> bool:
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

    trigger_at = TRIGGER_LINES

    pbar = tqdm(
        iter_blocks(), desc="blocks", unit="blk", total=4644, dynamic_ncols=True
    )
    for block_lines in pbar:
        for fn_name, sig, _params, _ret, pat_len in extracted:
            block_lines = _rewrite(block_lines, fn_name, sig, pat_len)
        buffer.extend(block_lines)

        while len(buffer) >= trigger_at and len(extracted) < MAX_FUNCTIONS:
            if not _run_one_bpe_round():
                trigger_at = len(buffer) + TRIGGER_LINES
                break
        pbar.set_postfix(lines=f"{len(buffer):,}", fns=len(extracted))

    pbar.close()

    tqdm.write(f"Final BPE pass on full buffer ({len(buffer):,} lines)...")
    while len(extracted) < MAX_FUNCTIONS:
        if not _run_one_bpe_round():
            break

    print(
        f"Extracted {len(extracted)} function(s) total. Final buffer: {len(buffer):,} lines"
    )

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
