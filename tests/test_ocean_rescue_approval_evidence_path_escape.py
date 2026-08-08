"""Regression tests for approval evidence path containment."""

from __future__ import annotations

import pytest

from scripts.ocean_rescue import validate_art_approval as validator


def _record(contact_sheet: str) -> dict:
    return {
        "evidence": {
            "focusedTest": "tests/test_ocean_rescue_art_approval.py",
            "contactSheet": contact_sheet,
            "visualReviewVerdict": "PASS",
        }
    }


def test_evidence_path_cannot_escape_and_reenter(
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = "proof/../../review/proof-art-contact-sheet.html"

    with pytest.raises(SystemExit) as exc_info:
        validator.validate_evidence_paths(_record(path))

    assert exc_info.value.code == 1
    assert "path-traversal evidence path" in capsys.readouterr().err


def test_evidence_path_may_normalize_without_escaping() -> None:
    validator.validate_evidence_paths(
        _record("proof/../review/proof-art-contact-sheet.html")
    )
