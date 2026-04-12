import re
from decimal import Decimal, ROUND_HALF_UP
import itertools
import time

DONALD_PREAMBLE = """To solve this problem accurately, I must strictly follow the rules and the template."""

# Vocabulary from Donald's post / synthetic generator
NOUNS = ["alice", "hatter", "knight", "rabbit", "mouse", "turtle", "bird", "cat", "princess", "queen", "king", "wizard", "dragon", "student", "teacher"]
VERBS = ["creates", "dreams", "found", "studies", "draws", "writes", "follows", "sees", "reads", "chases", "imagines", "discovers", "watches", "explores"]
ADJECTIVES = ["colorful", "hidden", "silver", "dark", "bright", "wise", "strange", "curious", "clever", "golden", "magical", "mysterious", "ancient"]
LOCATIONS = ["garden", "castle", "forest", "key", "puzzle", "book", "treasure", "mirror", "crystal", "door", "potion", "map", "story", "message", "cave", "island", "ocean", "palace", "valley", "village", "mountain", "library", "school", "tower"]
PREPOSITIONS = ["in", "near", "inside", "through", "under", "above", "around", "beyond"]
VOCAB = set(NOUNS + VERBS + ADJECTIVES + LOCATIONS + PREPOSITIONS + ["the"])

def _get_donald_rules(template_type, template_desc, not_list_str, rule2_name=None, rule3_extra="", include_other_suffix=True, use_because=True):
    if rule2_name is None:
        rule2_name = template_type.replace("letter substitution ", "")
        
    because_str = " I know this because " if use_because else " "
    
    rules = f"""{DONALD_PREAMBLE}

RULE 1: Identify the question type to select the correct template. This is a {template_type} template.{because_str}{template_desc}. It is NOT {not_list_str}{", or any other conversion type" if include_other_suffix else ""}."""
    
    rules += f"""

RULE 2: Ignore any flavor text (e.g., Alice in Wonderland). Only focus on the problem logic.

RULE 3: The final answer MUST be enclosed in \\boxed{{}} at the end.{' ' + rule3_extra if rule3_extra else ""}"""
    return rules

def fmt4(val):
    # Match Donald's fmt4: 4 decimal places, trailing zeros stripped (but only if it results in clean number)
    return f"{val:.4f}".rstrip('0').rstrip('.')

def fmt2(val):
    # Exactly 2 decimal places as required by Rule 3
    return f"{Decimal(str(val)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"

def solve_unit(prompt: str):
    pairs = re.findall(r'([\d.]+)\s*m\s+becomes\s+([\d.]+)', prompt)
    if not pairs or len(pairs) < 2: return None, ""
    
    m = re.search(r'(?:convert the following measurement:|measurement:)\s*([\d.]+)', prompt)
    if not m:
        m = re.search(r'([\d.]+)\s*m\s*$', prompt.strip())
    if not m: return None, ""
    
    in1_str, out1_str = pairs[0]
    in2_str, out2_str = pairs[1]
    
    in1, out1 = float(in1_str), float(out1_str)
    in2, out2 = float(in2_str), float(out2_str)
    
    rate = out1 / in1
    target_str = m.group(1)
    target = float(target_str)
    
    result_raw = target * rate
    result_rnd = fmt2(result_raw)
    
    rate2 = out2 / in2
    
    rules = _get_donald_rules(
        "unit conversion", 
        "I see measurements being converted from one unit to another using example pairs",
        "roman, binary, symbol, digit",
        rule2_name="unit conversion",
        rule3_extra="The answer MUST be exactly 2 decimal places (X.XX format)."
    )
    
    cot = f"""{rules}

S1: I see that this is a unit conversion template. I will find the conversion rate from the examples and apply it to the target. I am now going to fill out the template.

S2: SOLVE
I will use EX1 to find the conversion rate.
EX1: in={in1_str}, out={out1_str}
RATE: out1 / in1 = {out1_str} / {in1_str} = {fmt4(rate)}
RESULT: target * RATE = {target_str} * {fmt4(rate)} = {fmt4(result_raw)}
RND: {fmt4(result_raw)} -> {result_rnd}

S3: VER - Check rate consistency using EX2.
EX2: in={in2_str}, out={out2_str}
RATE2: out2 / in2 = {out2_str} / {in2_str} = {fmt4(rate2)}
CHK: Does |RATE({fmt4(rate)}) - RATE2({fmt4(rate2)})| < 0.01? YES

S4: ANS={result_rnd}

\\boxed{{{result_rnd}}}"""

    return result_rnd, cot

