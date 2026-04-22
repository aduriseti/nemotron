# Bit Manipulation Solver — Benchmark Report

Date: 2026-04-21 04:45:56
Solver timeout: 15.0s per problem
Problems evaluated: 300

## 1. Accuracy
| Outcome        | Count | % |
|----------------|-------|-----|
| Correct        |   296 | 98.7% |
| Wrong (solved) |     4 | 1.3% |
| Timed out      |     0 | 0.0% |
| **Total**      |   300 | 100% |

## 2. Runtime
| Metric                 | All problems | Solved only |
|------------------------|-------------|------------|
| Min (s)                | 0.000       | 0.000      |
| Max (s)                | 8.992       | 8.992      |
| Mean (s)               | 1.026       | 1.026      |
| Median (s)             | 0.004       |             |

### Runtime distribution (all problems)
| Bucket     | Count |
|------------|-------|
| <0.1s      |   212 |
| 0.1–0.5s   |    14 |
| 0.5–1s     |     8 |
| 1–5s       |    40 |
| 5–15s      |    26 |
| ≥15s (timeout) |     0 |

## 3. Solutions Found
- Solver found a rule for **300/300** problems (100.0%).
- Of those, **296/300** matched the expected answer (98.7% of solved).

## 4. Operation Usage in Found Rules
_(across 300 solved problems)_

### Boolean operations in AST nodes
| Operation | Count |
|-----------|-------|
| XOR       |   192 |
| NOT       |   125 |
| AND       |   123 |
| OR        |    96 |
| (leaf)    |    34 |

### Variable count per rule
| Vars used | Count |
|-----------|-------|
| 0         |     1 |
| 1         |    33 |
| 2         |   171 |
| 3         |    95 |

## 5. Transformation Complexity

### Transformation type (how variables are sourced from input)
| Type  | Count |
|-------|-------|
| shl   |   231 |
| rot   |   219 |
| shr   |   210 |

### Shift/rotation amounts
| Shift | Count |
|-------|-------|
|     0 |     1 |
|     1 |   100 |
|     2 |    90 |
|     3 |   105 |
|     4 |   102 |
|     5 |    77 |
|     6 |    93 |
|     7 |    92 |

### AST depth distribution
| Depth | Count |
|-------|-------|
|     0 |    34 |
|     1 |   135 |
|     2 |    68 |
|     3 |    63 |

### AST node count distribution
| Nodes | Count |
|-------|-------|
|     1 |    34 |
|     3 |   135 |
|     4 |    36 |
|     5 |    22 |
|     6 |    10 |
|     7 |    42 |
|     8 |     1 |
|     9 |     8 |
|    10 |    12 |

## 6. Rules with Multiple AND or OR Operators
_No rules with >1 AND or >1 OR found in this sample._

## 7. All Found Solutions
_(300 solved problems)_

