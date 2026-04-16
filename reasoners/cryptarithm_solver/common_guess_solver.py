import sys
import re
import pandas as pd
import tqdm
import json
from constraint import Problem, AllDifferentConstraint

WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path: sys.path.append(WORKSPACE_DIR)

from reasoners.store_types import Problem as NemotronProblem

# =============================================================================
# THE MOST COMMON PIPELINE (ABCD -> sub_abs -> raw)
# =============================================================================

def make_num(digits):
    """Calculates the integer value of a list of integer digits (e.g. [1, 2] -> 12)"""
    return sum(d * (10**(len(digits)-1-i)) for i, d in enumerate(digits))

# Pre-Op: ABCD
def eval_L(mapping, A_syms):
    return make_num([mapping[s] for s in A_syms])

def eval_R(mapping, B_syms):
    return make_num([mapping[s] for s in B_syms])

# Mid-Op: sub_abs
def eval_mid(L, R):
    return abs(L - R)

# Post-Op: raw
def check_post(expected_val, out_vals, is_negative):
    if expected_val is None: return False
    s_exp = str(expected_val)
    if is_negative and not s_exp.startswith('-'): return False
    if not is_negative and s_exp.startswith('-'): return False
    
    s_exp_abs = s_exp[1:] if is_negative else s_exp
    s_out = "".join(str(d) for d in out_vals)
    
    return s_exp_abs == s_out

# =============================================================================
# SOLVER IMPLEMENTATION
# =============================================================================

def solve_common_guess_cryptarithm(prompt: str):
    """
    Assumes the puzzle follows the most common 'equation_numeric_guess' pipeline:
    ABCD -> sub_abs -> raw.
    
    Treats the operator symbol simply as a placeholder (since we assume it means sub_abs)
    and uses python-constraint to solve the 10-digit bijective cipher.
    """
    lines = [l.strip() for l in prompt.split('\n') if '=' in l and 'determine' not in l.lower()]
    
    target_m = re.search(r'result for:\s*(\S{2})(\S)(\S{2})', prompt)
    if not target_m: 
        print("DEBUG: Target regex didn't match")
        return None, None
    
    tA_str, tgt_op_char, tB_str = target_m.groups()
    tA = list(tA_str)
    tB = list(tB_str)
    
    parsed_examples = []
    unique_symbols = set()
    
    for line in lines:
        m = re.search(r'^(\S{2})(\S)(\S{2})\s*=\s*(\S+)$', line)
        if not m: 
            print(f"DEBUG: Regex didn't match line: {line}")
            continue
        
        left_syms_A, op_char, left_syms_B, right_str = m.groups()
        
        # ONLY FOCUS ON EXAMPLES WITH THE TARGET OPERATOR
        if op_char != tgt_op_char:
            continue
        
        is_neg = False
        res_str = right_str.strip()
        if res_str.startswith('-'):
            is_neg = True
            res_str = res_str[1:]
            
        out_syms = list(res_str)
        
        parsed_examples.append({
            'A': list(left_syms_A),
            'B': list(left_syms_B),
            'out': out_syms,
            'is_neg': is_neg
        })
        
        unique_symbols.update(list(left_syms_A) + list(left_syms_B) + out_syms)
        
    unique_symbols.update(tA + tB)
    
    if len(unique_symbols) > 10:
        print(f"DEBUG: Too many unique symbols: {len(unique_symbols)}")
        return None, None
        
    sym_list = list(unique_symbols)
    
    problem = Problem()
    problem.addVariables(sym_list, range(10))
    problem.addConstraint(AllDifferentConstraint())
    
    # Leading digits cannot be 0
    for ex in parsed_examples:
        if len(ex['A']) > 1: problem.addConstraint(lambda x: x != 0, [ex['A'][0]])
        if len(ex['B']) > 1: problem.addConstraint(lambda x: x != 0, [ex['B'][0]])
        if len(ex['out']) > 1: problem.addConstraint(lambda x: x != 0, [ex['out'][0]])
        
    if len(tA) > 1: problem.addConstraint(lambda x: x != 0, [tA[0]])
    if len(tB) > 1: problem.addConstraint(lambda x: x != 0, [tB[0]])

    # Build the dynamic constraints for ABCD -> sub_abs -> raw
    for ex in parsed_examples:
        ex_syms = list(set(ex['A'] + ex['B'] + ex['out']))
        
        def make_ex_constraint(current_ex, current_syms):
            def ex_check(*args):
                mapping = dict(zip(current_syms, args))
                try:
                    L = eval_L(mapping, current_ex['A'])
                    R = eval_R(mapping, current_ex['B'])
                    expected_val = eval_mid(L, R)
                    
                    out_vals = [mapping[s] for s in current_ex['out']]
                    return check_post(expected_val, out_vals, current_ex['is_neg'])
                except Exception:
                    return False
            return ex_check
            
        problem.addConstraint(make_ex_constraint(ex, ex_syms), ex_syms)
        
    solutions = problem.getSolutions()
    
    if solutions:
        mapping = solutions[0]
        
        try:
            L = eval_L(mapping, tA)
            R = eval_R(mapping, tB)
            numeric_ans = eval_mid(L, R)
        except Exception:
            print("DEBUG: Math exception on target")
            return None, None
            
        if numeric_ans is None: 
            print("DEBUG: numeric_ans is None")
            return None, None
        
        # Encode back to symbols
        inv_map = {v: k for k, v in mapping.items()}
        encoded_ans = ""
        s_ans = str(numeric_ans)
        
        for char in s_ans:
            if char == '-':
                encoded_ans += '-'
            else:
                if int(char) not in inv_map:
                    # Missing symbol mapping required for answer
                    print(f"DEBUG: missing symbol mapping for digit {char}")
                    return None, None
                encoded_ans += inv_map[int(char)]
                
        # Add the operator prefix/suffix back if present in the examples
        # Find the original output string for the first valid example
        if parsed_examples:
            # Reconstruct original right hand string to check for prefix/suffix
            first_ex_line = [l.strip() for l in prompt.split('\n') if l.strip().startswith("".join(parsed_examples[0]['A']) + tgt_op_char + "".join(parsed_examples[0]['B']))][0]
            ex_res_0 = first_ex_line.split('=')[1].strip()
            
            if ex_res_0.startswith(tgt_op_char): encoded_ans = tgt_op_char + encoded_ans
            elif ex_res_0.endswith(tgt_op_char): encoded_ans = encoded_ans + tgt_op_char
        
        return encoded_ans, mapping

    print("DEBUG: No solutions found by constraint solver")
    return None, None

