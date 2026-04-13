# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Answers To Equation Data: Read Me! 84% Solve Rate
#
# 99% solve rate, problems with the target operator in examples.
#
# **Verification of Pre-Op / Mid-Op / Post-Op Pipeline Hypothesis**
#
# Reverse-engineering results from Kaggle "Equation Transformation" competition,   
# inspired by [Answers To Everything Data: Read Me! 100% Solve Rate](link).
#
# | Aspect | Details |
# |--------|---------|
# | **Objective** | Uncover mechanisms for deriving correct answers |
# | **Focus** | Equation Transformation (Numeric) |
# | **Dataset** | 732 problems analyzed |

# %% [markdown]
# ## Section 0: Contribution
#
# ### Key Results
#
# - **High Verification Rate**: 618 out of 732 Numeric problems (84.4%) have solutions matching the target answer
# - **Strict Quality Threshold**: 532 problems (72.6%) achieve ALL_VERIFIED status (all candidate solutions match target)
#
# ### 📊 Dataset Statistics
#
# ```
# Equation Transformation Problems (Numeric):
#   Total Equation Transformation problems:    1,555
#   Numeric subset analyzed:                     732
#
# Solution Quality Breakdown:
#   ALL_VERIFIED (all solutions match target):                       532 (72.6%)
#   PARTIAL_VERIFIED (some solutions match, others don't):            63 (8.6%)
#   NONE_VERIFIED (no solutions match target):                       145 (19.8%)
#
#
# Generated Chain-of-Thought Dataset Analysis
# - Total Numeric problems analyzed: 732
# - Average tokens per problem: 2,188
# - Token range: 971 to 5,000
#
# VERIFIED STATS:
#   verified=True: 618 (84.4%)
#   verified=False: 114 (15.6%)
#
# ```
#
# ### 📈 Research Methodology
#
# The dataset was constructed through:
# 1. **Solution Extraction**: Derive solutions from examples using Pre-Op/Mid-Op/Post-Op pipeline combinations
# 2. **Solution Verification**: Test each solution against target answer
# 3. **Operator Coverage Analysis**: Map target operators to applicable operations
# 4. **Format Pattern Analysis**: Identify Pre-Op/Post-Op combinations that actually occur
#
# ### 🎯 Key Findings
#
# - **Rigorous hypothesis validation** through exhaustive enumeration against 732 problems
# - **Strong pattern constraint**: Only 6 format patterns observed (vs. 156 theoretical possibilities)
# - **High-quality training data**: 72.6% of problems have fully verified solutions and token-efficient.
#

# %% [markdown]
# ## Section 1: Introduction & Hypothesis
#
# ### Hypothesis: Three-Stage Pipeline Model
#
# We propose that problem solving follows a decomposable three-stage process:
#
# #### **Stage 1: Pre-Op (Operand Preprocessing)**
# - **Purpose**: Determine permutation order of operands
# - **Observed Patterns**: `ABCD` (original), `BADC` (swap), `CDAB` (rotate), `DCBA` (reverse) — 4 variants
# - **Key Insight**: Most problems follow one of these four permutation patterns consistently
#
# #### **Stage 2: Mid-Op (Core Transformation)**
# - **Operations**: Arithmetic (add, sub, mul), string manipulation (cat), and variants
# - **Variants**: add1, addm1, mul1, mulm1, sub_abs, sub_rev, sub_neg_abs
# - **Special Rule**: `mod` always computed as `max(L,R) mod min(L,R)`
# - **Consistency**: Within a problem, the same operation variant doesn't appear under different operators (except `cat`)
#   - See 2f485a40, 2a73a462, 2a73a462, 4245e455.
#   - Sub variants and mod never exist concurrently
#
# #### **Stage 3: Post-Op (Result Finalization)**
# - **Purpose**: Transform the operation result
# - **Patterns**: 
#   - `raw` — use result as-is EF → EF
#   - `rev` — reverse, including sign. -EF → FE-
#   - `swap` — reverse, excluding sign. -EF → -FE
#
# ### Important Caveats
#
# **What This Hypothesis IS:**
# - ✅ Empirical pattern observed in 732 problems
# - ✅ Necessary framework for organizing transformation rules
#
# **What This Hypothesis IS NOT:**
# - ❌ Complete explanation for all problems (covers ~99%)
#     - Some problems (9/596) don't align with this hypothesis.
# - ❌ Insufficient alone to achieve perfect solving — requires additional ranking heuristics to disambiguate ambiguous problems.
#

