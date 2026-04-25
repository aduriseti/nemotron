# v8 Sliding-Window Stride Solver — Benchmark Report

## Approach

v8 replaces transformation-family enumeration (rot/shl/shr × signed offsets) with
**stride-enumeration over uniformly-strided input bit windows**:

- **Window 1**: reads `input[(q + anchor) % 8]`
- **Window 2**: reads `input[(q+anchor)%8]`, `input[(q+anchor+s)%8]`
- **Window 3**: arithmetic triple `(q+anchor)%8`, `(q+anchor+s)%8`, `(q+anchor+2s)%8`

For each `(window, stride s, anchor a, start position q)`, a TT is built
incrementally extending the run until contradiction. Runs are grouped by stride.
Stitching is stride-compatible: only runs from the same stride group s are
combined; window-1 runs (no stride) are eligible if their anchor appears in the
group's offsets. The stride group with the longest max run is tried first.

No boundary phase-2 — modular arithmetic throughout.

## Results (300 problems)

```
Solver          Acc   Wrong  None  Mean BC   p50     p90    ms/q
----------------------------------------------------------------
v1_base         294/300   4    2    4,575   1,159  13,083   2.59
v3_freqord      294/300   4    2    3,233     940   9,847   2.15
v6_a2prune      294/300   4    2    3,187     940   9,606   2.15  ← best v1-family
v8_sliding      224/300  63   13    6,759   5,026  15,288   5.76  ← this work
```

### Accuracy at bit-check budgets
```
Solver        @1K   @2K   @3K   @5K   @10K
-------------------------------------------
v1_base       42.3% 60.7% 64.0% 71.3%  82.0%
v3_freqord    50.3% 62.7% 68.3% 76.3%  89.0%
v8_sliding     0.0%  3.3% 15.3% 34.0%  59.7%
```

## Findings

### 1. Wrong answers from coincidentally consistent strides (63 wrong vs 4 for v1)

All 59 cases where v8 is wrong and v1 is correct involve **arity-2/3 rules with
mixed transformations** (e.g. `shl_1 + shl_7`, `rot_4 + shr_2 + shl_2`). A
wrong stride — most commonly s=1 or s=2 — happens to produce a longer
consistent run than the correct stride because coincidental bit patterns in the
training examples don't expose a contradiction early enough.

The stride group selection heuristic (longest max run first) reliably picks the
wrong group in these cases. The verification step is **tautological**: TTs are
built from training examples, so predicting those same examples trivially
succeeds.

Example failure:
```
Rule:  shl_1 + shl_7  (arity-2)
v8 picks: stride s=1 (coincidentally consistent), produces wrong bit 0
v1 finds: the correct two-transformation TT
```

### 2. High bit-check count (mean 6,759 vs 3,187 for v6)

All runs for all stride groups are built before any stitching attempt. There is
no early exit. The bit-check count reflects the full enumeration cost
regardless of problem difficulty. A length-8 rotation rule still costs the same
as an arity-3 shift rule.

### 3. Zero accuracy below @2K budget

Because all runs are always evaluated, minimum effective cost per query is ~5K
checks. Simple problems (arity-1 rotations) that v1 solves in ~216 checks cost
v8 ~5K.

## Root cause analysis

| Issue | Cause | Fix direction |
|---|---|---|
| Wrong strides win selection | "Longest max run" is not a reliable proxy for correct stride | Cross-validate: hold one example out, check if stride group predicts it correctly |
| Tautological verification | TTs built from same examples used to verify | Cross-validation or leave-one-out |
| No early stopping | All runs built upfront | Stop as soon as stride group achieves verified full coverage |
| High cost for easy problems | No fast path for arity-1/2 | Try window-1 runs first; only enumerate window-2/3 if needed |

## What works and what doesn't

**Works well:** Pure rotation rules (e.g. rot_3). Window-2 with the correct
stride gives run_len=8, the correct group wins, prediction is exact. This
subset would achieve near-100% accuracy with early stopping.

**Fails:** Any arity-2/3 rule where mixed transformations have different
effective strides. The stride-enumeration model assumes a single uniform stride
governs all window elements; v1's signed-offset model correctly handles
arbitrary transformation combinations.

## Conclusion

Stride enumeration has a genuinely smaller outer search space (1,344 candidates
vs ~29,000 for v1 arity-3) but does not reliably identify the correct stride
with limited training data. The wrong-answer rate (21%) makes v8 unsuitable
as a standalone solver. 

**Recommended next steps:**
1. Use v8 as a **fast first-pass** for arity-1 rotation detection only
   (window-1 + window-2 with full-length-8 single run, no stitching).
2. Fall through to v1 (or v6/v7) for everything else.
3. Or: add cross-validation to stride selection — hold one example out and
   verify the chosen stride group predicts it correctly before committing.
