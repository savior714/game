"""Browser regression contract: wrong-answer reinforcement must not reissue the same question immediately."""

from __future__ import annotations

import http.server
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright


REPO_ROOT = Path(__file__).resolve().parent.parent
MATH_URL = "/domains/math/index.html"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
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


def _get_question_key(page: Page) -> str:
    """Return the recentQuestions-style key for the current question."""
    return page.evaluate(
        """
        () => {
          const q = currentQData;
          if (!q) return '';
          const pair = [q.a, q.b].sort((a, b) => a - b);
          return pair.join(',') + q.op;
        }
        """
    )


def _get_wrong_answer_index(page: Page, correct_answer: str) -> int:
    index = page.evaluate(
        "expected => Array.from(document.querySelectorAll('.answer-btn'))"
        ".findIndex(button => button.textContent.trim() !== expected)",
        correct_answer,
    )
    assert index >= 0, "Math question must expose at least one wrong choice"
    return index


@pytest.mark.browser
def test_wrong_answer_next_question_is_different(static_server: str, page: Page) -> None:
    """After a wrong answer, pressing next must show a different problem (not immediate reinforcement)."""
    page_errors: list[str] = []
    console_errors: list[str] = []

    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on(
        "console",
        lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
    )

    page.goto(f"{static_server}{MATH_URL}")
    page.wait_for_selector(".answer-btn", state="visible", timeout=5000)

    answer_buttons = page.locator(".answer-btn")
    next_button = page.locator("#next-btn")
    feedback = page.locator("#feedback")

    expect(answer_buttons).to_have_count(4)
    expect(next_button).to_be_hidden()

    # Record the current question key before answering
    first_key = _get_question_key(page)
    assert first_key, "Math question must have a valid key"

    # Answer incorrectly
    correct_answer = page.evaluate("String(answer)")
    wrong_index = _get_wrong_answer_index(page, correct_answer)
    answer_buttons.nth(wrong_index).click()

    page.wait_for_function("answered === true", timeout=5000)
    expect(next_button).to_be_visible()
    expect(page.locator(".answer-btn.wrong")).to_have_count(1)
    expect(feedback).to_have_class("feedback-wrong")

    # Press next — this is where the bug manifests: same question re-issued
    next_button.click()

    page.wait_for_function("answered === false", timeout=5000)
    expect(next_button).to_be_hidden()

    # Question counter must have advanced by exactly 1
    assert page.evaluate("currentQ") == 1, "Question counter must advance by 1 after wrong answer"
    expect(page.locator("#q-count")).to_have_text("2")

    # The new question must NOT be the same as the one we just got wrong
    second_key = _get_question_key(page)
    assert second_key, "New question must have a valid key"
    assert second_key != first_key, (
        f"Reinforcement reissued the same question immediately: {first_key} -> {second_key}"
    )

    # State must be fully reset for the new question
    expect(page.locator(".answer-btn.wrong")).to_have_count(0)
    expect(page.locator(".answer-btn.correct")).to_have_count(0)

    assert page_errors == [], f"page errors: {page_errors}"
    assert console_errors == [], f"console errors: {console_errors}"


@pytest.mark.browser
def test_reinforcement_can_reappear_after_one_different_question(static_server: str, page: Page) -> None:
    """A wrong-answer problem should be eligible for reinforcement again after at least one other question."""
    page_errors: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))

    page.goto(f"{static_server}{MATH_URL}")
    page.wait_for_selector(".answer-btn", state="visible", timeout=5000)

    answer_buttons = page.locator(".answer-btn")
    next_button = page.locator("#next-btn")

    # Get and answer the first question correctly to advance
    correct_answer = page.evaluate("String(answer)")
    page.get_by_role("button", name=correct_answer, exact=True).click()
    page.wait_for_function("answered === true", timeout=5000)
    expect(next_button).to_be_visible()

    # Advance to question 2
    next_button.click()
    page.wait_for_function("answered === false", timeout=5000)

    # Now answer question 2 incorrectly to create a wrong pattern
    correct_answer = page.evaluate("String(answer)")
    wrong_index = _get_wrong_answer_index(page, correct_answer)
    answer_buttons.nth(wrong_index).click()

    page.wait_for_function("answered === true", timeout=5000)
    expect(next_button).to_be_visible()

    # Record the wrong question key
    wrong_key = _get_question_key(page)
    assert wrong_key

    # Answer correctly and advance past the reinforcement window
    correct_answer = page.evaluate("String(answer)")
    page.get_by_role("button", name=correct_answer, exact=True).click()
    page.wait_for_function("answered === true", timeout=5000)
    next_button.click()
    page.wait_for_function("answered === false", timeout=5000)

    # The reinforcement queue should now allow the wrong question to reappear
    # (it's no longer in recentQuestions, and wrongPatterns has it)
    assert page.evaluate("wrongPatterns.length > 0"), "Wrong patterns should be tracked"

    assert page_errors == [], f"page errors: {page_errors}"
