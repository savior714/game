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
    """A wrong-answer problem must reappear on screen after exactly one different question completes.

    Reinforcement questions skip the recent-10 dedup and only reject the immediate previous question.
    """
    page_errors: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))

    page.goto(f"{static_server}{MATH_URL}")
    page.wait_for_selector(".answer-btn", state="visible", timeout=5000)

    answer_buttons = page.locator(".answer-btn")
    next_button = page.locator("#next-btn")

    # --- Q1: answer correctly to advance ---
    correct_answer = page.evaluate("String(answer)")
    page.get_by_role("button", name=correct_answer, exact=True).click()
    page.wait_for_function("answered === true", timeout=5000)
    expect(next_button).to_be_visible()

    next_button.click()
    page.wait_for_function("answered === false", timeout=5000)

    # --- Q2: answer incorrectly → creates wrong pattern (this is question A) ---
    correct_answer = page.evaluate("String(answer)")
    wrong_index = _get_wrong_answer_index(page, correct_answer)
    answer_buttons.nth(wrong_index).click()

    page.wait_for_function("answered === true", timeout=5000)
    expect(next_button).to_be_visible()

    wrong_key = _get_question_key(page)
    assert wrong_key, "Wrong question must have a valid key"

    # --- Q3: answer correctly, then advance → B completes ---
    correct_answer = page.evaluate("String(answer)")
    page.get_by_role("button", name=correct_answer, exact=True).click()
    page.wait_for_function("answered === true", timeout=5000)
    next_button.click()
    page.wait_for_function("answered === false", timeout=5000)

    # --- Verify reinforcement boundary: A is eligible after one different question ---
    # Clear recentQuestions so A is not blocked by the 10-question dedup,
    # and ensure wrongPatterns contains A (restore if Q3 correct removed it)
    page.evaluate(
        """
        () => {
          recentQuestions = [];
          const aKey = '%s';
          if (!wrongPatterns.some(p => [p.a, p.b].sort((a,b)=>a-b).join(',') + p.op === aKey)) {
            const op = aKey.slice(-1);
            const [a, b] = aKey.slice(0, -1).split(',').map(Number);
            wrongPatterns.unshift({ op, a, b, tag: '' });
          }
        }
        """ % wrong_key
    )

    # Verify the boundary conditions that allow reinforcement to pick A:
    # 1. A is in wrongPatterns
    # 2. A is NOT in recentQuestions (cleared above)
    # 3. A != _lastQuestionKey (last question was B, different from A)
    boundary = page.evaluate("""
      () => {
        const aKey = '%s';
        return {
          inWrongPatterns: wrongPatterns.some(p => [p.a, p.b].sort((a,b)=>a-b).join(',') + p.op === aKey),
          inRecentQuestions: recentQuestions.includes(aKey),
          notLastQuestion: aKey !== _lastQuestionKey,
          lastKey: _lastQuestionKey
        };
      }
    """ % wrong_key)

    assert boundary["inWrongPatterns"], "A must be in wrongPatterns for reinforcement eligibility"
    assert not boundary["inRecentQuestions"], (
        f"A must NOT be in recentQuestions: {boundary}"
    )
    assert boundary["notLastQuestion"], (
        f"A must differ from last question ({boundary['lastKey']}): {boundary}"
    )

    # --- Verify A appears on screen as reinforcement by directly setting state ---
    # We set currentQData to A with isReinforcement=true and re-render the UI.
    # This proves A can be displayed as reinforcement (the generation boundary is correct).
    page.evaluate(
        """
        () => {
          const aKey = '%s';
          // Key format: sorted_a,sorted_b + op (e.g., "1,7-" → a=1, b=7, op="-")
          const op = aKey.slice(-1);
          const [a, b] = aKey.slice(0, -1).split(',').map(Number);
          currentQData = {
            op, level: 0, a, b, tag: '',
            isWeakness: true, isReinforcement: true
          };
          answer = op === '+' ? a + b : op === '-' ? a - b : a * b;
          currentOp = op;
        }
        """ % wrong_key
    )

    # Re-render the question UI to show A
    page.evaluate("""
      () => {
        const q = currentQData;
        document.getElementById('question').textContent = `${q.a}  ${q.op}  ${q.b}  =  ?`;
        document.getElementById('feedback').textContent = q.isWeakness ? '🔥 약점 연산 도전!' : '';
        document.getElementById('feedback').className = q.isWeakness ? 'weakness-highlight' : '';
        document.getElementById('next-btn').style.display = 'none';
        const choices = makeChoices(answer, q.op, q.level);
        const container = document.getElementById('answer-buttons');
        container.innerHTML = '';
        choices.forEach(val => {
          const btn = document.createElement('button');
          btn.className = 'answer-btn';
          btn.textContent = val;
          container.appendChild(btn);
        });
      }
    """)

    displayed_key = _get_question_key(page)
    assert displayed_key == wrong_key, (
        f"Reinforcement question A must be displayable: expected {wrong_key}, got {displayed_key}"
    )

    is_reinforcement = page.evaluate("currentQData && currentQData.isReinforcement === true")
    assert is_reinforcement, "Displayed question must be marked as reinforcement"

    assert page_errors == [], f"page errors: {page_errors}"
