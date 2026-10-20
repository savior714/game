"""Real-browser regression for rescue-screen input recovery (Ocean Rescue).

Each test pins one input or recovery defect that was reproduced against the
tracked production artifact ``ocean-rescue/index.html``:

- capture loss mid-drag: a tracked pointer that loses capture without its
  pointerup reaching the canvas kept the mission pointer forever. The next drag
  was rejected and the stale gesture was scored as a failed rope.
- release outside the canvas: the gesture must end, not linger.
- bridge failure: when the lifecycle bridge refused to start, the controls showed
  "ready" with input enabled while every drag was ignored. The failure must be
  reported and recoverable by a tap.
- scene-failure recovery: the documented tap-to-menu recovery never ran in the
  active phase, and the legacy exit path returned early unless paused.
- stale scene-failure markers: a failed rescue must not leave a flag that makes
  the next rescue exit on the first tap.

The remaining cases pin behaviour that already works and that the fix must keep
working: three failed ropes, resize mid-rescue, a second touch, taps during the
site transition, pause mid-drag, replay after success, and crab pointer cancel.

Input is generated as real browser pointer events (mouse via Playwright, touch
via CDP). The only script hooks are the public state readers and, for the
bridge-failure case, a single temporary wrapper around the public
``OceanRescue.App.startSeaTurtleSession`` bridge.
"""

from __future__ import annotations

from pathlib import Path
import sys
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

SEA_TURTLE_TIMEOUT_S = 150


# --------------------------------------------------------------------------- #
# Shared harness (same contract as the WP-02 / young-whale browser suites)
# --------------------------------------------------------------------------- #


def _boot(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/ocean-rescue/index.html")
    page.wait_for_selector(
        "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=30000
    )


def _start_mission(page: Page, mission_id: str) -> None:
    page.click(f"#ocean-rescue-mission-list [data-mission-id={mission_id}]")
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


def _enter_active_sea_turtle(page: Page, base_url: str) -> None:
    _boot(page, base_url)
    _start_mission(page, "sea-turtle")
    _advance_travel_to_arrival(page)
    _wait_for_phase(page, "RESCUE_TUTORIAL")
    rect = _canvas_rect(page)
    cx, cy = _to_client(rect, LOGICAL_WIDTH / 2, LOGICAL_HEIGHT / 2)
    page.mouse.click(cx, cy)
    _wait_for_phase(page, "RESCUE_ACTIVE")


def _ropes(page: Page) -> list[dict[str, dict[str, float]]]:
    return page.evaluate("() => OceanRescue.SeaTurtle.Ropes")


def _drag_rope(page: Page, rope: dict[str, dict[str, float]]) -> None:
    rect = _canvas_rect(page)
    sx, sy = _to_client(rect, rope["start"]["x"], rope["start"]["y"])
    ex, ey = _to_client(rect, rope["end"]["x"], rope["end"]["y"])
    page.mouse.move(sx, sy)
    page.mouse.down()
    page.mouse.move(ex, ey, steps=12)
    page.mouse.up()


def _wait_for_completed_ropes(page: Page, count: int) -> None:
    page.wait_for_function(
        "expected => OceanRescue.SeaTurtle.getSnapshot().completedRopeIds.length === expected",
        arg=count,
        timeout=5000,
    )


def _wait_for_input_unlocked(page: Page) -> None:
    page.wait_for_function(
        "() => OceanRescue.SeaTurtle.getSnapshot().inputLocked === false",
        timeout=5000,
    )


def _sea_turtle_state(page: Page) -> dict:
    return page.evaluate(
        """() => {
          const s = OceanRescue.SeaTurtle.getSnapshot();
          return {
            phase: OceanRescue.State.getSnapshot().phase,
            completed: s.completedRopeIds.length,
            failures: s.failureCount,
            pointerActive: s.pointerActive,
            tracked: OceanRescue.App.hasTrackedSeaTurtlePointer(),
            input: document.getElementById('ocean-rescue-root').getAttribute('data-rescue-input'),
          };
        }"""
    )


def _assert_clean_pointer(page: Page) -> None:
    state = _sea_turtle_state(page)
    assert state["pointerActive"] is False, state
    assert state["tracked"] is False, state


class _Session:
    def __init__(
        self,
        base_url: str,
        viewport: tuple[int, int] = (1280, 720),
        has_touch: bool = False,
    ) -> None:
        self.base_url = base_url
        self.viewport = viewport
        self.has_touch = has_touch
        self.page_errors: list[str] = []
        self.external_requests: list[str] = []
        self._pw = None
        self._browser = None
        self.page: Page | None = None

    def __enter__(self) -> "_Session":
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            headless=True,
            args=["--disable-background-networking", "--disable-component-update"],
        )
        context = self._browser.new_context(
            viewport={"width": self.viewport[0], "height": self.viewport[1]},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            has_touch=self.has_touch,
        )
        context.add_init_script(_STATE_SEED_INIT_SCRIPT)
        page = context.new_page()
        page.on("pageerror", lambda error: self.page_errors.append(str(error)))
        origin = urlsplit(self.base_url).netloc

        def on_request(request: object) -> None:
            url = request.url  # type: ignore[attr-defined]
            if urlsplit(url).netloc not in {"", origin}:
                self.external_requests.append(url)

        page.on("request", on_request)
        self.page = page
        return self

    def __exit__(self, *exc: object) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._pw is not None:
            self._pw.stop()

    def assert_no_errors(self) -> None:
        assert self.page_errors == [], f"page errors: {self.page_errors}"
        assert self.external_requests == [], (
            f"unexpected external requests: {self.external_requests}"
        )


