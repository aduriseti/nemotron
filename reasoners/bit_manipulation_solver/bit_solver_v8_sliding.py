"""
Stride-compatible truth-table solver (v8).

Output bit q is the anchor. For each offset tuple (d0, d1) or (d0, d1, d2),
truth tables are built by scanning output positions 0..7. A new TT is started
whenever a contradiction is encountered, so each position is visited at most
once. Cost per offset group: at most 8 × n_ex bit checks.

A run is (start_q, run_len, tt). Stitching uses all runs from the primary
group plus compatible lower-arity runs (offsets must be a subset).

Window 1: all 8 single offsets d ∈ 0..7
Window 2: all 56 ordered (d0, d1) pairs with d0 ≠ d1
Window 3: all 336 ordered triples (d0, d1, d2) with all distinct
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

_Run = tuple[int, int, list[int]]   # (start_q, run_len, tt)
_GroupRuns = dict[tuple, list[_Run]]


def _build_runs(
    in_bytes: list[int],
    out_bytes: list[int],
    offsets: tuple[int, ...],
) -> list[_Run]:
    """
    Single linear pass over positions 0..7. Start a fresh TT at each
    contradiction. Each position is visited exactly once.
    Cost: at most 8 × n_ex bit checks.
    """
    n_ex = len(in_bytes)
    tt_size = 1 << len(offsets)
    runs: list[_Run] = []
    pos = 0

    while pos < 8:
        start = pos
        tt: list[int] = [-1] * tt_size
        run_len = 0

        while pos < 8:
            q = pos
            ok = True
            for ex in range(n_ex):
                slot = 0
                for k, d in enumerate(offsets):
                    slot |= ((in_bytes[ex] >> (7 - (q + d) % 8)) & 1) << k
                expected = (out_bytes[ex] >> (7 - q)) & 1
                if tt[slot] == -1:
                    tt[slot] = expected
                elif tt[slot] != expected:
                    ok = False
                    break
            pos += 1
            if ok:
                run_len += 1
            else:
                break  # contradiction: skip this position, start fresh TT next

        if run_len > 0:
            runs.append((start, run_len, list(tt)))

    runs.sort(key=lambda x: -x[1])
    return runs


def _collect_all_runs(
    in_bytes: list[int], out_bytes: list[int]
) -> tuple[_GroupRuns, _GroupRuns, _GroupRuns]:
    w1: _GroupRuns = {}
    w2: _GroupRuns = {}
    w3: _GroupRuns = {}

    for d in range(8):
        runs = _build_runs(in_bytes, out_bytes, (d,))
        if runs:
            w1[(d,)] = runs

    for d0 in range(8):
        for d1 in range(8):
            if d1 == d0:
                continue
            runs = _build_runs(in_bytes, out_bytes, (d0, d1))
            if runs:
                w2[(d0, d1)] = runs

    for d0 in range(8):
        for d1 in range(8):
            if d1 == d0:
                continue
            for d2 in range(8):
                if d2 == d0 or d2 == d1:
                    continue
                runs = _build_runs(in_bytes, out_bytes, (d0, d1, d2))
                if runs:
                    w3[(d0, d1, d2)] = runs

    return w1, w2, w3


def _try_group(
    primary_offsets: tuple,
    primary_runs: list[_Run],
    w1: _GroupRuns,
    w2: _GroupRuns,
    target_byte: int,
) -> list[int]:
    offset_set = set(primary_offsets)

    tagged: list[tuple[tuple, _Run]] = [
        (primary_offsets, r) for r in primary_runs
    ]
    if len(primary_offsets) >= 3:
        for pair_key, runs in w2.items():
            if set(pair_key) <= offset_set:
                for r in runs:
                    tagged.append((pair_key, r))
    for w1_key, runs in w1.items():
        if w1_key[0] in offset_set:
            for r in runs:
                tagged.append((w1_key, r))

    tagged.sort(key=lambda x: -x[1][1])

    result_bits = [-1] * 8
    for offsets, (start, run_len, tt) in tagged:
        if all(b != -1 for b in result_bits):
            break
        for step in range(run_len):
            q = start + step  # linear positions only (no modular wrap within a run)
            if result_bits[q] != -1:
                continue
            slot = 0
            for k, d in enumerate(offsets):
                slot |= ((target_byte >> (7 - (q + d) % 8)) & 1) << k
            if tt[slot] != -1:
                result_bits[q] = tt[slot]

    return result_bits


def find_rule(
    in_arrays: list[list[int]],
    out_arrays: list[list[int]],
    target_bits: list[int],
    timeout: float = 15.0,
) -> tuple[str | None, int, tuple | None]:
    in_bytes    = [sum(r[i] << (7 - i) for i in range(8)) for r in in_arrays]
    out_bytes   = [sum(r[i] << (7 - i) for i in range(8)) for r in out_arrays]
    target_byte = sum(target_bits[i] << (7 - i) for i in range(8))
    n_ex = len(in_bytes)

    w1, w2, w3 = _collect_all_runs(in_bytes, out_bytes)

    bit_checks  = sum(r[1] * n_ex for runs in w1.values() for r in runs)
    bit_checks += sum(r[1] * n_ex for runs in w2.values() for r in runs)
    bit_checks += sum(r[1] * n_ex for runs in w3.values() for r in runs)

    candidates: list[tuple[tuple, list[_Run]]] = []
    for key, runs in w3.items():
        candidates.append((key, runs))
    for key, runs in w2.items():
        candidates.append((key, runs))
    for key, runs in w1.items():
        candidates.append((key, runs))
    candidates.sort(key=lambda x: -max(r[1] for r in x[1]))

    for offsets, primary_runs in candidates:
        result_bits = _try_group(offsets, primary_runs, w1, w2, target_byte)
        if all(b != -1 for b in result_bits):
            answer = ''.join(str(b) for b in result_bits)
            return answer, bit_checks, ('stride', offsets, result_bits)

    return None, bit_checks, None


def solve_bit_manipulation(prompt: str, timeout: float = 15.0) -> tuple[str | None, int, tuple | None]:
    ex_matches  = re.findall(r'([01]{8})\s*->\s*([01]{8})', prompt)
    query_match = re.search(r'(?:output for:|determine the output for:)\s*([01]{8})', prompt)
    if not ex_matches or not query_match:
        return None, 0, None
    target_bits = [int(b) for b in query_match.group(1)]
    in_arrays   = [[int(ex_matches[i][0][j]) for j in range(8)] for i in range(len(ex_matches))]
    out_arrays  = [[int(ex_matches[i][1][j]) for j in range(8)] for i in range(len(ex_matches))]
    return find_rule(in_arrays, out_arrays, target_bits, timeout)
