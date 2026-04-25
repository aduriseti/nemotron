# Bit Manipulation Solver: Optimization Evolution Report

**Dataset**: 300 bit_manipulation problems (first 300 of 1602 total)  
**Metric of interest**: Accuracy at fixed bit-check budgets, especially @5K  
**All runs**: unlimited budget, no ablation

---

## Solver Descriptions

| Solver | Key optimization over previous |
|--------|-------------------------------|
| `v1_base` | Baseline: direct truth-table inference, arity 0→1→2→3 |
| `v2_vsids` | + VSIDS hot_pos: carry last-contradiction bit-position across arities |
| `v3_freqord` | + Frequency-ordered s-value enumeration (`_S_ORDER_A2/A3`); s=0 omitted from arity-3 |
| `v4_exlimit` | v3 + n_ex_limit: truncate to first N examples (run here with N=0, i.e. disabled → identical to v3) |
| `v5_symbreak` | v3 + joint-permutation arity-3: check 560 unordered triples with all permutations simultaneously |
| `v6_a2prune` | v3 + single-pair a2 conflict prune: record `(pos_c, ex1, ex2)` from arity-2 failures; skip arity-3 triples in O(1) if s2 doesn't split witnesses |
| `v7_3pairs` | v6 + check all three pairwise conflicts `(s0,s1)`, `(s0,s2)`, `(s1,s2)` — **has regression bug, results invalid** |

---

## Raw Results

### Overall Accuracy and Bit-Check Distribution

```
Solver          Acc      Wrong  None   Mean BC    p50    p90    p95     p99   ms/q
v1_base      294/300      4     2     4,575    1,159  13,083  20,011  37,154  2.6ms
v2_vsids     294/300      4     2     3,584      986  10,610  13,976  21,073  2.5ms
v3_freqord   294/300      4     2     3,233      940   9,847  13,186  25,120  2.2ms
v4_exlimit   294/300      4     2     3,233      940   9,847  13,186  25,120  2.2ms  (= v3)
v5_symbreak  294/300      4     2     5,047      940  17,742  21,413  26,536  3.0ms  ✗ WORSE
v6_a2prune   294/300      4     2     3,187      940   9,606  13,076  24,156  2.2ms
v7_3pairs    285/300      4    11     4,010      940  11,653  16,575  33,996  2.8ms  ✗ BUG
```

### Accuracy at Fixed Bit-Check Budgets

| Solver | @1K | @2K | @3K | @5K | @10K |
|--------|-----|-----|-----|-----|------|
| v1_base | 42.3% | 60.7% | 64.0% | 71.3% | 82.0% |
| v2_vsids | 50.3% | 61.3% | 66.7% | 74.3% | 86.3% |
| v3_freqord | 50.3% | 62.7% | 68.3% | **76.3%** | 89.0% |
| v4_exlimit | 50.3% | 62.7% | 68.3% | **76.3%** | 89.0% |
| v5_symbreak | 50.3% | 61.0% | 66.0% | 68.0% | 77.7% |
| v6_a2prune | 50.3% | 62.0% | 67.3% | 76.0% | **89.3%** |
| v7_3pairs | 50.3% | 61.7% | 66.3% | 73.3% | 87.3% |

### Per-Arity p90 Bit-Checks

| Solver | arity-1 | arity-2 | arity-3 |
|--------|---------|---------|---------|
| v1_base | 848 | 1,410 | 20,510 |
| v2_vsids | 216 | 1,189 | 14,844 |
| v3_freqord | 216 | 1,510 | 13,775 |
| v4_exlimit | 216 | 1,510 | 13,775 |
| v5_symbreak | 216 | 1,510 | 22,804 |
| v6_a2prune | 216 | 1,510 | 13,167 |
| v7_3pairs | 216 | 1,510 | 13,520 |

---

## What Worked

