"""Focused browser and static proof for the WP-33B launch/travel controller."""

from __future__ import annotations

import json
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
LEGACY_MANIFEST = SRC_DIR / "build-manifest.legacy.json"
CONTROLLER = SRC_DIR / "controllers" / "launch-travel.ts"
RUNTIME_ABI = SRC_DIR / "contracts" / "runtime-abi.ts"


def _enter_launch(page: Page) -> None:
    page.click('[data-profile-animal-id="arctic-fox"]')
    page.click("#ocean-rescue-profile-continue")
    page.wait_for_function("OceanRescue.State.getSnapshot().phase === 'MISSION_SELECT'")
    page.click('[data-mission-id="sea-turtle"]')
    page.wait_for_function("OceanRescue.State.getSnapshot().phase === 'GUP_SELECT'")
    page.click('[data-gup-id="gup-c"]')
    page.click("#ocean-rescue-gup-launch")
    page.wait_for_function("OceanRescue.State.getSnapshot().phase === 'LAUNCH'")


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


def test_typed_launch_travel_controller_owns_skip_travel_and_arrival_flow() -> None:
    with ViteServerFixture() as server:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            context.add_init_script("localStorage.clear(); sessionStorage.clear();")
            page = context.new_page()
            errors = _instrument(page, server.base_url)
            page.goto(f"{server.base_url}/index.dev.html")
            page.wait_for_selector(
                "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=20000
            )

            contract = page.evaluate(
                """() => Object.fromEntries([
                  'renderGupSelect', 'selectGup', 'backToMissionSelect',
                  'launchSelectedGup', 'skipLaunch', 'cancelLaunchRuntime',
                  'pauseTravelRuntime', 'resumeTravelRuntime', 'stopTravelRuntime',
                  'computeTravelProgress'
                ].map((name) => [name, typeof OceanRescue.App[name]]))"""
            )
            assert set(contract.values()) == {"function"}
            assert page.evaluate(
                "typeof OceanRescue.TravelProgress.compute"
            ) == "function"

            assert page.evaluate("OceanRescue.App.boot()") is True
            assert page.evaluate("OceanRescue.App.boot()") is True

            _enter_launch(page)
            launch_state = page.evaluate(
                """() => {
                  const root = document.getElementById('ocean-rescue-root');
                  return {
                    phase: OceanRescue.State.getSnapshot().phase,
                    mission: root.getAttribute('data-launch-mission-id'),
                    gup: root.getAttribute('data-launch-gup-id'),
                    ready: root.getAttribute('data-launch-ready'),
                    sequence: root.getAttribute('data-launch-sequence'),
                    briefing: document.getElementById('ocean-rescue-launch-briefing').textContent,
                  };
                }"""
            )
            assert launch_state == {
                "phase": "LAUNCH",
                "mission": "sea-turtle",
                "gup": "gup-c",
                "ready": "true",
                "sequence": "active",
                "briefing": (
                    "A sea turtle is trapped in a net. Let’s find it and cut the ropes!"
                ),
            }

            page.click("#ocean-rescue-launch-skip")
            page.wait_for_function("OceanRescue.State.getSnapshot().phase === 'TRAVEL'")
            travel_state = page.evaluate(
                """() => {
                  const root = document.getElementById('ocean-rescue-root');
                  return {
                    runtime: root.getAttribute('data-travel-runtime'),
                    input: root.getAttribute('data-travel-input'),
                    skipped: root.getAttribute('data-launch-skipped'),
                    ready: root.getAttribute('data-travel-ready'),
                    active: OceanRescue.Travel.getSnapshot().active,
                    progress: OceanRescue.TravelProgress.compute(
                      OceanRescue.Travel.getSnapshot()
                    ),
                  };
                }"""
            )
            assert travel_state["runtime"] == "active"
            assert travel_state["input"] == "enabled"
            assert travel_state["skipped"] == "true"
            assert travel_state["ready"] == "true"
            assert travel_state["active"] is True
            assert travel_state["progress"]["valid"] is True

            assert page.evaluate("OceanRescue.App.skipLaunch()") is False
            assert page.evaluate("OceanRescue.State.getSnapshot().phase") == "TRAVEL"

            canvas = page.locator("#ocean-rescue-canvas")
            box = canvas.bounding_box()
            assert box is not None
            page.mouse.click(box["x"] + box["width"] * 0.5, box["y"] + 180)
            page.wait_for_function("OceanRescue.Travel.getSnapshot().tapTargetY !== null")

            before_y = page.evaluate("OceanRescue.Travel.getSnapshot().y")
            page.mouse.move(box["x"] + 300, box["y"] + 320)
            page.mouse.down()
            page.mouse.move(box["x"] + 300, box["y"] + 440, steps=8)
            page.mouse.up()
            after_y = page.evaluate("OceanRescue.Travel.getSnapshot().y")
            assert after_y != before_y
            assert page.evaluate("OceanRescue.Travel.getSnapshot().dragging") is False

            page.click("#ocean-rescue-pause-button")
            assert page.locator("#ocean-rescue-pause-overlay").is_visible()
            paused_distance = page.evaluate("OceanRescue.Travel.getSnapshot().distance")
            page.wait_for_timeout(150)
            assert page.evaluate("OceanRescue.Travel.getSnapshot().distance") == paused_distance
            page.click("#ocean-rescue-pause-resume")
            page.wait_for_function(
                "document.getElementById('ocean-rescue-pause-overlay').hidden === true",
                timeout=6000,
            )
            page.wait_for_timeout(150)
            assert page.evaluate("OceanRescue.Travel.getSnapshot().distance") > paused_distance

            page.evaluate(
                """() => {
                  for (let i = 0; i < 1100; i += 1) {
                    OceanRescue.Travel.step(50);
                  }
                }"""
            )
            page.wait_for_function(
                "OceanRescue.State.getSnapshot().phase === 'RESCUE_SITE_TRANSITION'",
                timeout=5000,
            )
            arrival = page.evaluate(
                """() => {
                  const root = document.getElementById('ocean-rescue-root');
                  return {
                    runtime: root.getAttribute('data-travel-runtime'),
                    input: root.getAttribute('data-travel-input'),
                    rescue: root.getAttribute('data-rescue-sequence'),
                    travelActive: OceanRescue.Travel.getSnapshot().active,
                  };
                }"""
            )
            assert arrival == {
                "runtime": "stopped",
                "input": "disabled",
                "rescue": "active",
                "travelActive": False,
            }

            page_errors, console_errors, request_failures, external_requests = errors
            assert page_errors == []
            assert console_errors == []
            assert request_failures == []
            assert [
                url
                for url in external_requests
                if not url.startswith("data:")
                and "localhost" not in url
                and "127.0.0.1" not in url
            ] == []
            context.close()
            browser.close()


