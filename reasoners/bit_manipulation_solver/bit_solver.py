import itertools
import time

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

def solve_bit_manipulation(prompt: str) -> str | None:
    import re
    ex_matches = re.findall(r'([01]{8})\s*->\s*([01]{8})', prompt)
    if not ex_matches:
        return None
    query_match = re.search(r'(?:output for:|determine the output for:)\s*([01]{8})', prompt)
    if not query_match:
        return None

    query_str = query_match.group(1)
    target_bits = [int(b) for b in query_str]
    num_examples = len(ex_matches)
    in_arrays = [[int(ex_matches[ex][0][j]) for j in range(8)] for ex in range(num_examples)]
    out_arrays = [[int(ex_matches[ex][1][j]) for j in range(8)] for ex in range(num_examples)]

    start_time = time.time()
    grammar_gen = generate_grammar_dynamically()

    for tt, node in grammar_gen:
        if time.time() - start_time > 15.0:
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
                    if t1 == t2:
                        continue
                    combinations.append({used[0]: t1, used[1]: t2})
        elif len(used) == 3:
            for t1, t2, t3 in itertools.permutations(TRANSFORMATIONS, 3):
                combinations.append({used[0]: t1, used[1]: t2, used[2]: t3})

        for trans_dict in combinations:
            if time.time() - start_time > 15.0:
                break

            if all(evaluate_example(node, trans_dict, ex, in_arrays, out_arrays) for ex in range(num_examples)):
                res = []
                for b_idx in range(8):
                    av = get_source_bit(target_bits, b_idx, trans_dict.get('{A}', ('rot', 0)))
                    bv = get_source_bit(target_bits, b_idx, trans_dict.get('{B}', ('rot', 0)))
                    cv = get_source_bit(target_bits, b_idx, trans_dict.get('{C}', ('rot', 0)))
                    res.append(str(evaluate_ast(node, av, bv, cv, 1)))
                return "".join(res)

    return None
