"""Browser E2E test for Math daily goal reward entitlement and Ocean Rescue access gate."""

from __future__ import annotations

import http.server
import json
import threading
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Serve the repository root without request-log noise."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def log_message(self, format, *args):  # noqa: A002
        pass


@pytest.fixture(scope="module")
def static_server():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.server_address
    yield f"http://{host}:{port}"

    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


@pytest.fixture
def tablet_context():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )
        yield context
        context.close()
        browser.close()


def test_ocean_rescue_gated_on_fresh_state_and_direct_navigation(
    static_server: str,
    tablet_context,
) -> None:
    page = tablet_context.new_page()

    # 1. Fresh state: Open Main Hub
    page.goto(f"{static_server}/index.html")
    page.wait_for_selector("#ocean-rescue-card", state="visible", timeout=5000)

    card = page.locator("#ocean-rescue-card")
    expect(card).to_have_attribute("data-locked", "true")

    action_text = page.locator("#ocean-rescue-card-action-text")
    expect(action_text).to_contain_text("오늘 목표 완료 시 오픈")

    # Click on locked card should prevent navigation
    card.click()
    assert "/index.html" in page.url

    # 2. Direct navigation attempt to /ocean-rescue/index.html without entitlement
    page.goto(f"{static_server}/ocean-rescue/index.html")
    page.wait_for_selector("#ocean-rescue-root", state="attached", timeout=5000)

    root = page.locator("#ocean-rescue-root")
    expect(root).to_have_attribute("data-access-denied", "true")

    gate = page.locator("#ocean-rescue-admission-gate")
    expect(gate).to_be_visible()
    expect(gate).to_contain_text("오늘의 목표를 완료하면 열려요")


def test_math_goal_completion_unlocks_ocean_rescue_end_to_end(
    static_server: str,
    tablet_context,
) -> None:
    page = tablet_context.new_page()

    # 1. Enter Math Quiz
    page.goto(f"{static_server}/domains/math/index.html")
    page.wait_for_selector("#question", state="visible", timeout=5000)

    # 2. Answer 5 questions correctly to complete daily goal
    for _ in range(5):
        page.evaluate(
            """
            () => {
              const buttons = document.querySelectorAll('.answer-btn');
              for (const btn of buttons) {
                if (parseInt(btn.textContent) === answer) {
                  btn.click();
                  break;
                }
              }
            }
            """
        )
        page.wait_for_selector("#next-btn", state="visible", timeout=3000)
        page.locator("#next-btn").click()

    # Verify daily goal is complete
    status = page.locator("#daily-goal-status")
    expect(status).to_have_text("달성 완료! 🎉")

    # Verify rewards persisted in study_rewards
    rewards_raw = page.evaluate("() => localStorage.getItem('study_rewards')")
    assert rewards_raw is not None
    rewards = json.loads(rewards_raw)
    assert rewards["gems"] >= 2
    assert rewards["youtube_minutes"] >= 10

    # 3. Return to Main Hub -> Ocean Rescue card must be unlocked
    page.goto(f"{static_server}/index.html")
    page.wait_for_selector("#ocean-rescue-card", state="visible", timeout=5000)

    card = page.locator("#ocean-rescue-card")
    expect(card).to_have_attribute("data-locked", "false")

    action_text = page.locator("#ocean-rescue-card-action-text")
    expect(action_text).to_have_text("탐험 미션 시작")

    # 4. Click Ocean Rescue card -> navigates to /ocean-rescue/index.html and starts game
    card.click()
    page.wait_for_selector(
        "#ocean-rescue-root[data-ocean-rescue-ready='true']", timeout=10000
    )

    root = page.locator("#ocean-rescue-root")
    expect(root).to_have_attribute("data-access-denied", "false")
    expect(root).to_have_attribute("data-ocean-rescue-ready", "true")

    # 5. Reload /ocean-rescue/index.html -> stays unlocked
    page.reload()
    page.wait_for_selector(
        "#ocean-rescue-root[data-ocean-rescue-ready='true']", timeout=10000
    )
    expect(root).to_have_attribute("data-access-denied", "false")

    # 6. Revisit Math -> reward amount unchanged (no duplicate grant)
    page.goto(f"{static_server}/domains/math/index.html")
    page.wait_for_selector("#question", state="visible", timeout=5000)

    rewards_after = json.loads(
        page.evaluate("() => localStorage.getItem('study_rewards')")
    )
    assert rewards_after["gems"] == rewards["gems"]
    assert rewards_after["youtube_minutes"] == rewards["youtube_minutes"]
