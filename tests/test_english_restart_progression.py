"""Focused browser regression for English quiz restart button binding."""

from __future__ import annotations

import http.server
import socketserver
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Page, sync_playwright


REPO_ROOT = Path(__file__).resolve().parent.parent
ENGLISH_URL = f"/domains/english/index.html"
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


def run_full_session_and_restart(static_server: str, page: Page) -> None:
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
    page.evaluate(
        "() => { window.pickQuestionType = () => 'kor2word'; }",
    )
    page.evaluate("() => { if (typeof startGame === 'function') startGame(); }")
    page.wait_for_selector(".answer-btn", state="visible", timeout=5000)

    for q_index in range(TOTAL_QUESTIONS):
        page.wait_for_selector(".answer-btn", state="visible", timeout=5000)
        assert page.evaluate("answered") is False

        current_answer = page.evaluate("String(answer)")
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

    restart_btn = page.locator("#restart-btn")
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
def test_english_restart_button_starts_new_session(static_server: str, page: Page) -> None:
    run_full_session_and_restart(static_server, page)
