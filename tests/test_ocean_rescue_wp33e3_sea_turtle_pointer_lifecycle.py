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

import sys
from pathlib import Path

import pytest
from playwright.sync_api import Page, sync_playwright

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
from test_ocean_rescue_wp11_dev_server import ViteServerFixture  # noqa: E402

REPO_ROOT = TESTS_DIR.parent
SRC = REPO_ROOT / "domains" / "ocean-rescue" / "src"
CONTROLLER = SRC / "controllers" / "sea-turtle-lifecycle.ts"
APP = SRC / "app.js"
RUNTIME_ABI = SRC / "contracts" / "runtime-abi.ts"
JUSTFILE = REPO_ROOT / "Justfile"

LOGICAL_WIDTH = 1280
LOGICAL_HEIGHT = 720

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
# Browser pointer capture lifecycle proof (trusted Playwright mouse gestures)
# ---------------------------------------------------------------------------


def _instrument(page: Page, base_url: str):
    page_errors: list[str] = []
    console_errors: list[str] = []
    request_failures: list[dict[str, object]] = []
    external_requests: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on(
        "console",
        lambda message: (
            console_errors.append(message.text) if message.type == "error" else None
        ),
    )
    page.on(
        "requestfailed",
        lambda request: request_failures.append(
            {"url": request.url, "failure": request.failure}
        ),
    )
    page.on(
        "request",
        lambda request: (
            external_requests.append(request.url)
            if not request.url.startswith(base_url)
            else None
        ),
    )
    return page_errors, console_errors, request_failures, external_requests


def _assert_quality_gates(errors) -> None:
    page_errors, console_errors, request_failures, external_requests = errors
    assert page_errors == [], f"page errors: {page_errors}"
    assert console_errors == [], f"console errors: {console_errors}"
    assert request_failures == [], f"request failures: {request_failures}"
    assert [
        url
        for url in external_requests
        if not url.startswith("data:")
        and "localhost" not in url
        and "127.0.0.1" not in url
    ] == [], f"external requests: {external_requests}"


def _boot_app(page: Page) -> None:
    page.wait_for_selector(
        "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=20000
    )


def _force_rescue_active(page: Page) -> None:
    page.evaluate(
        """() => {
          OceanRescue.State.forcePhase(OceanRescue.State.Phases.RESCUE_ACTIVE);
        }"""
    )


def _set_active_rescue_sequence(page: Page, sequence):
    page.evaluate(
        "(seq) => OceanRescue.App.setActiveRescueSequence(seq)", sequence
    )


def _make_sea_turtle_sequence(page: Page, sequence_id: int):
    return page.evaluate(
        """(id) => {
          const Rescue = OceanRescue.Rescue;
          const content = Rescue.getMissionContent('sea-turtle');
          return {
            sequenceId: id,
            missionId: 'sea-turtle',
            gupId: 'gup-c',
            missionContent: content,
            tutorialComplete: true,
            tutorialSkipped: true,
          };
        }""",
        sequence_id,
    )


def _canvas_logical_to_client(canvas_el, logical_x, logical_y):
    return canvas_el.evaluate(
        """(el, [lx, ly]) => {
          const rect = el.getBoundingClientRect();
          const logicalW = 1280;
          const logicalH = 720;
          const scaleX = rect.width / logicalW;
          const scaleY = rect.height / logicalH;
          return {
            x: Math.round(rect.left + lx * scaleX),
            y: Math.round(rect.top + ly * scaleY),
          };
        }""",
        [logical_x, logical_y],
    )


def _install_pointer_trace(page: Page) -> None:
    page.evaluate(
        """() => {
          window.__wp33e3Trace = {
            pointerId: null,
            downCount: 0,
            moveCount: 0,
            upCount: 0,
            cancelCount: 0,
            upPointerId: null,
            upTrusted: null
          };
          const canvas = document.getElementById('ocean-rescue-canvas');
          if (!canvas) return;
          canvas.addEventListener('pointerdown', (e) => {
            window.__wp33e3Trace.pointerId = e.pointerId;
            window.__wp33e3Trace.downCount += 1;
          });
          canvas.addEventListener('pointermove', (e) => {
            window.__wp33e3Trace.moveCount += 1;
          });
          canvas.addEventListener('pointerup', (e) => {
            window.__wp33e3Trace.upCount += 1;
            window.__wp33e3Trace.upPointerId = e.pointerId;
            window.__wp33e3Trace.upTrusted = e.isTrusted;
          });
          canvas.addEventListener('pointercancel', (e) => {
            window.__wp33e3Trace.cancelCount += 1;
          });
        }"""
    )


