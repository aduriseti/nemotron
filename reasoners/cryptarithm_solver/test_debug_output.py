import sys
import os

WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path: sys.path.append(WORKSPACE_DIR)

from reasoners.cryptarithm_solver.constraint_solver import PRE_OPS, MID_OPS, POST_OPS

def test_fdbdf50c_logic():
    """
    Tests the exact mathematical chain for PROBLEM fdbdf50c Eq 1.
    Cipher: {8: '?', 5: '|', 1: '^', 6: '<', 3: '\\', 2: '"', 0: '%', 7: "'", 4: ']', 9: ')'}
    Pipeline: BADC -> sub_abs -> rev
    Eq: %? - )\ = ^]
    """
    # 1. Setup the digits from the cipher mapping
    # symbols: % (0), ? (8) | ) (9), \ (3)
    A_vals = [0, 8]  # %?
    B_vals = [9, 3]  # )\
    
    # 2. Apply Permutation (BADC)
    # BADC on A1A0, B1B0 -> A0A1, B0B1
    # [0, 8] becomes [8, 0] -> 80
    # [9, 3] becomes [3, 9] -> 39
    L, R, _, _, _, _ = PRE_OPS['BADC'](A_vals, B_vals)
    assert L == 80
    assert R == 39
    
    # 3. Apply Math (sub_abs)
    res_raw = MID_OPS['sub_abs'](L, R, 0, 0, 0, 0)
    assert res_raw == 41
    
    # 4. Apply Formatting (rev)
    # rev(41) -> "14"
    res_str = str(res_raw)
    res_abs = res_str.replace('-', '')
    res_fmt = POST_OPS['rev'](res_abs)
    
    assert res_fmt == "14"
    
    # 5. Verify against expected symbols ( ^ is 1, ] is 4 )
    # RHS is ^] -> 14
    print(f"Test Passed for fdbdf50c logic!")
    print(f"  LHS: {A_vals} {B_vals} (BADC) -> {L} {R}")
    print(f"  Math: {L} sub_abs {R} = {res_raw}")
    print(f"  Fmt: rev({res_raw}) = '{res_fmt}'")
    print(f"  Matches RHS symbols: ^ (1) ] (4) -> '14'")

if __name__ == "__main__":
    test_fdbdf50c_logic()
