import sys
import re
import time
from typing import Any
from ortools.sat.python import cp_model

WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path: sys.path.append(WORKSPACE_DIR)

SYMBOL_UNIVERSE = ['!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', ':', '<', '=', '>', '?', '@', '[', '\\', ']', '^', '_', '`', '{', '|', '}', '~']

def make_num(digits):
    return sum(d * (10**(len(digits)-1-i)) for i, d in enumerate(digits))

MATH_OPS = {
    'add':         {'fn': lambda L, R, d1, d2, d3, d4: L + R,                                                   'sym': '+'},
    'sub':         {'fn': lambda L, R, d1, d2, d3, d4: L - R,                                                   'sym': '-'},
    'mul':         {'fn': lambda L, R, d1, d2, d3, d4: L * R,                                                   'sym': '*'},
    'cat':         {'fn': lambda L, R, d1, d2, d3, d4: int(str(L) + str(R)),                                    'sym': '||'},
    'max_mod_min': {'fn': lambda L, R, d1, d2, d3, d4: max(L,R) % min(L,R) if min(L,R) != 0 else max(L,R),    'sym': ''},
    'add1':        {'fn': lambda L, R, d1, d2, d3, d4: L + R + 1,                                               'sym': ''},
    'addm1':       {'fn': lambda L, R, d1, d2, d3, d4: L + R - 1,                                               'sym': '-'},
    'mul1':        {'fn': lambda L, R, d1, d2, d3, d4: L * R + 1,                                               'sym': ''},
    'mulm1':       {'fn': lambda L, R, d1, d2, d3, d4: L * R - 1,                                               'sym': '-'},
    'sub_abs':     {'fn': lambda L, R, d1, d2, d3, d4: abs(L - R),                                              'sym': ''},
    'sub_neg_abs': {'fn': lambda L, R, d1, d2, d3, d4: -abs(L - R),                                             'sym': '-'},
}

FORMATTERS = {
    'raw': {
        'pre':  lambda A_vals, B_vals: (make_num(A_vals), make_num(B_vals), A_vals[0], A_vals[1], B_vals[0], B_vals[1]),
        'post': lambda val: str(val)
    },
    'swap': {
        'pre':  lambda A_vals, B_vals: (make_num(A_vals[::-1]), make_num(B_vals[::-1]), A_vals[1], A_vals[0], B_vals[1], B_vals[0]),
        'post': lambda val: ('-' + str(val)[1:][::-1] if str(val).startswith('-') else str(val)[::-1])
    },
    'rev': {
        'pre':  lambda A_vals, B_vals: (make_num(B_vals[::-1]), make_num(A_vals[::-1]), B_vals[1], B_vals[0], A_vals[1], A_vals[0]),
        'post': lambda val: str(val)[::-1]
    }
}

PIPELINES = [(f, f) for f in FORMATTERS.keys()]

op_names = list(MATH_OPS.keys())
OP_INDEX = {name: i for i, name in enumerate(op_names)}
MUL_OPS = {'mul', 'mul1', 'mulm1'}


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
            if int(f_c) != mapping.get(o_c, -1): return False
        else:
            if f_c != o_c: return False
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
            raise ValueError(f"LHS must be 5 chars: '{line}'")
        parsed_examples.append({'A': list(lhs[:2]), 'B': list(lhs[3:5]), 'op': lhs[2], 'out': list(rhs)})
    return parsed_examples, list(tA_str), list(tB_str), tgt_op


def _plausible_ops(ex):
    out = ex['out']
    n = len(out)
    has_neg = (n > 1 and out[0] == ex['op'])
    val_len = n - 1 if has_neg else n
    result = []
    for name in op_names:
        if name in ('add', 'sub', 'add1', 'addm1', 'sub_abs', 'sub_neg_abs', 'max_mod_min'):
            if val_len <= 3: result.append(name)
        elif name in MUL_OPS:
            if val_len <= 5: result.append(name)
        elif name == 'cat':
            if val_len <= 4: result.append(name)
    return result


def _out_expr(digit_vars, syms, f_type):
    """Linear CP-SAT expression for the positive numeric value of a digit symbol sequence."""
    n = len(syms)
    if f_type == 'raw':
        return sum(digit_vars[c] * (10 ** (n - 1 - i)) for i, c in enumerate(syms))
    else:
        # swap/rev: the encoded string has reversed digit significance
        return sum(digit_vars[c] * (10 ** i) for i, c in enumerate(syms))