| ID | Expression | Transformations | Depth | AND# | OR# | Correct |
|----|-----------|-----------------|-------|------|-----|---------|
| d25d3b5f | `({B} OR {A})` | {A}=shr(6), {B}=shl(4) | 1 | 0 | 1 | ✓ |
| 24232d07 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(4), {B}=rot(7), {C}=shl(6) | 3 | 1 | 0 | ✓ |
| 06698d4e | `{A}` | {A}=shr(1) | 0 | 0 | 0 | ✓ |
| f2a167e5 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(7), {B}=shl(5), {C}=rot(4) | 3 | 1 | 0 | ✓ |
| 5a1179ee | `({B} OR {A})` | {A}=shl(7), {B}=shr(5) | 1 | 0 | 1 | ✓ |
| 51007339 | `({A} XOR ({B} AND ({C} XOR {A})))` | {A}=rot(3), {B}=shl(2), {C}=shr(2) | 3 | 1 | 0 | ✓ |
| 499c7735 | `({B} OR {A})` | {A}=shl(6), {B}=rot(5) | 1 | 0 | 1 | ✓ |
| 2dc6056a | `({A} XOR (({B} XOR {A}) AND ({C} XOR {A})))` | {A}=shr(1), {B}=shl(5), {C}=rot(6) | 3 | 1 | 0 | ✓ |
| f05dc9a6 | `({A} XOR (({B} XOR {A}) AND ({C} XOR {A})))` | {A}=shl(3), {B}=shr(4), {C}=rot(5) | 3 | 1 | 0 | ✓ |
| 20924dd4 | `({A} OR ({C} AND {B}))` | {A}=shl(4), {B}=shr(5), {C}=rot(4) | 2 | 1 | 1 | ✓ |
| dde0558e | `({B} AND {A})` | {A}=rot(4), {B}=shr(1) | 1 | 1 | 0 | ✓ |
| f24b8bee | `{A}` | {A}=rot(5) | 0 | 0 | 0 | ✓ |
| b4549ab9 | `(NOT({A}) XOR ({C} OR {B}))` | {A}=rot(5), {B}=rot(7), {C}=shr(3) | 2 | 0 | 1 | ✓ |
| 1c19ad3e | `({B} XOR {A})` | {A}=rot(7), {B}=shl(3) | 1 | 0 | 0 | ✓ |
| c113055a | `({B} XOR {A})` | {A}=shl(6), {B}=shr(1) | 1 | 0 | 0 | ✓ |
| 88872de7 | `({A} OR ({C} AND {B}))` | {A}=shr(4), {B}=shl(7), {C}=rot(4) | 2 | 1 | 1 | ✓ |
| 08615ada | `({B} XOR {A})` | {A}=shr(3), {B}=shl(2) | 1 | 0 | 0 | ✓ |
| 07e8cf66 | `({A} XOR ({B} AND ({C} XOR {A})))` | {A}=rot(7), {B}=shl(1), {C}=shr(3) | 3 | 1 | 0 | ✓ |
| 1deaf759 | `({A} AND NOT({B}))` | {A}=rot(3), {B}=shl(7) | 2 | 1 | 0 | ✓ |
| 47720c17 | `(NOT({A}) XOR ({C} OR {B}))` | {A}=rot(6), {B}=rot(4), {C}=shr(2) | 2 | 0 | 1 | ✓ |
| 4c8182b0 | `({B} XOR {A})` | {A}=shr(3), {B}=shl(2) | 1 | 0 | 0 | ✓ |
| a7dcc027 | `NOT(({B} XOR {A}))` | {A}=shl(3), {B}=shl(1) | 2 | 0 | 0 | ✓ |
| c536c44c | `({B} OR {A})` | {A}=rot(4), {B}=shl(2) | 1 | 0 | 1 | ✓ |
| 06b5da9f | `({A} XOR ({B} AND ({C} XOR {A})))` | {A}=rot(3), {B}=shl(4), {C}=shr(2) | 3 | 1 | 0 | ✓ |
| b91855fd | `({B} OR {A})` | {A}=shr(7), {B}=shl(3) | 1 | 0 | 1 | ✓ |
| 400c9250 | `({A} AND NOT({B}))` | {A}=rot(6), {B}=shl(4) | 2 | 1 | 0 | ✓ |
| ea0deb13 | `({B} XOR {A})` | {A}=shl(5), {B}=shr(1) | 1 | 0 | 0 | ✓ |
| d547f717 | `({B} OR {A})` | {A}=shl(7), {B}=shr(4) | 1 | 0 | 1 | ✓ |
| e67cbe88 | `({B} XOR {A})` | {A}=shr(4), {B}=shl(2) | 1 | 0 | 0 | ✓ |
| 8785d0c3 | `({B} AND {A})` | {A}=rot(4), {B}=shl(1) | 1 | 1 | 0 | ✓ |
| 48db5ccf | `({B} XOR {A})` | {A}=shl(4), {B}=shr(3) | 1 | 0 | 0 | ✓ |
| 8fa7ea3a | `({B} AND {A})` | {A}=rot(7), {B}=rot(1) | 1 | 1 | 0 | ✓ |
| c095f799 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(7), {B}=rot(7), {C}=shl(3) | 3 | 1 | 0 | ✓ |
| 5b16b484 | `({B} AND {A})` | {A}=rot(5), {B}=shl(2) | 1 | 1 | 0 | ✓ |
| 01e09228 | `({A} XOR ({B} AND ({C} XOR {A})))` | {A}=rot(4), {B}=shl(2), {C}=shr(2) | 3 | 1 | 0 | ✓ |
| f85074ab | `({A} AND ({C} OR {B}))` | {A}=rot(3), {B}=shr(6), {C}=rot(1) | 2 | 1 | 1 | ✓ |
| 33e4e9ec | `(NOT({A}) XOR (({C} XOR {B}) AND ({B} OR {A})))` | {A}=shl(2), {B}=rot(4), {C}=shr(2) | 3 | 1 | 1 | ✓ |
| e5bb9b26 | `({B} OR {A})` | {A}=shl(7), {B}=rot(6) | 1 | 0 | 1 | ✓ |
| 88ae9960 | `({B} AND {A})` | {A}=shl(7), {B}=rot(3) | 1 | 1 | 0 | ✓ |
| 6eb0d262 | `({B} OR {A})` | {A}=shr(6), {B}=rot(3) | 1 | 0 | 1 | ✓ |
| 32e5fe87 | `({B} AND {A})` | {A}=shr(7), {B}=rot(0) | 1 | 1 | 0 | ✓ |
| 46ae00b4 | `({A} OR ({C} AND {B}))` | {A}=shl(5), {B}=shr(5), {C}=shr(3) | 2 | 1 | 1 | ✓ |
| f9c59b61 | `NOT(({B} XOR {A}))` | {A}=shl(3), {B}=shl(1) | 2 | 0 | 0 | ✓ |
| 6dbd9643 | `({A} XOR ({C} AND {B}))` | {A}=rot(6), {B}=shl(6), {C}=rot(3) | 2 | 1 | 0 | ✓ |
| 1da4f2db | `({A} AND NOT({B}))` | {A}=rot(7), {B}=shl(6) | 2 | 1 | 0 | ✓ |
| 7b107eec | `(NOT({A}) XOR ({C} OR {B}))` | {A}=rot(3), {B}=shr(5), {C}=shl(1) | 2 | 0 | 1 | ✓ |
| 1f6c2fd9 | `({A} AND ({C} OR {B}))` | {A}=rot(1), {B}=shl(6), {C}=shr(5) | 2 | 1 | 1 | ✓ |
| 751d48a2 | `({A} OR ({C} AND {B}))` | {A}=shl(4), {B}=shr(7), {C}=rot(4) | 2 | 1 | 1 | ✓ |
| 709930e0 | `({A} AND NOT({B}))` | {A}=rot(1), {B}=shl(6) | 2 | 1 | 0 | ✓ |
| c5872355 | `({B} XOR {A})` | {A}=shl(4), {B}=shr(2) | 1 | 0 | 0 | ✓ |
| 56672c27 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(3), {B}=shl(7), {C}=rot(6) | 3 | 1 | 0 | ✓ |
| 0c7acd69 | `{A}` | {A}=rot(1) | 0 | 0 | 0 | ✓ |
| ee61df9f | `({A} AND ({C} OR {B}))` | {A}=rot(6), {B}=shr(7), {C}=shl(2) | 2 | 1 | 1 | ✓ |
| 942ddd73 | `({A} AND ({C} OR {B}))` | {A}=rot(4), {B}=shr(6), {C}=rot(1) | 2 | 1 | 1 | ✓ |
| b1f5a2e8 | `1` | identity | 0 | 0 | 0 | ✓ |
| 288c7eca | `NOT(({B} XOR {A}))` | {A}=shl(7), {B}=shl(6) | 2 | 0 | 0 | ✗ |
| 7aba9046 | `({B} XOR {A})` | {A}=shr(5), {B}=shl(1) | 1 | 0 | 0 | ✓ |
| 177b7d80 | `(NOT({A}) XOR (({C} XOR {B}) AND ({B} OR {A})))` | {A}=rot(3), {B}=shl(5), {C}=shr(2) | 3 | 1 | 1 | ✓ |
| b634898d | `({B} OR {A})` | {A}=shr(7), {B}=shl(6) | 1 | 0 | 1 | ✓ |
| 5f66eb60 | `({A} XOR (({B} XOR {A}) AND ({C} XOR {A})))` | {A}=rot(1), {B}=shr(1), {C}=rot(6) | 3 | 1 | 0 | ✓ |
| ce862776 | `({B} XOR {A})` | {A}=shl(2), {B}=shr(1) | 1 | 0 | 0 | ✓ |
| ca72b5b3 | `({B} OR {A})` | {A}=rot(7), {B}=shl(3) | 1 | 0 | 1 | ✓ |
| 75cd54d8 | `({B} OR {A})` | {A}=shl(6), {B}=shr(4) | 1 | 0 | 1 | ✓ |
| bd214062 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(4), {B}=shl(7), {C}=rot(6) | 3 | 1 | 0 | ✓ |
| 3e000b40 | `({B} XOR {A})` | {A}=shl(5), {B}=shr(2) | 1 | 0 | 0 | ✓ |
| e72155f3 | `({B} XOR {A})` | {A}=shr(6), {B}=rot(6) | 1 | 0 | 0 | ✓ |
| 13c8ae90 | `({A} AND NOT({B}))` | {A}=shr(1), {B}=shl(3) | 2 | 1 | 0 | ✓ |
| 0d7aacfc | `({B} XOR {A})` | {A}=shr(2), {B}=shl(1) | 1 | 0 | 0 | ✓ |
| d9441d16 | `({A} AND NOT({B}))` | {A}=rot(1), {B}=shl(7) | 2 | 1 | 0 | ✓ |
| 4b86e0bb | `({B} XOR {A})` | {A}=shl(3), {B}=shr(1) | 1 | 0 | 0 | ✓ |
| fd03c3d3 | `({B} XOR {A})` | {A}=shl(5), {B}=rot(2) | 1 | 0 | 0 | ✓ |
| 5dfea8b0 | `(NOT({A}) XOR ({C} OR {B}))` | {A}=rot(5), {B}=rot(6), {C}=shr(3) | 2 | 0 | 1 | ✓ |
| 17fd9612 | `({A} AND NOT({B}))` | {A}=rot(7), {B}=shl(4) | 2 | 1 | 0 | ✓ |
| 201b150e | `({B} XOR {A})` | {A}=shr(6), {B}=shl(1) | 1 | 0 | 0 | ✓ |
| 91dc0848 | `({B} XOR {A})` | {A}=shl(2), {B}=shr(1) | 1 | 0 | 0 | ✓ |
| d08ef8d1 | `({A} AND NOT({B}))` | {A}=rot(3), {B}=shl(5) | 2 | 1 | 0 | ✓ |
| 77804b32 | `({B} OR {A})` | {A}=rot(7), {B}=shr(4) | 1 | 0 | 1 | ✓ |
| 34b9db0e | `({B} OR {A})` | {A}=shl(5), {B}=shr(4) | 1 | 0 | 1 | ✓ |
| 789b83ce | `({B} XOR {A})` | {A}=shl(3), {B}=shr(1) | 1 | 0 | 0 | ✓ |
| 738f7c2d | `({B} XOR {A})` | {A}=shr(5), {B}=shl(2) | 1 | 0 | 0 | ✓ |
| 43b9343e | `({B} XOR {A})` | {A}=rot(7), {B}=shr(4) | 1 | 0 | 0 | ✓ |
| dbb789cc | `({B} OR {A})` | {A}=rot(6), {B}=shr(5) | 1 | 0 | 1 | ✓ |
| 573eaca1 | `({B} OR {A})` | {A}=shl(6), {B}=shr(3) | 1 | 0 | 1 | ✓ |
| e6af8e6f | `({B} OR {A})` | {A}=shr(7), {B}=shl(4) | 1 | 0 | 1 | ✓ |
| e0d92248 | `({A} AND ({C} OR {B}))` | {A}=rot(4), {B}=shr(7), {C}=shl(3) | 2 | 1 | 1 | ✓ |
| d5071155 | `({A} AND NOT({B}))` | {A}=rot(6), {B}=shl(3) | 2 | 1 | 0 | ✓ |
| 14742dd8 | `({B} XOR {A})` | {A}=shr(6), {B}=shl(1) | 1 | 0 | 0 | ✓ |
| c6fa3e3f | `{A}` | {A}=shr(2) | 0 | 0 | 0 | ✓ |
| d065968c | `(NOT({A}) XOR (({C} XOR {B}) AND ({B} OR {A})))` | {A}=shl(1), {B}=rot(7), {C}=shr(2) | 3 | 1 | 1 | ✓ |
| 378741b0 | `({B} OR {A})` | {A}=shr(6), {B}=shl(4) | 1 | 0 | 1 | ✓ |
| b16455a2 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(7), {B}=rot(5), {C}=shl(2) | 3 | 1 | 0 | ✓ |
| ee4f1423 | `NOT(({B} XOR {A}))` | {A}=shl(4), {B}=rot(3) | 2 | 0 | 0 | ✓ |
| 35364e9a | `({A} OR NOT({B}))` | {A}=shr(2), {B}=shr(5) | 2 | 0 | 1 | ✓ |
| 955e8713 | `NOT((({B} XOR {A}) XOR ({C} AND {A})))` | {A}=rot(7), {B}=shl(2), {C}=shr(4) | 3 | 1 | 0 | ✗ |
| 7af6e047 | `{A}` | {A}=rot(5) | 0 | 0 | 0 | ✓ |
| 57b03b2b | `({B} OR {A})` | {A}=shr(7), {B}=rot(2) | 1 | 0 | 1 | ✓ |
| d2695f15 | `({B} XOR {A})` | {A}=shl(6), {B}=rot(2) | 1 | 0 | 0 | ✓ |
| e266959e | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(5), {B}=shl(7), {C}=rot(5) | 3 | 1 | 0 | ✓ |
| b80795b4 | `({A} OR ({C} AND {B}))` | {A}=shl(3), {B}=rot(4), {C}=rot(3) | 2 | 1 | 1 | ✓ |
| 47a5c4f4 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(7), {B}=shl(6), {C}=rot(3) | 3 | 1 | 0 | ✓ |
| e124d12a | `({A} OR NOT({B}))` | {A}=shr(1), {B}=shr(4) | 2 | 0 | 1 | ✓ |
| 6a578940 | `{A}` | {A}=rot(3) | 0 | 0 | 0 | ✓ |
| fb5a7b9e | `({B} XOR {A})` | {A}=shl(5), {B}=shr(1) | 1 | 0 | 0 | ✓ |
| fd699316 | `{A}` | {A}=rot(1) | 0 | 0 | 0 | ✓ |
| 101e6f80 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(6), {B}=shl(6), {C}=rot(1) | 3 | 1 | 0 | ✓ |
| 4ba4a7ec | `NOT(({B} XOR {A}))` | {A}=shl(7), {B}=shl(6) | 2 | 0 | 0 | ✓ |
| 67032a5c | `{A}` | {A}=rot(3) | 0 | 0 | 0 | ✓ |
| 81e39cf5 | `({B} XOR {A})` | {A}=shr(4), {B}=rot(1) | 1 | 0 | 0 | ✓ |
| 574d1901 | `({A} XOR ({B} AND ({C} XOR {A})))` | {A}=rot(5), {B}=shl(2), {C}=shr(2) | 3 | 1 | 0 | ✓ |
| 129d29e1 | `({B} XOR {A})` | {A}=shl(5), {B}=rot(1) | 1 | 0 | 0 | ✓ |
| 4510a429 | `({A} OR NOT({B}))` | {A}=shr(1), {B}=shr(7) | 2 | 0 | 1 | ✓ |
| baa9e4ea | `{A}` | {A}=shl(4) | 0 | 0 | 0 | ✓ |
| ea5def07 | `(NOT({A}) XOR ({C} OR {B}))` | {A}=rot(4), {B}=rot(6), {C}=shr(4) | 2 | 0 | 1 | ✓ |
| 66e5eb55 | `({A} XOR (({B} XOR {A}) AND ({C} XOR {A})))` | {A}=shr(1), {B}=shl(3), {C}=rot(5) | 3 | 1 | 0 | ✓ |
| 4575c0a2 | `({B} XOR {A})` | {A}=shr(4), {B}=shl(1) | 1 | 0 | 0 | ✓ |
| d727ad5f | `{A}` | {A}=shr(6) | 0 | 0 | 0 | ✓ |
| a60c36ec | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(4), {B}=rot(6), {C}=shl(5) | 3 | 1 | 0 | ✓ |
| 807c4206 | `({B} OR {A})` | {A}=shl(7), {B}=rot(3) | 1 | 0 | 1 | ✓ |
| d2fc4490 | `(NOT({A}) XOR (({C} XOR {B}) AND ({B} OR {A})))` | {A}=rot(1), {B}=shl(2), {C}=shr(5) | 3 | 1 | 1 | ✓ |
| 93ef4c81 | `({B} OR {A})` | {A}=shr(5), {B}=rot(4) | 1 | 0 | 1 | ✓ |
| 2f51362d | `({B} OR {A})` | {A}=rot(6), {B}=shr(3) | 1 | 0 | 1 | ✓ |
| 567e3da4 | `({A} AND NOT({B}))` | {A}=rot(4), {B}=shl(7) | 2 | 1 | 0 | ✓ |
| 51a78467 | `NOT(({B} XOR {A}))` | {A}=shl(6), {B}=shl(3) | 2 | 0 | 0 | ✓ |
| f3971b9a | `({A} AND NOT({B}))` | {A}=rot(2), {B}=shl(4) | 2 | 1 | 0 | ✓ |
| b287ee74 | `{A}` | {A}=shr(6) | 0 | 0 | 0 | ✓ |
| 562cfc29 | `NOT(({B} XOR {A}))` | {A}=rot(7), {B}=shl(2) | 2 | 0 | 0 | ✓ |
| f3ebf8bc | `({A} XOR ({C} AND {B}))` | {A}=rot(3), {B}=shl(3), {C}=rot(1) | 2 | 1 | 0 | ✓ |
| bef8b5ec | `({A} AND ({C} OR {B}))` | {A}=rot(2), {B}=shl(7), {C}=shr(3) | 2 | 1 | 1 | ✓ |
| 8a057351 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(5), {B}=shl(7), {C}=rot(4) | 3 | 1 | 0 | ✓ |
| be8de8a1 | `(NOT({A}) XOR (({C} XOR {B}) AND ({B} OR {A})))` | {A}=rot(3), {B}=shl(4), {C}=shr(1) | 3 | 1 | 1 | ✓ |
| 81522f20 | `({A} XOR ({B} AND ({C} XOR {A})))` | {A}=rot(2), {B}=shl(4), {C}=shr(1) | 3 | 1 | 0 | ✓ |
| 75e869dd | `({B} OR {A})` | {A}=rot(7), {B}=shr(2) | 1 | 0 | 1 | ✓ |
| 2d74e088 | `({A} OR ({C} AND {B}))` | {A}=shl(6), {B}=shr(2), {C}=shr(1) | 2 | 1 | 1 | ✓ |
| a8f5ad76 | `({B} XOR {A})` | {A}=shl(4), {B}=shr(3) | 1 | 0 | 0 | ✓ |
| a4970d02 | `{A}` | {A}=rot(7) | 0 | 0 | 0 | ✓ |
| 1d5ad68a | `({B} AND {A})` | {A}=rot(7), {B}=shl(3) | 1 | 1 | 0 | ✓ |
| f62c1fa3 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(5), {B}=rot(6), {C}=shl(2) | 3 | 1 | 0 | ✓ |
| 0ddca8bf | `{A}` | {A}=shr(6) | 0 | 0 | 0 | ✓ |
| 236034b4 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(6), {B}=rot(5), {C}=shl(1) | 3 | 1 | 0 | ✓ |
| 31a4c9ef | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(4), {B}=shl(3), {C}=rot(2) | 3 | 1 | 0 | ✓ |
| ce00ffe4 | `({A} XOR (({B} XOR {A}) AND ({C} XOR {A})))` | {A}=rot(1), {B}=shl(2), {C}=shr(3) | 3 | 1 | 0 | ✓ |
| 3400e0d5 | `({B} XOR {A})` | {A}=rot(6), {B}=shl(5) | 1 | 0 | 0 | ✓ |
| dff2a315 | `{A}` | {A}=rot(6) | 0 | 0 | 0 | ✓ |
| c2dacc5b | `({B} XOR {A})` | {A}=shl(4), {B}=shr(1) | 1 | 0 | 0 | ✓ |
| 1249ddb4 | `({B} XOR {A})` | {A}=shr(3), {B}=shl(2) | 1 | 0 | 0 | ✓ |
| 7c538bb0 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(2), {B}=shl(7), {C}=rot(2) | 3 | 1 | 0 | ✓ |
| 7b412ac0 | `({B} OR {A})` | {A}=shr(6), {B}=shl(3) | 1 | 0 | 1 | ✓ |
| c2d8ef67 | `({B} AND {A})` | {A}=shl(5), {B}=rot(1) | 1 | 1 | 0 | ✓ |
| 9972f3f1 | `({B} OR {A})` | {A}=shr(7), {B}=shl(5) | 1 | 0 | 1 | ✓ |
| af358750 | `{A}` | {A}=rot(5) | 0 | 0 | 0 | ✓ |
| 5309f723 | `NOT(({B} XOR {A}))` | {A}=shl(3), {B}=shl(2) | 2 | 0 | 0 | ✓ |
| b6cd1807 | `NOT(({B} XOR {A}))` | {A}=shl(6), {B}=shl(3) | 2 | 0 | 0 | ✓ |
| 02778bd7 | `({B} AND {A})` | {A}=shl(7), {B}=rot(4) | 1 | 1 | 0 | ✓ |
| eb252a80 | `(NOT({A}) XOR ({C} OR {B}))` | {A}=rot(5), {B}=shr(3), {C}=rot(3) | 2 | 0 | 1 | ✓ |
| 24f44584 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(4), {B}=rot(7), {C}=shl(5) | 3 | 1 | 0 | ✓ |
| e0918834 | `({B} OR {A})` | {A}=shl(6), {B}=shr(5) | 1 | 0 | 1 | ✓ |
| b20b39bf | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(7), {B}=rot(7), {C}=shl(2) | 3 | 1 | 0 | ✓ |
| f4bb4d9c | `({B} XOR {A})` | {A}=shr(3), {B}=shl(2) | 1 | 0 | 0 | ✓ |
| fb955790 | `({B} OR {A})` | {A}=shl(6), {B}=shr(3) | 1 | 0 | 1 | ✓ |
| d290b24e | `({B} XOR {A})` | {A}=shr(3), {B}=rot(3) | 1 | 0 | 0 | ✓ |
| 5f76ba09 | `({B} XOR {A})` | {A}=rot(6), {B}=shl(1) | 1 | 0 | 0 | ✓ |
| 8b471ce9 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(1), {B}=shl(5), {C}=rot(1) | 3 | 1 | 0 | ✓ |
| 3385a400 | `{A}` | {A}=rot(7) | 0 | 0 | 0 | ✓ |
| 9238e8d6 | `({A} AND NOT({B}))` | {A}=rot(4), {B}=shl(7) | 2 | 1 | 0 | ✓ |
| 008b52fd | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(6), {B}=shl(7), {C}=rot(1) | 3 | 1 | 0 | ✓ |
| eb40d1f3 | `({A} AND ({C} OR {B}))` | {A}=rot(5), {B}=shr(6), {C}=shl(4) | 2 | 1 | 1 | ✓ |
| eae81189 | `{A}` | {A}=shl(4) | 0 | 0 | 0 | ✓ |
| 563c1afa | `NOT(({B} XOR {A}))` | {A}=shl(4), {B}=shl(1) | 2 | 0 | 0 | ✓ |
| a62dd199 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(2), {B}=shl(7), {C}=rot(3) | 3 | 1 | 0 | ✓ |
| f929c6cc | `{A}` | {A}=rot(5) | 0 | 0 | 0 | ✓ |
| 3a1f8cf0 | `({A} OR ({C} AND {B}))` | {A}=shl(4), {B}=shr(6), {C}=rot(4) | 2 | 1 | 1 | ✓ |
| a897b8bc | `({B} OR {A})` | {A}=rot(5), {B}=shr(1) | 1 | 0 | 1 | ✓ |
| 214d0570 | `NOT(({B} AND {A}))` | {A}=shl(6), {B}=rot(5) | 2 | 1 | 0 | ✗ |
| ccf02dee | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(6), {B}=rot(3), {C}=shl(1) | 3 | 1 | 0 | ✗ |
| 6218204f | `({A} AND NOT({B}))` | {A}=rot(5), {B}=shl(6) | 2 | 1 | 0 | ✓ |
| d2503f8b | `(NOT({A}) XOR (({C} XOR {B}) AND ({B} OR {A})))` | {A}=shl(1), {B}=rot(7), {C}=shr(3) | 3 | 1 | 1 | ✓ |
| 792a5ccd | `({B} XOR {A})` | {A}=shr(5), {B}=shl(1) | 1 | 0 | 0 | ✓ |
| f94ed862 | `({B} OR {A})` | {A}=shl(4), {B}=rot(3) | 1 | 0 | 1 | ✓ |
| 3456da40 | `{A}` | {A}=shr(2) | 0 | 0 | 0 | ✓ |
| b2bdef43 | `NOT(({B} XOR {A}))` | {A}=shl(7), {B}=shl(6) | 2 | 0 | 0 | ✓ |
| fecfb467 | `({B} XOR {A})` | {A}=shl(5), {B}=rot(4) | 1 | 0 | 0 | ✓ |
| af5e4060 | `({B} OR {A})` | {A}=shr(3), {B}=rot(3) | 1 | 0 | 1 | ✓ |
| 000b53cf | `({A} XOR ({B} AND ({C} XOR {A})))` | {A}=rot(2), {B}=shl(1), {C}=shr(1) | 3 | 1 | 0 | ✓ |
| c39705cd | `({A} OR ({C} AND {B}))` | {A}=shr(4), {B}=shr(3), {C}=shl(3) | 2 | 1 | 1 | ✓ |
| 6a41d37b | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(6), {B}=shl(5), {C}=rot(4) | 3 | 1 | 0 | ✓ |
| a30a5e37 | `({B} AND {A})` | {A}=rot(2), {B}=rot(1) | 1 | 1 | 0 | ✓ |
| 04d8c3e6 | `({A} AND ({C} OR {B}))` | {A}=rot(4), {B}=shr(7), {C}=shl(7) | 2 | 1 | 1 | ✓ |
| 2441e2b4 | `({B} OR {A})` | {A}=shl(7), {B}=shr(5) | 1 | 0 | 1 | ✓ |
| 7669569d | `({B} OR {A})` | {A}=shl(7), {B}=rot(4) | 1 | 0 | 1 | ✓ |
| 649bebaf | `({B} OR {A})` | {A}=shl(7), {B}=rot(3) | 1 | 0 | 1 | ✓ |
| 4ef3d311 | `({B} OR {A})` | {A}=shl(6), {B}=shr(5) | 1 | 0 | 1 | ✓ |
| 106aeb25 | `({B} OR {A})` | {A}=shr(7), {B}=shl(5) | 1 | 0 | 1 | ✓ |
| 4f80d363 | `(NOT({A}) XOR ({C} OR {B}))` | {A}=rot(7), {B}=rot(6), {C}=shr(1) | 2 | 0 | 1 | ✓ |
| 1bcd2b16 | `{A}` | {A}=shr(1) | 0 | 0 | 0 | ✓ |
| eeb60061 | `({B} XOR {A})` | {A}=shl(7), {B}=rot(4) | 1 | 0 | 0 | ✓ |
| a1a61c77 | `{A}` | {A}=rot(6) | 0 | 0 | 0 | ✓ |
| 132ec6ae | `({A} OR NOT({B}))` | {A}=shr(7), {B}=shr(1) | 2 | 0 | 1 | ✓ |
| f8f4c3b4 | `({B} OR {A})` | {A}=shl(6), {B}=shr(3) | 1 | 0 | 1 | ✓ |
| b14f7be3 | `({B} XOR {A})` | {A}=shl(4), {B}=shr(1) | 1 | 0 | 0 | ✓ |
| fa6f754d | `({A} XOR ({B} AND ({C} XOR {A})))` | {A}=rot(4), {B}=shl(3), {C}=shr(1) | 3 | 1 | 0 | ✓ |
| 28b6bc51 | `({B} OR {A})` | {A}=rot(2), {B}=shr(1) | 1 | 0 | 1 | ✓ |
| 294557bb | `{A}` | {A}=rot(6) | 0 | 0 | 0 | ✓ |
| d8d3648f | `({B} XOR {A})` | {A}=shl(3), {B}=shr(1) | 1 | 0 | 0 | ✓ |
| 9c5c6401 | `({B} XOR {A})` | {A}=rot(7), {B}=shl(1) | 1 | 0 | 0 | ✓ |
| b5e40e49 | `({B} XOR {A})` | {A}=rot(5), {B}=shl(1) | 1 | 0 | 0 | ✓ |
| 35e3c7c5 | `({B} XOR {A})` | {A}=rot(4), {B}=shl(1) | 1 | 0 | 0 | ✓ |
| aeca38ba | `({A} AND NOT({B}))` | {A}=rot(1), {B}=shl(7) | 2 | 1 | 0 | ✓ |
| c628dd06 | `({A} OR ({C} AND {B}))` | {A}=shr(4), {B}=rot(4), {C}=rot(1) | 2 | 1 | 1 | ✓ |
| 88c482d3 | `({B} OR {A})` | {A}=shr(7), {B}=shl(2) | 1 | 0 | 1 | ✓ |
| 45378f59 | `({A} OR ({C} AND {B}))` | {A}=shl(2), {B}=rot(4), {C}=rot(2) | 2 | 1 | 1 | ✓ |
| f5d74f50 | `({B} OR {A})` | {A}=rot(6), {B}=shl(5) | 1 | 0 | 1 | ✓ |
| e34cc6dd | `({B} AND {A})` | {A}=rot(3), {B}=rot(2) | 1 | 1 | 0 | ✓ |
| 405262aa | `({B} AND {A})` | {A}=shr(4), {B}=rot(1) | 1 | 1 | 0 | ✓ |
| e928acf8 | `({B} XOR {A})` | {A}=shr(4), {B}=shl(3) | 1 | 0 | 0 | ✓ |
| 663fd5e9 | `({A} AND NOT({B}))` | {A}=rot(3), {B}=shl(7) | 2 | 1 | 0 | ✓ |
| dbf2b40f | `({B} XOR {A})` | {A}=shl(5), {B}=shr(2) | 1 | 0 | 0 | ✓ |
| 790e0153 | `(NOT({A}) XOR ({C} AND {B}))` | {A}=shr(4), {B}=rot(4), {C}=shr(3) | 2 | 1 | 0 | ✓ |
| 8c743940 | `{A}` | {A}=shr(1) | 0 | 0 | 0 | ✓ |
| ab5f7c7f | `({B} XOR {A})` | {A}=shl(3), {B}=shr(2) | 1 | 0 | 0 | ✓ |
| 90f50354 | `(NOT({A}) XOR (({C} XOR {B}) AND ({B} OR {A})))` | {A}=shl(2), {B}=rot(7), {C}=shr(4) | 3 | 1 | 1 | ✓ |
| 26e985b5 | `({B} XOR {A})` | {A}=shr(5), {B}=shl(1) | 1 | 0 | 0 | ✓ |
| 522058b9 | `({B} OR {A})` | {A}=shr(7), {B}=shl(3) | 1 | 0 | 1 | ✓ |
| 4a374160 | `({B} OR {A})` | {A}=shl(6), {B}=shr(4) | 1 | 0 | 1 | ✓ |
| 124bc762 | `({B} OR {A})` | {A}=shr(6), {B}=shl(5) | 1 | 0 | 1 | ✓ |
| 6e56c02c | `{A}` | {A}=rot(3) | 0 | 0 | 0 | ✓ |
| 053f87d3 | `({B} OR {A})` | {A}=shr(2), {B}=rot(2) | 1 | 0 | 1 | ✓ |
| c05f5733 | `({A} XOR (({B} XOR {A}) AND ({C} XOR {A})))` | {A}=rot(1), {B}=shl(3), {C}=shr(3) | 3 | 1 | 0 | ✓ |
| b6e4a36d | `(NOT({A}) OR ({C} XOR {B}))` | {A}=rot(2), {B}=shl(6), {C}=shr(1) | 2 | 0 | 1 | ✓ |
| 4c06f388 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(5), {B}=rot(2), {C}=shl(1) | 3 | 1 | 0 | ✓ |
| c0788894 | `({B} OR {A})` | {A}=rot(3), {B}=shr(1) | 1 | 0 | 1 | ✓ |
| 01e395d0 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(4), {B}=shl(7), {C}=rot(3) | 3 | 1 | 0 | ✓ |
| 143627c4 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(6), {B}=rot(6), {C}=shl(5) | 3 | 1 | 0 | ✓ |
| e818def8 | `({B} OR {A})` | {A}=rot(7), {B}=shl(5) | 1 | 0 | 1 | ✓ |
| cf447906 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(6), {B}=rot(5), {C}=shl(4) | 3 | 1 | 0 | ✓ |
| 108e69ef | `(NOT({A}) XOR (({C} XOR {B}) AND ({B} OR {A})))` | {A}=shl(1), {B}=rot(2), {C}=shr(2) | 3 | 1 | 1 | ✓ |
| 4b925449 | `{A}` | {A}=rot(7) | 0 | 0 | 0 | ✓ |
| 12fd5b6c | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(4), {B}=rot(5), {C}=shl(2) | 3 | 1 | 0 | ✓ |
| 0855605b | `({B} XOR {A})` | {A}=shl(4), {B}=shr(2) | 1 | 0 | 0 | ✓ |
| 6bef21ca | `({B} OR {A})` | {A}=shr(7), {B}=shl(2) | 1 | 0 | 1 | ✓ |
| aa3ae31f | `({B} XOR {A})` | {A}=shr(4), {B}=shl(1) | 1 | 0 | 0 | ✓ |
| 4ec611d7 | `({B} XOR {A})` | {A}=rot(4), {B}=shr(2) | 1 | 0 | 0 | ✓ |
| 5b1b10d3 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(6), {B}=rot(7), {C}=shl(3) | 3 | 1 | 0 | ✓ |
| dbabfbdd | `({B} OR {A})` | {A}=shr(6), {B}=shl(5) | 1 | 0 | 1 | ✓ |
| a19734b3 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(4), {B}=shl(6), {C}=rot(5) | 3 | 1 | 0 | ✓ |
| 45da0a33 | `({B} XOR {A})` | {A}=shl(4), {B}=shr(2) | 1 | 0 | 0 | ✓ |
| 2b16044a | `({B} XOR {A})` | {A}=shl(3), {B}=shr(1) | 1 | 0 | 0 | ✓ |
| ec46d596 | `(NOT({A}) XOR (({C} XOR {B}) AND ({B} OR {A})))` | {A}=rot(5), {B}=shl(6), {C}=shr(1) | 3 | 1 | 1 | ✓ |
| bb429016 | `NOT(({B} XOR {A}))` | {A}=shl(3), {B}=shl(1) | 2 | 0 | 0 | ✓ |
| bd049614 | `({A} AND ({C} OR {B}))` | {A}=rot(2), {B}=shr(7), {C}=shl(5) | 2 | 1 | 1 | ✓ |
| 9b2b3698 | `({B} OR {A})` | {A}=shl(6), {B}=shr(5) | 1 | 0 | 1 | ✓ |
| 5028d953 | `{A}` | {A}=shr(2) | 0 | 0 | 0 | ✓ |
| 837d7158 | `({B} AND {A})` | {A}=rot(5), {B}=shr(1) | 1 | 1 | 0 | ✓ |
| 3d8e6b03 | `({B} OR {A})` | {A}=rot(2), {B}=shl(1) | 1 | 0 | 1 | ✓ |
| 1e677e2c | `({B} XOR {A})` | {A}=shl(6), {B}=rot(4) | 1 | 0 | 0 | ✓ |
| d864f0fb | `{A}` | {A}=rot(1) | 0 | 0 | 0 | ✓ |
| 8a5742e1 | `{A}` | {A}=shl(4) | 0 | 0 | 0 | ✓ |
| 736ae137 | `({B} AND {A})` | {A}=rot(6), {B}=rot(3) | 1 | 1 | 0 | ✓ |
| 88ca8c4a | `({A} AND ({C} OR {B}))` | {A}=rot(1), {B}=shl(7), {C}=shr(2) | 2 | 1 | 1 | ✓ |
| 84b4b07b | `({A} XOR (({B} XOR {A}) AND ({C} XOR {A})))` | {A}=shl(3), {B}=shr(4), {C}=rot(6) | 3 | 1 | 0 | ✓ |
| 98c4eb34 | `({B} AND {A})` | {A}=rot(7), {B}=rot(2) | 1 | 1 | 0 | ✓ |
| 0f8fe647 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(7), {B}=rot(6), {C}=shl(3) | 3 | 1 | 0 | ✓ |
| dc99f250 | `({B} OR {A})` | {A}=shl(7), {B}=shr(6) | 1 | 0 | 1 | ✓ |
| d6ceda8e | `({B} XOR {A})` | {A}=rot(6), {B}=shl(5) | 1 | 0 | 0 | ✓ |
| d4612468 | `{A}` | {A}=shr(7) | 0 | 0 | 0 | ✓ |
| 1fd310dc | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(2), {B}=rot(3), {C}=shl(1) | 3 | 1 | 0 | ✓ |
| 1126e314 | `({A} XOR (({B} XOR {A}) AND ({C} XOR {A})))` | {A}=rot(1), {B}=shr(1), {C}=shl(2) | 3 | 1 | 0 | ✓ |
| 823be38e | `({B} XOR {A})` | {A}=shl(4), {B}=shr(3) | 1 | 0 | 0 | ✓ |
| ee3bbe87 | `({B} XOR {A})` | {A}=shr(3), {B}=rot(2) | 1 | 0 | 0 | ✓ |
| 6e80733d | `{A}` | {A}=rot(3) | 0 | 0 | 0 | ✓ |
| 23410e94 | `({B} XOR {A})` | {A}=rot(7), {B}=shl(6) | 1 | 0 | 0 | ✓ |
| 5281a6b3 | `({B} XOR {A})` | {A}=rot(4), {B}=shr(2) | 1 | 0 | 0 | ✓ |
| 3dcc0195 | `({B} OR {A})` | {A}=rot(3), {B}=shl(2) | 1 | 0 | 1 | ✓ |
| 8f7b37be | `NOT(({B} XOR {A}))` | {A}=shl(7), {B}=shl(5) | 2 | 0 | 0 | ✓ |
| 2dcfc1a3 | `{A}` | {A}=rot(1) | 0 | 0 | 0 | ✓ |
| 3ad042eb | `({B} XOR {A})` | {A}=shr(4), {B}=shl(2) | 1 | 0 | 0 | ✓ |
| 95771a39 | `({A} XOR ({B} AND ({C} XOR {A})))` | {A}=rot(6), {B}=shl(1), {C}=shr(1) | 3 | 1 | 0 | ✓ |
| 52a052a0 | `({B} AND {A})` | {A}=rot(7), {B}=rot(3) | 1 | 1 | 0 | ✓ |
| 161667cd | `NOT(({B} XOR {A}))` | {A}=rot(4), {B}=shl(3) | 2 | 0 | 0 | ✓ |
| 8dcbf9d4 | `(NOT({A}) XOR (({C} XOR {B}) AND ({B} OR {A})))` | {A}=shl(1), {B}=rot(7), {C}=shr(2) | 3 | 1 | 1 | ✓ |
| b61afd75 | `(NOT({A}) XOR (({C} XOR {B}) AND ({B} OR {A})))` | {A}=shl(4), {B}=rot(5), {C}=shr(2) | 3 | 1 | 1 | ✓ |
| 1fa373db | `({B} XOR {A})` | {A}=shl(3), {B}=shr(2) | 1 | 0 | 0 | ✓ |
| 0ec17d2e | `(NOT({A}) XOR (({C} XOR {B}) AND ({B} OR {A})))` | {A}=rot(2), {B}=shl(4), {C}=shr(1) | 3 | 1 | 1 | ✓ |
| d623e937 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(3), {B}=shl(7), {C}=rot(4) | 3 | 1 | 0 | ✓ |
| b30f8610 | `({B} OR {A})` | {A}=rot(7), {B}=shr(3) | 1 | 0 | 1 | ✓ |
| 0334b2bf | `NOT(({B} XOR {A}))` | {A}=shl(4), {B}=shl(3) | 2 | 0 | 0 | ✓ |
| f55c1bf0 | `NOT(({B} XOR {A}))` | {A}=shl(6), {B}=shl(3) | 2 | 0 | 0 | ✓ |
| 4e918d82 | `({B} XOR {A})` | {A}=rot(6), {B}=shr(1) | 1 | 0 | 0 | ✓ |
| 36300e18 | `({B} XOR {A})` | {A}=shl(4), {B}=shr(1) | 1 | 0 | 0 | ✓ |
| 836b85e8 | `({B} AND {A})` | {A}=shr(4), {B}=shr(1) | 1 | 1 | 0 | ✓ |
| 9e61762f | `({B} XOR {A})` | {A}=shr(2), {B}=shl(1) | 1 | 0 | 0 | ✓ |
| 45bc0187 | `({B} AND {A})` | {A}=rot(4), {B}=shr(3) | 1 | 1 | 0 | ✓ |
| 35dafdbc | `{A}` | {A}=rot(3) | 0 | 0 | 0 | ✓ |
| 7abab429 | `({B} AND {A})` | {A}=shr(7), {B}=rot(4) | 1 | 1 | 0 | ✓ |
| 00754598 | `({B} XOR {A})` | {A}=shl(3), {B}=shr(2) | 1 | 0 | 0 | ✓ |
| 7eaa679e | `{A}` | {A}=rot(7) | 0 | 0 | 0 | ✓ |
| 56b1a67b | `({B} AND {A})` | {A}=rot(6), {B}=rot(2) | 1 | 1 | 0 | ✓ |
| 929bbda5 | `NOT((NOT({A}) AND ({C} XOR {B})))` | {A}=shr(4), {B}=shl(6), {C}=rot(3) | 3 | 1 | 0 | ✓ |
| 5d060d45 | `({B} AND {A})` | {A}=rot(6), {B}=shl(2) | 1 | 1 | 0 | ✓ |
| e5a5fdef | `({B} XOR {A})` | {A}=shl(2), {B}=shr(1) | 1 | 0 | 0 | ✓ |
| eea91b82 | `(NOT({A}) XOR ({C} OR {B}))` | {A}=rot(3), {B}=rot(6), {C}=shr(5) | 2 | 0 | 1 | ✓ |

