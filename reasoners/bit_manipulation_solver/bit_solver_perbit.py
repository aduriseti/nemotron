"""
Per-bit boolean decomposition solver.

Each output bit is solved independently as a boolean function of input bit positions
(NOT shifted/rotated bytes — raw bit indices 0-7).

Search order per output bit:
  arity-0: constants (0, 1)
  arity-1: identity, NOT  — over all 8 input positions
  arity-2: 10 non-trivial 2-input gates  — over all C(8,2)=28 unordered pairs
  arity-3: 254 non-constant 3-input truth tables  — over all C(8,3)=56 unordered triples
             (known nemotron dataset truth tables tried first for speed)

Truth tables are indexed as:  slot = a | (b<<1) | (c<<2)
where a,b,c = input bits at the chosen positions (in sorted order).
Trying all 254 arity-3 values covers every permutation of the triple implicitly.
"""

import re
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Arity-2 non-trivial truth tables in approximate frequency order
# (excludes constants tt=0,15 and single-input projections tt=3,5,10,12)
# tt indexed by slot = a | (b<<1)
_A2_TTS = [6, 14, 8, 7, 1, 9, 2, 4, 11, 13]
# names:  XOR OR AND NAND NOR XNOR  A&~B  ~A&B  ~A|B  A|~B

# Arity-3 truth tables: known nemotron dataset functions first (from KNOWN_FUNCTIONS),
# then all remaining non-constant values (0 and 255 excluded).
_A3_KNOWN = [235, 234, 169, 168, 232, 109, 226, 149, 106, 89, 138, 253, 100, 171, 125]
_A3_TTS = _A3_KNOWN + [tt for tt in range(1, 255) if tt not in _A3_KNOWN]


def find_rule(
    in_arrays: list[list[int]],
    out_arrays: list[list[int]],
    target_bits: list[int],
    timeout: float = 15.0,
) -> tuple[str | None, int, list | None]:
    """
    Returns (answer, total_bit_checks, per_bit_rules).
    per_bit_rules[i] = (arity, tt, [positions]) for output bit i.
    Returns (None, checks, None) if any output bit cannot be solved.
    """
    n_ex = len(in_arrays)

    # Transpose: in_cols[j][ex] = bit j of input for example ex
    in_cols = [[in_arrays[ex][j] for ex in range(n_ex)] for j in range(8)]
    out_cols = [[out_arrays[ex][op] for ex in range(n_ex)] for op in range(8)]

    total_checks = 0
    answer_bits: list[int | None] = []
    per_bit_rules: list[tuple | None] = []

    for op in range(8):
        out_col = out_cols[op]
        found = False

        # ── arity 0: constants ──────────────────────────────────────────────
        for const in (0, 1):
            total_checks += n_ex
            if all(v == const for v in out_col):
                answer_bits.append(const)
                per_bit_rules.append((0, const, []))
                found = True
                break
        if found:
            continue

        # ── arity 1 ─────────────────────────────────────────────────────────
        for j in range(8):
            icj = in_cols[j]
            for tt in (0b10, 0b01):   # 0b10 = identity, 0b01 = NOT
                chk = 0
                ok = True
                for ex in range(n_ex):
                    chk += 1
                    if ((tt >> icj[ex]) & 1) != out_col[ex]:
                        ok = False
                        break
                total_checks += chk
                if ok:
                    answer_bits.append((tt >> target_bits[j]) & 1)
                    per_bit_rules.append((1, tt, [j]))
                    found = True
                    break
            if found:
                break
        if found:
            continue

        # ── arity 2 ─────────────────────────────────────────────────────────
        for j, k in combinations(range(8), 2):
            icj = in_cols[j]
            ick = in_cols[k]
            for tt in _A2_TTS:
                chk = 0
                ok = True
                for ex in range(n_ex):
                    chk += 1
                    slot = icj[ex] | (ick[ex] << 1)
                    if ((tt >> slot) & 1) != out_col[ex]:
                        ok = False
                        break
                total_checks += chk
                if ok:
                    slot_tgt = target_bits[j] | (target_bits[k] << 1)
                    answer_bits.append((tt >> slot_tgt) & 1)
                    per_bit_rules.append((2, tt, [j, k]))
                    found = True
                    break
            if found:
                break
        if found:
            continue

        # ── arity 3 ─────────────────────────────────────────────────────────
        for j, k, l in combinations(range(8), 3):
            icj = in_cols[j]
            ick = in_cols[k]
            icl = in_cols[l]
            for tt in _A3_TTS:
                chk = 0
                ok = True
                for ex in range(n_ex):
                    chk += 1
                    slot = icj[ex] | (ick[ex] << 1) | (icl[ex] << 2)
                    if ((tt >> slot) & 1) != out_col[ex]:
                        ok = False
                        break
                total_checks += chk
                if ok:
                    slot_tgt = target_bits[j] | (target_bits[k] << 1) | (target_bits[l] << 2)
                    answer_bits.append((tt >> slot_tgt) & 1)
                    per_bit_rules.append((3, tt, [j, k, l]))
                    found = True
                    break
            if found:
                break

        if not found:
            answer_bits.append(None)
            per_bit_rules.append(None)

    if any(b is None for b in answer_bits):
        return None, total_checks, None

    return ''.join(str(b) for b in answer_bits), total_checks, per_bit_rules


def solve_bit_manipulation(prompt: str, timeout: float = 15.0):
    ex_matches = re.findall(r'([01]{8})\s*->\s*([01]{8})', prompt)
    query_match = re.search(r'(?:output for:|determine the output for:)\s*([01]{8})', prompt)
    if not ex_matches or not query_match:
        return None, 0, None
    target_bits = [int(b) for b in query_match.group(1)]
    in_arrays = [[int(ex_matches[i][0][j]) for j in range(8)] for i in range(len(ex_matches))]
    out_arrays = [[int(ex_matches[i][1][j]) for j in range(8)] for i in range(len(ex_matches))]
    return find_rule(in_arrays, out_arrays, target_bits, timeout)
