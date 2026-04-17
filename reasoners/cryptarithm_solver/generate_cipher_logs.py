import sys
import pandas as pd
import io

WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path: sys.path.append(WORKSPACE_DIR)

from reasoners.store_types import Problem
from reasoners.cryptarithm_solver.constraint_solver import solve_cipher_unified

df = pd.read_csv('/workspaces/nemotron/train.csv')
import random
random.seed(42)

problems = [p for p in Problem.load_all() if p.category == 'cryptarithm_deduce']
problems = random.sample(problems, min(10, len(problems)))

print(f'Running {len(problems)} random examples live to the terminal...', flush=True)

for p in problems:
    row = df[df['id'] == p.id]
    ans = str(row.iloc[0]['answer'])
    print(f'\n=== PROBLEM {p.id} ===', flush=True)
    print(p.prompt, flush=True)
    print(f'Expected Answer: {ans}\n', flush=True)
    
    # solve_cipher_unified will print DEBUG SOLUTION lines directly to terminal
    pred = solve_cipher_unified(p.prompt, mode='all')
    
    if pred is not None and ans in pred:
        print(f'\n[CORRECT] {p.id}: {ans} found in predictions!', flush=True)
    else:
        print(f'\n[INCORRECT] {p.id}: Expected {ans} | All Preds: {pred}', flush=True)

print("\nGeneration complete!", flush=True)
