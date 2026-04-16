import re
import sys
import pandas as pd
import tqdm
import json
import signal
from typing import Any, List, Dict, Tuple, Callable, Optional
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
# GRAMMAR AND CONSTRAINT DEFINITIONS
# =============================================================================

def make_num(digits: List[int]) -> int:
    """Calculates the integer value of a list of integer digits (e.g. [1, 2] -> 12)"""
    return sum(d * (10**(len(digits)-1-i)) for i, d in enumerate(digits))

# Pre-Ops: Return a tuple of lambdas that evaluate the Left and Right operands
def gen_pre_abcd(A_syms: List[str], B_syms: List[str]):
    return (lambda m: make_num([m[s] for s in A_syms]), lambda m: make_num([m[s] for s in B_syms]))

def gen_pre_badc(A_syms: List[str], B_syms: List[str]):
    return (lambda m: make_num([m[s] for s in A_syms[::-1]]), lambda m: make_num([m[s] for s in B_syms[::-1]]))

def gen_pre_cdab(A_syms: List[str], B_syms: List[str]):
    return (lambda m: make_num([m[s] for s in B_syms]), lambda m: make_num([m[s] for s in A_syms]))

def gen_pre_dcba(A_syms: List[str], B_syms: List[str]):
    return (lambda m: make_num([m[s] for s in B_syms[::-1]]), lambda m: make_num([m[s] for s in A_syms[::-1]]))

