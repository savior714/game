"""Focused browser and static proof for the WP-33C rescue-site/tutorial controller."""

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
CONTROLLER = SRC_DIR / "controllers" / "rescue-site-tutorial.ts"
RUNTIME_ABI = SRC_DIR / "contracts" / "runtime-abi.ts"


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


def _enter_rescue_site(page: Page) -> None:
    _enter_travel(page)
    page.evaluate(
        """() => {
          for (let index = 0; index < 1100; index += 1) {
            OceanRescue.Travel.step(50);
          }
        }"""
    )
    page.wait_for_function(
        "OceanRescue.State.getSnapshot().phase === 'RESCUE_SITE_TRANSITION'",
        timeout=5000,
    )


def test_typed_rescue_site_controller_owns_arrival_tutorial_and_skip_flow() -> None:
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
                  'handoffTravelArrival', 'skipTutorial',
                  'cancelRescueSiteRuntime', 'handleRescueStagePointerDown'
                ].map((name) => [name, typeof OceanRescue.App[name]]))"""
            )
            assert set(contract.values()) == {"function"}

            assert page.evaluate("OceanRescue.App.boot()") is True
            assert page.evaluate("OceanRescue.App.boot()") is True

            _enter_rescue_site(page)
            arrival = page.evaluate(
                """() => {
                  const root = document.getElementById('ocean-rescue-root');
                  return {
                    phase: OceanRescue.State.getSnapshot().phase,
                    rescuePhase: root.getAttribute('data-rescue-phase'),
                    rescueSequence: root.getAttribute('data-rescue-sequence'),
                    mission: root.getAttribute('data-rescue-mission-id'),
                    gup: root.getAttribute('data-rescue-gup-id'),
                    travelRuntime: root.getAttribute('data-travel-runtime'),
                    travelActive: OceanRescue.Travel.getSnapshot().active,
                    overlayHidden: document.getElementById('ocean-rescue-rescue-overlay').hidden,
                    readyHidden: document.getElementById('ocean-rescue-rescue-ready').hidden,
                  };
                }"""
            )
            assert arrival == {
                "phase": "RESCUE_SITE_TRANSITION",
                "rescuePhase": "site-transition",
                "rescueSequence": "active",
                "mission": "sea-turtle",
                "gup": "gup-c",
                "travelRuntime": "stopped",
                "travelActive": False,
                "overlayHidden": False,
                "readyHidden": False,
            }

            page.wait_for_function(
                "OceanRescue.State.getSnapshot().phase === 'RESCUE_TUTORIAL'",
                timeout=5000,
            )
            tutorial = page.evaluate(
                """() => {
                  const root = document.getElementById('ocean-rescue-root');
                  const tutorial = document.getElementById('ocean-rescue-rescue-tutorial');
                  return {
                    rescuePhase: root.getAttribute('data-rescue-phase'),
                    input: root.getAttribute('data-rescue-input'),
                    hidden: tutorial.hidden,
                    activeClass: tutorial.classList.contains('ocean-rescue-tutorial-active'),
                    instruction: document.getElementById('ocean-rescue-rescue-instruction').textContent,
                  };
                }"""
            )
            assert tutorial == {
                "rescuePhase": "tutorial",
                "input": "disabled",
                "hidden": False,
                "activeClass": True,
                "instruction": "Start here. Follow the rope to the end!",
            }

            page.dispatch_event(
                "#ocean-rescue-stage",
                "pointerdown",
                {"pointerId": 41, "button": 0, "isPrimary": True},
            )
            page.wait_for_function(
                "OceanRescue.State.getSnapshot().phase === 'RESCUE_ACTIVE'"
            )
            active = page.evaluate(
                """() => {
                  const root = document.getElementById('ocean-rescue-root');
                  return {
                    rescuePhase: root.getAttribute('data-rescue-phase'),
                    input: root.getAttribute('data-rescue-input'),
                    skipped: root.getAttribute('data-rescue-tutorial-skipped'),
                    seaTurtleActive: OceanRescue.SeaTurtle.getSnapshot().active,
                  };
                }"""
            )
            assert active == {
                "rescuePhase": "active",
                "input": "enabled",
                "skipped": "true",
                "seaTurtleActive": True,
            }
            assert page.evaluate("OceanRescue.App.skipTutorial()") is False

            page.wait_for_timeout(3200)
            assert (
                page.evaluate("OceanRescue.State.getSnapshot().phase")
                == "RESCUE_ACTIVE"
            )
            _assert_quality_gates(errors)
            context.close()
            browser.close()


def test_typed_rescue_tutorial_automatic_completion_reaches_active_once() -> None:
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
            _enter_rescue_site(page)
            page.wait_for_function(
                "OceanRescue.State.getSnapshot().phase === 'RESCUE_ACTIVE'",
                timeout=7000,
            )
            root = page.locator("#ocean-rescue-root")
            assert root.get_attribute("data-rescue-tutorial-skipped") == "false"
            assert page.evaluate("OceanRescue.App.skipTutorial()") is False
            assert page.evaluate("OceanRescue.SeaTurtle.getSnapshot().active") is True
            _assert_quality_gates(errors)
            context.close()
            browser.close()


def test_canonical_app_installs_wp33c_after_wp33b() -> None:
    text = ESM_APP.read_text(encoding="utf-8")
    assert "../controllers/profile-mission-selection" in text
    assert "../controllers/launch-travel" in text
    assert "../controllers/rescue-site-tutorial" in text
    profile_install = text.index(
        "installProfileMissionSelectionController(registeredApp)"
    )
    launch_install = text.index("installLaunchTravelController(profileMissionApp)")
    rescue_install = text.index("installRescueSiteTutorialController(launchTravelApp)")
    assert profile_install < launch_install < rescue_install
    assert "export { App };" in text


def test_legacy_direct_callers_dispatch_through_installed_wp33c_app() -> None:
    text = LEGACY_APP.read_text(encoding="utf-8")
    assert "App.handleRescueStagePointerDown(event);" in text
    assert "App.cancelRescueSiteRuntime();" in text
    for bridge in (
        "getActiveRescueSequence:",
        "setActiveRescueSequence:",
        "renderRescueSiteFrame: renderRescueSiteFrame",
        "startRescueInteraction: startRescueInteraction",
        "handleRescueStagePointerDown: onRescueStagePointerDown",
        "cancelRescueSiteRuntime: cancelRescueSiteRuntime",
    ):
        assert bridge in text


def test_wp33d_and_mission_specific_ownership_are_not_copied() -> None:
    text = CONTROLLER.read_text(encoding="utf-8")
    for forbidden in (
        "freezeAllPauseTimers",
        "rearmAllPauseTimers",
        "pauseRemainingByOwner",
        "pauseCountdownTimerId",
        "runCountdownTick",
        "bindRescuePointerInput",
        "beginSeaTurtleSuccessFeedback",
        "beginCrabSuccessFeedback",
        "beginYoungWhaleSuccessFeedback",
        "startMissionSuccessPresentation",
    ):
        assert forbidden not in text
    assert 'host.schedulePauseableTimer("site-transition"' in text
    assert 'host.schedulePauseableTimer("tutorial"' in text
    assert "host.startRescueInteraction(sequence)" in text
    assert "SeaTurtle.start(" not in text
    assert "Crab.start(" not in text
    assert "YoungWhale.start(" not in text


def test_runtime_abi_and_legacy_manifest_keep_wp33c_boundary() -> None:
    abi = RUNTIME_ABI.read_text(encoding="utf-8")
    assert "export interface RescueMissionContent" in abi
    assert "export interface MissionRuntimeApi" in abi
    assert "export interface RescueSceneApi" in abi
    assert "SiteTransitionMs" in abi
    assert "TutorialDurationMs" in abi
    assert "SeaTurtleScene?: SeaTurtleSceneApi" in abi
    assert "CrabScene?: RescueSceneApi" in abi
    assert "window." not in abi

    manifest = json.loads(LEGACY_MANIFEST.read_text(encoding="utf-8"))
    serialized = json.dumps(manifest)
    assert "controllers/rescue-site-tutorial" not in serialized
