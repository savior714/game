"""Bootstrap kernel — ensure repo root is importable for tools.tdd_gate_plugin."""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

pytest_plugins = ["tools.tdd_gate_plugin"]
