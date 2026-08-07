"""Focused tests for seaweed-loop-03 generated pipeline rebuild (B25)."""

from __future__ import annotations

import json
import pathlib
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
ATLAS_JSON = REPO_ROOT / "domains/ocean-rescue/assets/generated/scene/scene-0.json"
MANIFEST_JSON = REPO_ROOT / "domains/ocean-rescue/assets/generated/atlas-manifest.json"
REGISTRY_JS = REPO_ROOT / "domains/ocean-rescue/src/render-assets.generated.js"


def test_seaweed_loop_03_in_scene_atlas_json():
    assert ATLAS_JSON.exists()
    atlas_data = json.loads(ATLAS_JSON.read_text(encoding="utf-8"))
    frames = atlas_data.get("frames", {})
    assert "scene.seaweed-loop.03" in frames
    frame_info = frames["scene.seaweed-loop.03"]
    assert frame_info["anchor"] == {"x": 0.5, "y": 0.1}
    assert frame_info["sourceSize"] == {"w": 240, "h": 400}


def test_seaweed_loop_03_in_atlas_manifest():
    assert MANIFEST_JSON.exists()
    manifest_data = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    bundles = {b["name"]: b for b in manifest_data["bundles"]}
    assert "scene" in bundles
    scene_bundle = bundles["scene"]
    assert "scene.seaweed-loop.03" in scene_bundle["aliases"]


def test_seaweed_loop_03_in_render_assets_registry():
    assert REGISTRY_JS.exists()
    content = REGISTRY_JS.read_text(encoding="utf-8")
    assert "scene.seaweed-loop.03" in content
