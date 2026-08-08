"""Focused browser regression for Science quiz restart button binding."""

from __future__ import annotations

import http.server
import socketserver
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright


REPO_ROOT = Path(__file__).resolve().parent.parent
SCIENCE_URL = "/domains/science/index.html"
TOTAL_QUESTIONS = 10
REPEAT_RUNS = range(4)


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


def _play_full_session(page: Page) -> None:
    for q_index in range(TOTAL_QUESTIONS):
        page.wait_for_selector(".answer-btn", state="visible", timeout=5000)
        assert page.evaluate("answered") is False

        current_answer = page.evaluate("String(answer)")
        assert current_answer, "answer must be non-empty"

        page.locator(".answer-btn", has_text=current_answer).first.click()

        page.wait_for_function("answered === true", timeout=5000)
        next_btn = page.locator("#next-btn")
        next_btn.wait_for(state="visible", timeout=5000)

        is_last = q_index == TOTAL_QUESTIONS - 1
        if is_last:
            next_btn.click()
            page.wait_for_selector("#result-screen", state="visible", timeout=5000)
        else:
            next_btn.click()
            page.wait_for_function("answered === false", timeout=5000)


def _wrong_answer_index(page: Page, current_answer: str) -> int:
    index = page.evaluate(
        """
        expected => Array.from(document.querySelectorAll('.answer-btn'))
          .findIndex(button => button.textContent.trim() !== expected)
        """,
        current_answer,
    )
    assert index >= 0, "Science question must expose at least one wrong choice"
    return index


@pytest.mark.browser
def test_science_restart_button_starts_new_session(
    static_server: str, page: Page
) -> None:
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

    page.goto(f"{static_server}{SCIENCE_URL}")
    _wait_for_question(page)
    _play_full_session(page)

    restart_btn = page.locator("#restart-btn")
    restart_btn.wait_for(state="visible", timeout=5000)
    restart_btn.click()

    page.wait_for_selector("#game-area", state="visible", timeout=5000)

    assert page.evaluate("currentQ") == 0
    assert page.evaluate("score") == 0
    assert page.evaluate("answered") is False
    assert page.locator("#result-screen").is_hidden()
    page.wait_for_selector(".answer-btn", state="visible", timeout=5000)
    assert page.locator("#next-btn").is_hidden()

    assert page_errors == [], f"page errors: {page_errors}"
    assert console_errors == [], f"console errors: {console_errors}"
    assert failed_requests == [], f"failed requests: {failed_requests}"


@pytest.mark.browser
def test_science_restart_single_click_exact_effect(
    static_server: str, page: Page
) -> None:
    page.goto(f"{static_server}{SCIENCE_URL}")
    _wait_for_question(page)
    _play_full_session(page)

    restart_btn = page.locator("#restart-btn")
    restart_btn.wait_for(state="visible", timeout=5000)

    restart_btn.click()
    page.wait_for_selector("#game-area", state="visible", timeout=5000)

    assert page.evaluate("currentQ") == 0
    assert page.evaluate("score") == 0
    assert page.evaluate("answered") is False

    question_text = page.evaluate("document.getElementById('question').textContent")
    assert question_text.strip() != ""

    page.wait_for_timeout(1500)
    stable_text = page.evaluate("document.getElementById('question').textContent")
    assert stable_text == question_text, (
        "question text changed after restart settled — startGame likely called more than once"
    )

    timer_count = page.evaluate(
        "typeof timerInterval !== 'undefined' ? (timerInterval ? 1 : 0) : 0"
    )
    assert timer_count == 1, f"expected exactly 1 active timer, got {timer_count}"


