"""
Pure-Python drop-in for ortools_solver.py.

Same interface: solve_cipher_unified(prompt, mode, target_answer, log_path)

Algorithm: example-driven backtracking with inline op selection.
- For each example, try (A,B) digit assignments → compute result → for each plausible op,
  derive output symbol values directly (no branching on output)
- Op selection is pruned example-by-example (not pre-enumerated as combos)
- AllDifferent enforced via `used` set throughout
"""
from __future__ import annotations
import sys
import re
import time
from itertools import permutations as _permutations
from typing import Union

WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path:
    sys.path.append(WORKSPACE_DIR)

SYMBOL_UNIVERSE = [
    '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/',
    ':', '<', '=', '>', '?', '@', '[', '\\', ']', '^', '_', '`', '{', '|', '}', '~',
]

MATH_OPS = {
    'add':         {'fn': lambda L, R, d1, d2, d3, d4: L + R,                                                   'sym': '+'},
    'sub':         {'fn': lambda L, R, d1, d2, d3, d4: L - R,                                                   'sym': '-'},
    'mul':         {'fn': lambda L, R, d1, d2, d3, d4: L * R,                                                   'sym': '*'},
    'cat':         {'fn': lambda L, R, d1, d2, d3, d4: int(str(L) + str(R)),                                    'sym': '||'},
    'max_mod_min': {'fn': lambda L, R, d1, d2, d3, d4: max(L, R) % min(L, R) if min(L, R) != 0 else max(L, R), 'sym': ''},
    'add1':        {'fn': lambda L, R, d1, d2, d3, d4: L + R + 1,                                               'sym': ''},
    'addm1':       {'fn': lambda L, R, d1, d2, d3, d4: L + R - 1,                                               'sym': '-'},
    'mul1':        {'fn': lambda L, R, d1, d2, d3, d4: L * R + 1,                                               'sym': ''},
    'mulm1':       {'fn': lambda L, R, d1, d2, d3, d4: L * R - 1,                                               'sym': '-'},
    'sub_abs':     {'fn': lambda L, R, d1, d2, d3, d4: abs(L - R),                                              'sym': ''},
    'sub_neg_abs': {'fn': lambda L, R, d1, d2, d3, d4: -abs(L - R),                                             'sym': '-'},
}

FORMATTERS = {
    'raw': {
        'pre':  lambda A, B: (make_num(A), make_num(B), A[0], A[1], B[0], B[1]),
        'post': lambda val: str(val),
    },
    'swap': {
        'pre':  lambda A, B: (make_num(A[::-1]), make_num(B[::-1]), A[1], A[0], B[1], B[0]),
        'post': lambda val: ('-' + str(val)[1:][::-1] if str(val).startswith('-') else str(val)[::-1]),
    },
    'rev': {
        'pre':  lambda A, B: (make_num(B[::-1]), make_num(A[::-1]), B[1], B[0], A[1], A[0]),
        'post': lambda val: str(val)[::-1],
    },
}

op_names = list(MATH_OPS.keys())
MUL_OPS = {'mul', 'mul1', 'mulm1'}


def make_num(digits):
    return sum(d * (10 ** (len(digits) - 1 - i)) for i, d in enumerate(digits))


def _plausible_ops(ex: dict) -> list[str]:
    out = ex['out']
    n = len(out)
    has_neg = n > 1 and out[0] == ex['op']
    val_len = n - 1 if has_neg else n
    result = []
    for name in op_names:
        if name in ('add', 'sub', 'add1', 'addm1', 'sub_abs', 'sub_neg_abs', 'max_mod_min'):
            if val_len <= 3:
                result.append(name)
        elif name in MUL_OPS:
            if val_len <= 5:
                result.append(name)
        elif name == 'cat':
            if val_len <= 4:
                result.append(name)
    return result