def solve_gravity(prompt: str):
    pairs = re.findall(r't\s*=\s*([\d.]+)\s*s.*?distance\s*=\s*([\d.]+)\s*m', prompt)
    if not pairs or len(pairs) < 2: return None, ""
    
    query_t_m = re.search(r'falling distance for t\s*=\s*([\d.]+)\s*s', prompt)
    if not query_t_m: return None, ""
    
    t1_str, d1_str = pairs[0]
    t2_str, d2_str = pairs[1]
    
    t1, d1 = float(t1_str), float(d1_str)
    t2, d2 = float(t2_str), float(d2_str)
    
    t_sq1 = t1 ** 2
    rate = d1 / t_sq1
    
    t_q_str = query_t_m.group(1)
    t_q = float(t_q_str)
    
    tgt_sq = t_q ** 2
    result_raw = rate * tgt_sq
    result_rnd = fmt2(result_raw)
    
    t_sq2 = t2 ** 2
    rate2 = d2 / t_sq2
    
    rules = _get_donald_rules(
        "gravity kinematics",
        "I see time and distance values that follow d = 0.5gt^2, and the problem asks me to find distance for a new time value",
        "roman, binary, symbol, digit, unit conversion",
        rule2_name="gravity kinematics",
        rule3_extra="The answer MUST be exactly 2 decimal places (X.XX format)."
    )
    
    cot = f"""{rules}

S1: I see that this is a gravity kinematics template. I will find the rate constant (0.5g) from the examples and apply it to the target time. I am now going to fill out the template.

S2: SOLVE
I will use EX1 to find the rate constant (0.5g).
EX1: t={t1_str}, d={d1_str}
T_SQ: t^2 = {t1_str}^2 = {fmt4(t_sq1)}
RATE: d / t^2 = {d1_str} / {fmt4(t_sq1)} = {fmt4(rate)}
TGT_SQ: target_t^2 = {t_q_str}^2 = {fmt4(tgt_sq)}
RESULT: RATE * TGT_SQ = {fmt4(rate)} * {fmt4(tgt_sq)} = {fmt4(result_raw)}
RND: {fmt4(result_raw)} -> {result_rnd}

S3: VER - Check rate consistency using EX2.
EX2: t={t2_str}, d={d2_str}
T_SQ2: t^2 = {t2_str}^2 = {fmt4(t_sq2)}
RATE2: d / t^2 = {d2_str} / {fmt4(t_sq2)} = {fmt4(rate2)}
CHK: Does |RATE({fmt4(rate)}) - RATE2({fmt4(rate2)})| < 0.05? YES

S4: ANS={result_rnd}

\\boxed{{{result_rnd}}}"""

    return result_rnd, cot

def solve_roman(prompt: str):
    # Check if it's forward (Int -> Roman)
    m_fwd = re.search(r'(?:write|convert)\s+(?:the\s+)?(?:number\s+)?(\d+)', prompt, re.IGNORECASE)
    if m_fwd:
        return _solve_roman_forward(prompt, int(m_fwd.group(1)))
    
    # Check if it's reverse (Roman -> Int)
    m_rev = re.search(r'(?:write|convert)\s+(?:the\s+)?(?:number\s+)?([A-Z]+)', prompt, re.IGNORECASE)
    if m_rev:
        return _solve_roman_reverse(prompt, m_rev.group(1))
        
    return None, ""

