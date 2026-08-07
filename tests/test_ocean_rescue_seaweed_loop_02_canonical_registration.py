"""Focused tests for seaweed-loop-02 canonical registration (B24)."""

from __future__ import annotations

import json
import pathlib
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_SVG = REPO_ROOT / "domains/ocean-rescue/assets/source/scene/seaweed-loop-02.svg"
PACKET_JSON = REPO_ROOT / "domains/ocean-rescue/assets/source/art-packet.json"
APPROVAL_JSON = REPO_ROOT / "domains/ocean-rescue/assets/source/art-approval.json"


def test_seaweed_loop_02_canonical_source_exists():
    assert SOURCE_SVG.exists()
    assert SOURCE_SVG.read_bytes().startswith(b'<svg')


def test_seaweed_loop_02_art_packet_entry():
    packet = json.loads(PACKET_JSON.read_text(encoding="utf-8"))
    assets = {a["alias"]: a for a in packet["assets"]}
    assert "scene.seaweed-loop.02" in assets
    loop02 = assets["scene.seaweed-loop.02"]
    assert loop02["id"] == "scene-seaweed-loop-02-01"
    assert loop02["bundle"] == "scene"
    assert loop02["logicalSize"] == [120, 200]
    assert loop02["pivot"] == [0.5, 0.1]
    assert loop02["sourceSha256"] == "cc655806372919858f95048b0bda0e26ef84ecfff2eb3b06e07fec167a358f3e"


def test_seaweed_loop_02_approval_receipt():
    approval = json.loads(APPROVAL_JSON.read_text(encoding="utf-8"))
    assert approval["approvedAssetCount"] == 54
    assert approval["evidence"]["visualReviewVerdict"] == "PASS"
