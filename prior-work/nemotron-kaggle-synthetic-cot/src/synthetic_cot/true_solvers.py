import numpy as np
import re
import itertools
from collections import Counter, defaultdict

# =============================================================================
# NUMERAL SYSTEM (ROMAN)
# =============================================================================

def solve_roman(prompt: str):
    m = re.search(r'Now, write the number (\d+)', prompt)
    if not m: return None, ""
    n = int(m.group(1))
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    sym = ['M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I']
    
    result = ''
    for v, s in zip(val, sym):
        while n >= v:
            result += s
            n -= v
    return result, ""

# =============================================================================
# PHYSICS GRAVITY
# =============================================================================

def solve_physics(prompt: str):
    pairs = re.findall(r't\s*=\s*([\d.]+)s.*?distance\s*=\s*([\d.]+)\s*m', prompt)
    if not pairs: return None, ""
    
    gs = [2*float(d)/float(t)**2 for t, d in pairs]
    g_avg = np.mean(gs)
    
    m = re.search(r'for t\s*=\s*([\d.]+)s', prompt.split('Now,')[-1])
    if not m: return None, ""
    t_q = float(m.group(1))
    answer_val = round(0.5 * g_avg * t_q**2, 2)
    return f"{answer_val:.2f}", ""

# =============================================================================
# UNIT CONVERSION
# =============================================================================

def solve_unit(prompt: str):
    pairs = re.findall(r'([\d.]+)\s*m\s+becomes\s+([\d.]+)', prompt)
    if not pairs: return None, ""
    
    ratios = [float(o)/float(i) for i, o in pairs if float(i) != 0]
    ratio_avg = np.mean(ratios)
    
    m = re.search(r'(?:convert the following measurement:|measurement:)\s*([\d.]+)', prompt)
    if not m:
        m = re.search(r'([\d.]+)\s*m\s*$', prompt.strip())
    if not m: return None, ""
    
    val_q = float(m.group(1))
    answer_val = round(val_q * ratio_avg, 2)
    return f"{answer_val:.2f}", ""

# =============================================================================
# TEXT CIPHER
# =============================================================================

def solve_cipher(prompt: str):
    lines = [l.strip() for l in prompt.split('\n') if '->' in l]
    letter_map = {}
    for line in lines:
        parts = line.split('->')
        if len(parts) != 2: continue
        for cw, pw in zip(parts[0].split(), parts[1].split()):
            if len(cw) == len(pw):
                for cc, pc in zip(cw, pw):
                    letter_map[cc] = pc
                    
    m = re.search(r'decrypt the following text: (.+)', prompt)
    if not m: return None, ""
    query = m.group(1).strip()
    
    decoded = ''
    unknown = 0
    for ch in query:
        if ch == ' ':
            decoded += ' '
        elif ch in letter_map:
            decoded += letter_map[ch]
        else:
            decoded += '?'
            unknown += 1
            
    if unknown > 1:
        return None, ""
    return decoded.replace('?', ''), ""

# =============================================================================
# BIT MANIPULATION (Full Logic from bit-manipulation-solver-cot-generator.py)
# =============================================================================

FUNC_1 = [("ID", lambda a: a), ("NOT", lambda a: 1 - a)]
FUNC_2_ORIG = [
    ("AND", lambda a, b: a & b), ("OR", lambda a, b: a | b), ("XOR", lambda a, b: a ^ b),
    ("NAND", lambda a, b: 1 - (a & b)), ("NOR", lambda a, b: 1 - (a | b)), ("XNOR", lambda a, b: 1 - (a ^ b)),
]
FUNC_2_DICT = {n: f for n, f in FUNC_2_ORIG}
FUNC_2_ASYM = [
    ("INHIB", lambda a, b: a & (1 - b)),
    ("IMPL", lambda a, b: (1 - a) | b),
]
FUNC_3 = [
    ("MAJ", lambda a, b, c: 1 if (a + b + c) >= 2 else 0),
    ("CH", lambda a, b, c: (a & b) | ((1 - a) & c)),
    ("XOR3", lambda a, b, c: a ^ b ^ c),
]
OP_PRIOR = {
    "ID": 40.2, "AND": 14.7, "XOR": 8.1, "XNOR": 7.3, "OR": 7.3,
    "NOR": 5.8, "NOT": 5.0, "NAND": 3.4, "MAJ": 0.8, "CH": 0.5,
    "XOR3": 0.5, "C0": 0.3, "C1": 0.3, "INHIB": 2.0, "IMPL": 1.5
}