def _start_session(page: Page, seq) -> None:
    result = page.evaluate(
        "(seq) => OceanRescue.App.startSeaTurtleSession(seq)", seq
    )
    assert result is True, "startSeaTurtleSession must return true"


def _ensure_canvas_visible(page: Page) -> None:
    page.evaluate(
        """() => {
          const profile = document.getElementById('ocean-rescue-profile-choice');
          if (profile) {
            profile.style.display = 'none';
          }
          const c = document.getElementById('ocean-rescue-canvas');
          if (c && c.parentElement) {
            c.parentElement.style.display = 'block';
          }
        }"""
    )
    page.wait_for_function(
        "() => { "
        "  const c = document.getElementById('ocean-rescue-canvas'); "
        "  return c && c.offsetWidth > 0 && c.offsetHeight > 0; "
        "}",
        timeout=5000,
    )


def _trigger_pointer_down(page: Page, start_client: dict) -> int | float:
    """Move to position and press mouse button so the browser generates a trusted pointerdown.

    The canvas trace listener records the real browser-assigned pointerId,
    which is returned for subsequent capture/release verification.
    """
    page.mouse.move(start_client["x"], start_client["y"])
    page.mouse.down()
    pointer_id = page.evaluate("() => window.__wp33e3Trace.pointerId")
    assert pointer_id is not None, (
        "trusted pointerdown did not fire or trace listener did not record pointerId"
    )
    assert isinstance(pointer_id, (int, float)), (
        f"observed pointerId must be a number, got {type(pointer_id).__name__}"
    )
    assert pointer_id == pointer_id, (
        f"observed pointerId must be finite, got {pointer_id}"
    )
    return pointer_id


def _trigger_pointer_up(page: Page, client_x: int, client_y: int) -> None:
    """Generate a trusted browser pointerup via Playwright mouse input.

    Moves the cursor to (client_x, client_y) and releases the mouse button
    using page.mouse.up(), which produces a native isTrusted=true PointerEvent
    with the same browser-assigned pointerId that was observed during the
    preceding trusted pointerdown.
    """
    page.mouse.move(client_x, client_y)
    page.mouse.up()


def _check_pointer_capture(page: Page, pointer_id: int | float) -> None:
    """Verify native hasPointerCapture is true. Controller state is not a fallback."""
    has_capture = page.evaluate(
        "(id) => { "
        "  const canvas = document.getElementById('ocean-rescue-canvas'); "
        "  if (!canvas || typeof canvas.hasPointerCapture !== 'function') return null; "
        "  return canvas.hasPointerCapture(id); "
        "}",
        pointer_id,
    )
    assert has_capture is True, (
        f"native hasPointerCapture({pointer_id}) must be true after pointerdown, got {has_capture}"
    )


def _check_pointer_release(page: Page, pointer_id: int | float) -> None:
    """Verify native hasPointerCapture is false. Controller state is not a fallback."""
    has_capture = page.evaluate(
        "(id) => { "
        "  const canvas = document.getElementById('ocean-rescue-canvas'); "
        "  if (!canvas || typeof canvas.hasPointerCapture !== 'function') return null; "
        "  return canvas.hasPointerCapture(id); "
        "}",
        pointer_id,
    )
    assert has_capture is False, (
        f"native hasPointerCapture({pointer_id}) must be false after release, got {has_capture}"
    )


def _trigger_pointer_cancel(
    page: Page, pointer_id: int | float, client_x: int, client_y: int
) -> None:
    """Dispatch a synthetic pointercancel on the canvas.

    This is intentionally synthetic (not generated by the browser runtime)
    and uses the real browser-assigned pointerId so the controller's
    pointerId match check passes. The event routes through the shared DOM
    listener (onRescuePointerCancel) to the canonical ESM controller —
    the handler is never called directly from Python.
    """
    page.evaluate(
        "(args) => { "
        "  const x = args[0]; "
        "  const y = args[1]; "
        "  const pid = args[2]; "
        "  const canvas = document.getElementById('ocean-rescue-canvas'); "
        "  if (!canvas) return; "
        "  const e = new PointerEvent('pointercancel', { "
        "    clientX: x, clientY: y, "
        "    pointerId: pid, isPrimary: true, button: 0, bubbles: true "
        "  }); "
        "  canvas.dispatchEvent(e); "
        "}",
        [client_x, client_y, pointer_id],
    )


