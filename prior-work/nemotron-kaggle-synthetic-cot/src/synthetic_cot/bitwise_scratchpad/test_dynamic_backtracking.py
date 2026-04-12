import pandas as pd
import re
import time
import itertools

# 1. Define Operations
OPS = {
    'AND': lambda a, b: a & b,
    'OR': lambda a, b: a | b,
    'XOR': lambda a, b: a ^ b,
    'NAND': lambda a, b: ~(a & b),
    'NOR': lambda a, b: ~(a | b),
    'XNOR': lambda a, b: ~(a ^ b),
    'NOT_A_AND_B': lambda a, b: (~a) & b,
    'A_AND_NOT_B': lambda a, b: a & (~b),
    'NOT_A_OR_B': lambda a, b: (~a) | b,
    'A_OR_NOT_B': lambda a, b: a | (~b)
}

TRANSFORMATIONS = [('rot', 0)]
for k in range(1, 8):
    TRANSFORMATIONS.extend([('rot', k), ('shl', k), ('shr', k)])

def get_used_vars(expr):
    used = []
    if '{A}' in expr: used.append('{A}')
    if '{B}' in expr: used.append('{B}')
    if '{C}' in expr: used.append('{C}')
    return used

def get_source_bit(in_bits, out_idx, trans):
    ttype, shift_val = trans
    if ttype == 'rot': 
        return in_bits[(out_idx + shift_val) % 8]
    elif ttype == 'shl':
        src = out_idx + shift_val
        return in_bits[src] if 0 <= src < 8 else 0
    elif ttype == 'shr':
        src = out_idx - shift_val
        return in_bits[src] if 0 <= src < 8 else 0

def evaluate_bit(evaluator, trans_dict, bit_idx, in_arrays, out_arrays, num_examples):
    for ex in range(num_examples):
        in_bits = in_arrays[ex]
        expected = out_arrays[ex][bit_idx]
        
        a_val = get_source_bit(in_bits, bit_idx, trans_dict.get('{A}', ('rot', 0)))
        b_val = get_source_bit(in_bits, bit_idx, trans_dict.get('{B}', ('rot', 0)))
        c_val = get_source_bit(in_bits, bit_idx, trans_dict.get('{C}', ('rot', 0)))
        
        # mask=1 since we are operating on single bits
        res = evaluator(a_val, b_val, c_val, 1)
        if res != expected:
            return False
    return True

# 2. Dynamic Universal Grammar Generator (Yields abstract truth tables as it searches)
def generate_grammar_dynamically():
    mask = 255
    l0 = {
        0: ("C0", lambda a, b, c, m: 0),
        255: ("C1", lambda a, b, c, m: m),
        0b11110000: ("{A}", lambda a, b, c, m: a),
        0b11001100: ("{B}", lambda a, b, c, m: b),
        0b10101010: ("{C}", lambda a, b, c, m: c)
    }
    visited = set(l0.keys())
    levels = [l0]
    
    # Yield Level 0 immediately
    for tt, (expr, func) in l0.items():
        yield tt, expr, func
        
    for depth in range(1, 4): # depth 1, 2, 3
        next_level = {}
        
        # NOT
        for v, (expr, func) in levels[-1].items():
            not_v = (~v) & mask
            if not_v not in visited:
                new_expr = f"NOT({expr})"
                new_func = lambda a, b, c, m, f=func: (~f(a, b, c, m)) & m
                visited.add(not_v)
                next_level[not_v] = (new_expr, new_func)
                yield not_v, new_expr, new_func
                
        # 2-Input OPS
        for i in range(depth):
            j = depth - 1
            for v1, (expr1, func1) in levels[i].items():
                for v2, (expr2, func2) in levels[j].items():
                    for op_name, op_func in OPS.items():
                        # Skip symmetric duplicates
                        if i == j and v1 > v2 and op_name in ['AND', 'OR', 'XOR', 'NAND', 'NOR', 'XNOR']: 
                            continue
                            
                        val = op_func(v1, v2) & mask
                        if val not in visited:
                            new_expr = f"{op_name}({expr1}, {expr2})"
                            new_func = lambda a, b, c, m, f1=func1, f2=func2, op=op_func: op(f1(a, b, c, m), f2(a, b, c, m)) & m
                            visited.add(val)
                            next_level[val] = (new_expr, new_func)
                            yield val, new_expr, new_func
                            
                        # If asymmetric and levels are different, test reverse order
                        if i != j:
                            val2 = op_func(v2, v1) & mask
                            if val2 not in visited:
                                new_expr = f"{op_name}({expr2}, {expr1})"
                                new_func = lambda a, b, c, m, f1=func1, f2=func2, op=op_func: op(f2(a, b, c, m), f1(a, b, c, m)) & m
                                visited.add(val2)
                                next_level[val2] = (new_expr, new_func)
                                yield val2, new_expr, new_func
        levels.append(next_level)