## 8. Truth Table Coverage Analysis (Arity-2 and Arity-3)

At bit position p=0, the 22 transforms collapse to 9 distinct source values
(input bits 0–7 plus the constant 0). This analysis measures how many of the
possible input combinations are observed across the 8 examples — which determines
whether a truth-table reconstruction approach could identify the rule directly.

### Arity-2: Coverage of 2-input truth tables
Each problem yields 36 candidate pairs. Total pairs analysed: 14,652 (across 1602 problems).

| Distinct (A,B) combos seen | Pair count | % of all pairs |
|---------------------------|-----------|----------------|
| 0/4 |        0 | 0.0% |
| 1/4 |       28 | 0.2% |
| 2/4 |    3,499 | 23.9% |
| 3/4 |    3,913 | 26.7% |
| 4/4 |    7,212 | 49.2% |

**Per-problem best pair coverage** (max over all 36 pairs):

| Best coverage in problem | Problems | % |
|--------------------------|---------|---|
| 0/4 |     0 | 0.0% |
| 1/4 |     0 | 0.0% |
| 2/4 |     0 | 0.0% |
| 3/4 |     0 | 0.0% |
| 4/4 |   407 | 25.4% |

→ **407/1602 (25.4%) problems have at least one fully-covered pair (4/4 combos seen).**
  For these problems, the arity-2 truth table can be read directly without search.

