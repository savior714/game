"""Static contract tests for the authored sea-turtle Pixi scene adapter."""

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "domains" / "ocean-rescue" / "src"
SCENE = SRC / "sea-turtle-scene.js"
APP = SRC / "app.js"
RUNTIME = SRC / "render-runtime.js"
MANIFEST = SRC / "build-manifest.json"

ALIASES = [
    "scene.water.far",
    "scene.reef.mid",
    "scene.coral.foreground",
    "scene.submarine",
    "scene.seaweed-loop.01",
    "scene.sand-path",
    "scene.passage",
    "otter.tail",
    "otter.arm.far",
    "otter.torso",
    "otter.head",
    "otter.eyes.open",
    "otter.eyes.closed",
    "otter.mouth.neutral",
    "otter.mouth.concern",
    "otter.mouth.smile",
    "otter.arm.near",
    "turtle.worried",
    "turtle.free",
    "ui.drag-arrow",
    "fx.success-burst",
    "fx.cut-ring",
    "fx.cut-icon",
    "fx.bubbles",
    "fx.caustic",
    "hud.progress-cap",
    "hud.loop-icon",
]


def text(path):
    return path.read_text(encoding="utf-8")


def test_scene_module_exists_and_exports_namespace():
    source = text(SCENE)
    assert "window.OceanRescue" in source
    assert "root.SeaTurtleScene" in source


def test_manifest_orders_scene_after_runtime_and_sea_turtle_before_app():
    entries = json.loads(text(MANIFEST))["scripts"]
    namespaces = [entry["namespace"] for entry in entries]
    assert namespaces.index("OceanRescue.RenderRuntime") < namespaces.index(
        "OceanRescue.SeaTurtleScene"
    )
    assert namespaces.index("OceanRescue.SeaTurtle") < namespaces.index(
        "OceanRescue.SeaTurtleScene"
    )
    assert namespaces.index("OceanRescue.SeaTurtleScene") < namespaces.index(
        "OceanRescue.App"
    )
    app = next(entry for entry in entries if entry["namespace"] == "OceanRescue.App")
    assert "OceanRescue.SeaTurtleScene" in app["depends_on"]


def test_scene_declares_exact_required_alias_set():
    source = text(SCENE)
    for alias in ALIASES:
        assert f'"{alias}"' in source
    assert source.count('"scene.seaweed-loop.01"') == 2


def test_scene_requires_all_aliases_before_mount():
    source = text(SCENE)
    assert "function validateAliases" in source
    assert "missingAliases.length === 0" in source
    assert "Missing authored textures:" in source
    assert "function prepare" in source
    assert "validateAliases()" in source


def test_scene_uses_single_bounded_sprite_creation_helper():
    source = text(SCENE)
    assert source.count("new PIXI.Sprite(texture)") == 1
    assert "function makeSprite(alias, label)" in source
    assert "texture.defaultAnchor" in source
    assert "sprite.anchor.copyFrom" in source


def test_scene_creates_exactly_three_retained_loops_from_one_alias():
    source = text(SCENE)
    assert "nodes.loops.push" in source
    assert "for (var i = 0; i < 3; i += 1)" in source
    assert 'makeSprite("scene.seaweed-loop.01"' in source
    assert 'loop-count", 3' in source


def test_scene_graph_uses_canonical_containers_and_order():
    source = text(SCENE)
    expected = [
        'getContainer("farBackground")',
        'getContainer("midground")',
        'getContainer("submarine")',
        'getContainer("turtleAndObstacle")',
        'getContainer("seaOtterRig")',
        'getContainer("foreground")',
        'getContainer("effects")',
    ]
    positions = [source.index(item) for item in expected]
    assert positions == sorted(positions)
    assert "if (nodes)" in source
    assert "createSceneGraph();" in source


def test_scene_does_not_replace_or_clear_canonical_containers():
    source = text(SCENE)
    assert ".removeChildren(" not in source
    assert "containers =" not in source
    assert "stage.addChild" not in source


def test_visible_primary_art_uses_sprites_not_procedural_subjects():
    source = text(SCENE)
    assert "PIXI.Graphics" not in source
    assert "new PIXI.Text" not in source
    assert "fillRect" not in source
    assert "beginPath" not in source
    assert "CanvasRenderingContext2D" not in source


def test_scene_has_no_runtime_asset_loading_or_network_path():
    source = text(SCENE)
    for token in (
        "Assets.load",
        "fetch",
        "XMLHttpRequest",
        "Blob",
        "URL.createObjectURL",
    ):
        assert token not in source


def test_scene_layout_is_fixed_to_logical_viewport_and_regions():
    source = text(SCENE)
    assert "var WIDTH = 1280" in source
    assert "var HEIGHT = 720" in source
    assert "setPosition(nodes.submarine, 220, 390)" in source
    assert "setPosition(nodes.turtleWorried, 950, 430)" in source
    assert "setPosition(rig, 590, 420)" in source
    assert "loopBasePosition" in source


def test_loop_geometry_reads_sea_turtle_ropes_only():
    source = text(SCENE)
    assert "SeaTurtle.Ropes[i]" in source
    assert "rope.start.x" in source and "rope.end.x" in source
    assert "760, 300" not in source
    assert "750, 420" not in source
    assert "770, 540" not in source


def test_foreground_is_positioned_below_interaction_endpoints():
    source = text(SCENE)
    assert "setPosition(nodes.foreground, WIDTH / 2, 790)" in source
    assert "scene.coral.foreground" in source


