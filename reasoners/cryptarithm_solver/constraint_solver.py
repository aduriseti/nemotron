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
# GLOBAL SYMBOL UNIVERSE
# =============================================================================
SYMBOL_UNIVERSE = ['!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', ':', '<', '=', '>', '?', '@', '[', '\\', ']', '^', '_', '`', '{', '|', '}', '~']


# =============================================================================
# GRAMMAR AND ALGEBRAIC GENERATORS
# =============================================================================

def make_num(digits):
    """Calculates the integer value of a list of integer digits (e.g. [1, 2] -> 12)"""
    return sum(d * (10**(len(digits)-1-i)) for i, d in enumerate(digits))

# Pre-Ops: Return L, R, d1, d2, d3, d4
PRE_OPS = {
    'ABCD': lambda A_vals, B_vals: (make_num(A_vals), make_num(B_vals), A_vals[0], A_vals[1], B_vals[0], B_vals[1]),
    'BADC': lambda A_vals, B_vals: (make_num(A_vals[::-1]), make_num(B_vals[::-1]), A_vals[1], A_vals[0], B_vals[1], B_vals[0]),
    'DCBA': lambda A_vals, B_vals: (make_num(B_vals[::-1]), make_num(A_vals[::-1]), B_vals[1], B_vals[0], A_vals[1], A_vals[0])
}

# Mid-Ops: Standard mathematical operations
MID_OPS = {
    'add': lambda L, R, d1, d2, d3, d4: L + R,
    'sub': lambda L, R, d1, d2, d3, d4: L - R,
    'mul': lambda L, R, d1, d2, d3, d4: L * R,
    'cat': lambda L, R, d1, d2, d3, d4: int(str(L) + str(R)),
    'max_mod_min': lambda L, R, d1, d2, d3, d4: max(L, R) % min(L, R) if min(L, R) != 0 else max(L, R),
    'add1': lambda L, R, d1, d2, d3, d4: L + R + 1,
    'addm1': lambda L, R, d1, d2, d3, d4: L + R - 1,
    'mul1': lambda L, R, d1, d2, d3, d4: L * R + 1,
    'mulm1': lambda L, R, d1, d2, d3, d4: L * R - 1,
    'sub_abs': lambda L, R, d1, d2, d3, d4: abs(L - R),
    'sub_neg_abs': lambda L, R, d1, d2, d3, d4: -abs(L - R)
}

# Post-Ops: Format the numeric result
POST_OPS = {
    'raw': lambda s_exp_abs: s_exp_abs,
    'rev': lambda s_exp_abs: s_exp_abs[::-1],
    'swap': lambda s_exp_abs: s_exp_abs[::-1]
}

# Check if the mathematical result matches the expected output digits
def check_post(expected_val, out_vals, f_type, is_negative):
    if expected_val is None: return False
    s_exp = str(expected_val)
    if is_negative and not s_exp.startswith('-'): return False
    if not is_negative and s_exp.startswith('-'): return False
    
    s_exp_abs = s_exp[1:] if is_negative else s_exp
    s_out = "".join(str(d) for d in out_vals)
    
    actual_str = POST_OPS[f_type](s_exp_abs)
    if f_type == 'rev' and is_negative:
        actual_str = "-" + actual_str
        
    return actual_str == s_out

# The global formatting combinations
PIPELINES = []
for p in PRE_OPS.keys():
    for f in POST_OPS.keys():
        PIPELINES.append((p, f))

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
    active_digits = set()
    active_ops = set()
    
    prompt_syms = set()
    for char in prompt:
        if not char.isspace() and not char.isalnum() and char not in ['=', ',']:
            prompt_syms.add(char)
    
    for line in lines:
        m = re.search(r'^(\S{2})(\S)(\S{2})\s*=\s*(\S+)$', line)
        if not m: continue
        
        left_syms_A, op_sym, left_syms_B, right_str = m.groups()
        
        is_neg = False
        if right_str.startswith('-'):
            is_neg = True
            right_str = right_str[1:]
            
        # Handle potential symbol bleed in the answer string
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
        
        active_digits.update(list(left_syms_A) + list(left_syms_B) + out_syms)
        active_ops.add(op_sym)
        
    target_m = re.search(r'result for:\s*(\S{2})(\S)(\S{2})', prompt)
    if not target_m: return None, [], set(), set(), set(), ("", "", "")
    
    tA_str, tgt_op, tB_str = target_m.groups()
    tA = list(tA_str)
    tB = list(tB_str)
    
    active_digits.update(tA + tB)
    active_ops.add(tgt_op)
    
    return tgt_op, parsed_examples, active_digits, active_ops, prompt_syms, (tA_str, tgt_op, tB_str)


# =============================================================================
# SOLVER
# =============================================================================

