"""Browser E2E verification for Math Daily Streak vertical slice."""

from __future__ import annotations

import http.server
import json
import threading
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Serve repository root without verbose logs."""

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


@pytest.mark.browser
def test_child_math_streak_display_and_reload_persistence(static_server: str) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )
        page = context.new_page()

        # Seed existing 3-day streak into localStorage before load
        page.goto(f"{static_server}/index.html")
        page.evaluate(
            """
            () => {
              localStorage.setItem('aiden_math_streak_v1', JSON.stringify({
                schemaVersion: 1,
                currentStreak: 3,
                lastObservedDate: new Date().toISOString().split('T')[0],
                lastCompletedDate: null,
                updatedAt: new Date().toISOString()
              }));
            }
            """
        )

        page.goto(f"{static_server}/domains/math/index.html")
        page.wait_for_selector("#question", state="visible", timeout=5000)

        streak_el = page.locator("#daily-goal-streak")
        expect(streak_el).to_be_visible()
        expect(streak_el).to_have_text("🔥 3일 연속")

        # Reload and verify persistence
        page.reload()
        page.wait_for_selector("#question", state="visible", timeout=5000)
        expect(page.locator("#daily-goal-streak")).to_have_text("🔥 3일 연속")

        context.close()
        browser.close()


@pytest.mark.browser
def test_real_daily_goal_completion_increments_streak_and_idempotency(
    static_server: str,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )
        page = context.new_page()

        # Fresh state
        page.goto(f"{static_server}/index.html")
        page.evaluate("() => localStorage.clear()")

        page.goto(f"{static_server}/domains/math/index.html")
        page.wait_for_selector("#question", state="visible", timeout=5000)

        streak_el = page.locator("#daily-goal-streak")
        expect(streak_el).to_be_visible()
        expect(streak_el).to_have_text("🔥 0일 연속")

        # Solve 5 questions correctly to achieve daily goal
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

        # Goal is completed
        expect(page.locator("#daily-goal-status")).to_have_text("달성 완료! 🎉")
        expect(page.locator("#daily-goal-count")).to_have_text("5 / 5")

        # Streak indicator immediately updated to 1
        expect(page.locator("#daily-goal-streak")).to_have_text("🔥 1일 연속")

        # Check storage
        streak_raw = page.evaluate("() => localStorage.getItem('aiden_math_streak_v1')")
        assert streak_raw is not None
        streak_data = json.loads(streak_raw)
        assert streak_data["currentStreak"] == 1
        today_str = page.evaluate("() => new Date().toISOString().split('T')[0]")
        assert streak_data["lastCompletedDate"] == today_str

        # Solve 6th question -> streak remains 1 (idempotent, no duplicate increment)
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

        expect(page.locator("#daily-goal-streak")).to_have_text("🔥 1일 연속")
        streak_raw2 = page.evaluate(
            "() => localStorage.getItem('aiden_math_streak_v1')"
        )
        assert json.loads(streak_raw2)["currentStreak"] == 1

        context.close()
        browser.close()


@pytest.mark.browser
def test_guardian_math_streak_same_display_and_read_only(
    static_server: str,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )
        page = context.new_page()

        today_str = "2026-08-16"

        # Seed completed goal and streak 4 into storage
        page.goto(f"{static_server}/index.html")
        page.evaluate(
            f"""
            () => {{
              localStorage.setItem('aiden_math_daily_goal_v1', JSON.stringify({{
                schemaVersion: 1,
                date: '{today_str}',
                goalId: 'goal-{today_str}-test',
                skillId: 'math.add.within_10',
                skillName: '10 이하의 덧셈',
                targetCount: 5,
                currentCount: 5,
                completed: true,
                completedAt: Date.now(),
                rewardGranted: true,
                rewardReceiptId: 'receipt-1'
              }}));
              localStorage.setItem('aiden_math_streak_v1', JSON.stringify({{
                schemaVersion: 1,
                currentStreak: 4,
                lastObservedDate: '{today_str}',
                lastCompletedDate: '{today_str}',
                updatedAt: new Date().toISOString()
              }}));
            }}
            """
        )

        page.goto(f"{static_server}/domains/reward/guardian/index.html")
        page.wait_for_selector(
            "#math-progress-snapshot-section", state="visible", timeout=5000
        )

        val_el = page.locator("#guardian-math-streak-val")
        expect(val_el).to_be_visible()
        expect(val_el).to_have_text("4일")

        status_el = page.locator("#guardian-math-streak-status")
        expect(status_el).to_have_text("오늘 목표 완료")

        context.close()
        browser.close()


@pytest.mark.browser
def test_guardian_preset_selection_does_not_mutate_streak_or_stats(
    static_server: str,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )
        page = context.new_page()

        # Seed initial streak 5
        page.goto(f"{static_server}/index.html")
        page.evaluate(
            """
            () => {
              localStorage.setItem('aiden_math_streak_v1', JSON.stringify({
                schemaVersion: 1,
                currentStreak: 5,
                lastObservedDate: new Date().toISOString().split('T')[0],
                lastCompletedDate: null,
                updatedAt: new Date().toISOString()
              }));
              localStorage.setItem('aiden_math_stats', JSON.stringify({
                '+': { levels: { 0: { attempts: 10, correct: 9 } } }
              }));
            }
            """
        )

        page.goto(f"{static_server}/domains/reward/guardian/index.html")
        page.wait_for_selector("#preset-btn-challenge", state="visible", timeout=5000)

        # Click challenge preset (7)
        page.locator("#preset-btn-challenge").click()
        page.wait_for_timeout(300)

        # Streak in storage remains untouched (5)
        streak_raw = page.evaluate("() => localStorage.getItem('aiden_math_streak_v1')")
        assert json.loads(streak_raw)["currentStreak"] == 5

        # Stats remains untouched
        stats_raw = page.evaluate("() => localStorage.getItem('aiden_math_stats')")
        stats = json.loads(stats_raw)
        assert stats["+"]["levels"]["0"]["attempts"] == 10

        context.close()
        browser.close()


@pytest.mark.browser
def test_child_math_streak_indicator_narrow_viewport_layout(
    static_server: str,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        # Narrow mobile screen (360x740)
        context = browser.new_context(
            viewport={"width": 360, "height": 740},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )
        page = context.new_page()

        page.goto(f"{static_server}/domains/math/index.html")
        page.wait_for_selector("#question", state="visible", timeout=5000)

        streak_el = page.locator("#daily-goal-streak")
        expect(streak_el).to_be_visible()

        # Check core game controls are fully visible and not blocked
        question_el = page.locator("#question")
        expect(question_el).to_be_visible()

        answer_btns = page.locator(".answer-btn")
        expect(answer_btns.first).to_be_visible()
        expect(answer_btns.first).to_be_enabled()

        context.close()
        browser.close()
