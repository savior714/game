"""Safety contract for scripts/verify_live_core_sync.py.

This script mutates production Supabase rows, so its two most important guarantees
must not depend on Python being run without optimization:

1. The mutation opt-in and credential gates must stay fail-closed even when
   ``-O``/``PYTHONOPTIMIZE`` strips ``assert`` statements. Otherwise the script
   becomes a fail-open mutation path against real user data.
2. A reported production restore must be proven by reading the rows back, not by
   the PATCH call merely not raising. A DB-side rule (for example an
   ``updated_at`` trigger) can make a write succeed while the stored state differs
   from the backup.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts" / "verify_live_core_sync.py"

sys.path.insert(0, str(ROOT / "scripts"))

import verify_live_core_sync as verifier  # noqa: E402


def _run_verifier(
    env_overrides: dict[str, str], *, optimize: bool
) -> subprocess.CompletedProcess:
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("AIDEN_SUPABASE_TEST_")
        and k != "AIDEN_SUPABASE_LIVE_SYNC_ALLOW_MUTATION"
    }
    env.update(env_overrides)
    if optimize:
        env["PYTHONOPTIMIZE"] = "1"
    else:
        env.pop("PYTHONOPTIMIZE", None)
    return subprocess.run(
        [sys.executable, str(VERIFIER)],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(ROOT),
    )


@pytest.mark.parametrize("optimize", [False, True], ids=["normal", "python_optimize"])
def test_mutation_requires_explicit_opt_in_under_any_optimization(optimize):
    """No opt-in means no mutation, and the refusal must survive ``-O``."""
    result = _run_verifier(
        {
            "AIDEN_SUPABASE_TEST_EMAIL": "nobody@example.invalid",
            "AIDEN_SUPABASE_TEST_PASSWORD": "x",
        },
        optimize=optimize,
    )
    assert result.returncode != 0, (
        "verifier must refuse to run without explicit mutation opt-in"
    )
    assert "Refusing live mutation" in result.stderr


@pytest.mark.parametrize("optimize", [False, True], ids=["normal", "python_optimize"])
def test_missing_credentials_are_fatal_under_any_optimization(optimize):
    """Opt-in without credentials must fail before any network mutation attempt."""
    result = _run_verifier(
        {"AIDEN_SUPABASE_LIVE_SYNC_ALLOW_MUTATION": "1"}, optimize=optimize
    )
    assert result.returncode != 0, "verifier must fail when credentials are missing"
    assert "AIDEN_SUPABASE_TEST_EMAIL" in result.stderr


def test_safety_gates_do_not_depend_on_strippable_asserts():
    """Guard against reintroducing ``assert`` as a live-mutation safety gate."""
    tree = ast.parse(VERIFIER.read_text(encoding="utf-8"))
    bare_asserts = [
        node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)
    ]
    assert not bare_asserts, (
        "scripts/verify_live_core_sync.py must not use bare assert statements: "
        f"they are stripped under -O/PYTHONOPTIMIZE, which makes the mutation gate "
        f"fail-open. Offending lines: {bare_asserts}"
    )


def _backup(
    key: str, payload: dict, updated_at: str = "2026-01-01T00:00:00+00:00"
) -> dict:
    return {"data_key": key, "payload": payload, "updated_at": updated_at}


def test_restore_verification_passes_on_exact_match(monkeypatch):
    backups = {"aiden_math_stats": _backup("aiden_math_stats", {"gems": 3})}
    monkeypatch.setattr(
        verifier, "_read_row", lambda *a, **k: backups["aiden_math_stats"]
    )
    assert verifier._verify_restored_rows("token", "user-1", backups) == []


def test_restore_verification_detects_payload_mismatch(monkeypatch):
    backups = {"aiden_math_stats": _backup("aiden_math_stats", {"gems": 3})}
    drifted = _backup("aiden_math_stats", {"gems": 99})
    monkeypatch.setattr(verifier, "_read_row", lambda *a, **k: drifted)
    mismatches = verifier._verify_restored_rows("token", "user-1", backups)
    assert any("payload not restored" in m for m in mismatches)


def test_restore_verification_detects_updated_at_drift(monkeypatch):
    """A silent updated_at trigger must not be reported as a successful restore."""
    backups = {"aiden_math_stats": _backup("aiden_math_stats", {"gems": 3})}
    retimed = _backup(
        "aiden_math_stats",
        {"gems": 3},
        updated_at="2026-10-06T12:00:00+00:00",
    )
    monkeypatch.setattr(verifier, "_read_row", lambda *a, **k: retimed)
    mismatches = verifier._verify_restored_rows("token", "user-1", backups)
    assert any("updated_at not restored" in m for m in mismatches)


def test_restore_verification_detects_missing_row(monkeypatch):
    backups = {"aiden_math_stats": _backup("aiden_math_stats", {"gems": 3})}
    monkeypatch.setattr(verifier, "_read_row", lambda *a, **k: None)
    mismatches = verifier._verify_restored_rows("token", "user-1", backups)
    assert any("row missing after restore" in m for m in mismatches)


def test_restore_verification_reports_read_failure_without_masking(monkeypatch):
    backups = {"aiden_math_stats": _backup("aiden_math_stats", {"gems": 3})}

    def _boom(*a, **k):
        raise RuntimeError("connection reset")

    monkeypatch.setattr(verifier, "_read_row", _boom)
    mismatches = verifier._verify_restored_rows("token", "user-1", backups)
    assert any("restore read-back failed" in m for m in mismatches)


def test_verifier_targets_the_five_canonical_core_sync_rows():
    assert verifier.SYNC_KEYS == (
        "study_rewards",
        "aiden_math_stats",
        "aiden_english_stats",
        "aiden_korean_stats",
        "aiden_science_stats",
    )
