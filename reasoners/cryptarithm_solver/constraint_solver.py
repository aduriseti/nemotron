import sys
import pandas as pd
import tqdm
import json
import re
import signal
from typing import Any
from constraint import Problem, AllDifferentConstraint

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException()

signal.signal(signal.SIGALRM, timeout_handler)

WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path: sys.path.append(WORKSPACE_DIR)

from reasoners.store_types import Problem as NemotronProblem

# =============================================================================
# GRAMMAR AND ALGEBRAIC GENERATORS
# =============================================================================

def make_num(digits):
    """Calculates the integer value of a list of integer digits (e.g. [1, 2] -> 12)"""
    return sum(d * (10**(len(digits)-1-i)) for i, d in enumerate(digits))

# Pre-Ops: Return a tuple of lambdas that evaluate the Left and Right operands
# They now take an ordered list of integer digits corresponding to the symbols in A and B
PRE_OPS = {
    'ABCD': lambda A_vals, B_vals: (make_num(A_vals), make_num(B_vals)),
    'BADC': lambda A_vals, B_vals: (make_num(A_vals[::-1]), make_num(B_vals[::-1])),
    'CDAB': lambda A_vals, B_vals: (make_num(B_vals), make_num(A_vals)),
    'DCBA': lambda A_vals, B_vals: (make_num(B_vals[::-1]), make_num(A_vals[::-1]))
}

# Mid-Ops: Standard mathematical operations
MID_OPS = {
    'add': lambda L, R: L + R,
    'sub': lambda L, R: L - R,
    'mul': lambda L, R: L * R,
    'add1': lambda L, R: L + R + 1,
    'addm1': lambda L, R: L + R - 1,
    'mul1': lambda L, R: L * R + 1,
    'mulm1': lambda L, R: L * R - 1,
    'sub_abs': lambda L, R: abs(L - R),
    'sub_rev': lambda L, R: R - L,
    'sub_neg_abs': lambda L, R: -abs(L - R),
    'cat': lambda L, R: int(str(L) + str(R)),
    'mod': lambda L, R: max(L, R) % min(L, R) if min(L, R) != 0 else max(L, R)
}

# Post-Ops: Check if the mathematical result matches the expected output digits
def check_post(expected_val, out_vals, f_type, is_negative):
    if expected_val is None: return False
    s_exp = str(expected_val)
    if is_negative and not s_exp.startswith('-'): return False
    if not is_negative and s_exp.startswith('-'): return False
    
    s_exp_abs = s_exp[1:] if is_negative else s_exp
    s_out = "".join(str(d) for d in out_vals)
    
    if f_type == 'raw':
        return s_exp_abs == s_out
    elif f_type == 'rev':
        actual_str = "-" + s_out if is_negative else s_out
        return s_exp[::-1] == actual_str
    elif f_type == 'swap':
        return s_exp_abs[::-1] == s_out
        
    return False

# The 6 global formatting combinations from the EDA
PIPELINES = [
    ('BADC', 'swap'), ('DCBA', 'swap'),
    ('BADC', 'rev'), ('DCBA', 'rev'),
    ('ABCD', 'raw'), ('CDAB', 'raw')
]

# Sort formatting pipelines by empirical frequency
try:
    with open('/workspaces/nemotron/reasoners/equation_numeric_grammar/pipeline_frequencies.json', 'r') as f:
        freqs = json.load(f)
    combo_freqs = {}
    for k, v in freqs.items():
        parts = k.split(' -> ')
        if len(parts) >= 3:
            combo = (parts[0], parts[2])
            combo_freqs[combo] = combo_freqs.get(combo, 0.0) + v
    PIPELINES.sort(key=lambda c: combo_freqs.get(c, 0.0), reverse=True)
except Exception:
    pass


# =============================================================================
# PROBLEM PARSING
# =============================================================================

