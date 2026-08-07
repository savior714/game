"""Focused tests for seaweed-loop-03 rebuilt proof approval receipt (B26)."""

from __future__ import annotations

import json
import pathlib
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
APPROVAL_JSON = REPO_ROOT / "domains/ocean-rescue/assets/source/art-approval.json"
CONTACT_SHEET = REPO_ROOT / "domains/ocean-rescue/assets/review/proof-art-contact-sheet.html"


def test_seaweed_loop_03_rebuilt_proof_approval_receipt():
    assert APPROVAL_JSON.exists()
    approval = json.loads(APPROVAL_JSON.read_text(encoding="utf-8"))
    assert approval["approvedAssetCount"] == 55
    assert approval["decision"] == "approved"
    assert approval["evidence"]["visualReviewVerdict"] == "PASS"
    assert "scene.seaweed-loop.03" in approval["approvedAliases"]


def test_seaweed_loop_03_contact_sheet_exists():
    assert CONTACT_SHEET.exists()
    content = CONTACT_SHEET.read_text(encoding="utf-8")
    assert "scene.seaweed-loop.03" in content
