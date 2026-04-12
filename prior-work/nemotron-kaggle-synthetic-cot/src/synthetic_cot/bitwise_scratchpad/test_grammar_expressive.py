import pandas as pd
import re
import time
import itertools

# ==========================================
# 1. Define ALL Operations in ONE Place
# ==========================================

# Base 2-input boolean operations
OPS = {
    'AND': lambda a, b: a & b,
    'OR': lambda a, b: a | b,
    'XOR': lambda a, b: a ^ b,
}

# ==========================================
# 2. Universal Grammar Generator
# ==========================================

def generate_grammar_3vars():
    """
    Generates a universal grammar using the single source of truth OPS dictionary up to Depth 3.
    Memoizes on the abstract 8-bit truth table for 3 variables (A, B, C).
    Returns dict mapping truth table value -> (string_expression, evaluator_function)
    """
    mask = 255
    l0 = {
        0: ("C0", lambda a, b, c, m: 0),
        255: ("C1", lambda a, b, c, m: m),
        0b11110000: ("{A}", lambda a, b, c, m: a),
        0b11001100: ("{B}", lambda a, b, c, m: b),
        0b10101010: ("{C}", lambda a, b, c, m: c)
    }
    visited = dict(l0)
    levels = [l0]
    
    for depth in range(1, 4): # depth 1, 2, 3
        next_level = {}
        
        # 1-Input (NOT)
        for v, (expr, func) in levels[-1].items():
            not_v = (~v) & mask
            if not_v not in visited:
                new_expr = f"NOT({expr})"
                new_func = lambda a, b, c, m, f=func: (~f(a, b, c, m)) & m
                visited[not_v] = (new_expr, new_func)
                next_level[not_v] = (new_expr, new_func)
                
        # 2-Input (OPS)
        for i in range(depth):
            j = depth - 1
            for v1, (expr1, func1) in levels[i].items():
                for v2, (expr2, func2) in levels[j].items():
                    for op_name, op_func in OPS.items():
                        # Optimization: Skip symmetric duplicates
                        if i == j and v1 > v2 and op_name in ['AND', 'OR', 'XOR', 'NAND', 'NOR', 'XNOR']: 
                            continue
                            
                        val = op_func(v1, v2) & mask
                        if val not in visited:
                            new_expr = f"{op_name}({expr1}, {expr2})"
                            new_func = lambda a, b, c, m, f1=func1, f2=func2, op=op_func: op(f1(a, b, c, m), f2(a, b, c, m)) & m
                            visited[val] = (new_expr, new_func)
                            next_level[val] = (new_expr, new_func)
                            
                        # If asymmetric and levels are different, test reverse order
                        if i != j:
                            val2 = op_func(v2, v1) & mask
                            if val2 not in visited:
                                new_expr = f"{op_name}({expr2}, {expr1})"
                                new_func = lambda a, b, c, m, f1=func1, f2=func2, op=op_func: op(f2(a, b, c, m), f1(a, b, c, m)) & m
                                visited[val2] = (new_expr, new_func)
                                next_level[val2] = (new_expr, new_func)
                                
        levels.append(next_level)
    return visited

print("Generating grammar...")
AST_DICT = generate_grammar_3vars()
print(f"Generated {len(AST_DICT)} unique abstract truth tables up to depth 3.")

# ==========================================
# 3. Solver & Evaluator
# ==========================================

def compute_empirical_vector(in_arrays, t, num_examples):
    val = 0
    ttype, k = t
    for ex in range(num_examples):
        for b in range(8):
            if ttype == 'rot':
                src = (b + k) % 8
                bit = in_arrays[ex][src]
            elif ttype == 'shl':
                src = b + k
                bit = in_arrays[ex][src] if 0 <= src < 8 else 0
            elif ttype == 'shr':
                src = b - k
                bit = in_arrays[ex][src] if 0 <= src < 8 else 0
            val = (val << 1) | bit
    return val

def get_target_vector(out_arrays, num_examples):
    val = 0
    for ex in range(num_examples):
        for b in range(8):
            val = (val << 1) | out_arrays[ex][b]
    return val

TRANSFORMATIONS = [('rot', 0)]
for k in range(1, 8):
    TRANSFORMATIONS.extend([('rot', k), ('shl', k), ('shr', k)])

def get_used_vars(expr):
    used = []
    if '{A}' in expr: used.append('{A}')
    if '{B}' in expr: used.append('{B}')
    if '{C}' in expr: used.append('{C}')
    return used

def solve_puzzle(in_arrays, out_arrays, num_examples):
    mask = (1 << (num_examples * 8)) - 1
    target_val = get_target_vector(out_arrays, num_examples)
    
    emp_vectors = {}
    for t in TRANSFORMATIONS:
        emp_vectors[t] = compute_empirical_vector(in_arrays, t, num_examples)
        
    start_time = time.time()
        
    for tt, (expr, evaluator) in AST_DICT.items():
        if time.time() - start_time > 3.0:
            return "TIMEOUT", None
            
        used = get_used_vars(expr)
        
        def search(var_idx, current_kwargs, current_trans):
            if var_idx == len(used):
                if evaluator(current_kwargs.get('{A}', 0), current_kwargs.get('{B}', 0), current_kwargs.get('{C}', 0), mask) == target_val:
                    rule_str = expr
                    for v, t in current_trans.items():
                        rule_str = rule_str.replace(v, str(t))
                        
                    def predictor(q_in, trans_dict=dict(current_trans), ev=evaluator):
                        kw = {'{A}':0, '{B}':0, '{C}':0}
                        for v, t in trans_dict.items():
                            kw[v] = compute_empirical_vector([q_in], t, 1)
                        return ev(kw['{A}'], kw['{B}'], kw['{C}'], 255)
                        
                    return rule_str, predictor
                return None, None
                
            var = used[var_idx]
            for t in TRANSFORMATIONS:
                if t in current_trans.values(): 
                    continue # variables must use distinct transformations
                    
                current_kwargs[var] = emp_vectors[t]
                current_trans[var] = t
                
                res_str, res_pred = search(var_idx + 1, current_kwargs, current_trans)
                if res_str:
                    return res_str, res_pred
                    
                del current_kwargs[var]
                del current_trans[var]
                
            return None, None
            
        res_str, res_pred = search(0, {}, {})
        if res_str:
            return res_str, res_pred
                    
    return "NO MATCH FOUND", None

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
        
        rule_str, predictor = solve_puzzle(in_arrays, out_arrays, num_examples)
        
        if predictor:
            num_found += 1
            pred_val = predictor(query_in)
            pred_str = format(pred_val, '08b')
            is_correct = (pred_str == a)
            if is_correct: num_correct += 1
            print(f"FOUND: {rule_str}")
            print(f"Pred: {pred_str} | Ans: {a} | Correct: {is_correct}")
        else:
            print(f"{rule_str}")

    print(f"\nRules found: {num_found}/30")
    print(f"Correct predictions: {num_correct}/30 ({(num_correct/30)*100:.1f}%)")