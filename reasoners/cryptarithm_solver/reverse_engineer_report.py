import sys
import pandas as pd
import json
import io
import re

WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path: sys.path.append(WORKSPACE_DIR)

from reasoners.store_types import Problem
from reasoners.cryptarithm_solver.constraint_solver import solve_cipher_unified, MID_OPS, SYMBOL_UNIVERSE

def analyze_ground_truth(num_probs=20):
    df = pd.read_csv('/workspaces/nemotron/train.csv')
    problems = [p for p in Problem.load_all() if p.category == 'cryptarithm_deduce']
    
    print("# Cryptarithm Ground Truth Analysis\n", flush=True)
    print("This report lists the valid mathematical pipelines and digit ciphers that lead to the ground truth answers.\n", flush=True)
    
    for p in problems[:num_probs]:
        row = df[df['id'] == p.id]
        if row.empty: continue
        ground_truth = str(row.iloc[0]['answer'])
        
        print(f"## Problem: {p.id}", flush=True)
        print(f"**Ground Truth:** `{ground_truth}`", flush=True)
        print("**Prompt Equations:**", flush=True)
        lines = [l.strip() for l in p.prompt.split('\n') if '=' in l and 'determine' not in l.lower()]
        for l in lines:
            print(f"  - `{l}`", flush=True)
            
        target_m = re.search(r'result for:\s*(\S{2})(\S)(\S{2})', p.prompt)
        tA, tOp, tB = ("??", "?", "??")
        if target_m:
            tA, tOp, tB = target_m.groups()
            print(f"**Query Equation:** `{tA} {tOp} {tB} = ?`", flush=True)
        
        # Capture solver output to find matching pipelines
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        solve_cipher_unified(p.prompt, mode='all')
        solver_output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        
        blocks = solver_output.split("DEBUG SOLUTION: ")
        found_any = False
        
        valid_solutions = []
        all_csp_predictions = set()
        
        for block in blocks:
            if not block.strip(): continue
            
            # Find the encoded prediction for ambiguity check
            pred_match = re.search(r'Encoded: (\S+)', block)
            if pred_match:
                all_csp_predictions.add(pred_match.group(1))
            
            # Use python's rpartition or find to extract dicts safely, as regex struggles with '}' characters in the dictionary strings.
            try:
                map_str_start = block.find("map: {") + 5
                map_str_end = block.find("}", map_str_start) + 1
                map_str = block[map_str_start:map_str_end]
                
                ops_str_start = block.find("ops: {") + 5
                ops_str_end = block.find("}", ops_str_start) + 1
                ops_str = block[ops_str_start:ops_str_end]
                
                pipeline_name = block.split(", ops:")[0].strip()
                
                import ast
                op_map = ast.literal_eval(ops_str)
                digit_map = ast.literal_eval(map_str)
            except Exception:
                continue
            
            math_match = re.search(r'Target Math: .*? -> Math: (-?\d+) -> Fmt: (-?\d+)', block)
            if not math_match: continue
            
            numeric_ans = math_match.group(1)
            formatted_ans_str = math_match.group(2)
            
            match_possible = True
            temp_map = digit_map.copy()
            
            gt_to_check = ground_truth
            fmt_to_check = formatted_ans_str
            if ground_truth.startswith('-') and formatted_ans_str.startswith('-'):
                gt_to_check = ground_truth[1:]
                fmt_to_check = formatted_ans_str[1:]
            elif ground_truth.startswith('-') or formatted_ans_str.startswith('-'):
                match_possible = False
                
            if match_possible and len(gt_to_check) == len(fmt_to_check):
                for gt_char, fmt_char in zip(gt_to_check, fmt_to_check):
                    d = int(fmt_char)
                    if d in temp_map:
                        if temp_map[d] != gt_char:
                            match_possible = False
                            break
                    else:
                        temp_map[d] = gt_char
                
                if match_possible:
                    if len(set(temp_map.values())) == len(temp_map):
                        found_any = True
                        trace = []
                        eq_lines = [l.strip() for l in block.split('\n') if 'Eq ' in l]
                        for eq in eq_lines:
                            trace.append(f"    - {eq}")
                        
                        target_math_op = op_map.get(tOp, "Unknown")
                        sol_data = {
                            'pipeline': pipeline_name,
                            'cipher': temp_map,
                            'ops': op_map,
                            'trace': trace,
                            'target_math': f"{numeric_ans} (Fmt: {formatted_ans_str})",
                            'target_op': target_math_op
                        }
                        if sol_data not in valid_solutions:
                            valid_solutions.append(sol_data)

        if all_csp_predictions:
            if len(all_csp_predictions) == 1:
                print(f"\n> **[CONSISTENT]** All valid mathematical interpretations agree on the answer: `{list(all_csp_predictions)[0]}`", flush=True)
            else:
                print(f"\n> **[AMBIGUOUS]** The prompt is under-constrained. The CSP found multiple valid interpretations leading to different answers: `{', '.join(sorted(list(all_csp_predictions)))}`", flush=True)

        if valid_solutions:
            for sol in valid_solutions:
                print(f"\n### Valid Pipeline: `{sol['pipeline']}`", flush=True)
                print(f"**Math Ops:** `{sol['ops']}`", flush=True)
                print(f"**Query Operator:** `{tOp}` acts as `{sol['target_op']}`", flush=True)
                print(f"**Complete Cipher (Digit -> Symbol):**\n`{json.dumps(dict(sorted(sol['cipher'].items())))}`", flush=True)
                print(f"**Target Result:** {sol['target_math']}", flush=True)
                print("**Logic Trace:**", flush=True)
                for line in sol['trace']:
                    print(line, flush=True)
        else:
            print("\n> **[FAILED]** No valid pipelines or ciphers found matching the ground truth within the 11-operation grammar.", flush=True)
            
        print("\n" + "-"*50 + "\n", flush=True)

if __name__ == "__main__":
    analyze_ground_truth(20)