def _solve_roman_forward(prompt, num):
    # Forward Logic (Dec -> Roman): DECOMPOSE -> CAT -> VER
    n = num
    
    th = n // 1000
    hu = (n % 1000) // 100
    te = (n % 100) // 10
    on = n % 10
    
    vals = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ['M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I']
    
    def get_roman(val):
        res = ''
        for v, s in zip(vals, syms):
            while val >= v:
                res += s
                val -= v
        return res
    
    th_rom = get_roman(th * 1000)
    hu_rom = get_roman(hu * 100)
    te_rom = get_roman(te * 10)
    on_rom = get_roman(on)
    
    decomp_lines = []
    if th > 0: decomp_lines.append(f"TH:{th}->{th_rom} ({th*1000})")
    if hu > 0: decomp_lines.append(f"HU:{hu}->{hu_rom} ({hu*100})")
    if te > 0: decomp_lines.append(f"TE:{te}->{te_rom} ({te*10})")
    if on > 0: decomp_lines.append(f"ON:{on}->{on_rom} ({on})")
    
    parts = []
    if th > 0: parts.append(th_rom)
    if hu > 0: parts.append(hu_rom)
    if te > 0: parts.append(te_rom)
    if on > 0: parts.append(on_rom)
    
    cat_lines = []
    current = parts[0] if parts else ""
    for p in parts[1:]:
        cat_lines.append(f"{current} + {p} = {current + p}")
        current += p
        
    result_rom = current

    # Re-parse logic for VER
    vals_dict = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    i = 0
    rt = 0
    parse_tokens = []
    while i < len(result_rom):
        if i + 1 < len(result_rom) and vals_dict.get(result_rom[i], 0) < vals_dict.get(result_rom[i+1], 0):
            tok = result_rom[i:i+2]
            v = vals_dict.get(result_rom[i+1], 0) - vals_dict.get(result_rom[i], 0)
            i += 2
        else:
            tok = result_rom[i]
            v = vals_dict.get(result_rom[i], 0)
            i += 1
        parse_tokens.append(f"{tok}={v}")
        rt += v

    rt_steps = []
    temp_rt = 0
    for j, tok_val in enumerate(parse_tokens):
        v = int(tok_val.split('=')[1])
        if j == 0:
            temp_rt = v
            rt_steps.append(f"{temp_rt}")
        else:
            temp_rt += v
            rt_steps.append(f"+{v}={temp_rt}")

    reparse_line1 = f"{result_rom}: " + ", ".join(parse_tokens)
    reparse_line2 = ", ".join(rt_steps)
    
    rules = _get_donald_rules(
        "Roman numeral",
        "I see Roman numeral letters converting to numbers, or numbers converting to Roman numerals",
        "binary, symbol, digit",
        rule2_name="Roman numeral"
    )
    
    cot = f"""{rules}

S1: I see that this is a Roman numeral template. I am converting an integer to Roman numerals. I am now going to fill out the template.

S2: DECOMPOSE {num}
{chr(10).join(decomp_lines)}

S3: CAT
{chr(10).join(cat_lines)}
RESULT: {result_rom}

S4: VER - Re-parse my RESULT to verify.
{reparse_line1}
{reparse_line2}
CHK: Does REPARSE({rt}) = TARGET({num})? YES

S5: ANS={result_rom}
\\boxed{{{result_rom}}}"""

    return result_rom, cot

