

### Step 9: Synthetic CoT SFT (Behavioral Cloning - Rule-Based)
**Goal:** Implement Process-Supervised Fine-Tuning (PRM) by generating perfect, programmatic `<think>` traces for the deterministic puzzle types.
*   **Key Tasks:**
    *   Extract Python solvers for Roman Numerals, Physics (Gravity), and Unit Conversion.
    *   Modify the solvers to output step-by-step logic strings (e.g., extracting variables, applying formulas).
    *   Format training targets as: `<think> [Generated Logic] </think> \boxed{Answer}`.
    *   Fine-tune using `DataCollatorForCompletionOnlyLM` so loss is calculated on the reasoning steps.
*   **Relevant Notebooks:**
    *   `nemotron-6-puzzle-types-decoded-rule-solvers` (Contains the Python solvers we will adapt)
    *   `synthetic-dataset-generator-27k.py`
    *   `bit-manipulation-solver-cot-generator.py`
    *   `/workspaces/nemotron-kaggle/kaggle_notebooks/nvidia-nemotron-sft-grpo-colab-faster.py`
    *   `/workspaces/nemotron-kaggle/kaggle_notebooks/puzzle_types_reverse_engineered.md`