# %% [markdown]
# ## Section 2: Methodology
#
# ### Verification Framework
#
# We validate our Pre-Op/Mid-Op/Post-Op hypothesis through exhaustive enumeration and target verification:
#
# #### **Exhaustive Solution Extraction Algorithm**
#
# For each problem:
# 1. **Extract examples**: Parse all input-output pairs (Example 1, Example 2, ... Example N)
# 2. **Generate solution candidates** from examples:
#    - Enumerate all Pre-Op patterns (ABCD, BADC, CDAB, DCBA)
#    - Enumerate all Mid-Op operations (add, sub, mul, cat, mod, variants)
#    - Enumerate all Post-Op patterns (raw, rev, swap)
#    - For each combination: apply to examples and check if it produces correct outputs
#    - **Collect solutions**: Any (Pre-Op, Mid-Op, Post-Op) tuple that satisfies ALL examples
# 3. **Verify solutions against target answer**:
#    - For each solution discovered from examples
#    - Apply: target_input → Pre-Op → Mid-Op → Post-Op → prediction
#    - Check if prediction equals target_answer
#    - Mark solution as: verified=True or verified=False
# 4. **Classify problem** based on solution verification results:
#    - **ALL_VERIFIED**: ALL solutions match target_answer ✅
#    - **PARTIAL_VERIFIED**: SOME solutions match, OTHERS don't ⚠️
#    - **NONE_VERIFIED**: NO solutions match target_answer ❌
#
# #### **Key Distinction**
# - **Solutions** = (Pre-Op, Mid-Op, Post-Op) tuples that fit the training examples
# - **Verification** = Do those solutions correctly predict the target answer?
# - Multiple solutions can exist; we track how many verify against target
#
# #### **Additional Tracking**
#
# For each problem, we also record:
# - **Target operator presence**: Is the target operator visible in training examples?
# - **Format pattern used**: Which (Pre-Op, Post-Op) pair appears in verified solutions
# - **Operation distribution**: Which Mid-Op operations appear across solutions
#
# #### **Quality Definitions**
#
# **ALL_VERIFIED (Highest Confidence)**
# - Every solution derived from examples correctly predicts the target answer
# - Highly reliable for future test cases
# - These problems represent best-quality training data
#
# **PARTIAL_VERIFIED (Medium Confidence)**
# - Some solutions work on the target answer, some don't
# - Indicates potential ambiguity or data inconsistency
# - Disambiguation needed: which is the "true" solution?
#
# **NONE_VERIFIED (Lowest Confidence)**
# - Not a single solution from examples predicts the target answer correctly
# - Mainly because some problems(~20%) do not offer the target operator in examples.
#

# %%
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Setup plotting style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)

print("✓ Libraries imported successfully")
# Load datasets
DATA_DIR_ACTUAL = Path('/kaggle/input/datasets/optiminist/equation-numeric-analysis')

df_formats = pd.read_csv(DATA_DIR_ACTUAL / 'stat_format_combinations.csv')
df_operations = pd.read_csv(DATA_DIR_ACTUAL / 'stat_operator_operation_flat.csv')
df_solutions = pd.read_csv(DATA_DIR_ACTUAL / 'numeric_solutions_classification.csv')

print("✓ Data loaded successfully\n")

# %% [markdown]
# ## Section 3: Results - Format Pattern Analysis
#
# The most striking finding: **Only 6 format combinations actually appear in the data.**

# %%
# Visualize Format Combinations Distribution
fig, ax = plt.subplots(figsize=(10, 6))

# Create format labels
df_formats['format_label'] = df_formats['pre_format'] + '_' + df_formats['post_format']
colors = plt.cm.Set2(np.linspace(0, 1, len(df_formats)))

bars = ax.bar(df_formats['format_label'], df_formats['count'], color=colors, edgecolor='black', linewidth=1.5)

# Add value labels on bars
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{int(height)}',
            ha='center', va='bottom', fontsize=11, fontweight='bold')

