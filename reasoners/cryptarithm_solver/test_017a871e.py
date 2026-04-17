import itertools
import sys
WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path: sys.path.append(WORKSPACE_DIR)
from reasoners.cryptarithm_solver.constraint_solver import PRE_OPS, MID_OPS, check_post

def make_num(digits):
    return sum(d * (10**(len(digits)-1-i)) for i, d in enumerate(digits))

syms = ['\\', '!', '^', '{', '"', ']', '#', ':']

parsed = [
    (['#', ']'], '+', ['\\', '#'], ['"', '!'], False),
    (['#', '^'], '-', ['{', ']'], [']', '#'], False),
    (['\\', '{'], '*', ['\\', '!'], ['#', '\\', '^', ':'], False)
]

for p in itertools.permutations(range(10), 8):
    m = dict(zip(syms, p))
    
    for perm_name, pre_func in PRE_OPS.items():
        for f_name in ['raw', 'rev', 'swap']:
            # To speed up, check if operations exist for these pairs
            # But the operators could be ANY of the 31!
            # Let's see if there is ANY operator that works for Eq1
            
            L1, R1, d1_1, d2_1, d3_1, d4_1 = pre_func([m[s] for s in parsed[0][0]], [m[s] for s in parsed[0][2]])
            out1 = [m[s] for s in parsed[0][3]]
            valid_ops_1 = []
            for op_name, op_func in MID_OPS.items():
                try:
                    res = op_func(L1, R1, d1_1, d2_1, d3_1, d4_1)
                    if check_post(res, out1, f_name, parsed[0][4]):
                        valid_ops_1.append(op_name)
                except: pass
            if not valid_ops_1: continue
            
            L2, R2, d1_2, d2_2, d3_2, d4_2 = pre_func([m[s] for s in parsed[1][0]], [m[s] for s in parsed[1][2]])
            out2 = [m[s] for s in parsed[1][3]]
            valid_ops_2 = []
            for op_name, op_func in MID_OPS.items():
                try:
                    res = op_func(L2, R2, d1_2, d2_2, d3_2, d4_2)
                    if check_post(res, out2, f_name, parsed[1][4]):
                        valid_ops_2.append(op_name)
                except: pass
            if not valid_ops_2: continue
            
            L3, R3, d1_3, d2_3, d3_3, d4_3 = pre_func([m[s] for s in parsed[2][0]], [m[s] for s in parsed[2][2]])
            out3 = [m[s] for s in parsed[2][3]]
            valid_ops_3 = []
            for op_name, op_func in MID_OPS.items():
                try:
                    res = op_func(L3, R3, d1_3, d2_3, d3_3, d4_3)
                    if check_post(res, out3, f_name, parsed[2][4]):
                        valid_ops_3.append(op_name)
                except: pass
            if not valid_ops_3: continue
            
            print(f"FOUND SOLUTION: {m}")
            print(f"Perm: {perm_name}, Fmt: {f_name}")
            print(f"Ops: Eq1={valid_ops_1}, Eq2={valid_ops_2}, Eq3={valid_ops_3}")
            sys.exit(0)

