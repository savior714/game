"""Prove the full Young Whale three-debris rescue session in a real browser.

The Young Whale gameplay logic and Canvas geometry are already covered by the
Node VM fake-DOM suite (``test_ocean_rescue_young_whale_interaction.py``), but
no committed Playwright test drives the three-debris session against the real
production artifact. This module closes that gap:

- serves the tracked ``ocean-rescue/index.html`` artifact over HTTP;
- seeds the persisted progression contract so Young Whale is unlocked
  (Sea Turtle and Crab completed) and the profile is already chosen;
- selects Young Whale and a GUP through the real UI;
- completes Travel deterministically through the public ``Travel.step`` API;
- skips the rescue-site tutorial through the real stage pointer contract;
- performs connection + towing for debris-1, debris-2, and debris-3 as real
  canvas PointerEvents converted from the public coordinate contracts
  (``OceanRescue.YoungWhale.Debris``, ``GupStart``, ``GupHook``);
- waits on DOM/state polling (never fixed sleeps) for each feedback window;
- reaches the Young Whale mission-success presentation, advances the
  narration through the real pointer contract, and verifies the progression
  is persisted;
- asserts clean page/console/network quality with no duplicate initialization.

Only the established browser helpers are reused: ``HTTPServerFixture``,
synthetic PointerEvent dispatch, the pointer-capture neutralization init
script, and the deterministic Travel stepping already used by the WP-02 and
WP-32B browser suites. No new browser framework or npm dependency is added.
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Page, sync_playwright

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
from test_ocean_rescue_wp02_browser_baseline import (  # noqa: E402
    HTTPServerFixture,
)

REPO_ROOT = TESTS_DIR.parent
LOGICAL_WIDTH = 1280
LOGICAL_HEIGHT = 720
MAPPING_TOLERANCE = 1.5
PROGRESSION_KEY = "aidengame.oceanRescue.progression"
PROFILE_KEY = "aidengame.oceanRescue.profile"

# Synthetic PointerEvent dispatch has no real active pointer; the app's
# setPointerCapture/releasePointerCapture calls must be neutralized so the
# pointer flow completes without uncaught DOM errors (same approach as WP-31C
# and WP-32B).
_POINTER_CAPTURE_INIT_SCRIPT = (
    "(() => {"
    "if (typeof Element !== 'undefined') {"
    "Element.prototype.setPointerCapture = function () {};"
    "Element.prototype.releasePointerCapture = function () {};"
    "}"
    "})();"
)

# Seed the persisted contracts so Young Whale is unlocked and no profile
# choice is needed. This is the official progression/profile storage contract,
# not an internal state override or a test-only production hook.
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

# Duplicate-initialization observers. app.js registers exactly one
# DOMContentLoaded listener, and the boot guard sets data-ocean-rescue-ready
# exactly once. Any duplicate bundle execution or double boot would raise the
# observed counts.
_DUPLICATE_INIT_OBSERVER_SCRIPT = (
    "(() => {"
    "window.__ywDomContentLoadedCount = 0;"
    "const origAdd = document.addEventListener.bind(document);"
    "document.addEventListener = function (type, fn) {"
    "if (type === 'DOMContentLoaded') window.__ywDomContentLoadedCount += 1;"
    "return origAdd(type, fn);"
    "};"
    "window.__ywReadyTransitions = 0;"
    "const rootObserver = new MutationObserver(() => {"
    "const root = document.getElementById('ocean-rescue-root');"
    "if (!root) return;"
    "rootObserver.disconnect();"
    "const readyObserver = new MutationObserver(() => {"
    "if (root.getAttribute('data-ocean-rescue-ready') === 'true') {"
    "window.__ywReadyTransitions += 1;"
    "}"
    "});"
    "readyObserver.observe(root, { attributes: true, attributeFilter: ['data-ocean-rescue-ready'] });"
    "});"
    "rootObserver.observe(document, { childList: true, subtree: true });"
    "})();"
)


def _client_point(
    page: Page, rect: dict[str, float], logical_x: float, logical_y: float
) -> tuple[float, float]:
    return (
        rect["left"] + logical_x / LOGICAL_WIDTH * rect["w"],
        rect["top"] + logical_y / LOGICAL_HEIGHT * rect["h"],
    )


def _canvas_rect(page: Page) -> dict[str, float]:
    return page.evaluate(
        """() => {
          const r = document.getElementById('ocean-rescue-canvas').getBoundingClientRect();
          return { left: r.left, top: r.top, w: r.width, h: r.height };
        }"""
    )


def _launch_young_whale_to_rescue_active(page: Page, base_url: str) -> None:
    """Drive the real UI from boot to RESCUE_ACTIVE with Young Whale active."""
    page.goto(f"{base_url}/ocean-rescue/index.html")
    page.wait_for_selector(
        "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=30000
    )
    profile_visible = page.evaluate(
        """() => {
          const el = document.getElementById('ocean-rescue-profile-choice');
          return !!el && !el.hidden && getComputedStyle(el).display !== 'none';
        }"""
    )
    assert profile_visible is False, "seeded profile must skip the profile choice"
    page.wait_for_selector("#ocean-rescue-mission-list [data-mission-id=young-whale]")
    young_whale_unlocked = page.evaluate(
        "() => OceanRescue.Missions.isUnlocked('young-whale')"
    )
    assert young_whale_unlocked is True, "young-whale must be unlocked by the seed"

    page.click("#ocean-rescue-mission-list [data-mission-id=young-whale]")
    page.wait_for_selector("#ocean-rescue-gup-select:not([hidden])")
    page.click("#ocean-rescue-gup-list [data-gup-id=gup-x]")
    page.click("#ocean-rescue-gup-launch")
    page.wait_for_selector("#ocean-rescue-launch:not([hidden])")
    page.click("#ocean-rescue-launch-skip")
    page.wait_for_selector("#ocean-rescue-root[data-travel-runtime=active]")

    travel_snapshot = page.evaluate("() => OceanRescue.Travel.getSnapshot()")
    assert travel_snapshot["active"] is True

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
    page.wait_for_function(
        """() => ['site-transition', 'tutorial', 'active'].includes(
          document.getElementById('ocean-rescue-root').getAttribute('data-rescue-phase'))""",
        timeout=5000,
    )
    page.wait_for_function(
        "() => document.getElementById('ocean-rescue-root').getAttribute('data-rescue-phase') === 'tutorial'",
        timeout=5000,
    )
    page.mouse.click(640, 360)
    page.wait_for_function(
        "() => document.getElementById('ocean-rescue-root').getAttribute('data-rescue-phase') === 'active'",
        timeout=5000,
    )
    assert (
        page.evaluate(
            "() => document.getElementById('ocean-rescue-root').getAttribute('data-young-whale-active')"
        )
        == "true"
    ), "young-whale interaction must be active at RESCUE_ACTIVE"


def _young_whale_contract(page: Page) -> dict[str, object]:
    return page.evaluate(
        """() => {
          const YW = OceanRescue.YoungWhale;
          return {
            gupStart: { x: YW.GupStart.x, y: YW.GupStart.y },
            gupHook: { x: YW.GupHook.x, y: YW.GupHook.y },
            debris: YW.Debris.map(d => ({
              id: d.id,
              order: d.order,
              connection: { x: d.connection.x, y: d.connection.y },
              safeSpot: { x: d.safeSpot.x, y: d.safeSpot.y }
            }))
          };
        }"""
    )


def _connection_points(
    debris: dict[str, object], hook: dict[str, float]
) -> list[tuple[float, float]]:
    start = debris["connection"]
    return [
        (start["x"], start["y"]),
        (
            start["x"] + (hook["x"] - start["x"]) * 0.3,
            start["y"] + (hook["y"] - start["y"]) * 0.3,
        ),
        (
            start["x"] + (hook["x"] - start["x"]) * 0.55,
            start["y"] + (hook["y"] - start["y"]) * 0.55,
        ),
        (
            start["x"] + (hook["x"] - start["x"]) * 0.8,
            start["y"] + (hook["y"] - start["y"]) * 0.8,
        ),
        (hook["x"], hook["y"]),
    ]


def _towing_points(
    gup_start: dict[str, float], debris: dict[str, object]
) -> list[tuple[float, float]]:
    safe_spot = debris["safeSpot"]
    return [
        (gup_start["x"], gup_start["y"]),
        (
            gup_start["x"] + (safe_spot["x"] - gup_start["x"]) * 0.25,
            gup_start["y"] + (safe_spot["y"] - gup_start["y"]) * 0.25,
        ),
        (
            gup_start["x"] + (safe_spot["x"] - gup_start["x"]) * 0.5,
            gup_start["y"] + (safe_spot["y"] - gup_start["y"]) * 0.5,
        ),
        (
            gup_start["x"] + (safe_spot["x"] - gup_start["x"]) * 0.75,
            gup_start["y"] + (safe_spot["y"] - gup_start["y"]) * 0.75,
        ),
        (safe_spot["x"], safe_spot["y"]),
    ]


def _dispatch_pointer_gesture(
    page: Page,
    rect: dict[str, float],
    pointer_id: int,
    logical_points: list[tuple[float, float]],
) -> None:
    client_points = [_client_point(page, rect, x, y) for (x, y) in logical_points]
    page.evaluate(
        """({ pointer_id, client_points }) => {
          const canvas = document.getElementById('ocean-rescue-canvas');
          const mk = (type, x, y) => new PointerEvent(type, {
            pointerId: pointer_id, clientX: x, clientY: y,
            isPrimary: true, button: 0, bubbles: true
          });
          canvas.dispatchEvent(mk('pointerdown', client_points[0][0], client_points[0][1]));
          for (let i = 1; i < client_points.length - 1; i += 1) {
            canvas.dispatchEvent(mk('pointermove', client_points[i][0], client_points[i][1]));
          }
          canvas.dispatchEvent(mk('pointerup', client_points[client_points.length - 1][0], client_points[client_points.length - 1][1]));
        }""",
        {"pointer_id": pointer_id, "client_points": client_points},
    )


def _wait_for_young_whale_idle(page: Page, expected_stage: str) -> None:
    page.wait_for_function(
        """expected => {
          const root = document.getElementById('ocean-rescue-root');
          return root.getAttribute('data-young-whale-feedback') === 'none'
            && root.getAttribute('data-young-whale-stage') === expected;
        }""",
        arg=expected_stage,
        timeout=5000,
    )


def _wait_for_young_whale_complete(page: Page) -> None:
    page.wait_for_function(
        "() => document.getElementById('ocean-rescue-root').getAttribute('data-young-whale-complete') === 'true'",
        timeout=5000,
    )


def _assert_pointer_clean(page: Page, pointer_id: int, debris_id: str) -> None:
    snapshot = page.evaluate("() => OceanRescue.YoungWhale.getSnapshot()")
    assert snapshot["pointerActive"] is False, (
        f"pointerActive must be false after {debris_id}, got {snapshot}"
    )
    assert snapshot["inputLocked"] is False, (
        f"inputLocked must be false after {debris_id}, got {snapshot}"
    )
    assert (
        page.evaluate(
            "pointerId => document.getElementById('ocean-rescue-canvas').hasPointerCapture(pointerId)",
            pointer_id,
        )
        is False
    ), f"canvas pointer capture must be released after {debris_id}"


def _run_full_session(page: Page, base_url: str) -> dict[str, object]:
    _launch_young_whale_to_rescue_active(page, base_url)

    contract = _young_whale_contract(page)
    debris_by_id = {d["id"]: d for d in contract["debris"]}
    hook = contract["gupHook"]
    gup_start = contract["gupStart"]
    rect = _canvas_rect(page)

    initial = page.evaluate("() => OceanRescue.YoungWhale.getSnapshot()")
    assert initial["active"] is True
    assert initial["activeDebrisId"] == "debris-1"
    assert initial["stage"] == "connection"
    assert initial["inputLocked"] is False
    assert initial["completedDebrisIds"] == []
    assert initial["feedback"] is None
    assert initial["complete"] is False

    pointer_id = 100

    # debris-1: connection then towing
    pointer_id += 1
    _dispatch_pointer_gesture(
        page,
        rect,
        pointer_id,
        _connection_points(debris_by_id["debris-1"], hook),
    )
    snap = page.evaluate("() => OceanRescue.YoungWhale.getSnapshot()")
    assert snap["feedback"] == "success", f"debris-1 connection: {snap}"
    _wait_for_young_whale_idle(page, "towing")
    snap = page.evaluate("() => OceanRescue.YoungWhale.getSnapshot()")
    assert snap["stage"] == "towing" and snap["connected"] is True
    assert snap["completedDebrisIds"] == []
    assert snap["activeDebrisId"] == "debris-1"
    _assert_pointer_clean(page, pointer_id, "debris-1 connection")

    pointer_id += 1
    _dispatch_pointer_gesture(
        page, rect, pointer_id, _towing_points(gup_start, debris_by_id["debris-1"])
    )
    snap = page.evaluate("() => OceanRescue.YoungWhale.getSnapshot()")
    assert snap["feedback"] == "success", f"debris-1 towing: {snap}"
    _wait_for_young_whale_idle(page, "connection")
    snap = page.evaluate("() => OceanRescue.YoungWhale.getSnapshot()")
    assert snap["stage"] == "connection"
    assert snap["activeDebrisId"] == "debris-2"
    assert snap["completedDebrisIds"] == ["debris-1"]
    assert snap["connected"] is False
    _assert_pointer_clean(page, pointer_id, "debris-1 towing")

    # debris-2: connection then towing
    pointer_id += 1
    _dispatch_pointer_gesture(
        page,
        rect,
        pointer_id,
        _connection_points(debris_by_id["debris-2"], hook),
    )
    snap = page.evaluate("() => OceanRescue.YoungWhale.getSnapshot()")
    assert snap["feedback"] == "success", f"debris-2 connection: {snap}"
    _wait_for_young_whale_idle(page, "towing")
    snap = page.evaluate("() => OceanRescue.YoungWhale.getSnapshot()")
    assert snap["stage"] == "towing" and snap["connected"] is True
    assert snap["activeDebrisId"] == "debris-2"
    assert snap["completedDebrisIds"] == ["debris-1"]
    _assert_pointer_clean(page, pointer_id, "debris-2 connection")

    pointer_id += 1
    _dispatch_pointer_gesture(
        page, rect, pointer_id, _towing_points(gup_start, debris_by_id["debris-2"])
    )
    snap = page.evaluate("() => OceanRescue.YoungWhale.getSnapshot()")
    assert snap["feedback"] == "success", f"debris-2 towing: {snap}"
    _wait_for_young_whale_idle(page, "connection")
    snap = page.evaluate("() => OceanRescue.YoungWhale.getSnapshot()")
    assert snap["stage"] == "connection"
    assert snap["activeDebrisId"] == "debris-3"
    assert snap["completedDebrisIds"] == ["debris-1", "debris-2"]
    assert snap["connected"] is False
    _assert_pointer_clean(page, pointer_id, "debris-2 towing")

    # debris-3: connection then towing (towing completes the mission)
    pointer_id += 1
    _dispatch_pointer_gesture(
        page,
        rect,
        pointer_id,
        _connection_points(debris_by_id["debris-3"], hook),
    )
    snap = page.evaluate("() => OceanRescue.YoungWhale.getSnapshot()")
    assert snap["feedback"] == "success", f"debris-3 connection: {snap}"
    _wait_for_young_whale_idle(page, "towing")
    snap = page.evaluate("() => OceanRescue.YoungWhale.getSnapshot()")
    assert snap["stage"] == "towing" and snap["connected"] is True
    assert snap["activeDebrisId"] == "debris-3"
    assert snap["completedDebrisIds"] == ["debris-1", "debris-2"]
    _assert_pointer_clean(page, pointer_id, "debris-3 connection")

    pointer_id += 1
    _dispatch_pointer_gesture(
        page, rect, pointer_id, _towing_points(gup_start, debris_by_id["debris-3"])
    )
    snap = page.evaluate("() => OceanRescue.YoungWhale.getSnapshot()")
    assert snap["feedback"] == "success", f"debris-3 towing: {snap}"
    _wait_for_young_whale_complete(page)
    snap = page.evaluate("() => OceanRescue.YoungWhale.getSnapshot()")
    assert snap["complete"] is True
    assert snap["active"] is False
    assert snap["activeDebrisId"] is None
    assert snap["stage"] is None
    assert snap["inputLocked"] is True
    assert snap["completedDebrisIds"] == ["debris-1", "debris-2", "debris-3"]
    assert (
        page.evaluate(
            "() => document.getElementById('ocean-rescue-root').getAttribute('data-rescue-input')"
        )
        == "disabled"
    ), "rescue input must be disabled after mission completion"

    # Mission success presentation: reach narration-1 via the real timers, then
    # advance narration-1 -> narration-2 -> complete card via real pointer taps.
    page.wait_for_function(
        "() => document.getElementById('ocean-rescue-root').getAttribute('data-mission-success-active') === 'true'",
        timeout=10000,
    )
    page.wait_for_function(
        "() => document.getElementById('ocean-rescue-root').getAttribute('data-mission-success-stage') === 'narration-1'",
        timeout=20000,
    )
    page.mouse.click(640, 360)
    page.wait_for_function(
        "() => document.getElementById('ocean-rescue-root').getAttribute('data-mission-success-stage') === 'narration-2'",
        timeout=5000,
    )
    page.mouse.click(640, 360)
    page.wait_for_function(
        "() => document.getElementById('ocean-rescue-root').getAttribute('data-mission-completion-recorded') === 'true'",
        timeout=10000,
    )

    missions = page.evaluate("() => OceanRescue.Missions.getSnapshot()")
    stored = page.evaluate(
        "() => JSON.parse(window.localStorage.getItem('aidengame.oceanRescue.progression') || 'null')"
    )
    root_attrs = page.evaluate(
        """() => {
          const root = document.getElementById('ocean-rescue-root');
          return {
            rescuePhase: root.getAttribute('data-rescue-phase'),
            rescueInput: root.getAttribute('data-rescue-input'),
            successStage: root.getAttribute('data-mission-success-stage'),
            completionRecorded: root.getAttribute('data-mission-completion-recorded')
          };
        }"""
    )
    return {
        "missions": missions,
        "stored_progression": stored,
        "root_attrs": root_attrs,
        "debris_completed": snap["completedDebrisIds"],
    }


def test_young_whale_full_three_debris_browser_session() -> None:
    server = HTTPServerFixture()
    base_url = server.start()
    page_errors: list[str] = []
    console_errors: list[str] = []
    console_warnings: list[str] = []
    request_failures: list[str] = []
    external_requests: list[str] = []
    all_requests: list[dict[str, str]] = []
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
                context.add_init_script(_POINTER_CAPTURE_INIT_SCRIPT)
                context.add_init_script(_DUPLICATE_INIT_OBSERVER_SCRIPT)
                page = context.new_page()

                def on_pageerror(error: object) -> None:
                    page_errors.append(str(error))

                def on_console(message: object) -> None:
                    if message.type == "error":
                        console_errors.append(message.text)
                    elif message.type == "warning":
                        console_warnings.append(message.text)

                def on_requestfailed(request: object) -> None:
                    request_failures.append(request.url)

                def on_request(request: object) -> None:
                    url = request.url
                    all_requests.append(
                        {"url": url, "resource_type": request.resource_type}
                    )
                    origin = urlsplit(base_url).netloc
                    if urlsplit(url).netloc not in {"", origin}:
                        external_requests.append(url)

                page.on("pageerror", on_pageerror)
                page.on("console", on_console)
                page.on("requestfailed", on_requestfailed)
                page.on("request", on_request)

                result = _run_full_session(page, base_url)

                missions = result["missions"]
                stored = result["stored_progression"]
                attrs = result["root_attrs"]

                assert missions["completedMissionIds"] == [
                    "sea-turtle",
                    "crab",
                    "young-whale",
                ], f"progression must record young-whale: {missions}"
                assert missions["unlockedMissionIds"] == [
                    "sea-turtle",
                    "crab",
                    "young-whale",
                ]
                assert stored is not None and stored["completedMissionIds"] == [
                    "sea-turtle",
                    "crab",
                    "young-whale",
                ], f"stored progression must persist young-whale: {stored}"
                assert attrs["rescuePhase"] == "mission-complete"
                assert attrs["rescueInput"] == "disabled"
                assert attrs["successStage"] == "complete"
                assert attrs["completionRecorded"] == "true"

                dom_content_loaded_count = page.evaluate(
                    "() => window.__ywDomContentLoadedCount"
                )
                ready_transitions = page.evaluate("() => window.__ywReadyTransitions")

                page.close()
            finally:
                browser.close()
    finally:
        server.stop()

    # Browser quality gate.
    assert page_errors == [], f"page errors: {page_errors}"
    assert console_errors == [], f"console errors: {console_errors}"
    assert request_failures == [], f"request failures: {request_failures}"
    assert external_requests == [], f"external runtime requests: {external_requests}"
    assert dom_content_loaded_count == 1, (
        "duplicate initialization detected: more than one DOMContentLoaded boot handler"
    )
    assert ready_transitions == 1, (
        "duplicate initialization detected: more than one ready transition"
    )