ax.set_ylabel('Frequency', fontsize=12, fontweight='bold')
ax.set_xlabel('Format Combination (Pre-Op_Post-Op)', fontsize=12, fontweight='bold')
ax.set_title('Distribution of Format Combinations (Only 6 Patterns)', fontsize=14, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

# Rotate x labels
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()

# %% [markdown]
# ## Section 4: Operator × Operation Correlation
#
# ### Top Operator-Operation Mappings
#
# This table shows which operations are most frequently used for each target operator.
# - **Single dominant operation** → Strong pattern (high confidence)
# - **Multiple operations** → Exploration space (multiple candidates likely)

# %%
# Analyze top operators and their operation mappings
top_operators = df_operations['target_operator'].value_counts().head(10).index

# Create a pivot table for heatmap visualization
pivot_data = df_operations.pivot_table(
    index='target_operator',
    columns='normalized_operation',
    values='count',
    fill_value=0
)

# Sort by total count
pivot_data['total'] = pivot_data.sum(axis=1)
pivot_data = pivot_data.sort_values('total', ascending=False).drop('total', axis=1)

# Show top 15 operators with their operations
pivot_display = pivot_data.head(15)

# Visualize as Heatmap
fig, ax = plt.subplots(figsize=(14, 8))
sns.heatmap(pivot_display, annot=True, fmt='.0f', cmap='YlOrRd', ax=ax, cbar_kws={'label': 'Frequency'})
ax.set_title('Top 15 Operators × Operations Heatmap', fontsize=14, fontweight='bold')
ax.set_xlabel('Normalized Operation', fontsize=12, fontweight='bold')
ax.set_ylabel('Target Operator', fontsize=12, fontweight='bold')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()

# %% [markdown]
# ## Section 5: Solution Quality Verification
#
# ### Solution Classification Results
#
# For each problem, we extract solutions from examples and verify them against the target answer.
#
# Problems are classified by **verification rate of extracted solutions**:
#
# 1. **ALL_VERIFIED** ✅: ALL solutions extracted from examples correctly predict the target answer
#    - Every (Pre-Op, Mid-Op, Post-Op) tuple that fits examples also works on target
#    - High confidence in solution quality
#    
# 2. **PARTIAL_VERIFIED** ⚠️: SOME solutions predict the target answer, but OTHERS don't
#    - Mixed results: some tuples work on target, others fail
#    - Indicates ambiguity or conflicting constraints
#    
# 3. **NONE_VERIFIED** ❌: NO solutions from examples predict the target answer
#
# Additionally, we track whether the target operator appears in any of the training examples (relevant for assessing generalization difficulty).
#

# %%
# === DETAILED ROOT CAUSE ANALYSIS: NONE_VERIFIED Breakdown ===

none_verified_df = df_solutions[df_solutions['solution_quality'] == 'NONE_VERIFIED']
total_none_verified = len(none_verified_df)

# Root cause classification
none_with_op = len(none_verified_df[none_verified_df['target_op_in_examples'] == True])
none_without_op = len(none_verified_df[none_verified_df['target_op_in_examples'] == False])

# Visualization
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))

# Pie: NONE_VERIFIED root cause breakdown
root_causes = [none_with_op, none_without_op]
root_labels = [
    f'Model Limitation\n(In Examples)\n{none_with_op}',
    f'Data Quality Concern\n(Not In Examples)\n{none_without_op}'
]
colors_pie = ['#FF6B6B', '#FFB6B6']
wedges, texts, autotexts = ax1.pie(root_causes, labels=root_labels, colors=colors_pie, autopct='%1.1f%%',
                                     startangle=90, textprops={'fontsize': 10, 'weight': 'bold'})
ax1.set_title('NONE_VERIFIED: Root Cause Distribution', fontsize=12, fontweight='bold')

# Bar: Operator presence distribution across all quality classes
quality_vs_op_pct = pd.crosstab(df_solutions['solution_quality'], 
                                 df_solutions['target_op_in_examples'], 
                                 normalize='index') * 100

quality_order = ['ALL_VERIFIED', 'PARTIAL_VERIFIED', 'NONE_VERIFIED']
quality_vs_op_pct = quality_vs_op_pct.reindex(quality_order)

bars = ax2.bar(range(len(quality_order)), quality_vs_op_pct[False], label='Not in Examples', 
               color='#FFB6B6', edgecolor='black', linewidth=1.2)
bars2 = ax2.bar(range(len(quality_order)), quality_vs_op_pct[True], bottom=quality_vs_op_pct[False],
                label='In Examples', color='#4ECDC4', edgecolor='black', linewidth=1.2)

# Add percentage labels
for i, q in enumerate(quality_order):
    not_in = quality_vs_op_pct.loc[q, False]
    in_ex = quality_vs_op_pct.loc[q, True]
    ax2.text(i, not_in/2, f'{not_in:.0f}%', ha='center', va='center', 
            fontsize=10, weight='bold', color='white')
    ax2.text(i, not_in + in_ex/2, f'{in_ex:.0f}%', ha='center', va='center',
            fontsize=10, weight='bold', color='white')