@pytest.mark.browser
@pytest.mark.parametrize("repeat_run", REPEAT_RUNS)
def test_mixed_full_session_reaches_result_and_restarts_cleanly(
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

    page.goto(f"{static_server}{SCIENCE_URL}")
    _wait_for_question(page)

    next_button = page.locator("#next-btn")
    feedback = page.locator("#feedback")
    expected_score = 0
    final_feedback = ""

    for q_index in range(TOTAL_QUESTIONS):
        expect(page.locator("#q-count")).to_have_text(str(q_index + 1))
        expect(page.locator(".answer-btn")).to_have_count(4)
        expect(page.locator(".answer-btn.correct")).to_have_count(0)
        expect(page.locator(".answer-btn.wrong")).to_have_count(0)
        expect(next_button).to_be_hidden()
        assert page.evaluate("currentQ") == q_index
        assert page.evaluate("answered") is False
        assert page.evaluate("score") == expected_score
        assert feedback.evaluate(
            """
            element => !element.classList.contains('feedback-correct')
              && !element.classList.contains('feedback-wrong')
            """
        )

        current_answer = page.evaluate("String(answer)")
        assert current_answer
        should_answer_correctly = q_index % 2 == 0

        if should_answer_correctly:
            selected_button = page.get_by_role(
                "button", name=current_answer, exact=True
            )
            expect(selected_button).to_have_count(1)
            selected_button.click()
            expected_score += 1
            expect(feedback).to_have_class("feedback-correct")
            expect(page.locator(".answer-btn.correct")).to_have_count(1)
            expect(page.locator(".answer-btn.wrong")).to_have_count(0)
        else:
            answer_buttons = page.locator(".answer-btn")
            selected_button = answer_buttons.nth(
                _wrong_answer_index(page, current_answer)
            )
            selected_button.click()
            expect(feedback).to_have_class("feedback-wrong")
            expect(selected_button).to_have_class("answer-btn wrong")
            expect(page.locator(".answer-btn.correct")).to_have_count(1)
            expect(page.locator(".answer-btn.wrong")).to_have_count(1)

        page.wait_for_function("answered === true", timeout=5000)
        expect(next_button).to_be_visible()
        assert page.evaluate("currentQ") == q_index
        assert page.evaluate("score") == expected_score
        final_feedback = feedback.inner_text().strip()
        assert final_feedback

        next_button.click()
        if q_index < TOTAL_QUESTIONS - 1:
            page.wait_for_function(
                f"currentQ === {q_index + 1} && answered === false",
                timeout=5000,
            )
        else:
            page.wait_for_selector("#result-screen", state="visible", timeout=5000)

    expect(page.locator("#game-area")).to_be_hidden()
    expect(page.locator("#result-screen")).to_be_visible()
    expect(page.locator("#q-count")).to_have_text("10")
    expect(page.locator("#q-score")).to_have_text("5")
    expect(page.locator("#stars")).to_have_text("⭐")
    expect(page.locator("#result-title")).to_have_text("조금 더 연습해요!")
    expect(page.locator("#result-msg")).to_have_text(
        "10문제 중 5개 맞췄어요. 다음에 더 잘할 수 있어요! 💪"
    )
    assert page.evaluate("currentQ") == TOTAL_QUESTIONS
    assert page.evaluate("score") == 5
    assert page.evaluate("answered") is True

    page.locator("#restart-btn").click()
    page.wait_for_function(
        "currentQ === 0 && score === 0 && answered === false",
        timeout=5000,
    )

    expect(page.locator("#game-area")).to_be_visible()
    expect(page.locator("#result-screen")).to_be_hidden()
    expect(page.locator("#q-count")).to_have_text("1")
    expect(page.locator("#q-score")).to_have_text("0")
    expect(page.locator(".answer-btn")).to_have_count(4)
    expect(page.locator(".answer-btn.correct")).to_have_count(0)
    expect(page.locator(".answer-btn.wrong")).to_have_count(0)
    expect(next_button).to_be_hidden()
    assert feedback.inner_text().strip() != final_feedback
    assert feedback.evaluate(
        """
        element => !element.classList.contains('feedback-correct')
          && !element.classList.contains('feedback-wrong')
        """
    )
    assert page.evaluate("timerInterval ? 1 : 0") == 1

    assert page_errors == [], f"page errors: {page_errors}"
    assert console_errors == [], f"console errors: {console_errors}"
    assert failed_requests == [], f"failed requests: {failed_requests}"
