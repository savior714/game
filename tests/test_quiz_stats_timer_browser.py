"""Stats dialogs suspend active quiz time, not learning outcomes or stopped timers."""

from __future__ import annotations

import http.server
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SUBJECTS = ["math", "korean", "english", "science"]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format: str, *args):
        pass


@pytest.fixture(scope="module")
def static_server():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.fixture
def quiz_page(static_server: str, request: pytest.FixtureRequest):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )
        page = context.new_page()
        errors: list[str] = []
        failures: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("requestfailed", lambda req: failures.append(req.url))
        now = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)
        page.clock.install(time=now)
        page.clock.pause_at(now + timedelta(seconds=1))
        try:
            page.goto(f"{static_server}/domains/{request.param}/index.html")
            expect(page.locator("#question")).not_to_be_empty()
            yield page
            assert errors == []
            # Optional font/auth CDNs are outside this local-first timer contract.
            # Keep their failures in the test report; local runtime assets must load.
            request.node.user_properties.append(("request_failures", failures))
            assert [url for url in failures if url.startswith(static_server)] == []
        finally:
            context.close()
            browser.close()


def close_stats(page: Page, method: str) -> None:
    if method == "escape":
        page.keyboard.press("Escape")
    elif method == "backdrop":
        page.locator("#stats-modal").click(position={"x": 5, "y": 5})
    else:
        page.locator("#close-stats-btn").click()
    expect(page.locator("#stats-modal")).to_be_hidden()
    expect(page.locator("#stats-btn")).to_be_focused()


@pytest.mark.browser
@pytest.mark.parametrize("quiz_page", SUBJECTS, indirect=True)
@pytest.mark.parametrize("method", ["button", "escape", "backdrop"])
def test_stats_preserve_remaining_time_and_resume_once(quiz_page: Page, method: str):
    page = quiz_page
    page.clock.run_for(2000)
    remaining = page.evaluate("timeLeft")
    assert remaining == page.evaluate("TIME_LIMIT - 2")
    question = page.locator("#question").inner_text()

    page.locator("#stats-btn").click()
    expect(page.locator("#close-stats-btn")).to_be_focused()
    page.keyboard.press("Shift+Tab")
    expect(page.locator("#reset-stats-btn")).to_be_focused()
    page.keyboard.press("Tab")
    expect(page.locator("#close-stats-btn")).to_be_focused()
    assert page.locator("#main-area").evaluate("element => element.inert")
    page.clock.run_for(121000)
    assert page.evaluate("timeLeft") == remaining
    assert page.evaluate("answered") is False
    expect(page.locator("#next-btn")).to_be_hidden()
    assert page.locator("#question").inner_text() == question

    close_stats(page, method)
    assert not page.locator("#main-area").evaluate("element => element.inert")
    page.clock.run_for(1000)
    assert page.evaluate("timeLeft") == remaining - 1

    # Reopening must not reset the budget or create another interval.
    page.locator("#stats-btn").click()
    page.clock.run_for(5000)
    assert page.evaluate("timeLeft") == remaining - 1
    close_stats(page, method)
    page.clock.run_for(int((remaining - 2) * 1000))
    expect(page.locator("#next-btn")).to_be_hidden()
    page.clock.run_for(1000)
    expect(page.locator("#feedback")).to_contain_text("시간 초과")
    expect(page.locator("#next-btn")).to_be_visible()
    assert page.evaluate("timeLeft") == 0

    page.locator("#stats-btn").click()
    close_stats(page, method)
    page.clock.run_for(5000)
    assert page.evaluate("timerInterval") is None
    page.locator("#next-btn").click()
    expect(page.locator("#q-count")).to_have_text("2")
    assert page.evaluate("timeLeft") == page.evaluate("TIME_LIMIT")


@pytest.mark.browser
@pytest.mark.parametrize("quiz_page", ["math"], indirect=True)
@pytest.mark.parametrize("correct", [True, False])
def test_stats_after_answer_never_restart_timer(quiz_page: Page, correct: bool):
    page = quiz_page
    page.clock.run_for(3000)
    answer = page.evaluate("answer")
    buttons = page.locator(".answer-btn")
    if correct:
        page.get_by_role("button", name=str(answer), exact=True).click()
    else:
        next(
            button for button in buttons.all() if button.inner_text() != str(answer)
        ).click()
    expect(page.locator("#next-btn")).to_be_visible()
    before = page.evaluate("({ timeLeft, score, answered, stats })")
    for method in ["button", "escape", "backdrop"]:
        page.locator("#stats-btn").click()
        page.clock.run_for(121000)
        close_stats(page, method)
        page.clock.run_for(121000)
        assert page.evaluate("({ timeLeft, score, answered, stats })") == before
        assert page.evaluate("timerInterval") is None


@pytest.mark.browser
@pytest.mark.parametrize("quiz_page", ["english"], indirect=True)
def test_stats_do_not_start_an_untimed_typing_question(quiz_page: Page):
    page = quiz_page
    # Select the next content variant deterministically; transition via real input.
    page.evaluate("window.pickQuestionType = () => 'typing'")
    page.clock.run_for(121000)
    page.locator("#next-btn").click()
    expect(page.locator("#typing-input")).to_be_visible()
    expect(page.locator("#timer-text")).to_have_text("♾️")
    assert page.evaluate("timerInterval") is None
    for method in ["button", "escape", "backdrop"]:
        page.locator("#stats-btn").click()
        page.clock.run_for(121000)
        close_stats(page, method)
        page.clock.run_for(121000)
        assert page.evaluate("answered") is False
        assert page.evaluate("timerInterval") is None
        expect(page.locator("#timer-text")).to_have_text("♾️")
    page.locator("#typing-input").fill(page.evaluate("answer"))
    page.locator("#typing-input").press("Enter")
    expect(page.locator("#next-btn")).to_be_visible()
    expect(page.locator("#q-score")).to_have_text("1")
