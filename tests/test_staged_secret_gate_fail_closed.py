from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "verify" / "staged_secret_gate.py"
)
MODULE_SPEC = importlib.util.spec_from_file_location(
    "staged_secret_gate_under_test",
    MODULE_PATH,
)
assert MODULE_SPEC is not None
assert MODULE_SPEC.loader is not None
staged_secret_gate = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = staged_secret_gate
MODULE_SPEC.loader.exec_module(staged_secret_gate)


@pytest.mark.parametrize(
    "error",
    [
        subprocess.CalledProcessError(128, ["git"], stderr="probe failure"),
        FileNotFoundError("git unavailable"),
    ],
)
def test_main_fails_closed_when_staged_file_collection_fails(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    def raise_collection_error(*_args: object, **_kwargs: object) -> None:
        raise error

    monkeypatch.setattr(staged_secret_gate.subprocess, "run", raise_collection_error)

    assert staged_secret_gate.main() == 1