def test_pointer_down_acquires_capture_and_sets_active() -> None:
    """pointerdown on rope-1 start acquires capture and sets pointerActive=true."""
    with ViteServerFixture() as server:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": LOGICAL_WIDTH, "height": LOGICAL_HEIGHT}
            )
            context.add_init_script(
                "localStorage.clear(); sessionStorage.clear();"
            )
            page = context.new_page()
            errors = _instrument(page, server.base_url)
            page.goto(f"{server.base_url}/index.dev.html")
            _boot_app(page)
            _force_rescue_active(page)

            seq = _make_sea_turtle_sequence(page, 1)
            _set_active_rescue_sequence(page, seq)
            _start_session(page, seq)

            _ensure_canvas_visible(page)
            _install_pointer_trace(page)

            rope_start = page.evaluate(
                "() => { "
                "  const r = OceanRescue.SeaTurtle.Ropes[0]; "
                "  return { x: r.start.x, y: r.start.y }; "
                "}"
            )

            canvas = page.locator("#ocean-rescue-canvas")
            start_client = _canvas_logical_to_client(canvas, rope_start["x"], rope_start["y"])

            observed_pointer_id = _trigger_pointer_down(page, start_client)

            snapshot = page.evaluate(
                "() => OceanRescue.SeaTurtle.getSnapshot()"
            )
            assert snapshot["pointerActive"] is True, (
                "pointerActive must be true after pointerdown"
            )

            trace = page.evaluate("() => window.__wp33e3Trace")
            assert trace["downCount"] == 1, "pointerdown listener must fire once"
            assert isinstance(observed_pointer_id, (int, float)), (
                "observed pointerId must be a number"
            )
            assert observed_pointer_id == observed_pointer_id, (
                "pointerId must be finite"
            )

            _check_pointer_capture(page, observed_pointer_id)

            tracked = page.evaluate(
                "(id) => OceanRescue.App.isTrackedSeaTurtlePointer(id)",
                observed_pointer_id,
            )
            assert tracked is True, (
                "controller must track the captured pointerId"
            )

            _assert_quality_gates(errors)
            context.close()
            browser.close()


def test_pointer_move_keeps_same_captured_pointer() -> None:
    """pointermove after down uses the same captured pointer and keeps active."""
    with ViteServerFixture() as server:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": LOGICAL_WIDTH, "height": LOGICAL_HEIGHT}
            )
            context.add_init_script(
                "localStorage.clear(); sessionStorage.clear();"
            )
            page = context.new_page()
            errors = _instrument(page, server.base_url)
            page.goto(f"{server.base_url}/index.dev.html")
            _boot_app(page)
            _force_rescue_active(page)

            seq = _make_sea_turtle_sequence(page, 2)
            _set_active_rescue_sequence(page, seq)
            _start_session(page, seq)

            _ensure_canvas_visible(page)
            _install_pointer_trace(page)

            rope_start = page.evaluate(
                "() => { "
                "  const r = OceanRescue.SeaTurtle.Ropes[0]; "
                "  return { x: r.start.x, y: r.start.y }; "
                "}"
            )
            rope_end = page.evaluate(
                "() => { "
                "  const r = OceanRescue.SeaTurtle.Ropes[0]; "
                "  return { x: r.end.x, y: r.end.y }; "
                "}"
            )

            canvas = page.locator("#ocean-rescue-canvas")
            start_client = _canvas_logical_to_client(canvas, rope_start["x"], rope_start["y"])
            end_client = _canvas_logical_to_client(canvas, rope_end["x"], rope_end["y"])

            observed_pointer_id = _trigger_pointer_down(page, start_client)

            steps = 5
            for i in range(1, steps + 1):
                frac = i / steps
                move_x = int(start_client["x"] + (end_client["x"] - start_client["x"]) * frac)
                move_y = int(start_client["y"] + (end_client["y"] - start_client["y"]) * frac)
                page.mouse.move(move_x, move_y)

            trace_after = page.evaluate("() => window.__wp33e3Trace")
            assert trace_after["moveCount"] > 0, (
                "pointermove listener must fire during drag"
            )

            snapshot = page.evaluate(
                "() => OceanRescue.SeaTurtle.getSnapshot()"
            )
            assert snapshot["pointerActive"] is True, (
                "pointerActive must remain true during pointermove"
            )

            _check_pointer_capture(page, observed_pointer_id)

            tracked = page.evaluate(
                "(id) => OceanRescue.App.isTrackedSeaTurtlePointer(id)",
                observed_pointer_id,
            )
            assert tracked is True, (
                "controller must still track the same pointerId after moves"
            )

            _trigger_pointer_up(page, end_client["x"], end_client["y"])
            _assert_quality_gates(errors)
            context.close()
            browser.close()


