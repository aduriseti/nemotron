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
# # Benchmark Equation Numeric Solvers
# This notebook benchmarks several solvers on the `equation_numeric` problem type:
# 1. **Baseline**: Scaffolded generator provided with the answer.
# 2. **Donald**: Legacy backtracking solver.
# 3. **New Reasoner**: Modern deterministic CoT reasoner in current workspace.
# 4. **Perfect Pipeline (Greedy)**: Pure-python implementation of the 84% EDA pipeline rules.
# 5. **Theoretical Upper Bound**: Checks if *any* matching pipeline produces the correct answer (Simulates perfect disambiguation).

# %%
import os
import sys
import pandas as pd
import tqdm
import json
import re
from pathlib import Path
from types import ModuleType

# Mock src.utils for donald_solvers
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

# Fix paths
WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path: sys.path.append(WORKSPACE_DIR)
PRIOR_WORK_DIR = os.path.join(WORKSPACE_DIR, 'prior-work', 'nemotron-kaggle-synthetic-cot')
if PRIOR_WORK_DIR not in sys.path: sys.path.append(PRIOR_WORK_DIR)

from src.synthetic_cot.baseline_generators import SOLVER_MAP as BASELINE_MAP
from src.synthetic_cot.donald_solvers import DONALD_SOLVER_MAP
from reasoners.store_types import Problem
from reasoners.equation_numeric import reasoning_equation_numeric

def extract_boxed_answer(text):
    if not text: return None
    matches = re.findall(r"\\boxed\{([^}]*)\}", text)
    return matches[-1].strip() if matches else None

# %% [markdown]
# ## The Pipeline Hypothesis Solver
# Extracted from the Methodology section of the 84% solve-rate EDA notebook.

# %%
def solve_equation_pipeline(prompt, target_answer=None, mode='greedy'):
    """
    Implements the 3-stage Pre-Op/Mid-Op/Post-Op pipeline hypothesis.
    - greedy: returns first matching pipeline result.
    - theoretical: returns True if ANY matching pipeline result equals target_answer.
    """
    # 1. Extraction
    lines = [l.strip() for l in prompt.split('\n') if '=' in l and 'determine' not in l.lower()]
    examples = []
    for line in lines:
        m = re.search(r'(\d{2})([^\d\s])(\d{2})\s*=\s*(-?\d+[^\d\s]*|[^\d\s]*-?\d+)', line)
        if m: examples.append(m.groups())
            
    target_m = re.search(r'result for:\s*(\d{2})([^\d\s])(\d{2})', prompt)
    if not target_m: return None if mode == 'greedy' else False
    t_A_B, tgt_op, t_C_D = target_m.groups()
    
    # 6 Known valid format combinations based on the EDA
    FORMATS = [
        ('BADC', 'swap'), ('DCBA', 'swap'),
        ('BADC', 'rev'), ('DCBA', 'rev'),
        ('ABCD', 'raw'), ('CDAB', 'raw')
    ]
    
    # All ops mentioned in EDA
    OPS = [
        'add', 'sub', 'mul', 'cat', 'mod',
        'add1', 'addm1', 'mul1', 'mulm1', 
        'sub_abs', 'sub_rev', 'sub_neg_abs'
    ]

    def get_L_R(pairing, A, B, C, D):
        if pairing == 'ABCD': return int(A+B), int(C+D)
        if pairing == 'BADC': return int(B+A), int(D+C)
        if pairing == 'CDAB': return int(C+D), int(A+B)
        if pairing == 'DCBA': return int(D+C), int(B+A)
        return None, None

    def do_op(op, L, R):
        if op == 'add': return L + R
        if op == 'sub': return L - R
        if op == 'mul': return L * R
        if op == 'cat': return int(str(L) + str(R))
        if op == 'add1': return L + R + 1
        if op == 'addm1': return L + R - 1
        if op == 'mul1': return L * R + 1
        if op == 'mulm1': return L * R - 1
        if op == 'sub_abs': return abs(L - R)
        if op == 'sub_rev': return R - L
        if op == 'sub_neg_abs': return -abs(L - R)
        if op == 'mod':
            mi, ma = min(L, R), max(L, R)
            if mi == 0: return ma
            return ma % mi
        return None

    def apply_fmt(fmt, val):
        if val is None: return None
        s = str(val)
        if fmt == 'raw': return s
        if fmt == 'rev': return s[::-1]
        if fmt == 'swap':
            if s.startswith('-'): return '-' + s[1:][::-1]
            return s[::-1]
        return None

    op_examples = [ex for ex in examples if ex[1] == tgt_op]
    
    if op_examples:
        possible_answers = set()
        for p, f in FORMATS:
            for o in OPS:
                match_all = True
                for exA_B, ex_op, exC_D, ex_res in op_examples:
                    L, R = get_L_R(p, exA_B[0], exA_B[1], exC_D[0], exC_D[1])
                    val = do_op(o, L, R)
                    res = apply_fmt(f, val)
                    # Handle symbol prefix/suffixes
                    ex_clean = ex_res.replace(ex_op, '')
                    if res != ex_clean:
                        match_all = False; break
                if match_all:
                    L, R = get_L_R(p, t_A_B[0], t_A_B[1], t_C_D[0], t_C_D[1])
                    ans = apply_fmt(f, do_op(o, L, R))
                    # Restore symbols
                    if op_examples[0][3].startswith(tgt_op): ans = tgt_op + str(ans)
                    elif op_examples[0][3].endswith(tgt_op): ans = str(ans) + tgt_op
                    
                    if mode == 'greedy': return ans
                    possible_answers.add(ans)
        
        if mode == 'theoretical':
            return str(target_answer) in possible_answers

    # Guessing fallback for unseen operators
    if not op_examples:
        L, R = get_L_R('ABCD', t_A_B[0], t_A_B[1], t_C_D[0], t_C_D[1])
        ans = apply_fmt('raw', do_op('sub_abs', L, R))
        if mode == 'greedy': return ans
        return str(ans) == str(target_answer)
        
    return None if mode == 'greedy' else False

