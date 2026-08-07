"""Focused browser test for English typing 10-question completion -> result screen -> clean restart state."""

from __future__ import annotations

import http.server
import socketserver
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
ENGLISH_URL = "/domains/english/index.html"
TOTAL_QUESTIONS = 10
REPEAT_RUNS = range(4)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Serve the repository root without request-log noise."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def log_message(self, format, *args):  # noqa: A002
        pass


@pytest.fixture(scope="module")
def static_server():
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("127.0.0.1", 0), QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.server_address
    yield f"http://{host}:{port}"

    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )
        browser_page = context.new_page()
        yield browser_page
        context.close()
        browser.close()


def run_typing_full_session_and_restart(static_server: str, page: Page) -> None:
    page_errors: list[str] = []
    console_errors: list[str] = []
    failed_requests: list[str] = []

    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on(
        "console",
        lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on(
        "requestfailed",
        lambda req: failed_requests.append(f"{req.url} {req.failure}"),
    )

    page.goto(f"{static_server}{ENGLISH_URL}")
    page.wait_for_selector("#game-area", state="visible", timeout=5000)

    page.evaluate("() => { window.pickQuestionType = () => 'typing'; }")
    page.evaluate("() => { if (typeof startGame === 'function') startGame(); }")
    page.wait_for_selector("#typing-input", state="visible", timeout=5000)

    previous_feedback = ""

    for q_index in range(TOTAL_QUESTIONS):
        typing_input = page.locator("#typing-input")
        typing_submit = page.locator("#typing-submit")
        next_btn = page.locator("#next-btn")
        feedback = page.locator("#feedback")

        expect(typing_input).to_be_visible(timeout=5000)
        expect(typing_input).to_be_enabled()
        assert page.evaluate("answered") is False

        correct_answer = page.evaluate("String(answer)")
        typing_input.fill(correct_answer)
        typing_submit.click()

        page.wait_for_function("answered === true", timeout=5000)
        expect(next_btn).to_be_visible(timeout=5000)

        is_last = q_index == TOTAL_QUESTIONS - 1
        if is_last:
            assert page.evaluate("answered") is True
            expect(typing_input).to_be_disabled()
            assert page.evaluate(
                "document.getElementById('typing-input').classList.contains('correct')"
            )
            expect(feedback).to_have_class("feedback-correct")
            previous_feedback = feedback.inner_text().strip()
            assert previous_feedback != ""
            expect(next_btn).to_be_visible()

            next_btn.click()
            page.wait_for_selector("#result-screen", state="visible", timeout=5000)
        else:
            next_btn.click()
            page.wait_for_function("answered === false", timeout=5000)

    restart_btn = page.locator("#restart-btn")
    expect(restart_btn).to_be_visible()
    restart_btn.click()

    page.wait_for_selector("#game-area", state="visible", timeout=5000)

    assert page.evaluate("currentQ") == 0
    assert page.evaluate("score") == 0
    assert page.evaluate("answered") is False
    expect(page.locator("#q-count")).to_have_text("1")
    expect(page.locator("#q-score")).to_have_text("0")
    expect(page.locator("#result-screen")).to_be_hidden()

    new_input = page.locator("#typing-input")
    expect(new_input).to_be_visible(timeout=5000)
    expect(new_input).to_be_enabled()
    expect(new_input).to_have_value("")

    assert not page.evaluate(
        "document.getElementById('typing-input').classList.contains('correct')"
    )
    assert not page.evaluate(
        "document.getElementById('typing-input').classList.contains('wrong')"
    )
    assert page.locator("#feedback").inner_text().strip() != previous_feedback
    assert not page.evaluate(
        "document.getElementById('feedback').classList.contains('feedback-correct')"
    )
    assert not page.evaluate(
        "document.getElementById('feedback').classList.contains('feedback-wrong')"
    )
    expect(page.locator("#next-btn")).to_be_hidden()

    assert page_errors == [], f"page errors: {page_errors}"
    assert console_errors == [], f"console errors: {console_errors}"
    assert failed_requests == [], f"failed requests: {failed_requests}"


@pytest.mark.browser
@pytest.mark.parametrize("repeat_run", REPEAT_RUNS)
def test_english_typing_restart_progression(
    static_server: str, page: Page, repeat_run: int
) -> None:
    del repeat_run
    run_typing_full_session_and_restart(static_server, page)
