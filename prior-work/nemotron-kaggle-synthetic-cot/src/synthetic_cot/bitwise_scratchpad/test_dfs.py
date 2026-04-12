import pandas as pd
import re
import itertools
import sys

G2 = {
    'AND': lambda a, b: a & b, 'OR': lambda a, b: a | b, 'XOR': lambda a, b: a ^ b,
    'NAND': lambda a, b: 1 - (a & b), 'NOR': lambda a, b: 1 - (a | b), 'XNOR': lambda a, b: 1 - (a ^ b),
    'NOT_A_AND_B': lambda a, b: (1-a) & b, 'A_AND_NOT_B': lambda a, b: a & (1-b),
    'NOT_A_OR_B': lambda a, b: (1-a) | b, 'A_OR_NOT_B': lambda a, b: a | (1-b)
}

G3 = {
    'MAJ': lambda a, b, c: 1 if (a + b + c) >= 2 else 0,
    'CHO': lambda a, b, c: b if a == 1 else c,
    'PAR3': lambda a, b, c: a ^ b ^ c,
    'AO': lambda a, b, c: (a & b) | c,
    'OA': lambda a, b, c: (a | b) & c,
    'AX': lambda a, b, c: (a & b) ^ c,
    'OX': lambda a, b, c: (a | b) ^ c,
    'XA': lambda a, b, c: (a ^ b) & c,
    'XO': lambda a, b, c: (a ^ b) | c,
    'NOT_MAJ': lambda a, b, c: 1 - (1 if (a + b + c) >= 2 else 0),
    'NOT_CHO': lambda a, b, c: 1 - (b if a == 1 else c),
    'NOT_PAR3': lambda a, b, c: 1 - (a ^ b ^ c),
    'NOT_AO': lambda a, b, c: 1 - ((a & b) | c),
    'NOT_OA': lambda a, b, c: 1 - ((a | b) & c),
    'NOT_AX': lambda a, b, c: 1 - ((a & b) ^ c),
    'NOT_OX': lambda a, b, c: 1 - ((a | b) ^ c),
    'NOT_XA': lambda a, b, c: 1 - ((a ^ b) & c),
    'NOT_XO': lambda a, b, c: 1 - ((a ^ b) | c)
}

G4 = {
    'AOA': lambda a, b, c, d: (a & b) | (c & d),
    'OAO': lambda a, b, c, d: (a | b) & (c | d),
    'PAR4': lambda a, b, c, d: a ^ b ^ c ^ d,
    'XX': lambda a, b, c, d: (a ^ b) ^ (c ^ d),
    'AXA': lambda a, b, c, d: (a & b) ^ (c & d),
    'NOT_AOA': lambda a, b, c, d: 1 - ((a & b) | (c & d)),
    'NOT_OAO': lambda a, b, c, d: 1 - ((a | b) & (c | d)),
    'NOT_PAR4': lambda a, b, c, d: 1 - (a ^ b ^ c ^ d),
    'NOT_XX': lambda a, b, c, d: 1 - ((a ^ b) ^ (c ^ d)),
    'NOT_AXA': lambda a, b, c, d: 1 - ((a & b) ^ (c & d)),
    'A_AND_CHO': lambda a, b, c, d: a & (c if b == 1 else d),
    'A_OR_CHO': lambda a, b, c, d: a | (c if b == 1 else d),
    'A_XOR_CHO': lambda a, b, c, d: a ^ (c if b == 1 else d),
    'NOT_A_AND_CHO': lambda a, b, c, d: 1 - (a & (c if b == 1 else d)),
    'NOT_A_OR_CHO': lambda a, b, c, d: 1 - (a | (c if b == 1 else d)),
    'NOT_A_XOR_CHO': lambda a, b, c, d: 1 - (a ^ (c if b == 1 else d)),
    'CHO_AND_CHO': lambda a, b, c, d: (b if a == 1 else c) & d,
    'CHO_OR_CHO': lambda a, b, c, d: (b if a == 1 else c) | d,
    'CHO_XOR_CHO': lambda a, b, c, d: (b if a == 1 else c) ^ d,
    'NESTED_CHO': lambda a, b, c, d: c if (b if a == 1 else c) == 1 else d
}

# Exhaustive G2 Fallback (16 functions)
G2_FALLBACK = {}
for i in range(16):
    name = f"F2_{i:04b}"
    G2_FALLBACK[name] = (lambda tt: lambda a, b: (tt >> ((a << 1) | b)) & 1)(i)

TRANSFORMATIONS = [('rot', 0)]
for k in range(1, 8):
    TRANSFORMATIONS.extend([('rot', k), ('shl', k), ('shr', k)])

def get_source_bit(in_bits, out_idx, trans):
    ttype, shift_val = trans
    if ttype == 'rot':
        return in_bits[(out_idx + shift_val) % 8]
    elif ttype == 'shl':
        src_idx = out_idx + shift_val
        return in_bits[src_idx] if 0 <= src_idx < 8 else 0
    elif ttype == 'shr':
        src_idx = out_idx - shift_val
        return in_bits[src_idx] if 0 <= src_idx < 8 else 0

