"""Verify cotl traces for bit_manipulation problems.

Loads 2 bit_manipulation problems, emits a cotl trace for each,
runs the interpreter, and checks the answer matches both the solver
and the golden answer from the dataset.

Usage:
    uv run reasoners/cot_lang/verify_bit.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from reasoners.cot_lang.bit_trace_emitter import emit_trace  # noqa: E402
from reasoners.cot_lang.interpreter import Interpreter  # noqa: E402

INDEX = ROOT / "problems.jsonl"
PROBLEMS_DIR = ROOT / "problems"


def load_problems(n: int = 2, category: str = "bit_manipulation") -> list[dict]:
    problems = []
    with INDEX.open() as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("category") == category:
                path = PROBLEMS_DIR / f"{entry['id']}.jsonl"
                with path.open() as pf:
                    prob = json.loads(pf.readline())
                problems.append(prob)
                if len(problems) >= n:
                    break
    return problems


def main() -> None:
    problems = load_problems(2)
    if not problems:
        print("No bit_manipulation problems found.")
        sys.exit(1)

    all_pass = True
    for prob in problems:
        pid = prob["id"]
        print(f"\n{'=' * 60}")
        print(f"Problem {pid}")
        print(f"{'=' * 60}")

        solver_answer, trace_src = emit_trace(prob["prompt"])
        print(trace_src)

        interp = Interpreter()
        interp_answer, _ = interp.run(trace_src)

        golden = prob["answer"]
        ok_solver = interp_answer == solver_answer
        ok_golden = interp_answer == golden

        print(f"Interpreter answer : {interp_answer!r}")
        print(f"Solver answer      : {solver_answer!r}")
        print(f"Golden answer      : {golden!r}")

        if ok_solver and ok_golden:
            print("PASS")
        else:
            print("FAIL")
            if not ok_solver:
                print("  MISMATCH: interpreter != solver")
            if not ok_golden:
                print("  MISMATCH: interpreter != golden")
            all_pass = False

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
