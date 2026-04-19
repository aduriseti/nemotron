import sys
import pandas as pd
import json
import io
import re
import ast
import time

WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path: sys.path.append(WORKSPACE_DIR)

from reasoners.store_types import Problem
from reasoners.cryptarithm_solver.z3_solver import solve_cipher_unified, MATH_OPS, SYMBOL_UNIVERSE

def analyze_z3(num_probs=10):
    df = pd.read_csv('/workspaces/nemotron/train.csv')
    problems = [p for p in Problem.load_all() if p.category == 'cryptarithm_deduce']
    
    print("# Z3 Cryptarithm Solver Test\n", flush=True)
    
    for p in problems[:num_probs]:
        row = df[df['id'] == p.id]
        if row.empty: continue
        ground_truth = str(row.iloc[0]['answer'])
        
        print(f"## Problem: {p.id}", flush=True)
        print(f"**Ground Truth:** `{ground_truth}`", flush=True)
        
        target_m = re.search(r'result for:\s*(\S{2})(\S)(\S{2})', p.prompt)
        tA, tOp, tB = ("??", "?", "??")
        if target_m:
            tA, tOp, tB = target_m.groups()
            print(f"**Query Equation:** `{tA} {tOp} {tB} = ?`", flush=True)
        
        start_time = time.time()
        
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            # We call solve_cipher_unified directly.
            # In z3_solver.py, it returns possible_answers dict if mode='all'
            ans = solve_cipher_unified(p.prompt, mode='all', target_answer=ground_truth)
        except Exception as e:
            ans = {}
            print(f"Error: {e}")
        solver_output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        
        elapsed = time.time() - start_time
        
        # ans is a dict of possible answers and their frequencies (or equivalent)
        # However, z3_solver.py currently returns possible_answers (dict of answer -> count)
        
        print(f"**Time Taken:** {elapsed:.2f}s", flush=True)
        
        if not ans:
            print("> **[FAILED]** No solutions found or returned None.\n")
            continue
            
        num_solutions = sum(ans.values()) if isinstance(ans, dict) else len(ans)
        unique_answers = list(ans.keys()) if isinstance(ans, dict) else list(ans)
        
        print(f"**Total CSP Models Found:** {num_solutions}", flush=True)
        print(f"**Unique Target Answers Found:** {len(unique_answers)}", flush=True)
        
        has_target = ground_truth in unique_answers
        
        if len(unique_answers) == 1:
            ans_str = unique_answers[0]
            if ans_str == ground_truth:
                print(f"> **[SUCCESS]** Found exactly ONE unambiguous answer, and it MATCHES the target: `{ans_str}`")
            else:
                print(f"> **[CONSISTENT BUT WRONG]** Found unambiguous answer `{ans_str}`, but target is `{ground_truth}`")
        else:
            if has_target:
                print(f"> **[AMBIGUOUS - CONTAINS TARGET]** Target `{ground_truth}` is among the {len(unique_answers)} possible answers: {unique_answers}")
            else:
                print(f"> **[AMBIGUOUS - MISSING TARGET]** Target `{ground_truth}` is NOT in the possible answers: {unique_answers}")
        
        print("\n" + "-"*50 + "\n", flush=True)

if __name__ == "__main__":
    analyze_z3(1)
