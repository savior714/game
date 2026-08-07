"""Focused tests for seaweed-loop-03 handoff asset brief (B21)."""

from __future__ import annotations

import pathlib
import subprocess
import sys
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
BRIEF_MD = REPO_ROOT / "domains/ocean-rescue/assets/handoff/briefs/scene-seaweed-loop-03-01.md"
VALIDATOR_SCRIPT = REPO_ROOT / "scripts/ocean-rescue/validate-handoff-svg.py"


def test_seaweed_loop_03_brief_exists():
    assert BRIEF_MD.exists()
    content = BRIEF_MD.read_text(encoding="utf-8")
    assert "scene-seaweed-loop-03-01" in content
    assert "scene.seaweed-loop.03" in content
    assert "0 0 120 200" in content
    assert "scene-seaweed-loop-03" in content


def test_seaweed_loop_03_brief_parsable_by_validator():
    import importlib.util
    spec = importlib.util.spec_from_file_location("validate_handoff_svg", VALIDATOR_SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    brief_data = mod._parse_brief(BRIEF_MD)
    assert brief_data["assetId"] == "scene-seaweed-loop-03-01"
    assert brief_data["alias"] == "scene.seaweed-loop.03"
    assert brief_data["canonicalTarget"] == "domains/ocean-rescue/assets/source/scene/seaweed-loop-03.svg"
    assert brief_data["viewBox"] == "0 0 120 200"
    assert brief_data["rootGroup"] == "scene-seaweed-loop-03"