### Arity-3: Coverage of 3-input truth tables
Each problem yields 84 candidate triples. Total triples analysed: 34,188 (across 1602 problems).

| Distinct (A,B,C) combos seen | Triple count | % of all triples |
|------------------------------|-------------|------------------|
| 0/8 |        0 | 0.0% |
| 1/8 |        2 | 0.0% |
| 2/8 |      285 | 0.8% |
| 3/8 |    4,319 | 12.6% |
| 4/8 |   10,829 | 31.7% |
| 5/8 |    9,363 | 27.4% |
| 6/8 |    7,746 | 22.7% |
| 7/8 |    1,575 | 4.6% |
| 8/8 |       69 | 0.2% |

**Per-problem best triple coverage** (max over all 84 triples):

| Best coverage in problem | Problems | % |
|--------------------------|---------|---|
| 0/8 |     0 | 0.0% |
| 1/8 |     0 | 0.0% |
| 2/8 |     0 | 0.0% |
| 3/8 |     0 | 0.0% |
| 4/8 |     0 | 0.0% |
| 5/8 |     0 | 0.0% |
| 6/8 |    68 | 4.2% |
| 7/8 |   298 | 18.6% |
| 8/8 |    41 | 2.6% |

→ **41/1602 (2.6%) problems have at least one fully-covered triple (8/8 combos seen).**