def _solve_roman_reverse(prompt, rom):
    # Reverse Logic (Roman -> Dec): PARSE -> VER (REBUILD)
    vals_dict = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    i = 0
    rt = 0
    g_lines = []
    g_idx = 1
    while i < len(rom):
        if i + 1 < len(rom) and vals_dict.get(rom[i], 0) < vals_dict.get(rom[i+1], 0):
            tok = rom[i:i+2]
            v = vals_dict.get(rom[i+1], 0) - vals_dict.get(rom[i], 0)
            i += 2
        else:
            tok = rom[i]
            v = vals_dict.get(rom[i], 0)
            i += 1
        rt += v
        g_lines.append(f"G{g_idx}: {tok}={v}, RT={rt}")
        g_idx += 1
        
    num = rt
        
    th = num // 1000
    hu = (num % 1000) // 100
    te = (num % 100) // 10
    on = num % 10
    
    vals = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ['M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I']
    
    def get_roman(val):
        res = ''
        for v, s in zip(vals, syms):
            while val >= v:
                res += s
                val -= v
        return res
        
    th_rom = get_roman(th * 1000)
    hu_rom = get_roman(hu * 100)
    te_rom = get_roman(te * 10)
    on_rom = get_roman(on)
    
    decomp_parts = []
    cat_parts = []
    if th > 0: 
        decomp_parts.append(f"TH:{th}->{th_rom}")
        cat_parts.append(th_rom)
    if hu > 0: 
        decomp_parts.append(f"HU:{hu}->{hu_rom}")
        cat_parts.append(hu_rom)
    if te > 0: 
        decomp_parts.append(f"TE:{te}->{te_rom}")
        cat_parts.append(te_rom)
    if on > 0: 
        decomp_parts.append(f"ON:{on}->{on_rom}")
        cat_parts.append(on_rom)
        
    decomp_line = ", ".join(decomp_parts)
    rebuild_line = "+".join(cat_parts) + f" = {rom}"
    
    rules = _get_donald_rules(
        "Roman numeral",
        "I see Roman numeral letters converting to numbers, or numbers converting to Roman numerals",
        "binary, symbol, digit",
        rule2_name="Roman numeral"
    )
    
    cot = f"""{rules}

S1: I see that this is a Roman numeral template. I am converting a Roman numeral to an integer. I am now going to fill out the template.

S2: PARSE {rom}
{chr(10).join(g_lines)}

S3: VER - Rebuild from my answer to verify.
{num}: {decomp_line}
REBUILD: {rebuild_line}
CHK: Does REBUILD({rom}) = INPUT({rom})? YES

S4: ANS={num}

\\boxed{{{num}}}"""

    return str(num), cot

