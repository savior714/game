"""Focused tests for Ocean Rescue B28 final mandatory asset completeness inventory."""

from __future__ import annotations

import json
import pathlib
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
ART_PACKET = REPO_ROOT / "domains/ocean-rescue/assets/source/art-packet.json"
ART_APPROVAL = REPO_ROOT / "domains/ocean-rescue/assets/source/art-approval.json"
RENDERING_MVP_SPEC = REPO_ROOT / "docs/specs/product/AIDENGAME_OCEAN_RESCUE_RENDERING_MVP.md"


def test_seaweed_loops_all_three_present_and_approved():
    packet = json.loads(ART_PACKET.read_text(encoding="utf-8"))
    approval = json.loads(ART_APPROVAL.read_text(encoding="utf-8"))
    aliases = {a["alias"] for a in packet["assets"]}
    approved_aliases = set(approval["approvedAliases"])

    # All three required seaweed loops must be present and approved
    assert "scene.seaweed-loop.01" in aliases
    assert "scene.seaweed-loop.02" in aliases
    assert "scene.seaweed-loop.03" in aliases

    assert "scene.seaweed-loop.01" in approved_aliases
    assert "scene.seaweed-loop.02" in approved_aliases
    assert "scene.seaweed-loop.03" in approved_aliases


def test_rendering_mvp_total_asset_count_completeness():
    packet = json.loads(ART_PACKET.read_text(encoding="utf-8"))
    approval = json.loads(ART_APPROVAL.read_text(encoding="utf-8"))

    assert len(packet["assets"]) == 55
    assert approval["approvedAssetCount"] == 55
    assert approval["decision"] == "approved"
    assert approval["evidence"]["visualReviewVerdict"] == "PASS"
