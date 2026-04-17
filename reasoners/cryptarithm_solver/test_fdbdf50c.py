import sys
WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path: sys.path.append(WORKSPACE_DIR)
from reasoners.cryptarithm_solver.constraint_solver import solve_cipher_unified

prompt = r"""In Alice's Wonderland, a secret set of transformation rules is applied to equations. Below are a few examples:
%?-)\ = ^]
??-?? = %
<^}"| = ?<
]^(?] = "'<
)'-?" = ^|
Now, determine the result for: |\-?|"""

print("Testing problem fdbdf50c...")
pred = solve_cipher_unified(prompt, mode='all')
print(f"\nFinal possible answers: {pred}")