def check_hypothesis_for_bit(hypothesis, bit_idx, in_arrays, out_arrays, num_examples):
    htype, params = hypothesis
    for ex in range(num_examples):
        in_bits = in_arrays[ex]
        out_bit = out_arrays[ex][bit_idx]
        
        if htype == 'C0': res = 0
        elif htype == 'C1': res = 1
        elif htype == 'ID': res = get_source_bit(in_bits, bit_idx, params[0])
        elif htype == 'NOT': res = 1 - get_source_bit(in_bits, bit_idx, params[0])
        elif htype == 'G2':
            gn, t1, t2 = params
            res = G2[gn](get_source_bit(in_bits, bit_idx, t1), get_source_bit(in_bits, bit_idx, t2))
        elif htype == 'G3':
            gn, t1, t2, t3 = params
            res = G3[gn](get_source_bit(in_bits, bit_idx, t1), get_source_bit(in_bits, bit_idx, t2), get_source_bit(in_bits, bit_idx, t3))
        elif htype == 'G4':
            gn, t1, t2, t3, t4 = params
            res = G4[gn](get_source_bit(in_bits, bit_idx, t1), get_source_bit(in_bits, bit_idx, t2), get_source_bit(in_bits, bit_idx, t3), get_source_bit(in_bits, bit_idx, t4))
        elif htype == 'G2_FALLBACK':
            gn, t1, t2 = params
            res = G2_FALLBACK[gn](get_source_bit(in_bits, bit_idx, t1), get_source_bit(in_bits, bit_idx, t2))
            
        if res != out_bit:
            return False
    return True

def generate_hypotheses(bit_idx, in_arrays, out_arrays, num_examples):
    # Constants
    if check_hypothesis_for_bit(('C0', None), bit_idx, in_arrays, out_arrays, num_examples): yield ('C0', None)
    if check_hypothesis_for_bit(('C1', None), bit_idx, in_arrays, out_arrays, num_examples): yield ('C1', None)
    
    # Identity & NOT
    for t1 in TRANSFORMATIONS:
        if check_hypothesis_for_bit(('ID', (t1,)), bit_idx, in_arrays, out_arrays, num_examples): yield ('ID', (t1,))
        if check_hypothesis_for_bit(('NOT', (t1,)), bit_idx, in_arrays, out_arrays, num_examples): yield ('NOT', (t1,))
        
    # G2 Named
    for gn in G2:
        for t1 in TRANSFORMATIONS:
            for t2 in TRANSFORMATIONS:
                if t1 == t2: continue
                if check_hypothesis_for_bit(('G2', (gn, t1, t2)), bit_idx, in_arrays, out_arrays, num_examples):
                    yield ('G2', (gn, t1, t2))
                    
    # G3 Named
    for gn in G3:
        for t1, t2, t3 in itertools.permutations(TRANSFORMATIONS, 3):
            if check_hypothesis_for_bit(('G3', (gn, t1, t2, t3)), bit_idx, in_arrays, out_arrays, num_examples):
                yield ('G3', (gn, t1, t2, t3))
                
    # G4 Named
    for gn in G4:
        for t1, t2, t3, t4 in itertools.permutations(TRANSFORMATIONS, 4):
            if check_hypothesis_for_bit(('G4', (gn, t1, t2, t3, t4)), bit_idx, in_arrays, out_arrays, num_examples):
                yield ('G4', (gn, t1, t2, t3, t4))
                
    # G2 Exhaustive Fallback
    for gn in G2_FALLBACK:
        for t1 in TRANSFORMATIONS:
            for t2 in TRANSFORMATIONS:
                if t1 == t2: continue
                if check_hypothesis_for_bit(('G2_FALLBACK', (gn, t1, t2)), bit_idx, in_arrays, out_arrays, num_examples):
                    yield ('G2_FALLBACK', (gn, t1, t2))

def solve_dfs(in_arrays, out_arrays, num_examples):
    for hyp in generate_hypotheses(0, in_arrays, out_arrays, num_examples):
        valid_global = True
        for b in range(1, 8):
            if not check_hypothesis_for_bit(hyp, b, in_arrays, out_arrays, num_examples):
                valid_global = False
                break
        if valid_global:
            return hyp
    return None

def predict(hypothesis, in_bits):
    if not hypothesis: return None
    htype, params = hypothesis
    res = []
    for bit_idx in range(8):
        if htype == 'C0': r = 0
        elif htype == 'C1': r = 1
        elif htype == 'ID': r = get_source_bit(in_bits, bit_idx, params[0])
        elif htype == 'NOT': r = 1 - get_source_bit(in_bits, bit_idx, params[0])
        elif htype == 'G2':
            gn, t1, t2 = params
            r = G2[gn](get_source_bit(in_bits, bit_idx, t1), get_source_bit(in_bits, bit_idx, t2))
        elif htype == 'G3':
            gn, t1, t2, t3 = params
            r = G3[gn](get_source_bit(in_bits, bit_idx, t1), get_source_bit(in_bits, bit_idx, t2), get_source_bit(in_bits, bit_idx, t3))
        elif htype == 'G4':
            gn, t1, t2, t3, t4 = params
            r = G4[gn](get_source_bit(in_bits, bit_idx, t1), get_source_bit(in_bits, bit_idx, t2), get_source_bit(in_bits, bit_idx, t3), get_source_bit(in_bits, bit_idx, t4))
        elif htype == 'G2_FALLBACK':
            gn, t1, t2 = params
            r = G2_FALLBACK[gn](get_source_bit(in_bits, bit_idx, t1), get_source_bit(in_bits, bit_idx, t2))
        res.append(str(r))
    return "".join(res)

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
    target_bits = [int(b) for b in query_match.group(1)]
    
    rule = solve_dfs(in_arrays, out_arrays, num_examples)
    
    if rule:
        num_found += 1
        prediction = predict(rule, target_bits)
        is_correct = (prediction == a)
        if is_correct: num_correct += 1
        print(f"Sample {idx} (ID: {row['id']}): FOUND: {rule} | Pred: {prediction} | Ans: {a} | Correct: {is_correct}")
    else:
        print(f"Sample {idx} (ID: {row['id']}): NO GLOBAL MATCH FOUND")

print(f"\nRules found: {num_found}/30")
print(f"Correct predictions: {num_correct}/30 ({(num_correct/30)*100:.1f}%)")