def test_typed_launch_automatic_completion_reaches_travel_once() -> None:
    with ViteServerFixture() as server:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            context.add_init_script("localStorage.clear(); sessionStorage.clear();")
            page = context.new_page()
            errors = _instrument(page, server.base_url)
            page.goto(f"{server.base_url}/index.dev.html")
            page.wait_for_selector(
                "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=20000
            )
            _enter_launch(page)
            page.wait_for_function(
                "OceanRescue.State.getSnapshot().phase === 'TRAVEL'", timeout=9000
            )
            assert (
                page.locator("#ocean-rescue-root").get_attribute(
                    "data-launch-skipped"
                )
                == "false"
            )
            assert page.evaluate("OceanRescue.App.skipLaunch()") is False
            page_errors, console_errors, request_failures, external_requests = errors
            assert page_errors == []
            assert console_errors == []
            assert request_failures == []
            assert [
                url
                for url in external_requests
                if not url.startswith("data:")
                and "localhost" not in url
                and "127.0.0.1" not in url
            ] == []
            context.close()
            browser.close()


def test_canonical_app_installs_controllers_in_order() -> None:
    text = ESM_APP.read_text(encoding="utf-8")
    assert "../controllers/profile-mission-selection" in text
    assert "../controllers/launch-travel" in text
    profile_install = text.index("installProfileMissionSelectionController(registeredApp)")
    launch_install = text.index("installLaunchTravelController(profileMissionApp)")
    assert profile_install < launch_install
    assert "export { App };" in text


def test_legacy_direct_callers_dispatch_through_installed_app() -> None:
    text = LEGACY_APP.read_text(encoding="utf-8")
    required = (
        "App.backToMissionSelect();",
        "App.launchSelectedGup();",
        "App.skipLaunch();",
        "App.pauseTravelRuntime();",
        "App.resumeTravelRuntime();",
        "App.stopTravelRuntime();",
        "App.cancelLaunchRuntime();",
    )
    for marker in required:
        assert marker in text
    assert "schedulePauseableTimer: scheduleWithRegistry" in text
    assert "handoffTravelArrival: handoffTravelArrival" in text


def test_wp33c_and_wp33d_ownership_are_not_copied() -> None:
    text = CONTROLLER.read_text(encoding="utf-8")
    for forbidden in (
        "freezeAllPauseTimers",
        "rearmAllPauseTimers",
        "pauseRemainingByOwner",
        "pauseCountdownTimerId",
        "runCountdownTick",
        "beginRescueArrival",
        "completeSiteTransition",
        "scheduleTutorialCompletion",
        "completeTutorial",
    ):
        assert forbidden not in text
    assert 'host.schedulePauseableTimer("launch"' in text
    assert 'host.schedulePauseableTimer("goal-banner"' in text
    assert "host.handoffTravelArrival()" in text


def test_runtime_abi_is_type_only_and_legacy_manifest_excludes_controller() -> None:
    abi = RUNTIME_ABI.read_text(encoding="utf-8")
    assert "import type" in abi
    assert "export interface TerrainApi" in abi
    assert "export interface RescueApi" in abi
    assert "export interface TravelSceneApi" in abi
    assert "export interface RenderRuntimeTravelApi" in abi
    assert "window." not in abi

    manifest = json.loads(LEGACY_MANIFEST.read_text(encoding="utf-8"))
    serialized = json.dumps(manifest)
    assert "controllers/launch-travel" not in serialized