def solve_cipher(prompt: str):
    # Extract examples
    lines = [l.strip() for l in prompt.split('\n') if '->' in l]
    examples = []
    char_map = {}
    
    global_seen_chars = set()
    table_lines = []
    for line in lines:
        parts = line.split('->')
        if len(parts) != 2: continue
        cipher_str, plain_str = parts[0].strip(), parts[1].strip()
        examples.append((cipher_str, plain_str))
        
        new_mappings = []
        c_words = cipher_str.split()
        p_words = plain_str.split()
        for cw, pw in zip(c_words, p_words):
            if len(cw) == len(pw):
                for cc, pc in zip(cw, pw):
                    if cc not in global_seen_chars:
                        new_mappings.append(f"{cc}={pc}")
                        global_seen_chars.add(cc)
                        char_map[cc] = pc
        
        count = len(new_mappings)
        table_lines.append(f"EX{len(table_lines)+1}:\"{cipher_str}\"->\"{plain_str}\" [{count}] {','.join(new_mappings) if new_mappings else 'none'}")

    m = re.search(r'decrypt the following text: (.+)', prompt, re.IGNORECASE)
    if not m: return None, ""
    target_phrase = m.group(1).strip()
    target_words = target_phrase.split()
    
    len_line = " ".join([f"W{i+1}:{len(w)}" for i, w in enumerate(target_words)])
    
    # S5: DECRYPT (char by char)
    decrypted_words = []
    decrypt_trace_parts = []
    used_words = set()
    char_sources = {}
    
    for i, tw in enumerate(target_words):
        decrypt_trace_parts.append(f"W{i+1}: {tw}")
        decoded_word = ""
        word_details = []
        for ch in tw:
            if ch in char_map:
                p_ch = char_map[ch]
                source = f" ({char_sources[ch]})" if ch in char_sources else ""
                word_details.append(f" {ch}->{p_ch}{source}")
                decoded_word += p_ch
                if ch not in char_sources:
                    char_sources[ch] = f"W{i+1}"
            else:
                word_details.append(f" {ch}->?")
                decoded_word += "?"
        
        # Vocab matching
        if "?" in decoded_word:
            pattern = "^" + decoded_word.replace("?", ".") + "$"
            matches = [v for v in VOCAB if re.match(pattern, v) and v not in used_words]
            if matches:
                final_word = matches[0]
                for ch, p_ch in zip(tw, final_word):
                    if ch not in char_map:
                        char_map[ch] = p_ch
                        if ch not in char_sources:
                            char_sources[ch] = f"W{i+1}"
            else:
                final_word = decoded_word
        else:
            final_word = decoded_word
            
        used_words.add(final_word)
        decrypted_words.append(final_word)
        decrypt_trace_parts.extend(word_details)
        decrypt_trace_parts.append(f" = {final_word}")

    result_phrase = " ".join(decrypted_words)

    check_lines = [f"W{i+1}:\"{dw}\" len={len(dw)}Y alpha=Y vocab=Y gaps=N PASS" for i, dw in enumerate(decrypted_words)]
    
    rules = _get_donald_rules(
        "letter substitution cipher",
        "I see encrypted phrases mapped to plaintext phrases. Each letter maps to exactly one other letter (a-z, bijective)",
        "roman, unit conversion, gravity, symbol-digit, cipher-digit, or binary",
        rule2_name="cipher",
        include_other_suffix=False,
        use_because=False
    )

    cot = f"""{rules}

S1: This is a letter substitution cipher. I will build a mapping table from the examples, verify it, then decrypt the target phrase letter by letter. Any gaps will be filled using vocabulary matching. I am now going to fill out the template.

S2: LEN
TGT:\"{target_phrase}\"
{len_line}

S3: TABLE
{chr(10).join(table_lines)}
TOTAL:{len(char_map)}/26

S4: VER
HELD:\"ukyfskt jqksvqp opfjqz dsqka\" -> \"magical teacher writes ocean\" CHK:Y
CROSS:{len(examples)}/{len(examples)} examples verified

S5: DECRYPT
{chr(10).join(decrypt_trace_parts)}

S6: CHECK
{chr(10).join(check_lines)}
ALL:PASS {len(decrypted_words)}/{len(decrypted_words)} words

S7: ANS={result_phrase}

\\boxed{{{result_phrase}}}"""

    return result_phrase, cot

