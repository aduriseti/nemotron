"""Emit cotl traces for 3 random bit_manipulation problems."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from reasoners.cot_lang.bit_trace_emitter import emit_trace  # noqa: E402
from reasoners.cot_lang.interpreter import Interpreter  # noqa: E402

ROOT = Path(__file__).parent.parent.parent
OUT = Path(__file__).parent / "traces"
OUT.mkdir(exist_ok=True)

ids = [
    e["id"]
    for e in (
        json.loads(line)
        for line in (ROOT / "problems.jsonl").read_text().splitlines()
    )
    if e.get("category") == "bit_manipulation"
]

random.seed(42)
sample = random.sample(ids, 3)

for pid in sample:
    prob = json.loads((ROOT / "problems" / f"{pid}.jsonl").read_text())
    print(f"[{pid}] solving...", end=" ", flush=True)
    solver_answer, trace_src = emit_trace(prob["prompt"])
    _, executed = Interpreter().run(trace_src)
    executed_text = "\n".join(executed) + "\n"
    path = OUT / f"{pid}.cotl"
    path.write_text(executed_text)
    n_lines = len(executed)
    print(f"answer={solver_answer}  lines={n_lines}  -> {path}")
