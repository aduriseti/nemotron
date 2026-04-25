# Cat Fast-Path Analysis: Operations and Accuracy

Greedy first-match solver. Operations = cat permutation attempts + `_derive_output` calls.

## With cat fast-path

- Accuracy: **58/100 (58.0%)**
- Cat fast-path triggered: 10/100 (10.0%)

### Operation counts (all 100 problems)

| Stat | Value |
|------|------:|
| Mean | 106666.6 |
| Median | 42,680 |
| p75 | 103,202 |
| p90 | 233,738 |
| p99 | 1,885,171 |
| Max | 1,885,171 |
| Total | 10,666,658 |

## Without cat fast-path

- Accuracy: **57/100 (57.0%)**

### Operation counts (all 100 problems)

| Stat | Value |
|------|------:|
| Mean | 137118.3 |
| Median | 52,886 |
| p75 | 112,483 |
| p90 | 312,585 |
| p99 | 1,909,139 |
| Max | 1,909,139 |
| Total | 13,711,834 |

## Budget vs Accuracy

|     Budget |     With cat |       No cat |
|------------:|--------------:|--------------:|
|          1 |   10/100 (10.0%) |    0/100 ( 0.0%) |
|          5 |   10/100 (10.0%) |    0/100 ( 0.0%) |
|         10 |   10/100 (10.0%) |    0/100 ( 0.0%) |
|         25 |   10/100 (10.0%) |    0/100 ( 0.0%) |
|         50 |   10/100 (10.0%) |    0/100 ( 0.0%) |
|        100 |   10/100 (10.0%) |    0/100 ( 0.0%) |
|        250 |   10/100 (10.0%) |    0/100 ( 0.0%) |
|        500 |   10/100 (10.0%) |    0/100 ( 0.0%) |
|      1,000 |   10/100 (10.0%) |    0/100 ( 0.0%) |
|      5,000 |   13/100 (13.0%) |    3/100 ( 3.0%) |
|     10,000 |   18/100 (18.0%) |    8/100 ( 8.0%) |
|     50,000 |   32/100 (32.0%) |   27/100 (27.0%) |
|    100,000 |   43/100 (43.0%) |   40/100 (40.0%) |

## Summary

| | With cat fast-path | Without cat fast-path |
|-|-|-|
| Accuracy | 58/100 (58.0%) | 57/100 (57.0%) |
| Total ops | 10,666,658 | 13,711,834 |
| Mean ops/problem | 106666.6 | 137118.3 |
| Ops reduction | **1.3x fewer ops** | — |

