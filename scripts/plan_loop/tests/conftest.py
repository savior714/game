"""plan_loop 테스트 — repo 루트 TDD gate 플러그인 로드."""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[3]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

pytest_plugins = ["tools.tdd_gate_plugin"]
