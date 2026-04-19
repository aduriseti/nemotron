# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Benchmark Cryptarithm Solvers
# This notebook benchmarks both solvers on all `cryptarithm_deduce` and `cryptarithm_guess` problems:
# 1. **OR-Tools solver**: CP-SAT based solver via `ortools_solver.solve_cipher_unified`
# 2. **Python solver**: Pure-Python example-driven backtracking (drop-in replacement)
#
# For each solver we report:
# - **Greedy accuracy**: does the top-voted answer match the golden answer?
# - **Theoretical accuracy**: is the golden answer anywhere in the candidate set?

# %%
import sys
import time
import pandas as pd
import tqdm

WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path:
    sys.path.append(WORKSPACE_DIR)

from reasoners.store_types import Problem
from reasoners.cryptarithm_solver.ortools_solver import solve_cipher_unified as ort_solve
from reasoners.cryptarithm_solver.python_solver import solve_cipher_unified as py_solve

# %% [markdown]
# ## Load Problems

# %%
all_problems = [p for p in Problem.load_all() if 'cryptarithm' in p.category]
print(f"Total cryptarithm problems: {len(all_problems)}")
from collections import Counter
for cat, n in sorted(Counter(p.category for p in all_problems).items()):
    print(f"  {cat}: {n}")

# %% [markdown]
# ## Run Solvers

# %%
results = []
for p in tqdm.tqdm(all_problems, desc='Benchmarking'):
    golden = str(p.answer)

    t0 = time.time()
    ort_votes = ort_solve(p.prompt, mode=None, target_answer=p.answer) or {}
    ort_t = time.time() - t0
    ort_ans = max(ort_votes, key=ort_votes.get) if ort_votes else None

    t0 = time.time()
    py_votes = py_solve(p.prompt, mode=None, target_answer=p.answer) or {}
    py_t = time.time() - t0
    py_ans = max(py_votes, key=py_votes.get) if py_votes else None

    results.append({
        'id': p.id,
        'category': p.category,
        'golden': golden,
        'ort_greedy': str(ort_ans) == golden,
        'ort_theoretical': golden in ort_votes,
        'ort_none': ort_ans is None,
        'ort_t': ort_t,
        'py_greedy': str(py_ans) == golden,
        'py_theoretical': golden in py_votes,
        'py_none': py_ans is None,
        'py_t': py_t,
    })

df = pd.DataFrame(results)

# %% [markdown]
# ## Overall Results

# %%
n = len(df)
print(f"{'Metric':<35} {'OR-Tools':>10} {'Python':>10}")
print('-' * 57)
print(f"{'Greedy accuracy':<35} {df['ort_greedy'].mean()*100:>9.1f}% {df['py_greedy'].mean()*100:>9.1f}%")
print(f"{'Theoretical accuracy':<35} {df['ort_theoretical'].mean()*100:>9.1f}% {df['py_theoretical'].mean()*100:>9.1f}%")
print(f"{'Returned None':<35} {df['ort_none'].mean()*100:>9.1f}% {df['py_none'].mean()*100:>9.1f}%")
print(f"{'Avg time (s)':<35} {df['ort_t'].mean():>10.3f} {df['py_t'].mean():>10.3f}")
print(f"{'Total time (s)':<35} {df['ort_t'].sum():>10.1f} {df['py_t'].sum():>10.1f}")
print(f"{'n':<35} {n:>10}")

# %% [markdown]
# ## Breakdown by Category

# %%
print("\nAccuracy by category:")
cat_df = df.groupby('category').agg(
    n=('id', 'count'),
    ort_greedy=('ort_greedy', 'mean'),
    ort_theoretical=('ort_theoretical', 'mean'),
    py_greedy=('py_greedy', 'mean'),
    py_theoretical=('py_theoretical', 'mean'),
    ort_avg_t=('ort_t', 'mean'),
    py_avg_t=('py_t', 'mean'),
).reset_index()

for _, row in cat_df.iterrows():
    print(f"\n  {row['category']}  (n={row['n']})")
    print(f"    {'':20} {'OR-Tools':>10} {'Python':>10}")
    print(f"    {'Greedy accuracy':20} {row['ort_greedy']*100:>9.1f}% {row['py_greedy']*100:>9.1f}%")
    print(f"    {'Theoretical':20} {row['ort_theoretical']*100:>9.1f}% {row['py_theoretical']*100:>9.1f}%")
    print(f"    {'Avg time (s)':20} {row['ort_avg_t']:>10.3f} {row['py_avg_t']:>10.3f}")

# %% [markdown]
# ## Agreement Analysis

# %%
agree = (df['ort_greedy'] == df['py_greedy']).mean()
both_correct = (df['ort_greedy'] & df['py_greedy']).mean()
ort_only = (df['ort_greedy'] & ~df['py_greedy']).mean()
py_only = (~df['ort_greedy'] & df['py_greedy']).mean()
both_wrong = (~df['ort_greedy'] & ~df['py_greedy']).mean()

print(f"\nAgreement analysis (n={n}):")
print(f"  Both correct:      {both_correct*100:.1f}%  ({int(both_correct*n)})")
print(f"  OR-Tools only:     {ort_only*100:.1f}%  ({int(ort_only*n)})")
print(f"  Python only:       {py_only*100:.1f}%  ({int(py_only*n)})")
print(f"  Both wrong:        {both_wrong*100:.1f}%  ({int(both_wrong*n)})")
print(f"  Agreement rate:    {agree*100:.1f}%")

# %% [markdown]
# ## Save Results

# %%
out_path = '/workspaces/nemotron/reasoners/cryptarithm_solver/benchmark_results.csv'
df.to_csv(out_path, index=False)
print(f"Results saved to {out_path}")
# %%
