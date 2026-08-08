"""Focused tests for seaweed-loop-03 B -> A producer handoff verification (B27)."""

from __future__ import annotations

import hashlib
import json
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Seven Track B producer deliverables required for Track A runtime consumption
SOURCE_SVG = REPO_ROOT / "domains/ocean-rescue/assets/source/scene/seaweed-loop-03.svg"
ART_PACKET = REPO_ROOT / "domains/ocean-rescue/assets/source/art-packet.json"
ART_APPROVAL = REPO_ROOT / "domains/ocean-rescue/assets/source/art-approval.json"
ATLAS_PNG = REPO_ROOT / "domains/ocean-rescue/assets/generated/scene/scene-0.png"
ATLAS_JSON = REPO_ROOT / "domains/ocean-rescue/assets/generated/scene/scene-0.json"
ATLAS_MANIFEST = REPO_ROOT / "domains/ocean-rescue/assets/generated/atlas-manifest.json"
REGISTRY_JS = REPO_ROOT / "domains/ocean-rescue/src/render-assets.generated.js"


def test_b_to_a_producer_deliverables_exist():
    assert SOURCE_SVG.exists()
    assert ART_PACKET.exists()
    assert ART_APPROVAL.exists()
    assert ATLAS_PNG.exists()
    assert ATLAS_JSON.exists()
    assert ATLAS_MANIFEST.exists()
    assert REGISTRY_JS.exists()


def test_b_to_a_producer_source_hash_binding():
    svg_bytes = SOURCE_SVG.read_bytes()
    expected_hash = hashlib.sha256(svg_bytes).hexdigest()

    packet = json.loads(ART_PACKET.read_text(encoding="utf-8"))
    assets = {a["alias"]: a for a in packet["assets"]}
    assert "scene.seaweed-loop.03" in assets
    loop03_packet = assets["scene.seaweed-loop.03"]
    assert loop03_packet["sourceSha256"] == expected_hash

    approval = json.loads(ART_APPROVAL.read_text(encoding="utf-8"))
    assert "scene.seaweed-loop.03" in approval["approvedAliases"]
    assert approval["evidence"]["visualReviewVerdict"] == "PASS"


def test_b_to_a_producer_runtime_atlas_contract():
    atlas_data = json.loads(ATLAS_JSON.read_text(encoding="utf-8"))
    frames = atlas_data.get("frames", {})
    assert "scene.seaweed-loop.03" in frames
    frame_info = frames["scene.seaweed-loop.03"]
    assert frame_info["anchor"] == {"x": 0.5, "y": 0.1}
    assert frame_info["sourceSize"] == {"w": 240, "h": 400}

    registry_content = REGISTRY_JS.read_text(encoding="utf-8")
    assert "scene.seaweed-loop.03" in registry_content
