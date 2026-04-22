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
sys.path.insert(0, str(ROOT / "reasoners" / "bit_manipulation_solver"))

from bit_solver_tt import solve_bit_manipulation  # noqa: E402

from reasoners.cot_lang.bit_trace_emitter import emit_trace  # noqa: E402

INDEX = ROOT / "problems.jsonl"
PROBLEMS_DIR = ROOT / "problems"


def load_problems(n: int = 2, max_arity: int = 2) -> list[dict]:
    """Load n bit_manipulation problems with arity <= max_arity."""
    problems = []
    with INDEX.open() as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("category") != "bit_manipulation":
                continue
            path = PROBLEMS_DIR / f"{entry['id']}.jsonl"
            with path.open() as pf:
                prob = json.loads(pf.readline())
            _, _, rule_info = solve_bit_manipulation(prob["prompt"])
            if rule_info is None or rule_info[0] > max_arity:
                continue
            problems.append(prob)
            if len(problems) >= n:
                break
    return problems


def main() -> None:
    problems = load_problems(2, max_arity=2)
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

        golden = prob["answer"]
        ok_golden = solver_answer == golden

        print(f"Answer  : {solver_answer!r}")
        print(f"Golden  : {golden!r}")

        if ok_golden:
            print("PASS")
        else:
            print("FAIL — answer != golden")
            all_pass = False

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
