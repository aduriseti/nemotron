def check_symmetry():
    # BADC -> rev vs DCBA -> swap
    
    A, B = 12, 34
    
    # BADC means A is [A1, A0], B is [B1, B0]
    badc_A = 21
    badc_B = 43
    
    # DCBA means B is [B1, B0], A is [A1, A0]
    dcba_A = 43
    dcba_B = 21
    
    # Let op be add
    badc_add = badc_A + badc_B # 64
    dcba_add = dcba_A + dcba_B # 64
    
    # rev(64) -> 46
    # swap(64) -> 46
    print(f"BADC add rev: {str(badc_add)[::-1]}")
    print(f"DCBA add swap: {str(dcba_add)[::-1]}")
    
    # Let op be sub_abs
    badc_sub = abs(badc_A - badc_B) # abs(21 - 43) = 22
    dcba_sub = abs(dcba_A - dcba_B) # abs(43 - 21) = 22
    print(f"BADC sub rev: {str(badc_sub)[::-1]}")
    print(f"DCBA sub swap: {str(dcba_sub)[::-1]}")
    
check_symmetry()
