"""Focused browser contract for the math next-question control."""

from __future__ import annotations

import http.server
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright


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
