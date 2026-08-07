"""Browser contract for English typing answer state reset between questions."""

from __future__ import annotations

import http.server
import socketserver
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
ENGLISH_URL = "/domains/english/index.html"
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


def _setup_typing_game(
    static_server: str, page: Page
) -> tuple[list[str], list[str], list[str]]:
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

    return page_errors, console_errors, failed_requests


def _verify_initial_typing_state(page: Page) -> None:
    typing_input = page.locator("#typing-input")
    typing_submit = page.locator("#typing-submit")
    next_button = page.locator("#next-btn")

    assert page.evaluate("currentQ") == 0
    assert page.evaluate("score") == 0
    assert page.evaluate("answered") is False
    expect(page.locator("#q-count")).to_have_text("1")
    expect(page.locator("#q-score")).to_have_text("0")

    expect(typing_input).to_be_visible()
    expect(typing_input).to_be_enabled()
    expect(typing_input).to_have_value("")
    expect(typing_submit).to_be_visible()
    expect(next_button).to_be_hidden()

    assert not page.evaluate(
        "document.getElementById('typing-input').classList.contains('correct')"
    )
    assert not page.evaluate(
        "document.getElementById('typing-input').classList.contains('wrong')"
    )


@pytest.mark.browser
@pytest.mark.parametrize("repeat_run", REPEAT_RUNS)
def test_english_typing_correct_answer_resets_on_next_question(
    static_server: str,
    page: Page,
    repeat_run: int,
) -> None:
    del repeat_run
    page_errors, console_errors, failed_requests = _setup_typing_game(
        static_server, page
    )
    _verify_initial_typing_state(page)

    typing_input = page.locator("#typing-input")
    typing_submit = page.locator("#typing-submit")
    next_button = page.locator("#next-btn")
    feedback = page.locator("#feedback")

    correct_answer = page.evaluate("String(answer)")
    typing_input.fill(correct_answer)
    typing_submit.click()

    page.wait_for_function("answered === true", timeout=5000)
    assert page.evaluate("answered") is True
    assert page.evaluate("score") == 1
    expect(page.locator("#q-score")).to_have_text("1")
    expect(page.locator("#q-count")).to_have_text("1")

    expect(typing_input).to_be_disabled()
    expect(typing_input).to_have_class("typing-input correct")
    assert not page.evaluate(
        "document.getElementById('typing-input').classList.contains('wrong')"
    )
    expect(feedback).to_have_class("feedback-correct")
    previous_feedback = feedback.inner_text().strip()
    assert previous_feedback != ""
    expect(next_button).to_be_visible()

    next_button.click()

    page.wait_for_function("currentQ === 1 && answered === false", timeout=5000)
    assert page.evaluate("currentQ") == 1
    assert page.evaluate("answered") is False
    assert page.evaluate("score") == 1
    expect(page.locator("#q-count")).to_have_text("2")
    expect(page.locator("#q-score")).to_have_text("1")

    new_input = page.locator("#typing-input")
    expect(new_input).to_be_visible()
    expect(new_input).to_be_enabled()
    expect(new_input).to_have_value("")

    assert not page.evaluate(
        "document.getElementById('typing-input').classList.contains('correct')"
    )
    assert not page.evaluate(
        "document.getElementById('typing-input').classList.contains('wrong')"
    )
    assert feedback.evaluate(
        "element => !element.classList.contains('feedback-correct')"
    )
    assert feedback.inner_text().strip() != previous_feedback
    expect(next_button).to_be_hidden()

    assert page_errors == [], f"page errors: {page_errors}"
    assert console_errors == [], f"console errors: {console_errors}"
    assert failed_requests == [], f"failed requests: {failed_requests}"


@pytest.mark.browser
@pytest.mark.parametrize("repeat_run", REPEAT_RUNS)
def test_english_typing_wrong_answer_resets_on_next_question(
    static_server: str,
    page: Page,
    repeat_run: int,
) -> None:
    del repeat_run
    page_errors, console_errors, failed_requests = _setup_typing_game(
        static_server, page
    )
    _verify_initial_typing_state(page)

    typing_input = page.locator("#typing-input")
    typing_submit = page.locator("#typing-submit")
    next_button = page.locator("#next-btn")
    feedback = page.locator("#feedback")

    correct_answer = page.evaluate("String(answer)")
    wrong_answer = correct_answer + "_invalid_wrong"
    typing_input.fill(wrong_answer)
    typing_submit.click()

    page.wait_for_function("answered === true", timeout=5000)
    assert page.evaluate("answered") is True
    assert page.evaluate("score") == 0
    expect(page.locator("#q-score")).to_have_text("0")
    expect(page.locator("#q-count")).to_have_text("1")

    expect(typing_input).to_be_disabled()
    expect(typing_input).to_have_class("typing-input wrong")
    assert not page.evaluate(
        "document.getElementById('typing-input').classList.contains('correct')"
    )
    expect(feedback).to_have_class("feedback-wrong")
    previous_feedback = feedback.inner_text().strip()
    assert previous_feedback != ""
    expect(next_button).to_be_visible()

    next_button.click()

    page.wait_for_function("currentQ === 1 && answered === false", timeout=5000)
    assert page.evaluate("currentQ") == 1
    assert page.evaluate("answered") is False
    assert page.evaluate("score") == 0
    expect(page.locator("#q-count")).to_have_text("2")
    expect(page.locator("#q-score")).to_have_text("0")

    new_input = page.locator("#typing-input")
    expect(new_input).to_be_visible()
    expect(new_input).to_be_enabled()
    expect(new_input).to_have_value("")

    assert not page.evaluate(
        "document.getElementById('typing-input').classList.contains('correct')"
    )
    assert not page.evaluate(
        "document.getElementById('typing-input').classList.contains('wrong')"
    )
    assert feedback.evaluate("element => !element.classList.contains('feedback-wrong')")
    assert feedback.inner_text().strip() != previous_feedback
    expect(next_button).to_be_hidden()

    assert page_errors == [], f"page errors: {page_errors}"
    assert console_errors == [], f"console errors: {console_errors}"
    assert failed_requests == [], f"failed requests: {failed_requests}"
