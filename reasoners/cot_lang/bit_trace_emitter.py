"""Emit a flat cotl trace for a bit manipulation problem.

Loads the fixed program (programs/bit_manipulation.cotl) once and runs it
with problem-specific context ($ex0_in..$ex7_out, $query).
"""

from __future__ import annotations

import re
from pathlib import Path

_PROGRAM_PATH = Path(__file__).parent / "programs" / "bit_manipulation.cotl"
_PROGRAM_SRC: str | None = None


def _load_program() -> str:
    global _PROGRAM_SRC
    if _PROGRAM_SRC is None:
        _PROGRAM_SRC = _PROGRAM_PATH.read_text()
    return _PROGRAM_SRC


def _parse_context(prompt: str) -> dict:
    ex_matches = re.findall(r"([01]{8})\s*->\s*([01]{8})", prompt)
    qm = re.search(
        r"(?:output for:|determine the output for:)\s*([01]{8})",
        prompt,
        re.IGNORECASE,
    )
    ctx: dict = {}
    for i, (in_s, out_s) in enumerate(ex_matches):
        ctx[f"ex{i}_in"] = in_s
        ctx[f"ex{i}_out"] = out_s
    ctx["query"] = qm.group(1)
    return ctx


def emit_trace(prompt: str) -> tuple[str, str]:
    """Return (answer, cotl_trace) by running the fixed program with problem context."""
    from reasoners.cot_lang.interpreter import Interpreter  # noqa: PLC0415

    context = _parse_context(prompt)
    program = _load_program()
    answer, trace_lines = Interpreter().run(program, context)
    return answer, "\n".join(trace_lines) + "\n"