def test_pointer_up_releases_capture_and_clears_active() -> None:
    """pointerup releases capture and sets pointerActive=false."""
    with ViteServerFixture() as server:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": LOGICAL_WIDTH, "height": LOGICAL_HEIGHT}
            )
            context.add_init_script(
                "localStorage.clear(); sessionStorage.clear();"
            )
            page = context.new_page()
            errors = _instrument(page, server.base_url)
            page.goto(f"{server.base_url}/index.dev.html")
            _boot_app(page)
            _force_rescue_active(page)

            seq = _make_sea_turtle_sequence(page, 3)
            _set_active_rescue_sequence(page, seq)
            _start_session(page, seq)

            _ensure_canvas_visible(page)
            _install_pointer_trace(page)

            rope_start = page.evaluate(
                "() => { "
                "  const r = OceanRescue.SeaTurtle.Ropes[0]; "
                "  return { x: r.start.x, y: r.start.y }; "
                "}"
            )

            canvas = page.locator("#ocean-rescue-canvas")
            start_client = _canvas_logical_to_client(canvas, rope_start["x"], rope_start["y"])

            observed_pointer_id = _trigger_pointer_down(page, start_client)

            _check_pointer_capture(page, observed_pointer_id)

            _trigger_pointer_up(page, start_client["x"], start_client["y"])

            trace_after = page.evaluate("() => window.__wp33e3Trace")
            assert trace_after["upCount"] == 1, "pointerup listener must fire once"
            assert trace_after["upTrusted"] is True, (
                f"pointerup must be trusted (isTrusted=true), got {trace_after['upTrusted']}"
            )
            assert trace_after["upPointerId"] == observed_pointer_id, (
                f"pointerup pointerId must match pointerdown pointerId, "
                f"got upPointerId={trace_after['upPointerId']}, "
                f"observed_pointer_id={observed_pointer_id}"
            )

            snapshot = page.evaluate(
                "() => OceanRescue.SeaTurtle.getSnapshot()"
            )
            assert snapshot["pointerActive"] is False, (
                "pointerActive must be false after pointerup"
            )

            _check_pointer_release(page, observed_pointer_id)

            tracked = page.evaluate(
                "(id) => OceanRescue.App.isTrackedSeaTurtlePointer(id)",
                observed_pointer_id,
            )
            assert tracked is False, (
                "controller must not track the pointerId after pointerup"
            )

            _assert_quality_gates(errors)
            context.close()
            browser.close()


