from __future__ import annotations

import sys
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "bit_manipulation_solver"))

from bit_solver_v1_base import find_rule as _find_rule_infer
from reasoners.bit_manipulation_tt import reasoning_bit_manipulation_tt

reasoning_bit_manipulation_infer = partial(reasoning_bit_manipulation_tt, solver=_find_rule_infer)