def _add_op_constraints(model, op_name, b, L_var, R_var, result_var, uid, digit_vars, out_syms, f_type, ex):
    """
    Add CP-SAT constraints for one op choice, enforced only when BoolVar b is True.
    Returns True if output-matching constraints were successfully added.
    """
    m_sym = MATH_OPS[op_name]['sym']

    # Determine output structure — mutually exclusive cases
    has_neg_prefix = (
        m_sym == '-' and len(out_syms) > 1
        and out_syms[0] == ex['op'] and f_type != 'rev'
    )
    has_neg_suffix = (
        m_sym == '-' and len(out_syms) > 1
        and out_syms[-1] == ex['op'] and f_type == 'rev'
    )
    all_digit_syms = all(c in digit_vars for c in out_syms)
    pos_digit_syms = (has_neg_prefix and all(c in digit_vars for c in out_syms[1:]))
    suf_digit_syms = (has_neg_suffix and all(c in digit_vars for c in out_syms[:-1]))

    # --- Build the math result expression ---
    if op_name == 'add':
        eq_expr = L_var + R_var
    elif op_name == 'sub':
        eq_expr = L_var - R_var
    elif op_name == 'add1':
        eq_expr = L_var + R_var + 1
    elif op_name == 'addm1':
        eq_expr = L_var + R_var - 1
    elif op_name == 'sub_abs':
        diff = model.NewIntVar(-99, 99, f"diff_{uid}")
        model.Add(diff == L_var - R_var)
        abs_var = model.NewIntVar(0, 99, f"abs_{uid}")
        model.AddAbsEquality(abs_var, diff)
        eq_expr = abs_var
    elif op_name == 'sub_neg_abs':
        diff = model.NewIntVar(-99, 99, f"diff_{uid}")
        model.Add(diff == L_var - R_var)
        abs_var = model.NewIntVar(0, 99, f"abs_{uid}")
        model.AddAbsEquality(abs_var, diff)
        neg_abs = model.NewIntVar(-99, 0, f"negabs_{uid}")
        model.Add(neg_abs == -abs_var)
        eq_expr = neg_abs
    elif op_name in MUL_OPS:
        mul_var = model.NewIntVar(0, 9801, f"mul_{uid}")
        model.AddMultiplicationEquality(mul_var, [L_var, R_var])
        if op_name == 'mul':     eq_expr = mul_var
        elif op_name == 'mul1':  eq_expr = mul_var + 1
        else:                    eq_expr = mul_var - 1  # mulm1
    elif op_name == 'cat':
        # cat(L,R) = str(L)+str(R) without zero-padding
        # R in 0-99: single digit (<10) → L*10+R; two digits (≥10) → L*100+R
        r_single = model.NewBoolVar(f"rsin_{uid}")
        model.Add(R_var < 10).OnlyEnforceIf(r_single)
        model.Add(R_var >= 10).OnlyEnforceIf(r_single.Not())
        cat_var = model.NewIntVar(0, 9999, f"cat_{uid}")
        model.Add(cat_var == L_var * 10 + R_var).OnlyEnforceIf(r_single)
        model.Add(cat_var == L_var * 100 + R_var).OnlyEnforceIf(r_single.Not())
        eq_expr = cat_var
    elif op_name == 'max_mod_min':
        mx = model.NewIntVar(0, 99, f"mx_{uid}")
        mn = model.NewIntVar(0, 99, f"mn_{uid}")
        model.AddMaxEquality(mx, [L_var, R_var])
        model.AddMinEquality(mn, [L_var, R_var])
        mn_zero = model.NewBoolVar(f"mnz_{uid}")
        model.Add(mn == 0).OnlyEnforceIf(mn_zero)
        model.Add(mn != 0).OnlyEnforceIf(mn_zero.Not())
        # Use mn_safe = max(mn, 1) to avoid division-by-zero in AddModuloEquality
        one = model.NewIntVar(1, 1, f"one_{uid}")
        mn_safe = model.NewIntVar(1, 99, f"mns_{uid}")
        model.AddMaxEquality(mn_safe, [mn, one])
        mod_var = model.NewIntVar(0, 98, f"mod_{uid}")
        model.AddModuloEquality(mod_var, mx, mn_safe)
        mmm = model.NewIntVar(0, 99, f"mmm_{uid}")
        model.Add(mmm == mx).OnlyEnforceIf(mn_zero)
        model.Add(mmm == mod_var).OnlyEnforceIf(mn_zero.Not())
        eq_expr = mmm
    else:
        return False

    # --- Match eq_expr to encoded output — exactly one case applies ---
    if has_neg_prefix and pos_digit_syms:
        # Negative result: out[0] is the sign character, out[1:] encode |result|
        out_mag = _out_expr(digit_vars, out_syms[1:], f_type)
        model.Add(result_var == eq_expr).OnlyEnforceIf(b)
        model.Add(result_var == -out_mag).OnlyEnforceIf(b)
        return True
    elif has_neg_suffix and suf_digit_syms:
        # Negative result with 'rev': sign char is at the end
        out_mag = _out_expr(digit_vars, out_syms[:-1], 'rev')
        model.Add(result_var == eq_expr).OnlyEnforceIf(b)
        model.Add(result_var == -out_mag).OnlyEnforceIf(b)
        return True
    elif all_digit_syms and not has_neg_prefix and not has_neg_suffix:
        # Positive result: all out chars are digit symbols
        out_val = _out_expr(digit_vars, out_syms, f_type)
        model.Add(result_var == eq_expr).OnlyEnforceIf(b)
        model.Add(result_var == out_val).OnlyEnforceIf(b)
        return True

    return False