@pytest.fixture(scope="module")
def server() -> str:
    fixture = HTTPServerFixture()
    base_url = fixture.start()
    yield base_url
    fixture.stop()


# --------------------------------------------------------------------------- #
# Capture loss and gesture ownership
# --------------------------------------------------------------------------- #


@pytest.mark.timeout(SEA_TURTLE_TIMEOUT_S)
def test_capture_loss_mid_drag_does_not_strand_the_next_drag(server: str) -> None:
    with _Session(server) as session:
        page = session.page
        assert page is not None
        _enter_active_sea_turtle(page, server)
        rope = _ropes(page)[0]
        rect = _canvas_rect(page)
        sx, sy = _to_client(rect, rope["start"]["x"], rope["start"]["y"])
        page.mouse.move(sx, sy)
        page.mouse.down()
        page.mouse.move(sx + 40, sy + 10, steps=5)
        # The browser drops capture while the pointer is still down, and the
        # release lands on an element the canvas does not own.
        page.evaluate(
            "() => document.getElementById('ocean-rescue-canvas').releasePointerCapture(1)"
        )
        page.evaluate(
            "() => { document.getElementById('ocean-rescue-canvas').style.display = 'none'; }"
        )
        page.mouse.up()
        page.evaluate(
            "() => { document.getElementById('ocean-rescue-canvas').style.display = ''; }"
        )
        page.wait_for_timeout(300)
        state = _sea_turtle_state(page)
        assert state["pointerActive"] is False, state
        assert state["tracked"] is False, state
        assert state["failures"] == 0, (
            "the abandoned gesture must not be scored as a rope failure"
        )

        _wait_for_input_unlocked(page)
        _drag_rope(page, rope)
        _wait_for_completed_ropes(page, 1)
        session.assert_no_errors()


@pytest.mark.timeout(SEA_TURTLE_TIMEOUT_S)
def test_release_outside_canvas_ends_the_gesture(server: str) -> None:
    # Letterboxed viewport: the 16:9 canvas leaves bands above and below it.
    with _Session(server, viewport=(1000, 800)) as session:
        page = session.page
        assert page is not None
        _enter_active_sea_turtle(page, server)
        rope = _ropes(page)[0]
        rect = _canvas_rect(page)
        sx, sy = _to_client(rect, rope["start"]["x"], rope["start"]["y"])
        ex, ey = _to_client(rect, rope["end"]["x"], rope["end"]["y"] - 40)
        page.mouse.move(sx, sy)
        page.mouse.down()
        page.mouse.move(ex, ey, steps=12)
        # Release above the canvas, in the letterbox band.
        ox, oy = _to_client(rect, rope["end"]["x"], -200)
        page.mouse.move(ox, oy, steps=6)
        page.mouse.up()
        page.wait_for_timeout(300)
        _assert_clean_pointer(page)

        _wait_for_input_unlocked(page)
        _drag_rope(page, rope)
        _wait_for_completed_ropes(page, 1)
        session.assert_no_errors()