def extract_all_examples(prompt: str):
    lines = [l.strip() for l in prompt.split('\n') if '=' in l and 'determine' not in l.lower()]
    target_m = re.search(r'result for:\s*(\S{2})(\S)(\S{2})', prompt)
    if not target_m:
        return None, [], '', '', ''
    tA_str, tgt_op, tB_str = target_m.groups()
    parsed = []
    for line in lines:
        parts = line.split('=')
        if len(parts) != 2:
            continue
        lhs, rhs = parts[0].strip(), parts[1].strip()
        if len(lhs) != 5:
            continue
        parsed.append({'A': list(lhs[:2]), 'B': list(lhs[3:5]), 'op': lhs[2], 'out': list(rhs)})
    return parsed, list(tA_str), list(tB_str), tgt_op


# ---------------------------------------------------------------------------
# Derive output symbol assignments from a computed result
# ---------------------------------------------------------------------------

def _derive_output(
    result_val,
    out_syms: list[str],
    f_type: str,
    op_name: str,
    op_sym: str,
    digit_map: dict[str, int],
    used: set[int],
) -> tuple[dict[str, int], bool]:
    try:
        fmt_str = FORMATTERS[f_type]['post'](result_val)
    except Exception:
        return {}, False
    m_sym = MATH_OPS[op_name]['sym']
    if m_sym == '-':
        fmt_str = fmt_str.replace('-', op_sym)
    elif m_sym != '':
        fmt_str = fmt_str.replace(m_sym, op_sym)

    if len(fmt_str) != len(out_syms):
        return {}, False

    new_assign: dict[str, int] = {}
    new_used: set[int] = set()

    for ch, sym in zip(fmt_str, out_syms):
        if ch.isdigit():
            required = int(ch)
            if sym in digit_map:
                if digit_map[sym] != required:
                    return {}, False
            elif sym in new_assign:
                if new_assign[sym] != required:
                    return {}, False
            else:
                if required in used or required in new_used:
                    return {}, False
                new_assign[sym] = required
                new_used.add(required)
        else:
            if ch != sym:
                return {}, False

    return new_assign, True


# ---------------------------------------------------------------------------
# Example-driven recursive search (op selected per example, not pre-enumerated)
# ---------------------------------------------------------------------------

def _syms_for_pipeline(ex: dict, f_type: str) -> tuple[str, str, str, str]:
    """Return (A0_sym, A1_sym, B0_sym, B1_sym) for the given pipeline.
    Mirrors how OR-Tools constructs L_var and R_var:
      raw:  L = d[A[0]]*10 + d[A[1]],  R = d[B[0]]*10 + d[B[1]]
      swap: L = d[A[1]]*10 + d[A[0]],  R = d[B[1]]*10 + d[B[0]]
      rev:  L = d[B[1]]*10 + d[B[0]],  R = d[A[1]]*10 + d[A[0]]
    """
    if f_type == 'raw':
        return ex['A'][0], ex['A'][1], ex['B'][0], ex['B'][1]
    if f_type == 'swap':
        return ex['A'][1], ex['A'][0], ex['B'][1], ex['B'][0]
    # rev
    return ex['B'][1], ex['B'][0], ex['A'][1], ex['A'][0]


