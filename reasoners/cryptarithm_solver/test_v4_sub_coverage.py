"""Verify solve_v4 handles sub / sub_abs / sub_neg_abs puzzles.

Design assumption: all three op types are covered by the `sub` math-op under
the four pipeline orderings (raw / swap / rev / rev_swap) — no special-case
handling for sub_abs or sub_neg_abs is needed.

Run:
    uv run pytest reasoners/cryptarithm_solver/test_v4_sub_coverage.py -v
    uv run pytest reasoners/cryptarithm_solver/test_v4_sub_coverage.py -v -k sub_neg_abs
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from reasoners.store_types import Problem
from reasoners.cryptarithm_solver.python_solver_arith_abs import solve_v4

_INDEX = Path(__file__).parent / "op_index.json"
TARGET_OPS = ("sub", "sub_abs", "sub_neg_abs")


def _load_cases():
    with open(_INDEX) as f:
        op_index = json.load(f)
    cases = []
    for p in Problem.load_all():
        if "cryptarithm" not in p.category:
            continue
        op = op_index.get(p.id, {}).get("target_op")
        if op not in TARGET_OPS:
            continue
        cases.append(
            pytest.param(
                p.prompt, str(p.answer), op,
                id=f"{op}/{p.id[:8]}",
            )
        )
    return cases


@pytest.mark.parametrize("prompt,expected,op", _load_cases())
def test_solve_v4_sub_variant(prompt: str, expected: str, op: str) -> None:
    got = solve_v4(prompt)
    assert str(got) == expected, f"[{op}] expected {expected!r}, got {got!r}"
