"""Browser regression: leaving a rescue through pause -> menu must not break the next rescue.

Two defects were reproduced in real Chromium against the tracked production
artifact ``ocean-rescue/index.html`` and are pinned here:

1. Stale rescue sequence. The canonical ESM pause controller left the previous
   rescue sequence active after pause -> menu from the site-transition, tutorial
   or active stage. The next travel arrival was then silently blocked by
   ``handoffTravelArrival`` (``getActiveRescueSequence() !== null``), so the ship
   reached the destination and the rescue screen never opened.

2. Self-recursive host bridge. ``controller`` and ``host`` are the same object,
   so re-assigning ``cancelMissionSuccessPresentationForMenu`` as a wrapper made
   it call itself. Pause -> menu from the mission-success screen then threw
   ``Maximum call stack size exceeded`` and never left RESCUE_SUCCESS.

Input is driven with browser-generated mouse events (no direct handler calls).
Travel is advanced through the public ``Travel.step`` API, as in the Young Whale
browser session. No new browser framework or npm dependency is added.
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import Page, sync_playwright

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
from test_ocean_rescue_wp02_browser_baseline import (  # noqa: E402
    HTTPServerFixture,
)

LOGICAL_WIDTH = 1280
LOGICAL_HEIGHT = 720
PROFILE_KEY = "aidengame.oceanRescue.profile"
PROGRESSION_KEY = "aidengame.oceanRescue.progression"

# Official persisted contracts only: the profile is chosen and sea-turtle is
# unlocked so the mission can be started through the real mission list.
_STATE_SEED_INIT_SCRIPT = (
    "window.localStorage.clear();"
    "window.localStorage.setItem("
    f"'{PROFILE_KEY}', "
    "JSON.stringify({ schemaVersion: 1, playerName: 'Aiden', animalId: 'arctic-fox' })"
    ");"
    "window.localStorage.setItem("
    f"'{PROGRESSION_KEY}', "
    "JSON.stringify({ schemaVersion: 1, completedMissionIds: ['sea-turtle', 'crab'], newMissionIds: [] })"
    ");"
)

_REENTRY_STAGES = ("RESCUE_SITE_TRANSITION", "RESCUE_TUTORIAL", "RESCUE_ACTIVE")


def _boot(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/ocean-rescue/index.html")
    page.wait_for_selector(
        "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=30000
    )


def _start_sea_turtle(page: Page) -> None:
    page.click("#ocean-rescue-mission-list [data-mission-id=sea-turtle]")
    page.wait_for_selector("#ocean-rescue-gup-select:not([hidden])")
    page.click("#ocean-rescue-gup-list [data-gup-id=gup-x]")
    page.click("#ocean-rescue-gup-launch")
    page.wait_for_selector("#ocean-rescue-launch:not([hidden])")
    page.click("#ocean-rescue-launch-skip")
    page.wait_for_selector("#ocean-rescue-root[data-travel-runtime=active]")


def _advance_travel_to_arrival(page: Page) -> None:
    page.evaluate(
        """() => {
          const T = OceanRescue.Travel;
          let calls = 0;
          while (T.getSnapshot().distance < OceanRescue.Rescue.ArrivalDistance && calls < 3000) {
            if (!T.step(50, 1)) throw new Error('public Travel.step rejected step');
            calls += 1;
          }
          return calls;
        }"""
    )


def _wait_for_phase(page: Page, phase: str, timeout: int = 8000) -> None:
    page.wait_for_function(
        "expected => OceanRescue.State.getSnapshot().phase === expected",
        arg=phase,
        timeout=timeout,
    )


def _active_sequence_id(page: Page) -> int | None:
    return page.evaluate(
        "() => OceanRescue.App.getActiveRescueSequence()?.sequenceId ?? null"
    )


def _pause_to_menu(page: Page) -> None:
    page.click("#ocean-rescue-pause-button")
    page.wait_for_function(
        "() => document.getElementById('ocean-rescue-pause-overlay').hidden === false"
    )
    page.click("#ocean-rescue-pause-menu-button")
    _wait_for_phase(page, "MISSION_SELECT")


def _canvas_rect(page: Page) -> dict[str, float]:
    return page.evaluate(
        """() => {
          const r = document.getElementById('ocean-rescue-canvas').getBoundingClientRect();
          return { left: r.left, top: r.top, w: r.width, h: r.height };
        }"""
    )


def _to_client(rect: dict[str, float], x: float, y: float) -> tuple[float, float]:
    return (
        rect["left"] + x / LOGICAL_WIDTH * rect["w"],
        rect["top"] + y / LOGICAL_HEIGHT * rect["h"],
    )


def _drag_rope(page: Page, rope: dict[str, dict[str, float]]) -> None:
    rect = _canvas_rect(page)
    sx, sy = _to_client(rect, rope["start"]["x"], rope["start"]["y"])
    ex, ey = _to_client(rect, rope["end"]["x"], rope["end"]["y"])
    page.mouse.move(sx, sy)
    page.mouse.down()
    page.mouse.move(ex, ey, steps=12)
    page.mouse.up()


def _sea_turtle_ropes(page: Page) -> list[dict[str, dict[str, float]]]:
    return page.evaluate("() => OceanRescue.SeaTurtle.Ropes")


def _wait_for_completed_ropes(page: Page, count: int) -> None:
    page.wait_for_function(
        """expected => OceanRescue.SeaTurtle.getSnapshot().completedRopeIds.length === expected""",
        arg=count,
        timeout=5000,
    )


def _wait_for_input_unlocked(page: Page) -> None:
    # Input stays locked for the success/failure feedback window of the last
    # rope; the feedback timer releases it before the next rope can be dragged.
    page.wait_for_function(
        "() => OceanRescue.SeaTurtle.getSnapshot().inputLocked === false",
        timeout=5000,
    )


@pytest.mark.parametrize("stage", _REENTRY_STAGES)
def test_pause_menu_from_rescue_stage_does_not_block_next_arrival(stage: str) -> None:
    server = HTTPServerFixture()
    base_url = server.start()
    page_errors: list[str] = []
    external_requests: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--disable-background-networking", "--disable-component-update"],
            )
            try:
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    locale="ko-KR",
                    timezone_id="Asia/Seoul",
                )
                context.add_init_script(_STATE_SEED_INIT_SCRIPT)
                page = context.new_page()
                page.on("pageerror", lambda error: page_errors.append(str(error)))

                def on_request(request: object) -> None:
                    url = request.url  # type: ignore[attr-defined]
                    origin = urlsplit(base_url).netloc
                    if urlsplit(url).netloc not in {"", origin}:
                        external_requests.append(url)

                page.on("request", on_request)

                _boot(page, base_url)
                _start_sea_turtle(page)
                _advance_travel_to_arrival(page)
                _wait_for_phase(page, stage)
                first_sequence = _active_sequence_id(page)
                assert first_sequence is not None

                _pause_to_menu(page)
                assert _active_sequence_id(page) is None, (
                    f"rescue sequence must be cleared after pause -> menu from {stage}"
                )

                _start_sea_turtle(page)
                _advance_travel_to_arrival(page)
                page.wait_for_function(
                    """() => {
                      const p = OceanRescue.State.getSnapshot().phase;
                      return p === 'RESCUE_SITE_TRANSITION' || p === 'RESCUE_TUTORIAL';
                    }""",
                    timeout=8000,
                )
                second_sequence = _active_sequence_id(page)
                assert second_sequence is not None and second_sequence != first_sequence, (
                    "arrival after pause -> menu must hand off to a new rescue site"
                )

                _wait_for_phase(page, "RESCUE_TUTORIAL")
                rect = _canvas_rect(page)
                cx, cy = _to_client(rect, LOGICAL_WIDTH / 2, LOGICAL_HEIGHT / 2)
                page.mouse.click(cx, cy)
                _wait_for_phase(page, "RESCUE_ACTIVE")

                ropes = _sea_turtle_ropes(page)
                _drag_rope(page, ropes[0])
                _wait_for_completed_ropes(page, 1)
            finally:
                browser.close()
    finally:
        server.stop()

    assert page_errors == [], f"page errors: {page_errors}"
    assert external_requests == [], f"unexpected external requests: {external_requests}"


def test_pause_menu_from_mission_success_returns_to_menu_without_recursion() -> None:
    server = HTTPServerFixture()
    base_url = server.start()
    page_errors: list[str] = []
    external_requests: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--disable-background-networking", "--disable-component-update"],
            )
            try:
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    locale="ko-KR",
                    timezone_id="Asia/Seoul",
                )
                context.add_init_script(_STATE_SEED_INIT_SCRIPT)
                page = context.new_page()
                page.on("pageerror", lambda error: page_errors.append(str(error)))

                def on_request(request: object) -> None:
                    url = request.url  # type: ignore[attr-defined]
                    origin = urlsplit(base_url).netloc
                    if urlsplit(url).netloc not in {"", origin}:
                        external_requests.append(url)

                page.on("request", on_request)

                _boot(page, base_url)
                _start_sea_turtle(page)
                _advance_travel_to_arrival(page)
                _wait_for_phase(page, "RESCUE_TUTORIAL")
                rect = _canvas_rect(page)
                cx, cy = _to_client(rect, LOGICAL_WIDTH / 2, LOGICAL_HEIGHT / 2)
                page.mouse.click(cx, cy)
                _wait_for_phase(page, "RESCUE_ACTIVE")

                ropes = _sea_turtle_ropes(page)
                for index, rope in enumerate(ropes):
                    if index > 0:
                        _wait_for_input_unlocked(page)
                    _drag_rope(page, rope)
                    _wait_for_completed_ropes(page, index + 1)
                _wait_for_phase(page, "RESCUE_SUCCESS")

                _pause_to_menu(page)
                assert (
                    page.evaluate(
                        "() => OceanRescue.App.isPauseActive() === false"
                    )
                    is True
                )
            finally:
                browser.close()
    finally:
        server.stop()

    assert page_errors == [], f"page errors: {page_errors}"
    assert external_requests == [], f"unexpected external requests: {external_requests}"