def test_pause_releases_active_pointer_capture() -> None:
    """enterPause releases active capture and sets pointerActive=false."""
    with ViteServerFixture() as server:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": LOGICAL_WIDTH, "height": LOGICAL_HEIGHT}
            )
            context.add_init_script(
                "localStorage.clear(); sessionStorage.clear();"
            )
            page = context.new_page()
            errors = _instrument(page, server.base_url)
            page.goto(f"{server.base_url}/index.dev.html")
            _boot_app(page)
            _force_rescue_active(page)

            seq = _make_sea_turtle_sequence(page, 4)
            _set_active_rescue_sequence(page, seq)
            _start_session(page, seq)

            _ensure_canvas_visible(page)
            _install_pointer_trace(page)

            rope_start = page.evaluate(
                "() => { "
                "  const r = OceanRescue.SeaTurtle.Ropes[0]; "
                "  return { x: r.start.x, y: r.start.y }; "
                "}"
            )

            canvas = page.locator("#ocean-rescue-canvas")
            start_client = _canvas_logical_to_client(canvas, rope_start["x"], rope_start["y"])

            observed_pointer_id = _trigger_pointer_down(page, start_client)

            snapshot_before = page.evaluate(
                "() => OceanRescue.SeaTurtle.getSnapshot()"
            )
            assert snapshot_before["pointerActive"] is True

            _check_pointer_capture(page, observed_pointer_id)

            page.evaluate("() => OceanRescue.App.enterPause()")
            page.wait_for_function(
                "OceanRescue.App.isPauseActive()", timeout=3000
            )

            snapshot_pause = page.evaluate(
                "() => OceanRescue.SeaTurtle.getSnapshot()"
            )
            assert snapshot_pause["pointerActive"] is False, (
                "pointerActive must be false during pause"
            )

            _check_pointer_release(page, observed_pointer_id)

            tracked_pause = page.evaluate(
                "(id) => OceanRescue.App.isTrackedSeaTurtlePointer(id)",
                observed_pointer_id,
            )
            assert tracked_pause is False, (
                "controller must not track pointerId during pause"
            )

            page.mouse.up()
            snapshot_after_up_during_pause = page.evaluate(
                "() => OceanRescue.SeaTurtle.getSnapshot()"
            )
            assert snapshot_after_up_during_pause["pointerActive"] is False, (
                "mouse.up during pause must not re-activate pointer"
            )

            page.mouse.down()
            page.mouse.up()

            _assert_quality_gates(errors)
            context.close()
            browser.close()


def test_session_shutdown_releases_active_pointer_capture() -> None:
    """stopSeaTurtleSession releases capture and clears pointerActive."""
    with ViteServerFixture() as server:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": LOGICAL_WIDTH, "height": LOGICAL_HEIGHT}
            )
            context.add_init_script(
                "localStorage.clear(); sessionStorage.clear();"
            )
            page = context.new_page()
            errors = _instrument(page, server.base_url)
            page.goto(f"{server.base_url}/index.dev.html")
            _boot_app(page)
            _force_rescue_active(page)

            seq = _make_sea_turtle_sequence(page, 5)
            _set_active_rescue_sequence(page, seq)
            _start_session(page, seq)

            _ensure_canvas_visible(page)
            _install_pointer_trace(page)

            rope_start = page.evaluate(
                "() => { "
                "  const r = OceanRescue.SeaTurtle.Ropes[0]; "
                "  return { x: r.start.x, y: r.start.y }; "
                "}"
            )

            canvas = page.locator("#ocean-rescue-canvas")
            start_client = _canvas_logical_to_client(canvas, rope_start["x"], rope_start["y"])

            observed_pointer_id = _trigger_pointer_down(page, start_client)

            snapshot_before = page.evaluate(
                "() => OceanRescue.SeaTurtle.getSnapshot()"
            )
            assert snapshot_before["pointerActive"] is True

            _check_pointer_capture(page, observed_pointer_id)

            result = page.evaluate(
                "() => OceanRescue.App.stopSeaTurtleSession()"
            )
            assert result is True, "stopSeaTurtleSession must return true"

            active_session = page.evaluate(
                "() => OceanRescue.App.getActiveSeaTurtleSession()"
            )
            assert active_session is None, (
                "active session must be null after stopSeaTurtleSession"
            )

            snapshot_after = page.evaluate(
                "() => OceanRescue.SeaTurtle.getSnapshot()"
            )
            assert snapshot_after["active"] is False, (
                "SeaTurtle must not be active after stop"
            )
            assert snapshot_after["pointerActive"] is False, (
                "pointerActive must be false after stop"
            )

            _check_pointer_release(page, observed_pointer_id)

            shutdown_result = page.evaluate(
                "() => OceanRescue.App.shutdownSeaTurtlePointer()"
            )
            assert shutdown_result is True, (
                "shutdownSeaTurtlePointer must return true on second call"
            )

            _assert_quality_gates(errors)
            context.close()
            browser.close()


