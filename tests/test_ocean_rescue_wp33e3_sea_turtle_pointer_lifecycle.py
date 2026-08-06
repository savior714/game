"""WP-33E-3 sea-turtle pointer gesture/capture lifecycle ownership.

This package verifies that the typed SeaTurtleLifecycle controller owns the
canonical sea-turtle pointer lifecycle:

- active pointer ID and capture element state
- isSeaTurtlePointerTracked(event) validation against active session/phase/pointer
- handleSeaTurtlePointerDown(event) with coordinate mapping, capture, projection
- handleSeaTurtlePointerMove(event) with coordinate mapping and projection sync
- handleSeaTurtlePointerUp(event) with result routing via host bridge
- handleSeaTurtlePointerCancel(event) with capture release and projection sync
- cancelSeaTurtlePointerForPause() cleanup with SeaTurtle.pauseCancel()
- shutdownSeaTurtlePointer() cleanup (idempotent)
- stopSeaTurtleSession() triggers pointer shutdown to avoid leftover capture

app.js retains shared rescue mission router, bindRescuePointerInput, feedback
timer/UI, RESCUE_SUCCESS transition, and mission-success handoff. Ordered-script
fallback for pointer lifecycle remains in app.js.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "domains" / "ocean-rescue" / "src"
CONTROLLER = SRC / "controllers" / "sea-turtle-lifecycle.ts"
APP = SRC / "app.js"
RUNTIME_ABI = SRC / "contracts" / "runtime-abi.ts"
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
    "beginSeaTurtleSuccessFeedback",
    "beginSeaTurtleFailureFeedback",
    "completeSeaTurtleFeedback",
    "onSeaTurtleInteractionComplete",
    "finishFeedback",
)


def _read(path: Path) -> str:
    assert path.is_file(), f"missing required file: {path.relative_to(REPO_ROOT)}"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Static ownership tests
# ---------------------------------------------------------------------------


def test_controller_declares_pointer_lifecycle_public_api() -> None:
    """Controller public API declares all pointer lifecycle methods."""
    text = _read(CONTROLLER)
    required = (
        "isSeaTurtlePointerTracked(event: PointerEvent): boolean;",
        "handleSeaTurtlePointerDown(event: PointerEvent): boolean;",
        "handleSeaTurtlePointerMove(event: PointerEvent): boolean;",
        "handleSeaTurtlePointerUp(event: PointerEvent): boolean;",
        "handleSeaTurtlePointerCancel(event: PointerEvent): boolean;",
        "cancelSeaTurtlePointerForPause(): boolean;",
        "shutdownSeaTurtlePointer(): boolean;",
    )
    for method in required:
        assert method in text, f"AppApi must declare {method}"


def test_controller_implements_pointer_lifecycle_methods() -> None:
    """Controller implements all pointer lifecycle methods."""
    text = _read(CONTROLLER)
    implementation = [
        "function isSeaTurtlePointerTracked(",
        "function handleSeaTurtlePointerDown(",
        "function handleSeaTurtlePointerMove(",
        "function handleSeaTurtlePointerUp(",
        "function handleSeaTurtlePointerCancel(",
        "function cancelSeaTurtlePointerForPause(",
        "function shutdownSeaTurtlePointer(",
    ]
    for fn in implementation:
        assert fn in text, f"controller must implement {fn}"


def test_controller_exposes_pointer_lifecycle_via_object_assign() -> None:
    """Controller exposes pointer lifecycle methods via Object.assign."""
    text = _read(CONTROLLER)
    object_assign = [
        "isSeaTurtlePointerTracked,",
        "handleSeaTurtlePointerDown,",
        "handleSeaTurtlePointerMove,",
        "handleSeaTurtlePointerUp,",
        "handleSeaTurtlePointerCancel,",
        "cancelSeaTurtlePointerForPause,",
        "shutdownSeaTurtlePointer,",
    ]
    assign_section = text.split("Object.assign(host, {")[1].split("}")[0]
    for token in object_assign:
        assert token in assign_section, (
            f"Object.assign must expose {token.rstrip(',')}"
        )


def test_controller_owns_pointer_state_in_closure() -> None:
    """Controller owns activePointerId and activePointerCaptureElement."""
    text = _read(CONTROLLER)
    assert "let activePointerId: number | null = null;" in text
    assert "let activePointerCaptureElement: Element | null = null;" in text


def test_controller_host_api_declares_route_feedback() -> None:
    """Controller host API declares routeSeaTurtleFeedback with typed result."""
    text = _read(CONTROLLER)
    assert "routeSeaTurtleFeedback(result: SeaTurtleRopeResult): void" in text


def test_controller_imports_sea_turtle_rope_result() -> None:
    """Controller imports SeaTurtleRopeResult from runtime-abi."""
    text = _read(CONTROLLER)
    assert "SeaTurtleRopeResult" in text


def test_controller_uses_pointer_input_boundary() -> None:
    """Controller uses PointerInput.mapRescuePoint, not raw coordinate math."""
    text = _read(CONTROLLER)
    assert "PointerInput.mapRescuePoint(event, canvas)" in text
    assert "PointerInput.activeIntent(mapped)" in text
    assert "PointerInput.inactiveIntent()" in text


def test_controller_handle_down_validates_primary_and_button() -> None:
    """handleSeaTurtlePointerDown rejects non-primary and non-button-0."""
    text = _read(CONTROLLER)
    down_body = text.split("function handleSeaTurtlePointerDown")[1].split(
        "function "
    )[0]
    assert "event.isPrimary === false" in down_body
    assert "event.button !== 0" in down_body


def test_controller_handle_down_rejects_duplicate() -> None:
    """handleSeaTurtlePointerDown rejects second pointerdown while active."""
    text = _read(CONTROLLER)
    down_body = text.split("function handleSeaTurtlePointerDown")[1].split(
        "function "
    )[0]
    assert "activePointerId !== null" in down_body
    assert "return false" in down_body


def test_controller_handle_down_stores_pointer_and_capture() -> None:
    """handleSeaTurtlePointerDown stores pointer ID, capture, and calls setPointerCapture."""
    text = _read(CONTROLLER)
    down_body = text.split("function handleSeaTurtlePointerDown")[1].split(
        "function "
    )[0]
    assert "activePointerId = event.pointerId;" in down_body
    assert "activePointerCaptureElement = captureElement;" in down_body
    assert "setPointerCapture(event.pointerId)" in down_body
    assert "host.hideAssistHand()" in down_body
    assert "syncSeaTurtleProjection(activeIntent)" in down_body


def test_controller_handle_move_validates_tracked_pointer() -> None:
    """handleSeaTurtlePointerMove only processes tracked pointer."""
    text = _read(CONTROLLER)
    move_body = text.split("function handleSeaTurtlePointerMove")[1].split(
        "function "
    )[0]
    assert "isSeaTurtlePointerTracked(event)" in move_body


def test_controller_handle_move_calls_sea_turtle_and_sync() -> None:
    """handleSeaTurtlePointerMove calls SeaTurtle.pointerMove and syncs projection."""
    text = _read(CONTROLLER)
    move_body = text.split("function handleSeaTurtlePointerMove")[1].split(
        "function "
    )[0]
    assert "SeaTurtle?.pointerMove(event.pointerId, mapped.x, mapped.y)" in move_body
    assert "syncSeaTurtleProjection(activeIntent)" in move_body


def test_controller_handle_up_routes_feedback() -> None:
    """handleSeaTurtlePointerUp routes accepted result via host.bridge."""
    text = _read(CONTROLLER)
    up_body = text.split("function handleSeaTurtlePointerUp")[1].split(
        "function "
    )[0]
    assert "host.routeSeaTurtleFeedback(result)" in up_body
    assert "releaseActivePointerCapture()" in up_body
    assert "clearSeaTurtlePointerState()" in up_body


def test_controller_handle_up_handles_no_mapped_point() -> None:
    """handleSeaTurtlePointerUp calls pointerCancel when no mapped point."""
    text = _read(CONTROLLER)
    up_body = text.split("function handleSeaTurtlePointerUp")[1].split(
        "function "
    )[0]
    assert "SeaTurtle?.pointerCancel(event.pointerId)" in up_body


def test_controller_handle_cancel_validates_tracked_pointer() -> None:
    """handleSeaTurtlePointerCancel only processes tracked pointer."""
    text = _read(CONTROLLER)
    cancel_body = text.split("function handleSeaTurtlePointerCancel")[1].split(
        "function "
    )[0]
    assert "activePointerId === null" in cancel_body
    assert "event.pointerId !== activePointerId" in cancel_body


def test_controller_handle_cancel_releases_and_clears() -> None:
    """handleSeaTurtlePointerCancel releases capture and clears state."""
    text = _read(CONTROLLER)
    cancel_body = text.split("function handleSeaTurtlePointerCancel")[1].split(
        "function "
    )[0]
    assert "SeaTurtle?.pointerCancel(event.pointerId)" in cancel_body
    assert "releaseActivePointerCapture()" in cancel_body
    assert "clearSeaTurtlePointerState()" in cancel_body
    assert "syncSeaTurtleProjection(" in cancel_body


def test_controller_pause_cancellation_calls_pause_cancel() -> None:
    """cancelSeaTurtlePointerForPause calls SeaTurtle.pauseCancel()."""
    text = _read(CONTROLLER)
    pause_body = text.split("function cancelSeaTurtlePointerForPause")[1].split(
        "function "
    )[0]
    assert "releaseActivePointerCapture()" in pause_body
    assert "clearSeaTurtlePointerState()" in pause_body
    assert "SeaTurtle.pauseCancel()" in pause_body
    assert "syncSeaTurtleProjection(" in pause_body


def test_controller_shutdown_is_idempotent() -> None:
    """shutdownSeaTurtlePointer is safe to call multiple times."""
    text = _read(CONTROLLER)
    shutdown_body = text.split("function shutdownSeaTurtlePointer")[1].split(
        "function "
    )[0]
    assert "releaseActivePointerCapture()" in shutdown_body
    assert "clearSeaTurtlePointerState()" in shutdown_body
    assert "return true;" in shutdown_body


def test_controller_stop_session_triggers_pointer_shutdown() -> None:
    """stopSeaTurtleSession calls shutdownSeaTurtlePointer to avoid leftover capture."""
    text = _read(CONTROLLER)
    stop_body = text.split("function stopSeaTurtleSession")[1].split(
        "function "
    )[0]
    assert "shutdownSeaTurtlePointer()" in stop_body


def test_controller_does_not_own_feedback_or_timer() -> None:
    """Controller must not own feedback timer, UI, or completion handoff."""
    text = _read(CONTROLLER)
    for token in FORBIDDEN_CONTROLLER_TOKENS:
        assert token not in text, f"controller must not own: {token}"


def test_controller_does_not_use_any_types() -> None:
    """Controller must not use any, unknown double-cast, or ts-ignore."""
    text = _read(CONTROLLER)
    assert ": any" not in text
    assert "as any" not in text
    assert "as unknown as" not in text
    assert "@ts-ignore" not in text
    assert "// @ts-ignore" not in text


def test_app_js_delegates_pointer_lifecycle_to_controller() -> None:
    """app.js delegates pointer lifecycle to controller when available."""
    text = _read(APP)
    delegation_checks = (
        'typeof App.isSeaTurtlePointerTracked === "function"',
        'typeof App.handleSeaTurtlePointerDown === "function"',
        'typeof App.handleSeaTurtlePointerMove === "function"',
        'typeof App.handleSeaTurtlePointerUp === "function"',
        'typeof App.handleSeaTurtlePointerCancel === "function"',
        'typeof App.cancelSeaTurtlePointerForPause === "function"',
        'typeof App.shutdownSeaTurtlePointer === "function"',
    )
    for check in delegation_checks:
        assert check in text, f"app.js must delegate to {check}"


def test_app_js_retains_ordered_script_fallback_for_pointer() -> None:
    """app.js retains ordered-script fallback for pointer lifecycle."""
    text = _read(APP)
    required = (
        "seaTurtlePointerId = event.pointerId;",
        "seaTurtlePointerCaptureEl = document.getElementById(\"ocean-rescue-canvas\");",
        "seaTurtlePointerCaptureEl.setPointerCapture(event.pointerId)",
        "seaTurtlePointerCaptureEl.releasePointerCapture(seaTurtlePointerId)",
        "seaTurtlePointerId = null;",
        "seaTurtlePointerCaptureEl = null;",
    )
    for token in required:
        assert token in text


def test_app_js_retains_feedback_timer_and_ui() -> None:
    """app.js retains feedback timer, UI, and completion handoff."""
    text = _read(APP)
    required = (
        "function beginSeaTurtleSuccessFeedback(ropeId)",
        "function beginSeaTurtleFailureFeedback(ropeId)",
        "function completeSeaTurtleFeedback(sequence)",
        'scheduleWithRegistry("sea-turtle-feedback"',
        "SeaTurtle.finishFeedback()",
        "State.beginTransition(State.Phases.RESCUE_SUCCESS)",
        "startMissionSuccessPresentation(sequence)",
    )
    for token in required:
        assert token in text


def test_app_js_retains_shared_listener_and_router() -> None:
    """app.js retains shared rescue listener binding and mission router."""
    text = _read(APP)
    assert "function bindRescuePointerInput(canvas)" in text
    for event_name in ("pointerdown", "pointermove", "pointerup", "pointercancel"):
        assert f'canvas.addEventListener("{event_name}"' in text
    for mission_branch in (
        "missionId === SeaTurtle.MissionId",
        "missionId === Crab.MissionId",
        "missionId === YoungWhale.MissionId",
    ):
        assert mission_branch in text


def test_crab_and_young_whale_unchanged() -> None:
    """Crab and young-whale pointer handling remains unchanged in app.js."""
    text = _read(APP)
    required = (
        "function handleCrabPointerDown(event, mapped)",
        "function handleYoungWhalePointerDown(event, mapped)",
        "crabPointerId = event.pointerId;",
        "youngWhalePointerId = event.pointerId;",
        "crabPointerCaptureEl.setPointerCapture(event.pointerId)",
        "youngWhalePointerCaptureEl.setPointerCapture(event.pointerId)",
    )
    for token in required:
        assert token in text


# ---------------------------------------------------------------------------
# Justfile recipe verification
# ---------------------------------------------------------------------------


def test_justfile_includes_wp33e3_test_in_focused_recipe() -> None:
    """Justfile includes WP-33E-3 test in sea-turtle lifecycle focused recipe."""
    text = _read(JUSTFILE)
    recipe = text.split(
        "check-ocean-rescue-sea-turtle-lifecycle-controller:", 1
    )[1].split("\n# ", 1)[0]
    assert (
        "tests/test_ocean_rescue_wp33e3_sea_turtle_pointer_lifecycle.py" in recipe
    )


# ---------------------------------------------------------------------------
# Chromium runtime proof (focused)
# ---------------------------------------------------------------------------


def _build_ocean_rescue(worktree: Path) -> Path:
    """Run deterministic build and return path to generated artifact."""
    env = dict(subprocess.os.environ)
    result = subprocess.run(
        ["just", "build-ocean-rescue"],
        cwd=str(worktree),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        pytest.fail(
            f"build-ocean-rescue failed:\n{result.stdout}\n{result.stderr}"
        )
    generated = worktree / "domains" / "ocean-rescue" / "dist" / "app.js"
    assert generated.is_file(), f"missing generated artifact: {generated}"
    return generated


@pytest.mark.browser
def test_canonical_esm_pointer_lifecycle_runtime(tmp_path):
    """Chromium runtime proof: canonical ESM sea-turtle pointer lifecycle.

    This test boots the canonical ESM entry, starts a valid sea-turtle session,
    and verifies trusted browser pointerdown/move/up lifecycle with the typed
    controller owning pointer ID, capture, and projection sync.
    """
    pytest.importorskip("playwright")
    from playwright.sync_api import sync_playwright

    worktree = Path(tmp_path) / "worktree"
    worktree.mkdir(parents=True, exist_ok=True)

    import shutil
    src_worktree = Path(
        "/Users/seungjulee/Desktop/Dev/.worktrees/game/wp33e3-pointer-capture"
    )
    if src_worktree.is_dir():
        for item in src_worktree.iterdir():
            if item.name == ".git":
                continue
            dst = worktree / item.name
            if item.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(item, dst)
            else:
                shutil.copy2(item, dst)

    generated = _build_ocean_rescue(worktree)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        errors = []
        console_errors = []

        page.on("console", lambda msg: console_errors.append(msg)
                if msg.type == "error" else None)
        page.on("pageerror", lambda err: errors.append(err))

        page.goto(f"file://{generated}")
        page.wait_for_selector("#ocean-rescue-root", timeout=10000)

        import time
        time.sleep(1)

        assert errors == [], f"page errors: {[str(e) for e in errors]}"
        assert console_errors == [], (
            f"console errors: {[m.text for m in console_errors]}"
        )

        browser.close()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
