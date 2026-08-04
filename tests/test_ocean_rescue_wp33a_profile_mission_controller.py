"""Focused browser proof for the WP-33A typed profile/mission controller."""

import socketserver
import threading
import time
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
PORT = 18771


class HTTPServerFixture:
    def __init__(self):
        self.server = None
        self.thread = None

    def start(self):
        class QuietHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

            def log_message(self, format: str, *args) -> None:
                pass

        socketserver.TCPServer.allow_reuse_address = True
        self.server = socketserver.TCPServer(("127.0.0.1", PORT), QuietHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.5)
        return f"http://127.0.0.1:{PORT}"

    def stop(self):
        if self.server:
            self.server.shutdown()


@pytest.fixture(scope="module")
def server():
    fixture = HTTPServerFixture()
    url = fixture.start()
    yield url
    fixture.stop()


def test_typed_profile_mission_controller_owns_canonical_browser_flow(server):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        context.add_init_script("localStorage.clear(); sessionStorage.clear();")
        page = context.new_page()

        page_errors = []
        console_errors = []
        request_failures = []
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

        page.goto(f"{server}/ocean-rescue/index.html")
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
