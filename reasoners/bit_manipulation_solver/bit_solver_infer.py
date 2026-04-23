"""
Direct truth-table inference solver with signed-offset parameterisation for arity-3.

Signed-offset convention (s ∈ {-7..+7}):
  s > 0  →  shl_s only            (1 option, deterministic, no ambiguity)
  s = 0  →  rot_0 only            (1 option, deterministic)
  s < 0  →  rot_{8-|s|} or shr_{|s|}  (2 options — wrap vs zero-pad at p < |s|)

For a triple (s0, s1, s2):
  lo = max(|s_i| for s_i < 0, default 0)   — shr safe boundary
  hi = max(s_i  for s_i > 0, default 0)   — shl safe boundary
  Phase-1 safe zone: lo ≤ p < 8-hi

Within the safe zone, every option agrees with its representative:
  s > 0: shl_s is exact (only option).
  s < 0: rot_{8-k} and shr_k both read from p-k when p ≥ k (≥ lo). ✓

Phase-1 contradiction rules out all ≤ 2³ = 8 type-combos for this s-triple.
Phase-2 resolves the rot-vs-shr choice only for negative-s variables.
Arity-0/1/2 use simple direct inference (no grouping needed).
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

TRANSFORMATIONS = [('rot', 0)]
for _k in range(1, 8):
    TRANSFORMATIONS.extend([('rot', _k), ('shl', _k), ('shr', _k)])


def _build_trans_bytes() -> list[list[int]]:
    tables: list[list[int]] = []
    for ttype, k in TRANSFORMATIONS:
        table = []
        for byte_val in range(256):
            result = 0
            for pos in range(8):
                if ttype == 'rot':
                    src = (pos + k) & 7
                    result |= ((byte_val >> (7 - src)) & 1) << (7 - pos)
                elif ttype == 'shl':
                    src = pos + k
                    if src < 8:
                        result |= ((byte_val >> (7 - src)) & 1) << (7 - pos)
                else:
                    src = pos - k
                    if src >= 0:
                        result |= ((byte_val >> (7 - src)) & 1) << (7 - pos)
            table.append(result)
        tables.append(table)
    return tables


_TRANS_BYTES = _build_trans_bytes()

# Signed-offset lookup tables.
# For k in 1..7:
#   rot_k  → TRANSFORMATIONS index 3k-2
#   shl_k  → TRANSFORMATIONS index 3k-1
#   shr_k  → TRANSFORMATIONS index 3k
#
# s = +k  →  shl_k only (index 3k-1)
# s =  0  →  rot_0     (index 0)
# s = -k  →  rot_{8-k} (index 3*(8-k)-2) as representative, or shr_k (index 3k)
#   Correctness: at safe positions p ≥ k, rot_{8-k} reads (p+8-k)%8 = p-k = shr_k's source. ✓

_S_REP: dict[int, int] = {0: 0}
_S_OPTIONS: dict[int, list[int]] = {0: [0]}

for _k in range(1, 8):
    _shl_idx = 3 * _k - 1
    _shr_idx = 3 * _k
    _rot_8mk_idx = 3 * (8 - _k) - 2   # rot_{8-k}

    _S_REP[_k] = _shl_idx
    _S_OPTIONS[_k] = [_shl_idx]

    _S_REP[-_k] = _rot_8mk_idx
    _S_OPTIONS[-_k] = [_rot_8mk_idx, _shr_idx]


def _apply_inferred(inferred: list[int], tbs: list[list[int]], target_byte: int) -> str | None:
    """Apply inferred TT to target. Returns None if any queried slot is unseen (-1)."""
    result = 0
    for pos in range(8):
        slot = 0
        for i, tb in enumerate(tbs):
            slot |= ((tb[target_byte] >> (7 - pos)) & 1) << i
        bit = inferred[slot]
        if bit == -1:
            return None
        result |= bit << (7 - pos)
    return format(result, '08b')


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
    check_order = [(ex, pos) for pos in range(8) for ex in range(n_ex)]
    bit_checks = 0

    # ── arity 0 ──────────────────────────────────────────────────────────────
    ref = out_bytes[0]
    if all(b == ref for b in out_bytes):
        for ex, pos in check_order:
            bit_checks += 1
            if ((out_bytes[ex] >> (7 - pos)) & 1) != ((ref >> (7 - pos)) & 1):
                break
        else:
            return format(ref, '08b'), bit_checks, (0, ref, [])

    # ── arity 1 ──────────────────────────────────────────────────────────────
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
            tt_val = inferred[0] | ((inferred[1] if inferred[1] != -1 else 0) << 1)
            return answer, bit_checks, (1, tt_val, [TRANSFORMATIONS[t0_idx]])

    # ── arity 2 (signed-offset phase-1/2) ────────────────────────────────────
    for s0 in range(-7, 8):
        rep0 = _TRANS_BYTES[_S_REP[s0]]
        for s1 in range(-7, 8):
            rep1 = _TRANS_BYTES[_S_REP[s1]]

            lo = max((abs(s) for s in (s0, s1) if s < 0), default=0)
            hi = max((s for s in (s0, s1) if s > 0), default=0)

            p1: list[int] = [-1, -1, -1, -1]
            p1_fail = False
            for pos in range(lo, 8 - hi):
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
                for pos in range(8)
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
                        tt_val = sum((v if v != -1 else 0) << i for i, v in enumerate(inferred))
                        return answer, bit_checks, (2, tt_val, [TRANSFORMATIONS[i0], TRANSFORMATIONS[i1]])

    # ── arity 3 (signed-offset phase-1/2) ────────────────────────────────────
    # Each transform appears in exactly one _S_OPTIONS bucket, so every distinct
    # triple (i0,i1,i2) is visited exactly once across all s-triple iterations.
    for s0 in range(-7, 8):
        rep0 = _TRANS_BYTES[_S_REP[s0]]
        for s1 in range(-7, 8):
            rep1 = _TRANS_BYTES[_S_REP[s1]]
            for s2 in range(-7, 8):
                rep2 = _TRANS_BYTES[_S_REP[s2]]

                lo = max((abs(s) for s in (s0, s1, s2) if s < 0), default=0)
                hi = max((s for s in (s0, s1, s2) if s > 0), default=0)

                # Phase-1: partial TT from safe positions ─────────────────────
                p1: list[int] = [-1, -1, -1, -1, -1, -1, -1, -1]
                p1_fail = False
                for pos in range(lo, 8 - hi):
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

                # Phase-2: resolve type-combos at boundary positions ──────────
                ambig_order = [
                    (ex, pos)
                    for pos in range(8)
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
                                tt_val = sum(
                                    (v if v != -1 else 0) << i
                                    for i, v in enumerate(inferred)
                                )
                                return answer, bit_checks, (
                                    3, tt_val,
                                    [TRANSFORMATIONS[i0], TRANSFORMATIONS[i1], TRANSFORMATIONS[i2]],
                                )

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
