"""Browser verification for Math curriculum skill mastery and adaptive daily goal vertical slice."""

from __future__ import annotations

import http.server
import json
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright


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
def tablet_math_page(static_server: str):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        # Galaxy Tab S10 landscape viewport baseline
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )
        page = context.new_page()
        page_errors: list[str] = []
        console_errors: list[str] = []

        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "console",
            lambda msg: (
                console_errors.append(msg.text) if msg.type == "error" else None
            ),
        )

        page.goto(f"{static_server}/domains/math/index.html")
        page.wait_for_selector("#question", state="visible", timeout=5000)

        yield page, page_errors, console_errors

        context.close()
        browser.close()


@pytest.mark.browser
def test_math_daily_goal_banner_displayed_on_load(
    tablet_math_page: tuple[Page, list[str], list[str]],
) -> None:
    page, page_errors, console_errors = tablet_math_page

    banner = page.locator("#daily-goal-banner")
    expect(banner).to_be_visible()

    desc = page.locator("#daily-goal-desc")
    expect(desc).to_contain_text("마스터하기")

    status = page.locator("#daily-goal-status")
    expect(status).to_have_text("도전 중")

    counter = page.locator("#daily-goal-count")
    expect(counter).to_have_text("0 / 5")

    assert page_errors == []


@pytest.mark.browser
def test_math_learning_evidence_and_daily_goal_progression(
    tablet_math_page: tuple[Page, list[str], list[str]],
) -> None:
    page, page_errors, console_errors = tablet_math_page

    # Answer questions correctly until goal completes (5 target answers)
    for _ in range(5):
        # Click the correct answer
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

        # Check evidence in localStorage
        raw_evidence = page.evaluate(
            "() => localStorage.getItem('aiden_math_learning_evidence_v1')"
        )
        assert raw_evidence is not None
        evidence_data = json.loads(raw_evidence)
        assert len(evidence_data["items"]) >= 1
        last_item = evidence_data["items"][-1]
        assert "skillId" in last_item
        assert last_item["correct"] is True

        # Click next question
        page.locator("#next-btn").click()

    # Verify daily goal is completed
    status = page.locator("#daily-goal-status")
    expect(status).to_have_text("달성 완료! 🎉")

    counter = page.locator("#daily-goal-count")
    expect(counter).to_have_text("5 / 5")

    # Verify reward (gems and youtube minutes) in study_rewards
    rewards_raw = page.evaluate("() => localStorage.getItem('study_rewards')")
    assert rewards_raw is not None
    rewards = json.loads(rewards_raw)
    assert rewards["gems"] >= 2
    assert rewards["youtube_minutes"] >= 10

    # Verify receipt stored
    goal_raw = page.evaluate("() => localStorage.getItem('aiden_math_daily_goal_v1')")
    goal = json.loads(goal_raw)
    assert goal["completed"] is True
    assert goal["rewardGranted"] is True
    assert goal["rewardReceiptId"] is not None

    receipt_raw = page.evaluate(
        f"() => localStorage.getItem('aiden_receipt_{goal['rewardReceiptId']}')"
    )
    assert receipt_raw is not None

    assert page_errors == []


@pytest.mark.browser
def test_math_daily_goal_reward_is_idempotent_on_reload(
    tablet_math_page: tuple[Page, list[str], list[str]],
) -> None:
    page, page_errors, console_errors = tablet_math_page

    # Complete 5 questions
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

    # Record initial reward balance
    rewards_before = json.loads(
        page.evaluate("() => localStorage.getItem('study_rewards')")
    )
    gems_before = rewards_before["gems"]
    yt_before = rewards_before["youtube_minutes"]

    # Reload page
    page.reload()
    page.wait_for_selector("#question", state="visible", timeout=5000)

    # Verify goal remains completed
    status = page.locator("#daily-goal-status")
    expect(status).to_have_text("달성 완료! 🎉")

    # Verify rewards did not increase on reload
    rewards_after = json.loads(
        page.evaluate("() => localStorage.getItem('study_rewards')")
    )
    assert rewards_after["gems"] == gems_before
    assert rewards_after["youtube_minutes"] == yt_before

    assert page_errors == []


@pytest.mark.browser
def test_math_landscape_and_portrait_responsiveness_zero_errors(
    tablet_math_page: tuple[Page, list[str], list[str]],
) -> None:
    page, page_errors, console_errors = tablet_math_page

    # 1. Landscape (1280x800)
    page.set_viewport_size({"width": 1280, "height": 800})
    expect(page.locator("#daily-goal-banner")).to_be_visible()
    expect(page.locator("#question")).to_be_visible()
    expect(page.locator("#rocket-panel")).to_be_visible()

    # 2. Portrait (800x1280)
    page.set_viewport_size({"width": 800, "height": 1280})
    expect(page.locator("#daily-goal-banner")).to_be_visible()
    expect(page.locator("#question")).to_be_visible()

    # 3. Split screen (600x800)
    page.set_viewport_size({"width": 600, "height": 800})
    expect(page.locator("#daily-goal-banner")).to_be_visible()
    expect(page.locator("#question")).to_be_visible()

    assert page_errors == []
