import sys
import time
from typing import Any
from z3 import Solver, Int, Distinct, And, Or, If, sat

SYMBOL_UNIVERSE = ['!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', ':', '<', '=', '>', '?', '@', '[', '\\', ']', '^', '_', '`', '{', '|', '}', '~']

MATH_OPS = {
    'add': {'sym': '+'}, 'sub': {'sym': '-'}, 'mul': {'sym': '*'},
    'cat': {'sym': '||'}, 'max_mod_min': {'sym': ''}, 'add1': {'sym': ''},
    'addm1': {'sym': '-'}, 'mul1': {'sym': ''}, 'mulm1': {'sym': '-'},
    'sub_abs': {'sym': ''}, 'sub_neg_abs': {'sym': '-'}
}

def make_num(digits):
    if not digits: return 0
    return sum(d * (10**(len(digits)-1-i)) for i, d in enumerate(digits))

solver = Solver()
digit_syms = ['[', ']', '-', '!', "'"] # From 00457d26
digit_vars = {s: Int(s) for s in digit_syms}
for var in digit_vars.values():
    solver.add(And(var >= 0, var <= 9))
solver.add(Distinct(*list(digit_vars.values())))

# Eq: [[ - !' = ?
L = digit_vars['['] * 10 + digit_vars['[']
R = digit_vars['!'] * 10 + digit_vars["'"]

# Let's say operator is sub ('-')
eq_val = L - R
m_sym = '-'
out_syms = ['?'] # wait, the prompt doesn't give the output, the target is the query!
