"""Verify solve_v4 handles sub / sub_abs / sub_neg_abs puzzles.

Restriction: only puzzles where every training example AND the target query use
an op in {sub, sub_abs, sub_neg_abs}. Puzzles containing examples with ops
outside that set (add, mul, mulm1, max_mod_min, etc.) are skipped — those are
out of scope for v4 regardless of search quality.

Assertion: the golden answer must appear among the answers v4 produces (across
all valid ciphers it discovers). Allows the puzzle to be ambiguous.

The golden cipher is reverse-engineered with the baseline (full-op) solver to
classify each example's op without trusting v4.

Run:
    uv run pytest reasoners/cryptarithm_solver/test_v4_sub_coverage.py -v
    uv run pytest reasoners/cryptarithm_solver/test_v4_sub_coverage.py -v -k sub_neg_abs
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from reasoners.store_types import Problem
from reasoners.cryptarithm_solver.python_solver import (
    extract_all_examples,
    _search,
    _plausible_ops,
    FORMATTERS,
)
from reasoners.cryptarithm_solver.python_solver_arith_abs import solve_v4_all_answers

_INDEX = Path(__file__).parent / "op_index.json"
TARGET_OPS = ("sub", "sub_abs", "sub_neg_abs")
ALLOWED_GOLDEN_OPS = frozenset(TARGET_OPS)
BASELINE_DEADLINE = 5.0


def _find_golden_op_assign(prompt: str) -> dict[str, str] | None:
    """Run baseline _search across all pipelines; return op_assign of first cipher."""
    extraction = extract_all_examples(prompt)
    parsed_examples = extraction[0]
    if parsed_examples is None:
        return None
    for f_type in FORMATTERS:
        plausible = []
        skip = False
        for ex in parsed_examples:
            ops = _plausible_ops(ex)
            if not ops:
                skip = True
                break
            plausible.append(ops)
        if skip:
            continue
        sols: list = []
        _search(parsed_examples, 0, {}, set(), {}, plausible,
                f_type, sols, time.time() + BASELINE_DEADLINE, max_solutions=1)
        if sols:
            _, op_assign = sols[0]
            return op_assign
    return None


def _load_cases():
    with open(_INDEX) as f:
        op_index = json.load(f)

    cases = []
    skipped_no_cipher = 0
    skipped_unsupported_example_op = 0
    for p in Problem.load_all():
        if "cryptarithm" not in p.category:
            continue
        target = op_index.get(p.id, {}).get("target_op")
        if target not in TARGET_OPS:
            continue

        op_assign = _find_golden_op_assign(p.prompt)
        if op_assign is None:
            skipped_no_cipher += 1
            continue

        # Strict filter: every op-symbol in this puzzle (covering every example
        # AND the target query) must map to an op in ALLOWED_GOLDEN_OPS.
        if any(op not in ALLOWED_GOLDEN_OPS for op in op_assign.values()):
            skipped_unsupported_example_op += 1
            continue

        cases.append(
            pytest.param(
                p.prompt, str(p.answer), target,
                id=f"{target}/{p.id[:8]}",
            )
        )

    print(
        f"\n[v4_sub_coverage] cases={len(cases)} "
        f"skipped_no_baseline_cipher={skipped_no_cipher} "
        f"skipped_unsupported_example_op={skipped_unsupported_example_op}",
        file=sys.stderr,
    )
    return cases


@pytest.mark.parametrize("prompt,expected,op", _load_cases())
def test_solve_v4_sub_variant(prompt: str, expected: str, op: str) -> None:
    answers = solve_v4_all_answers(prompt)
    assert expected in answers, (
        f"[{op}] expected {expected!r} not in v4 answers (n={len(answers)}): "
        f"{sorted(answers)[:10]}"
    )