ax2.set_xticks(range(len(quality_order)))
ax2.set_xticklabels(quality_order, rotation=0)
ax2.set_ylabel('Percentage (%)', fontsize=11, fontweight='bold')
ax2.set_ylabel('Solution Quality', fontsize=11, fontweight='bold')
ax2.set_title('Operator Presence Distribution by Quality Class', fontsize=12, fontweight='bold')
ax2.legend(fontsize=10, loc='upper left')
ax2.set_ylim(0, 100)
ax2.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.show()


# %% [markdown]
# ### Breakdown by Target Operator Presence
#
# | Quality | Operator NOT in Examples | Operator IN Examples | Total |
# |---|---|---|---|
# | ALL_VERIFIED | 0 | 524 | 524 |
# | PARTIAL_VERIFIED | 0 | 63 | 63 |
# | NONE_VERIFIED | 136 | 9 | 145 |
# | **All** | **136** | **596** | **732** |
#
# **Key Insights:**
# - **ALL_VERIFIED problems**: ALL require visible operators (100% target_op_in_examples)
# - **PARTIAL_VERIFIED problems**: ALL also require visible operators (100% target_op_in_examples)
# - **NONE_VERIFIED breakdown**:
#   - 136 cases (93.8%) with operator NOT in examples → Data quality / generalization challenge
#   - 9 cases (6.2%) with operator IN examples → Algorithm incompleteness (hypothesis needs extension)

