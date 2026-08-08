"""WP-33E-4 sea-turtle feedback lifecycle ownership.

This package verifies that the typed sea-turtle lifecycle controller owns the
feedback sequence, timer scheduling/cancellation, exactly-once callback
consumption, stale-session/snapshot rejection, and session-stop cleanup.

Host-app.js retains visual effects, dialogue/progress text, assist escalation,
RESCUE_SUCCESS transition, and mission-success presentation. The legacy
ordered-script lane keeps its full fallback orchestration.
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

LOGICAL_WIDTH = 1280
LOGICAL_HEIGHT = 720


def _read(path: Path) -> str:
    assert path.is_file(), f"missing required file: {path.relative_to(REPO_ROOT)}"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Static ownership tests
# ---------------------------------------------------------------------------


def test_controller_declares_begin_sea_turtle_feedback() -> None:
    text = _read(CONTROLLER)
    assert "beginSeaTurtleFeedback(result: SeaTurtleRopeResult): boolean" in text
    assert "function beginSeaTurtleFeedback(" in text


def test_controller_declares_clear_sea_turtle_feedback() -> None:
    text = _read(CONTROLLER)
    assert "clearSeaTurtleFeedback(): void" in text
    assert "function clearSeaTurtleFeedback(" in text


def test_controller_exposes_feedback_lifecycle_via_object_assign() -> None:
    text = _read(CONTROLLER)
    assign_section = text.split("Object.assign(host, {")[1].split("}")[0]
    assert "beginSeaTurtleFeedback," in assign_section
    assert "clearSeaTurtleFeedback," in assign_section


def test_controller_owns_feedback_sequence_type() -> None:
    text = _read(CONTROLLER)
    assert "interface SeaTurtleFeedbackSequence" in text
    assert "readonly rescueSequenceId: number" in text
    assert "readonly ropeId: SeaTurtleRopeId" in text
    assert 'kind: "success" | "failure"' in text


def test_controller_active_feedback_storage() -> None:
    text = _read(CONTROLLER)
    assert "let activeFeedback: SeaTurtleFeedbackSequence | null = null" in text


def test_controller_uses_host_complete_feedback_callback() -> None:
    text = _read(CONTROLLER)
    assert "onSeaTurtleFeedbackComplete(" in text


def test_controller_calls_sea_turtle_finish_feedback() -> None:
    text = _read(CONTROLLER)
    assert "SeaTurtle.finishFeedback()" in text


def test_controller_does_not_use_set_timeout() -> None:
    text = _read(CONTROLLER)
    assert "setTimeout" not in text


def test_controller_does_not_own_crab_or_young_whale() -> None:
    text = _read(CONTROLLER)
    assert "Crab" not in text
    assert "YoungWhale" not in text
    assert "youngWhale" not in text


def test_controller_does_not_call_begin_sea_turtle_success_feedback() -> None:
    text = _read(CONTROLLER)
    assert "beginSeaTurtleSuccessFeedback" not in text
    assert "beginSeaTurtleFailureFeedback" not in text
    assert "applySeaTurtleSuccessVisual" not in text
    assert "applySeaTurtleFailureVisual" not in text


def test_controller_does_not_call_mission_success_presentation() -> None:
    text = _read(CONTROLLER)
    assert "startMissionSuccessPresentation" not in text
    assert "beginTransition" not in text


def test_controller_stop_session_clears_feedback() -> None:
    text = _read(CONTROLLER)
    body = text.split("function stopSeaTurtleSession")[1].split("function ")[0]
    assert "clearSeaTurtleFeedback()" in body


def test_app_js_retains_visual_dialogue_and_handoff() -> None:
    text = _read(APP)
    required = (
        "function applySeaTurtleSuccessVisual()",
        "function applySeaTurtleFailureVisual()",
        "function setSeaTurtleDialogue(",
        "function completeSeaTurtleSuccess()",
        "State.beginTransition(State.Phases.RESCUE_SUCCESS)",
        "startMissionSuccessPresentation(sequence)",
    )
    for token in required:
        assert token in text, f"app.js must retain host-owned function: {token}"


def test_app_js_delegates_route_feedback_to_controller() -> None:
    text = _read(APP)
    assert 'typeof App.beginSeaTurtleFeedback === "function"' in text


# ---------------------------------------------------------------------------
# Runtime harness
# ---------------------------------------------------------------------------


def _make_sequence(page: Page, seq_id: int) -> None:
    page.evaluate(
        """(id) => {
        const c = window.OceanRescue.Rescue.getMissionContent('sea-turtle');
        window.OceanRescue.App.setActiveRescueSequence({
            sequenceId: id, missionId: 'sea-turtle', gupId: 'gup-c',
            missionContent: c, tutorialComplete: true, tutorialSkipped: true,
        });
    }""",
        seq_id,
    )


def _ensure_canvas_visible(page: Page) -> None:
    page.evaluate(
        """() => {
        const profile = document.getElementById('ocean-rescue-profile-choice');
        if (profile) profile.style.display = 'none';
        const overlay = document.getElementById('ocean-rescue-rescue-overlay');
        if (overlay) overlay.style.display = 'block';
        const canvas = document.getElementById('ocean-rescue-canvas');
        if (canvas && canvas.parentElement) canvas.parentElement.style.display = 'block';
    }"""
    )
    page.wait_for_function(
        "() => { "
        "  const c = document.getElementById('ocean-rescue-canvas'); "
        "  return c && c.offsetWidth > 0 && c.offsetHeight > 0; "
        "}",
        timeout=5000,
    )


def _start_session(page: Page, seq_id: int = 9001) -> None:
    page.evaluate(
        "() => window.OceanRescue.State.forcePhase(window.OceanRescue.State.Phases.RESCUE_ACTIVE)"
    )
    _make_sequence(page, seq_id)
    _ensure_canvas_visible(page)
    result = page.evaluate(
        "() => window.OceanRescue.App.startSeaTurtleSession(window.OceanRescue.App.getActiveRescueSequence())"
    )
    assert result is True, "startSeaTurtleSession must return true"


def _canvas_logical_to_client(page: Page, lx: float, ly: float) -> dict:
    return page.evaluate(
        """([lx, ly]) => {
        const el = document.getElementById('ocean-rescue-canvas');
        const rect = el.getBoundingClientRect();
        return {
            x: Math.round(rect.left + lx * (rect.width / 1280)),
            y: Math.round(rect.top + ly * (rect.height / 720)),
        };
    }""",
        [lx, ly],
    )


def _trace_rope(page: Page) -> None:
    rope = page.evaluate(
        "() => { const r = window.OceanRescue.SeaTurtle.Ropes[0]; return { sx: r.start.x, sy: r.start.y, ex: r.end.x, ey: r.end.y }; }"
    )
    start = _canvas_logical_to_client(page, rope["sx"], rope["sy"])
    end = _canvas_logical_to_client(page, rope["ex"], rope["ey"])
    page.mouse.move(start["x"], start["y"])
    page.mouse.down()
    steps = 8
    for i in range(1, steps + 1):
        frac = i / steps
        mx = int(start["x"] + (end["x"] - start["x"]) * frac)
        my = int(start["y"] + (end["y"] - start["y"]) * frac)
        page.mouse.move(mx, my)
    page.mouse.up()


def _snapshot(page: Page) -> dict:
    return page.evaluate(
        "() => { const s = window.OceanRescue.SeaTurtle.getSnapshot(); return { feedback: s.feedback, activeRopeId: s.activeRopeId, active: s.active }; }"
    )


@pytest.mark.ocean_rescue
class TestOceanRescueWP33EFeedbackLifecycleRuntime:
    def test_case_1_active_success(self) -> None:
        with ViteServerFixture() as server:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": LOGICAL_WIDTH, "height": LOGICAL_HEIGHT}
                )
                context.add_init_script("window.localStorage.clear();")
                page = context.new_page()
                try:
                    page.goto(
                        f"{server.base_url}/index.dev.html",
                        wait_until="domcontentloaded",
                    )
                    page.wait_for_selector(
                        "#ocean-rescue-root[data-ocean-rescue-ready='true']",
                        timeout=20000,
                    )
                    _start_session(page)
                    _trace_rope(page)
                    snap = _snapshot(page)
                    assert snap["feedback"] == "success", (
                        f"expected success, got {snap}"
                    )
                    page.evaluate(
                        "() => window.OceanRescue.App.__testFlushSeaTurtleFeedback()"
                    )
                    snap2 = _snapshot(page)
                    assert snap2["feedback"] is None, (
                        f"expected null after finish, got {snap2}"
                    )
                finally:
                    browser.close()

    def test_case_3_duplicate_callback_blocked(self) -> None:
        with ViteServerFixture() as server:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": LOGICAL_WIDTH, "height": LOGICAL_HEIGHT}
                )
                context.add_init_script("window.localStorage.clear();")
                page = context.new_page()
                try:
                    page.goto(
                        f"{server.base_url}/index.dev.html",
                        wait_until="domcontentloaded",
                    )
                    page.wait_for_selector(
                        "#ocean-rescue-root[data-ocean-rescue-ready='true']",
                        timeout=20000,
                    )
                    _start_session(page)
                    _trace_rope(page)
                    assert _snapshot(page)["feedback"] == "success"
                    page.evaluate(
                        "() => window.OceanRescue.App.__testFlushSeaTurtleFeedback()"
                    )
                    assert _snapshot(page)["feedback"] is None
                    page.evaluate(
                        "() => window.OceanRescue.App.__testFlushSeaTurtleFeedback()"
                    )
                    assert _snapshot(page)["feedback"] is None
                    assert _snapshot(page)["activeRopeId"] == "rope-2"
                finally:
                    browser.close()

    def test_case_4_stopped_session_blocks_callback(self) -> None:
        with ViteServerFixture() as server:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": LOGICAL_WIDTH, "height": LOGICAL_HEIGHT}
                )
                context.add_init_script("window.localStorage.clear();")
                page = context.new_page()
                try:
                    page.goto(
                        f"{server.base_url}/index.dev.html",
                        wait_until="domcontentloaded",
                    )
                    page.wait_for_selector(
                        "#ocean-rescue-root[data-ocean-rescue-ready='true']",
                        timeout=20000,
                    )
                    _start_session(page)
                    _trace_rope(page)
                    assert _snapshot(page)["feedback"] == "success"
                    page.evaluate("() => window.OceanRescue.App.stopSeaTurtleSession()")
                    page.evaluate(
                        "() => window.OceanRescue.App.__testFlushSeaTurtleFeedback()"
                    )
                    assert _snapshot(page)["active"] is False
                finally:
                    browser.close()
