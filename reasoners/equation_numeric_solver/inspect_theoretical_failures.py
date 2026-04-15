import pandas as pd
import sys
import os

WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path: sys.path.append(WORKSPACE_DIR)

from reasoners.store_types import Problem
from grammar_solver import solve_with_type_safe_grammar

problems = [p for p in Problem.load_all() if p.category == 'equation_numeric_deduce']
df = pd.read_csv('/workspaces/nemotron/train.csv')

count = 0
for p_obj in problems:
    row = df[df['id'] == p_obj.id].iloc[0]
    p_text, a = row['prompt'], str(row['answer'])
    
    # Check if theoretical can solve it
    theo_ok = solve_with_type_safe_grammar(p_text, target_answer=a, mode='theoretical')
    
    if not theo_ok:
        print(f"ID: {p_obj.id}")
        print(f"Prompt:\n{p_text}")
        print(f"Target Answer: {a}")
        print("-" * 50)
        count += 1
        if count >= 3:
            break
