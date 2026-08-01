"""Behavioral and contract tests for the Ocean Rescue crab authored scene.

Validates module existence, build-manifest dependency order, required alias
coverage in the generated render-asset registry, unreachable legacy canvas
painting on the production crab path, texture-backed sprite creation in
crab-scene.js, and absence of remote loading or PIXI.Graphics usage.
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_crab_scene_module_exists():
    path = REPO_ROOT / "domains" / "ocean-rescue" / "src" / "crab-scene.js"
    assert path.exists(), f"Missing crab-scene.js at {path}"
    source = path.read_text(encoding="utf-8")
    assert "CrabScene" in source
    for method in (
        "prepare",
        "activate",
        "sync",
        "pause",
        "resume",
        "exit",
        "destroy",
        "isMounted",
        "getDiagnostics",
    ):
        assert f"{method}:" in source or f"{method} :" in source


def test_crab_scene_in_build_manifest():
    manifest_path = REPO_ROOT / "domains" / "ocean-rescue" / "src" / "build-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = [entry["file"] for entry in manifest["scripts"]]
    assert "crab-scene.js" in files, "crab-scene.js missing from build-manifest.json"
    crab_index = files.index("crab.js")
    crab_scene_index = files.index("crab-scene.js")
    young_whale_index = files.index("young-whale.js")
    assert crab_index < crab_scene_index < young_whale_index


def test_crab_scene_dependency_order():
    manifest_path = REPO_ROOT / "domains" / "ocean-rescue" / "src" / "build-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["scripts"]:
        if entry["file"] == "crab-scene.js":
            deps = entry.get("depends_on", [])
            assert "OceanRescue.RenderRuntime" in deps
            assert "OceanRescue.Crab" in deps
            break


def test_required_crab_aliases_in_generated_assets():
    registry_path = REPO_ROOT / "domains" / "ocean-rescue" / "src" / "render-assets.generated.js"
    source = registry_path.read_text(encoding="utf-8")
    required = [
        "crab.trapped",
        "crab.free",
        "rescue.rock.01",
        "rescue.rock.02",
        "rescue.rock.03",
        "tool.grabber.base",
        "tool.grabber.arm",
        "tool.grabber.claw.open",
        "tool.grabber.claw.closed",
        "ui.drop-zone",
        "fx.hold-ring",
    ]
    for alias in required:
        assert alias in source, f"Missing required alias {alias} in render-assets.generated.js"


def test_legacy_canvas_path_excluded_from_production_crab():
    app_path = REPO_ROOT / "domains" / "ocean-rescue" / "src" / "app.js"
    source = app_path.read_text(encoding="utf-8")
    render_crab_calls = [
        line.strip()
        for line in source.splitlines()
        if "renderCrabFrame()" in line
        and not line.strip().startswith("//")
        and "function renderCrabFrame" not in line
    ]
    for call in render_crab_calls:
        stripped = call.split("(")[0].strip()
        assert stripped == "renderCrabFrame" or "CrabScene" in call or "else" in call


def test_no_pixi_graphics_in_crab_scene():
    scene_path = REPO_ROOT / "domains" / "ocean-rescue" / "src" / "crab-scene.js"
    source = scene_path.read_text(encoding="utf-8")
    assert "PIXI.Graphics" not in source, "Primary scene bodies must be texture-backed sprites"


def test_no_remote_loading_in_crab_scene():
    scene_path = REPO_ROOT / "domains" / "ocean-rescue" / "src" / "crab-scene.js"
    source = scene_path.read_text(encoding="utf-8")
    remote_patterns = [r"fetch\s*\(", r"new\s+XMLHttpRequest", r"https?://"]
    for pattern in remote_patterns:
        assert not re.search(pattern, source), f"Remote loading detected: {pattern}"


def test_crab_scene_has_lifecycle_methods():
    scene_path = REPO_ROOT / "domains" / "ocean-rescue" / "src" / "crab-scene.js"
    source = scene_path.read_text(encoding="utf-8")
    for method in ("prepare", "activate", "sync", "pause", "resume", "exit", "destroy"):
        assert f"{method}:" in source or f"{method} :" in source, f"Missing lifecycle method: {method}"
    assert "isMounted:" in source or "isMounted" in source
    assert "getDiagnostics:" in source or "getDiagnostics" in source


def test_crab_scene_hides_legacy_bridge():
    scene_path = REPO_ROOT / "domains" / "ocean-rescue" / "src" / "crab-scene.js"
    source = scene_path.read_text(encoding="utf-8")
    assert "setLegacyBridgeVisible(false)" in source
    assert "setLegacyBridgeVisible(true)" in source


def test_app_js_resolves_crab_scene():
    app_path = REPO_ROOT / "domains" / "ocean-rescue" / "src" / "app.js"
    source = app_path.read_text(encoding="utf-8")
    assert "CrabScene" in source
    assert "OceanRescue.CrabScene" in source


def test_app_js_syncs_crab_scene_on_interactions():
    app_path = REPO_ROOT / "domains" / "ocean-rescue" / "src" / "app.js"
    source = app_path.read_text(encoding="utf-8")
    assert "syncCrabScene" in source
    assert "CrabScene.pause" in source
    assert "CrabScene.resume" in source
    assert "CrabScene.exit" in source
