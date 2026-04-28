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
| Correct | 433 | 65.9% |
| Wrong (cipher ambiguity) | 223 | 33.9% |
| Timeout (≥1.9s, no answer) | 0 | 0.0% |
| Exhausted (<1.9s, no answer) | 1 | 0.2% |

Cipher ambiguity dominates: 223 wrong-cipher cases vs 1 no-answer cases (timeout + exhausted).

## Per-op breakdown

| Op | Total | ✓ | Timeout | Exhausted | Wrong | %✓ | %Timeout | %Exhausted | %Wrong |
|----|------:|--:|--------:|----------:|------:|---:|---------:|-----------:|-------:|
| add | 113 | 76 | 0 | 0 | 37 | 67.3% | 0.0% | 0.0% | 32.7% |
| sub | 76 | 51 | 0 | 0 | 25 | 67.1% | 0.0% | 0.0% | 32.9% |
| mul | 143 | 106 | 0 | 0 | 37 | 74.1% | 0.0% | 0.0% | 25.9% |
| cat | 59 | 58 | 0 | 0 | 1 | 98.3% | 0.0% | 0.0% | 1.7% |
| add1 | 35 | 22 | 0 | 0 | 13 | 62.9% | 0.0% | 0.0% | 37.1% |
| addm1 | 33 | 19 | 0 | 1 | 13 | 57.6% | 0.0% | 3.0% | 39.4% |
| mul1 | 39 | 26 | 0 | 0 | 13 | 66.7% | 0.0% | 0.0% | 33.3% |
| mulm1 | 23 | 11 | 0 | 0 | 12 | 47.8% | 0.0% | 0.0% | 52.2% |
| sub_abs | 96 | 43 | 0 | 0 | 53 | 44.8% | 0.0% | 0.0% | 55.2% |
| sub_neg_abs | 23 | 12 | 0 | 0 | 11 | 52.2% | 0.0% | 0.0% | 47.8% |
| max_mod_min | 17 | 9 | 0 | 0 | 8 | 52.9% | 0.0% | 0.0% | 47.1% |

## By category

| Category | n | ✓ | None | Wrong |
|----------|--:|--:|-----:|------:|
| cryptarithm_deduce | 657 | 433 (65.9%) | 1 (0.2%) | 223 (33.9%) |

## Diagnosis

### Cipher ambiguity (structural)

- 223/657 puzzles (33.9%) — wrong-but-internally-consistent answers.
- The search found a valid cipher (digit_map + op_assign satisfying every example), just not the one used to generate the golden answer.
- Multiple consistent ciphers extrapolate to different target answers when the target uses under-constrained digit symbols.
- Mitigations: enumerate multiple ciphers and aggregate answers (majority vote); add tiebreaker heuristics for free-symbol assignments.

### Timeouts (search ran out of budget)

- 0/657 puzzles (0.0%) — at least one pipeline hit its 2s deadline before finding a cipher.
- Mitigations: longer deadline, better A0/B0/B1 ordering, tighter pruning.

### Exhausted (no cipher under current pruning)

- 1/657 puzzles (0.2%) — search exited fast with no candidates.
- Indicates over-pruning in column-derivation: a valid cipher exists (baseline finds it) but our constraints reject every candidate.
- Mitigations: review per-op column logic for edge cases that prune valid ciphers.