# %% [markdown]
# # Appendix
# ### 053f4545
#
# ```
# In Alice's Wonderland, a secret set of transformation rules is applied to equations. Below are a few examples:
# 79-12 = 67
# 27-05 = 22
# 65-21 = 44
# 65?19 = 5905
# Now, determine the result for: 06@77
# ```
# ### CoT
# 2124 tokens
# ```
# This puzzle involves equation transformation with hidden operation rules.
# Its characteristic is that simple arithmetic operations are masked by operand reordering and result formatting.
# We must determine the pattern: which operands are transformed (pre-format), which operation is applied,
# and how the result is formatted (post-format).
# Sometimes, all digits are transformed into symbols. This type of problems require identifying the symbol to digit mapping.
# However, the operator position would still be preserved if digits are transformed into symbols.
#
#
# First, we examine the given examples to understand the problem structure:
#   EX1  79 - 12 becomes 67
#   EX2  27 - 05 becomes 22
#   EX3  65 - 21 becomes 44
#   EX4  65 ? 19 becomes 5905
# Target  06 @ 77 becomes UNKNOWN
#
# Next, we analyze each operator to narrow down operation candidates.
# Analyzing operator - with examples:
#   All results are 2 digits
#   This could be addition, subtraction or modulo operations
#   Checking candidates among add add1 addm1 sub sub_rev sub_abs sub_n_abs mod
# Analyzing operator ? with examples:
#   All results are 4 digits  examples: ['5905']
#   All 4-digit results have consistent digit patterns  suggests concatenation
#   Checking candidates among cat mul mul1 mulm1
#
# Now we test format combinations to determine which transformation rules match all examples.
# Testing these 6 format combinations: BADC+swap, DCBA+swap, BADC+rev, DCBA+rev, ABCD+raw, CDAB+raw
# We examine examples with fewer operation candidates first to maximize constraints.
#
# Trying format 1 of 6  pre BADC  post swap
#   Testing examples in order of constraint (fewest candidates first)...
#   EX4 with operator ? trying 4 candidates
#     cat  65?19 via BADC becomes 56?91  computing 56 concatenate 91 = 5691  formatted via swap to 1965  final 1965 MISMATCH expected 5905
#     mul  65?19 via BADC becomes 56?91  computing 56 × 91 = 5096  formatted via swap to 6905  final 6905 MISMATCH expected 5905
#     mul1  65?19 via BADC becomes 56?91  computing 56 × 91 + 1 = 5097  formatted via swap to 7905  final 7905 MISMATCH expected 5905
#     mulm1  65?19 via BADC becomes 56?91  computing 56 × 91 - 1 = 5095  formatted via swap to 5905  final 5905 MATCH
#   Operator ? locked as mulm1
#   EX4 working operations ['mulm1']
#   EX1 with operator - trying 8 candidates
#     add  79-12 via BADC becomes 97-21  computing 97 + 21 = 118  formatted via swap to 811  final 811 MISMATCH expected 67
#     add1  79-12 via BADC becomes 97-21  computing 97 + 21 + 1 = 119  formatted via swap to 911  final 911 MISMATCH expected 67
#     addm1  79-12 via BADC becomes 97-21  computing 97 + 21 - 1 = 117  formatted via swap to 711  final 711 MISMATCH expected 67
#     mod  79-12 via BADC becomes 97-21  computing max(97, 21) mod min(97, 21) = 97 mod 21 = 13  formatted via swap to 31  final 31 MISMATCH expected 67
#     sub  79-12 via BADC becomes 97-21  computing 97 - 21 = 76  formatted via swap to 67  final 67 MATCH
#     sub_abs  79-12 via BADC becomes 97-21  computing abs(97 - 21) = 76  formatted via swap to 67  final 67 MATCH
#     sub_n_abs  79-12 via BADC becomes 97-21  computing -abs(97 - 21) = -76  formatted via swap to -67  final -67 MISMATCH expected 67
#     sub_rev  79-12 via BADC becomes 97-21  computing 21 - 97 = -76  formatted via swap to -67  final -67 MISMATCH expected 67
#   Operator - pending with 2 candidates: ['sub', 'sub_abs']
#   EX1 working operations ['sub', 'sub_abs']
#   EX2 with operator - narrowing from previous ['sub', 'sub_abs']
#     sub  27-05 via BADC becomes 72-50  computing 72 - 50 = 22  formatted via swap to 22  final 22 MATCH
#     sub_abs  27-05 via BADC becomes 72-50  computing abs(72 - 50) = 22  formatted via swap to 22  final 22 MATCH
#   Operator - narrowed from ['sub', 'sub_abs'] to ['sub', 'sub_abs']
#   EX2 working operations ['sub', 'sub_abs']
#   EX3 with operator - narrowing from previous ['sub', 'sub_abs']
#     sub  65-21 via BADC becomes 56-12  computing 56 - 12 = 44  formatted via swap to 44  final 44 MATCH
#     sub_abs  65-21 via BADC becomes 56-12  computing abs(56 - 12) = 44  formatted via swap to 44  final 44 MATCH
#   Operator - narrowed from ['sub', 'sub_abs'] to ['sub', 'sub_abs']
#   EX3 working operations ['sub', 'sub_abs']
# Format 1 of 6 found the rule
# Finalizing pending operators using frequency data:
#   -: narrowed to ['sub', 'sub_abs']
#     → Selected sub (35.1%)
# Identified operator-to-operation mappings
#   - maps to sub
#   ? maps to mulm1
#
# Rule confirmed and verified with all examples.
#
# Verification Applying the rule to all examples
#   79-12  79,12 via BADC  97,21  via sub  76  via swap  67  result 67 MATCH
#   27-05  27,05 via BADC  72,50  via sub  22  via swap  22  result 22 MATCH
#   65-21  65,21 via BADC  56,12  via sub  44  via swap  44  result 44 MATCH
#   65?19  65,19 via BADC  56,91  via mulm1  5095  via swap  5905  result 5905 MATCH
#
# Applying our rule to the target
#
# Note: Operator @ does not appear in any examples.
# We will infer its operation using statistical patterns.
# Step 1: Exclude operation families already locked to other operators
#   - SUB+MOD family (sub, sub_rev, sub_abs, sub_n_abs, mod)
#   - MUL family (mul, mul1, mulm1)
#   Total excluded operations: ['mod', 'mul', 'mul1', 'mulm1', 'sub', 'sub_abs', 'sub_n_abs', 'sub_rev']
# Step 2: Consult statistical frequency data for this operator
#   - mul: 24 cases (33.3%) EXCLUDED
#   - add: 12 cases (16.7%) available
# Step 3: Select add
#   Rationale: add appears in 12 dataset examples (16.7% of @ cases)
#   This is the most frequent operation for @ that is not excluded by other operators
#   - addm1: 8 cases (11.1%) available
#   - mod: 8 cases (11.1%) EXCLUDED
#   - mulm1: 8 cases (11.1%) EXCLUDED
#   - sub: 6 cases (8.3%) EXCLUDED
#   - add1: 4 cases (5.6%) available
#   - cat: 2 cases (2.8%) available
# 06@77  06,77 via BADC  60,77  via add  137  via swap  731  result 731
#
# </think>
# The answer is \boxed{731}
# ```
