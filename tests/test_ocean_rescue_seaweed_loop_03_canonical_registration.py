"""Focused tests for seaweed-loop-03 canonical registration (B24)."""

from __future__ import annotations

import json
import pathlib
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_SVG = REPO_ROOT / "domains/ocean-rescue/assets/source/scene/seaweed-loop-03.svg"
PACKET_JSON = REPO_ROOT / "domains/ocean-rescue/assets/source/art-packet.json"
APPROVAL_JSON = REPO_ROOT / "domains/ocean-rescue/assets/source/art-approval.json"


def test_seaweed_loop_03_canonical_source_exists():
    assert SOURCE_SVG.exists()
    assert SOURCE_SVG.read_bytes().startswith(b'<svg')


def test_seaweed_loop_03_art_packet_entry():
    packet = json.loads(PACKET_JSON.read_text(encoding="utf-8"))
    assets = {a["alias"]: a for a in packet["assets"]}
    assert "scene.seaweed-loop.03" in assets
    loop03 = assets["scene.seaweed-loop.03"]
    assert loop03["id"] == "scene-seaweed-loop-03-01"
    assert loop03["bundle"] == "scene"
    assert loop03["logicalSize"] == [120, 200]
    assert loop03["pivot"] == [0.5, 0.1]
    assert loop03["sourceSha256"] == "e01585f8fd1b995dd7c7081710332b2a4b7db729dfc08326c209f76e98a278b7"


def test_seaweed_loop_03_approval_receipt():
    approval = json.loads(APPROVAL_JSON.read_text(encoding="utf-8"))
    assert approval["approvedAssetCount"] == 55
    assert approval["evidence"]["visualReviewVerdict"] == "PASS"
    assert "scene.seaweed-loop.03" in approval["approvedAliases"]
