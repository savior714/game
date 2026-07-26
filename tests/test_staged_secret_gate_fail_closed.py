from __future__ import annotations

import subprocess

import pytest

from scripts.verify import staged_secret_gate


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