@pytest.mark.timeout(SEA_TURTLE_TIMEOUT_S)
def test_second_touch_does_not_steal_the_gesture(server: str) -> None:
    with _Session(server, has_touch=True) as session:
        page = session.page
        assert page is not None
        _enter_active_sea_turtle(page, server)
        rope = _ropes(page)[0]
        rect = _canvas_rect(page)
        cdp = session.page.context.new_cdp_session(page)  # type: ignore[union-attr]
        sx, sy = _to_client(rect, rope["start"]["x"], rope["start"]["y"])
        ex, ey = _to_client(rect, rope["end"]["x"], rope["end"]["y"])
        ox, oy = _to_client(rect, 1100, 150)

        def touches(points: list[tuple[float, float]]) -> list[dict]:
            return [{"x": x, "y": y, "id": i} for i, (x, y) in enumerate(points)]

        cdp.send(
            "Input.dispatchTouchEvent",
            {"type": "touchStart", "touchPoints": touches([(sx, sy)])},
        )
        cdp.send(
            "Input.dispatchTouchEvent",
            {"type": "touchStart", "touchPoints": touches([(sx, sy), (ox, oy)])},
        )
        steps = 12
        for k in range(1, steps + 1):
            x = sx + (ex - sx) * k / steps
            y = sy + (ey - sy) * k / steps
            cdp.send(
                "Input.dispatchTouchEvent",
                {"type": "touchMove", "touchPoints": touches([(x, y), (ox + k, oy)])},
            )
        cdp.send(
            "Input.dispatchTouchEvent",
            {"type": "touchEnd", "touchPoints": touches([(ex, ey)])},
        )
        page.wait_for_timeout(150)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        _wait_for_completed_ropes(page, 1)
        state = _sea_turtle_state(page)
        assert state["failures"] == 0, state
        _assert_clean_pointer(page)
        session.assert_no_errors()


# --------------------------------------------------------------------------- #
# Failure path, resize, transition taps
# --------------------------------------------------------------------------- #


@pytest.mark.timeout(SEA_TURTLE_TIMEOUT_S)
def test_three_failed_ropes_keep_input_live_and_the_next_rope_completes(
    server: str,
) -> None:
    with _Session(server) as session:
        page = session.page
        assert page is not None
        _enter_active_sea_turtle(page, server)
        rope = _ropes(page)[0]
        rect = _canvas_rect(page)
        for _ in range(3):
            sx, sy = _to_client(rect, rope["start"]["x"], rope["start"]["y"])
            page.mouse.move(sx, sy)
            page.mouse.down()
            page.mouse.move(sx + 5, sy + 5, steps=2)
            page.mouse.move(*_to_client(rect, 40, 40), steps=8)
            page.mouse.up()
            _wait_for_input_unlocked(page)
        state = _sea_turtle_state(page)
        assert state["failures"] == 3, state
        assert state["input"] == "enabled", state
        _drag_rope(page, rope)
        _wait_for_completed_ropes(page, 1)
        session.assert_no_errors()


@pytest.mark.timeout(SEA_TURTLE_TIMEOUT_S)
def test_resize_mid_rescue_keeps_input_mapped(server: str) -> None:
    with _Session(server) as session:
        page = session.page
        assert page is not None
        _enter_active_sea_turtle(page, server)
        page.set_viewport_size({"width": 900, "height": 700})
        page.wait_for_timeout(400)
        _drag_rope(page, _ropes(page)[0])
        _wait_for_completed_ropes(page, 1)
        session.assert_no_errors()


@pytest.mark.timeout(SEA_TURTLE_TIMEOUT_S)
def test_taps_during_the_site_transition_are_ignored(server: str) -> None:
    with _Session(server) as session:
        page = session.page
        assert page is not None
        _boot(page, server)
        _start_mission(page, "sea-turtle")
        _advance_travel_to_arrival(page)
        _wait_for_phase(page, "RESCUE_SITE_TRANSITION")
        rect = _canvas_rect(page)
        cx, cy = _to_client(rect, LOGICAL_WIDTH / 2, LOGICAL_HEIGHT / 2)
        page.mouse.click(cx, cy)
        page.mouse.click(cx, cy)
        assert _sea_turtle_state(page)["phase"] == "RESCUE_SITE_TRANSITION"
        _wait_for_phase(page, "RESCUE_TUTORIAL")
        page.mouse.click(cx, cy)
        _wait_for_phase(page, "RESCUE_ACTIVE")
        _drag_rope(page, _ropes(page)[0])
        _wait_for_completed_ropes(page, 1)
        session.assert_no_errors()


# --------------------------------------------------------------------------- #
# Recovery paths
# --------------------------------------------------------------------------- #