def bits(s): return [int(b) for b in s]

def get_cands(ai, ao, qb, op):
    n = len(ai); tgt = [ao[e][op] for e in range(n)]; cs = []
    if all(t == 0 for t in tgt): cs.append(("C0", (), 0, 0))
    if all(t == 1 for t in tgt): cs.append(("C1", (), 1, 0))
    for ip in range(8):
        src = [ai[e][ip] for e in range(n)]
        for fn, f in FUNC_1:
            if [f(s) for s in src] == tgt:
                cs.append((fn, (ip,), f(qb[ip]), 1 if fn == "ID" else 2))
    for i1 in range(8):
        for i2 in range(i1 + 1, 8):
            s1 = [ai[e][i1] for e in range(n)]; s2 = [ai[e][i2] for e in range(n)]
            for fn, f in FUNC_2_ORIG:
                if [f(a, b) for a, b in zip(s1, s2)] == tgt:
                    cs.append((fn, (i1, i2), f(qb[i1], qb[i2]), 3))
    for i1 in range(8):
        for i2 in range(8):
            if i1 == i2: continue
            s1 = [ai[e][i1] for e in range(n)]; s2 = [ai[e][i2] for e in range(n)]
            for fn, f in FUNC_2_ASYM:
                if [f(a, b) for a, b in zip(s1, s2)] == tgt:
                    cs.append((fn, (i1, i2), f(qb[i1], qb[i2]), 3))
    if not cs:
        for i1 in range(8):
            for i2 in range(i1 + 1, 8):
                for i3 in range(i2 + 1, 8):
                    s1 = [ai[e][i1] for e in range(n)]; s2 = [ai[e][i2] for e in range(n)]; s3 = [ai[e][i3] for e in range(n)]
                    for fn, f in FUNC_3:
                        if [f(a, b, c) for a, b, c in zip(s1, s2, s3)] == tgt:
                            cs.append((fn, (i1, i2, i3), f(qb[i1], qb[i2], qb[i3]), 4))
    return cs

def resolve_phases12(all_cands):
    result = [None] * 8; conf = [0] * 8
    for op in range(8):
        vals = set(c[2] for c in all_cands[op])
        if len(vals) == 1:
            result[op] = list(vals)[0]; conf[op] = 1
        elif not vals: result[op] = 0
    shift_ev = Counter(); pair_ev = Counter(); perm = {}
    for op in range(8):
        for c in all_cands[op]:
            is_conf = (conf[op] == 1 and c[2] == result[op])
            w = 5 if is_conf else 1
            if c[0] in ("ID", "NOT") and len(c[1]) == 1:
                shift_ev[(c[1][0] - op) % 8] += w
                if is_conf: perm[op] = c[1][0]
            elif len(c[1]) == 2 and (conf[op] != 1 or c[2] == result[op]):
                s1 = (c[1][0] - op) % 8; s2 = (c[1][1] - op) % 8
                pair_ev[(min(s1, s2), max(s1, s2), c[0])] += w
    top_shifts = shift_ev.most_common(2)
    dom_pair = pair_ev.most_common(1)[0] if pair_ev else None
    ambig = [i for i in range(8) if result[i] is None]
    for op in ambig:
        cands = all_cands[op]
        if not cands: result[op] = 0; continue
        resolved = False
        for shift, sw in top_shifts:
            if sw < 5: break
            esrc = (op + shift) % 8
            sc = [c for c in cands if c[0] in ("ID", "NOT") and len(c[1]) == 1 and c[1][0] == esrc]
            if sc:
                vals = set(c[2] for c in sc)
                if len(vals) == 1:
                    result[op] = list(vals)[0]; conf[op] = 2; perm[op] = esrc; resolved = True; break
        if resolved: continue
        if len(perm) >= 4:
            missing = set(range(8)) - set(perm.values())
            pc = [c for c in cands if c[0] in ("ID", "NOT") and len(c[1]) == 1 and c[1][0] in missing]
            if pc:
                vals = set(c[2] for c in pc)
                if len(vals) == 1: result[op] = list(vals)[0]; conf[op] = 2; perm[op] = pc[0][1][0]
    return result, conf, shift_ev, pair_ev, perm

