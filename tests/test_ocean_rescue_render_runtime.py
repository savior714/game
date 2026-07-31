"""Contract tests for the Ocean Rescue Pixi scene skeleton runtime."""

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "domains" / "ocean-rescue" / "src"
MANIFEST = SRC / "build-manifest.json"
RUNTIME = SRC / "render-runtime.js"
APP = SRC / "app.js"
ARTIFACT = REPO_ROOT / "ocean-rescue" / "index.html"


def _manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _runtime():
    return RUNTIME.read_text(encoding="utf-8")


def test_manifest_places_runtime_between_assets_and_state_and_app_depends_on_it():
    entries = _manifest()["scripts"]
    namespaces = [entry["namespace"] for entry in entries]
    assert namespaces.index("PIXI") < namespaces.index("OceanRescue.RenderAssets")
    assert namespaces.index("OceanRescue.RenderAssets") < namespaces.index(
        "OceanRescue.RenderRuntime"
    )
    assert namespaces.index("OceanRescue.RenderRuntime") < namespaces.index(
        "OceanRescue.State"
    )
    app = next(entry for entry in entries if entry["namespace"] == "OceanRescue.App")
    assert "OceanRescue.RenderRuntime" in app["depends_on"]


def test_application_contract_is_explicit_and_reuses_visible_canvas():
    source = _runtime()
    assert "new PIXI.Application()" in source
    assert "application.init({" in source
    assert "canvas: visibleCanvas" in source
    assert "width: WIDTH" in source and "height: HEIGHT" in source
    assert 'preference: ["webgl", "canvas"]' in source
    assert "autoDensity: false" in source
    assert "autoStart: false" in source
    assert "sharedTicker: false" in source
    assert "application.start" not in source
    assert "resizeTo" not in source


def test_runtime_has_single_bridge_and_canonical_container_order():
    source = _runtime()
    for name in (
        "farBackground",
        "midground",
        "gameplayWorld",
        "legacyPaintBridge",
        "submarine",
        "turtleAndObstacle",
        "seaOtterRig",
        "foreground",
        "effects",
        "hud",
    ):
        assert f'"{name}"' in source
    assert 'document.createElement("canvas")' in source
    assert "new window.PIXI.CanvasSource" in source
    assert "new window.PIXI.Sprite" in source
    assert "application.render()" in source
    assert "legacySource.update()" in source


def test_runtime_parses_embedded_pages_without_network_or_ticker():
    source = _runtime()
    assert "RenderAssets" in source
    assert "new window.PIXI.Spritesheet" in source
    assert ".parse()" in source
    assert "fetch" not in source
    assert "XMLHttpRequest" not in source
    assert "Assets.load" not in source
    assert "requestAnimationFrame" not in source


def test_runtime_exposes_input_and_lifecycle_contracts():
    source = _runtime()
    for name in (
        "getTexture",
        "hasTexture",
        "getTextureAliases",
        "getContainer",
        "getContainerNames",
        "getLegacyCanvas",
        "getLegacyContext",
        "presentLegacyFrame",
        "mapClientToLogical",
        "pause",
        "resume",
        "destroy",
    ):
        assert re.search(rf"\b{name}\b", source)
    assert "mapPositionToPoint" in source
    assert "inside:" in source
    assert "This device could not start the Ocean Rescue renderer." in source


def test_app_separates_visible_input_from_paint_surface_and_gates_production_boot():
    source = APP.read_text(encoding="utf-8")
    assert "function resolveVisibleInputCanvas" in source
    assert "function resolvePaintCanvas" in source
    assert "function resolvePaintContext" in source
    assert "function presentPaintFrame" in source
    assert "RenderRuntime.mapClientToLogical" in source
    assert "RenderRuntime.boot()" in source
    assert "RenderRuntime.showCompatibilityFailure()" in source
    assert "travelPaintCanvas" in source