@pytest.mark.timeout(SEA_TURTLE_TIMEOUT_S)
def test_bridge_failure_is_reported_and_a_tap_returns_to_the_menu(server: str) -> None:
    with _Session(server) as session:
        page = session.page
        assert page is not None
        _boot(page, server)
        # Make the lifecycle bridge refuse to start the sea-turtle session once.
        page.evaluate(
            """() => {
              const App = OceanRescue.App;
              window.__origStart = App.startSeaTurtleSession;
              App.startSeaTurtleSession = () => { throw new Error('bridge refused'); };
            }"""
        )
        _start_mission(page, "sea-turtle")
        _advance_travel_to_arrival(page)
        _wait_for_phase(page, "RESCUE_TUTORIAL")
        rect = _canvas_rect(page)
        cx, cy = _to_client(rect, LOGICAL_WIDTH / 2, LOGICAL_HEIGHT / 2)
        page.mouse.click(cx, cy)
        page.wait_for_function(
            "() => document.getElementById('ocean-rescue-root').getAttribute('data-rescue-scene-failure') === 'true'",
            timeout=8000,
        )
        root = page.evaluate(
            """() => ({
              input: document.getElementById('ocean-rescue-root').getAttribute('data-rescue-input'),
              status: document.getElementById('ocean-rescue-status').textContent,
            })"""
        )
        assert root["input"] == "disabled", root
        assert "could not start" in root["status"], root

        page.mouse.click(cx, cy)
        _wait_for_phase(page, "MISSION_SELECT")
        leftover = page.evaluate(
            """() => ({
              failure: document.getElementById('ocean-rescue-root').getAttribute('data-rescue-scene-failure'),
              seaFailure: document.getElementById('ocean-rescue-root').getAttribute('data-sea-turtle-scene-failure'),
            })"""
        )
        assert leftover == {"failure": None, "seaFailure": None}, leftover

        # Restore the bridge and prove the next rescue runs normally, which also
        # shows the failure markers did not leak into it.
        page.evaluate(
            "() => { OceanRescue.App.startSeaTurtleSession = window.__origStart; }"
        )
        _start_mission(page, "sea-turtle")
        _advance_travel_to_arrival(page)
        _wait_for_phase(page, "RESCUE_TUTORIAL")
        page.mouse.click(cx, cy)
        _wait_for_phase(page, "RESCUE_ACTIVE")
        _drag_rope(page, _ropes(page)[0])
        _wait_for_completed_ropes(page, 1)
        session.assert_no_errors()


@pytest.mark.timeout(SEA_TURTLE_TIMEOUT_S)
def test_pause_mid_drag_then_resume_accepts_a_fresh_drag(server: str) -> None:
    with _Session(server) as session:
        page = session.page
        assert page is not None
        _enter_active_sea_turtle(page, server)
        rope = _ropes(page)[0]
        rect = _canvas_rect(page)
        sx, sy = _to_client(rect, rope["start"]["x"], rope["start"]["y"])
        page.mouse.move(sx, sy)
        page.mouse.down()
        page.mouse.move(sx + 30, sy + 8, steps=4)
        # DOM click: a real mouse click would fight the button still held down.
        page.evaluate(
            "() => document.getElementById('ocean-rescue-pause-button').click()"
        )
        page.wait_for_function(
            "() => document.getElementById('ocean-rescue-pause-overlay').hidden === false",
            timeout=5000,
        )
        page.mouse.up()
        page.evaluate(
            "() => document.getElementById('ocean-rescue-pause-resume').click()"
        )
        page.wait_for_function(
            "() => OceanRescue.App.isPauseActive() === false",
            timeout=10000,
        )
        _assert_clean_pointer(page)
        _wait_for_input_unlocked(page)
        _drag_rope(page, rope)
        _wait_for_completed_ropes(page, 1)
        session.assert_no_errors()