### Implications for truth-table reconstruction
- Arity-2 full coverage is achievable in 25.4% of problems — useful as a fast path for simple rules.
- Arity-3 full coverage is rare (2.6%) with only 8 examples, making direct truth-table
  reconstruction unreliable for degree-3 rules.
- Most arity-3 problems reach 7/8 coverage (18.6%), leaving one input combination unobserved
  and requiring at least a 2-way branch to resolve ambiguity.
- Partial coverage still strongly constrains the function: 7/8 coverage narrows the
  256 possible 3-input functions down to at most 2 consistent candidates.

## 9. Distinct Boolean Functions Used in the Dataset (300-problem sample)

Across 300 solved problems, the solver found rules using only a tiny fraction
of all possible boolean functions. The dataset is far more constrained than the
theoretical maximum.

### Arity distribution

| Arity | Problems | Distinct truth tables | Out of possible |
|-------|----------|-----------------------|-----------------|
| 0 (constant) | 1 | 1 | 2 |
| 1 (single var) | 33 | 1 | 4 |
| 2 (two vars) | 171 | 7 | 16 |
| 3 (three vars) | 95 | 11 | 256 |

### Arity-1 functions (1 of 4 possible)

| Truth table | Decimal | Problems | Meaning |
|-------------|---------|----------|---------|
| `10` | 2 | 33 | identity (f=A) |

