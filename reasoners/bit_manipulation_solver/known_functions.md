# Known Boolean Functions in the Bit Manipulation Dataset

24 distinct boolean functions cover 100% of the 1602 problems.
Listed in order of frequency (most common first).

| Arity | Truth Table | Dec | Freq | Grammar Expression |
|-------|-------------|-----|------|--------------------|
| 2 | `0110` | 6 | 324 | `({B} XOR {A})` |
| 2 | `1110` | 14 | 289 | `({B} OR {A})` |
| 1 | `10` | 2 | 149 | `{A}` |
| 3 | `11101011` | 235 | 164 | `NOT((NOT({A}) AND ({C} XOR {B})))` |
| 2 | `1000` | 8 | 131 | `({B} AND {A})` |
| 2 | `0010` | 2 | 86 | `({A} AND NOT({B}))` |
| 3 | `11101010` | 234 | 70 | `({A} OR ({C} AND {B}))` |
| 3 | `10101001` | 169 | 61 | `(NOT({A}) XOR ({C} OR {B}))` |
| 3 | `10101000` | 168 | 61 | `({A} AND ({C} OR {B}))` |
| 3 | `11101000` | 232 | 54 | `({A} XOR (({B} XOR {A}) AND ({C} XOR {A})))` |
| 3 | `01101101` | 109 | 53 | `(NOT({A}) XOR (({C} XOR {B}) AND ({C} OR {A})))` |
| 3 | `11100010` | 226 | 46 | `({A} XOR ({B} AND ({C} XOR {A})))` |
| 2 | `1001` | 9 | 41 | `NOT(({B} XOR {A}))` |
| 2 | `1011` | 11 | 25 | `({A} OR NOT({B}))` |
| 3 | `10010101` | 149 | 13 | `(NOT({A}) XOR ({C} AND {B}))` |
| 3 | `01101010` | 106 | 10 | `({A} XOR ({C} AND {B}))` |
| 3 | `01011001` | 89 | 6 | `NOT((({B} XOR {A}) XOR ({C} AND {B})))` |
| 3 | `10001010` | 138 | 4 | `({A} AND ({B} OR NOT({C})))` |
| 3 | `11111101` | 253 | 3 | `(NOT({A}) OR ({C} OR {B}))` |
| 3 | `01100100` | 100 | 2 | `(({B} XOR {A}) AND ({C} OR {B}))` |
| 2 | `0001` | 1 | 2 | `NOT(({B} OR {A}))` |
| 3 | `10101011` | 171 | 1 | `NOT((NOT({A}) AND ({C} OR {B})))` |
| 3 | `01111101` | 125 | 1 | `(NOT({A}) OR ({C} XOR {B}))` |
| 2 | `0111` | 7 | 1 | `NOT(({B} AND {A}))` |
| 0 | `0` | 0 | 3 | `0` |
| 0 | `1` | 1 | 2 | `1` |

## Notes
- Arity-0: constant output (independent of input)
- Arity-1: output depends on one transformed input
- Arity-2: output depends on two distinct transforms of the input
- Arity-3: output depends on three distinct transforms of the input
- Variables {A},{B},{C} are placeholders; each is assigned one of 22 transforms
  (rot 0-7, shl 1-7, shr 1-7) when solving a specific problem.
