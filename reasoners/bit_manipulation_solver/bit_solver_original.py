import re
import itertools
import time
from decimal import Decimal, ROUND_HALF_UP

SOLVER_PREAMBLE = """To solve this problem accurately, I must strictly follow the rules and the template."""

def _get_solver_rules(template_type, template_desc, not_list_str, rule2_name=None, rule3_extra="", include_other_suffix=True, use_because=True):
    if rule2_name is None:
        rule2_name = template_type.replace("letter substitution ", "")
        
    because_str = " I know this because " if use_because else " "
    
    rules = f"""{SOLVER_PREAMBLE}

RULE 1: Identify the question type to select the correct template. This is a {template_type} template.{because_str}{template_desc}. It is NOT {not_list_str}{", or any other conversion type" if include_other_suffix else ""}."""
    
    rules += f"""

RULE 2: Ignore any flavor text (e.g., Alice in Wonderland). Only focus on the problem logic.

RULE 3: The final answer MUST be enclosed in \\boxed{{}} at the end.{' ' + rule3_extra if rule3_extra else ""}"""
    return rules

OPS = {
    'AND': lambda a, b: a & b,
    'OR': lambda a, b: a | b,
    'XOR': lambda a, b: a ^ b,
}

def generate_grammar_dynamically():
    mask = 255
    l0 = {
        0: ('C0',),
        255: ('C1',),
        0b11110000: ('VAR', '{A}'),
        0b11001100: ('VAR', '{B}'),
        0b10101010: ('VAR', '{C}')
    }
    visited = set(l0.keys())
    levels = [l0]
    
    for tt, node in l0.items():
        yield tt, node
        
    for depth in range(1, 4):
        next_level = {}
        for v, node in levels[-1].items():
            not_v = (~v) & mask
            if not_v not in visited:
                new_node = ('NOT', node)
                visited.add(not_v)
                next_level[not_v] = new_node
                yield not_v, new_node
                
        for i in range(depth):
            j = depth - 1
            for v1, node1 in levels[i].items():
                for v2, node2 in levels[j].items():
                    for op_name, op_func in OPS.items():
                        if i == j and v1 > v2 and op_name in ['AND', 'OR', 'XOR', 'NAND', 'NOR', 'XNOR']: 
                            continue
                        val = op_func(v1, v2) & mask
                        if val not in visited:
                            new_node = ('OP', op_name, node1, node2)
                            visited.add(val)
                            next_level[val] = new_node
                            yield val, new_node
                        if i != j:
                            val2 = op_func(v2, v1) & mask
                            if val2 not in visited:
                                new_node = ('OP', op_name, node2, node1)
                                visited.add(val2)
                                next_level[val2] = new_node
                                yield val2, new_node
        levels.append(next_level)

def evaluate_ast(node, a, b, c, m):
    if node[0] == 'C0': return 0
    elif node[0] == 'C1': return m
    elif node[0] == 'VAR': 
        if node[1] == '{A}': return a
        elif node[1] == '{B}': return b
        elif node[1] == '{C}': return c
    elif node[0] == 'NOT':
        return (~evaluate_ast(node[1], a, b, c, m)) & m
    elif node[0] == 'OP':
        op_name = node[1]
        v1 = evaluate_ast(node[2], a, b, c, m)
        v2 = evaluate_ast(node[3], a, b, c, m)
        return OPS[op_name](v1, v2) & m

def format_expr(node, trans_dict):
    if node[0] == 'C0': return "C0"
    elif node[0] == 'C1': return "C1"
    elif node[0] == 'VAR':
        t = trans_dict.get(node[1], ('rot', 0))
        return f"{t[0]}_{t[1]}"
    elif node[0] == 'NOT':
        return f"NOT({format_expr(node[1], trans_dict)})"
    elif node[0] == 'OP':
        return f"{node[1]}({format_expr(node[2], trans_dict)}, {format_expr(node[3], trans_dict)})"

