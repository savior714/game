"""Focused browser contracts for math progression and static controls."""

from __future__ import annotations

import http.server
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Dialog, Page, expect, sync_playwright


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
def math_page(static_server: str):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )
        page = context.new_page()
        page_errors: list[str] = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.goto(f"{static_server}/domains/math/index.html")
        page.wait_for_selector("#question", state="visible", timeout=5000)

        yield page, page_errors

        context.close()
        browser.close()


@pytest.mark.browser
def test_next_button_advances_exactly_one_question(
    math_page: tuple[Page, list[str]],
) -> None:
    page, page_errors = math_page
    question = page.locator("#question")
    count = page.locator("#q-count")
    next_button = page.locator("#next-btn")

    first_question = question.inner_text().strip()
    assert first_question
    expect(count).to_have_text("1")

    page.locator(".answer-btn").first.click()
    expect(next_button).to_be_visible()

    next_button.click()

    expect(count).to_have_text("2")
    expect(next_button).to_be_hidden()
    assert question.inner_text().strip() != first_question
    assert page_errors == []


@pytest.mark.browser
def test_stats_controls_open_close_reset_and_backdrop(
    math_page: tuple[Page, list[str]],
) -> None:
    page, page_errors = math_page
    modal = page.locator("#stats-modal")
    attempts = page.locator("#stats-tbody tr").first.locator("td").nth(1)

    page.evaluate(
        """
        stats = emptyStats();
        stats['+'].levels[0].attempts = 3;
        stats['+'].levels[0].correct = 2;
        stats['+'].levels[0].totalTime = 9;
        saveStats();
        bindStaticControls();
        """
    )

    expect(page.locator("#stats-btn")).to_have_attribute(
        "data-math-control-bound", "true"
    )
    page.locator("#stats-btn").click()
    expect(modal).to_be_visible()
    expect(page.locator("#stats-tbody tr")).to_have_count(3)
    expect(attempts).to_have_text("3")

    page.locator("#close-stats-btn").click()
    expect(modal).to_be_hidden()

    page.locator("#stats-btn").click()
    expect(modal).to_be_visible()
    modal.click(position={"x": 5, "y": 5})
    expect(modal).to_be_hidden()

    page.locator("#stats-btn").click()
    expect(modal).to_be_visible()

    dialog_messages: list[str] = []

    def accept_reset(dialog: Dialog) -> None:
        dialog_messages.append(dialog.message)
        dialog.accept()

    page.once("dialog", accept_reset)
    page.locator("#reset-stats-btn").click()

    expect(attempts).to_have_text("0")
    assert dialog_messages == ["누적 기록을 모두 지울까요?"]
    stored_attempts = page.evaluate(
        "JSON.parse(localStorage.getItem(STATS_KEY))['+'].levels[0].attempts"
    )
    assert stored_attempts == 0
    assert page_errors == []


@pytest.mark.browser
def test_restart_button_starts_a_fresh_session(
    math_page: tuple[Page, list[str]],
) -> None:
    page, page_errors = math_page
    game_area = page.locator("#game-area")
    result_screen = page.locator("#result-screen")

    page.evaluate(
        """
        score = 7;
        document.getElementById('q-score').textContent = '7';
        showResult();
        bindStaticControls();
        """
    )

    expect(game_area).to_be_hidden()
    expect(result_screen).to_be_visible()
    expect(page.locator("#restart-btn")).to_have_attribute(
        "data-math-control-bound", "true"
    )

    page.locator("#restart-btn").click()

    expect(result_screen).to_be_hidden()
    expect(game_area).to_be_visible()
    expect(page.locator("#q-count")).to_have_text("1")
    expect(page.locator("#q-score")).to_have_text("0")
    expect(page.locator("#next-btn")).to_be_hidden()
    assert page_errors == []