def extract_all_examples(prompt: str):
    lines = [l.strip() for l in prompt.split('\n') if '=' in l and 'determine' not in l.lower()]
    
    parsed_examples = []
    unique_digit_syms = set()
    unique_op_syms = set()
    
    for line in lines:
        m = re.search(r'^(\S{2})(\S)(\S{2})\s*=\s*(\S+)$', line)
        if not m: continue
        
        left_syms_A, op_sym, left_syms_B, right_str = m.groups()
        
        is_neg = False
        if right_str.startswith('-'):
            is_neg = True
            right_str = right_str[1:]
            
        # Handle potential symbol bleed in the answer string
        # If the operator symbol appears as a prefix/suffix, strip it for math evaluation
        prefix_bleed = right_str.startswith(op_sym)
        suffix_bleed = right_str.endswith(op_sym)
        
        if prefix_bleed: right_str = right_str[len(op_sym):]
        if suffix_bleed: right_str = right_str[:-len(op_sym)]
        
        out_syms = list(right_str)
        
        parsed_examples.append({
            'A': list(left_syms_A),
            'B': list(left_syms_B),
            'op': op_sym,
            'out': out_syms,
            'is_neg': is_neg,
            'prefix': prefix_bleed,
            'suffix': suffix_bleed
        })
        
        unique_digit_syms.update(list(left_syms_A) + list(left_syms_B) + out_syms)
        unique_op_syms.add(op_sym)
        
    target_m = re.search(r'result for:\s*(\S{2})(\S)(\S{2})', prompt)
    if not target_m: return None, [], set(), set(), ("", "", "")
    
    tA_str, tgt_op, tB_str = target_m.groups()
    tA = list(tA_str)
    tB = list(tB_str)
    
    unique_digit_syms.update(tA + tB)
    unique_op_syms.add(tgt_op)
    
    return tgt_op, parsed_examples, unique_digit_syms, unique_op_syms, (tA_str, tgt_op, tB_str)


# =============================================================================
# SOLVER
# =============================================================================

