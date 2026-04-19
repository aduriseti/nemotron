import sys
import json
import re
import signal
import time
from typing import Any

from z3 import Solver, Int, Distinct, And, Or, If, sat, unknown, set_param

WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path: sys.path.append(WORKSPACE_DIR)

from reasoners.store_types import Problem as NemotronProblem

# Enable verbose telemetry for Z3
set_param('verbose', 1)

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
    op_names = list(MATH_OPS.keys())
    
    for f_type, _ in PIPELINES:
        print(f"  [>] Trialling pipeline: `{f_type}->{f_type}` with Z3 Solver", file=sys.__stdout__, flush=True)
            
        solver = Solver()
        solver.set("timeout", 2000) # Hard timeout of 2 seconds for Z3 internal search
        
        # 1. Variables
        digit_vars = {sym: Int(sym) for sym in digit_sym_list}
        for var in digit_vars.values():
            solver.add(And(var >= 0, var <= 9))
            
        solver.add(Distinct(*list(digit_vars.values())))
        
        op_vars = {sym: Int(f"{sym}_op") for sym in op_sym_list}
        for op_var in op_vars.values():
            solver.add(And(op_var >= 0, op_var <= len(op_names) - 1))

        def z3_make_num(digits):
            if not digits: return 0
            return sum(d * (10**(len(digits)-1-i)) for i, d in enumerate(digits))

        def z3_abs(x):
            return If(x >= 0, x, -x)

        def z3_max(x, y):
            return If(x > y, x, y)

        def z3_min(x, y):
            return If(x < y, x, y)

        # 2. Add Disjunction Constraints for each Example
        for ex in parsed_examples:
            if f_type == 'raw':
                A_vals = [digit_vars.get(s, Int(s)) for s in ex['A']]
                B_vals = [digit_vars.get(s, Int(s)) for s in ex['B']]
            elif f_type == 'swap':
                A_vals = [digit_vars.get(s, Int(s)) for s in ex['A'][::-1]]
                B_vals = [digit_vars.get(s, Int(s)) for s in ex['B'][::-1]]
            elif f_type == 'rev':
                A_vals = [digit_vars.get(s, Int(s)) for s in ex['A'][::-1]]
                B_vals = [digit_vars.get(s, Int(s)) for s in ex['B'][::-1]]
                
            L = z3_make_num(A_vals)
            R = z3_make_num(B_vals)
            
            op_var = op_vars[ex['op']]
            possible_conditions = []
            
            for i, op_name in enumerate(op_names):
                if op_name == 'add': eq_val = L + R
                elif op_name == 'sub': eq_val = L - R
                elif op_name == 'mul': eq_val = L * R
                elif op_name == 'cat': 
                    eq_val = If(R < 10, L * 10 + R, L * 100 + R)
                elif op_name == 'max_mod_min':
                    mn = z3_min(L, R)
                    mx = z3_max(L, R)
                    eq_val = If(mn != 0, mx % mn, mx)
                elif op_name == 'add1': eq_val = L + R + 1
                elif op_name == 'addm1': eq_val = L + R - 1
                elif op_name == 'mul1': eq_val = L * R + 1
                elif op_name == 'mulm1': eq_val = L * R - 1
                elif op_name == 'sub_abs': eq_val = z3_abs(L - R)
                elif op_name == 'sub_neg_abs': eq_val = -z3_abs(L - R)
                else: continue
                
                m_sym = MATH_OPS[op_name]['sym']
                out_syms = ex['out']
                
                cond = False
                
                # Try to parse the expected output dynamically based on formatter
                if all(c in digit_vars for c in out_syms):
                    if f_type == 'raw':
                        out_val_z3 = z3_make_num([digit_vars[c] for c in out_syms])
                    elif f_type == 'swap':
                        # The string was formed, THEN swapped. So out_syms corresponds to the swapped string.
                        # To match `eq_val`, we need to un-swap `out_syms`? No, eq_val is the math result.
                        # The math result is stringified, then swapped, to produce `out_syms`.
                        # So `eq_val` should equal the numeric value of `out_syms` UN-SWAPPED.
                        # swap: reversed string. Wait, formatter 'swap' applies [::-1] to the string *if not negative*, else preserves '-' and reverses the rest.
                        # Assuming positive for simplicity in SMT:
                        out_val_z3 = z3_make_num([digit_vars[c] for c in out_syms[::-1]])
                    elif f_type == 'rev':
                        out_val_z3 = z3_make_num([digit_vars[c] for c in out_syms[::-1]])
                        
                    cond = (eq_val == out_val_z3)
                elif len(out_syms) > 1 and out_syms[0] == ex['op'] and all(c in digit_vars for c in out_syms[1:]):
                    if f_type == 'raw':
                        out_val_z3 = z3_make_num([digit_vars[c] for c in out_syms[1:]])
                    elif f_type == 'swap':
                        out_val_z3 = z3_make_num([digit_vars[c] for c in out_syms[1:][::-1]])
                    elif f_type == 'rev':
                        # 'rev' reverses the entire string, including the minus sign!
                        # So the minus sign would be at the END. This block assumes it's at the beginning.
                        out_val_z3 = z3_make_num([digit_vars[c] for c in out_syms[1:]]) # fallback
                        
                    cond = And(eq_val < 0, eq_val == -out_val_z3)
                elif f_type == 'rev' and len(out_syms) > 1 and out_syms[-1] == ex['op'] and all(c in digit_vars for c in out_syms[:-1]):
                    # for 'rev', negative sign ends up at the end
                    out_val_z3 = z3_make_num([digit_vars[c] for c in out_syms[:-1][::-1]])
                    cond = And(eq_val < 0, eq_val == -out_val_z3)
                        
                possible_conditions.append(And(op_var == i, cond))
                
            solver.add(Or(*possible_conditions))
            
        start_time = time.time()
        solutions_found = 0
        z3_check_time = 0.0
        
        while True:
            t0 = time.time()
            res = solver.check()
            z3_check_time += time.time() - t0
            
            if res == unknown:
                print(f"  [!] Z3 returned 'unknown' (likely hit 2000ms timeout). Stats: {solver.statistics()}", file=sys.__stdout__, flush=True)
                break
            elif res != sat:
                break
                
            model = solver.model()
            solutions_found += 1
            if solutions_found >= 50000: break
            
            # Print statistics for this model
            stats = solver.statistics()
            conflicts = stats.get_key_value('smt.conflicts') if 'smt.conflicts' in stats.keys() else 0
            decisions = stats.get_key_value('smt.decisions') if 'smt.decisions' in stats.keys() else 0
            print(f"  [i] Model {solutions_found} found in {z3_check_time:.4f}s. Z3 Stats: Conflicts={conflicts}, Decisions={decisions}", file=sys.__stdout__, flush=True)
            
            # Extract
            digit_map = {sym: model[digit_vars[sym]].as_long() for sym in digit_sym_list}
            op_map = {sym: op_names[model[op_vars[sym]].as_long()] for sym in op_sym_list}
            
            # Force Z3 to find a different solution
            block = []
            for sym, var in digit_vars.items():
                block.append(var != digit_map[sym])
            for sym, var in op_vars.items():
                block.append(var != model[var])
            solver.add(Or(*block))
            
            # -------------------------------------------------------------
            # EXACT PYTHON VALIDATION (Same as original)
            # -------------------------------------------------------------
            all_valid = True
            for ex in parsed_examples:
                A_vals = [digit_map.get(s, -1) for s in ex['A']]
                B_vals = [digit_map.get(s, -1) for s in ex['B']]
                
                if -1 in A_vals or -1 in B_vals: 
                    all_valid = False
                    break
                    
                op_name = op_map[ex['op']]
                L, R, d1, d2, d3, d4 = FORMATTERS[f_type]['pre'](A_vals, B_vals)
                expected_val = MATH_OPS[op_name]['fn'](L, R, d1, d2, d3, d4)
                if not check_post(expected_val, ex['out'], f_type, op_name, ex['op'], digit_map):
                    all_valid = False
                    break
                    
            if not all_valid:
                continue
                
            # If valid, process target answer!
            tA_vals = [digit_map.get(s, -1) for s in tA]
            tB_vals = [digit_map.get(s, -1) for s in tB]
            if -1 in tA_vals or -1 in tB_vals: continue
            
            tgt_math_op = op_map[tgt_op_str]
            L_tgt, R_tgt, _, _, _, _ = FORMATTERS[f_type]['pre'](tA_vals, tB_vals)
            numeric_ans = MATH_OPS[tgt_math_op]['fn'](L_tgt, R_tgt, 0, 0, 0, 0)

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
                if encoded_ans not in possible_answers:
                    possible_answers[encoded_ans] = 0
                possible_answers[encoded_ans] += 1
                
                # Telemetry for solution found
                print(f"  [+] Found Valid Model. Encoded Ans: {encoded_ans}", file=sys.__stdout__, flush=True)

        # Print telemetry stats
        print(f"  [=] Pipeline {f_type} finished. Total models: {solutions_found}. Z3 Time: {z3_check_time:.4f}s", file=sys.__stdout__, flush=True)

    if mode == 'greedy':
        if possible_answers: 
            return max(possible_answers, key=possible_answers.get)
        return None

    if mode == 'theoretical':
        return str(target_answer) in possible_answers
        
    return possible_answers