def _search(
    examples: list[dict],           # ORIGINAL (non-reversed) examples
    ex_idx: int,
    digit_map: dict[str, int],
    used: set[int],
    op_assign: dict[str, str],     # op_sym → op_name chosen so far
    plausible: list[list[str]],    # plausible ops per example
    f_type: str,
    solutions: list[tuple[dict, dict]],
    deadline: float,
    max_solutions: int,
):
    if time.time() > deadline or len(solutions) >= max_solutions:
        return
    if ex_idx == len(examples):
        solutions.append((dict(digit_map), dict(op_assign)))
        return

    ex = examples[ex_idx]
    A0s, A1s, B0s, B1s = _syms_for_pipeline(ex, f_type)
    op_sym = ex['op']

    # Determine which ops are still consistent with prior choices for this op_sym
    allowed_ops = plausible[ex_idx]
    if op_sym in op_assign:
        allowed_ops = [o for o in allowed_ops if o == op_assign[op_sym]]
        if not allowed_ops:
            return

    def iter_sym(sym, dm, u):
        if sym in dm:
            yield dm[sym]
        else:
            for v in range(10):
                if v not in u:
                    yield v

    for a0 in iter_sym(A0s, digit_map, used):
        a0_new = A0s not in digit_map
        used2 = used | {a0} if a0_new else used
        dm2 = {**digit_map, A0s: a0} if a0_new else digit_map

        for a1 in iter_sym(A1s, dm2, used2):
            a1_new = A1s not in dm2
            used3 = used2 | {a1} if a1_new else used2
            dm3 = {**dm2, A1s: a1} if a1_new else dm2

            for b0 in iter_sym(B0s, dm3, used3):
                b0_new = B0s not in dm3
                used4 = used3 | {b0} if b0_new else used3
                dm4 = {**dm3, B0s: b0} if b0_new else dm3

                for b1 in iter_sym(B1s, dm4, used4):
                    b1_new = B1s not in dm4
                    used5 = used4 | {b1} if b1_new else used4
                    dm5 = {**dm4, B1s: b1} if b1_new else dm4

                    # Compute L and R directly (A0_sym is the tens digit, A1_sym ones digit)
                    # This mirrors OR-Tools: L_var = digit_vars[A_syms[0]]*10 + digit_vars[A_syms[1]]
                    L = a0 * 10 + a1
                    R = b0 * 10 + b1

                    for op_name in allowed_ops:
                        try:
                            result_val = MATH_OPS[op_name]['fn'](L, R, 0, 0, 0, 0)
                        except Exception:
                            continue

                        new_out, ok = _derive_output(
                            result_val, ex['out'], f_type, op_name, op_sym, dm5, used5
                        )
                        if not ok:
                            continue

                        dm6 = {**dm5, **new_out}
                        used6 = used5 | set(new_out.values())
                        op6 = {**op_assign, op_sym: op_name}

                        _search(examples, ex_idx + 1, dm6, used6, op6,
                                plausible, f_type, solutions, deadline, max_solutions)


# ---------------------------------------------------------------------------
# Answer encoding
# ---------------------------------------------------------------------------

def _encode_answer(
    numeric_ans,
    tgt_math_op: str,
    tgt_op_str: str,
    f_type: str,
    digit_map: dict[str, int],
    digit_sym_list: list[str],
    ops_used: set[str],
) -> str | None:
    try:
        s_val_str = FORMATTERS[f_type]['post'](numeric_ans)
    except Exception:
        return None
    m_sym = MATH_OPS[tgt_math_op]['sym']
    if m_sym == '-':
        s_val_str = s_val_str.replace('-', tgt_op_str)
    elif m_sym != '':
        s_val_str = s_val_str.replace(m_sym, tgt_op_str)

    inv = {v: k for k, v in digit_map.items()}
    enc = ''
    used_missing: set[str] = set()
    for ch in s_val_str:
        if ch.isdigit():
            d = int(ch)
            if d not in inv:
                fb = next(
                    (s for s in SYMBOL_UNIVERSE
                     if s not in digit_sym_list and s not in ops_used and s not in used_missing),
                    None,
                )
                if fb is None:
                    return None
                inv[d] = fb
                used_missing.add(fb)
            enc += inv[d]
        else:
            enc += ch
    return enc


# ---------------------------------------------------------------------------
# Main solver
# ---------------------------------------------------------------------------

