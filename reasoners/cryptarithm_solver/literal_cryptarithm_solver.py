import re
import sys
import pandas as pd
import tqdm
import json
import ast
import operator
from constraint import Problem, AllDifferentConstraint

WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path: sys.path.append(WORKSPACE_DIR)
from reasoners.store_types import Problem as NemotronProblem

# Map string operators to actual math functions
LITERAL_OPS = {
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': lambda a, b: a // b if b != 0 else None,
    '%': lambda a, b: a % b if b != 0 else None,
    '^': operator.pow,
    '|': operator.or_,
    '&': operator.and_,
    '<<': operator.lshift,
    '>>': operator.rshift,
}

def solve_literal_cryptarithm(prompt: str):
    """
    Assumes operators are literal and not encrypted.
    Assumes no digit reordering (strictly ABCD -> result).
    Cracks the cipher by treating it as a standard cryptarithmetic puzzle (like SEND+MORE=MONEY).
    """
    lines = [l.strip() for l in prompt.split('\n') if '=' in l and 'determine' not in l.lower()]
    
    parsed_examples = []
    unique_symbols = set()
    
    # Regex to capture: Operand1, Operator, Operand2, Result
    # This assumes the operator is exactly 1 character and is literal.
    # However, operators might be multiple chars or the symbols might be anything.
    # Let's use a more robust regex looking for the structure: (symbols) (literal_op) (symbols) = (symbols)
    # The prompt usually looks like: `! * [{ = '"[`
    
    for line in lines:
        # Match groups of non-whitespace separated by equals
        left, right = line.split('=')
        left = left.strip()
        right = right.strip()
        
        # Try to find a known mathematical operator in the left side
        op_match = None
        for op in LITERAL_OPS.keys():
            if op in left:
                op_match = op
                break
                
        if not op_match:
            print(f"DEBUG: No literal operator found in '{left}'")
            return None
            
        parts = left.split(op_match)
        if len(parts) != 2:
            print(f"DEBUG: Split by '{op_match}' didn't yield 2 parts in '{left}'")
            return None
            
        A_syms = list(parts[0].strip())
        B_syms = list(parts[1].strip())
        
        # Handle negative results
        is_neg = False
        res_str = right
        if res_str.startswith('-'):
            is_neg = True
            res_str = res_str[1:]
            
        out_syms = list(res_str)
        
        parsed_examples.append({
            'A': A_syms,
            'B': B_syms,
            'op': op_match,
            'out': out_syms,
            'is_neg': is_neg
        })
        
        unique_symbols.update(A_syms)
        unique_symbols.update(B_syms)
        unique_symbols.update(out_syms)
        
    # Parse target
    target_m = re.search(r'result for:\s*(.*)', prompt)
    if not target_m: return None
    
    target_str = target_m.group(1).strip()
    tgt_op_match = None
    for op in LITERAL_OPS.keys():
        if op in target_str:
            tgt_op_match = op
            break
            
    if not tgt_op_match: return None
    
    t_parts = target_str.split(tgt_op_match)
    if len(t_parts) != 2: return None
    
    tA = list(t_parts[0].strip())
    tB = list(t_parts[1].strip())
    
    unique_symbols.update(tA)
    unique_symbols.update(tB)
    
    # We must have <= 10 unique symbols for a base-10 cipher
    if len(unique_symbols) > 10:
        return None
        
    sym_list = list(unique_symbols)
    
    problem = Problem()
    problem.addVariables(sym_list, range(10))
    problem.addConstraint(AllDifferentConstraint())
    
    # Leading digits cannot be 0 (unless the number is exactly "0", which is 1 char)
    for ex in parsed_examples:
        if len(ex['A']) > 1: problem.addConstraint(lambda x: x != 0, [ex['A'][0]])
        if len(ex['B']) > 1: problem.addConstraint(lambda x: x != 0, [ex['B'][0]])
        if len(ex['out']) > 1: problem.addConstraint(lambda x: x != 0, [ex['out'][0]])
        
    if len(tA) > 1: problem.addConstraint(lambda x: x != 0, [tA[0]])
    if len(tB) > 1: problem.addConstraint(lambda x: x != 0, [tB[0]])

    def make_num(digits):
        return sum(d * (10**(len(digits)-1-i)) for i, d in enumerate(digits))

    # Fast validation constraints per example
    for ex in parsed_examples:
        ex_syms = list(set(ex['A'] + ex['B'] + ex['out']))
        op_func = LITERAL_OPS[ex['op']]
        
        def make_ex_constraint(current_ex, current_syms, current_op_func):
            def ex_check(*args):
                mapping = dict(zip(current_syms, args))
                
                A_vals = [mapping[s] for s in current_ex['A']]
                B_vals = [mapping[s] for s in current_ex['B']]
                out_vals = [mapping[s] for s in current_ex['out']]
                
                L = make_num(A_vals)
                R = make_num(B_vals)
                expected_out = make_num(out_vals)
                if current_ex['is_neg']:
                    expected_out = -expected_out
                    
                try:
                    res = current_op_func(L, R)
                    if res is None or res != expected_out:
                        return False
                except Exception:
                    return False
                return True
            return ex_check
            
        problem.addConstraint(make_ex_constraint(ex, ex_syms, op_func), ex_syms)
        
    solutions = problem.getSolutions()
    
    if solutions:
        mapping = solutions[0]
        
        tA_vals = [mapping[s] for s in tA]
        tB_vals = [mapping[s] for s in tB]
        
        L = make_num(tA_vals)
        R = make_num(tB_vals)
        op_func = LITERAL_OPS[tgt_op_match]
        
        try:
            numeric_ans = op_func(L, R)
        except Exception:
            return None
            
        if numeric_ans is None: return None
        
        # Encode back to symbols
        inv_map = {v: k for k, v in mapping.items()}
        encoded_ans = ""
        s_ans = str(numeric_ans)
        
        for char in s_ans:
            if char == '-':
                encoded_ans += '-'
            else:
                if int(char) not in inv_map:
                    # If we need a digit that wasn't in our mapping, we can't encode it.
                    return None
                encoded_ans += inv_map[int(char)]
                
        return encoded_ans

    return None

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
    
    correct = 0
    total = 0
    
    print(f"Testing literal operator hypothesis on {min(50, len(df_crypt))} problems...")
    for _, row in tqdm.tqdm(df_crypt.head(50).iterrows(), total=min(50, len(df_crypt))):
        total += 1
        prompt = row['prompt']
        ans = str(row['answer'])
        
        pred = solve_literal_cryptarithm(prompt)
        
        if pred == ans:
            correct += 1
            print(f"\n[CORRECT] {row['id']}: {pred} == {ans}")
        elif pred is not None:
            print(f"\n[WRONG] {row['id']}: Got {pred}, Expected {ans}")
            
    print(f"\nAccuracy: {correct}/{total} ({correct/total*100:.2f}%)")
