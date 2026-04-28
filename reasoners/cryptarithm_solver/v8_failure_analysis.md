# v8 Failure Analysis

Date: 2026-04-28

Solver: `solve_v8` (full 11-op support, 2s deadline per pipeline, greedy)
Test set: 657 cryptarithm puzzles with target_op in supported set

## Outcome categories

- **correct** — golden answer matches.
- **timeout** — no answer; puzzle elapsed ≥ 1.9s, so at least one pipeline hit its 2s deadline.
- **exhausted** — no answer; puzzle elapsed < 1.9s, so all pipelines exited fast without finding a cipher (pruning rejected every candidate).
- **wrong** — cipher found, but its extrapolation to the target query differs from golden (cipher ambiguity).

## Overall

| Outcome | Count | % |
|---------|------:|---:|
| Correct | 407 | 61.9% |
| Wrong (cipher ambiguity) | 207 | 31.5% |
| Timeout (≥1.9s, no answer) | 0 | 0.0% |
| Exhausted (<1.9s, no answer) | 43 | 6.5% |

Cipher ambiguity dominates: 207 wrong-cipher cases vs 43 no-answer cases (timeout + exhausted).

## Per-op breakdown

| Op | Total | ✓ | Timeout | Exhausted | Wrong | %✓ | %Timeout | %Exhausted | %Wrong |
|----|------:|--:|--------:|----------:|------:|---:|---------:|-----------:|-------:|
| add | 113 | 70 | 0 | 10 | 33 | 61.9% | 0.0% | 8.8% | 29.2% |
| sub | 76 | 48 | 0 | 3 | 25 | 63.2% | 0.0% | 3.9% | 32.9% |
| mul | 143 | 105 | 0 | 0 | 38 | 73.4% | 0.0% | 0.0% | 26.6% |
| cat | 59 | 58 | 0 | 0 | 1 | 98.3% | 0.0% | 0.0% | 1.7% |
| add1 | 35 | 23 | 0 | 1 | 11 | 65.7% | 0.0% | 2.9% | 31.4% |
| addm1 | 33 | 19 | 0 | 1 | 13 | 57.6% | 0.0% | 3.0% | 39.4% |
| mul1 | 39 | 15 | 0 | 12 | 12 | 38.5% | 0.0% | 30.8% | 30.8% |
| mulm1 | 23 | 8 | 0 | 4 | 11 | 34.8% | 0.0% | 17.4% | 47.8% |
| sub_abs | 96 | 42 | 0 | 9 | 45 | 43.8% | 0.0% | 9.4% | 46.9% |
| sub_neg_abs | 23 | 10 | 0 | 2 | 11 | 43.5% | 0.0% | 8.7% | 47.8% |
| max_mod_min | 17 | 9 | 0 | 1 | 7 | 52.9% | 0.0% | 5.9% | 41.2% |

## By category

| Category | n | ✓ | None | Wrong |
|----------|--:|--:|-----:|------:|
| cryptarithm_deduce | 657 | 407 (61.9%) | 43 (6.5%) | 207 (31.5%) |

## Diagnosis

### Cipher ambiguity (structural)

- 207/657 puzzles (31.5%) — wrong-but-internally-consistent answers.
- The search found a valid cipher (digit_map + op_assign satisfying every example), just not the one used to generate the golden answer.
- Multiple consistent ciphers extrapolate to different target answers when the target uses under-constrained digit symbols.
- Mitigations: enumerate multiple ciphers and aggregate answers (majority vote); add tiebreaker heuristics for free-symbol assignments.

### Timeouts (search ran out of budget)

- 0/657 puzzles (0.0%) — at least one pipeline hit its 2s deadline before finding a cipher.
- Mitigations: longer deadline, better A0/B0/B1 ordering, tighter pruning.

### Exhausted (no cipher under current pruning)

- 43/657 puzzles (6.5%) — search exited fast with no candidates.
- Indicates over-pruning in column-derivation: a valid cipher exists (baseline finds it) but our constraints reject every candidate.
- Mitigations: review per-op column logic for edge cases that prune valid ciphers.