### Arity-2 functions (7 of 16 possible)

| Truth table | Decimal | Problems | Meaning |
|-------------|---------|----------|---------|
| `0110` | 6 | 63 | A XOR B |
| `1110` | 14 | 51 | A OR B |
| `1000` | 8 | 21 | A AND B |
| `1001` | 9 | 16 | NOT(A XOR B) |
| `0010` | 2 | 15 | NOT(A) AND B |
| `1011` | 11 | 4 | NOT(A AND NOT(B)) |
| `0111` | 7 | 1 | NOT(A AND B) |

### Arity-3 functions (11 of 256 possible)

| Truth table | Decimal | Problems |
|-------------|---------|----------|
| `11101011` | 235 | 33 |
| `01101101` | 109 | 12 |
| `11101010` | 234 | 10 |
| `10101000` | 168 | 10 |
| `11100010` | 226 | 9 |
| `11101000` | 232 | 8 |
| `10101001` | 169 | 8 |
| `01101010` | 106 | 2 |
| `01011001` | 89 | 1 |
| `10010101` | 149 | 1 |
| `01111101` | 125 | 1 |

### Key insight
The dataset uses only **7/16** arity-2 and **11/256** arity-3 boolean functions.
This extreme concentration means a lookup-based approach matching against these
~19 known function templates would solve nearly the entire dataset — the search
is not over all possible boolean functions but a tiny enumerable set.

## 10. Truth Table Function Distribution & Coverage — Full Dataset (1602 problems)