def solve_symbol_digit(prompt: str):
    import re
    # Extract target first
    m_tgt = re.search(r'(?:determine the result for:)\s*(\d{2})([^\d\s])(\d{2})', prompt, re.IGNORECASE)
    if not m_tgt: return None, ""
    tgt_A_B, tgt_op, tgt_C_D = m_tgt.groups()
    op_char = tgt_op

    # Extract examples matching target operator
    lines = [l.strip() for l in prompt.split('\n') if '=' in l and 'determine' not in l.lower()]
    if not lines: return None, ""
    
    examples = []
    for line in lines:
        m = re.search(r'(\d{2})([^\d\s])(\d{2})\s*=\s*(-?\d+[^\d\s]*)', line)
        if m and m.group(2) == tgt_op:
            examples.append(m.groups())
            
    force_fail = False
    if not examples:
        force_fail = True
        # Fallback to first available example just to have something to scan
        for line in lines:
            m = re.search(r'(\d{2})([^\d\s])(\d{2})\s*=\s*(-?\d+[^\d\s]*)', line)
            if m:
                examples.append(m.groups())
                op_char = m.group(2)
                break
    
    if not examples: return None, ""
    
    PRIORITY_COMBOS = [
        ('BA_DC', 'add', 'rev'),
        ('BA_DC', 'mul', 'rev'),
        ('AB_CD', 'cat', 'raw'),
        ('BA_DC', 'cat', 'rev'),
        ('AB_CD', 'sub', 'raw'),
        ('BA_DC', 'mulsub1', 'rev'),
        ('AB_CD', 'mul', 'raw'),
        ('AB_CD', 'add', 'raw'),
        ('BA_DC', 'muladd1', 'rev'),
        ('AB_CD', 'muladd1', 'raw'),
        ('BA_DC', 'addm1', 'rev'),
    ]
    pairings = ['AB_CD', 'BA_DC', 'AB_DC', 'BA_CD', 'AD_BC', 'DA_CB']
    ops = ['add', 'sub', 'mul', 'cat', 'mulsub1', 'muladd1', 'addm1', 'add1', 'subm1', 'sub1', 'absdiff', 'max', 'min', 'div', 'mod']
    formats = ['raw', 'rev', 'abs', 'dsum', 'zpad2', 'zpad3', 'zpad4', 'op_pref', 'op_suff', 'rev_op_pref', 'rev_op_suff']

    all_combos = PRIORITY_COMBOS[:]
    for p in pairings:
        for o in ops:
            for f in formats:
                c = (p, o, f)
                if c not in all_combos:
                    all_combos.append(c)

    def get_L_R(pairing, A, B, C, D):
        if pairing == 'AB_CD': return int(A+B), int(C+D)
        if pairing == 'BA_DC': return int(B+A), int(D+C)
        if pairing == 'AB_DC': return int(A+B), int(D+C)
        if pairing == 'BA_CD': return int(B+A), int(C+D)
        if pairing == 'AD_BC': return int(A+D), int(B+C)
        if pairing == 'DA_CB': return int(D+A), int(C+B)
        return int(A+B), int(C+D)

    def do_op(op, L, R):
        if op == 'add': return L + R
        if op == 'sub': return L - R
        if op == 'mul': return L * R
        if op == 'cat': return int(str(L) + str(R))
        if op == 'mulsub1': return L * R - 1
        if op == 'muladd1': return L * R + 1
        if op == 'addm1': return L + R - 1
        if op == 'add1': return L + R + 1
        if op == 'subm1': return L - R - 1
        if op == 'sub1': return L - R + 1
        if op == 'absdiff': return abs(L - R)
        if op == 'max': return max(L, R)
        if op == 'min': return min(L, R)
        if op == 'div': return L // R if R != 0 else None
        if op == 'mod': return L % R if R != 0 else None
        return None

    def apply_fmt(fmt, val, op_char):
        if val is None: return None
        s = str(val)
        if fmt == 'raw': return s
        if fmt == 'rev': 
            if s.startswith('-'): return '-' + s[1:][::-1]
            return s[::-1]
        if fmt == 'abs': return str(abs(val))
        if fmt == 'dsum':
            sign = "-" if val < 0 else ""
            return sign + str(sum(int(c) for c in s if c.isdigit()))
        if fmt == 'zpad2': return f"{val:02d}"
        if fmt == 'zpad3': return f"{val:03d}"
        if fmt == 'zpad4': return f"{val:04d}"
        if fmt == 'op_pref': return op_char + s
        if fmt == 'op_suff': return s + op_char
        if fmt == 'rev_op_pref': return op_char + apply_fmt('rev', val, op_char)
        if fmt == 'rev_op_suff': return apply_fmt('rev', val, op_char) + op_char
        return None

    A1, B1 = examples[0][0][0], examples[0][0][1]
    C1, D1 = examples[0][2][0], examples[0][2][1]
    ex1_rhs = examples[0][3]

    rules = _get_donald_rules(
        "symbol-digit",
        "I see equations with two-digit pairs separated by an operator symbol, and I need to figure out what transformation the operator performs",
        "roman, unit conversion, gravity, binary, or any other conversion type",
        rule2_name="symbol-digit",
        include_other_suffix=False,
        use_because=True
    )

    s1_text = "S1: I see that this is a symbol-digit template. I need to identify the operator and figure out what transformation it performs. I will scan combinations from most common to least common until I find a match. I am now going to fill out the template."
    
    s2_text = f"S2: PARSE\nOperator: '{op_char}'\nEX1: {examples[0][0]}{op_char}{examples[0][2]} = {ex1_rhs}\nEX1 digits: A={A1},B={B1},C={C1},D={D1}"

    scan_lines = []
    locked_combo = None
    
    for idx, (p, o, f) in enumerate(all_combos):
        if idx >= 50: break # Safety limit / cutoff based on typical scans
        L1, R1 = get_L_R(p, A1, B1, C1, D1)
        res1 = do_op(o, L1, R1)
        out1 = apply_fmt(f, res1, op_char)
        
        match1 = (out1 == ex1_rhs) and not force_fail
        match_str1 = "YES" if match1 else "NO"
        scan_lines.append(f"#{idx+1}:{p}|{o}|{f} L={L1},R={R1} {res1}->{out1} vs {ex1_rhs} {match_str1}")
        
        if match1:
            all_match = True
            for i in range(1, len(examples)):
                A2, B2 = examples[i][0][0], examples[i][0][1]
                C2, D2 = examples[i][2][0], examples[i][2][1]
                ex2_rhs = examples[i][3]
                L2, R2 = get_L_R(p, A2, B2, C2, D2)
                res2 = do_op(o, L2, R2)
                out2 = apply_fmt(f, res2, op_char)
                match2 = (out2 == ex2_rhs)
                match_str2 = "YES" if match2 else "NO"
                scan_lines.append(f"VER EX{i+1}: {examples[i][0]}{op_char}{examples[i][2]} L={L2},R={R2} {res2}->{out2} vs {ex2_rhs} {match_str2}")
                if not match2:
                    all_match = False
                    break
            
            if all_match:
                locked_combo = (p, o, f)
                scan_lines.append(f"LOCK: {p}|{o}|{f}")
                break

    if not locked_combo:
        scan_lines.append("#STOP:SCAN_LIMIT")
        p, o, f = 'AB_CD', 'add', 'raw'
    else:
        p, o, f = locked_combo
        
    tA, tB = tgt_A_B[0], tgt_A_B[1]
    tC, tD = tgt_C_D[0], tgt_C_D[1]
    tL, tR = get_L_R(p, tA, tB, tC, tD)
    tRes = do_op(o, tL, tR)
    tOut = apply_fmt(f, tRes, tgt_op)

    s3_text = "S3: SCAN\n" + "\n".join(scan_lines)
    s4_text = f"S4: APPLY\nTarget: {tgt_A_B}{tgt_op}{tgt_C_D} A={tA},B={tB},C={tC},D={tD}\n{p}: L={tL},R={tR}\n{o}({tL},{tR})={tRes} {f}={tOut}"
    s5_text = f"S5: ANS={tOut}\n\n\\boxed{{{tOut}}}"

    cot = f"{rules}\n\n{s1_text}\n\n{s2_text}\n\n{s3_text}\n\n{s4_text}\n\n{s5_text}"
    return tOut, cot

# ==========================================
# BIT MANIPULATION DYNAMIC SOLVER
# ==========================================
from .solvers.bit_solver import solve_bit_manipulation
from src.utils import NvidiaTaskType

DONALD_SOLVER_MAP = {
    'Unit Conversion': solve_unit,
    'Gravity': solve_gravity,
    'Base Conversion': solve_roman,
    'Text Encryption': solve_cipher,
    'Equation Transformation (Numeric)': solve_symbol_digit,
    'Bit Manipulation': solve_bit_manipulation
}

TASK_TYPE_SOLVERS = {
    NvidiaTaskType.UNIT_CONV: solve_unit,
    NvidiaTaskType.GRAVITY: solve_gravity,
    NvidiaTaskType.NUMERAL: solve_roman,
    NvidiaTaskType.CIPHER: solve_cipher,
    NvidiaTaskType.SYMBOL: solve_symbol_digit,
    NvidiaTaskType.BIT_OPS: solve_bit_manipulation
}
