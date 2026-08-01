"""Focused contract test for Ocean Rescue authored travel Pixi scene.

Verifies that the TRAVEL phase renders through an authored Pixi scene
(OceanRescue.TravelScene) rather than the legacy Canvas 2D primitive path.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOMAIN_SRC = REPO_ROOT / "domains" / "ocean-rescue" / "src"
GENERATED_JS = DOMAIN_SRC / "render-assets.generated.js"
BUILD_MANIFEST = DOMAIN_SRC / "build-manifest.json"
APP_JS = DOMAIN_SRC / "app.js"
TRAVEL_SCENE_JS = DOMAIN_SRC / "travel-scene.js"
ARTIFACT = REPO_ROOT / "ocean-rescue" / "index.html"
BUILDER = REPO_ROOT / "scripts" / "ocean_rescue" / "build_single_html.py"


def _load_manifest():
    return json.loads(BUILD_MANIFEST.read_text(encoding="utf-8"))


def _load_app_js():
    return APP_JS.read_text(encoding="utf-8")


def _load_travel_scene_js():
    return TRAVEL_SCENE_JS.read_text(encoding="utf-8")


def _load_artifact():
    if not ARTIFACT.exists():
        return ""
    return ARTIFACT.read_text(encoding="utf-8")


def _legacy_primitive_functions():
    return [
        "renderTravelFrame",
        "drawTravelBackground",
        "drawTravelWater",
        "drawTravelTerrain",
        "drawTerrainObstacle",
        "drawTravelGup",
        "drawCollisionFeedback",
    ]


def test_travel_scene_module_exists_and_is_loaded():
    """travel-scene.js must exist and be declared in the build manifest."""
    assert TRAVEL_SCENE_JS.exists(), (
        f"Missing travel-scene.js at {TRAVEL_SCENE_JS}"
    )
    manifest = _load_manifest()
    files = {entry["file"] for entry in manifest.get("scripts", [])}
    assert "travel-scene.js" in files, (
        "build-manifest.json does not declare travel-scene.js"
    )


def test_travel_scene_namespace_is_registered():
    """OceanRescue.TravelScene must be the declared namespace."""
    manifest = _load_manifest()
    for entry in manifest.get("scripts", []):
        if entry["file"] == "travel-scene.js":
            assert entry.get("namespace") == "OceanRescue.TravelScene", (
                "travel-scene.js must register OceanRescue.TravelScene"
            )
            return
    raise AssertionError("travel-scene.js entry missing from manifest")


def test_travel_scene_requires_required_aliases():
    """TravelScene must declare required texture aliases that exist in the asset package."""
    source = _load_travel_scene_js()
    match = re.search(
        r"var\s+REQUIRED_ALIASES\s*=\s*\[([^\]]+)\]", source
    )
    assert match is not None, "REQUIRED_ALIASES not found in travel-scene.js"
    aliases_raw = match.group(1)
    aliases = re.findall(r'"([^"]+)"', aliases_raw)
    assert len(aliases) >= 5, (
        f"TravelScene requires at least 5 aliases, found {len(aliases)}"
    )
    generated = GENERATED_JS.read_text(encoding="utf-8")
    manifest_match = re.search(
        r'"atlasManifest"\s*:\s*(\{.*?\})\s*,\s*"atlasManifestSha256"',
        generated,
        re.DOTALL,
    )
    assert manifest_match is not None, (
        "Could not locate atlasManifest in render-assets.generated.js"
    )
    manifest_obj = json.loads(manifest_match.group(1))
    available_aliases = set()
    for bundle in manifest_obj.get("bundles", []):
        for alias in bundle.get("aliases", []):
            available_aliases.add(alias)
    missing = [a for a in aliases if a not in available_aliases]
    assert missing == [], (
        f"TravelScene requires aliases not present in the asset package: {missing}"
    )


def test_app_js_routes_travel_through_travel_scene():
    """app.js must prepare/activate TravelScene during travel start."""
    source = _load_app_js()
    assert "TravelScene" in source, (
        "app.js does not reference TravelScene at all"
    )
    assert "TravelScene.prepare" in source, (
        "app.js does not call TravelScene.prepare()"
    )
    assert "TravelScene.activate" in source, (
        "app.js does not call TravelScene.activate()"
    )
    assert "TravelScene.sync" in source, (
        "app.js does not call TravelScene.sync() during the travel frame"
    )
    assert "TravelScene.exit" in source, (
        "app.js does not call TravelScene.exit() before rescue transition"
    )


def test_app_js_does_not_enable_legacy_bridge_for_travel():
    """startTravelRuntime must not call setLegacyBridgeVisible(true)."""
    source = _load_app_js()
    start_match = re.search(
        r"function startTravelRuntime\(\) \{([^}]*(?:\{[^}]*\}[^}]*)*)\}",
        source,
        re.DOTALL,
    )
    assert start_match is not None, "Could not locate startTravelRuntime"
    body = start_match.group(1)
    assert "setLegacyBridgeVisible(true)" not in body, (
        "startTravelRuntime still enables the legacy bridge for travel"
    )


def test_legacy_primitive_travel_paint_removed():
    """Legacy Canvas 2D travel paint functions must not be defined in app.js."""
    source = _load_app_js()
    for fn in _legacy_primitive_functions():
        pattern = re.compile(r"function\s+" + re.escape(fn) + r"\s*\(")
        assert not pattern.search(source), (
            f"Legacy primitive function '{fn}' is still defined in app.js"
        )


def test_single_html_includes_travel_scene():
    """The built single HTML must embed travel-scene.js source."""
    artifact = _load_artifact()
    assert "travel-scene" in artifact, (
        "ocean-rescue/index.html does not include travel-scene.js"
    )


def test_single_html_includes_app_js_dependency_on_travel_scene():
    """The built single HTML must load travel-scene.js before app.js."""
    artifact = _load_artifact()
    travel_scene_pos = artifact.find("travel-scene")
    app_pos = artifact.find("OceanRescue.App")
    assert travel_scene_pos != -1 and app_pos != -1, (
        "Missing travel-scene or OceanRescue.App reference in single HTML"
    )
    assert travel_scene_pos < app_pos, (
        "travel-scene.js must load before app.js in the single HTML"
    )


def test_travel_scene_lifecycle_is_complete():
    """TravelScene must expose the full lifecycle API."""
    source = _load_travel_scene_js()
    for method in [
        "prepare",
        "activate",
        "sync",
        "pause",
        "resume",
        "exit",
        "destroy",
        "isMounted",
        "getDiagnostics",
    ]:
        assert method in source, (
            f"TravelScene missing lifecycle method: {method}"
        )


def test_travel_scene_uses_atlas_textures_not_primitives():
    """TravelScene must create sprites via RenderRuntime.getTexture, not Canvas primitives."""
    source = _load_travel_scene_js()
    assert "RenderRuntime.getTexture" in source, (
        "TravelScene does not read textures from RenderRuntime"
    )
    assert "new PIXI.Sprite" in source, (
        "TravelScene does not create Pixi Sprites"
    )
    for forbidden in ["fillRect", "fillText", 'getContext("2d")']:
        assert forbidden not in source, (
            f"TravelScene uses forbidden primitive: {forbidden}"
        )


def test_travel_scene_hides_legacy_bridge_on_activate():
    """TravelScene must hide the legacy bridge when activating."""
    source = _load_travel_scene_js()
    assert "setLegacyBridgeVisible(false)" in source, (
        "TravelScene does not hide the legacy bridge on prepare"
    )


def test_travel_scene_shows_owned_nodes_and_hides_on_exit():
    """TravelScene must show owned nodes on activate and hide them on exit."""
    source = _load_travel_scene_js()
    assert "showOwnedNodes" in source, (
        "TravelScene missing showOwnedNodes"
    )
    assert "hideOwnedNodes" in source, (
        "TravelScene missing hideOwnedNodes"
    )


def test_travel_scene_provides_diagnostics():
    """TravelScene must expose deterministic runtime diagnostics."""
    source = _load_travel_scene_js()
    assert "data-travel-scene=" in source or "data-travel-scene" in source, (
        "TravelScene does not set data-travel-scene diagnostic attribute"
    )
    assert "data-travel-scene-legacy-visible" in source, (
        "TravelScene does not set data-travel-scene-legacy-visible"
    )
    assert "data-travel-scene-node-count" in source, (
        "TravelScene does not set data-travel-scene-node-count"
    )
    assert "data-travel-scene-obstacle-count" in source, (
        "TravelScene does not set data-travel-scene-obstacle-count"
    )
    assert "data-travel-scene-animation" in source, (
        "TravelScene does not set data-travel-scene-animation"
    )


def test_build_manifest_depends_on_order():
    """app.js must depend on TravelScene in the build manifest."""
    manifest = _load_manifest()
    app_entry = None
    for entry in manifest.get("scripts", []):
        if entry["file"] == "app.js":
            app_entry = entry
            break
    assert app_entry is not None, "app.js missing from build manifest"
    deps = app_entry.get("depends_on", [])
    assert "OceanRescue.TravelScene" in deps, (
        "app.js does not declare OceanRescue.TravelScene as a dependency"
    )


def test_no_network_or_remote_loads_in_travel_scene():
    """TravelScene must not fetch, import, or WebSocket at runtime."""
    source = _load_travel_scene_js()
    forbidden = [r"\bimport\s*\(", r"\bfetch\s*\(", r"\bWebSocket\b"]
    for pattern in forbidden:
        assert not re.search(pattern, source), (
            f"TravelScene uses forbidden runtime pattern: {pattern.pattern}"
        )


def test_rescue_arrival_exits_travel_scene():
    """beginRescueArrival must call TravelScene.exit() before the rescue transition."""
    source = _load_app_js()
    begin_pos = source.find("function beginRescueArrival")
    exit_pos = source.find("TravelScene.exit")
    assert begin_pos != -1, "Could not locate beginRescueArrival in app.js"
    assert exit_pos != -1, "Could not locate TravelScene.exit in app.js"
    assert exit_pos > begin_pos, (
        "TravelScene.exit() must appear after beginRescueArrival definition"
    )
    body_start = source.index("{", begin_pos)
    depth = 0
    body_end = body_start
    for i in range(body_start, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                body_end = i
                break
    body = source[body_start:body_end]
    assert "TravelScene.exit" in body, (
        "beginRescueArrival does not call TravelScene.exit()"
    )
