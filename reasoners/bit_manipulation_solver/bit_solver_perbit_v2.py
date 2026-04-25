"""
Per-bit boolean decomposition solver v2 — evidence-driven, no truth-table enumeration.

For each output bit independently:
  1. Try constants.
  2. For arity 1, 2, 3: iterate over all position combinations.
     - Build the partial truth table directly from examples (slot → output_bit).
     - Reject the position set if any slot is contradictory (same input, different output).
     - Only record a prediction when the TARGET's input combination was directly
       observed in the training examples (not extrapolated).
  3. Collect all valid predictions at the lowest matching arity and use plurality vote.
     Agreement across all consistent position sets is the strongest possible signal.

This eliminates the false-positive problem in v1 (which accepted any truth table that
happened to match all 8 examples, leading to ~51% accuracy from chance coincidences).
"""

import re
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def find_rule(
    in_arrays: list[list[int]],
    out_arrays: list[list[int]],
    target_bits: list[int],
    timeout: float = 15.0,
) -> tuple[str | None, int, list | None]:
    n_ex = len(in_arrays)
    in_cols  = [[in_arrays[ex][j]  for ex in range(n_ex)] for j in range(8)]
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

        # ── arity 1 / 2 / 3: evidence-driven partial truth table ────────────
        #
        # For each position set, build partial_tt[slot] = output_bit from examples.
        # Reject on contradiction.  Record prediction only when target slot is seen.
        # Use plurality vote across all position sets that cover the target.

        for arity, pos_iter in [
            (1, ((j,)          for j      in range(8))),
            (2, ((j, k)        for j, k   in combinations(range(8), 2))),
            (3, ((j, k, l)     for j, k, l in combinations(range(8), 3))),
        ]:
            votes = {0: 0, 1: 0}

            for positions in pos_iter:
                partial_tt: dict[int, int] = {}
                consistent = True

                for ex in range(n_ex):
                    total_checks += 1
                    slot = 0
                    for i, j in enumerate(positions):
                        slot |= in_cols[j][ex] << i
                    out_bit = out_col[ex]
                    if slot in partial_tt:
                        if partial_tt[slot] != out_bit:
                            consistent = False
                            break
                    else:
                        partial_tt[slot] = out_bit

                if not consistent:
                    continue

                tgt_slot = 0
                for i, j in enumerate(positions):
                    tgt_slot |= target_bits[j] << i

                if tgt_slot in partial_tt:
                    votes[partial_tt[tgt_slot]] += 1

            total_votes = votes[0] + votes[1]
            if total_votes == 0:
                continue   # no position set covered the target at this arity

            # Plurality vote: whichever value has more supporting position sets wins.
            # Ties broken toward 0 (arbitrary, rarely reached).
            pred = 1 if votes[1] > votes[0] else 0

            # Build a representative rule for reporting
            best_rule = (arity, -1, [])
            answer_bits.append(pred)
            per_bit_rules.append(best_rule)
            found = True
            break   # don't try higher arity if this one gave any coverage

        if not found:
            answer_bits.append(None)
            per_bit_rules.append(None)

    if any(b is None for b in answer_bits):
        return None, total_checks, None

    return ''.join(str(b) for b in answer_bits), total_checks, per_bit_rules


def solve_bit_manipulation(prompt: str, timeout: float = 15.0):
    ex_matches  = re.findall(r'([01]{8})\s*->\s*([01]{8})', prompt)
    query_match = re.search(r'(?:output for:|determine the output for:)\s*([01]{8})', prompt)
    if not ex_matches or not query_match:
        return None, 0, None
    target_bits = [int(b) for b in query_match.group(1)]
    in_arrays   = [[int(ex_matches[i][0][j]) for j in range(8)] for i in range(len(ex_matches))]
    out_arrays  = [[int(ex_matches[i][1][j]) for j in range(8)] for i in range(len(ex_matches))]
    return find_rule(in_arrays, out_arrays, target_bits, timeout)
