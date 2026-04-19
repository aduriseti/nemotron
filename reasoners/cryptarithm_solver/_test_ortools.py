import sys
sys.path.insert(0, '/workspaces/nemotron')

from reasoners.store_types import Problem
from reasoners.cryptarithm_solver.ortools_solver import solve_cipher_unified
import time

LOG = '/tmp/ortools_30.log'
open(LOG, 'w').close()  # clear

problems = [p for p in Problem.load_all() if p.category == 'cryptarithm_deduce']
print(f"Loaded {len(problems)} problems\n")

correct = 0
for p in problems[:30]:
    t0 = time.time()
    result = solve_cipher_unified(p.prompt, mode='greedy', target_answer=p.answer, log_path=LOG)
    elapsed = time.time() - t0
    ok = str(result) == str(p.answer)
    if ok: correct += 1
    print(f"{'✓' if ok else '✗'} {p.id}: expected={p.answer!r} got={result!r} ({elapsed:.2f}s)")

print(f"\n{correct}/30 correct")
