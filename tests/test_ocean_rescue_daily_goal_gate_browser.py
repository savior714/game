import functools
import http.server
import threading
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def local_server():
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(ROOT)
    )
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        thread.join()


def _set_goal(page, *, completed, date_offset_days=0):
    page.evaluate(
        """({ completed, dateOffsetDays }) => {
          const date = new Date();
          date.setDate(date.getDate() + dateOffsetDays);
          const year = date.getFullYear();
          const month = String(date.getMonth() + 1).padStart(2, '0');
          const day = String(date.getDate()).padStart(2, '0');
          const dayStr = `${year}-${month}-${day}`;
          localStorage.setItem('aiden_math_daily_goal_v1', JSON.stringify({
            schemaVersion: 1,
            date: dayStr,
            targetCount: 5,
            currentCount: completed ? 5 : 0,
            completed,
            completedAt: completed ? Date.now() : null,
            rewardGranted: completed,
            rewardReceiptId: completed ? `math_daily_goal:${dayStr}:1` : null
          }));
        }""",
        {"completed": completed, "dateOffsetDays": date_offset_days},
    )


def _assert_locked(page, expected):
    page.reload(wait_until="domcontentloaded")
    assert page.locator("#ocean-rescue-card").get_attribute("data-locked") == expected


def test_ocean_rescue_gate_uses_today_daily_goal_state(local_server):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{local_server}/index.html", wait_until="domcontentloaded")
        page.evaluate("localStorage.clear()")
        _assert_locked(page, "true")

        _set_goal(page, completed=True)
        page.evaluate(
            "localStorage.setItem('study_rewards', JSON.stringify({gems: 2, youtube_minutes: 0}))"
        )
        _assert_locked(page, "false")

        page.evaluate("localStorage.clear()")
        _set_goal(page, completed=False)
        page.evaluate(
            """() => {
              localStorage.setItem('study_rewards', JSON.stringify({gems: 0, youtube_minutes: 30}));
              localStorage.setItem('study_youtube_free_time_session_v1', JSON.stringify({
                status: 'running',
                endsAt: Date.now() + 60_000
              }));
            }"""
        )
        _assert_locked(page, "true")

        page.evaluate("localStorage.clear()")
        _set_goal(page, completed=True, date_offset_days=-1)
        _assert_locked(page, "true")

        page.evaluate("localStorage.setItem('aiden_math_daily_goal_v1', '{bad json')")
        _assert_locked(page, "true")
        browser.close()


def test_ocean_rescue_source_has_no_second_free_time_gate():
    source = (ROOT / "domains/ocean-rescue/src/app.js").read_text(encoding="utf-8")
    assert "checkFreeTimeEntitlement" not in source
    assert "localStorage.getItem('study_rewards')" not in source
