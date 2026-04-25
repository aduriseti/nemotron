# Empirical Frequency Analysis

- Problems analysed: 100
- Problems solved (≥1 correct solution): 93
- Each problem contributes weight 1.0 total (split evenly across correct solutions)

## Operation Frequencies

Weighted sum = 93.0 (= n_solved = 93)

|      Operation |   Weight | Frequency | Rank |
|----------------:|----------:|-----------:|------|
|            add |    17.62 |    18.9%  |    1 |
|            sub |    14.82 |    15.9%  |    2 |
|            mul |    13.00 |    14.0%  |    3 |
|        sub_abs |     8.88 |     9.5%  |    4 |
|          addm1 |     8.04 |     8.6%  |    5 |
|            cat |     8.00 |     8.6%  |    6 |
|           mul1 |     7.00 |     7.5%  |    7 |
|    max_mod_min |     6.56 |     7.1%  |    8 |
|    sub_neg_abs |     4.50 |     4.8%  |    9 |
|           add1 |     3.58 |     3.8%  |   10 |
|          mulm1 |     1.00 |     1.1%  |   11 |

**Recommended op order**: `['add', 'sub', 'mul', 'sub_abs', 'addm1', 'cat', 'mul1', 'max_mod_min', 'sub_neg_abs', 'add1', 'mulm1']`

## Pipeline Frequencies

Weighted sum = 93.0 (= n_solved = 93)

|   Pipeline |   Weight | Frequency |
|------------:|----------:|-----------:|
|        raw |    52.48 |    56.4%  |
|       swap |    29.00 |    31.2%  |
|        rev |    11.52 |    12.4%  |

**Recommended pipeline order**: `['raw', 'swap', 'rev']`

## Digit Value Frequencies

Weighted sum = 892.0 (each problem contributes #unique_digits_used weight)

| Digit |   Weight | % of total | Rank |
|-------:|----------:|------------:|------|
|     4 |    92.45 |     10.4%  |    1 |
|     1 |    91.84 |     10.3%  |    2 |
|     3 |    90.91 |     10.2%  |    3 |
|     6 |    89.95 |     10.1%  |    4 |
|     5 |    89.84 |     10.1%  |    5 |
|     2 |    89.72 |     10.1%  |    6 |
|     7 |    89.34 |     10.0%  |    7 |
|     8 |    87.59 |      9.8%  |    8 |
|     9 |    86.92 |      9.7%  |    9 |
|     0 |    83.45 |      9.4%  |   10 |

**Recommended digit order**: `[4, 1, 3, 6, 5, 2, 7, 8, 9, 0]`

## Per-Position Digit Frequencies

Each position sums to n_solved (weight 1.0 per problem per position).

| Digit | A0 (tens-L) | A1 (ones-L) | B0 (tens-R) | B1 (ones-R) |
|-------:|-------------:|-------------:|-------------:|-------------:|
|     0 |       0.0% |      11.2% |       0.0% |      10.5% |
|     1 |      11.5% |      10.8% |      10.9% |      10.1% |
|     2 |      12.1% |       8.6% |      10.0% |      11.7% |
|     3 |      10.7% |      11.1% |      11.0% |       8.9% |
|     4 |      11.9% |       8.4% |      11.4% |       8.6% |
|     5 |      13.0% |      10.0% |      11.7% |       7.3% |
|     6 |      10.8% |       9.4% |      11.9% |       9.6% |
|     7 |       8.4% |      11.4% |      11.4% |      11.6% |
|     8 |      11.3% |       6.6% |      11.4% |      11.1% |
|     9 |      10.2% |      12.4% |      10.4% |      10.5% |

### Recommended digit order per position
- `A0`: `[5, 2, 4, 1, 8, 6, 3, 9, 7, 0]`
- `A1`: `[9, 7, 0, 3, 1, 5, 6, 2, 4, 8]`
- `B0`: `[6, 5, 8, 7, 4, 3, 1, 9, 2]`
- `B1`: `[2, 7, 8, 9, 0, 1, 6, 3, 4, 5]`

