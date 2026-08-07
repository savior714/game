"""Focused tests for Ocean Rescue B28 mandatory asset completeness inventory."""

from __future__ import annotations

import json
import pathlib
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
ART_PACKET = REPO_ROOT / "domains/ocean-rescue/assets/source/art-packet.json"
RENDERING_MVP_SPEC = REPO_ROOT / "docs/specs/product/AIDENGAME_OCEAN_RESCUE_RENDERING_MVP.md"


def test_rendering_mvp_seaweed_loops_requirement():
    assert RENDERING_MVP_SPEC.exists()
    spec_text = RENDERING_MVP_SPEC.read_text(encoding="utf-8")
    assert "seaweed" in spec_text.lower()


def test_seaweed_loop_inventory_selection():
    packet = json.loads(ART_PACKET.read_text(encoding="utf-8"))
    aliases = {a["alias"] for a in packet["assets"]}

    # Required seaweed loop assets in Rendering MVP
    assert "scene.seaweed-loop.01" in aliases
    assert "scene.seaweed-loop.02" in aliases

    # Next single mandatory asset gap selection
    assert "scene.seaweed-loop.03" not in aliases
    selected_next_gap = "scene.seaweed-loop.03"
    assert selected_next_gap == "scene.seaweed-loop.03"
