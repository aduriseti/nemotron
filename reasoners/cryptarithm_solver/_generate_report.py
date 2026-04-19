"""Generate solver comparison report."""
import sys, time, re
sys.path.insert(0, '/workspaces/nemotron')

from reasoners.store_types import Problem
from reasoners.cryptarithm_solver.ortools_solver import solve_cipher_unified as ort_solve
from reasoners.cryptarithm_solver.python_solver import solve_cipher_unified as py_solve
from reasoners.cryptarithm_solver.python_solver import extract_all_examples

problems = [p for p in Problem.load_all() if p.category == 'cryptarithm_deduce'][:30]

def _missing_target_syms(p):
    exs, tA, tB, _ = extract_all_examples(p.prompt)
    if exs is None:
        return set()
    all_ex_syms = set()
    for ex in exs:
        all_ex_syms.update(ex['A'] + ex['B'] + ex['out'])
    return (set(tA + tB)) - all_ex_syms

def _prompt_condensed(prompt):
    lines = [l.strip() for l in prompt.split('\n') if l.strip() and 'Wonderland' not in l and 'secret' not in l and 'transformation' not in l and 'applied' not in l]
    return '  /  '.join(lines)

rows = []
print("Running solvers on 30 problems...")
for i, p in enumerate(problems):
    print(f"  {i+1}/30 {p.id[:8]}...", end='\r')

    t0 = time.time()
    ort_votes = ort_solve(p.prompt, mode=None, target_answer=p.answer) or {}
    ort_t = time.time() - t0
    ort_ans = max(ort_votes, key=ort_votes.get) if ort_votes else None

    t0 = time.time()
    py_votes = py_solve(p.prompt, mode=None, target_answer=p.answer) or {}
    py_t = time.time() - t0
    py_ans = max(py_votes, key=py_votes.get) if py_votes else None

    golden = str(p.answer)
    ort_ok = str(ort_ans) == golden
    py_ok  = str(py_ans)  == golden
    ort_found = golden in ort_votes
    py_found  = golden in py_votes
    missing   = _missing_target_syms(p)

    if ort_ok and py_ok:       cat = 'both_correct'
    elif ort_ok and not py_ok: cat = 'ort_only'
    elif py_ok and not ort_ok: cat = 'py_only'
    elif ort_ans is None and py_ans is None: cat = 'both_none'
    else:                      cat = 'both_wrong'

    ort_mode = None
    if not ort_ok:
        if ort_ans is None:
            ort_mode = 'no_solutions'
        elif ort_found:
            ort_mode = 'found_not_selected'
        else:
            ort_mode = 'wrong_answer'

    py_mode = None
    if not py_ok:
        if py_ans is None:
            py_mode = 'missing_target_sym' if missing else 'no_solutions'
        elif py_found:
            py_mode = 'found_not_selected'
        else:
            py_mode = 'wrong_answer'

    rows.append({
        'id': p.id, 'prompt': p.prompt, 'condensed': _prompt_condensed(p.prompt),
        'golden': golden,
        'ort_ans': str(ort_ans) if ort_ans else 'None',
        'ort_votes': ort_votes, 'ort_t': ort_t, 'ort_ok': ort_ok,
        'ort_found': ort_found, 'ort_mode': ort_mode,
        'py_ans': str(py_ans) if py_ans else 'None',
        'py_votes': py_votes, 'py_t': py_t, 'py_ok': py_ok,
        'py_found': py_found, 'py_mode': py_mode,
        'cat': cat, 'missing_syms': missing,
    })

print("\nDone. Writing report...")

# ---------------------------------------------------------------------------
# Counts
# ---------------------------------------------------------------------------
cats = {c: sum(1 for r in rows if r['cat'] == c)
        for c in ['both_correct','ort_only','py_only','both_wrong','both_none']}
ort_found_not_sel = sum(1 for r in rows if r['ort_mode'] == 'found_not_selected')
py_found_not_sel  = sum(1 for r in rows if r['py_mode']  == 'found_not_selected')
ort_no_sol  = sum(1 for r in rows if r['ort_mode'] == 'no_solutions')
py_no_sol   = sum(1 for r in rows if r['py_mode']  == 'no_solutions')
py_miss_sym = sum(1 for r in rows if r['py_mode']  == 'missing_target_sym')
ort_wrong   = sum(1 for r in rows if r['ort_mode'] == 'wrong_answer')
py_wrong    = sum(1 for r in rows if r['py_mode']  == 'wrong_answer')