def solve_cipher_unified(prompt: str, target_answer: str = None, mode: str = 'greedy') -> Any:
    tgt_op, parsed_examples, digit_syms, op_syms, (tA, tgt_op_str, tB) = extract_all_examples(prompt)
    
    if not tgt_op or not parsed_examples: return None
    
    # 1. IMMEDIATE REJECTION: Too many symbols for a base-10 bijective cipher
    if len(digit_syms) > 10:
        return False if mode == 'theoretical' else None

    # 2. IMMEDIATE REJECTION: Length Compatibility
    for ex in parsed_examples:
        if len(ex['A']) != 2 or len(ex['B']) != 2:
            return False if mode == 'theoretical' else None
    if len(tA) != 2 or len(tB) != 2:
        return False if mode == 'theoretical' else None

    digit_sym_list = list(digit_syms)
    op_sym_list = list(op_syms)
    
    possible_answers = set()
    
    # Loop over the 6 global formatting pipelines
    for p, f in PIPELINES:
        problem = Problem()
        
        # --- ADD VARIABLES ---
        # Digits get 0-9
        problem.addVariables(digit_sym_list, range(10))
        problem.addConstraint(AllDifferentConstraint(), digit_sym_list)
        
        # Operators get the string names of the 12 math functions
        problem.addVariables(op_sym_list, list(MID_OPS.keys()))
        
        # --- BASE CONSTRAINTS ---
        # Leading digits cannot be 0
        for ex in parsed_examples:
            if len(ex['A']) > 1: problem.addConstraint(lambda x: x != 0, [ex['A'][0]])
            if len(ex['B']) > 1: problem.addConstraint(lambda x: x != 0, [ex['B'][0]])
            if len(ex['out']) > 1: problem.addConstraint(lambda x: x != 0, [ex['out'][0]])
        if len(tA) > 1: problem.addConstraint(lambda x: x != 0, [tA[0]])
        if len(tB) > 1: problem.addConstraint(lambda x: x != 0, [tB[0]])

        # --- DYNAMIC MATH CONSTRAINTS PER EXAMPLE ---
        for ex in parsed_examples:
            # The variables involved in this specific equation
            ex_digit_syms = list(set(ex['A'] + ex['B'] + ex['out']))
            
            # We must create a closure to capture the loop variables correctly
            def make_ex_constraint(current_ex, current_digit_syms, p_type, f_type):
                def ex_check(*args):
                    # args will contain: [digit_val_1, digit_val_2, ..., op_name]
                    digit_vals = args[:-1]
                    op_name = args[-1]
                    
                    mapping = dict(zip(current_digit_syms, digit_vals))
                    
                    A_vals = [mapping[s] for s in current_ex['A']]
                    B_vals = [mapping[s] for s in current_ex['B']]
                    out_vals = [mapping[s] for s in current_ex['out']]
                    
                    try:
                        L, R = PRE_OPS[p_type](A_vals, B_vals)
                        expected_val = MID_OPS[op_name](L, R)
                        return check_post(expected_val, out_vals, f_type, current_ex['is_neg'])
                    except Exception:
                        return False
                return ex_check
                
            # Attach constraint: variables = [digit symbols] + [the operator symbol]
            problem.addConstraint(
                make_ex_constraint(ex, ex_digit_syms, p, f), 
                ex_digit_syms + [ex['op']]
            )
            
        # --- SOLVE CSP ---
        # 2-second timeout per global formatting pipeline
        try:
            signal.alarm(2)
            solutions = problem.getSolutions()
            signal.alarm(0)
        except TimeoutException:
            continue
            
        if solutions:
            for sol in solutions:
                # Separate digit mapping from operator mapping
                digit_map = {sym: sol[sym] for sym in digit_sym_list}
                op_map = {sym: sol[sym] for sym in op_sym_list}
                
                tA_vals = [digit_map[s] for s in tA]
                tB_vals = [digit_map[s] for s in tB]
                tgt_math_op = op_map[tgt_op_str]
                
                try:
                    L, R = PRE_OPS[p](tA_vals, tB_vals)
                    numeric_ans = MID_OPS[tgt_math_op](L, R)
                except Exception:
                    continue

                if numeric_ans is None: continue
                
                # Format numeric answer
                s_val = str(numeric_ans)
                if f == 'rev': s_val = s_val[::-1]
                elif f == 'swap':
                    s_val = '-' + s_val[1:][::-1] if s_val.startswith('-') else s_val[::-1]
                    
                # Encode back to symbols
                inv_digit_map = {v: k for k, v in digit_map.items()}
                encoded_ans = ""
                can_encode = True
                
                for char in s_val:
                    if char == '-': encoded_ans += '-'
                    else:
                        digit_int = int(char)
                        if digit_int not in inv_digit_map:
                            can_encode = False
                            break
                        encoded_ans += inv_digit_map[digit_int]
                        
                if can_encode:
                    # Restore symbol bleed if the FIRST example had it
                    if parsed_examples[0]['prefix']: encoded_ans = tgt_op_str + encoded_ans
                    if parsed_examples[0]['suffix']: encoded_ans = encoded_ans + tgt_op_str
                    
                    if mode == 'greedy': return encoded_ans
                    possible_answers.add(encoded_ans)

    if mode == 'theoretical':
        return str(target_answer) in possible_answers
        
    return None

if __name__ == "__main__":
    print("Loading cryptarithm problems...")
    problems = [p for p in NemotronProblem.load_all() if p.category == 'cryptarithm_deduce']
    df = pd.read_csv('/workspaces/nemotron/train.csv')
    
    df['category'] = None
    with open('/workspaces/nemotron/problems.jsonl', 'r') as f:
        for line in f:
            p = json.loads(line)
            df.loc[df['id'] == p['id'], 'category'] = p['category']
            
    df_crypt = df[df['category'] == 'cryptarithm_deduce']
    print(f"Total cryptarithm_deduce problems: {len(df_crypt)}")

    correct = 0
    total = 0
    # Testing 10 problems to observe the massive speedup and accuracy
    for _, row in tqdm.tqdm(df_crypt.head(10).iterrows(), total=min(10, len(df_crypt))):
        total += 1
        prompt = row['prompt']
        ans = str(row['answer'])
        pred = solve_cipher_unified(prompt, mode='greedy')
        if pred == ans:
            correct += 1
            print(f"\n[CORRECT] Problem {row['id']}: {pred} == {ans}")
        else:
            print(f"\n[INCORRECT] Problem {row['id']}: Expected {ans}, Got {pred}")
            
    print(f"\nAccuracy on subset: {correct}/{total} ({correct/total*100:.2f}%)")
