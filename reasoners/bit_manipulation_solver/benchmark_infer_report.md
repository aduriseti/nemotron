# Benchmark: bit_solver_tt vs bit_solver_infer

Date: 2026-04-23 02:03:33  
Problems evaluated: 300

## 1. Accuracy
| Outcome | tt solver | infer solver |
|---------|-----------|--------------|
| Correct        | 298 (99.3%) | 294 (98.0%) |
| Wrong (solved) | 2 | 4 |
| Timed out / None | 0 | 2 |

## 2. Runtime (seconds)
| Metric  | tt solver | infer solver | ratio (tt/infer) |
|---------|-----------|--------------|-----------------|
| Min     | 0.0001 | 0.0000 | 3.21x |
| Max     | 0.4634 | 0.0266 | 17.41x |
| Mean    | 0.0530 | 0.0026 | 20.80x |
| Median  | 0.0052 | 0.0006 | 8.79x |

### Runtime distribution
| Bucket | tt solver | infer solver |
|--------|-----------|--------------|
| <0.1s | 250 | 300 |
| 0.1-0.5s | 50 | 0 |
| 0.5-1s | 0 | 0 |
| 1-5s | 0 | 0 |
| 5-15s | 0 | 0 |
| >=15s | 0 | 0 |

## 3. Bit Checks
| Metric  | tt solver | infer solver | ratio (tt/infer) |
|---------|-----------|--------------|-----------------|
| Min     | 105 | 59 | 1.75x |
| Max     | 631,952 | 53,624 | 11.78x |
| Mean    | 61,914 | 4,575 | 13.53x |
| Median  | 6,029 | 1,153 | 5.22x |

## 4. Per-Arity Breakdown
| Arity | Solver | Count | Acc% | Mean time (s) | Median time (s) | Mean bit_checks |
|-------|--------|-------|------|---------------|-----------------|-----------------|
| 1 | infer | 29 | 100.0% | 0.0001 | 0.0000 | 261 |
| 2 | tt | 179 | 100.0% | 0.0094 | 0.0006 | 10,328 |
| 2 | infer | 161 | 97.5% | 0.0005 | 0.0004 | 909 |
| 3 | tt | 121 | 98.3% | 0.1176 | 0.0610 | 138,229 |
| 3 | infer | 108 | 100.0% | 0.0059 | 0.0053 | 10,557 |
| None | infer | 2 | 0.0% | 0.0259 | 0.0259 | 39,131 |

## 5. Disagreements Between Solvers (4 problems)
| Problem ID | Expected | tt answer | infer answer |
|------------|----------|-----------|--------------|
| 004ef7c7 | 11111111 | 11111111 | None |
| 214d0570 | 10111111 | 10111111 | 01111111 |
| 288c7eca | 01111111 | 01111111 | 00111111 |
| 2bb09a3e | 11001111 | 11001111 | None |

## 6. Per-Problem Speedup (tt_time / infer_time)
| Metric | Value |
|--------|-------|
| Mean speedup   | 27.31x |
| Median speedup | 5.43x |
| Max speedup    | 540.30x |
| Min speedup    | 0.16x |
| Problems where infer is faster | 239 / 300 |