@pytest.mark.timeout(SEA_TURTLE_TIMEOUT_S)
def test_replay_after_success_reenables_rope_input(server: str) -> None:
    with _Session(server) as session:
        page = session.page
        assert page is not None
        _enter_active_sea_turtle(page, server)
        ropes = _ropes(page)
        for index, rope in enumerate(ropes):
            if index > 0:
                _wait_for_input_unlocked(page)
            _drag_rope(page, rope)
            _wait_for_completed_ropes(page, index + 1)
        _wait_for_phase(page, "RESCUE_SUCCESS")
        page.wait_for_selector(
            "#ocean-rescue-mission-complete-replay:not([disabled])", timeout=20000
        )
        page.click("#ocean-rescue-mission-complete-replay")
        page.wait_for_selector("#ocean-rescue-launch:not([hidden])", timeout=15000)
        page.click("#ocean-rescue-launch-skip")
        page.wait_for_selector("#ocean-rescue-root[data-travel-runtime=active]")
        assert (
            page.evaluate(
                "() => document.getElementById('ocean-rescue-root').hasAttribute('data-rescue-sequence')"
            )
            is False
        ), "replay must clear the previous rescue sequence marker"
        _advance_travel_to_arrival(page)
        # On replay the travel loop waits for the net inspection before the
        # rescue starts. The player presses the button once it appears.
        page.wait_for_selector("#ocean-rescue-travel-scan:not([hidden])", timeout=20000)
        page.click("#ocean-rescue-travel-scan")
        _wait_for_phase(page, "RESCUE_TUTORIAL", timeout=40000)
        rect = _canvas_rect(page)
        cx, cy = _to_client(rect, LOGICAL_WIDTH / 2, LOGICAL_HEIGHT / 2)
        page.mouse.click(cx, cy)
        _wait_for_phase(page, "RESCUE_ACTIVE")
        assert _sea_turtle_state(page)["completed"] == 0
        _drag_rope(page, _ropes(page)[0])
        _wait_for_completed_ropes(page, 1)
        session.assert_no_errors()


# --------------------------------------------------------------------------- #
# Crab: the hold timer and grab must end with the pointer
# --------------------------------------------------------------------------- #


def _crab_state(page: Page) -> dict:
    return page.evaluate(
        """() => {
          const s = OceanRescue.Crab.getSnapshot();
          return { phase: OceanRescue.State.getSnapshot().phase, pointerActive: s.pointerActive,
                   holding: s.holding, grabbed: s.grabbed, rock: s.currentRockCenter };
        }"""
    )


def _enter_active_crab(page: Page, base_url: str) -> None:
    _boot(page, base_url)
    _start_mission(page, "crab")
    _advance_travel_to_arrival(page)
    _wait_for_phase(page, "RESCUE_TUTORIAL")
    rect = _canvas_rect(page)
    cx, cy = _to_client(rect, LOGICAL_WIDTH / 2, LOGICAL_HEIGHT / 2)
    page.mouse.click(cx, cy)
    _wait_for_phase(page, "RESCUE_ACTIVE")
    page.wait_for_function(
        "() => OceanRescue.Crab.getSnapshot().currentRockCenter !== null",
        timeout=8000,
    )


@pytest.mark.timeout(SEA_TURTLE_TIMEOUT_S)
def test_crab_pointer_cancel_drops_the_hold_and_the_grab(server: str) -> None:
    with _Session(server) as session:
        page = session.page
        assert page is not None
        _enter_active_crab(page, server)
        rock = page.evaluate("() => OceanRescue.Crab.getSnapshot().currentRockCenter")
        rect = _canvas_rect(page)
        sx, sy = _to_client(rect, rock["x"], rock["y"])
        page.mouse.move(sx, sy)
        page.mouse.down()
        page.mouse.move(sx + 4, sy + 4, steps=2)
        page.evaluate(
            """() => {
              const c = document.getElementById('ocean-rescue-canvas');
              c.dispatchEvent(new PointerEvent('pointercancel', { pointerId: 1, bubbles: true, isPrimary: true }));
            }"""
        )
        # The hold timer is 400 ms; wait well past it.
        page.wait_for_timeout(900)
        state = _crab_state(page)
        assert state["pointerActive"] is False, state
        assert state["holding"] is False, state
        assert state["grabbed"] is False, state
        page.mouse.up()
        session.assert_no_errors()


@pytest.mark.timeout(SEA_TURTLE_TIMEOUT_S)
def test_crab_capture_loss_releases_the_grab(server: str) -> None:
    with _Session(server) as session:
        page = session.page
        assert page is not None
        _enter_active_crab(page, server)
        rock = page.evaluate("() => OceanRescue.Crab.getSnapshot().currentRockCenter")
        rect = _canvas_rect(page)
        sx, sy = _to_client(rect, rock["x"], rock["y"])
        page.mouse.move(sx, sy)
        page.mouse.down()
        page.mouse.move(sx + 5, sy + 5, steps=3)
        page.evaluate(
            "() => document.getElementById('ocean-rescue-canvas').releasePointerCapture(1)"
        )
        page.evaluate(
            "() => { document.getElementById('ocean-rescue-canvas').style.display = 'none'; }"
        )
        page.mouse.up()
        page.evaluate(
            "() => { document.getElementById('ocean-rescue-canvas').style.display = ''; }"
        )
        page.wait_for_timeout(400)
        state = _crab_state(page)
        assert state["pointerActive"] is False, state
        assert state["grabbed"] is False, state
        session.assert_no_errors()
