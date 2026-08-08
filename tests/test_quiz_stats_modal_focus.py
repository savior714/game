"""
Focused browser test: focus moves into stats modal on open.

Verifies that calling openStats() moves keyboard focus to #close-stats-btn.
Uses Korean subject page only (shared core behavior, not per-subject).
"""

import os
import http.server
import socketserver
import threading
import time
import pytest
from pathlib import Path
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).parent.parent


class HTTPServerFixture:
    def __init__(self):
        self.server = None
        self.thread = None
        self.base_url = None
        self._port = None

    def start(self):
        os.chdir(REPO_ROOT)

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

            def log_message(self, format, *args):
                pass

        socketserver.TCPServer.allow_reuse_address = True
        self.server = socketserver.TCPServer(("127.0.0.1", 0), QuietHandler)
        self._port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.5)
        self.base_url = f"http://127.0.0.1:{self._port}"
        return self.base_url

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()


@pytest.fixture(scope="session")
def server():
    srv = HTTPServerFixture()
    url = srv.start()
    yield url
    srv.stop()


@pytest.fixture
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="ko-KR",
        timezone_id="Asia/Seoul",
    )
    pg = context.new_page()
    yield pg
    context.close()


def clear_storage(pg):
    try:
        pg.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    except Exception:
        pass


@pytest.mark.browser
class TestStatsModalFocusOnOpen:
    """Focus must move into stats modal when openStats() is called."""

    def test_focus_moves_to_close_button_on_open(self, server, page):
        """Calling openStats() must place focus on #close-stats-btn."""
        url = f"{server}/domains/korean/index.html"

        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        clear_storage(page)
        page.wait_for_selector("#question", state="visible", timeout=5000)

        # Step 1: focus the stats button
        page.focus("#stats-btn")
        active_before = page.evaluate("() => document.activeElement.id")
        assert active_before == "stats-btn", (
            f"Expected stats-btn to be focused before open, got '{active_before}'"
        )

        # Step 2: call openStats() via the shared QuizUICore
        page.evaluate(
            "() => window.QuizUICore.createStatsModalCore({renderStatsTable: function(){}}).openStats()"
        )

        # Step 3: verify focus moved into the modal
        active_after = page.evaluate("() => document.activeElement.id")
        assert active_after == "close-stats-btn", (
            f"Expected focus on #close-stats-btn after openStats(), "
            f"but activeElement.id was '{active_after}'"
        )
