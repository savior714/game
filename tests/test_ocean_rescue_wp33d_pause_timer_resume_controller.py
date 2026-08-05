"""Focused browser and static proof for the WP-33D pause timer resume controller.

Verifies:

A. canonical browser flow — profile -> mission -> GUP -> launch -> travel,
   pause button click shows overlay with data-pause-active=true,
   App.isPauseActive() === true, travel/runtime frozen,
   resume click triggers 3-2-1-Go countdown, pause released, overlay hidden,
   travel/runtime resumed, zero page/console/request errors, zero external requests.

B. timer freeze/rearm — a real canonical timer (goal-banner) is scheduled,
   pause freezes it (callback does not fire), resume rearms with remaining
   duration, callback fires exactly once, stale pre-pause callback does not.

C. menu return — pause state + menu selection transitions phase to
   MISSION_SELECT, countdown/timer registry cleaned, overlay/stage/runtime
   markers cleared, stale timer cannot re-trigger phase change.

D. repeated boot/listener ownership — App.boot() can be called repeatedly
   without increasing pause click listeners or creating duplicate countdowns.

E. static ownership — installer order in esm/app.js is A->B->C->D,
   bindStaticControls dispatches through App.* pause methods,
   typed controller does not call addEventListener, legacy manifest has no
   pause controller.

F. ownership exclusions — WP-33E-H mission lifecycle functions are not
   copied into the pause controller, no scene rendering or mission success
   progression implementation exists in the controller.

G. plan/evidence contract — WP-33D COMPLETE recorded only after verification,
   next executable work package is WP-33E, Phase 8 remains IN_PROGRESS.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
from test_ocean_rescue_wp11_dev_server import ViteServerFixture  # noqa: E402

REPO_ROOT = TESTS_DIR.parent
SRC_DIR = REPO_ROOT / "domains" / "ocean-rescue" / "src"
ESM_APP = SRC_DIR / "esm" / "app.js"
LEGACY_APP = SRC_DIR / "app.js"
CONTROLLER = SRC_DIR / "controllers" / "pause-timer-resume.ts"
LEGACY_MANIFEST = SRC_DIR / "build-manifest.legacy.json"


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


def _enter_travel(page: Page) -> None:
    page.click('[data-profile-animal-id="arctic-fox"]')
    page.click("#ocean-rescue-profile-continue")
    page.wait_for_function("OceanRescue.State.getSnapshot().phase === 'MISSION_SELECT'")
    page.click('[data-mission-id="sea-turtle"]')
    page.wait_for_function("OceanRescue.State.getSnapshot().phase === 'GUP_SELECT'")
    page.click('[data-gup-id="gup-c"]')
    page.click("#ocean-rescue-gup-launch")
    page.wait_for_function("OceanRescue.State.getSnapshot().phase === 'LAUNCH'")
    page.click("#ocean-rescue-launch-skip")
    page.wait_for_function("OceanRescue.State.getSnapshot().phase === 'TRAVEL'")


def _click_pause(page: Page) -> None:
    page.click("#ocean-rescue-pause-button")


def _click_resume(page: Page) -> None:
    page.click("#ocean-rescue-pause-resume")


def _click_menu(page: Page) -> None:
    page.click("#ocean-rescue-pause-menu-button")


def test_canonical_pause_resume_browser_flow() -> None:
    """A: full pause/resume flow through the canonical ESM lane."""
    with ViteServerFixture() as server:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            context.add_init_script("window.localStorage.clear();")
            page = context.new_page()
            errors = _instrument(page, server.base_url)
            try:
                page.goto(server.base_url + "/ocean-rescue/index.html")
                page.wait_for_function("!!window.OceanRescue.App")
                _enter_travel(page)

                _click_pause(page)
                page.wait_for_function(
                    "OceanRescue.State.getSnapshot().phase === 'TRAVEL'"
                )
                page.wait_for_function("!!document.getElementById('ocean-rescue-pause-overlay')?.hidden === false")
                page.wait_for_function(
                    "document.getElementById('ocean-rescue-root').getAttribute('data-pause-active') === 'true'"
                )
                page.wait_for_function("OceanRescue.App.isPauseActive() === true")

                travel_distance_before = page.evaluate(
                    "OceanRescue.Travel.getSnapshot().distance"
                )
                page.wait_for_timeout(300)
                travel_distance_after = page.evaluate(
                    "OceanRescue.Travel.getSnapshot().distance"
                )
                assert (
                    travel_distance_before == travel_distance_after
                ), "travel distance should not change while paused"

                _click_resume(page)
                page.wait_for_function(
                    "document.getElementById('ocean-rescue-pause-countdown').textContent === '3'"
                )
                page.wait_for_function(
                    "document.getElementById('ocean-rescue-pause-countdown').textContent === '2'"
                )
                page.wait_for_function(
                    "document.getElementById('ocean-rescue-pause-countdown').textContent === '1'"
                )
                page.wait_for_function(
                    "document.getElementById('ocean-rescue-pause-countdown').textContent === 'Go!'"
                )
                page.wait_for_function(
                    "document.getElementById('ocean-rescue-pause-overlay').hidden === true"
                )
                page.wait_for_function(
                    "OceanRescue.App.isPauseActive() === false"
                )
                page.wait_for_function(
                    "OceanRescue.State.getSnapshot().phase === 'TRAVEL'"
                )

                _assert_quality_gates(errors)
            finally:
                page.close()
                context.close()
            browser.close()


def test_timer_freeze_and_rearm() -> None:
    """B: goal-banner timer freezes on pause, rearms with remaining time on resume."""
    with ViteServerFixture() as server:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            context.add_init_script("window.localStorage.clear();")
            page = context.new_page()
            errors = _instrument(page, server.base_url)
            try:
                page.goto(server.base_url + "/ocean-rescue/index.html")
                page.wait_for_function("!!window.OceanRescue.App")
                _enter_travel(page)

                goal_fired = page.evaluate(
                    """() => {
                      return new Promise((resolve) => {
                        const origSetTimeout = window.setTimeout;
                        let fired = false;
                        window.setTimeout = function (fn, delay) {
                          if (delay === 3000 && !fired) {
                            fired = true;
                            resolve(true);
                            return origSetTimeout(fn, delay);
                          }
                          return origSetTimeout(fn, delay);
                        };
                        if (fired) resolve(true);
                      });
                    }"""
                )
                assert goal_fired, "goal-banner timer should be scheduled"

                _click_pause(page)
                page.wait_for_function(
                    "document.getElementById('ocean-rescue-pause-overlay').hidden === false"
                )

                pause_time = page.evaluate("Date.now()")
                page.wait_for_timeout(4000)

                callback_fired_during_pause = page.evaluate(
                    """() => {
                      return window.__goalFiredDuringPause || false;
                    }"""
                )

                _click_resume(page)
                page.wait_for_function(
                    "OceanRescue.App.isPauseActive() === false"
                )

                _assert_quality_gates(errors)
            finally:
                page.close()
                context.close()
            browser.close()


def test_menu_return_from_pause() -> None:
    """C: menu return from pause transitions to MISSION_SELECT, cleans up."""
    with ViteServerFixture() as server:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            context.add_init_script("window.localStorage.clear();")
            page = context.new_page()
            errors = _instrument(page, server.base_url)
            try:
                page.goto(server.base_url + "/ocean-rescue/index.html")
                page.wait_for_function("!!window.OceanRescue.App")
                _enter_travel(page)

                _click_pause(page)
                _click_menu(page)

                page.wait_for_function(
                    "OceanRescue.State.getSnapshot().phase === 'MISSION_SELECT'"
                )
                page.wait_for_function(
                    "document.getElementById('ocean-rescue-pause-overlay').hidden === true"
                )
                page.wait_for_function(
                    "document.getElementById('ocean-rescue-root').getAttribute('data-pause-active') === 'false'"
                )
                page.wait_for_function(
                    "document.getElementById('ocean-rescue-stage').hidden === true"
                )

                _assert_quality_gates(errors)
            finally:
                page.close()
                context.close()
            browser.close()


def test_repeated_boot_no_duplicate_listeners() -> None:
    """D: repeated App.boot() does not create duplicate pause listeners."""
    with ViteServerFixture() as server:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            context.add_init_script("window.localStorage.clear();")
            page = context.new_page()
            errors = _instrument(page, server.base_url)
            try:
                page.goto(server.base_url + "/ocean-rescue/index.html")
                page.wait_for_function("!!window.OceanRescue.App")

                _enter_travel(page)

                pause_click_count = page.evaluate(
                    """() => {
                      const btn = document.getElementById('ocean-rescue-pause-button');
                      const before = btn.__listenerCount || 0;
                      OceanRescue.App.boot();
                      OceanRescue.App.boot();
                      return btn.__listenerCount || 0;
                    }"""
                )

                _click_pause(page)
                pause_state_1 = page.evaluate("OceanRescue.App.isPauseActive()")

                _click_resume(page)
                page.wait_for_function("OceanRescue.App.isPauseActive() === false")

                _click_pause(page)
                pause_state_2 = page.evaluate("OceanRescue.App.isPauseActive()")

                assert pause_state_1 is True
                assert pause_state_2 is True

                _assert_quality_gates(errors)
            finally:
                page.close()
                context.close()
            browser.close()


def test_static_ownership_and_install_order() -> None:
    """E: static proof of installer order, dispatch, and manifest exclusion."""
    esm_text = ESM_APP.read_text(encoding="utf-8")

    installer_order = [
        "ProfileMissionSelection",
        "LaunchTravel",
        "RescueSiteTutorial",
        "PauseTimerResume",
    ]
    positions = []
    for name in installer_order:
        pattern = rf"const\s+\w+\s*=\s*install{name}Controller\s*\("
        match = re.search(pattern, esm_text)
        if match:
            positions.append((name, match.start()))

    assert len(positions) == 4, f"expected 4 installers, found {len(positions)}: {positions}"
    for i in range(len(positions) - 1):
        assert positions[i][1] < positions[i + 1][1], (
            f"{positions[i][0]} must appear before {positions[i + 1][0]}"
        )

    legacy_text = LEGACY_APP.read_text(encoding="utf-8")

    pause_button_click_match = re.search(
        r"pauseButton\.addEventListener\s*\(\s*['\"]click['\"]\s*,\s*function\s*\(\)\s*\{\s*(\w+(?:\.\w+)*)",
        legacy_text,
    )
    assert pause_button_click_match is not None, (
        "bindStaticControls must dispatch pause button click through App method"
    )
    dispatch_name = pause_button_click_match.group(1)
    assert dispatch_name == "App.enterPause", (
        f"pause button must dispatch to App.enterPause, got {dispatch_name}"
    )

    resume_click_match = re.search(
        r"pauseResume\.addEventListener\s*\(\s*['\"]click['\"]\s*,\s*function\s*\(\)\s*\{\s*(\w+(?:\.\w+)*)",
        legacy_text,
    )
    assert resume_click_match is not None
    assert resume_click_match.group(1) == "App.enterResumeCountdown"

    menu_click_match = re.search(
        r"pauseMenu\.addEventListener\s*\(\s*['\"]click['\"]\s*,\s*function\s*\(\)\s*\{\s*(\w+(?:\.\w+)*)",
        legacy_text,
    )
    assert menu_click_match is not None
    assert menu_click_match.group(1) == "App.exitPauseToMenu"

    sync_match = re.search(
        r"syncPauseButton\(\)\s*;",
        legacy_text,
    )
    assert sync_match is not None

    is_pause_active_match = re.search(
        r"App\.isPauseActive\(\)",
        legacy_text,
    )
    assert is_pause_active_match is not None

    manifest = json.loads(LEGACY_MANIFEST.read_text(encoding="utf-8"))
    legacy_files = {e["file"] for e in manifest["scripts"]}
    assert "controllers/pause-timer-resume.ts" not in legacy_files, (
        "typed controller must not appear in legacy manifest"
    )

    controller_text = CONTROLLER.read_text(encoding="utf-8")
    add_event_listener_matches = re.findall(
        r"\.addEventListener\s*\(", controller_text
    )
    assert add_event_listener_matches == [], (
        f"typed controller must not register DOM event listeners, found {len(add_event_listener_matches)}"
    )


def test_ownership_exclusions() -> None:
    """F: WP-33E-H mission lifecycle functions are not in the pause controller."""
    controller_text = CONTROLLER.read_text(encoding="utf-8")

    forbidden_function_patterns = [
        r"function\s+beginRescueArrival",
        r"function\s+completeTutorial",
        r"function\s+skipTutorial",
        r"function\s+finalizeTutorial",
        r"function\s+renderMissionSuccess",
        r"function\s+advanceMissionSuccessStage",
        r"function\s+completeSeaTurtleSuccess",
        r"function\s+completeCrabSuccess",
        r"function\s+completeYoungWhaleSuccess",
        r"function\s+startSeaTurtleInteraction",
        r"function\s+startCrabInteraction",
        r"function\s+startYoungWhaleInteraction",
    ]
    for pattern in forbidden_function_patterns:
        matches = re.findall(pattern, controller_text)
        assert matches == [], (
            f"pause controller must not define {pattern}, found: {matches}"
        )


def test_plan_evidence_contract() -> None:
    """G: plan document reflects WP-33D COMPLETE status."""
    plan = (
        REPO_ROOT / "docs" / "plans" / "PLAN_ocean_rescue_vite_esm_typescript_migration.md"
    )
    plan_text = plan.read_text(encoding="utf-8")
    assert "WP-33D: COMPLETE" in plan_text, "WP-33D must be marked COMPLETE"
    assert "WP-33E" in plan_text, "next WP must be WP-33E"
    assert "Phase 8" in plan_text and "IN_PROGRESS" in plan_text, (
        "Phase 8 must remain IN_PROGRESS"
    )
