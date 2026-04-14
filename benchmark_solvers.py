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
# # Benchmark Solvers
# Benchmarking:
# 1) baseline, true, donald from `prior-work/nemotron-kaggle-synthetic-cot/src/synthetic_cot`
# 2) reasoners from `/workspaces/nemotron/reasoners`
#
# **Note**: All statistics are broken down by metadata-derived categories from `problems.jsonl`.

# %%
import os
import sys
import pandas as pd
import tqdm
import json
import re
from pathlib import Path
from types import ModuleType

# Mock src.utils before importing solvers that depend on it
# This is needed because donald_solvers.py imports from src.utils which is missing
if "src.utils" not in sys.modules:
    utils_mod = ModuleType("src.utils")
    class NvidiaTaskType:
        UNIT_CONV = "UNIT_CONV"
        GRAVITY = "GRAVITY"
        NUMERAL = "NUMERAL"
        CIPHER = "CIPHER"
        SYMBOL = "SYMBOL"
        BIT_OPS = "BIT_OPS"
    utils_mod.NvidiaTaskType = NvidiaTaskType
    sys.modules["src.utils"] = utils_mod

# Fix paths to allow imports
WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path:
    sys.path.append(WORKSPACE_DIR)

PRIOR_WORK_DIR = os.path.join(WORKSPACE_DIR, 'prior-work', 'nemotron-kaggle-synthetic-cot')
if PRIOR_WORK_DIR not in sys.path:
    sys.path.append(PRIOR_WORK_DIR)

from src.synthetic_cot.baseline_generators import SOLVER_MAP as BASELINE_MAP
from src.synthetic_cot.true_solvers import TRUE_SOLVER_MAP
from src.synthetic_cot.donald_solvers import DONALD_SOLVER_MAP

from reasoners.store_types import Problem
from reasoners.numeral import reasoning_numeral
from reasoners.bit_manipulation import reasoning_bit_manipulation
from reasoners.equation_numeric import reasoning_equation_numeric
from reasoners.cipher import reasoning_cipher
from reasoners.gravity import reasoning_gravity
from reasoners.unit_conversion import reasoning_unit_conversion
from reasoners.cryptarithm import reasoning_cryptarithm

from train_common import Category

# Map metadata categories to legacy solver keys using the Category enum values
LEGACY_CAT_MAP = {
    "bit_manipulation": "Bit Manipulation",
    "cipher": "Text Encryption",
    "equation_numeric_deduce": "Equation Transformation (Numeric)",
    "equation_numeric_guess": "Equation Transformation (Numeric)",
    "cryptarithm_deduce": "Equation Transformation (Symbolic)",
    "cryptarithm_guess": "Equation Transformation (Symbolic)",
    "gravity": "Gravity",
    "numeral": "Base Conversion",
    "unit_conversion": "Unit Conversion",
}

NEW_REASONER_MAP = {
    "numeral": reasoning_numeral,
    "bit_manipulation": reasoning_bit_manipulation,
    "equation_numeric_deduce": reasoning_equation_numeric,
    "equation_numeric_guess": reasoning_equation_numeric,
    "cipher": reasoning_cipher,
    "gravity": reasoning_gravity,
    "unit_conversion": reasoning_unit_conversion,
    "cryptarithm_deduce": reasoning_cryptarithm,
    "cryptarithm_guess": reasoning_cryptarithm,
}

def is_correct(pred, truth):
    if pred is None:
        return False
    pred_s = str(pred).strip()
    truth_s = str(truth).strip()
    if pred_s == truth_s:
        return True
    try:
        # Fuzzy match for numbers
        return abs(float(pred_s) - float(truth_s)) <= 1e-2
    except (ValueError, TypeError):
        return pred_s.lower() == truth_s.lower()

def extract_boxed_answer(text):
    if not text:
        return None
    matches = re.findall(r"\\boxed\{([^}]*)\}", text)
    if matches:
        return matches[-1].strip()
    return None

# %%
# Load Problems
print("Loading problems from reasoners jsonl...")
problems = Problem.load_all()
problem_dict = {p.id: p for p in problems}
print(f"Loaded {len(problems)} problems from jsonl.")

# Load corpus info to identify 'included' problems
print("Loading corpus index...")
corpus_included = set()
with open('/workspaces/nemotron/corpus.jsonl') as f:
    for line in f:
        e = json.loads(line)
        if e.get('included'):
            corpus_included.add(e['problem_id'])
print(f"Loaded {len(corpus_included)} included problem IDs from corpus.")

# Load CSV
df = pd.read_csv('/workspaces/nemotron/train.csv')
print(f"Loaded {len(df)} rows from train.csv")

# Only evaluate those present in `problem_dict`
df_subset = df[df['id'].isin(problem_dict.keys())].copy()

# Optional: limit sample size
df_subset = df_subset.sample(min(500, len(df_subset)), random_state=42)
print(f"Benchmarking on {len(df_subset)} sampled problems.")

# %%
# Run Benchmark
results = []
FAILURES_DIR = Path('/workspaces/nemotron/benchmark_failures')

