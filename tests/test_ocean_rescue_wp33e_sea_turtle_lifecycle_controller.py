"""WP-33E-0 sea-turtle characterization and ABI-lock contract.

This package must not move runtime ownership. It locks the concrete sea-turtle
ABI, records the existing app.js orchestration landmarks, and ensures the next
ownership package starts from an explicit characterization baseline.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "domains" / "ocean-rescue" / "src"
RUNTIME_ABI = SRC / "contracts" / "runtime-abi.ts"
CONTROLLER = SRC / "controllers" / "sea-turtle-lifecycle.ts"
APP = SRC / "app.js"
SEA_TURTLE = SRC / "sea-turtle.js"
SEA_TURTLE_SCENE = SRC / "sea-turtle-scene.js"
JUSTFILE = REPO_ROOT / "Justfile"

FORBIDDEN_CONTROLLER_TOKENS = (
    "addEventListener",
    "setTimeout",
    "completeMission",
    "startMissionSuccessPresentation",
    "Crab",
    "YoungWhale",
    "as unknown as",
    ": any",
    "as any",
)


def _read(path: Path) -> str:
    assert path.is_file(), f"missing required file: {path.relative_to(REPO_ROOT)}"
    return path.read_text(encoding="utf-8")


def test_runtime_abi_locks_exact_sea_turtle_values() -> None:
    text = _read(RUNTIME_ABI)
    required = (
        'export type SeaTurtleRopeId = "rope-1" | "rope-2" | "rope-3";',
        "export interface SeaTurtlePoint",
        "export interface SeaTurtleConstants",
        'readonly MissionId: "sea-turtle";',
        "readonly Constants: Readonly<SeaTurtleConstants>;",
        "readonly Ropes: readonly SeaTurtleRope[];",
        "readonly Dialogues: readonly [string, string, string];",
        "readonly activeRopeId: SeaTurtleRopeId | null;",
        "readonly completedRopeIds: readonly SeaTurtleRopeId[];",
        "readonly ropeId: SeaTurtleRopeId | null;",
        "readonly nextRopeId: SeaTurtleRopeId | null;",
    )
    for token in required:
        assert token in text, f"missing concrete sea-turtle ABI token: {token}"


def test_runtime_abi_matches_current_state_machine_exports() -> None:
    abi = _read(RUNTIME_ABI)
    runtime = _read(SEA_TURTLE)
    for name in (
        "baseEndpointRadius",
        "assistedEndpointRadius",
        "basePathTolerance",
        "assistedPathTolerance",
        "tapMovementThreshold",
        "minimumTraceProgress",
        "maxBackwardProgress",
        "successFeedbackMs",
        "failureFeedbackMs",
    ):
        assert name in runtime
        assert f"readonly {name}: number;" in abi
    for exported in (
        "MissionId",
        "Constants",
        "Ropes",
        "Dialogues",
        "getSnapshot",
        "start",
        "stop",
        "pointerDown",
        "pointerMove",
        "pointerUp",
        "pointerCancel",
        "finishFeedback",
        "pauseCancel",
    ):
        assert f"{exported}:" in runtime


def test_authored_scene_sync_contract_includes_pointer_intent() -> None:
    abi = _read(RUNTIME_ABI)
    scene = _read(SEA_TURTLE_SCENE)
    assert "function sync(current, intent)" in scene
    assert "snapshot: SeaTurtleSnapshot," in abi
    assert "intent?: PointerIntent," in abi


def test_controller_exposes_concrete_snapshot_and_session_reference() -> None:
    text = _read(CONTROLLER)
    required = (
        "export interface SeaTurtleSessionRef",
        "readonly rescueSequenceId: number;",
        'readonly missionId: "sea-turtle";',
        "getSeaTurtleSnapshot(): SeaTurtleSnapshot | null;",
        "function getSeaTurtleSnapshot(): SeaTurtleSnapshot | null",
        "Object.assign(host, {",
    )
    for token in required:
        assert token in text
    assert "getSeaTurtleSnapshot(): unknown | null" not in text


def test_controller_remains_characterization_only() -> None:
    text = _read(CONTROLLER)
    for token in FORBIDDEN_CONTROLLER_TOKENS:
        assert token not in text, f"WP-33E-0 moved forbidden runtime ownership: {token}"
    for future_method in (
        "handleSeaTurtlePointerDown",
        "handleSeaTurtlePointerMove",
        "handleSeaTurtlePointerUp",
        "handleSeaTurtlePointerCancel",
        "beginSeaTurtleSuccessFeedback",
        "beginSeaTurtleFailureFeedback",
        "completeSeaTurtleFeedback",
        "onSeaTurtleInteractionComplete",
    ):
        assert future_method not in text


def test_start_eligibility_and_initial_projection_remain_characterized() -> None:
    controller = _read(CONTROLLER)
    app = _read(APP)
    assert "State.getSnapshot().phase !== State.Phases.RESCUE_ACTIVE" in controller
    assert "SeaTurtle.start()" in controller
    assert "SeaTurtleScene?.isMounted()" in controller
    assert "SeaTurtleScene.activate()" in controller
    assert "syncSeaTurtleProjection();" in controller
    assert "function startSeaTurtleInteraction(sequence)" in app
    assert 'progress.textContent = "Rope 1 of 3";' in app


def test_shared_rescue_listener_and_mission_router_remain_in_app_js() -> None:
    app = _read(APP)
    assert "function bindRescuePointerInput(canvas)" in app
    for event_name in ("pointerdown", "pointermove", "pointerup", "pointercancel"):
        assert f'canvas.addEventListener("{event_name}"' in app
    for mission_branch in (
        "missionId === SeaTurtle.MissionId",
        "missionId === Crab.MissionId",
        "missionId === YoungWhale.MissionId",
    ):
        assert mission_branch in app


def test_pointer_capture_and_cancel_baseline_remain_in_app_js() -> None:
    app = _read(APP)
    required = (
        "function handleSeaTurtlePointerDown(event, mapped)",
        "function releaseSeaTurtlePointerCapture(pointerId)",
        "seaTurtlePointerCaptureEl.setPointerCapture(event.pointerId)",
        "seaTurtlePointerCaptureEl.releasePointerCapture(pointerId)",
        "function onRescuePointerMove(event)",
        "function onRescuePointerUp(event)",
        "function onRescuePointerCancel(event)",
        "SeaTurtle.pointerCancel(event.pointerId)",
    )
    for token in required:
        assert token in app


def test_feedback_timing_and_stale_sequence_guards_remain_in_app_js() -> None:
    app = _read(APP)
    required = (
        "function beginSeaTurtleSuccessFeedback(ropeId)",
        "function beginSeaTurtleFailureFeedback(ropeId)",
        "function completeSeaTurtleFeedback(sequence)",
        'scheduleWithRegistry("sea-turtle-feedback"',
        "sequence.sequenceId !== activeRescueSequence.sequenceId",
        "snapshot.feedback !== sequence.kind",
        "snapshot.activeRopeId !== sequence.ropeId",
        "SeaTurtle.finishFeedback()",
    )
    for token in required:
        assert token in app


def test_pause_menu_and_completion_handoff_remain_host_owned() -> None:
    app = _read(APP)
    required = (
        "function cancelPausePointerInteractions()",
        "SeaTurtle.pauseCancel()",
        "function shutdownRescueInteractionState()",
        "function completeSeaTurtleSuccess()",
        "State.beginTransition(State.Phases.RESCUE_SUCCESS)",
        "startMissionSuccessPresentation(sequence)",
    )
    for token in required:
        assert token in app


def test_characterization_recipe_exists_and_includes_direct_regressions() -> None:
    justfile = _read(JUSTFILE)
    recipe = justfile.split(
        "check-ocean-rescue-sea-turtle-lifecycle-controller:", 1
    )[1].split("\n# ", 1)[0]
    required = (
        "tests/test_ocean_rescue_wp33e_sea_turtle_lifecycle_controller.py",
        "tests/test_ocean_rescue_sea_turtle_interaction.py",
        "tests/test_ocean_rescue_authored_sea_turtle_scene.py",
        "tests/test_ocean_rescue_rope_geometry_runtime.py",
        "tests/test_ocean_rescue_wp33d_pause_timer_resume_controller.py",
        "tests/test_ocean_rescue_wp33c_rescue_site_tutorial_controller.py",
        "tests/test_ocean_rescue_wp32b_pointer_renderer_boundary.py",
        "tests/test_ocean_rescue_wp30_esm_entry_module_graph.py",
    )
    for path in required:
        assert path in recipe


def test_controller_exposes_sync_sea_turtle_projection() -> None:
    text = _read(CONTROLLER)
    assert "syncSeaTurtleProjection(intent?: PointerIntent): boolean" in text
    assert "function syncSeaTurtleProjection(intent?: PointerIntent): boolean" in text


def test_controller_owns_authored_scene_sync_directly() -> None:
    text = _read(CONTROLLER)
    assert "SeaTurtleScene.sync(snapshot, resolvedIntent)" in text
    assert "SeaTurtleScene?.isMounted()" in text


def test_controller_projects_six_root_markers_directly() -> None:
    text = _read(CONTROLLER)
    required_markers = (
        '"data-sea-turtle-active"',
        '"data-sea-turtle-rope-id"',
        '"data-sea-turtle-completed-count"',
        '"data-sea-turtle-help-level"',
        '"data-sea-turtle-feedback"',
        '"data-sea-turtle-complete"',
    )
    for marker in required_markers:
        assert marker in text, f"missing root marker attribute: {marker}"


def test_projection_reads_snapshot_exactly_once() -> None:
    text = _read(CONTROLLER)
    snapshot_calls = (
        text.count("SeaTurtle.getSnapshot()")
        + text.count("SeaTurtle?.getSnapshot()")
    )
    assert snapshot_calls == 3, (
        f"expected exactly 3 SeaTurtle.getSnapshot() calls "
        f"(1 in isSeaTurtleActive + 1 in getSeaTurtleSnapshot + "
        f"1 in syncSeaTurtleProjection), "
        f"got {snapshot_calls}"
    )
    projection_body = text.split("function syncSeaTurtleProjection")[1].split(
        "function "
    )[0]
    assert (
        "const snapshot = SeaTurtle.getSnapshot();" in projection_body
    ), "syncSeaTurtleProjection must read snapshot exactly once into a local"


def test_projection_passes_same_snapshot_to_scene_or_fallback() -> None:
    text = _read(CONTROLLER)
    projection_body = text.split("function syncSeaTurtleProjection")[1].split(
        "function "
    )[0]
    assert "SeaTurtleScene.sync(snapshot, resolvedIntent)" in projection_body
    assert "host.renderLegacySeaTurtleFrame(snapshot, intent)" in projection_body


def test_legacy_host_bridge_receives_concrete_snapshot() -> None:
    text = _read(CONTROLLER)
    assert "snapshot: SeaTurtleSnapshot," in text
    assert "host.renderLegacySeaTurtleFrame(" in text


def test_production_esm_app_js_delegates_to_controller_projection() -> None:
    text = _read(APP)
    delegation_checks = (
        'typeof App.syncSeaTurtleProjection === "function"',
        "App.syncSeaTurtleProjection(PointerInput.activeIntent(mapped))",
        "App.syncSeaTurtleProjection(PointerInput.inactiveIntent())",
        "App.syncSeaTurtleProjection()",
    )
    for check in delegation_checks:
        assert check in text, f"missing controller delegation in app.js: {check}"


def test_ordered_script_fallback_remains_in_app_js() -> None:
    text = _read(APP)
    assert "renderSeaTurtleFrame();" in text
    assert "updateSeaTurtleRootMarkers();" in text
    assert "function renderLegacySeaTurtleFrame(snapshot, _intent)" in text


def test_pointer_down_move_up_cancel_ownership_remains_in_app_js() -> None:
    text = _read(APP)
    required = (
        "function handleSeaTurtlePointerDown(event, mapped)",
        "function onRescuePointerMove(event)",
        "function onRescuePointerUp(event)",
        "function onRescuePointerCancel(event)",
        "SeaTurtle.pointerDown(event.pointerId, mapped.x, mapped.y)",
        "SeaTurtle.pointerMove(event.pointerId, mapped.x, mapped.y)",
        "SeaTurtle.pointerUp(event.pointerId, mapped.x, mapped.y)",
        "SeaTurtle.pointerCancel(event.pointerId)",
    )
    for token in required:
        assert token in text


def test_pointer_capture_release_ownership_remains_in_app_js() -> None:
    text = _read(APP)
    required = (
        "seaTurtlePointerCaptureEl.setPointerCapture(event.pointerId)",
        "seaTurtlePointerCaptureEl.releasePointerCapture(pointerId)",
    )
    for token in required:
        assert token in text


def test_feedback_scheduling_and_stale_sequence_guard_remain_in_app_js() -> None:
    text = _read(APP)
    required = (
        "function beginSeaTurtleSuccessFeedback(ropeId)",
        "function beginSeaTurtleFailureFeedback(ropeId)",
        "function completeSeaTurtleFeedback(sequence)",
        'scheduleWithRegistry("sea-turtle-feedback"',
        "sequence.sequenceId !== activeRescueSequence.sequenceId",
        "snapshot.feedback !== sequence.kind",
        "snapshot.activeRopeId !== sequence.ropeId",
        "SeaTurtle.finishFeedback()",
    )
    for token in required:
        assert token in text


def test_pause_menu_cleanup_and_mission_success_handoff_remain_host_owned() -> None:
    text = _read(APP)
    required = (
        "function cancelPausePointerInteractions()",
        "SeaTurtle.pauseCancel()",
        "function shutdownRescueInteractionState()",
        "function completeSeaTurtleSuccess()",
        "State.beginTransition(State.Phases.RESCUE_SUCCESS)",
        "startMissionSuccessPresentation(sequence)",
    )
    for token in required:
        assert token in text


def test_controller_has_no_dom_or_timer_ownership() -> None:
    text = _read(CONTROLLER)
    forbidden = (
        "addEventListener",
        "setTimeout",
        "completeMission",
        "startMissionSuccessPresentation",
        "Crab",
        "YoungWhale",
    )
    for token in forbidden:
        assert token not in text, f"controller must not own: {token}"