PRE_OPS = {
    'ABCD': gen_pre_abcd,
    'BADC': gen_pre_badc,
    'CDAB': gen_pre_cdab,
    'DCBA': gen_pre_dcba
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

# Post-Ops: Check if the mathematical result matches the expected symbol output
def check_post(expected_val: int, out_vals: List[int], f_type: str, is_negative: bool) -> bool:
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

# =============================================================================
# PROBLEM PARSING
# =============================================================================

def extract_examples(prompt: str) -> Tuple[Optional[str], List[Dict[str, Any]], Tuple[List[str], List[str]], List[str], str, str]:
    """Extracts and parses all examples and targets from the prompt."""
    lines = [l.strip() for l in prompt.split('\n') if '=' in l and 'determine' not in l.lower()]
    all_examples = []
    
    for line in lines:
        m = re.search(r'(\S{2})(\S)(\S{2})\s*=\s*(\S+)', line)
        if m: all_examples.append(m.groups())
            
    target_m = re.search(r'result for:\s*(\S{2})(\S)(\S{2})', prompt)
    if not target_m: return None, [], ([], []), [], "", ""
    
    tA_str, tgt_op, tB_str = target_m.groups()
    op_examples_raw = [(ex[0], ex[2], ex[3]) for ex in all_examples if ex[1] == tgt_op]
    
    if not op_examples_raw:
        return tgt_op, [], (list(tA_str), list(tB_str)), [], "", ""

    # Determine symbol bleed (prefix/suffix on the answer)
    ex_res_0 = op_examples_raw[0][2]
    prefix = tgt_op if ex_res_0.startswith(tgt_op) else ""
    suffix = tgt_op if ex_res_0.endswith(tgt_op) else ""

    unique_symbols = set()
    parsed_examples = []
    
    for exA, exB, ex_res in op_examples_raw:
        clean_res = ex_res.replace(tgt_op, '')
        is_neg = False
        if clean_res.startswith('-'):
            is_neg = True
            clean_res = clean_res[1:]
            
        A_syms = list(exA)
        B_syms = list(exB)
        out_syms = list(clean_res)
        
        parsed_examples.append({
            'A': A_syms,
            'B': B_syms,
            'out': out_syms,
            'is_neg': is_neg
        })
        
        unique_symbols.update(A_syms + B_syms + out_syms)
        
    tA, tB = list(tA_str), list(tB_str)
    unique_symbols.update(tA + tB)
    
    return tgt_op, parsed_examples, (tA, tB), list(unique_symbols), prefix, suffix

# =============================================================================
# CONSTRAINT GENERATOR
# =============================================================================

def generate_constraints(problem: Problem, parsed_examples: List[Dict[str, Any]], sym_list: List[str], pipeline: Tuple[str, str, str]):
    """
    Generates and attaches the specific constraints for a given pipeline
    to the provided python-constraint Problem object.
    """
    p, m, f = pipeline
    
    # Base constraints
    problem.addVariables(sym_list, range(10))
    problem.addConstraint(AllDifferentConstraint())

    # Leading zeros constraint
    for ex in parsed_examples:
        if len(ex['A']) > 1: problem.addConstraint(lambda x: x != 0, [ex['A'][0]])
        if len(ex['B']) > 1: problem.addConstraint(lambda x: x != 0, [ex['B'][0]])
        if len(ex['out']) > 1: problem.addConstraint(lambda x: x != 0, [ex['out'][0]])

    # The mathematical rule constraints
    for ex in parsed_examples:
        ex_syms = list(set(ex['A'] + ex['B'] + ex['out']))
        
        eval_L, eval_R = PRE_OPS[p](ex['A'], ex['B'])
        eval_mid = MID_OPS[m]
        
        # We must create a closure to capture the loop variables correctly
        def make_ex_constraint(e_L, e_R, e_mid, e_out, e_is_neg, e_f, e_syms):
            def generated_constraint(*args):
                mapping = dict(zip(e_syms, args))
                try:
                    L = e_L(mapping)
                    R = e_R(mapping)
                    expected_val = e_mid(L, R)
                    
                    out_vals = [mapping[s] for s in e_out]
                    return check_post(expected_val, out_vals, e_f, e_is_neg)
                except Exception:
                    return False
            return generated_constraint
            
        problem.addConstraint(
            make_ex_constraint(eval_L, eval_R, eval_mid, ex['out'], ex['is_neg'], f, ex_syms), 
            ex_syms
        )

# =============================================================================
# SOLVER
# =============================================================================

def load_combos():
    base_pipelines = [
        ('BADC', 'swap'), ('DCBA', 'swap'),
        ('BADC', 'rev'), ('DCBA', 'rev'),
        ('ABCD', 'raw'), ('CDAB', 'raw')
    ]
    combos = [(p, m, f) for (p, f) in base_pipelines for m in MID_OPS.keys()]
    
    try:
        with open('/workspaces/nemotron/reasoners/equation_numeric_grammar/pipeline_frequencies.json', 'r') as f:
            freqs = json.load(f)
        combo_freqs = {}
        for k, v in freqs.items():
            parts = k.split(' -> ')
            if len(parts) >= 3:
                c = (parts[0], parts[1], parts[2])
                combo_freqs[c] = combo_freqs.get(c, 0.0) + v
        combos.sort(key=lambda c: combo_freqs.get(c, 0.0), reverse=True)
    except Exception:
        pass
        
    return combos

COMBOS = load_combos()

def solve_cipher_digit(prompt: str, target_answer: str = None, mode: str = 'greedy') -> Any:
    tgt_op, parsed_examples, (tA, tB), sym_list, prefix, suffix = extract_examples(prompt)
    
    if not tgt_op or not parsed_examples: return None
    if len(sym_list) > 10: return None

    # Length check (our grammar requires 2-digit operands)
    for ex in parsed_examples:
        if len(ex['A']) != 2 or len(ex['B']) != 2: return None
    if len(tA) != 2 or len(tB) != 2: return None

    possible_answers = set()
    
    for p, m, f in COMBOS:
        problem = Problem()
        
        # 1) Generate and attach all constraints for THIS pipeline
        generate_constraints(problem, parsed_examples, sym_list, (p, m, f))

        # 2) Solve with timeout since some paths might hang without native bounds pruning
        try:
            signal.alarm(2)
            solutions = problem.getSolutions()
            signal.alarm(0)
        except TimeoutException:
            continue
        
        # 3) Process results
        if solutions:
            for mapping in solutions:
                eval_tL, eval_tR = PRE_OPS[p](tA, tB)
                
                try:
                    L = eval_tL(mapping)
                    R = eval_tR(mapping)
                    numeric_ans = MID_OPS[m](L, R)
                except Exception:
                    continue

                if numeric_ans is None: continue
                
                # Format
                s_val = str(numeric_ans)
                if f == 'rev': s_val = s_val[::-1]
                elif f == 'swap':
                    s_val = '-' + s_val[1:][::-1] if s_val.startswith('-') else s_val[::-1]
                    
                # Re-encode to symbols
                inv_map = {v: k for k, v in mapping.items()}
                encoded_ans = ""
                can_encode = True
                
                for char in s_val:
                    if char == '-': encoded_ans += '-'
                    else:
                        if int(char) not in inv_map:
                            can_encode = False
                            break
                        encoded_ans += inv_map[int(char)]
                        
                if can_encode:
                    encoded_ans = prefix + encoded_ans + suffix
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
    for _, row in tqdm.tqdm(df_crypt.head(50).iterrows(), total=min(50, len(df_crypt))):
        total += 1
        prompt = row['prompt']
        ans = str(row['answer'])
        pred = solve_cipher_digit(prompt)
        if pred == ans:
            correct += 1
            print(f"\n[CORRECT] Problem {row['id']}: {pred} == {ans}")
        else:
            print(f"\n[INCORRECT] Problem {row['id']}: Expected {ans}, Got {pred}")
            
    print(f"\nAccuracy on subset: {correct}/{total} ({correct/total*100:.2f}%)")