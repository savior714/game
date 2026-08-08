"""Browser contract for English typing question unlimited timer policy."""

from __future__ import annotations

import http.server
import socketserver
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
ENGLISH_URL = "/domains/english/index.html"


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


def test_english_typing_unlimited_timer_ui_and_behavior(
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
        "requestfailed", lambda req: failed_requests.append(f"{req.url} {req.failure}")
    )

    page.goto(f"{static_server}{ENGLISH_URL}")
    page.wait_for_selector("#game-area", state="visible", timeout=5000)

    # Force typing question type
    page.evaluate("() => { window.pickQuestionType = () => 'typing'; }")
    page.evaluate("() => { if (typeof startGame === 'function') startGame(); }")
    page.wait_for_selector("#typing-input", state="visible", timeout=5000)

    # Verify UI shows infinite timer
    timer_text = page.locator("#timer-text")
    expect(timer_text).to_have_text("♾️")

    # Verify timer bar is full and has no warn/danger classes
    assert (
        page.evaluate("() => document.getElementById('timer-bar').style.width")
        == "100%"
    )
    assert not page.locator("#game-card").is_visible() or "time-danger" not in (
        page.locator("#game-card").get_attribute("class") or ""
    )

    # Wait 1 second and check timer is still no-limit and answered is false
    page.wait_for_timeout(1000)
    expect(timer_text).to_have_text("♾️")
    assert page.evaluate("answered") is False

    # Explicitly trigger timeOut() and verify typing question ignores it
    page.evaluate("() => { if (typeof timeOut === 'function') timeOut(); }")
    assert page.evaluate("answered") is False
    expect(page.locator("#typing-input")).to_be_enabled()

    assert not page_errors, f"Page errors: {page_errors}"
    assert not console_errors, f"Console errors: {console_errors}"
    assert not failed_requests, f"Failed requests: {failed_requests}"
