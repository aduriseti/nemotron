import sys
import pandas as pd
import json
import re
import signal
from typing import Any
from constraint import Problem, AllDifferentConstraint

WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path: sys.path.append(WORKSPACE_DIR)

from reasoners.store_types import Problem as NemotronProblem

# =============================================================================
# GLOBAL SYMBOL UNIVERSE
# =============================================================================
SYMBOL_UNIVERSE = ['!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', ':', '<', '=', '>', '?', '@', '[', '\\', ']', '^', '_', '`', '{', '|', '}', '~']

def make_num(digits):
    return sum(d * (10**(len(digits)-1-i)) for i, d in enumerate(digits))

MATH_OPS = {
    'add': {'fn': lambda L, R, d1, d2, d3, d4: L + R, 'sym': '+'},
    'sub': {'fn': lambda L, R, d1, d2, d3, d4: L - R, 'sym': '-'},
    'mul': {'fn': lambda L, R, d1, d2, d3, d4: L * R, 'sym': '*'},
    'cat': {'fn': lambda L, R, d1, d2, d3, d4: int(str(L) + str(R)), 'sym': '||'},
    'max_mod_min': {'fn': lambda L, R, d1, d2, d3, d4: max(L, R) % min(L, R) if min(L, R) != 0 else max(L, R), 'sym': ''},
    'add1': {'fn': lambda L, R, d1, d2, d3, d4: L + R + 1, 'sym': ''},
    'addm1': {'fn': lambda L, R, d1, d2, d3, d4: L + R - 1, 'sym': '-'},
    'mul1': {'fn': lambda L, R, d1, d2, d3, d4: L * R + 1, 'sym': ''},
    'mulm1': {'fn': lambda L, R, d1, d2, d3, d4: L * R - 1, 'sym': '-'},
    'sub_abs': {'fn': lambda L, R, d1, d2, d3, d4: abs(L - R), 'sym': ''},
    'sub_neg_abs': {'fn': lambda L, R, d1, d2, d3, d4: -abs(L - R), 'sym': '-'}
}

FORMATTERS = {
    'raw': {
        'pre': lambda A_vals, B_vals: (make_num(A_vals), make_num(B_vals), A_vals[0], A_vals[1], B_vals[0], B_vals[1]),
        'post': lambda val: str(val)
    },
    'swap': {
        'pre': lambda A_vals, B_vals: (make_num(A_vals[::-1]), make_num(B_vals[::-1]), A_vals[1], A_vals[0], B_vals[1], B_vals[0]),
        'post': lambda val: ('-' + str(val)[1:][::-1] if str(val).startswith('-') else str(val)[::-1])
    },
    'rev': {
        'pre': lambda A_vals, B_vals: (make_num(B_vals[::-1]), make_num(A_vals[::-1]), B_vals[1], B_vals[0], A_vals[1], A_vals[0]),
        'post': lambda val: str(val)[::-1]
    }
}

PIPELINES = [(f, f) for f in FORMATTERS.keys()]

def check_post(expected_val, out_syms, fmt_name, op_name, op_sym, mapping):
    if expected_val is None: return False
    
    fmt_val_str = FORMATTERS[fmt_name]['post'](expected_val)
    m_sym = MATH_OPS[op_name]['sym']
    
    if m_sym == '-':
        fmt_val_str = fmt_val_str.replace('-', op_sym)
    elif m_sym != "":
        fmt_val_str = fmt_val_str.replace(m_sym, op_sym)
        
    if len(fmt_val_str) != len(out_syms): return False
    
    for f_c, o_c in zip(fmt_val_str, out_syms):
        if f_c.isdigit():
            if int(f_c) != mapping.get(o_c, -1):
                return False
        else:
            if f_c != o_c:
                return False
    return True

def extract_all_examples(prompt: str):
    lines = [l.strip() for l in prompt.split('\n') if '=' in l and 'determine' not in l.lower()]
    parsed_examples = []
    
    target_m = re.search(r'result for:\s*(\S{2})(\S)(\S{2})', prompt)
    if not target_m: return None, [], "", "", ""
    tA_str, tgt_op, tB_str = target_m.groups()
    
    for line in lines:
        parts = line.split('=')
        if len(parts) != 2: continue
        lhs = parts[0].strip()
        rhs = parts[1].strip()
        
        if len(lhs) != 5:
            raise ValueError(f"LHS is strictly required to be exactly 5 characters! Line: '{line}' | LHS: '{lhs}' | Length: {len(lhs)}")
            
        parsed_examples.append({
            'A': list(lhs[:2]),
            'B': list(lhs[3:5]),
            'op': lhs[2],
            'out': list(rhs)
        })
        
    return parsed_examples, list(tA_str), list(tB_str), tgt_op