Solver run on all 1602 bit_manipulation problems. Unsolved: 0.

### Arity distribution and truth table coverage

| Arity | Problems | Distinct fns | Out of possible | Avg coverage | Full coverage |
|-------|----------|--------------|-----------------|--------------|---------------|
| 0 | 5 | 1/2 | 50.0% used | 100.0% | 5 (100.0%) |
| 1 | 149 | 1/4 | 25.0% used | 100.0% | 149 (100.0%) |
| 2 | 899 | 8/16 | 50.0% used | 95.3% | 731 (81.3%) |
| 3 | 549 | 15/256 | 5.9% used | 83.6% | 187 (34.1%) |

### Arity-2 functions used

| Truth table | Dec | Problems |
|-------------|-----|----------|
| `0110` | 6 | 324 |
| `1110` | 14 | 289 |
| `1000` | 8 | 131 |
| `0010` | 2 | 86 |
| `1001` | 9 | 41 |
| `1011` | 11 | 25 |
| `0001` | 1 | 2 |
| `0111` | 7 | 1 |

### Arity-3 functions used

| Truth table | Dec | Problems |
|-------------|-----|----------|
| `11101011` | 235 | 164 |
| `11101010` | 234 | 70 |
| `10101001` | 169 | 61 |
| `10101000` | 168 | 61 |
| `11101000` | 232 | 54 |
| `01101101` | 109 | 53 |
| `11100010` | 226 | 46 |
| `10010101` | 149 | 13 |
| `01101010` | 106 | 10 |
| `01011001` | 89 | 6 |
| `10001010` | 138 | 4 |
| `11111101` | 253 | 3 |
| `01100100` | 100 | 2 |
| `10101011` | 171 | 1 |
| `01111101` | 125 | 1 |

## 11. Frequency-Ordered Truth-Table Solver — Bit-Check Count (300 problems)

Solver enumerates the 24 known boolean functions in frequency order.
Tests one bit at a time, interleaving examples, for fast invalidation.
Canonical permutations avoid redundant symmetric transform assignments.

**Accuracy: 297/300 correct (99.0%), 3 wrong, 0 no solution**

### Bit-check statistics (all 300 problems)

| Metric | Value |
|--------|-------|
| Min | 136 |
| Max | 507,182 |
| Mean | 54,937 |
| Median | 5,436 |

### Distribution of bit checks per problem

| Bucket | Count | % |
|--------|-------|---|
| <100 | 0 | 0.0% |
| 100-499 | 56 | 18.7% |
| 500-999 | 52 | 17.3% |
| 1k-4999 | 41 | 13.7% |
| 5k-9999 | 14 | 4.7% |
| 10k-49999 | 71 | 23.7% |
| >=50k | 66 | 22.0% |

## 12. Per-Problem Bit-Check Counts (300-problem sample)

