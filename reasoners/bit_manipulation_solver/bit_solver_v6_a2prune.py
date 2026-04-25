"""
v3_freqord + arity-2 contradiction pre-pruning for arity-3.

When arity-2 phase-1 fails for a (s0, s1) representative pair, record the
witness conflict: (pos_c, ex1, ex2) — two examples that land on the same
(a, b) slot at position pos_c but have different expected output bits.

In arity-3, before running phase-1 for (s0, s1, s2):
  1. Check if pos_c is still inside the arity-3 safe zone [lo3, safe_hi3).
  2. If yes, evaluate c_ex1 and c_ex2 — the s2-transform bits for those two
     examples at pos_c.
  3. If c_ex1 == c_ex2, the two examples still map to the same arity-3 slot
     with conflicting outputs → contradiction guaranteed → skip (O(1)).
  4. If c_ex1 != c_ex2, s2 splits the conflict; fall through to normal phase-1.

Expected benefit: ~50% of s2 values get rejected per (s0, s1) pair that
recorded a conflict, with near-zero cost (2 table lookups vs O(8 × n_ex)).
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

_S_REP: dict[int, int] = {0: 0}
_S_OPTIONS: dict[int, list[int]] = {0: [0]}

for _k in range(1, 8):
    _shl_idx = 3 * _k - 1
    _shr_idx = 3 * _k
    _rot_8mk_idx = 3 * (8 - _k) - 2

    _S_REP[_k] = _shl_idx
    _S_OPTIONS[_k] = [_shl_idx]

    _S_REP[-_k] = _rot_8mk_idx
    _S_OPTIONS[-_k] = [_rot_8mk_idx, _shr_idx]

_S_ORDER_A2 = [-1, -6, -2, -4, -3, 1, -5, 4, 5, -7, 6, 7, 2, 3, 0]
_S_ORDER_A3 = [-4, -3, -5, -2, -6, -7, -1, 2, 3, 1, 5, 7, 4, 6]


def _rotated_range(start: int, lo: int, hi: int):
    if lo >= hi:
        return
    if lo <= start < hi:
        for p in range(start, hi):
            yield p
        for p in range(lo, start):
            yield p
    else:
        yield from range(lo, hi)


def _apply_inferred(inferred: list[int], tbs: list[list[int]], target_byte: int) -> str | None:
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
    bit_checks = 0

    hot_pos: int = 0

    # ── arity 0 ──────────────────────────────────────────────────────────────
    ref = out_bytes[0]
    if all(b == ref for b in out_bytes):
        for pos in range(8):
            for ex in range(n_ex):
                bit_checks += 1
                if ((out_bytes[ex] >> (7 - pos)) & 1) != ((ref >> (7 - pos)) & 1):
                    break
            else:
                continue
            break
        else:
            return format(ref, '08b'), bit_checks, (0, ref, [])

    # ── arity 1 ──────────────────────────────────────────────────────────────
    for t0_idx in range(len(TRANSFORMATIONS)):
        tb0 = _TRANS_BYTES[t0_idx]
        inferred: list[int] = [-1, -1]
        contradiction = False
        for pos in _rotated_range(hot_pos, 0, 8):
            if contradiction:
                break
            for ex in range(n_ex):
                bit_checks += 1
                slot = (tb0[in_bytes[ex]] >> (7 - pos)) & 1
                expected = (out_bytes[ex] >> (7 - pos)) & 1
                if inferred[slot] == -1:
                    inferred[slot] = expected
                elif inferred[slot] != expected:
                    contradiction = True
                    hot_pos = pos
                    break
        if contradiction:
            continue
        answer = _apply_inferred(inferred, [tb0], target_byte)
        if answer is not None:
            tt_val = inferred[0] | ((inferred[1] if inferred[1] != -1 else 0) << 1)
            return answer, bit_checks, (1, tt_val, [TRANSFORMATIONS[t0_idx]])

    # ── arity 2 (frequency-ordered; record phase-1 conflicts for arity-3) ───
    # a2_conflicts[(s0, s1)] = (pos_c, ex1, ex2): two examples that agree on
    # the (a,b) representative bits at pos_c but have different output bits.
    a2_conflicts: dict[tuple[int, int], tuple[int, int, int]] = {}

    for s0 in _S_ORDER_A2:
        rep0 = _TRANS_BYTES[_S_REP[s0]]
        for s1 in _S_ORDER_A2:
            rep1 = _TRANS_BYTES[_S_REP[s1]]

            lo = max((abs(s) for s in (s0, s1) if s < 0), default=0)
            hi = max((s for s in (s0, s1) if s > 0), default=0)
            safe_hi = 8 - hi

            p1: list[int] = [-1, -1, -1, -1]
            slot_first_ex: list[int] = [-1, -1, -1, -1]
            p1_fail = False
            conflict_rec: tuple[int, int, int] | None = None

            for pos in _rotated_range(hot_pos, lo, safe_hi):
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
                        slot_first_ex[slot] = ex
                    elif p1[slot] != expected:
                        conflict_rec = (pos, slot_first_ex[slot], ex)
                        p1_fail = True
                        hot_pos = pos
                        break

            if p1_fail:
                a2_conflicts[(s0, s1)] = conflict_rec
                continue

            boundary_positions = [p for p in range(8) if p < lo or p >= safe_hi]
            if hot_pos in boundary_positions:
                ordered_boundary = [hot_pos] + [p for p in boundary_positions if p != hot_pos]
            else:
                ordered_boundary = boundary_positions
            ambig_order = [(ex, pos) for pos in ordered_boundary for ex in range(n_ex)]

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
                            hot_pos = pos
                            break
                    if contradiction:
                        continue
                    answer = _apply_inferred(inferred, [tb0, tb1], target_byte)
                    if answer is not None:
                        tt_val = sum((v if v != -1 else 0) << i for i, v in enumerate(inferred))
                        return answer, bit_checks, (2, tt_val, [TRANSFORMATIONS[i0], TRANSFORMATIONS[i1]])

    # ── arity 3 (frequency-ordered; a2-conflict pre-pruning) ─────────────────
    for s0 in _S_ORDER_A3:
        rep0 = _TRANS_BYTES[_S_REP[s0]]
        for s1 in _S_ORDER_A3:
            rep1 = _TRANS_BYTES[_S_REP[s1]]

            a2_conf = a2_conflicts.get((s0, s1))

            for s2 in _S_ORDER_A3:
                rep2 = _TRANS_BYTES[_S_REP[s2]]

                lo = max((abs(s) for s in (s0, s1, s2) if s < 0), default=0)
                hi = max((s for s in (s0, s1, s2) if s > 0), default=0)
                safe_hi = 8 - hi

                # O(1) pre-prune: if the arity-2 conflict is still in the
                # arity-3 safe zone and s2 doesn't split the two witnesses,
                # this triple is guaranteed to contradict → skip.
                if a2_conf is not None:
                    pos_c, ex1_c, ex2_c = a2_conf
                    if lo <= pos_c < safe_hi:
                        bit_checks += 2
                        c1 = (rep2[in_bytes[ex1_c]] >> (7 - pos_c)) & 1
                        c2 = (rep2[in_bytes[ex2_c]] >> (7 - pos_c)) & 1
                        if c1 == c2:
                            hot_pos = pos_c
                            continue

                p1: list[int] = [-1, -1, -1, -1, -1, -1, -1, -1]
                p1_fail = False
                for pos in _rotated_range(hot_pos, lo, safe_hi):
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
                            hot_pos = pos
                            break
                if p1_fail:
                    continue

                boundary_positions = [p for p in range(8) if p < lo or p >= safe_hi]
                if hot_pos in boundary_positions:
                    ordered_boundary = [hot_pos] + [p for p in boundary_positions if p != hot_pos]
                else:
                    ordered_boundary = boundary_positions
                ambig_order = [(ex, pos) for pos in ordered_boundary for ex in range(n_ex)]

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
                                    hot_pos = pos
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