def solve_cipher_unified(
    prompt: str,
    mode: str = 'greedy',
    target_answer: str = None,
    log_path: str = None,
) -> Union[str, dict[str, int], bool, None]:
    extraction = extract_all_examples(prompt)
    if extraction[0] is None:
        return False if mode == 'theoretical' else None

    parsed_examples, tA, tB, tgt_op_str = extraction

    a_b_syms: set[str] = set(tA + tB)
    for ex in parsed_examples:
        a_b_syms.update(ex['A'] + ex['B'])
    out_syms_set: set[str] = set()
    for ex in parsed_examples:
        out_syms_set.update(ex['out'])
    active_digits = a_b_syms | out_syms_set
    ops_used: set[str] = set(ex['op'] for ex in parsed_examples) | {tgt_op_str}
    for op in list(ops_used):
        if op not in a_b_syms and len(active_digits) > 10:
            active_digits.discard(op)

    digit_sym_list = list(active_digits)
    possible_answers: dict[str, int] = {}

    _log_fh = open(log_path, 'a') if log_path else None

    def emit(msg: str):
        print(msg, file=sys.__stdout__, flush=True)
        if _log_fh:
            print(msg, file=_log_fh, flush=True)

    encTA = ''.join(tA)
    encTB = ''.join(tB)
    emit(f"\n{'='*60}")
    emit(f"PROBLEM: {encTA}{tgt_op_str}{encTB}=?  target={target_answer!r}")

    try:
        for f_type in FORMATTERS:
            emit(f"\n--- PIPELINE {f_type} ---")
            pipeline_answers: dict[str, int] = {}
            start = time.time()
            deadline = start + 2.0
            sol_count = 0
            target_hits = 0

            # Compute plausible ops using original examples (same as OR-Tools)
            plausible_per_ex = []
            skip = False
            for ex in parsed_examples:
                ops = _plausible_ops(ex)
                if not ops:
                    skip = True
                    break
                plausible_per_ex.append(ops)

            if skip:
                emit('  [SKIP] no plausible ops for some example')
                continue

            solutions: list[tuple[dict, dict]] = []
            _search(parsed_examples, 0, {}, set(), {}, plausible_per_ex,
                    f_type, solutions, deadline, max_solutions=50000)

            # Determine target symbol order for this pipeline (same logic as OR-Tools)
            tgt_ex = {'A': tA, 'B': tB, 'op': tgt_op_str, 'out': []}
            tA0s, tA1s, tB0s, tB1s = _syms_for_pipeline(tgt_ex, f_type)

            # When target op not seen in training, try all ops (cryptarithm_guess)
            tgt_op_seen = any(ex['op'] == tgt_op_str for ex in parsed_examples)

            for digit_map, op_assign in solutions:
                sol_count += 1
                if tgt_op_seen:
                    tgt_math_op = op_assign.get(tgt_op_str)
                    if not tgt_math_op:
                        continue
                    candidate_ops = [tgt_math_op]
                else:
                    candidate_ops = op_names

                target_syms_4 = (tA0s, tA1s, tB0s, tB1s)
                unique_missing = list(dict.fromkeys(s for s in target_syms_4 if s not in digit_map))

                if unique_missing:
                    avail = [v for v in range(10) if v not in digit_map.values()]
                    if len(avail) < len(unique_missing):
                        continue
                    maps_to_try: list[dict[str, int]] = [
                        {**digit_map, **dict(zip(unique_missing, combo))}
                        for combo in _permutations(avail, len(unique_missing))
                    ]
                else:
                    maps_to_try = [digit_map]

                for dm in maps_to_try:
                    ta0, ta1, tb0, tb1 = dm[tA0s], dm[tA1s], dm[tB0s], dm[tB1s]
                    L_tgt = ta0 * 10 + ta1
                    R_tgt = tb0 * 10 + tb1
                    for tgt_math_op in candidate_ops:
                        try:
                            numeric_ans = MATH_OPS[tgt_math_op]['fn'](L_tgt, R_tgt, 0, 0, 0, 0)
                        except (ZeroDivisionError, ValueError, OverflowError):
                            continue

                        encoded = _encode_answer(
                            numeric_ans, tgt_math_op, tgt_op_str, f_type,
                            dm, digit_sym_list, ops_used,
                        )
                        if encoded is not None:
                            possible_answers[encoded] = possible_answers.get(encoded, 0) + 1
                            pipeline_answers[encoded] = pipeline_answers.get(encoded, 0) + 1
                            if target_answer is not None and encoded == str(target_answer):
                                target_hits += 1

            elapsed = time.time() - start
            timed_out = elapsed >= 2.0
            emit(f"  [PIPELINE {f_type}] valid={sol_count} answers={pipeline_answers} "
                 f"target_hits={target_hits} timed_out={timed_out} elapsed={elapsed:.2f}s")

        greedy_answer = max(possible_answers, key=possible_answers.get) if possible_answers else None
        emit(f"\n[GLOBAL] answers={possible_answers} pick={greedy_answer!r} target={target_answer!r} "
             f"found={str(target_answer) in possible_answers if target_answer is not None else '?'}")

    finally:
        if _log_fh:
            _log_fh.close()

    if mode == 'greedy':
        return greedy_answer
    if mode == 'theoretical':
        return str(target_answer) in possible_answers
    return possible_answers
