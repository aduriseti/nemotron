# Bit Manipulation — Transform Pattern Analysis (300-problem sample)

Sample: 300 problems (seed=42)

## 1. Transform type frequency

| Type | Count | % |
|------|-------|---|
| rot | 230 | 32.1% |
| shl | 248 | 34.6% |
| shr | 239 | 33.3% |

## 2. Shift/rotation amount (k) distribution

| k | rot | shl | shr | total |
|---|-----|-----|-----|-------|
| 0 | 2 | 0 | 0 | 2 |
| 1 | 30 | 34 | 45 | 109 |
| 2 | 27 | 35 | 37 | 99 |
| 3 | 38 | 39 | 34 | 111 |
| 4 | 41 | 31 | 34 | 106 |
| 5 | 22 | 32 | 31 | 85 |
| 6 | 36 | 37 | 23 | 96 |
| 7 | 34 | 40 | 35 | 109 |

## 3. Most common individual transforms

| Transform | Count |
|-----------|-------|
| shr(1) | 45 |
| rot(4) | 41 |
| shl(7) | 40 |
| shl(3) | 39 |
| rot(3) | 38 |
| shl(6) | 37 |
| shr(2) | 37 |
| rot(6) | 36 |
| shr(7) | 35 |
| shl(2) | 35 |
| shr(4) | 34 |
| rot(7) | 34 |
| shr(3) | 34 |
| shl(1) | 34 |
| shl(5) | 32 |

## 4. Transform usage by boolean function

| Function | Arity | Problems | Top transforms |
|----------|-------|----------|----------------|
| `({B} XOR {A})` | 2 | 123 | shl(6):19, shl(5):18, shr(1):18, shl(1):18 |
| `NOT((NOT({A}) AND ({C} XOR {B})))` | 3 | 63 | shr(7):15, rot(3):15, rot(6):13, shl(7):12 |
| `({B} OR {A})` | 2 | 24 | rot(3):7, rot(7):5, rot(2):4, rot(4):3 |
| `({B} AND {A})` | 2 | 21 | rot(4):5, rot(1):4, rot(7):4, rot(3):4 |
| `({A} AND NOT({B}))` | 2 | 15 | shl(7):6, rot(3):3, shl(4):3, shl(6):3 |
| `(NOT({A}) XOR (({C} XOR {B}) AND ({C} OR {A})))` | 3 | 15 | shr(2):6, rot(7):5, shl(2):4, shl(1):4 |
| `({A} XOR ({B} AND ({C} XOR {A})))` | 3 | 11 | shr(2):5, rot(3):4, shr(1):4, shl(2):3 |
| `({A} OR ({C} AND {B}))` | 3 | 10 | rot(4):7, shl(4):3, shr(4):3, shr(5):2 |
| `({A} AND ({C} OR {B}))` | 3 | 10 | rot(1):4, shr(7):4, shr(6):3, rot(4):3 |
| `({A} XOR (({B} XOR {A}) AND ({C} XOR {A})))` | 3 | 8 | shr(1):4, shl(3):4, rot(1):4, rot(6):3 |