def solve_cipher_unified(prompt: str, mode: str = 'greedy', target_answer: str = None) -> Any:
    extraction = extract_all_examples(prompt)
    if extraction[0] is None: return False if mode == 'theoretical' else None
    
    parsed_examples, tA, tB, tgt_op_str = extraction
    
    a_b_syms = set(tA + tB)
    for ex in parsed_examples:
        a_b_syms.update(ex['A'] + ex['B'])
        
    out_syms = set()
    for ex in parsed_examples:
        out_syms.update(ex['out'])
        
    active_digits = a_b_syms | out_syms
    ops_used = set(ex['op'] for ex in parsed_examples) | {tgt_op_str}
    
    for op in ops_used:
        if op not in a_b_syms and len(active_digits) > 10:
            active_digits.discard(op)
            
    digit_sym_list = list(active_digits)
    op_sym_list = list(ops_used)
    
    possible_answers = {}
    
    for f_type, _ in PIPELINES:
        print(f"  [>] Trialling pipeline: `{f_type}->{f_type}`", file=sys.__stdout__, flush=True)
            
        problem = Problem()
        problem.addVariables(digit_sym_list, range(10))
        problem.addConstraint(AllDifferentConstraint(), digit_sym_list)
        problem.addVariables([f"{sym}_op" for sym in op_sym_list], list(MATH_OPS.keys()))
        
        for ex in parsed_examples:
            ex_digit_syms = list(set(ex['A'] + ex['B'] + ex['out']) & active_digits)
            ex_op_var = f"{ex['op']}_op"
            
            def make_ex_constraint(current_ex, current_digit_syms, fmt):
                def ex_check(*args):
                    digit_vals = args[:-1]
                    op_name = args[-1]
                    
                    mapping = dict(zip(current_digit_syms, digit_vals))
                    
                    A_vals = [mapping.get(s, -1) for s in current_ex['A']]
                    B_vals = [mapping.get(s, -1) for s in current_ex['B']]
                    
                    if -1 in A_vals or -1 in B_vals: return False
                    
                    try:
                        L, R, d1, d2, d3, d4 = FORMATTERS[fmt]['pre'](A_vals, B_vals)
                        expected_val = MATH_OPS[op_name]['fn'](L, R, d1, d2, d3, d4)
                        return check_post(expected_val, current_ex['out'], fmt, op_name, current_ex['op'], mapping)
                    except Exception:
                        return False
                return ex_check
                
            problem.addConstraint(
                make_ex_constraint(ex, ex_digit_syms, f_type), 
                ex_digit_syms + [ex_op_var]
            )
            
        import time
        start_time = time.time()
        iterator = problem.getSolutionIter()
        solutions = []
        for i, sol in enumerate(iterator):
            if time.time() - start_time > 2.0:
                print(f"  [!] Timeout reached for pipeline `{f_type}->{f_type}` after 2.0s", file=sys.__stdout__, flush=True)
                break
            solutions.append(sol)
            if i >= 50000: break
            
        if solutions:
            seen_math_maps = set()
            for sol in solutions:
                digit_map = {sym: sol[sym] for sym in digit_sym_list}
                op_map = {sym: sol[f"{sym}_op"] for sym in op_sym_list}
                
                active_digit_map = tuple(sorted(digit_map.items()))
                active_op_map = tuple(sorted(op_map.items()))
                math_sig = (active_digit_map, active_op_map)
                
                if math_sig in seen_math_maps: continue
                seen_math_maps.add(math_sig)
                
                tA_vals = [digit_map.get(s, -1) for s in tA]
                tB_vals = [digit_map.get(s, -1) for s in tB]
                if -1 in tA_vals or -1 in tB_vals: continue
                
                tgt_math_op = op_map[tgt_op_str]
                
                try:
                    L_tgt, R_tgt, _, _, _, _ = FORMATTERS[f_type]['pre'](tA_vals, tB_vals)
                    numeric_ans = MATH_OPS[tgt_math_op]['fn'](L_tgt, R_tgt, 0, 0, 0, 0)
                except Exception:
                    continue

                if numeric_ans is None: continue
                
                s_val_str = FORMATTERS[f_type]['post'](numeric_ans)
                m_sym = MATH_OPS[tgt_math_op]['sym']
                
                if m_sym == '-':
                    s_val_str = s_val_str.replace('-', tgt_op_str)
                elif m_sym != "":
                    s_val_str = s_val_str.replace(m_sym, tgt_op_str)
                
                inv_digit_map = {v: k for k, v in digit_map.items()}
                
                encoded_ans = ""
                can_encode = True
                
                used_missing_syms = set()
                
                for char in s_val_str:
                    if char.isdigit():
                        digit_int = int(char)
                        if digit_int not in inv_digit_map:
                            found_sym = None
                            for fallback_sym in SYMBOL_UNIVERSE:
                                if fallback_sym not in digit_sym_list and fallback_sym not in ops_used and fallback_sym not in used_missing_syms:
                                    found_sym = fallback_sym
                                    break
                            if not found_sym:
                                can_encode = False
                                break
                            inv_digit_map[digit_int] = found_sym
                            used_missing_syms.add(found_sym)
                        encoded_ans += inv_digit_map[digit_int]
                    else:
                        encoded_ans += char
                        
                if can_encode:
                    # Print mathematically truthful debug info
                    print(f"\n========================================")
                    print(f"DEBUG SOLUTION: {f_type}->{f_type}")
                    print(f"Original Prompt:\n{prompt}")
                    print(f"Ops Map: {op_map}")
                    print(f"Digit Map: {inv_digit_map}")
                    print(f"----------------------------------------")
                    for ex_num, current_ex in enumerate(parsed_examples):
                        A_vals = [digit_map.get(c, "?") for c in current_ex['A']]
                        B_vals = [digit_map.get(c, "?") for c in current_ex['B']]
                        out_vals = [digit_map.get(c, "?") for c in current_ex['out']]
                        
                        math_op = op_map[current_ex['op']]
                        
                        L_ex, R_ex, _, _, _, _ = FORMATTERS[f_type]['pre'](A_vals, B_vals)
                        math_res = MATH_OPS[math_op]['fn'](L_ex, R_ex, 0, 0, 0, 0)
                        
                        fmt_ex = FORMATTERS[f_type]['post'](math_res)
                        m_sym_ex = MATH_OPS[math_op]['sym']
                        if m_sym_ex == '-':
                            fmt_ex = fmt_ex.replace('-', current_ex['op'])
                        elif m_sym_ex != "":
                            fmt_ex = fmt_ex.replace(m_sym_ex, current_ex['op'])
                            
                        encA = "".join(current_ex['A'])
                        encB = "".join(current_ex['B'])
                        encOut = "".join(current_ex['out'])
                        decA = "".join(str(v) for v in A_vals)
                        decB = "".join(str(v) for v in B_vals)
                        decOut = "".join(str(v) for v in out_vals)
                        
                        print(f"  Eq {ex_num+1}: {encA} {current_ex['op']} {encB} = {encOut}")
                        print(f"    Decrypted: {decA} {math_op} {decB} = {decOut}")
                        print(f"    Math: {L_ex} {math_op} {R_ex} -> Math Res: {math_res} -> Encrypted: {fmt_ex} == {encOut}")

                    encTA = "".join(tA)
                    encTB = "".join(tB)
                    decTA = "".join(str(digit_map.get(c, "?")) for c in tA)
                    decTB = "".join(str(digit_map.get(c, "?")) for c in tB)
                    
                    print(f"  Target Math:")
                    print(f"    Query: {encTA} {tgt_op_str} {encTB} = ?")
                    print(f"    Decrypted: {decTA} {tgt_math_op} {decTB} = ?")
                    print(f"    Math Evaluated: {L_tgt} {tgt_math_op} {R_tgt} -> Math Res: {numeric_ans} -> Formatted: {s_val_str} -> Encoded: {encoded_ans}", flush=True)
                    print(f"========================================\n")
                    
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