def test_turtle_has_four_distinct_relief_mappings():
    source = text(SCENE)
    for stage in ("worried", "relief-1", "relief-2", "free"):
        assert f'"{stage}"' in source
    assert "nodes.turtleWorried.alpha = 1" in source
    assert "nodes.turtleWorried.alpha = 0.72" in source
    assert "nodes.turtleWorried.alpha = 0.38" in source
    assert "nodes.turtleFree.alpha = 1" in source


def test_otter_rig_part_order_and_approved_face_states_are_explicit():
    source = text(SCENE)
    order = [
        "nodes.otterTail",
        "nodes.otterArmFar",
        "nodes.otterTorso",
        "nodes.otterHead",
        "nodes.otterEyesOpen",
        "nodes.otterEyesClosed",
        "nodes.otterMouthNeutral",
        "nodes.otterMouthConcern",
        "nodes.otterMouthSmile",
        "nodes.otterArmNear",
    ]
    positions = [source.index(f"addChild(seaOtterRig, {name})") for name in order]
    assert positions == sorted(positions)
    for alias in (
        "otter.eyes.open",
        "otter.eyes.closed",
        "otter.mouth.neutral",
        "otter.mouth.concern",
        "otter.mouth.smile",
    ):
        assert f'"{alias}"' in source


def test_active_loop_contrast_and_single_drag_arrow_are_state_driven():
    source = text(SCENE)
    assert "loop.alpha = isActive ? 1 : 0.58" in source
    assert "loop.tint = isActive ? 0xffffb0 : 0x6f9d91" in source
    assert "nodes.dragArrow.visible = !!activeRopeId" in source
    assert "nodes.dragArrow.position.set" in source
    assert "nodes.dragArrow.rotation" in source


def test_failure_and_success_feedback_are_bounded_and_current_rope_scoped():
    source = text(SCENE)
    assert 'feedback === "failure"' in source
    assert 'feedback === "success"' in source
    assert "Math.sin(activeTime / 26) * 7" in source
    assert "FEEDBACK_MOTION_MS = 400" in source
    assert "nodes.successBurst.visible = !!burstRopeId" in source
    assert 'completed || (isActive && feedback === "success")' in source


def test_pointer_intent_is_visual_only_and_domain_is_not_called():
    source = text(SCENE)
    assert "pointerIntent.active" in source
    assert "pointerIntent.x" in source
    assert "SeaTurtle.pointerDown" not in source
    assert "SeaTurtle.pointerMove" not in source
    assert "SeaTurtle.pointerUp" not in source
    assert "SeaTurtle.pointerCancel" not in source


def test_scene_has_one_bounded_raf_loop_and_no_ticker():
    source = text(SCENE)
    assert source.count("requestAnimationFrame") >= 2
    assert "PIXI.Ticker" not in source
    assert "application.start" not in source
    assert "MAX_DELTA_MS = 50" in source
    assert "Math.min(MAX_DELTA_MS" in source
    assert "if (active)" in source


def test_pause_resume_and_exit_stop_visual_loop_without_wall_clock_jump():
    source = text(SCENE)
    assert "function pause()" in source
    assert "function resume()" in source
    assert "function exit()" in source
    assert "cancelFrame();" in source
    assert "lastTimestamp = null" in source
    assert "mounted = false" in source


def test_reduced_motion_keeps_state_changes_and_disables_continuous_motion():
    source = text(SCENE)
    assert "prefers-reduced-motion: reduce" in source
    assert "reducedMotion" in source
    assert "var hover = reducedMotion ? 0" in source
    assert "if (isActive && !reducedMotion" in source


def test_runtime_exposes_scene_render_and_legacy_visibility_contract():
    source = text(RUNTIME)
    for name in (
        "renderSceneFrame",
        "setLegacyBridgeVisible",
        "getLegacyBridgeVisible",
    ):
        assert name in source
    assert "if (paused)" in source
    assert "dirty = true" in source
    assert "application.render()" in source


def test_app_mounts_before_interaction_and_syncs_after_domain_calls():
    source = text(APP)
    assert "var SeaTurtleScene = window.OceanRescue.SeaTurtleScene || null;" in source
    assert "SeaTurtleScene.prepare(sequence)" in source
    assert "SeaTurtleScene.activate()" in source
    assert "SeaTurtleScene.sync(SeaTurtle.getSnapshot(), intent)" in source
    assert "RenderRuntime.setLegacyBridgeVisible(false)" in text(SCENE)
    assert "RenderRuntime.setLegacyBridgeVisible(true)" in source


def test_app_does_not_use_authored_scene_for_other_missions():
    source = text(APP)
    assert "SeaTurtleScene.exit()" in source
    assert "mission.id === SeaTurtle.MissionId" in source
    assert "activeRescueSequence.missionId === SeaTurtle.MissionId" in source


def test_diagnostics_are_plain_and_include_required_evidence():
    source = text(SCENE)
    for key in (
        "mounted",
        "active",
        "paused",
        "nodeCount",
        "spriteCount",
        "loopCount",
        "activeRopeId",
        "completedCount",
        "reliefStage",
        "animationRunning",
        "legacyBridgeVisible",
        "requiredAliasCount",
        "missingAliases",
    ):
        assert re.search(rf"\b{key}\s*:", source)
    assert "Object.freeze({" in source