| Problem ID | Outcome | Bit Checks |
|------------|---------|------------|
| 06b5da9f | ✓ | 507,182 |
| 01e09228 | ✓ | 471,135 |
| 790e0153 | ✓ | 447,056 |
| 95771a39 | ✓ | 428,308 |
| c05f5733 | ✓ | 425,252 |
| 000b53cf | ✓ | 404,114 |
| 574d1901 | ✓ | 382,212 |
| fa6f754d | ✓ | 368,293 |
| 81522f20 | ✓ | 364,679 |
| 51007339 | ✓ | 336,744 |
| f3ebf8bc | ✓ | 313,497 |
| d2fc4490 | ✓ | 312,420 |
| b61afd75 | ✓ | 308,160 |
| f05dc9a6 | ✓ | 301,531 |
| ce00ffe4 | ✓ | 296,572 |
| 6dbd9643 | ✓ | 295,878 |
| 177b7d80 | ✓ | 293,155 |
| 07e8cf66 | ✓ | 286,508 |
| 955e8713 | ✓ | 278,236 |
| b6e4a36d | ✓ | 266,553 |
| 0ec17d2e | ✓ | 256,619 |
| 66e5eb55 | ✓ | 251,990 |
| 84b4b07b | ✓ | 250,684 |
| d2503f8b | ✓ | 250,008 |
| eb40d1f3 | ✓ | 249,368 |
| 108e69ef | ✓ | 248,862 |
| be8de8a1 | ✓ | 247,397 |
| 1126e314 | ✓ | 241,818 |
| 33e4e9ec | ✓ | 240,076 |
| bd049614 | ✓ | 236,028 |
| 8dcbf9d4 | ✓ | 232,682 |
| 90f50354 | ✓ | 232,573 |
| e0d92248 | ✓ | 227,684 |
| d065968c | ✓ | 222,557 |
| 04d8c3e6 | ✓ | 219,952 |
| 5f66eb60 | ✓ | 216,432 |
| ec46d596 | ✓ | 205,450 |
| 942ddd73 | ✓ | 204,857 |
| 88ca8c4a | ✓ | 204,465 |
| 2dc6056a | ✓ | 202,518 |
| bef8b5ec | ✓ | 186,108 |
| ee61df9f | ✓ | 179,140 |
| f85074ab | ✓ | 173,736 |
| 1f6c2fd9 | ✓ | 169,231 |
| 3a1f8cf0 | ✓ | 122,800 |
| 751d48a2 | ✓ | 114,039 |
| c39705cd | ✓ | 106,695 |
| 20924dd4 | ✓ | 104,697 |
| 46ae00b4 | ✓ | 92,688 |
| b80795b4 | ✓ | 91,938 |
| 45378f59 | ✓ | 80,929 |
| 88872de7 | ✓ | 76,022 |
| 2d74e088 | ✓ | 66,818 |
| d08ef8d1 | ✓ | 65,753 |
| e34cc6dd | ✓ | 61,833 |
| 663fd5e9 | ✓ | 61,739 |
| aeca38ba | ✓ | 61,133 |
| 17fd9612 | ✓ | 60,908 |
| 56b1a67b | ✓ | 60,242 |
| 8785d0c3 | ✓ | 57,960 |
| c628dd06 | ✓ | 55,838 |
| 405262aa | ✓ | 54,304 |
| 143627c4 | ✓ | 54,143 |
| 98c4eb34 | ✓ | 52,986 |
| 35364e9a | ✓ | 51,760 |
| 6a41d37b | ✓ | 50,406 |
| 7abab429 | ✓ | 49,530 |
| 1da4f2db | ✓ | 49,419 |
| 567e3da4 | ✓ | 48,915 |
| 6218204f | ✓ | 48,314 |
| 88ae9960 | ✓ | 47,667 |
| 13c8ae90 | ✓ | 46,261 |
| 1deaf759 | ✓ | 46,064 |
| d5071155 | ✓ | 46,032 |
| 836b85e8 | ✓ | 45,679 |
| 8fa7ea3a | ✓ | 45,673 |
| 45bc0187 | ✓ | 45,642 |
| c2d8ef67 | ✓ | 45,399 |
| 32e5fe87 | ✓ | 45,253 |
| d9441d16 | ✓ | 44,723 |
| 400c9250 | ✓ | 44,669 |
| 736ae137 | ✓ | 44,238 |
| a30a5e37 | ✓ | 43,589 |
| f3971b9a | ✓ | 43,313 |
| 837d7158 | ✓ | 43,098 |
| 02778bd7 | ✓ | 42,784 |
| 5b16b484 | ✓ | 42,601 |
| 1d5ad68a | ✓ | 42,310 |
| dde0558e | ✓ | 41,995 |
| 5d060d45 | ✓ | 41,878 |
| 9238e8d6 | ✓ | 40,625 |
| b4549ab9 | ✓ | 38,542 |
| 52a052a0 | ✓ | 38,443 |
| e266959e | ✓ | 37,707 |
| 709930e0 | ✓ | 37,704 |
| 0f8fe647 | ✓ | 33,347 |
| 24232d07 | ✓ | 30,673 |
| 0334b2bf | ✓ | 30,256 |
| 8a057351 | ✓ | 29,869 |
| 47a5c4f4 | ✓ | 29,273 |
| ee4f1423 | ✓ | 29,262 |
| cf447906 | ✓ | 28,958 |
| ea5def07 | ✓ | 28,796 |
| 5b1b10d3 | ✓ | 28,484 |
| 56672c27 | ✓ | 28,302 |
| 12fd5b6c | ✓ | 28,043 |
| e124d12a | ✓ | 26,126 |
| a19734b3 | ✓ | 26,096 |
| a60c36ec | ✓ | 25,319 |
| b6cd1807 | ✓ | 25,269 |
| 24f44584 | ✓ | 24,991 |
| 8f7b37be | ✓ | 24,872 |
| 51a78467 | ✓ | 24,669 |
| eea91b82 | ✓ | 24,079 |
| 132ec6ae | ✗ | 23,939 |
| f55c1bf0 | ✓ | 23,295 |
| bd214062 | ✓ | 23,270 |
| f2a167e5 | ✓ | 23,239 |
| 47720c17 | ✓ | 22,624 |
| 161667cd | ✓ | 20,276 |
| 929bbda5 | ✓ | 20,257 |
| c095f799 | ✓ | 19,668 |
| d623e937 | ✓ | 19,492 |
| 5dfea8b0 | ✓ | 18,802 |
| 4ba4a7ec | ✓ | 18,116 |
| f62c1fa3 | ✓ | 17,271 |
| 562cfc29 | ✓ | 17,168 |
| eb252a80 | ✓ | 16,820 |
| 01e395d0 | ✓ | 15,810 |
| b20b39bf | ✓ | 15,518 |
| 5309f723 | ✓ | 14,773 |
| a62dd199 | ✓ | 13,982 |
| b16455a2 | ✓ | 13,812 |
| 288c7eca | ✓ | 13,367 |
| 101e6f80 | ✓ | 11,845 |
| 7c538bb0 | ✓ | 10,607 |
| 31a4c9ef | ✓ | 10,275 |
| b2bdef43 | ✓ | 9,962 |
| 4f80d363 | ✓ | 9,223 |
| b1f5a2e8 | ✓ | 9,110 |
| 7b107eec | ✓ | 8,399 |
| 4510a429 | ✓ | 7,975 |
| ccf02dee | ✗ | 7,813 |
| 236034b4 | ✓ | 7,618 |
| 1fd310dc | ✓ | 7,223 |
| 4c06f388 | ✓ | 7,004 |
| a7dcc027 | ✓ | 6,880 |
| 008b52fd | ✓ | 6,310 |
| 563c1afa | ✓ | 6,000 |
| bb429016 | ✓ | 5,720 |
| f9c59b61 | ✓ | 5,153 |
| 8b471ce9 | ✓ | 4,358 |
| 57b03b2b | ✓ | 2,566 |
| 214d0570 | ✓ | 2,492 |
| 93ef4c81 | ✓ | 2,346 |
| 6eb0d262 | ✓ | 2,296 |
| dbb789cc | ✓ | 2,255 |
| 77804b32 | ✓ | 2,079 |
| c6fa3e3f | ✓ | 2,026 |
| b30f8610 | ✓ | 1,991 |
| af5e4060 | ✓ | 1,938 |
| 499c7735 | ✓ | 1,890 |
| f94ed862 | ✓ | 1,820 |
| 053f87d3 | ✓ | 1,750 |
| f5d74f50 | ✓ | 1,742 |
| 75e869dd | ✓ | 1,732 |
| 2f51362d | ✓ | 1,704 |
| 3dcc0195 | ✓ | 1,684 |
| 7669569d | ✓ | 1,680 |
| 06698d4e | ✓ | 1,662 |
| e818def8 | ✓ | 1,632 |
| b634898d | ✓ | 1,622 |
| 1bcd2b16 | ✓ | 1,558 |
| ca72b5b3 | ✓ | 1,529 |
| e72155f3 | ✓ | 1,518 |
| 28b6bc51 | ✓ | 1,510 |
| a897b8bc | ✓ | 1,497 |
| c536c44c | ✓ | 1,432 |
| 8c743940 | ✓ | 1,426 |
| 5028d953 | ✓ | 1,386 |
| 649bebaf | ✓ | 1,378 |
| c0788894 | ✓ | 1,375 |
| 3d8e6b03 | ✓ | 1,352 |
| 3456da40 | ✓ | 1,274 |
| 9b2b3698 | ✓ | 1,261 |
| 9972f3f1 | ✓ | 1,230 |
| 106aeb25 | ✓ | 1,225 |
| d25d3b5f | ✓ | 1,172 |
| b91855fd | ✓ | 1,160 |
| 378741b0 | ✓ | 1,053 |
| e6af8e6f | ✓ | 1,029 |
| 124bc762 | ✓ | 1,017 |
| dbabfbdd | ✓ | 989 |
| 4ef3d311 | ✓ | 943 |
| 2441e2b4 | ✓ | 942 |
| dc99f250 | ✓ | 928 |
| 807c4206 | ✓ | 907 |
| 7b412ac0 | ✓ | 889 |
| e0918834 | ✓ | 857 |
| 6e56c02c | ✓ | 850 |
| 67032a5c | ✓ | 842 |
| 23410e94 | ✓ | 838 |
| 6a578940 | ✓ | 820 |
| e5bb9b26 | ✗ | 811 |
| 6e80733d | ✓ | 806 |
| 75cd54d8 | ✓ | 801 |
| d547f717 | ✓ | 776 |
| 3400e0d5 | ✓ | 775 |
| 35dafdbc | ✓ | 763 |
| 522058b9 | ✓ | 761 |
| fecfb467 | ✓ | 742 |
| 88c482d3 | ✓ | 740 |
| e928acf8 | ✓ | 723 |
| 2dcfc1a3 | ✓ | 722 |
| 0c7acd69 | ✓ | 721 |
| d6ceda8e | ✓ | 713 |
| d864f0fb | ✓ | 709 |
| 34b9db0e | ✓ | 703 |
| 738f7c2d | ✓ | 665 |
| 8a5742e1 | ✓ | 665 |
| 5a1179ee | ✓ | 663 |
| baa9e4ea | ✓ | 656 |
| 43b9343e | ✓ | 652 |
| 6bef21ca | ✓ | 631 |
| 3ad042eb | ✓ | 626 |
| e67cbe88 | ✓ | 624 |
| 573eaca1 | ✓ | 621 |
| 823be38e | ✓ | 604 |
| 201b150e | ✓ | 601 |
| eae81189 | ✓ | 597 |
| 4a374160 | ✓ | 597 |
| 48db5ccf | ✓ | 593 |
| 7af6e047 | ✓ | 592 |
| 14742dd8 | ✓ | 570 |
| 4c8182b0 | ✓ | 566 |
| f24b8bee | ✓ | 564 |
| 08615ada | ✓ | 559 |
| 1249ddb4 | ✓ | 548 |
| 792a5ccd | ✓ | 536 |
| dff2a315 | ✓ | 518 |
| 1e677e2c | ✓ | 514 |
| 26e985b5 | ✓ | 513 |
| eeb60061 | ✓ | 504 |
| f929c6cc | ✓ | 502 |
| f4bb4d9c | ✓ | 488 |
| fd699316 | ✓ | 486 |
| f8f4c3b4 | ✓ | 486 |
| a8f5ad76 | ✓ | 483 |
| af358750 | ✓ | 477 |
| e5a5fdef | ✓ | 473 |
| 3e000b40 | ✓ | 466 |
| a1a61c77 | ✓ | 466 |
| 1c19ad3e | ✓ | 465 |
| d290b24e | ✓ | 435 |
| 7aba9046 | ✓ | 428 |
| 294557bb | ✓ | 414 |
| fb955790 | ✓ | 405 |
| 0d7aacfc | ✓ | 400 |
| ab5f7c7f | ✓ | 398 |
| 4575c0a2 | ✓ | 395 |
| 1fa373db | ✓ | 393 |
| aa3ae31f | ✓ | 386 |
| 4ec611d7 | ✓ | 373 |
| 5281a6b3 | ✓ | 373 |
| d2695f15 | ✓ | 371 |
| c5872355 | ✓ | 369 |
| 9e61762f | ✓ | 363 |
| 00754598 | ✓ | 353 |
| b287ee74 | ✓ | 351 |
| dbf2b40f | ✓ | 331 |
| d727ad5f | ✓ | 329 |
| 0ddca8bf | ✓ | 324 |
| 0855605b | ✓ | 324 |
| 9c5c6401 | ✓ | 317 |
| c2dacc5b | ✓ | 300 |
| 45da0a33 | ✓ | 297 |
| fb5a7b9e | ✓ | 289 |
| b5e40e49 | ✓ | 278 |
| 789b83ce | ✓ | 272 |
| ce862776 | ✓ | 270 |
| fd03c3d3 | ✓ | 268 |
| ee3bbe87 | ✓ | 268 |
| b14f7be3 | ✓ | 250 |
| 2b16044a | ✓ | 243 |
| 3385a400 | ✓ | 242 |
| 91dc0848 | ✓ | 237 |
| d8d3648f | ✓ | 237 |
| a4970d02 | ✓ | 235 |
| 35e3c7c5 | ✓ | 235 |
| ea0deb13 | ✓ | 230 |
| 5f76ba09 | ✓ | 230 |
| 4b925449 | ✓ | 227 |
| 4b86e0bb | ✓ | 216 |
| c113055a | ✓ | 210 |
| 36300e18 | ✓ | 208 |
| 7eaa679e | ✓ | 207 |
| 4e918d82 | ✓ | 192 |
| 81e39cf5 | ✓ | 175 |
| 129d29e1 | ✓ | 160 |
| d4612468 | ✓ | 136 |
