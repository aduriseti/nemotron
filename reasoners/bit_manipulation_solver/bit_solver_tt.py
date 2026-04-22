"""
Frequency-ordered truth-table solver.

Enumerates the 24 boolean functions observed in the dataset in order of
frequency. For each function, tries all valid transform assignments and
checks one bit at a time for fast early invalidation.

Returns (answer, bit_checks) where bit_checks is the total number of
single-bit comparisons made before the answer was found.
"""

import re
import sys
from itertools import permutations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

_MASK = 0xFF

TRANSFORMATIONS = [('rot', 0)]
for _k in range(1, 8):
    TRANSFORMATIONS.extend([('rot', _k), ('shl', _k), ('shr', _k)])

# (arity, tt, dataset_freq) sorted by descending frequency across full dataset.
# Arity-2 truth tables are 4-bit (indexed by A|B<<1).
# Arity-3 truth tables are 8-bit (indexed by A|B<<1|C<<2).
KNOWN_FUNCTIONS = [
    (2, 0b0110, 324),   # XOR
    (2, 0b1110, 289),   # OR
    (1, 0b10,   149),   # identity
    (3,  235,   164),
    (2, 0b1000, 131),   # AND
    (2, 0b0010,  86),   # NOT(A) AND B
    (3,  234,    70),
    (3,  169,    61),
    (3,  168,    61),
    (3,  232,    54),
    (3,  109,    53),
    (3,  226,    46),
    (2, 0b1001,  41),   # XNOR
    (2, 0b1011,  25),   # A IMPLIES B
    (3,  149,    13),
    (3,  106,    10),
    (3,   89,     6),
    (3,  138,     4),
    (3,  253,     3),
    (3,  100,     2),
    (2, 0b0001,   2),   # NOR
    (3,  171,     1),
    (3,  125,     1),
    (2, 0b0111,   1),   # NAND
    (0,    0,     3),   # constant 0
    (0,    1,     2),   # constant 1
]


def _canonical_perms(tt: int, arity: int) -> list:
    """Return one representative permutation per distinct permuted truth table.

    Avoids redundant transform assignments for symmetric/partially-symmetric
    functions (e.g., XOR(A,B) == XOR(B,A) so only one ordering is needed).
    """
    seen: dict[int, tuple] = {}
    for perm in permutations(range(arity)):
        new_tt = 0
        for combo in range(1 << arity):
            inputs = [(combo >> i) & 1 for i in range(arity)]
            permuted = [inputs[perm[i]] for i in range(arity)]
            orig_idx = sum(permuted[i] << i for i in range(arity))
            bit = (tt >> orig_idx) & 1
            new_tt |= bit << combo
        if new_tt not in seen:
            seen[new_tt] = perm
    return list(seen.values())


def _transform_bit(byte_val: int, ttype: str, k: int, pos: int) -> int:
    if ttype == 'rot':
        src = (pos + k) & 7
    elif ttype == 'shl':
        src = pos + k
        if src >= 8:
            return 0
    else:
        src = pos - k
        if src < 0:
            return 0
    return (byte_val >> (7 - src)) & 1


def _apply(tt: int, arity: int, ordered_trans: list, target_byte: int) -> str:
    result = 0
    for pos in range(8):
        vals = [_transform_bit(target_byte, t, k, pos) for t, k in ordered_trans]
        idx = sum(vals[i] << i for i in range(arity))
        bit = (tt >> idx) & 1
        result |= bit << (7 - pos)
    return format(result, '08b')


# Check order: interleave examples before advancing bit position so a wrong
# candidate is rejected as early as possible across the example set.
def _make_check_order(n_ex: int) -> list:
    return [(ex, pos) for pos in range(8) for ex in range(n_ex)]


