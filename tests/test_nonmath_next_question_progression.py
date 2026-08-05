"""Browser regression contract for non-math next-question progression."""

from __future__ import annotations

import http.server
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright


REPO_ROOT = Path(__file__).resolve().parent.parent
SUBJECTS = ("korean", "english", "science")


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


def answer_current_question_correctly(page: Page) -> None:
    """Complete either a standard choice or English sequential-blank question."""

    has_sequential_blanks = page.evaluate(
        "typeof seqBlanks !== 'undefined' && Boolean(seqBlanks)"
    )
    if not has_sequential_blanks:
        current_answer = page.evaluate("String(answer)")
        page.get_by_role("button", name=current_answer, exact=True).click()
        return

    while page.evaluate("Boolean(seqBlanks) && !answered"):
        current_character = page.evaluate("seqBlanks.blanks[seqStep].char")
        page.get_by_role("button", name=current_character, exact=True).click()


@pytest.mark.browser
@pytest.mark.parametrize("subject", SUBJECTS)
def test_correct_answer_then_next_advances_exactly_one_question(
    static_server: str,
    page: Page,
    subject: str,
) -> None:
    page_errors: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))

    page.goto(f"{static_server}/domains/{subject}/index.html")
    page.wait_for_selector(".answer-btn", state="visible", timeout=5000)

    next_button = page.locator("#next-btn")
    expect(next_button).to_be_hidden()
    assert page.evaluate("currentQ") == 0
    assert page.evaluate(
        "document.getElementById('next-btn').dataset.progressionBound"
    ) == "true"

    answer_current_question_correctly(page)

    expect(next_button).to_be_visible()
    expect(page.locator("#q-score")).to_have_text("1")
    assert page.evaluate("answered") is True

    next_button.click()

    expect(next_button).to_be_hidden()
    assert page.evaluate("currentQ") == 1
    assert page.evaluate("answered") is False
    assert page_errors == []
