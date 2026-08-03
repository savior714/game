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


def test_main_fails_closed_when_trufflehog_exits_without_findings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def staged_files() -> list[str]:
        return ["safe.txt"]

    def not_sensitive(_path: str, _allowlist: list[str]) -> bool:
        return False

    def trufflehog_path(_name: str) -> str:
        return "/usr/bin/trufflehog"

    def scannable_paths(_staged_files: list[str]) -> list[str]:
        return ["safe.txt"]

    def failed_scan(
        *_args: object, **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["trufflehog"],
            returncode=2,
            stdout="",
            stderr="scanner failure",
        )

    monkeypatch.setattr(staged_secret_gate, "get_staged_files", staged_files)
    monkeypatch.setattr(staged_secret_gate, "is_sensitive_path", not_sensitive)
    monkeypatch.setattr(staged_secret_gate.shutil, "which", trufflehog_path)
    monkeypatch.setattr(staged_secret_gate, "staged_scannable_paths", scannable_paths)
    monkeypatch.setattr(staged_secret_gate.subprocess, "run", failed_scan)

    assert staged_secret_gate.main() == 1
