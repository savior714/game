"""WP-33E-5A sea-turtle completion handoff.

Verifies that the typed sea-turtle lifecycle controller splits terminal
completion from non-terminal feedback, and that the host validates the active
session before executing RESCUE_SUCCESS transition and mission-success
presentation.
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
# Static contract checks
# ---------------------------------------------------------------------------


def test_host_api_declares_on_sea_turtle_interaction_complete() -> None:
    text = _read(CONTROLLER)
    assert "onSeaTurtleInteractionComplete(" in text
    assert "session: SeaTurtleSessionRef" in text


def test_controller_terminal_branch_calls_interaction_complete() -> None:
    text = _read(CONTROLLER)
    body = text.split("function finishActiveFeedback")[1].split("function ")[0]
    assert "onSeaTurtleInteractionComplete(session)" in body
    assert "result.complete === true" in body


def test_controller_terminal_branch_does_not_call_feedback_complete() -> None:
    text = _read(CONTROLLER)
    body = text.split("function finishActiveFeedback")[1].split("function ")[0]
    # The terminal branch must not call the general feedback callback
    # Find the terminal branch section
    terminal_section = body.split("result.complete === true")[1].split(
        "result.complete === false"
    )[0]
    assert "onSeaTurtleFeedbackComplete(" not in terminal_section


def test_controller_non_terminal_branch_keeps_feedback_complete() -> None:
    text = _read(CONTROLLER)
    body = text.split("function finishActiveFeedback")[1].split("function ")[0]
    non_terminal = (
        body.split("result.complete === false")[1]
        if "result.complete === false" in body
        else ""
    )
    assert "onSeaTurtleFeedbackComplete(sequence, result)" in non_terminal


def test_app_js_implements_on_sea_turtle_interaction_complete() -> None:
    text = _read(APP)
    assert "function onSeaTurtleInteractionComplete(" in text


def test_app_js_exposes_interaction_complete_in_app_object() -> None:
    text = _read(APP)
    assert "onSeaTurtleInteractionComplete: onSeaTurtleInteractionComplete" in text


def test_canonical_feedback_callback_does_not_call_complete_success() -> None:
    text = _read(APP)
    body = text.split("function onSeaTurtleFeedbackComplete")[1].split("function ")[0]
    assert "completeSeaTurtleSuccess()" not in body


def test_controller_does_not_own_rescue_success_or_presentation() -> None:
    text = _read(CONTROLLER)
    # Controller must not directly call transition or presentation functions
    assert "State.Phases.RESCUE_SUCCESS" not in text
    assert "startMissionSuccessPresentation" not in text
    assert "beginTransition" not in text


def test_legacy_inline_fallback_terminal_completion_remains() -> None:
    text = _read(APP)
    legacy_body = text.split("function completeSeaTurtleFeedback")[1].split(
        "function "
    )[0]
    assert "result.complete" in legacy_body
    assert "completeSeaTurtleSuccess()" in legacy_body


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


def _trace_active_rope(page: Page) -> None:
    rope = page.evaluate(
        """() => {
        const s = window.OceanRescue.SeaTurtle.getSnapshot();
        const ropes = window.OceanRescue.SeaTurtle.Ropes;
        const active = ropes.find(r => r.id === s.activeRopeId);
        return { sx: active.start.x, sy: active.start.y, ex: active.end.x, ey: active.end.y };
    }"""
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
        "() => { const s = window.OceanRescue.SeaTurtle.getSnapshot(); return { feedback: s.feedback, activeRopeId: s.activeRopeId, active: s.active, complete: s.complete }; }"
    )


def _install_completion_counter(page: Page) -> None:
    page.evaluate(
        """() => {
        window.__completionCalls = 0;
        window.__completionSession = null;
        const original = window.OceanRescue.App.onSeaTurtleInteractionComplete;
        window.OceanRescue.App.onSeaTurtleInteractionComplete = function(session) {
            window.__completionCalls += 1;
            window.__completionSession = session;
            return original.call(window.OceanRescue.App, session);
        };
    }"""
    )


def _get_completion_count(page: Page) -> int:
    return page.evaluate("() => window.__completionCalls")


def _get_completion_session(page: Page) -> dict:
    return page.evaluate("() => window.__completionSession")


@pytest.mark.ocean_rescue
class TestOceanRescueSeaTurtleCompletionHandoff:
    def test_real_three_rope_session_completes_exactly_once(self) -> None:
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
                    _start_session(page, seq_id=9001)
                    _install_completion_counter(page)

                    # Rope 1
                    _trace_active_rope(page)
                    assert _snapshot(page)["feedback"] == "success"
                    page.evaluate(
                        "() => window.OceanRescue.App.__testFlushSeaTurtleFeedback()"
                    )
                    assert _snapshot(page)["feedback"] is None
                    assert _get_completion_count(page) == 0

                    # Rope 2
                    _trace_active_rope(page)
                    assert _snapshot(page)["feedback"] == "success"
                    page.evaluate(
                        "() => window.OceanRescue.App.__testFlushSeaTurtleFeedback()"
                    )
                    assert _snapshot(page)["feedback"] is None
                    assert _get_completion_count(page) == 0

                    # Rope 3 (terminal)
                    _trace_active_rope(page)
                    assert _snapshot(page)["feedback"] == "success"
                    page.evaluate(
                        "() => window.OceanRescue.App.__testFlushSeaTurtleFeedback()"
                    )

                    # Exactly-once completion handoff
                    assert _get_completion_count(page) == 1
                    session = _get_completion_session(page)
                    assert session["missionId"] == "sea-turtle"
                    assert session["rescueSequenceId"] == 9001

                    # State phase is RESCUE_SUCCESS
                    phase = page.evaluate(
                        "() => window.OceanRescue.State.getSnapshot().phase"
                    )
                    assert phase == "RESCUE_SUCCESS"

                    # Root rescue phase marker reflects success
                    root_phase = page.evaluate(
                        "() => document.getElementById('ocean-rescue-root').getAttribute('data-rescue-phase')"
                    )
                    assert root_phase is not None and root_phase.startswith("success")

                    # Re-flushing does not trigger another completion
                    page.evaluate(
                        "() => window.OceanRescue.App.__testFlushSeaTurtleFeedback()"
                    )
                    assert _get_completion_count(page) == 1

                    # No page errors
                    assert page.evaluate("() => window.__pageErrors || []") == []
                finally:
                    browser.close()

    def test_premature_callback_does_not_trigger_success(self) -> None:
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
                    _start_session(page, seq_id=9002)
                    _install_completion_counter(page)

                    # Complete rope 1 only
                    _trace_active_rope(page)
                    page.evaluate(
                        "() => window.OceanRescue.App.__testFlushSeaTurtleFeedback()"
                    )

                    # Directly invoke completion callback with session that is not complete
                    page.evaluate(
                        """() => {
                        const session = window.OceanRescue.App.getActiveSeaTurtleSession();
                        window.OceanRescue.App.onSeaTurtleInteractionComplete(session);
                    }"""
                    )

                    # Should NOT trigger success
                    phase = page.evaluate(
                        "() => window.OceanRescue.State.getSnapshot().phase"
                    )
                    assert phase != "RESCUE_SUCCESS"
                    assert _snapshot(page)["complete"] is False
                finally:
                    browser.close()

    def test_stale_sequence_callback_does_not_trigger_success(self) -> None:
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
                    _start_session(page, seq_id=9003)
                    _install_completion_counter(page)

                    # Invoke completion with stale sequence ID
                    page.evaluate(
                        """() => {
                        window.OceanRescue.App.onSeaTurtleInteractionComplete({
                            missionId: 'sea-turtle',
                            rescueSequenceId: 99999,
                        });
                    }"""
                    )

                    phase = page.evaluate(
                        "() => window.OceanRescue.State.getSnapshot().phase"
                    )
                    assert phase != "RESCUE_SUCCESS"
                finally:
                    browser.close()

    def test_wrong_mission_callback_does_not_trigger_success(self) -> None:
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
                    _start_session(page, seq_id=9004)
                    _install_completion_counter(page)

                    # Invoke completion with wrong mission but same sequence ID
                    page.evaluate(
                        """() => {
                        const seq = window.OceanRescue.App.getActiveRescueSequence();
                        window.OceanRescue.App.onSeaTurtleInteractionComplete({
                            missionId: 'crab',
                            rescueSequenceId: seq.sequenceId,
                        });
                    }"""
                    )

                    phase = page.evaluate(
                        "() => window.OceanRescue.State.getSnapshot().phase"
                    )
                    assert phase != "RESCUE_SUCCESS"
                finally:
                    browser.close()

    def test_duplicate_callback_does_not_trigger_success_twice(self) -> None:
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
                    _start_session(page, seq_id=9005)

                    # Track actual success effects via mission-success sequence counter
                    page.evaluate(
                        """() => {
                        window.__successTransitions = 0;
                        const original = window.OceanRescue.App.onSeaTurtleInteractionComplete;
                        window.OceanRescue.App.onSeaTurtleInteractionComplete = function(session) {
                            const before = window.OceanRescue.State.getSnapshot().phase;
                            const result = original.call(window.OceanRescue.App, session);
                            const after = window.OceanRescue.State.getSnapshot().phase;
                            if (before !== after) {
                                window.__successTransitions += 1;
                            }
                            return result;
                        };
                    }"""
                    )

                    # Complete all 3 ropes
                    _trace_active_rope(page)
                    page.evaluate(
                        "() => window.OceanRescue.App.__testFlushSeaTurtleFeedback()"
                    )
                    _trace_active_rope(page)
                    page.evaluate(
                        "() => window.OceanRescue.App.__testFlushSeaTurtleFeedback()"
                    )
                    _trace_active_rope(page)
                    page.evaluate(
                        "() => window.OceanRescue.App.__testFlushSeaTurtleFeedback()"
                    )

                    phase = page.evaluate(
                        "() => window.OceanRescue.State.getSnapshot().phase"
                    )
                    assert phase == "RESCUE_SUCCESS"
                    assert page.evaluate("() => window.__successTransitions") == 1

                    # Now invoke duplicate callback with same session
                    page.evaluate(
                        """() => {
                        const session = { missionId: 'sea-turtle', rescueSequenceId: 9005 };
                        window.OceanRescue.App.onSeaTurtleInteractionComplete(session);
                    }"""
                    )

                    # Should still be exactly 1 transition (duplicate rejected)
                    assert page.evaluate("() => window.__successTransitions") == 1
                finally:
                    browser.close()
