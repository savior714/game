"""
Focused browser test: focus restores to trigger element after closeStats().

Verifies that calling openStats() then closeStats() returns keyboard focus
to the element that was focused immediately before openStats() was called.
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
PORT = 18767


class HTTPServerFixture:
    def __init__(self):
        self.server = None
        self.thread = None
        self.base_url = None

    def start(self):
        os.chdir(REPO_ROOT)

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

            def log_message(self, format, *args):
                pass

        socketserver.TCPServer.allow_reuse_address = True
        self.server = socketserver.TCPServer(("127.0.0.1", PORT), QuietHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.5)
        self.base_url = f"http://127.0.0.1:{PORT}"
        return self.base_url

    def stop(self):
        if self.server:
            self.server.shutdown()


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
class TestStatsModalFocusRestorationOnClose:
    """Focus must restore to the trigger element after closeStats()."""

    def test_focus_restores_to_trigger_after_close(self, server, page):
        """Closing the stats modal must return focus to #stats-btn."""
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
        active_after_open = page.evaluate("() => document.activeElement.id")
        assert active_after_open == "close-stats-btn", (
            f"Expected focus on #close-stats-btn after openStats(), "
            f"but activeElement.id was '{active_after_open}'"
        )

        # Step 4: call closeStats() via the shared QuizUICore
        page.evaluate(
            "() => window.QuizUICore.createStatsModalCore({renderStatsTable: function(){}}).closeStats()"
        )

        # Step 5: verify focus returned to the trigger element
        active_after_close = page.evaluate("() => document.activeElement.id")
        assert active_after_close == "stats-btn", (
            f"Expected focus to restore to #stats-btn after closeStats(), "
            f"but activeElement.id was '{active_after_close}'"
        )
