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

    # 1. Fresh state: Main Hub is the single admission gate.
    page.goto(f"{static_server}/index.html")
    page.wait_for_selector("#ocean-rescue-card", state="visible", timeout=5000)

    card = page.locator("#ocean-rescue-card")
    expect(card).to_have_attribute("data-locked", "true")

    action_text = page.locator("#ocean-rescue-card-action-text")
    expect(action_text).to_contain_text("오늘 목표 완료 시 오픈")

    # Click on locked card should prevent navigation.
    card.click()
    assert "/index.html" in page.url

    # 2. Ocean Rescue itself no longer owns a second free-time admission gate.
    page.goto(f"{static_server}/ocean-rescue/index.html")
    page.wait_for_selector(
        "#ocean-rescue-root[data-ocean-rescue-ready='true']", timeout=10000
    )

    root = page.locator("#ocean-rescue-root")
    expect(root).to_have_attribute("data-ocean-rescue-ready", "true")
    assert root.get_attribute("data-access-denied") != "true"
    page.close()


def test_math_goal_completion_unlocks_ocean_rescue_with_back_and_stale_revalidation(
    static_server: str,
    tablet_context,
) -> None:
    page = tablet_context.new_page()

    # 1. Main Hub starts fresh (locked)
    page.goto(f"{static_server}/index.html")
    page.wait_for_selector("#ocean-rescue-card", state="visible", timeout=5000)
    card = page.locator("#ocean-rescue-card")
    expect(card).to_have_attribute("data-locked", "true")

    # 2. Navigate from Main Hub to Math Quiz (browser navigation history)
    page.goto(f"{static_server}/domains/math/index.html")
    page.wait_for_selector("#question", state="visible", timeout=5000)

    # 3. Answer 5 questions correctly to complete daily goal (Standard preset = 5)
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

    # 4. Return to Main Hub via browser Back (go_back) without page reload
    page.go_back()
    page.wait_for_selector("#ocean-rescue-card", state="visible", timeout=5000)

    # Due to pageshow handler, card state is immediately unlocked without manual reload
    expect(card).to_have_attribute("data-locked", "false")
    action_text = page.locator("#ocean-rescue-card-action-text")
    expect(action_text).to_have_text("탐험 미션 시작")

    # 5. Stale DOM revalidation check: artificially force data-locked="true" on the DOM element
    page.evaluate(
        "() => document.getElementById('ocean-rescue-card').setAttribute('data-locked', 'true')"
    )
    expect(card).to_have_attribute("data-locked", "true")

    # Click must revalidate against canonical storage and allow navigation despite stale attribute
    card.click()
    page.wait_for_selector(
        "#ocean-rescue-root[data-ocean-rescue-ready='true']", timeout=10000
    )
    root = page.locator("#ocean-rescue-root")
    expect(root).to_have_attribute("data-ocean-rescue-ready", "true")
    assert root.get_attribute("data-access-denied") != "true"
    page.close()


