"""WP-33E-2 sea-turtle session activation and shutdown ownership.

This package verifies that the typed controller owns sea-turtle session
lifecycle: sequence-bound start, duplicate idempotency, wrong/stale sequence
rejection, shared pointer listener binding request, initial projection,
and explicit stop with scene exit and SeaTurtle.stop().

app.js retains shared rescue mission router, pointer capture, feedback timer,
feedback UI, assist escalation, RESCUE_SUCCESS transition, and mission-success
handoff.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "domains" / "ocean-rescue" / "src"
CONTROLLER = SRC / "controllers" / "sea-turtle-lifecycle.ts"
APP = SRC / "app.js"
RUNTIME_ABI = SRC / "contracts" / "runtime-abi.ts"

FORBIDDEN_CONTROLLER_TOKENS = (
    "addEventListener",
    "setPointerCapture",
    "releasePointerCapture",
    "pointerDown(",
    "pointerMove(",
    "pointerUp(",
    "pointerCancel(",
    "setTimeout",
    "beginSeaTurtleSuccessFeedback",
    "beginSeaTurtleFailureFeedback",
    "completeMission",
    "startMissionSuccessPresentation",
    "Crab",
    "YoungWhale",
    "any",
    "as unknown as",
    "applySeaTurtleSuccessVisual",
    "applySeaTurtleFailureVisual",
    "setSeaTurtleDialogue",
)


def _read(path: Path) -> str:
    assert path.is_file(), f"missing required file: {path.relative_to(REPO_ROOT)}"
    return path.read_text(encoding="utf-8")


def test_host_api_extends_pause_timer_resume_app_api() -> None:
    text = _read(CONTROLLER)
    assert "extends PauseTimerResumeAppApi" in text
    assert "SeaTurtleLifecycleHostApi" in text


def test_host_api_declares_ensure_rescue_pointer_input_bound() -> None:
    text = _read(CONTROLLER)
    assert "ensureRescuePointerInputBound(canvas: HTMLCanvasElement): void" in text


def test_host_api_declares_hide_assist_hand() -> None:
    text = _read(CONTROLLER)
    assert "hideAssistHand(): void" in text


def test_public_api_exposes_start_sea_turtle_session_with_sequence() -> None:
    text = _read(CONTROLLER)
    assert (
        "startSeaTurtleSession(sequence: RescueSiteSequence): boolean" in text
    )


def test_public_api_exposes_stop_sea_turtle_session() -> None:
    text = _read(CONTROLLER)
    assert "stopSeaTurtleSession(): boolean" in text


def test_public_api_exposes_get_active_sea_turtle_session() -> None:
    text = _read(CONTROLLER)
    assert (
        "getActiveSeaTurtleSession(): SeaTurtleSessionRef | null" in text
    )


def test_public_api_exposes_is_sea_turtle_session_active() -> None:
    text = _read(CONTROLLER)
    assert "isSeaTurtleSessionActive(): boolean" in text


def test_session_storage_exists_in_install_closure() -> None:
    text = _read(CONTROLLER)
    assert "let activeSession: SeaTurtleSessionRef | null = null" in text


def test_session_ref_type_has_required_fields() -> None:
    text = _read(CONTROLLER)
    assert "readonly rescueSequenceId: number;" in text
    assert 'readonly missionId: "sea-turtle";' in text


def test_start_validates_sea_turtle_dependency_exists() -> None:
    text = _read(CONTROLLER)
    body = text.split("function startSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "!SeaTurtle" in body


def test_start_validates_sequence_is_object() -> None:
    text = _read(CONTROLLER)
    body = text.split("function startSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert 'typeof sequence !== "object"' in body


def test_start_validates_sequence_mission_id_matches() -> None:
    text = _read(CONTROLLER)
    body = text.split("function startSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "sequence.missionId !== SeaTurtle.MissionId" in body


def test_start_validates_active_sequence_not_null() -> None:
    text = _read(CONTROLLER)
    body = text.split("function startSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "host.getActiveRescueSequence()" in body
    assert "activeSequence === null" in body


def test_start_validates_sequence_id_matches_active() -> None:
    text = _read(CONTROLLER)
    body = text.split("function startSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "activeSequence.sequenceId !== sequence.sequenceId" in body


def test_start_validates_active_sequence_mission_is_sea_turtle() -> None:
    text = _read(CONTROLLER)
    body = text.split("function startSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert 'activeSequence.missionId !== "sea-turtle"' in body


def test_start_validates_rescue_active_phase() -> None:
    text = _read(CONTROLLER)
    body = text.split("function startSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "State.Phases.RESCUE_ACTIVE" in body


def test_start_validates_visible_canvas_exists() -> None:
    text = _read(CONTROLLER)
    body = text.split("function startSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "HTMLCanvasElement" in body


def test_start_validates_overlay_exists() -> None:
    text = _read(CONTROLLER)
    body = text.split("function startSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "ocean-rescue-rescue-overlay" in body


def test_start_validates_no_duplicate_active_session() -> None:
    text = _read(CONTROLLER)
    body = text.split("function startSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "activeSession !== null" in body


def test_start_idempotency_returns_true_for_same_sequence() -> None:
    text = _read(CONTROLLER)
    body = text.split("function startSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "activeSession.rescueSequenceId === sequence.sequenceId" in body
    assert "return true" in body


def test_start_rejects_different_active_session() -> None:
    text = _read(CONTROLLER)
    body = text.split("function startSeaTurtleSession")[1].split(
        "function "
    )[0]
    lines = body.split("\n")
    in_duplicate_block = False
    found_reject_false = False
    for line in lines:
        if "activeSession !== null" in line:
            in_duplicate_block = True
        if in_duplicate_block and "return false" in line:
            found_reject_false = True
    assert found_reject_false, (
        "different active session must return false without auto-replace"
    )


def test_activation_calls_sea_turtle_start() -> None:
    text = _read(CONTROLLER)
    body = text.split("function startSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "SeaTurtle.start()" in body


def test_activation_stores_active_session() -> None:
    text = _read(CONTROLLER)
    body = text.split("function startSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "activeSession = {" in body
    assert "rescueSequenceId: sequence.sequenceId" in body
    assert 'missionId: "sea-turtle"' in body


def test_activation_activates_authored_scene() -> None:
    text = _read(CONTROLLER)
    body = text.split("function startSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "SeaTurtleScene.activate()" in body


def test_activation_requests_pointer_listener_binding() -> None:
    text = _read(CONTROLLER)
    body = text.split("function startSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "host.ensureRescuePointerInputBound(canvas)" in body


def test_activation_sets_initial_progress() -> None:
    text = _read(CONTROLLER)
    body = text.split("function startSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert '"Rope 1 of 3"' in body


def test_activation_hides_assist_hand() -> None:
    text = _read(CONTROLLER)
    body = text.split("function startSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "host.hideAssistHand()" in body


def test_activation_calls_sync_projection() -> None:
    text = _read(CONTROLLER)
    body = text.split("function startSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "syncSeaTurtleProjection()" in body


def test_activation_calls_sync_pause_button() -> None:
    text = _read(CONTROLLER)
    body = text.split("function startSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "host.syncPauseButton()" in body


def test_activation_returns_true_on_success() -> None:
    text = _read(CONTROLLER)
    body = text.split("function startSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "return true;" in body, (
        "startSeaTurtleSession must contain 'return true;'"
    )


def test_stop_exits_authored_scene() -> None:
    text = _read(CONTROLLER)
    body = text.split("function stopSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "SeaTurtleScene.exit()" in body


def test_stop_calls_sea_turtle_stop_when_active() -> None:
    text = _read(CONTROLLER)
    body = text.split("function stopSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "SeaTurtle.stop()" in body


def test_stop_clears_active_session() -> None:
    text = _read(CONTROLLER)
    body = text.split("function stopSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "activeSession = null" in body


def test_stop_returns_true_when_session_existed() -> None:
    text = _read(CONTROLLER)
    body = text.split("function stopSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "hadSession" in body


def test_stop_returns_false_when_already_stopped() -> None:
    text = _read(CONTROLLER)
    body = text.split("function stopSeaTurtleSession")[1].split(
        "function "
    )[0]
    lines = body.split("\n")
    in_return_section = False
    found_false_return = False
    for line in lines:
        if "hadSession" in line:
            in_return_section = True
        if in_return_section and "return false" in line:
            found_false_return = True
    assert found_false_return, (
        "stopSeaTurtleSession must return false when no session existed"
    )


def test_stop_does_not_clear_active_rescue_sequence() -> None:
    text = _read(CONTROLLER)
    body = text.split("function stopSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "setActiveRescueSequence" not in body


def test_stop_does_not_transition_phase() -> None:
    text = _read(CONTROLLER)
    body = text.split("function stopSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "beginTransition" not in body
    assert "forcePhase" not in body


def test_controller_does_not_call_add_event_listener() -> None:
    text = _read(CONTROLLER)
    assert "addEventListener" not in text


def test_controller_does_not_use_set_timeout() -> None:
    text = _read(CONTROLLER)
    assert "setTimeout" not in text


def test_controller_does_not_own_feedback_visuals() -> None:
    """WP-33E-4: controller owns sequence + timer, but not app.js visuals."""
    text = _read(CONTROLLER)
    assert "beginSeaTurtleSuccessFeedback" not in text
    assert "beginSeaTurtleFailureFeedback" not in text
    assert "applySeaTurtleSuccessVisual" not in text
    assert "applySeaTurtleFailureVisual" not in text


def test_controller_does_not_own_completion_handoff() -> None:
    text = _read(CONTROLLER)
    assert "completeMission" not in text
    assert "startMissionSuccessPresentation" not in text


def test_controller_does_not_own_crab_or_young_whale() -> None:
    text = _read(CONTROLLER)
    assert "Crab" not in text
    assert "YoungWhale" not in text


def test_controller_does_not_use_any_type() -> None:
    text = _read(CONTROLLER)
    assert ": any" not in text
    assert "as any" not in text
    assert "as unknown as" not in text


def test_app_js_delegates_start_to_controller() -> None:
    text = _read(APP)
    assert 'typeof App.startSeaTurtleSession === "function"' in text
    assert "App.startSeaTurtleSession(sequence)" in text


def test_app_js_delegates_stop_to_controller() -> None:
    text = _read(APP)
    assert 'typeof App.stopSeaTurtleSession === "function"' in text
    assert "App.stopSeaTurtleSession()" in text


def test_app_js_ordered_script_fallback_preserved() -> None:
    text = _read(APP)
    assert "SeaTurtle.start()" in text
    assert "bindRescuePointerInput(canvas)" in text
    assert "renderSeaTurtleFrame()" in text


def test_app_js_retains_shared_listener_registration() -> None:
    text = _read(APP)
    assert "function bindRescuePointerInput(canvas)" in text
    for event_name in ("pointerdown", "pointermove", "pointerup", "pointercancel"):
        assert f'canvas.addEventListener("{event_name}"' in text


def test_app_js_retains_pointer_capture_and_methods() -> None:
    text = _read(APP)
    required = (
        "seaTurtlePointerCaptureEl.setPointerCapture(event.pointerId)",
        "seaTurtlePointerCaptureEl.releasePointerCapture(pointerId)",
        "function handleSeaTurtlePointerDown(event, mapped)",
        "function onRescuePointerMove(event)",
        "function onRescuePointerUp(event)",
        "function onRescuePointerCancel(event)",
    )
    for token in required:
        assert token in text


def test_app_js_retains_feedback_timer_and_stale_guards() -> None:
    text = _read(APP)
    required = (
        "function beginSeaTurtleSuccessFeedback(ropeId)",
        "function beginSeaTurtleFailureFeedback(ropeId)",
        'scheduleWithRegistry("sea-turtle-feedback"',
        "sequence.sequenceId !== activeRescueSequence.sequenceId",
    )
    for token in required:
        assert token in text


def test_app_js_retains_completion_handoff() -> None:
    text = _read(APP)
    required = (
        "function completeSeaTurtleSuccess()",
        "State.beginTransition(State.Phases.RESCUE_SUCCESS)",
        "startMissionSuccessPresentation(sequence)",
    )
    for token in required:
        assert token in text


def test_no_start_sea_turtle_interaction_without_sequence_in_public_api() -> None:
    text = _read(CONTROLLER)
    lines = text.split("\n")
    public_api_lines = []
    in_public_api = False
    for line in lines:
        if "export interface SeaTurtleLifecycleAppApi" in line:
            in_public_api = True
        if in_public_api:
            public_api_lines.append(line)
            if line.strip() == "}":
                break
    public_api_text = "\n".join(public_api_lines)
    assert "startSeaTurtleInteraction()" not in public_api_text, (
        "startSeaTurtleInteraction() without sequence must not remain in public API"
    )