def get_used_vars(node):
    if node[0] in ['C0', 'C1']: return []
    elif node[0] == 'VAR': return [node[1]]
    elif node[0] == 'NOT': return get_used_vars(node[1])
    elif node[0] == 'OP':
        used = get_used_vars(node[2]) + get_used_vars(node[3])
        return list(dict.fromkeys(used))

TRANSFORMATIONS = [('rot', 0)]
for k in range(1, 8):
    TRANSFORMATIONS.extend([('rot', k), ('shl', k), ('shr', k)])

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

def evaluate_example_with_trace(node, trans_dict, ex, in_arrays, out_arrays):
    trace_lines = []
    
    hyp_str = format_expr(node, trans_dict)
    
    in_bits = in_arrays[ex]
    in_str = "".join(map(str, in_bits))
    
    # Replace variables with their values applied to the input string
    eval_str = hyp_str
    for var, v_name in [('{A}', 'a'), ('{B}', 'b'), ('{C}', 'c')]:
        if var in trans_dict:
            v_trans = trans_dict[var]
            if v_trans[0] == 'rot': t_str = f"rot_{v_trans[1]}"
            elif v_trans[0] == 'shl': t_str = f"shl_{v_trans[1]}"
            elif v_trans[0] == 'shr': t_str = f"shr_{v_trans[1]}"
            else: t_str = str(v_trans)
            eval_str = eval_str.replace(t_str, f"{t_str}({in_str})")
            
    out_str = "".join(map(str, out_arrays[ex]))
    trace_lines.append(f"Example {ex+1}: Testing {eval_str} =? {out_str}")
    
    for bit_idx in range(8):
        expected = out_arrays[ex][bit_idx]
        
        a_val = get_source_bit(in_bits, bit_idx, trans_dict.get('{A}', ('rot', 0)))
        b_val = get_source_bit(in_bits, bit_idx, trans_dict.get('{B}', ('rot', 0)))
        c_val = get_source_bit(in_bits, bit_idx, trans_dict.get('{C}', ('rot', 0)))
        
        res = evaluate_ast(node, a_val, b_val, c_val, 1)
        
        trace_lines.append(f"  Bit {bit_idx}: got = {res}, should = {expected}")
        
        if res != expected:
            trace_lines.append(f"  -> CONTRADICTION on Bit {bit_idx}. Backtracking...")
            return False, trace_lines
            
    trace_lines.append(f"  -> ALL MATCH FOR EXAMPLE {ex+1}")
    return True, trace_lines

def evaluate_example(node, trans_dict, ex, in_arrays, out_arrays):
    in_bits = in_arrays[ex]
    for bit_idx in range(8):
        expected = out_arrays[ex][bit_idx]
        
        a_val = get_source_bit(in_bits, bit_idx, trans_dict.get('{A}', ('rot', 0)))
        b_val = get_source_bit(in_bits, bit_idx, trans_dict.get('{B}', ('rot', 0)))
        c_val = get_source_bit(in_bits, bit_idx, trans_dict.get('{C}', ('rot', 0)))
        
        res = evaluate_ast(node, a_val, b_val, c_val, 1)
        if res != expected:
            return False
    return True