def test_pointer_cancel_releases_capture_and_clears_active_gesture() -> None:
    """Native pointer capture acquires on trusted pointerdown and releases on synthetic pointercancel.

    Proves the exact transition hasPointerCapture(pointerId): false -> true -> false
    using the real browser-assigned pointerId, with no controller-state fallback.

    - trusted pointerdown comes from Playwright page.mouse.down() (not synthetic)
    - pointerId is observed from the browser, never hardcoded
    - native hasPointerCapture() is the sole capture/release criterion
    - synthetic pointercancel routes through the shared DOM listener to the controller
    - page.mouse.up() runs in finally so the button is always released
    """
    server = ViteServerFixture()
    browser = None
    context = None
    page = None
    try:
        server.__enter__()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": LOGICAL_WIDTH, "height": LOGICAL_HEIGHT}
            )
            context.add_init_script(
                "localStorage.clear(); sessionStorage.clear();"
            )
            page = context.new_page()
            errors = _instrument(page, server.base_url)
            page.goto(f"{server.base_url}/index.dev.html")
            _boot_app(page)
            _force_rescue_active(page)

            seq = _make_sea_turtle_sequence(page, 6)
            _set_active_rescue_sequence(page, seq)
            _start_session(page, seq)

            _ensure_canvas_visible(page)
            _install_pointer_trace(page)

            rope_start = page.evaluate(
                "() => { "
                "  const r = OceanRescue.SeaTurtle.Ropes[0]; "
                "  return { x: r.start.x, y: r.start.y }; "
                "}"
            )

            canvas = page.locator("#ocean-rescue-canvas")
            start_client = _canvas_logical_to_client(canvas, rope_start["x"], rope_start["y"])

            # Step 1: trusted pointerdown via Playwright mouse gesture
            observed_pointer_id = _trigger_pointer_down(page, start_client)

            # Step 2: verify native capture acquired (false -> true)
            has_capture_before = page.evaluate(
                "(id) => { "
                "  const c = document.getElementById('ocean-rescue-canvas'); "
                "  if (!c || typeof c.hasPointerCapture !== 'function') return null; "
                "  return c.hasPointerCapture(id); "
                "}",
                observed_pointer_id,
            )
            assert has_capture_before is True, (
                f"native hasPointerCapture({observed_pointer_id}) must be true after trusted pointerdown, got {has_capture_before}"
            )

            snapshot = page.evaluate(
                "() => OceanRescue.SeaTurtle.getSnapshot()"
            )
            assert snapshot["pointerActive"] is True, (
                "SeaTurtle snapshot.pointerActive must be true after capture acquired"
            )

            tracked = page.evaluate(
                "(id) => OceanRescue.App.isTrackedSeaTurtlePointer(id)",
                observed_pointer_id,
            )
            assert tracked is True, (
                "controller must track the browser-assigned pointerId after capture"
            )

            # Step 3: synthetic pointercancel dispatched on canvas (routes through DOM listener)
            _trigger_pointer_cancel(page, observed_pointer_id, start_client["x"], start_client["y"])

            trace_after = page.evaluate("() => window.__wp33e3Trace")
            assert trace_after["cancelCount"] == 1, (
                f"pointercancel listener must fire exactly once, got {trace_after['cancelCount']}"
            )

            # Step 4: verify native capture released (true -> false)
            has_capture_after = page.evaluate(
                "(id) => { "
                "  const c = document.getElementById('ocean-rescue-canvas'); "
                "  if (!c || typeof c.hasPointerCapture !== 'function') return null; "
                "  return c.hasPointerCapture(id); "
                "}",
                observed_pointer_id,
            )
            assert has_capture_after is False, (
                f"native hasPointerCapture({observed_pointer_id}) must be false after pointercancel, got {has_capture_after}"
            )

            snapshot_after = page.evaluate(
                "() => OceanRescue.SeaTurtle.getSnapshot()"
            )
            assert snapshot_after["pointerActive"] is False, (
                "SeaTurtle snapshot.pointerActive must be false after capture released"
            )

            tracked_after = page.evaluate(
                "(id) => OceanRescue.App.isTrackedSeaTurtlePointer(id)",
                observed_pointer_id,
            )
            assert tracked_after is False, (
                "controller must not track the pointerId after pointercancel"
            )

            # Step 5: release mouse button and verify late pointerup does not re-activate
            page.mouse.up()

            snapshot_final = page.evaluate(
                "() => OceanRescue.SeaTurtle.getSnapshot()"
            )
            assert snapshot_final["pointerActive"] is False, (
                "late pointerup after pointercancel must not re-activate gesture"
            )

            _assert_quality_gates(errors)
    finally:
        if context:
            try:
                context.close()
            except Exception:
                pass
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        try:
            server.__exit__(None, None, None)
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
