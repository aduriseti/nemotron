# Benchmark: bit_solver_tt vs bit_solver_infer

Date: 2026-04-23 00:29:27  
Problems evaluated: 300

## 1. Accuracy
| Outcome | tt solver | infer solver |
|---------|-----------|--------------|
| Correct        | 298 (99.3%) | 295 (98.3%) |
| Wrong (solved) | 2 | 3 |
| Timed out / None | 0 | 2 |

## 2. Runtime (seconds)
| Metric  | tt solver | infer solver | ratio (tt/infer) |
|---------|-----------|--------------|-----------------|
| Min     | 0.0001 | 0.0000 | 3.19x |
| Max     | 0.4663 | 0.0430 | 10.85x |
| Mean    | 0.0509 | 0.0028 | 17.98x |
| Median  | 0.0048 | 0.0006 | 7.98x |

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
| Max     | 631,952 | 131,137 | 4.82x |
| Mean    | 61,914 | 8,787 | 7.05x |
| Median  | 6,029 | 2,340 | 2.57x |

## 4. Per-Arity Breakdown
| Arity | Solver | Count | Acc% | Mean time (s) | Median time (s) | Mean bit_checks |
|-------|--------|-------|------|---------------|-----------------|-----------------|
| 1 | infer | 29 | 100.0% | 0.0001 | 0.0000 | 261 |
| 2 | tt | 179 | 100.0% | 0.0089 | 0.0005 | 10,328 |
| 2 | infer | 161 | 98.8% | 0.0004 | 0.0003 | 1,701 |
| 3 | tt | 121 | 98.3% | 0.1130 | 0.0573 | 138,229 |
| 3 | infer | 108 | 99.1% | 0.0068 | 0.0047 | 20,837 |
| None | infer | 2 | 0.0% | 0.0185 | 0.0185 | 52,181 |

## 5. Disagreements Between Solvers (5 problems)
| Problem ID | Expected | tt answer | infer answer |
|------------|----------|-----------|--------------|
| 004ef7c7 | 11111111 | 11111111 | None |
| 0df8306a | 10000000 | 10000000 | 10000010 |
| 132ec6ae | 11101100 | 01101100 | 11101100 |
| 288c7eca | 01111111 | 01111111 | 00111111 |
| 2bb09a3e | 11001111 | 11001111 | None |

## 6. Per-Problem Speedup (tt_time / infer_time)
| Metric | Value |
|--------|-------|
| Mean speedup   | 32.59x |
| Median speedup | 3.60x |
| Max speedup    | 539.39x |
| Min speedup    | 0.19x |
| Problems where infer is faster | 246 / 300 |