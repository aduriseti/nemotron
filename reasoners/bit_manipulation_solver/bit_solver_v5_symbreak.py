"""
Symmetry-breaking arity-3 solver.

Key optimization over infer3: instead of enumerating 2744 ordered (s0,s1,s2)
triples and paying ~3.5 bit-checks per wrong ordered triple (21 total per
unordered triple since all 6 orderings are tried), enumerate the 560 distinct
UNORDERED triples and check all their permutations JOINTLY in a single
(ex, pos) pass.

Each bit-check contributes to ALL permutations' truth tables simultaneously.
Expected bit-checks per wrong unordered triple: ~8.6 (vs 21 sequential).
This gives 2.4× fewer bit-checks for arity-3, covering 73% of the unordered
search space within the arity-3 budget vs 36% currently.

Retains infer3's hot_pos VSIDS and frequency ordering.
"""

import re
import sys
from itertools import combinations_with_replacement, permutations as _iperms
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

_RANK3 = {s: i for i, s in enumerate(_S_ORDER_A3)}


def _build_a3_triples():
    """
    Build all 560 unordered triples from _S_ORDER_A3, sorted by
    (max_rank, mid_rank, min_rank) ascending so high-frequency triples come first.
    Each entry: (unordered_triple, list_of_index_permutations).
    Index permutation ip means: slot position j uses input bit from unordered[ip[j]].
    """
    raw = list(combinations_with_replacement(_S_ORDER_A3, 3))

    def key(t):
        return tuple(sorted(_RANK3[s] for s in t))

    result = []
    for t in sorted(raw, key=key):
        seen = set()
        idx_perms = []
        for ip in _iperms(range(3)):
            s_ord = tuple(t[ip[i]] for i in range(3))
            if s_ord not in seen:
                seen.add(s_ord)
                idx_perms.append(ip)
        result.append((t, idx_perms))
    return result


_A3_TRIPLES = _build_a3_triples()


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

    # ── arity 2 (frequency-ordered) ──────────────────────────────────────────
    for s0 in _S_ORDER_A2:
        rep0 = _TRANS_BYTES[_S_REP[s0]]
        for s1 in _S_ORDER_A2:
            rep1 = _TRANS_BYTES[_S_REP[s1]]

            lo = max((abs(s) for s in (s0, s1) if s < 0), default=0)
            hi = max((s for s in (s0, s1) if s > 0), default=0)
            safe_hi = 8 - hi

            p1: list[int] = [-1, -1, -1, -1]
            p1_fail = False
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

    # ── arity 3 (symmetry-breaking: joint phase-1 for all permutations) ──────
    for unordered, idx_perms in _A3_TRIPLES:
        lo = max((abs(s) for s in unordered if s < 0), default=0)
        hi = max((s for s in unordered if s > 0), default=0)
        safe_hi = 8 - hi

        # Representative transform tables for the unordered triple
        reps = [_TRANS_BYTES[_S_REP[s]] for s in unordered]

        # Phase-1: build TT for each permutation jointly
        n_p = len(idx_perms)
        infs = [[-1] * 8 for _ in range(n_p)]
        failed = [False] * n_p

        for pos in _rotated_range(hot_pos, lo, safe_hi):
            if all(failed):
                break
            for ex in range(n_ex):
                bit_checks += 1
                # Compute 3 input bits once for this (ex, pos)
                b0 = (reps[0][in_bytes[ex]] >> (7 - pos)) & 1
                b1 = (reps[1][in_bytes[ex]] >> (7 - pos)) & 1
                b2 = (reps[2][in_bytes[ex]] >> (7 - pos)) & 1
                bits3 = (b0, b1, b2)
                expected = (out_bytes[ex] >> (7 - pos)) & 1

                for pidx in range(n_p):
                    if failed[pidx]:
                        continue
                    ip = idx_perms[pidx]
                    slot = bits3[ip[0]] | (bits3[ip[1]] << 1) | (bits3[ip[2]] << 2)
                    if infs[pidx][slot] == -1:
                        infs[pidx][slot] = expected
                    elif infs[pidx][slot] != expected:
                        failed[pidx] = True
                        hot_pos = pos

                if all(failed):
                    break

        # Phase-2: resolve type ambiguity for each surviving permutation
        boundary_positions = [p for p in range(8) if p < lo or p >= safe_hi]
        if hot_pos in boundary_positions:
            ordered_boundary = [hot_pos] + [p for p in boundary_positions if p != hot_pos]
        else:
            ordered_boundary = boundary_positions
        ambig_order = [(ex, pos) for pos in ordered_boundary for ex in range(n_ex)]

        for pidx in range(n_p):
            if failed[pidx]:
                continue
            ip = idx_perms[pidx]
            s0, s1, s2 = unordered[ip[0]], unordered[ip[1]], unordered[ip[2]]
            p1 = infs[pidx]

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
