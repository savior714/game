"""Focused browser contract for Math full 10-question session to clean restart transition."""

from __future__ import annotations

import http.server
import re
import socketserver
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright


REPO_ROOT = Path(__file__).resolve().parent.parent
MATH_URL = "/domains/math/index.html"
TOTAL_QUESTIONS = 10


class QuietHandler(http.server.SimpleHTTPRequestHandler):
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


def _play_full_10_questions_with_final_wrong(page: Page) -> str:
    """Plays 9 correct + 1 wrong question, asserts terminal wrong state, and proceeds to result."""
    page.wait_for_selector("#question", state="visible", timeout=5000)
    page.wait_for_selector(".answer-btn", state="visible", timeout=5000)

    for q_index in range(TOTAL_QUESTIONS - 1):
        expect(page.locator("#q-count")).to_have_text(str(q_index + 1))
        assert page.evaluate("answered") is False

        correct_answer = str(page.evaluate("answer"))
        assert correct_answer != "", "answer must be non-empty"

        exact_pattern = re.compile(rf"^{re.escape(correct_answer)}$")
        correct_btn = page.locator(".answer-btn").filter(has_text=exact_pattern).first
        correct_btn.click()

        page.wait_for_function("answered === true", timeout=5000)
        next_btn = page.locator("#next-btn")
        expect(next_btn).to_be_visible()
        next_btn.click()
        page.wait_for_function("answered === false", timeout=5000)

    # Q10 (final question): choose wrong answer
    expect(page.locator("#q-count")).to_have_text(str(TOTAL_QUESTIONS))
    assert page.evaluate("answered") is False

    correct_answer = str(page.evaluate("answer"))
    assert correct_answer != "", "answer must be non-empty"

    exact_pattern = re.compile(rf"^{re.escape(correct_answer)}$")
    wrong_btn = page.locator(".answer-btn").filter(has_not_text=exact_pattern).first
    wrong_btn.click()

    page.wait_for_function("answered === true", timeout=5000)
    assert page.evaluate("answered") is True
    assert page.evaluate("score") == 9

    # Assert terminal wrong state
    correct_btn = page.locator(".answer-btn").filter(has_text=exact_pattern).first
    expect(wrong_btn).to_have_class(re.compile(r"\bwrong\b"))
    expect(correct_btn).to_have_class(re.compile(r"\bcorrect\b"))

    feedback_el = page.locator("#feedback")
    expect(feedback_el).to_have_class("feedback-wrong")
    terminal_wrong_feedback = feedback_el.inner_text().strip()
    assert terminal_wrong_feedback != "", "Terminal wrong feedback text must be non-empty"

    next_btn = page.locator("#next-btn")
    expect(next_btn).to_be_visible()
    next_btn.click()

    page.wait_for_selector("#result-screen", state="visible", timeout=5000)
    return terminal_wrong_feedback


@pytest.mark.browser
@pytest.mark.parametrize("run_index", range(4))
def test_math_full_session_clean_restart_contract(
    static_server: str, run_index: int
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )
        page = context.new_page()

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

        page.goto(f"{static_server}{MATH_URL}")

        terminal_wrong_feedback = _play_full_10_questions_with_final_wrong(page)

        game_area = page.locator("#game-area")
        result_screen = page.locator("#result-screen")
        restart_btn = page.locator("#restart-btn")

        expect(game_area).to_be_hidden()
        expect(result_screen).to_be_visible()
        expect(restart_btn).to_be_visible()

        assert page.evaluate("score") == 9
        result_msg = page.locator("#result-msg").inner_text()
        assert "9개" in result_msg

        # Install test-only instrumentation before restart click
        page.evaluate("""() => {
            window.__askQuestionCallCount = 0;
            window.__startTimerCallCount = 0;
            const origAskQuestion = window.askQuestion;
            window.askQuestion = function(...args) {
                window.__askQuestionCallCount++;
                return origAskQuestion.apply(this, args);
            };
            const origStartTimer = window.startTimer;
            window.startTimer = function(...args) {
                window.__startTimerCallCount++;
                return origStartTimer.apply(this, args);
            };
        }""")

        restart_btn.click()

        expect(result_screen).to_be_hidden()
        expect(game_area).to_be_visible()

        page.wait_for_selector(".answer-btn", state="visible", timeout=5000)

        # State evaluations
        assert page.evaluate("currentQ") == 0
        assert page.evaluate("score") == 0
        assert page.evaluate("answered") is False

        # DOM evaluations
        expect(page.locator("#q-count")).to_have_text("1")
        expect(page.locator("#q-score")).to_have_text("0")
        expect(page.locator("#next-btn")).to_be_hidden()

        answer_btns = page.locator(".answer-btn")
        expect(answer_btns).to_have_count(4)
        expect(page.locator(".answer-btn.correct")).to_have_count(0)
        expect(page.locator(".answer-btn.wrong")).to_have_count(0)

        # Feedback evaluation
        feedback_class = page.evaluate("document.getElementById('feedback').className")
        assert "feedback-correct" not in feedback_class
        assert "feedback-wrong" not in feedback_class

        current_feedback_text = page.locator("#feedback").inner_text().strip()
        assert current_feedback_text != terminal_wrong_feedback, (
            f"Terminal wrong feedback leaked to new question: {terminal_wrong_feedback}"
        )

        new_q_text = page.locator("#question").inner_text().strip()
        assert new_q_text != "", "New question text must be non-empty"

        # Answer button interactivity
        first_btn = answer_btns.first
        expect(first_btn).to_be_enabled()

        # Instrumentation exact calls evaluation
        ask_count = page.evaluate("window.__askQuestionCallCount")
        assert ask_count == 1, f"Expected askQuestion call count to be 1, got {ask_count}"

        timer_start_count = page.evaluate("window.__startTimerCallCount")
        assert (
            timer_start_count == 1
        ), f"Expected startTimer call count to be 1, got {timer_start_count}"

        # Timer single ownership check
        timer_active = page.evaluate(
            "typeof timerInterval !== 'undefined' ? (timerInterval ? 1 : 0) : 0"
        )
        assert timer_active == 1, f"Expected exactly 1 active timer interval, got {timer_active}"

        # Stability check for single-click restart invocation
        page.wait_for_timeout(1500)
        stable_q_text = page.locator("#question").inner_text().strip()
        assert stable_q_text == new_q_text, (
            "Question text changed after restart settled — startGame likely called more than once"
        )

        stable_timer_active = page.evaluate(
            "typeof timerInterval !== 'undefined' ? (timerInterval ? 1 : 0) : 0"
        )
        assert stable_timer_active == 1, (
            f"Expected timer interval count to stay 1, got {stable_timer_active}"
        )

        assert page_errors == [], f"Page errors found: {page_errors}"
        assert console_errors == [], f"Console errors found: {console_errors}"
        assert failed_requests == [], f"Failed requests found: {failed_requests}"

        context.close()
        browser.close()