def _add_blocking_clause(model, digit_vars, digit_sym_list, op_vars, op_sym_list, digit_map, op_val_map, sol_id):
    """Add a clause requiring at least one variable to differ from the current solution."""
    lits = []
    for sym in digit_sym_list:
        bv = model.NewBoolVar(f"blk_d_{sym}_{sol_id}")
        model.Add(digit_vars[sym] != digit_map[sym]).OnlyEnforceIf(bv)
        model.Add(digit_vars[sym] == digit_map[sym]).OnlyEnforceIf(bv.Not())
        lits.append(bv)
    for sym in op_sym_list:
        bv = model.NewBoolVar(f"blk_op_{sym}_{sol_id}")
        model.Add(op_vars[sym] != op_val_map[sym]).OnlyEnforceIf(bv)
        model.Add(op_vars[sym] == op_val_map[sym]).OnlyEnforceIf(bv.Not())
        lits.append(bv)
    model.AddBoolOr(lits)


def solve_cipher_unified(
    prompt: str,
    mode: str = 'greedy',
    target_answer: str = None,
    log_path: str = None,
) -> Any:
    extraction = extract_all_examples(prompt)
    if extraction[0] is None: return False if mode == 'theoretical' else None

    parsed_examples, tA, tB, tgt_op_str = extraction

    a_b_syms = set(tA + tB)
    for ex in parsed_examples:
        a_b_syms.update(ex['A'] + ex['B'])

    out_syms_set = set()
    for ex in parsed_examples:
        out_syms_set.update(ex['out'])

    active_digits = a_b_syms | out_syms_set
    ops_used = set(ex['op'] for ex in parsed_examples) | {tgt_op_str}

    for op in ops_used:
        if op not in a_b_syms and len(active_digits) > 10:
            active_digits.discard(op)

    digit_sym_list = list(active_digits)
    op_sym_list = list(ops_used)

    possible_answers = {}
    _log_fh = open(log_path, 'a') if log_path else None

    def emit(msg: str):
        print(msg, file=sys.__stdout__, flush=True)
        if _log_fh:
            print(msg, file=_log_fh, flush=True)

    try:
        encTA = ''.join(tA)
        encTB = ''.join(tB)
        emit(f"\n{'='*60}")
        emit(f"PROBLEM: {encTA}{tgt_op_str}{encTB}=?  |  target_answer={target_answer!r}")
        emit(f"  examples ({len(parsed_examples)}): " +
             "  ".join(f"{''.join(ex['A'])}{ex['op']}{''.join(ex['B'])}={''.join(ex['out'])}" for ex in parsed_examples))
        emit(f"  digit_syms={digit_sym_list}  op_syms={list(ops_used)}")

        for f_type, _ in PIPELINES:
            emit(f"\n--- PIPELINE {f_type} ---")

            model = cp_model.CpModel()
            digit_vars = {sym: model.NewIntVar(0, 9, f"d_{sym}") for sym in digit_sym_list}
            model.AddAllDifferent(list(digit_vars.values()))
            op_vars = {sym: model.NewIntVar(0, len(op_names) - 1, f"op_{sym}") for sym in op_sym_list}

            pipeline_ok = True
            for ex_idx, ex in enumerate(parsed_examples):
                if f_type == 'raw':
                    A_syms, B_syms = ex['A'], ex['B']
                elif f_type == 'swap':
                    A_syms, B_syms = ex['A'][::-1], ex['B'][::-1]
                else:
                    A_syms, B_syms = ex['B'][::-1], ex['A'][::-1]

                L_var = model.NewIntVar(0, 99, f"L_{ex_idx}")
                R_var = model.NewIntVar(0, 99, f"R_{ex_idx}")
                model.Add(L_var == digit_vars[A_syms[0]] * 10 + digit_vars[A_syms[1]])
                model.Add(R_var == digit_vars[B_syms[0]] * 10 + digit_vars[B_syms[1]])

                op_var = op_vars[ex['op']]
                result_var = model.NewIntVar(-9999, 99999, f"res_{ex_idx}")
                plausible = _plausible_ops(ex)

                op_bools = []
                for op_name in plausible:
                    b = model.NewBoolVar(f"b_{ex_idx}_{op_name}")
                    model.Add(op_var == OP_INDEX[op_name]).OnlyEnforceIf(b)
                    model.Add(op_var != OP_INDEX[op_name]).OnlyEnforceIf(b.Not())
                    uid = f"{ex_idx}_{op_name}"
                    added = _add_op_constraints(model, op_name, b, L_var, R_var, result_var, uid, digit_vars, ex['out'], f_type, ex)
                    if added:
                        op_bools.append(b)
                    else:
                        model.Add(b == 0)

                if not op_bools:
                    pipeline_ok = False
                    break
                model.AddExactlyOne(op_bools)

            if not pipeline_ok:
                emit(f"  [SKIP] no plausible ops for some example")
                continue

            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 2.0

            start_time = time.time()
            raw_count = 0
            valid_count = 0
            invalid_count = 0
            target_hit_count = 0
            pipeline_answers: dict[str, int] = {}
            timed_out = False

            while True:
                if time.time() - start_time > 2.0:
                    timed_out = True
                    break

                status = solver.Solve(model)
                if status not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
                    break
                if raw_count >= 50000:
                    break

                raw_count += 1
                digit_map = {sym: solver.Value(digit_vars[sym]) for sym in digit_sym_list}
                op_val_map = {sym: solver.Value(op_vars[sym]) for sym in op_sym_list}
                op_map = {sym: op_names[op_val_map[sym]] for sym in op_sym_list}

                _add_blocking_clause(model, digit_vars, digit_sym_list, op_vars, op_sym_list, digit_map, op_val_map, raw_count)

                emit(f"  [RAW #{raw_count}] digit={digit_map} ops={op_map}")

                # Python-level validation
                all_valid = True
                fail_detail = ""
                for ex_idx2, ex in enumerate(parsed_examples):
                    A_vals = [digit_map.get(s, -1) for s in ex['A']]
                    B_vals = [digit_map.get(s, -1) for s in ex['B']]
                    if -1 in A_vals or -1 in B_vals:
                        all_valid = False
                        fail_detail = f"ex{ex_idx2}: missing digit sym"
                        break
                    op_name = op_map[ex['op']]
                    L, R, d1, d2, d3, d4 = FORMATTERS[f_type]['pre'](A_vals, B_vals)
                    try:
                        expected_val = MATH_OPS[op_name]['fn'](L, R, d1, d2, d3, d4)
                        if not check_post(expected_val, ex['out'], f_type, op_name, ex['op'], digit_map):
                            all_valid = False
                            fail_detail = (
                                f"ex{ex_idx2}: {''.join(ex['A'])}{ex['op']}{''.join(ex['B'])}={''.join(ex['out'])}"
                                f" → {L} {op_name} {R} = {expected_val} ≠ expected encoding"
                            )
                            break
                    except Exception as e:
                        all_valid = False
                        fail_detail = f"ex{ex_idx2}: exception {e}"
                        break

                if not all_valid:
                    invalid_count += 1
                    emit(f"    [INVALID] {fail_detail}")
                    continue

                valid_count += 1

                # Decode each example for logging
                ex_lines = []
                for ex in parsed_examples:
                    A_vals = [digit_map[s] for s in ex['A']]
                    B_vals = [digit_map[s] for s in ex['B']]
                    out_vals = [digit_map.get(s, '?') for s in ex['out']]
                    op_name = op_map[ex['op']]
                    L, R, d1, d2, d3, d4 = FORMATTERS[f_type]['pre'](A_vals, B_vals)
                    math_result = MATH_OPS[op_name]['fn'](L, R, d1, d2, d3, d4)
                    ex_lines.append(
                        f"    {''.join(ex['A'])}{ex['op']}{''.join(ex['B'])}={''.join(ex['out'])}"
                        f"  →  {L} {op_name} {R} = {math_result}  ✓"
                    )

                # Compute target answer
                tA_vals = [digit_map.get(s, -1) for s in tA]
                tB_vals = [digit_map.get(s, -1) for s in tB]
                tgt_math_op = op_map.get(tgt_op_str)
                encoded_ans = None
                target_detail = "  target: could not compute"

                if -1 not in tA_vals and -1 not in tB_vals and tgt_math_op:
                    try:
                        L_tgt, R_tgt, _, _, _, _ = FORMATTERS[f_type]['pre'](tA_vals, tB_vals)
                        numeric_ans = MATH_OPS[tgt_math_op]['fn'](L_tgt, R_tgt, 0, 0, 0, 0)
                        if numeric_ans is not None:
                            s_val_str = FORMATTERS[f_type]['post'](numeric_ans)
                            m_sym = MATH_OPS[tgt_math_op]['sym']
                            if m_sym == '-':
                                s_val_str = s_val_str.replace('-', tgt_op_str)
                            elif m_sym != "":
                                s_val_str = s_val_str.replace(m_sym, tgt_op_str)

                            inv_digit_map = {v: k for k, v in digit_map.items()}
                            enc = ""
                            can_encode = True
                            used_missing_syms: set = set()
                            for char in s_val_str:
                                if char.isdigit():
                                    d_int = int(char)
                                    if d_int not in inv_digit_map:
                                        fb = next(
                                            (s for s in SYMBOL_UNIVERSE
                                             if s not in digit_sym_list and s not in ops_used and s not in used_missing_syms),
                                            None
                                        )
                                        if not fb: can_encode = False; break
                                        inv_digit_map[d_int] = fb
                                        used_missing_syms.add(fb)
                                    enc += inv_digit_map[d_int]
                                else:
                                    enc += char

                            if can_encode:
                                encoded_ans = enc
                                matches = (encoded_ans == str(target_answer)) if target_answer is not None else None
                                match_tag = ('YES ✓' if matches else 'NO  ✗') if matches is not None else '?'
                                target_detail = (
                                    f"  target: {encTA}{tgt_op_str}{encTB}"
                                    f" → {L_tgt} {tgt_math_op} {R_tgt} = {numeric_ans}"
                                    f" → {s_val_str!r} → encoded={encoded_ans!r}"
                                    f"  matches_target={match_tag}"
                                )
                    except Exception as e:
                        target_detail = f"  target: exception {e}"

                emit(f"    [VALID #{valid_count}] ops={op_map}")
                for line in ex_lines:
                    emit(line)
                emit(target_detail)

                if encoded_ans is not None:
                    possible_answers[encoded_ans] = possible_answers.get(encoded_ans, 0) + 1
                    pipeline_answers[encoded_ans] = pipeline_answers.get(encoded_ans, 0) + 1
                    if target_answer is not None and encoded_ans == str(target_answer):
                        target_hit_count += 1

            elapsed = time.time() - start_time
            emit(f"\n  [PIPELINE {f_type} SUMMARY]")
            emit(f"    raw_models:    {raw_count}")
            emit(f"    valid_models:  {valid_count}  (invalid: {invalid_count})")
            emit(f"    answers_found: {pipeline_answers}")
            emit(f"    target_hits:   {target_hit_count}")
            emit(f"    timed_out:     {timed_out}")
            emit(f"    elapsed:       {elapsed:.2f}s")

        greedy_answer = max(possible_answers, key=possible_answers.get) if possible_answers else None
        emit(f"\n[GLOBAL SUMMARY]")
        emit(f"  possible_answers: {possible_answers}")
        emit(f"  greedy_pick:      {greedy_answer!r}")
        emit(f"  target_answer:    {target_answer!r}")
        emit(f"  target_found:     {str(target_answer) in possible_answers if target_answer is not None else '?'}")

    finally:
        if _log_fh:
            _log_fh.close()

    if mode == 'greedy':
        return greedy_answer
    if mode == 'theoretical':
        return str(target_answer) in possible_answers
    return possible_answers