### v2: VSIDS hot_pos (+3pt @5K)
Starting each candidate's phase-1 at the last contradiction position dramatically reduces arity-1 p90 (848→216) and arity-3 p90 (20,510→14,844). The bit position that last caused a contradiction is often the most discriminating one for subsequent candidates.

### v3: Frequency ordering (+2pt @5K)
Enumerating s-values in empirically derived frequency order puts the correct s-triple earlier in the search. Arity-3 p90 drops from 14,844→13,775. s=0 excluded from arity-3 (zero occurrences in training data).

### v6: Single-pair a2 conflict prune (marginal, +0.3pt @10K)
Records the first conflict `(pos_c, ex1, ex2)` from each arity-2 phase-1 failure. In arity-3, checks if s2 splits the two witnesses at pos_c in O(1) (2 table lookups). If not, the arity-2 contradiction survives into arity-3 → skip.

**Why gain is small**: Phase-1 terminates in ~3.5 bit-checks on average (birthday paradox: 8 slots, 10 examples). The prune check costs 2 lookups and fires ~50% of the time. Net savings per pruned triple: ~1.5 bit-checks. Not transformative.

---

## What Didn't Work

### v5: Symmetry-breaking joint permutation (large regression)
**Theory**: Enumerate 560 unordered triples instead of 2744 ordered. Check all permutations jointly in one (ex,pos) pass. Expected 2.4× fewer bit-checks.

**Reality**: Arity-3 p90 went from 13,775→22,804. The joint pass must wait until ALL permutations fail before moving on — you pay for the slowest permutation, not the average. With n=6 permutations, E[max] ≈ 2.45× E[single], and VSIDS hot_pos becomes noisy (multiple updates per group). Net result: more work.

### v7: Three-pair prune (regression bug + fundamentally marginal)
Checking all three pairwise conflicts `(s0,s1)`, `(s0,s2)`, `(s1,s2)` should give ~87.5% prune rate vs 50% for one pair.

**Implementation bug**: 11 None answers vs 2 baseline — valid triples are being incorrectly pruned. Likely a key-ordering or table-assignment error in the `(s0,s2)` or `(s1,s2)` lookups.

**Fundamental problem** (even if bug-fixed): 3-pair check costs up to 6 lookups. Phase-1 costs ~3.5 bit-checks. The overhead exceeds the savings:

```
Expected cost per triple with 3-pair prune:
  50% pruned at check 1:  cost = 2
  25% pruned at check 2:  cost = 4
  12.5% pruned at check 3: cost = 6
  12.5% reach phase-1:    cost = 9.5

Weighted average = 3.94 > 3.5 (just running phase-1 directly)
```

The prune approach is only beneficial when phase-1 is expensive — i.e., many more examples or larger alphabet.

---

## Current Best: v3_freqord

**76.3% @ 5K budget**, 2.2ms/query, 294/300 correct at unlimited budget.

The 6 unsolvable problems (4 wrong, 2 None) are structural limits:
- **4 wrong**: multiple s-triples are consistent with the examples; solver picks a wrong one
- **2 None**: the truth-table slot needed for the query was never observed in any example

---

## What Could Still Help

1. **Multiple conflicts per (s0,s1) pair**: recording k conflicts gives `(1/2)^k` prune rate per pair. But the cost analysis above shows this is still marginal given phase-1's cheapness.

2. **Arity-2 conflicts to set hot_pos** (free win already in v6): `pos_c` from the conflict record is a good hot_pos initialization for arity-3 — already exploited.

3. **Better disambiguation of the 4 wrong-answer cases**: those require knowing which of several consistent rules is the "intended" one — needs either more examples or a different prior (e.g., prefer simpler rules).

4. **XOR/AND/OR rule detection**: the current solver handles `f(T0, T1, T2)` as an arbitrary 8-entry truth table. Some rules may be structurally simpler (XOR of two transforms, etc.) and could be detected earlier.

---

*Generated from benchmark_all.py on 300 bit_manipulation problems.*