sys.path.insert(0, str(Path(WORKSPACE_DIR) / 'reasoners' / 'equation_numeric_solver'))
from grammar_solver import solve_with_type_safe_grammar

# %% [markdown]
# ## Load Problems and Run Benchmark

# %%
print("Loading equation problems...")
problems = [p for p in Problem.load_all() if p.category.startswith('equation_numeric')]
df = pd.read_csv('/workspaces/nemotron/train.csv')
p_dict = {p.id: p for p in problems}

results = []
for p_obj in tqdm.tqdm(problems):
    p_id = p_obj.id
    row = df[df['id'] == p_id].iloc[0]
    p_text, a = row['prompt'], str(row['answer'])
    
    # 1. Baseline
    b_pred, b_cot = BASELINE_MAP['Equation Transformation (Numeric) Gold'](p_text, a) if 'Equation Transformation (Numeric) Gold' in BASELINE_MAP else (None, None)
    if b_pred is None: # Fallback to standard
        b_pred, b_cot = BASELINE_MAP['Equation Transformation (Numeric)'](p_text, a)
    b_ok = (str(b_pred) == a or extract_boxed_answer(b_cot) == a)
    
    # 2. Donald
    d_pred, d_cot = DONALD_SOLVER_MAP['Equation Transformation (Numeric)'](p_text)
    d_ok = (str(d_pred) == a or extract_boxed_answer(d_cot) == a)
    
    # 3. New Reasoner
    n_cot = reasoning_equation_numeric(p_obj)
    n_ok = (extract_boxed_answer(n_cot) == a)
    
    # 4. Perfect Pipeline (Greedy)
    p_pred = solve_equation_pipeline(p_text, mode='greedy')
    p_ok = (str(p_pred) == a)

    # 5. Theoretical Upper Bound (Perfect Pipeline)
    t_ok = solve_equation_pipeline(p_text, target_answer=a, mode='theoretical')
    
    # 6. Type-Safe Grammar Solver (Greedy)
    ts_pred = solve_with_type_safe_grammar(p_text, mode='greedy')
    ts_ok = (str(ts_pred) == a)
    
    # 7. Type-Safe Grammar Solver (Theoretical)
    tst_ok = solve_with_type_safe_grammar(p_text, target_answer=a, mode='theoretical')

    results.append({
        'id': p_id, 
        'category': p_obj.category,
        'baseline': b_ok, 
        'donald': d_ok, 
        'new_reasoner': n_ok, 
        'perfect_pipeline': p_ok,
        'typesafe_greedy': ts_ok,
        'theoretical_pipeline': t_ok,
        'typesafe_theoretical': tst_ok
    })

res_df = pd.DataFrame(results)

# %% [markdown]
# ## Results Summary

# %%
print("\nAccuracy Breakdown (%):")
print(res_df[['baseline', 'donald', 'new_reasoner', 'perfect_pipeline', 'typesafe_greedy', 'theoretical_pipeline', 'typesafe_theoretical']].mean() * 100)

# %% [markdown]
# ## Breakdown by Metadata Category

# %%
print("\nCategory Breakdown (Accuracy %):")
cat_stats = res_df.groupby('category')[['new_reasoner', 'perfect_pipeline', 'typesafe_greedy', 'theoretical_pipeline', 'typesafe_theoretical']].mean() * 100
print(cat_stats)
# %%
