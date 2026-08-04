"""Focused browser proof for the WP-33A typed profile/mission controller."""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
from test_ocean_rescue_wp11_dev_server import ViteServerFixture  # noqa: E402


def test_typed_profile_mission_controller_owns_canonical_browser_flow() -> None:
    with ViteServerFixture() as server:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            context.add_init_script("localStorage.clear(); sessionStorage.clear();")
            page = context.new_page()

            page_errors: list[str] = []
            console_errors: list[str] = []
            request_failures: list[dict[str, object]] = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.on(
                "console",
                lambda message: (
                    console_errors.append(message.text)
                    if message.type == "error"
                    else None
                ),
            )
            page.on(
                "requestfailed",
                lambda request: request_failures.append(
                    {"url": request.url, "failure": request.failure}
                ),
            )

            page.goto(f"{server.base_url}/index.dev.html")
            page.wait_for_selector(
                "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=20000
            )

            controller_contract = page.evaluate(
                """() => ({
                  renderProfileChoice: typeof OceanRescue.App.renderProfileChoice,
                  selectProfileAnimal: typeof OceanRescue.App.selectProfileAnimal,
                  confirmProfileSelection: typeof OceanRescue.App.confirmProfileSelection,
                  renderMissionSelect: typeof OceanRescue.App.renderMissionSelect,
                  selectMission: typeof OceanRescue.App.selectMission,
                })"""
            )
            assert controller_contract == {
                "renderProfileChoice": "function",
                "selectProfileAnimal": "function",
                "confirmProfileSelection": "function",
                "renderMissionSelect": "function",
                "selectMission": "function",
            }

            profile = page.locator("#ocean-rescue-profile-choice")
            assert profile.is_visible()
            animals = page.locator(
                "#ocean-rescue-profile-animal-list [data-profile-animal-id]"
            )
            assert animals.count() == 3

            continue_button = page.locator("#ocean-rescue-profile-continue")
            assert continue_button.is_disabled()
            page.click('[data-profile-animal-id="arctic-fox"]')
            assert (
                page.locator('[data-profile-animal-id="arctic-fox"]').get_attribute(
                    "aria-pressed"
                )
                == "true"
            )
            assert continue_button.is_enabled()
            continue_button.click()

            page.wait_for_function(
                """() => OceanRescue.State.getSnapshot().phase === 'MISSION_SELECT'"""
            )
            assert not profile.is_visible()
            mission_cards = page.locator(
                "#ocean-rescue-mission-list [data-mission-id]"
            )
            assert mission_cards.count() == 3

            sea_turtle = page.locator('[data-mission-id="sea-turtle"]')
            crab = page.locator('[data-mission-id="crab"]')
            young_whale = page.locator('[data-mission-id="young-whale"]')
            assert sea_turtle.is_enabled()
            assert crab.is_disabled()
            assert young_whale.is_disabled()

            sea_turtle.click()
            page.wait_for_function(
                """() => OceanRescue.State.getSnapshot().phase === 'GUP_SELECT'"""
            )
            page.wait_for_selector("#ocean-rescue-gup-select:not([hidden])")
            mission_snapshot = page.evaluate(
                """() => OceanRescue.Missions.getSnapshot()"""
            )
            assert mission_snapshot["selectedMissionId"] == "sea-turtle"
            assert mission_snapshot["newMissionIds"] == []

            assert page_errors == []
            assert console_errors == []
            assert request_failures == []

            context.close()
            browser.close()