def format_hyp(expr, trans_dict):
    s = expr
    for k, v in trans_dict.items():
        s = s.replace(k, str(v))
    return s

def solve_dfs_trace_dynamic(in_arrays, out_arrays, num_examples):
    trace = []
    start_time = time.time()
    
    # 3. Interleave Grammar Generation with Backtracking
    grammar_gen = generate_grammar_dynamically()
    
    for tt, expr, evaluator in grammar_gen:
        if time.time() - start_time > 5.0:
            trace.append("TIMEOUT")
            return trace, None
            
        used = get_used_vars(expr)
        
        # Instantiate this abstract function with all possible unique shifts
        combinations = []
        if len(used) == 0:
            combinations.append({})
        elif len(used) == 1:
            for t1 in TRANSFORMATIONS:
                combinations.append({used[0]: t1})
        elif len(used) == 2:
            for t1 in TRANSFORMATIONS:
                for t2 in TRANSFORMATIONS:
                    if t1 == t2: continue
                    combinations.append({used[0]: t1, used[1]: t2})
        elif len(used) == 3:
            for t1, t2, t3 in itertools.permutations(TRANSFORMATIONS, 3):
                combinations.append({used[0]: t1, used[1]: t2, used[2]: t3})
                
        # Now perform Sudoku-style backtracking on these concrete hypotheses
        for trans_dict in combinations:
            if time.time() - start_time > 5.0:
                trace.append("TIMEOUT")
                return trace, None
                
            # Test Bit 0 first (Fail fast)
            if evaluate_bit(evaluator, trans_dict, 0, in_arrays, out_arrays, num_examples):
                hyp_str = format_hyp(expr, trans_dict)
                trace.append(f"B0: Testing {hyp_str} -> YES")
                
                valid_global = True
                # Sequentially verify the rest of the bits
                for b in range(1, 8):
                    if evaluate_bit(evaluator, trans_dict, b, in_arrays, out_arrays, num_examples):
                        trace.append(f"B{b}: Testing {hyp_str} -> YES")
                    else:
                        trace.append(f"B{b}: Testing {hyp_str} -> NO. Contradiction, backtracking...")
                        valid_global = False
                        break # BACKTRACK!
                        
                if valid_global:
                    trace.append(f"GLOBAL MATCH FOUND: {hyp_str}")
                    def predictor(q_in, trans_dict=dict(trans_dict), ev=evaluator):
                        a_val = get_source_bit(q_in, 0, trans_dict.get('{A}', ('rot', 0))) # Not used but avoids binding issues
                        res = []
                        for b_idx in range(8):
                            av = get_source_bit(q_in, b_idx, trans_dict.get('{A}', ('rot', 0)))
                            bv = get_source_bit(q_in, b_idx, trans_dict.get('{B}', ('rot', 0)))
                            cv = get_source_bit(q_in, b_idx, trans_dict.get('{C}', ('rot', 0)))
                            res.append(str(ev(av, bv, cv, 1)))
                        return "".join(res)
                    return trace, predictor
                    
    trace.append("NO MATCH FOUND")
    return trace, None

if __name__ == "__main__":
    df = pd.read_csv('bit_samples_30.csv')
    num_correct = 0
    num_found = 0
    
    for idx, row in df.iterrows():
        p = row['prompt']
        a = str(row['answer']).strip().zfill(8)
        ex_matches = re.findall(r'([01]{8})\s*->\s*([01]{8})', p)
        num_examples = len(ex_matches)
        in_arrays = [[int(ex_matches[ex][0][j]) for j in range(8)] for ex in range(num_examples)]
        out_arrays = [[int(ex_matches[ex][1][j]) for j in range(8)] for ex in range(num_examples)]
        
        query_match = re.search(r'(?:output for:|determine the output for:)\s*([01]{8})', p)
        query_in = [int(b) for b in query_match.group(1)]
        
        print(f"\nSample {idx} (ID: {row['id']}):")
        trace, predictor = solve_dfs_trace_dynamic(in_arrays, out_arrays, num_examples)
        
        if len(trace) > 10:
            print("\n".join(trace[:5]))
            print("...")
            print("\n".join(trace[-5:]))
        else:
            print("\n".join(trace))
            
        if predictor:
            num_found += 1
            pred_str = predictor(query_in)
            is_correct = (pred_str == a)
            if is_correct: num_correct += 1
            print(f"Pred: {pred_str} | Ans: {a} | Correct: {is_correct}")
        else:
            print("FAILED TO FIND RULE")
            
    print(f"\nRules found: {num_found}/30")
    print(f"Correct predictions: {num_correct}/30 ({(num_correct/30)*100:.1f}%)")
