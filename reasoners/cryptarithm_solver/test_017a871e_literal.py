import itertools
import operator

def make_num(digits):
    return sum(d * (10**(len(digits)-1-i)) for i, d in enumerate(digits))

syms = ['\\', '!', '^', '{', '"', ']', '#', ':']

for p in itertools.permutations(range(10), 8):
    m = dict(zip(syms, p))
    
    # Try all 8 formatting pipelines
    for perm in ['ABCD', 'BADC', 'CDAB', 'DCBA']:
        if perm == 'ABCD':
            A1, B1 = [m['#'], m[']']], [m['\\'], m['#']]
            A2, B2 = [m['#'], m['^']], [m['{'], m[']']]
            A3, B3 = [m['\\'], m['{']], [m['\\'], m['!']]
        elif perm == 'BADC':
            A1, B1 = [m[']'], m['#']], [m['#'], m['\\']]
            A2, B2 = [m['^'], m['#']], [m[']'], m['{']]
            A3, B3 = [m['{'], m['\\']], [m['!'], m['\\']]
        elif perm == 'CDAB':
            A1, B1 = [m['\\'], m['#']], [m['#'], m[']']]
            A2, B2 = [m['{'], m[']']], [m['#'], m['^']]
            A3, B3 = [m['\\'], m['!']], [m['\\'], m['{']]
        elif perm == 'DCBA':
            A1, B1 = [m['#'], m['\\']], [m[']'], m['#']]
            A2, B2 = [m[']'], m['{']], [m['^'], m['#']]
            A3, B3 = [m['!'], m['\\']], [m['{'], m['\\']]
            
        valA1, valB1 = make_num(A1), make_num(B1)
        valA2, valB2 = make_num(A2), make_num(B2)
        valA3, valB3 = make_num(A3), make_num(B3)
        
        valOut1 = make_num([m['"'], m['!']])
        valOut2 = make_num([m[']'], m['#']])
        valOut3 = make_num([m['#'], m['\\'], m['^'], m[':']])
        
        res1_raw = valA1 + valB1
        res2_raw = valA2 - valB2
        res3_raw = valA3 * valB3
        
        for fmt in ['raw', 'rev', 'swap', 'zpad2']:
            def fmt_num(val):
                s = str(val)
                if fmt == 'raw': return s
                if fmt == 'rev': return s[::-1]
                if fmt == 'swap': return '-' + s[1:][::-1] if s.startswith('-') else s[::-1]
                if fmt == 'zpad2': return f"{val:02d}"
                
            if fmt_num(res1_raw) == str(valOut1) and fmt_num(res2_raw) == str(valOut2) and fmt_num(res3_raw) == str(valOut3):
                print(f"FOUND EXACT SOLUTION: {m}")
                print(f"Perm: {perm}, Fmt: {fmt}")
                
                # Target: #! - "^
                if perm == 'ABCD':
                    valTA, valTB = make_num([m['#'], m['!']]), make_num([m['"'], m['^']])
                elif perm == 'BADC':
                    valTA, valTB = make_num([m['!'], m['#']]), make_num([m['^'], m['"']])
                elif perm == 'CDAB':
                    valTA, valTB = make_num([m['"'], m['^']]), make_num([m['#'], m['!']])
                elif perm == 'DCBA':
                    valTA, valTB = make_num([m['^'], m['"']]), make_num([m['!'], m['#']])
                    
                ans = fmt_num(valTA - valTB)
                print(f"Target res: {ans}")
                
                # Encode answer
                inv_m = {v:k for k,v in m.items()}
                enc = ""
                for c in ans:
                    if c == '-': enc += '-'
                    else: enc += inv_m[int(c)]
                print(f"Encoded Target: {enc}")
                import sys; sys.exit(0)