# Clean or create failures directory
if FAILURES_DIR.exists():
    import shutil
    shutil.rmtree(FAILURES_DIR)
FAILURES_DIR.mkdir(parents=True)

for _, row in tqdm.tqdm(df_subset.iterrows(), total=len(df_subset)):
    p_id = row['id']
    p_text = row['prompt']
    a = str(row['answer'])
    
    problem_obj = problem_dict[p_id]
    cat_metadata = problem_obj.category
    cat_legacy = LEGACY_CAT_MAP.get(cat_metadata, "Unknown")
    
    # Run Legacy Solvers
    b_pred, b_cot, t_pred, t_cot, d_pred, d_cot = None, None, None, None, None, None
    b_solved, t_solved, d_solved = False, False, False
    
    if cat_legacy in BASELINE_MAP:
        try:
            b_pred, b_cot = BASELINE_MAP[cat_legacy](p_text, a)
            if is_correct(b_pred, a) or is_correct(extract_boxed_answer(b_cot), a):
                b_solved = True
        except Exception: pass
            
    if cat_legacy in TRUE_SOLVER_MAP:
        try:
            t_pred, t_cot = TRUE_SOLVER_MAP[cat_legacy](p_text)
            if is_correct(t_pred, a) or is_correct(extract_boxed_answer(t_cot), a):
                t_solved = True
        except Exception: pass
            
    if cat_legacy in DONALD_SOLVER_MAP:
        try:
            d_pred, d_cot = DONALD_SOLVER_MAP[cat_legacy](p_text)
            if is_correct(d_pred, a) or is_correct(extract_boxed_answer(d_cot), a):
                d_solved = True
        except Exception: pass

    # Run New Reasoner
    n_solved = False
    n_cot = None
    n_pred = None
    if cat_metadata in NEW_REASONER_MAP:
        try:
            n_cot = NEW_REASONER_MAP[cat_metadata](problem_obj)
            n_pred = extract_boxed_answer(n_cot)
            if is_correct(n_pred, a):
                n_solved = True
        except Exception: pass

    # Record Results
    results.append({
        'id': p_id,
        'category': cat_metadata,
        'included_in_corpus': p_id in corpus_included,
        'baseline_solved': b_solved,
        'true_solved': t_solved,
        'donald_solved': d_solved,
        'new_reasoner_solved': n_solved
    })

    # Save failing examples broken down by solver and category
    solvers_info = [
        ("baseline", b_solved, b_pred, b_cot),
        ("true", t_solved, t_pred, t_cot),
        ("donald", d_solved, d_pred, d_cot),
        ("new_reasoner", n_solved, n_pred, n_cot)
    ]

    for s_name, s_solved, s_pred, s_cot in solvers_info:
        if s_pred is None and s_cot is None:
            continue # Solver was not applicable or failed to run
            
        if not s_solved:
            s_cat_dir = FAILURES_DIR / s_name / cat_metadata
            s_cat_dir.mkdir(parents=True, exist_ok=True)
            failure_data = {
                "id": p_id,
                "category": cat_metadata,
                "prompt": p_text,
                "golden_answer": a,
                "predicted_answer": s_pred or extract_boxed_answer(s_cot),
                "cot": s_cot
            }
            with open(s_cat_dir / f"{p_id}.json", "w") as f:
                json.dump(failure_data, f, indent=2)

results_df = pd.DataFrame(results)

# %% [markdown]
# # Statistics by Category
# Results aggregated by metadata categories from `problems.jsonl`.

# %%
stats = results_df.groupby('category').agg(
    total=('id', 'count'),
    included_in_corpus=('included_in_corpus', 'sum'),
    baseline_solved=('baseline_solved', 'sum'),
    true_solved=('true_solved', 'sum'),
    donald_solved=('donald_solved', 'sum'),
    new_reasoner_solved=('new_reasoner_solved', 'sum')
)
stats['baseline_acc'] = (stats['baseline_solved'] / stats['total'] * 100).round(2)
stats['true_acc'] = (stats['true_solved'] / stats['total'] * 100).round(2)
stats['donald_acc'] = (stats['donald_solved'] / stats['total'] * 100).round(2)
stats['new_reasoner_acc'] = (stats['new_reasoner_solved'] / stats['total'] * 100).round(2)

print("Benchmark Results by Category:")
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
print(stats[['total', 'included_in_corpus', 'baseline_acc', 'true_acc', 'donald_acc', 'new_reasoner_acc']])

# %% [markdown]
# # Performance on Included vs Excluded Problems

# %%
inc_stats = results_df.groupby(['category', 'included_in_corpus']).agg(
    total=('id', 'count'),
    new_reasoner_solved=('new_reasoner_solved', 'sum')
)
inc_stats['new_reasoner_acc'] = (inc_stats['new_reasoner_solved'] / inc_stats['total'] * 100).round(2)
print("\nNew Reasoner Performance (Included vs Excluded):")
print(inc_stats[['total', 'new_reasoner_acc']])
# %%
