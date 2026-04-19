"""Benchmark ortools_solver vs python_solver on 30 cryptarithm_deduce problems."""
import sys, time
sys.path.insert(0, '/workspaces/nemotron')

from reasoners.store_types import Problem
from reasoners.cryptarithm_solver.ortools_solver import solve_cipher_unified as ort_solve
from reasoners.cryptarithm_solver.python_solver import solve_cipher_unified as py_solve

problems = [p for p in Problem.load_all() if p.category == 'cryptarithm_deduce'][:30]
print(f"Loaded {len(problems)} problems\n")
print(f"{'id':10} {'exp':8} {'ort':8} {'py':8} {'ok_o':5} {'ok_p':5} {'t_o':7} {'t_p':7}")
print('-' * 65)

results = []
for p in problems:
    exp = str(p.answer)

    t0 = time.time()
    ort_ans = ort_solve(p.prompt, mode='greedy', target_answer=p.answer)
    ort_t = time.time() - t0
    ort_ans = str(ort_ans) if ort_ans is not None else 'None'

    t0 = time.time()
    py_ans = py_solve(p.prompt, mode='greedy', target_answer=p.answer)
    py_t = time.time() - t0
    py_ans = str(py_ans) if py_ans is not None else 'None'

    ort_ok = ort_ans == exp
    py_ok  = py_ans  == exp
    results.append(dict(ort_ok=ort_ok, py_ok=py_ok, ort_t=ort_t, py_t=py_t,
                        ort_ans=ort_ans, py_ans=py_ans, exp=exp))
    print(f"{p.id[:10]:10} {exp!r:8} {ort_ans!r:8} {py_ans!r:8} "
          f"{'✓' if ort_ok else '✗':5} {'✓' if py_ok else '✗':5} "
          f"{ort_t:6.2f}s {py_t:6.2f}s")

n = len(results)
ort_acc = sum(r['ort_ok'] for r in results)
py_acc  = sum(r['py_ok']  for r in results)
agree   = sum(r['ort_ans'] == r['py_ans'] for r in results)
ort_avg = sum(r['ort_t'] for r in results) / n
py_avg  = sum(r['py_t']  for r in results) / n

print(f"\n{'='*65}")
print(f"OR-Tools : {ort_acc}/{n} correct  avg={ort_avg:.3f}s  total={sum(r['ort_t'] for r in results):.1f}s")
print(f"Python   : {py_acc}/{n} correct  avg={py_avg:.3f}s  total={sum(r['py_t'] for r in results):.1f}s")
print(f"Agreement: {agree}/{n}")
if ort_avg > 0:
    print(f"Slowdown : {py_avg/ort_avg:.1f}x")