def score_v14(pred, all_cands, perm_fixed, dom_shift, dom_shift_cnt, dom_pair):
    sc = 0; chosen = []; perm = dict(perm_fixed)
    for op in range(8):
        pv = pred[op]; supp = [c for c in all_cands[op] if c[2] == pv]
        if not supp: sc -= 100; chosen.append(None); continue
        supp.sort(key=lambda c: -OP_PRIOR.get(c[0], 0))
        best = supp[0]; chosen.append(best)
        sc += OP_PRIOR.get(best[0], 0) * 0.5 + max(0, (5 - best[3])) * 3
        if best[0] in ("ID", "NOT") and len(best[1]) == 1: perm[op] = best[1][0]
    op_names = [c[0] for c in chosen if c]
    if op_names:
        if len(set(op_names)) <= 2: sc += 12
        if len(set(op_names)) == 1: sc += 8
    np_ = len(perm)
    if np_ == 8 and len(set(perm.values())) == 8: sc += 35
    if dom_shift is not None and dom_shift_cnt >= 3:
        sc += sum(1 for op, src in perm.items() if (src - op) % 8 == dom_shift) * 3
    return sc

def _format_cand(c):
    fn, inputs, val, complexity = c
    if not inputs: return f"{fn}"
    elif len(inputs) == 1: return f"{fn}(in[{inputs[0]}])"
    elif len(inputs) == 2: return f"{fn}(in[{inputs[0]}], in[{inputs[1]}])"
    elif len(inputs) == 3: return f"{fn}(in[{inputs[0]}], in[{inputs[1]}], in[{inputs[2]}])"
    return fn

def solve_bit_manipulation(prompt: str):
    ex = re.findall(r'([01]{8})\s*->\s*([01]{8})', prompt)
    m = re.search(r'determine the output for:\s*([01]{8})', prompt)
    if not ex or not m: return None, ""
    query = m.group(1); qb = bits(query)
    
    ai = [bits(i) for i, _ in ex]; ao = [bits(o) for _, o in ex]
    all_cands = [get_cands(ai, ao, qb, op) for op in range(8)]
    result, conf, shift_ev, pair_ev, perm = resolve_phases12(all_cands)
    
    still = [i for i in range(8) if result[i] is None]
    if still:
        possible = [list(set(c[2] for c in all_cands[i])) if all_cands[i] else [0, 1] for i in still]
        top_shifts = shift_ev.most_common(1)
        dsv = top_shifts[0][0] if top_shifts else None; dsc = top_shifts[0][1] if top_shifts else 0
        dom_pair = pair_ev.most_common(1)[0] if pair_ev else None
        scored = []
        for combo in itertools.product(*possible):
            pred = list(result)
            for i, bi in enumerate(still): pred[bi] = combo[i]
            sc = score_v14(pred, all_cands, perm, dsv, dsc, dom_pair)
            scored.append((sc, pred))
        scored.sort(key=lambda x: -x[0])
        final_bits = scored[0][1]
    else:
        final_bits = result
        
    answer = "".join(str(b) for b in final_bits)
    
    lines = ["I need to find the bit transformation rule from the examples.", ""]
    for op in range(8):
        cands = all_cands[op]
        if not cands:
            lines.append(f"  Bit {op}: No rule found, defaulting to 0.")
        else:
            best = sorted(cands, key=lambda c: (-OP_PRIOR.get(c[0], 0), c[3]))[0]
            lines.append(f"  Bit {op}: Rule={best[0]}, Input bits={best[1]} -> result={final_bits[op]}")
            
    cot = "\n".join(lines) + f"\n\nThe answer is {answer}."
    return answer, cot

# Helper map
TRUE_SOLVER_MAP = {
    'Gravity': solve_physics,
    'Unit Conversion': solve_unit,
    'Base Conversion': solve_roman,
    'Text Encryption': solve_cipher,
    'Bit Manipulation': solve_bit_manipulation
}