if __name__ == "__main__":
    print("Loading cryptarithm problems...")
    problems = [p for p in NemotronProblem.load_all() if p.category == 'cryptarithm_deduce']
    df = pd.read_csv('/workspaces/nemotron/train.csv')
    
    # Add category to df
    df['category'] = None
    with open('/workspaces/nemotron/problems.jsonl', 'r') as f:
        for line in f:
            p = json.loads(line)
            df.loc[df['id'] == p['id'], 'category'] = p['category']
            
    df_crypt = df[df['category'] == 'cryptarithm_deduce']
    print(f"Total cryptarithm_deduce problems: {len(df_crypt)}")
    
    correct = 0
    total = 0
    
    print(f"Testing ABCD->sub_abs->raw hypothesis on {min(10, len(df_crypt))} problems...")
    for _, row in tqdm.tqdm(df_crypt.head(10).iterrows(), total=min(10, len(df_crypt))):
        total += 1
        prompt = row['prompt']
        ans = str(row['answer'])
        
        pred, mapping = solve_common_guess_cryptarithm(prompt)
        
        if pred == ans:
            correct += 1
            print(f"\n[CORRECT] {row['id']}: Pred: {pred} == Expected: {ans}")
            print(f"  Cipher Mapping: {mapping}")
        elif pred is not None:
            print(f"\n[WRONG] {row['id']}: Pred: {pred} != Expected: {ans}")
            print(f"  Cipher Mapping: {mapping}")
        else:
            print(f"\n[NO MATCH] {row['id']}: No solution found. Expected {ans}")
            
    print(f"\nAccuracy: {correct}/{total} ({correct/total*100:.2f}%)")