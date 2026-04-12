# Implementation Plan: Process-Supervised True Solvers (Donald's Methodology)

## Background & Motivation
Our diagnostic baseline evaluation revealed that the existing "solvers" in the repository either cheat by peeking at the answer (Baseline Generators) or have significant accuracy gaps and lack rigorous CoT traces (True Solvers: 58% - 82% accuracy, except Roman). 

To achieve 100% accuracy and produce high-quality, verifiable Process-Supervised Fine-Tuning (SFT) data, we need to implement true algorithmic solvers that exactly mirror the rigid `S1...S4` logical structure detailed in Donald's Kaggle post (`puzzle_types_reverse_engineered.md`).

We will implement these solvers iteratively, starting with the easiest categories and progressing to the hardest, verifying accuracy at each step.

## Key Insights from Donald's Post
Donald's methodology treats these puzzles like Sudoku: you must **PROVE** the math is correct first at each step, lock what you can prove, and if you hit a contradiction later, you backtrack. 
- **Bit-Serial Gate Computation:** For binary, the model cannot do multi-bit AND/OR/XOR in parallel. You must force it to spell out every op one bit at a time (e.g., `0&1=0 1&1=1`).
- **Target Verification:** Multiple ops can match all examples by coincidence. You must cross-validate (e.g., `|RATE - RATE2| < 0.05` for Gravity).
- **Rule Preamble:** Every trace must begin with a strong preamble asserting its identity and rules, and explicitly rejecting the flavor text. This prevents the model from being distracted by "Alice in Wonderland" noise.

## Scope & Impact
1.  **Refactor `inspect_existing_cots.py`:** Clean up the notebook to output Pandas DataFrames natively for better visual inspection and hide the sample dumps so we can focus strictly on the `true_acc` metric.
2.  **Iterative Implementation (`src/synthetic_cot/donald_solvers.py`):**
    *   **Phase 1 (Easiest): Unit Conversion (`unitconv`)**
    *   **Phase 2 (Easy): Gravity (`gravity`)**
    *   **Phase 3 (Medium): Base Conversion (`roman`)**
    *   **Phase 4 (Hard): Text Encryption (`cipher`)**
    *   **Phase 5 (Hard): Equation Transformation - Numeric (`symbol_digit`)**
    *   **Phase 6 (Harder): Equation Transformation - Symbolic (`cipher_digit`)**
    *   **Phase 7 (Hardest): Bit Manipulation (`binary`)**

## Implementation Phases & Traces

### Phase 1: Unit Conversion
*   **Logic:** Extract EX1 (`in1`, `out1`) and compute `RATE = out1 / in1`. Extract target and compute `RESULT = target * RATE`. Round to exactly 2 decimals.
*   **Verification (S3):** Extract EX2 (`in2`, `out2`), compute `RATE2 = out2 / in2`, and assert `|RATE - RATE2| < 0.01` to ensure the rate is consistent.
*   **Donald's Trace Reference:** `src/synthetic_cot/donald_traces/unitcon.txt`

### Phase 2: Gravity
*   **Logic:** Extract EX1 (`t1`, `d1`). Compute `T_SQ = t1^2`. Compute `RATE = d1 / T_SQ`. Extract target `t_q` and compute `TGT_SQ = t_q^2`. Compute `RESULT = RATE * TGT_SQ`. Round to 2 decimals.
*   **Verification (S3):** Extract EX2 (`t2`, `d2`), compute `RATE2 = d2 / t2^2`, and assert `|RATE - RATE2| < 0.05`.
*   **Donald's Trace Reference:** `src/synthetic_cot/donald_traces/gravity.txt`

### Phase 3: Roman Numerals
*   **Forward Logic (Dec -> Roman):** `DECOMPOSE` the integer into thousands, hundreds, tens, units. Convert each to Roman numerals. `CAT` (concatenate) the strings.
*   **Reverse Logic (Roman -> Dec):** `PARSE` the Roman numeral string. Convert characters to integers. `VER` (verify) by checking if reversing the process yields the original string.
*   **Donald's Trace References:** 
    *   Forward: `src/synthetic_cot/donald_traces/roman.txt`
    *   Reverse: `src/synthetic_cot/donald_traces/roman_reverse.txt`

### Phase 4: Text Encryption
*   **Logic:** `S2: LEN` (word lengths). `S3: TABLE` (build mapping from examples).
*   **Verification:** `VER` mapping, then `DECRYPT` char by char. Finally `CHECK` (vocab match, length match).
*   **Donald's Trace Reference:** `src/synthetic_cot/donald_traces/cipher.txt`

### Phase 5: Equation Transformation (Numeric / `symbol_digit`)
*   **Logic:** Parse operators and operands. Perform a brute-force frequency scan across 47 known operator functions.
*   **Verification:** `VER` on EX2. `LOCK` the winning rule.
*   **Donald's Trace Reference:** `src/synthetic_cot/donald_traces/symboldigit.txt`

### Phase 6: Equation Transformation (Symbolic / `cipher_digit`)
*   **Logic:** First, crack the symbol-to-digit cipher. Then, apply symbol_digit logic.
*   **Donald's Trace Reference:** `src/synthetic_cot/donald_traces/cipherdigit.txt`

### Phase 7: Bit Manipulation
*   **Logic:** Re-implement the massive bit manipulation solver. Instead of the current heuristics, rigidly implement Donald's `S1: ALIGN`, `S2: COLUMNS` (bit-serial processing like `i0=... i1=...`), `S3: SCAN` (finding boolean gates that satisfy the columns), and `S4: LOCK` syntax. 
*   **Verification (S3):** Verify the selected boolean gate satisfies all example columns for that bit position.
*   **Donald's Trace Reference:** `src/synthetic_cot/donald_traces/binary.txt`

## Verification & Testing
- We will execute `pytest tests/test_existing_cots_notebook.py` after implementing each phase.
- We expect the Pandas DataFrame output to show `donald_acc` (or similar metric) reaching 100% for the targeted category at each step.