@pytest.mark.parametrize(
    ("preset_id", "target_count"),
    [
        ("light", 3),
        ("standard", 5),
        ("challenge", 7),
    ],
)
def test_established_mastery_profile_completes_goal_in_single_session(
    static_server: str,
    tablet_context,
    preset_id: str,
    target_count: int,
) -> None:
    page = tablet_context.new_page()

    # Setup non-fresh established profile with weak, review, and mastered skills
    page.goto(f"{static_server}/index.html")
    page.evaluate(
        """(preset) => {
          localStorage.clear();
          localStorage.setItem('aiden_math_goal_preference_v1', JSON.stringify({
            schemaVersion: 1,
            presetId: preset,
            updatedAt: new Date().toISOString()
          }));

          // Multi-evidence history making several skills weak/review/mastered
          const evidence = [
            { id: '1', skillId: 'math.add.within_10', correct: true, firstAttempt: true, timestamp: Date.now() - 86400000 * 5 },
            { id: '2', skillId: 'math.add.within_10', correct: true, firstAttempt: true, timestamp: Date.now() - 86400000 * 4 },
            { id: '3', skillId: 'math.add.within_10', correct: true, firstAttempt: true, timestamp: Date.now() - 86400000 * 3 },
            { id: '4', skillId: 'math.add.within_20.carry', correct: false, firstAttempt: false, timestamp: Date.now() - 86400000 * 2 },
            { id: '5', skillId: 'math.add.within_20.carry', correct: false, firstAttempt: false, timestamp: Date.now() - 86400000 * 1 },
          ];
          localStorage.setItem('aiden_math_learning_evidence_v1', JSON.stringify({
            schemaVersion: 1,
            items: evidence
          }));
        }""",
        preset_id,
    )

    # Enter Math Quiz
    page.goto(f"{static_server}/domains/math/index.html")
    page.wait_for_selector("#question", state="visible", timeout=5000)

    # Solve all 10 questions in a standard session
    completed_at_question = None
    for q_idx in range(1, 11):
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
        is_completed = page.evaluate(
            "() => mathDailyGoal && mathDailyGoal.completed === true"
        )
        if is_completed and completed_at_question is None:
            completed_at_question = q_idx

        # If not last question, click next
        if q_idx < 10:
            page.wait_for_selector("#next-btn", state="visible", timeout=3000)
            page.locator("#next-btn").click()

    # Assert goal was completed during this single 10-question session
    assert completed_at_question is not None, (
        f"Goal was not completed for preset {preset_id}"
    )
    assert completed_at_question == target_count, (
        f"Goal with targetCount={target_count} should complete exactly on question {target_count}, "
        f"but completed on question {completed_at_question}"
    )

    # Verify reward exactly once for daily goal (gems >= 2, free time >= 10 minutes, exactly 1 receipt)
    rewards_raw = page.evaluate("() => localStorage.getItem('study_rewards')")
    assert rewards_raw is not None
    rewards = json.loads(rewards_raw)
    assert rewards["gems"] >= 2
    assert rewards["youtube_minutes"] >= 10

    # Receipt exists exactly once
    receipt_data = page.evaluate(
        "() => Object.keys(localStorage).filter(k => k.startsWith('aiden_receipt_receipt-math-goal-'))"
    )
    assert len(receipt_data) == 1

    # Main Hub is unlocked
    page.goto(f"{static_server}/index.html")
    card = page.locator("#ocean-rescue-card")
    expect(card).to_have_attribute("data-locked", "false")
    page.close()


def test_local_calendar_date_boundary_asia_seoul(
    static_server: str,
    tablet_context,
) -> None:
    page = tablet_context.new_page()

    # Under Asia/Seoul (UTC+9), 00:15 KST, 08:59 KST, 09:01 KST on 2026-09-01 are all date '2026-09-01'
    page.goto(f"{static_server}/index.html")

    # Set completed goal for local date 2026-09-01
    date_eval = page.evaluate(
        """() => {
          // Verify local date string generation at different KST times on 2026-09-01:
          // 2026-09-01 00:15:00 KST = 2026-08-31T15:15:00.000Z
          const t1 = new Date('2026-08-31T15:15:00.000Z');
          // 2026-09-01 08:59:00 KST = 2026-08-31T23:59:00.000Z
          const t2 = new Date('2026-08-31T23:59:00.000Z');
          // 2026-09-01 09:01:00 KST = 2026-09-01T00:01:00.000Z (UTC midnight rollover point)
          const t3 = new Date('2026-09-01T00:01:00.000Z');

          const d1 = MathDailyGoalEngine.getTodayDateString(t1);
          const d2 = MathDailyGoalEngine.getTodayDateString(t2);
          const d3 = MathDailyGoalEngine.getTodayDateString(t3);

          return { d1, d2, d3 };
        }"""
    )

    assert date_eval["d1"] == "2026-09-01"
    assert date_eval["d2"] == "2026-09-01"
    assert date_eval["d3"] == "2026-09-01"

    # Set completed goal for today
    today_str = page.evaluate("() => MathDailyGoalEngine.getTodayDateString()")
    page.evaluate(
        """(day) => {
          localStorage.setItem('aiden_math_daily_goal_v1', JSON.stringify({
            schemaVersion: 1,
            date: day,
            targetCount: 5,
            currentCount: 5,
            completed: true,
            completedAt: Date.now(),
            rewardGranted: true,
            rewardReceiptId: `receipt-${day}`
          }));
        }""",
        today_str,
    )

    page.reload()
    card = page.locator("#ocean-rescue-card")
    expect(card).to_have_attribute("data-locked", "false")

    # Next local calendar day rollover: prior day completion becomes locked on the next day
    page.evaluate(
        """() => {
          const yesterday = '2020-01-01';
          localStorage.setItem('aiden_math_daily_goal_v1', JSON.stringify({
            schemaVersion: 1,
            date: yesterday,
            targetCount: 5,
            currentCount: 5,
            completed: true,
            completedAt: Date.now(),
            rewardGranted: true,
            rewardReceiptId: `receipt-${yesterday}`
          }));
        }"""
    )
    page.reload()
    expect(card).to_have_attribute("data-locked", "true")
    page.close()
