"""Emit cotl traces for 3 random bit_manipulation problems."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "bit_manipulation_solver"))

from bit_solver_tt import solve_bit_manipulation  # noqa: E402

from reasoners.cot_lang.bit_trace_emitter import emit_trace  # noqa: E402

ROOT = Path(__file__).parent.parent.parent
OUT = Path(__file__).parent / "traces"
OUT.mkdir(exist_ok=True)

# only sample arity-2 problems (program doesn't cover arity-3 yet)
all_entries = [
    json.loads(line)
    for line in (ROOT / "problems.jsonl").read_text().splitlines()
    if json.loads(line).get("category") == "bit_manipulation"
]

arity2_ids = []
for entry in all_entries:
    prob = json.loads((ROOT / "problems" / f"{entry['id']}.jsonl").read_text())
    _, _, rule_info = solve_bit_manipulation(prob["prompt"])
    if rule_info and rule_info[0] <= 2:
        arity2_ids.append(entry["id"])

random.seed(42)
sample = random.sample(arity2_ids, 3)

for pid in sample:
    prob = json.loads((ROOT / "problems" / f"{pid}.jsonl").read_text())
    print(f"[{pid}] solving...", end=" ", flush=True)
    solver_answer, trace_src = emit_trace(prob["prompt"])
    path = OUT / f"{pid}.cotl"
    path.write_text(trace_src)
    n_lines = trace_src.count("\n")
    print(f"answer={solver_answer}  lines={n_lines}  -> {path}")