# ---------------------------------------------------------------------------
# Write report
# ---------------------------------------------------------------------------
lines = []
def w(*args): lines.append(' '.join(str(a) for a in args))

w('# Solver Comparison Report: OR-Tools vs Python')
w()
w(f'**Problems evaluated:** 30 cryptarithm_deduce  ')
w(f'**OR-Tools accuracy:** {cats["both_correct"]+cats["ort_only"]}/30  ')
w(f'**Python accuracy:** {cats["both_correct"]+cats["py_only"]}/30  ')
w()

w('## Summary')
w()
w('| Category | Count |')
w('|---|---|')
w(f'| Both correct | {cats["both_correct"]} |')
w(f'| Only OR-Tools correct | {cats["ort_only"]} |')
w(f'| Only Python correct | {cats["py_only"]} |')
w(f'| Both wrong (different answers) | {cats["both_wrong"]} |')
w(f'| Both returned None | {cats["both_none"]} |')
w(f'| **OR-Tools**: correct found but not selected (voting loss) | {ort_found_not_sel} |')
w(f'| **Python**: correct found but not selected (voting loss) | {py_found_not_sel} |')
w()

w('## Failure Mode Breakdown')
w()
w('### OR-Tools failures')
w(f'- **No solutions found**: {ort_no_sol}')
w(f'- **Wrong answer selected** (correct not in candidates): {ort_wrong}')
w(f'- **Correct found but voting loss**: {ort_found_not_sel}')
w()
w('### Python failures')
w(f'- **Missing target symbol** (symbol in target not in any training example): {py_miss_sym}')
w(f'- **No solutions found** (other): {py_no_sol}')
w(f'- **Wrong answer selected** (correct not in candidates): {py_wrong}')
w(f'- **Correct found but voting loss**: {py_found_not_sel}')
w()

w('---')
w()
w('## Per-Problem Detail')
w()

for r in rows:
    exs, tA, tB, tgt_op = extract_all_examples(r['prompt'])
    examples_str = '  '.join(
        f"`{''.join(ex['A'])}{ex['op']}{''.join(ex['B'])}={''.join(ex['out'])}`"
        for ex in (exs or [])
    )
    target_str = f"`{''.join(tA)}{tgt_op}{''.join(tB)}=?`"

    w(f'### {r["id"][:8]}')
    w()
    w(f'**Target:** {target_str}  ')
    w(f'**Examples:** {examples_str}  ')
    w(f'**Golden answer:** `{r["golden"]}`  ')
    w(f'**Category:** `{r["cat"]}`  ')
    if r['missing_syms']:
        w(f'**Missing target symbols:** `{r["missing_syms"]}` *(appear in target but not in any training example)*  ')
    w()

    w('| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |')
    w('|---|---|---|---|---|---|---|')

    ort_cands = ', '.join(f'`{a}`:{v}' for a, v in sorted(r['ort_votes'].items(), key=lambda x: -x[1])) or '—'
    py_cands  = ', '.join(f'`{a}`:{v}' for a, v in sorted(r['py_votes'].items(),  key=lambda x: -x[1])) or '—'

    ort_found_tag = '✓' if r['ort_found'] else ('—' if r['ort_ans'] == 'None' else '✗')
    py_found_tag  = '✓' if r['py_found']  else ('—' if r['py_ans']  == 'None' else '✗')

    w(f'| OR-Tools | `{r["ort_ans"]}` | {"✓" if r["ort_ok"] else "✗"} | {ort_found_tag} | {ort_cands} | {r["ort_t"]:.2f}s | {r["ort_mode"] or "—"} |')
    w(f'| Python   | `{r["py_ans"]}`  | {"✓" if r["py_ok"]  else "✗"} | {py_found_tag}  | {py_cands}  | {r["py_t"]:.2f}s  | {r["py_mode"]  or "—"} |')
    w()

out_path = '/workspaces/nemotron/reasoners/cryptarithm_solver/solver_comparison_report.md'
with open(out_path, 'w') as f:
    f.write('\n'.join(lines))

print(f"Report written to {out_path}")
print(f"Both correct: {cats['both_correct']}  ORT only: {cats['ort_only']}  PY only: {cats['py_only']}  Both wrong: {cats['both_wrong']}  Both none: {cats['both_none']}")
