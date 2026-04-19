import sys
import pandas as pd
import json
import io
import re
import ast

WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path: sys.path.append(WORKSPACE_DIR)

from reasoners.store_types import Problem
from reasoners.cryptarithm_solver.constraint_solver import solve_cipher_unified, MATH_OPS, SYMBOL_UNIVERSE

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
        
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            solve_cipher_unified(p.prompt, mode='all', target_answer=ground_truth)
        except Exception as e:
            pass # Just proceed to check stdout
        solver_output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        
        blocks = solver_output.split("DEBUG SOLUTION: ")
        
        valid_solutions = []
        all_csp_predictions = set()
        
        for block in blocks[1:]:
            lines = block.split('\n')
            pipeline_name = lines[0].strip()
            
            op_map = {}
            digit_map = {}
            numeric_ans = ""
            formatted_ans_str = ""
            encoded_ans = ""
            
            for line in lines:
                if line.startswith("Ops Map:"):
                    try:
                        op_map = ast.literal_eval(line.replace("Ops Map:", "").strip())
                    except Exception:
                        pass
                elif line.startswith("Digit Map:"):
                    try:
                        digit_map = ast.literal_eval(line.replace("Digit Map:", "").strip())
                    except Exception:
                        pass
                elif "Math Evaluated:" in line:
                    m = re.search(r'Math Res: (-?\d+) -> Formatted: (-?\d+) -> Encoded: (\S+)', line)
                    if m:
                        numeric_ans = m.group(1)
                        formatted_ans_str = m.group(2)
                        encoded_ans = m.group(3)
                        all_csp_predictions.add(encoded_ans)
            
            if not formatted_ans_str: continue
            
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
                prompt_syms = set(p.prompt)
                for gt_char, fmt_char in zip(gt_to_check, fmt_to_check):
                    d = int(fmt_char)
                    if d in temp_map:
                        if temp_map[d] != gt_char:
                            if temp_map[d] not in prompt_syms:
                                # This was a solver fallback guess; override with ground truth
                                temp_map[d] = gt_char
                            else:
                                match_possible = False
                                break
                    else:
                        temp_map[d] = gt_char
                
                if match_possible:
                    if len(set(temp_map.values())) == len(temp_map):
                        trace = []
                        for line in lines:
                            if line.strip().startswith("Eq "):
                                trace.append(f"    - {line.strip()}")
                            elif line.strip().startswith("Decrypted:") or line.strip().startswith("Math:"):
                                trace.append(f"      {line.strip()}")
                        
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
