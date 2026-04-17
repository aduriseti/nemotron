problems = [
    {
        'id': '00457d26',
        'map': {0: '>', 1: '@', 2: "'", 3: '\\', 4: '[', 5: '`', 6: '!', 7: '"', 8: '&', 9: '{'},
        'equations': [
            ("`!", "[{", "'\"[`"),
            ("\\'", "'>", "![@"),
            ("\\'", "!`", "\\\\"),
            ("`!", "\\&", "'@'{")
        ]
    }
]

for p in problems:
    print(f"\n--- Problem {p['id']} ---")
    m = p['map']
    inv_m = {v: k for k, v in m.items()}
    
    for A, B, out in p['equations']:
        valA = int("".join(str(inv_m[c]) for c in A))
        valB = int("".join(str(inv_m[c]) for c in B))
        valOut = int("".join(str(inv_m[c]) for c in out))
        
        asciiA = sum(ord(c) for c in A)
        asciiB = sum(ord(c) for c in B)
        asciiOut = sum(ord(c) for c in out)
        
        print(f"Eq: {A} op {B} = {out}")
        print(f"  Values: A={valA:02d}, B={valB:02d}, Out={valOut}")
        print(f"  ASCII Sums: A={asciiA}, B={asciiB}, Out={asciiOut}")
        print(f"  ASCII % 100: A={asciiA%100}, B={asciiB%100}, Out={asciiOut%100}")
        print(f"  ASCII // 10: A={asciiA//10}, B={asciiB//10}, Out={asciiOut//10}")
        
        # Look for combinations
        print(f"  (valA + asciiA) = {valA + asciiA}")
        print(f"  Chars ASCII: A={[ord(c) for c in A]}, B={[ord(c) for c in B]}")
        
        for c in A:
            print(f"    Char '{c}': Val={inv_m[c]}, ASCII={ord(c)}, ASCII%10={ord(c)%10}, ASCII//10={ord(c)//10}, ASCII%26={ord(c)%26}")
            
