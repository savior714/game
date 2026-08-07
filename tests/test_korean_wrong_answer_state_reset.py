"""Browser contract for Korean wrong-answer state reset between questions."""

from __future__ import annotations

import http.server
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright


REPO_ROOT = Path(__file__).resolve().parent.parent
KOREAN_URL = "/domains/korean/index.html"
REPEAT_RUNS = range(4)


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


def _wait_for_question(page: Page) -> None:
    page.wait_for_function(
        "window.WORDS && Object.keys(window.WORDS).length > 0",
        timeout=10000,
    )
    page.wait_for_selector("#question", state="visible", timeout=5000)
    page.wait_for_function(
        "document.getElementById('question').textContent.trim().length > 0",
        timeout=5000,
    )
    page.wait_for_selector(".answer-btn", state="visible", timeout=5000)


def _wrong_answer_index(page: Page, current_answer: str) -> int:
    index = page.evaluate(
        """
        expected => Array.from(document.querySelectorAll('.answer-btn'))
          .findIndex(button => button.textContent.trim() !== expected)
        """,
        current_answer,
    )
    assert index >= 0, "Korean question must expose at least one wrong choice"
    return index


@pytest.mark.browser
@pytest.mark.parametrize("repeat_run", REPEAT_RUNS)
def test_wrong_answer_state_resets_on_next_question(
    static_server: str,
    page: Page,
    repeat_run: int,
) -> None:
    del repeat_run
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

    page.goto(f"{static_server}{KOREAN_URL}")
    _wait_for_question(page)

    answer_buttons = page.locator(".answer-btn")
    feedback = page.locator("#feedback")
    next_button = page.locator("#next-btn")

    expect(answer_buttons.first).to_be_visible()
    expect(next_button).to_be_hidden()
    assert page.evaluate("currentQ") == 0
    assert page.evaluate("score") == 0
    assert page.evaluate("answered") is False
    expect(page.locator("#q-count")).to_have_text("1")
    expect(page.locator("#q-score")).to_have_text("0")

    current_answer = page.evaluate("String(answer)")
    wrong_button = answer_buttons.nth(_wrong_answer_index(page, current_answer))
    wrong_button.click()

    page.wait_for_function("answered === true", timeout=5000)
    expect(next_button).to_be_visible()
    assert page.evaluate("currentQ") == 0
    assert page.evaluate("score") == 0
    expect(page.locator("#q-count")).to_have_text("1")
    expect(page.locator("#q-score")).to_have_text("0")

    expect(wrong_button).to_have_class("answer-btn wrong")
    expect(page.locator(".answer-btn.wrong")).to_have_count(1)
    expect(page.locator(".answer-btn.correct")).to_have_count(1)
    expect(feedback).to_have_class("feedback-wrong")

    previous_feedback = feedback.inner_text().strip()
    assert previous_feedback, "Feedback text must not be empty on wrong answer"

    next_button.click()

    page.wait_for_function("currentQ === 1 && answered === false", timeout=5000)
    assert page.evaluate("score") == 0
    expect(page.locator("#q-count")).to_have_text("2")
    expect(page.locator("#q-score")).to_have_text("0")
    expect(next_button).to_be_hidden()
    expect(page.locator(".answer-btn.wrong")).to_have_count(0)
    expect(page.locator(".answer-btn.correct")).to_have_count(0)

    assert feedback.evaluate("element => !element.classList.contains('feedback-wrong')")
    assert feedback.inner_text().strip() != previous_feedback

    question_text = page.evaluate(
        "(document.getElementById('question').textContent || '').trim()"
    )
    assert question_text != "", "New question text must not be empty"
    expect(answer_buttons.first).to_be_visible()

    # Verify next click advances currentQ exactly +1 to 1
    answer_buttons.first.click()
    page.wait_for_function("answered === true", timeout=5000)
    expect(next_button).to_be_visible()
    assert page.evaluate("currentQ") == 1

    assert page_errors == [], f"page errors: {page_errors}"
    assert console_errors == [], f"console errors: {console_errors}"
    assert failed_requests == [], f"failed requests: {failed_requests}"
