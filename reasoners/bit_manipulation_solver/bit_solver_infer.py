"""
Direct truth-table inference solver (no known-function list).

For each transform combination, infer the required truth table directly from
the examples. Any contradiction (same TT slot maps to conflicting outputs)
immediately rejects the combination. If the inferred TT is fully determined
(no unseen slots), apply it directly to the target — no known-function list
needed. Skip combinations where the target hits an unseen TT slot.

This is more general than bit_solver_tt.py: it works for any boolean function,
not just the 24 observed in the dataset.

Returns (answer, bit_checks, rule_info) with the same interface as bit_solver_tt.
rule_info = (arity, inferred_tt_as_int, [transforms])
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


def _apply_inferred(inferred: list[int], trans_bytes_for_combo: list[list[int]], target_byte: int) -> str | None:
    """Apply inferred TT to target. Returns answer string or None if any slot unseen."""
    result = 0
    for pos in range(8):
        slot = 0
        for i, tb in enumerate(trans_bytes_for_combo):
            slot |= ((tb[target_byte] >> (7 - pos)) & 1) << i
        bit = inferred[slot]
        if bit == -1:
            return None
        result |= bit << (7 - pos)
    return format(result, '08b')


def _make_check_order(n_ex: int) -> list[tuple[int, int]]:
    return [(ex, pos) for pos in range(8) for ex in range(n_ex)]


def find_rule(in_arrays: list[list[int]], out_arrays: list[list[int]], target_bits: list[int], timeout: float = 15.0) -> tuple[str | None, int, tuple | None]:
    in_bytes    = [sum(r[i] << (7 - i) for i in range(8)) for r in in_arrays]
    out_bytes   = [sum(r[i] << (7 - i) for i in range(8)) for r in out_arrays]
    target_byte = sum(target_bits[i] << (7 - i) for i in range(8))
    n_ex = len(in_bytes)
    check_order = _make_check_order(n_ex)
    bit_checks = 0

    # ── arity 0: output is same constant byte for all examples ───────────────
    ref = out_bytes[0]
    if all(b == ref for b in out_bytes):
        # verify all 8 bit positions (count checks for fair comparison)
        for ex, pos in check_order:
            bit_checks += 1
            if ((out_bytes[ex] >> (7 - pos)) & 1) != ((ref >> (7 - pos)) & 1):
                break
        else:
            return format(ref, '08b'), bit_checks, (0, ref, [])

    # ── arity 1 ──────────────────────────────────────────────────────────────
    for t0_idx in range(len(TRANSFORMATIONS)):
        tb0 = _TRANS_BYTES[t0_idx]
        inferred = [-1, -1]
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

    # ── arity 2 ──────────────────────────────────────────────────────────────
    for t0_idx in range(len(TRANSFORMATIONS)):
        tb0 = _TRANS_BYTES[t0_idx]
        for t1_idx in range(len(TRANSFORMATIONS)):
            if t1_idx == t0_idx:
                continue
            tb1 = _TRANS_BYTES[t1_idx]
            inferred = [-1, -1, -1, -1]
            contradiction = False
            for ex, pos in check_order:
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
                return answer, bit_checks, (2, tt_val, [TRANSFORMATIONS[t0_idx], TRANSFORMATIONS[t1_idx]])

    # ── arity 3 ──────────────────────────────────────────────────────────────
    for t0_idx in range(len(TRANSFORMATIONS)):
        tb0 = _TRANS_BYTES[t0_idx]
        for t1_idx in range(len(TRANSFORMATIONS)):
            if t1_idx == t0_idx:
                continue
            tb1 = _TRANS_BYTES[t1_idx]
            for t2_idx in range(len(TRANSFORMATIONS)):
                if t2_idx == t0_idx or t2_idx == t1_idx:
                    continue
                tb2 = _TRANS_BYTES[t2_idx]
                inferred = [-1, -1, -1, -1, -1, -1, -1, -1]
                contradiction = False
                for ex, pos in check_order:
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
                    tt_val = sum((v if v != -1 else 0) << i for i, v in enumerate(inferred))
                    return answer, bit_checks, (3, tt_val, [TRANSFORMATIONS[t0_idx], TRANSFORMATIONS[t1_idx], TRANSFORMATIONS[t2_idx]])

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
