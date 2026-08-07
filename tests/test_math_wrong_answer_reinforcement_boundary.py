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
def test_reinforcement_flow_a_to_b_to_a(static_server: str, page: Page) -> None:
    """A wrong-answer problem must reappear on screen after exactly one different question completes.

    Reinforcement questions skip the recent-10 dedup and only reject the immediate previous question.
    This test proves the A → B → A flow through actual generateQuestion() → askQuestion(),
    not by directly writing currentQData.
    """
    page_errors: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))

    page.goto(f"{static_server}{MATH_URL}")
    page.wait_for_selector(".answer-btn", state="visible", timeout=5000)

    answer_buttons = page.locator(".answer-btn")
    next_button = page.locator("#next-btn")

    # --- Force initial question to be A (2 + 3 = 5) via askQuestion() ---
    page.evaluate(
        """
        () => {
          wrongPatterns = [
            { op: '+', level: 0, a: 2, b: 3, tag: 'add_unit_2_3' },
          ];
          recentQuestions = [];
          _lastQuestionKey = '';
          Math.random = () => 0.4;
          askQuestion();
        }
        """
    )

    a_key = _get_question_key(page)
    assert a_key == "2,3+", f"Initial question must be pre-seeded A (2+3), got {a_key}"

    # --- Q1: answer A incorrectly ---
    correct_answer = page.evaluate("String(answer)")
    wrong_index = _get_wrong_answer_index(page, correct_answer)
    answer_buttons.nth(wrong_index).click()

    page.wait_for_function("answered === true", timeout=5000)
    expect(next_button).to_be_visible()

    # --- Set Math.random to non-reinforcement (0.8) so Q2 becomes B (different from A) ---
    page.evaluate("Math.random = () => 0.8;")

    # --- Q2: advance → B appears (guaranteed different from A="2,3+") ---
    next_button.click()
    page.wait_for_function("answered === false", timeout=5000)

    b_key = _get_question_key(page)
    assert b_key != "2,3+", f"B must differ from A (2,3+): got {b_key}"

    # --- Q2: answer B correctly ---
    correct_answer = page.evaluate("String(answer)")
    page.locator(f".answer-btn:text-is('{correct_answer}')").click()
    page.wait_for_function("answered === true", timeout=5000)
    expect(next_button).to_be_visible()

    # --- Clear recentQuestions, normalize wrongPatterns to ONLY A,
    #     seed Math.random to force reinforcement path (0.4) ---
    page.evaluate(
        """
        () => {
          recentQuestions = [];
          wrongPatterns = [
            { op: '+', level: 0, a: 2, b: 3, tag: 'add_unit_2_3' },
          ];
          Math.random = () => 0.4;
        }
        """
    )

    # --- Advance: this triggers generateQuestion() → askQuestion() and should show A ---
    next_button.click()
    page.wait_for_function("answered === false", timeout=5000)

    # --- Verify A (2+3) appears on screen via actual askQuestion() rendering ---
    displayed_key = _get_question_key(page)
    assert displayed_key == "2,3+", (
        f"Reinforcement must show pre-seeded A (2+3) through generateQuestion(): expected 2,3+, got {displayed_key}"
    )

    # Verify the question DOM matches A's operands (proves generateQuestion → askQuestion path)
    question_text = page.locator("#question").inner_text().strip()
    assert "2" in question_text and "3" in question_text, (
        f"Question DOM must show A's operands (2 + 3), got: {question_text}"
    )

    assert page_errors == [], f"page errors: {page_errors}"


@pytest.mark.browser
def test_fallback_does_not_repeat_immediate_previous_question(static_server: str, page: Page) -> None:
    """When reinforcement candidates are exhausted, fallback must not return the immediate previous question.

    This verifies the bounded fallback path in generateQuestion() rejects _lastQuestionKey.
    """
    page_errors: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))

    page.goto(f"{static_server}{MATH_URL}")
    page.wait_for_selector(".answer-btn", state="visible", timeout=5000)

    answer_buttons = page.locator(".answer-btn")
    next_button = page.locator("#next-btn")

    # --- Q1: answer incorrectly → recorded as A ---
    correct_answer = page.evaluate("String(answer)")
    wrong_index = _get_wrong_answer_index(page, correct_answer)
    answer_buttons.nth(wrong_index).click()

    page.wait_for_function("answered === true", timeout=5000)
    expect(next_button).to_be_visible()

    a_key = _get_question_key(page)
    assert a_key, "Question A must have a valid key"

    # --- Q2: advance → B appears, answer correctly ---
    next_button.click()
    page.wait_for_function("answered === false", timeout=5000)

    b_key = _get_question_key(page)
    assert b_key != a_key, f"B must differ from A: {a_key} -> {b_key}"

    correct_answer = page.evaluate("String(answer)")
    page.locator(f".answer-btn:text-is('{correct_answer}')").click()
    page.wait_for_function("answered === true", timeout=5000)
    expect(next_button).to_be_visible()

    # --- Force fallback path: only A in wrongPatterns, clear recentQuestions ---
    page.evaluate(
        """
        () => {
          recentQuestions = [];
          wrongPatterns = [
            { op: '+', level: 0, a: 2, b: 3, tag: 'add_unit_2_3' },
          ];
        }
        """
    )

    # Advance — generateQuestion() fallback must not return A (same as _lastQuestionKey)
    next_button.click()
    page.wait_for_function("answered === false", timeout=5000)

    displayed_key = _get_question_key(page)
    assert displayed_key != a_key, (
        f"Fallback must not repeat immediate previous question A: {a_key} -> {displayed_key}"
    )

    assert page_errors == [], f"page errors: {page_errors}"