def solve_cipher_unified(prompt: str, target_answer: str = None, mode: str = 'greedy') -> Any:
    extract_result = extract_all_examples(prompt)
    if not extract_result[0]: return None
    tgt_op, parsed_examples, active_digits, active_ops, prompt_syms, (tA, tgt_op_str, tB) = extract_result
    
    if not parsed_examples: return None

    # Length Compatibility Check
    for ex in parsed_examples:
        if len(ex['A']) != 2 or len(ex['B']) != 2:
            return False if mode == 'theoretical' else None
    if len(tA) != 2 or len(tB) != 2:
        return False if mode == 'theoretical' else None

    # ==========================================
    # BUILD THE DIGIT AND OPERATOR DOMAINS
    # ==========================================
    active_ops_only = active_ops - active_digits
    
    if len(active_digits) > 10:
        return False if mode == 'theoretical' else None
        
    digit_sym_list = list(active_digits) + list(active_ops_only)
    op_sym_list = list(active_ops)
    possible_answers = {}

    # Loop over the 6 global formatting pipelines
    for p, f in PIPELINES:
        problem = Problem()        
        # --- ADD VARIABLES ---
        # 1. Definite Digits get 0-9
        problem.addVariables(list(active_digits), range(10))
        
        # 2. Ops-Only get NEGATIVES ONLY so they don't steal 0-9 from actual missing digit symbols
        if active_ops_only:
            negatives = list(range(-1, -len(active_ops_only) - 1, -1))
            problem.addVariables(list(active_ops_only), negatives)
            
        problem.addConstraint(AllDifferentConstraint(), digit_sym_list)
        
        # 3. Operators get the string names of the 12 math functions
        op_vars = [f"{sym}_op" for sym in op_sym_list]
        problem.addVariables(op_vars, list(MID_OPS.keys()))
        problem.addConstraint(AllDifferentConstraint(), op_vars)
        
        # --- BASE CONSTRAINTS ---
        # Leading digits CAN be 0 in cryptarithms apparently! 
        # (This is why 017a871e failed, it required a leading zero)
        # We will not enforce non-zero leading digits.

        # --- DYNAMIC MATH CONSTRAINTS PER EXAMPLE ---
        for ex in parsed_examples:
            ex_digit_syms = list(set(ex['A'] + ex['B'] + ex['out']))
            ex_op_var = f"{ex['op']}_op"
            
            def make_ex_constraint(current_ex, current_digit_syms, p_type, f_type):
                def ex_check(*args):
                    digit_vals = args[:-1]
                    op_name = args[-1]
                    
                    mapping = dict(zip(current_digit_syms, digit_vals))
                    
                    A_vals = [mapping[s] for s in current_ex['A']]
                    B_vals = [mapping[s] for s in current_ex['B']]
                    out_vals = [mapping[s] for s in current_ex['out']]
                    
                    try:
                        L, R, d1, d2, d3, d4 = PRE_OPS[p_type](A_vals, B_vals)
                        expected_val = MID_OPS[op_name](L, R, d1, d2, d3, d4)
                        return check_post(expected_val, out_vals, f_type, current_ex['is_neg'])
                    except Exception:
                        return False
                return ex_check
                
            problem.addConstraint(
                make_ex_constraint(ex, ex_digit_syms, p, f), 
                ex_digit_syms + [ex_op_var]
            )
            
        # --- SOLVE CSP ---
        try:
            import time
            start_time = time.time()
            iterator = problem.getSolutionIter()
            solutions = []
            while time.time() - start_time < 2.0:
                try:
                    sol = next(iterator)
                    solutions.append(sol)
                except StopIteration:
                    break
        except TimeoutException:
            print(f"DEBUG: Timeout for {p}->{f}")
            continue
            
        if solutions:
            for sol in solutions:
                digit_map = {sym: sol[sym] for sym in digit_sym_list}
                op_map = {sym: sol[f"{sym}_op"] for sym in op_sym_list}
                
                tA_vals = [digit_map[s] for s in tA]
                tB_vals = [digit_map[s] for s in tB]
                tgt_math_op = op_map[tgt_op_str]
                
                try:
                    L, R, d1, d2, d3, d4 = PRE_OPS[p](tA_vals, tB_vals)
                    numeric_ans = MID_OPS[tgt_math_op](L, R, d1, d2, d3, d4)
                except Exception:
                    continue

                if numeric_ans is None: continue
                
                # Format numeric answer
                s_val = str(numeric_ans)
                s_val_abs = s_val[1:] if s_val.startswith('-') else s_val
                
                fmt_ans = POST_OPS[f](s_val_abs)
                if f == 'rev' and s_val.startswith('-'):
                    fmt_ans = '-' + fmt_ans
                elif f == 'swap' and s_val.startswith('-'):
                    fmt_ans = '-' + fmt_ans
                s_val = fmt_ans
                
                inv_digit_map = {v: k for k, v in digit_map.items() if v >= 0}
                print(f"DEBUG SOLUTION: {p}->{f}, ops: {op_map}, ans: {s_val}, map: {inv_digit_map}")
                    
                # Encode back to symbols
                encoded_ans = ""
                can_encode = True
                
                used_missing_syms = set()
                
                for char in s_val:
                    if char == '-': encoded_ans += '-'
                    else:
                        digit_int = int(char)
                        if digit_int not in inv_digit_map:
                            found_sym = None
                            for fallback_sym in SYMBOL_UNIVERSE:
                                if fallback_sym not in digit_sym_list and fallback_sym not in prompt_syms and fallback_sym not in used_missing_syms:
                                    found_sym = fallback_sym
                                    break
                            if not found_sym:
                                can_encode = False
                                break
                            
                            inv_digit_map[digit_int] = found_sym
                            used_missing_syms.add(found_sym)
                            
                        encoded_ans += inv_digit_map[digit_int]
                        
                if can_encode:
                    # Restore symbol bleed if the FIRST example had it
                    if parsed_examples[0]['prefix']: encoded_ans = tgt_op_str + encoded_ans
                    if parsed_examples[0]['suffix']: encoded_ans = encoded_ans + tgt_op_str
                    
                    if encoded_ans not in possible_answers:
                        possible_answers[encoded_ans] = 0
                    possible_answers[encoded_ans] += 1

    if mode == 'greedy':
        if possible_answers: 
            return max(possible_answers, key=possible_answers.get)
        return None

    if mode == 'theoretical':
        return str(target_answer) in possible_answers
        
    return possible_answers

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
    # Testing subset to observe the accuracy improvement
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
