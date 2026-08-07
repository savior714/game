"""Browser verification for external-tab-launcher: noopener + success/detectability."""

from __future__ import annotations

import http.server
import socketserver
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Page, sync_playwright


REPO_ROOT = Path(__file__).resolve().parent.parent
PORT = 18924


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def log_message(self, format, *args):  # noqa: A002
        pass


@pytest.fixture(scope="module")
def static_server():
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("127.0.0.1", PORT), QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{PORT}"

    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


@pytest.fixture
def page():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
        )
        browser_page = context.new_page()
        yield browser_page
        context.close()
        browser.close()


def test_browser_single_tab_noopener(static_server: str, page: Page) -> None:
    """한 번의 클릭으로 새 탭 한 개, opener=null, 같은-origin 대상, YouTube 아님."""
    page_errors: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))

    # Navigate to test page
    page.goto(f"{static_server}/tests/fixtures/test-page.html")
    page.wait_for_selector("#status", state="visible", timeout=5000)

    # Click launch button
    page.click("#launchBtn")
    page.wait_for_timeout(1500)

    # Parent reports success
    status = page.text_content("#status")
    assert status == "launched:ok", f"expected launched:ok, got {status}"

    # Popup should exist
    pages = page.context.pages
    assert len(pages) >= 2, f"expected >=2 pages, got {len(pages)}"
    popup = pages[1]

    # Popup URL: same-origin test target or about:blank, NOT YouTube
    popup_url = popup.url
    assert "/test-target.html" in popup_url or "about:blank" in popup_url, (
        f"popup URL should be test target or about:blank, got {popup_url}"
    )
    assert "youtube.com" not in popup_url, "popup should NOT navigate to YouTube"

    # Popup opener is null
    opener_null = popup.evaluate("() => window.opener === null")
    assert opener_null is True, "popup window.opener should be null"

    # No page errors on parent
    assert len(page_errors) == 0, f"parent page errors: {page_errors}"

    # Collect popup errors
    popup_errors: list[str] = []
    popup.on("pageerror", lambda error: popup_errors.append(str(error)))

    # No page errors on popup
    assert len(popup_errors) == 0, f"popup page errors: {popup_errors}"

    # Exactly one new tab
    assert len(pages) == 2, f"expected exactly 2 pages, got {len(pages)}"