def solve_bit_manipulation(prompt: str):
    import re
    import time
    ex_matches = re.findall(r'([01]{8})\s*->\s*([01]{8})', prompt)
    if not ex_matches: return None, ""
    query_match = re.search(r'(?:output for:|determine the output for:)\s*([01]{8})', prompt)
    if not query_match: return None, ""
    
    query_str = query_match.group(1)
    target_bits = [int(b) for b in query_str]
    num_examples = len(ex_matches)
    in_arrays = [[int(ex_matches[ex][0][j]) for j in range(8)] for ex in range(num_examples)]
    out_arrays = [[int(ex_matches[ex][1][j]) for j in range(8)] for ex in range(num_examples)]
    
    rules = _get_solver_rules(
        "binary boolean decomposition",
        "I see 8-bit binary strings mapped to 8-bit binary strings. Each output bit is an independent boolean function of the input bits",
        "roman, unit conversion, gravity, symbol-digit, or cipher-digit",
        rule2_name="binary",
        include_other_suffix=False,
        use_because=False,
        rule3_extra="" 
    )
    
    rule4 = "RULE 4: For gate computations, I MUST spell out each bit operation individually. I CANNOT compute multi-bit results in parallel. AND(0,1): 1&0=0 0&1=0 1&1=1 -> one bit at a time."
    s1_text = "S1: This is a binary boolean decomposition template. Each output bit is an independent boolean function. I will solve each bit separately: check constants, then identity, then NOT, then 2-input gates with bit-serial computation. I am now going to fill out the template."
    
    in_cols = ["".join([ex[0][i] for ex in ex_matches]) for i in range(8)]
    out_cols = ["".join([ex[1][i] for ex in ex_matches]) for i in range(8)]
    s2_text = "S2: COLUMNS\\nIN: " + " ".join([f"i{i}={in_cols[i]}" for i in range(8)]) + "\\nOUT: " + " ".join([f"o{i}={out_cols[i]}" for i in range(8)]) + f"\\nTGT: {query_str}"
    
    solve_chunks = []
    ans_str = "00000000"
    
    start_time = time.time()
    grammar_gen = generate_grammar_dynamically()
    
    found_rule = False
    
    for tt, node in grammar_gen:
        if time.time() - start_time > 15.0:
            solve_chunks.append(["TIMEOUT"])
            break
            
        used = get_used_vars(node)
        
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
                
        for trans_dict in combinations:
            if time.time() - start_time > 15.0:
                solve_chunks.append(["TIMEOUT"])
                break
                
            if evaluate_example(node, trans_dict, 0, in_arrays, out_arrays):
                hyp_str = format_expr(node, trans_dict)
                hyp_trace = [f"testing op {hyp_str} for all bits in all examples ..."]
                valid_global = True
                
                success_traces = []
                for ex in range(num_examples):
                    success, ex_trace = evaluate_example_with_trace(node, trans_dict, ex, in_arrays, out_arrays)
                    
                    if not success:
                        valid_global = False
                        hyp_trace.extend(ex_trace)
                        break
                    else:
                        success_traces.extend(ex_trace)
                        
                if valid_global:
                    hyp_trace.extend(success_traces)
                    hyp_trace.append(f"GLOBAL MATCH FOUND: {hyp_str}")
                    solve_chunks.append(hyp_trace)
                    
                    res = []
                    for b_idx in range(8):
                        av = get_source_bit(target_bits, b_idx, trans_dict.get('{A}', ('rot', 0)))
                        bv = get_source_bit(target_bits, b_idx, trans_dict.get('{B}', ('rot', 0)))
                        cv = get_source_bit(target_bits, b_idx, trans_dict.get('{C}', ('rot', 0)))
                        res.append(str(evaluate_ast(node, av, bv, cv, 1)))
                    ans_str = "".join(res)
                    found_rule = True
                    break
                else:
                    solve_chunks.append(hyp_trace)
                    
        if found_rule:
            break
            
    if not found_rule:
        solve_chunks.append(["NO MATCH FOUND"])
    
    APPROX_TRACE_TOKENS = 1000
    TRACE_CHARS = 4000
    # Truncate trace chunks from the tail so the total length is < 4000 characters
    char_count = 0
    tail_chunks = []
    for chunk in reversed(solve_chunks):
        chunk_str = "\n".join(chunk)
        if char_count + len(chunk_str) > TRACE_CHARS and len(tail_chunks) > 0:
            break
        tail_chunks.insert(0, chunk)
        char_count += len(chunk_str) + 1
        
    solve_lines = []
    for chunk in tail_chunks:
        solve_lines.extend(chunk)
        
    cot = f"""{rules}

{rule4}

{s1_text}

{s2_text}

S3: SOLVE
{chr(10).join(solve_lines)[-TRACE_CHARS:]}

S4: ANS={ans_str}

\\boxed{{{ans_str}}}"""

    return ans_str, cot