def find_rule(in_arrays, out_arrays, target_bits, timeout=15.0):
    """Returns (answer, bit_checks, rule_info) where rule_info = (arity, tt, ordered_transforms)."""
    in_bytes    = [sum(r[i] << (7 - i) for i in range(8)) for r in in_arrays]
    out_bytes   = [sum(r[i] << (7 - i) for i in range(8)) for r in out_arrays]
    target_byte = sum(target_bits[i] << (7 - i) for i in range(8))
    n_ex = len(in_bytes)
    check_order = _make_check_order(n_ex)
    bit_checks = 0

    for arity, tt, _ in KNOWN_FUNCTIONS:

        if arity == 0:
            const_byte = 0xFF if tt else 0x00
            ok = True
            for ex, pos in check_order:
                bit_checks += 1
                if ((out_bytes[ex] >> (7 - pos)) & 1) != ((const_byte >> (7 - pos)) & 1):
                    ok = False
                    break
            if ok:
                return format(const_byte, '08b'), bit_checks, (0, tt, [])
            continue

        if arity == 1:
            for t0 in TRANSFORMATIONS:
                for ex, pos in check_order:
                    bit_checks += 1
                    a = _transform_bit(in_bytes[ex], t0[0], t0[1], pos)
                    if ((tt >> a) & 1) != ((out_bytes[ex] >> (7 - pos)) & 1):
                        break
                else:
                    return _apply(tt, 1, [t0], target_byte), bit_checks, (1, tt, [t0])
            continue

        canon_perms = _canonical_perms(tt, arity)

        if arity == 2:
            for t0 in TRANSFORMATIONS:
                for t1 in TRANSFORMATIONS:
                    if t0 == t1:
                        continue
                    for perm in canon_perms:
                        ordered = [[t0, t1][perm[i]] for i in range(2)]
                        for ex, pos in check_order:
                            bit_checks += 1
                            a = _transform_bit(in_bytes[ex], ordered[0][0], ordered[0][1], pos)
                            b = _transform_bit(in_bytes[ex], ordered[1][0], ordered[1][1], pos)
                            idx = a | (b << 1)
                            if ((tt >> idx) & 1) != ((out_bytes[ex] >> (7 - pos)) & 1):
                                break
                        else:
                            return _apply(tt, 2, ordered, target_byte), bit_checks, (2, tt, ordered)
            continue

        if arity == 3:
            for t0 in TRANSFORMATIONS:
                for t1 in TRANSFORMATIONS:
                    if t1 == t0:
                        continue
                    for t2 in TRANSFORMATIONS:
                        if t2 == t0 or t2 == t1:
                            continue
                        for perm in canon_perms:
                            ordered = [[t0, t1, t2][perm[i]] for i in range(3)]
                            for ex, pos in check_order:
                                bit_checks += 1
                                a = _transform_bit(in_bytes[ex], ordered[0][0], ordered[0][1], pos)
                                b = _transform_bit(in_bytes[ex], ordered[1][0], ordered[1][1], pos)
                                c = _transform_bit(in_bytes[ex], ordered[2][0], ordered[2][1], pos)
                                idx = a | (b << 1) | (c << 2)
                                if ((tt >> idx) & 1) != ((out_bytes[ex] >> (7 - pos)) & 1):
                                    break
                            else:
                                return _apply(tt, 3, ordered, target_byte), bit_checks, (3, tt, ordered)

    return None, bit_checks, None


def solve_bit_manipulation(prompt: str, timeout: float = 15.0):
    ex_matches  = re.findall(r'([01]{8})\s*->\s*([01]{8})', prompt)
    query_match = re.search(r'(?:output for:|determine the output for:)\s*([01]{8})', prompt)
    if not ex_matches or not query_match:
        return None, 0, None
    target_bits = [int(b) for b in query_match.group(1)]
    in_arrays   = [[int(ex_matches[i][0][j]) for j in range(8)] for i in range(len(ex_matches))]
    out_arrays  = [[int(ex_matches[i][1][j]) for j in range(8)] for i in range(len(ex_matches))]
    return find_rule(in_arrays, out_arrays, target_bits, timeout)
