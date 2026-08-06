"""
Focused browser test: sequential keyboard focus must stay within #stats-modal.

Verifies that Tab / Shift+Tab at the modal boundaries loops focus back inside
#stats-modal instead of escaping to elements outside the modal.

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
PORT = 18768


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


def open_modal(pg):
    pg.evaluate(
        "() => window.QuizUICore.createStatsModalCore({renderStatsTable: function(){}}).openStats()"
    )


def close_modal(pg):
    pg.evaluate(
        "() => window.QuizUICore.createStatsModalCore({renderStatsTable: function(){}}).closeStats()"
    )


def is_descendant_of_modal(pg, element_id):
    return pg.evaluate(
        """(id) => {
            const el = document.getElementById(id);
            if (!el) return false;
            const modal = document.getElementById('stats-modal');
            return modal && modal.contains(el);
        }""",
        element_id,
    )


@pytest.mark.browser
class TestStatsModalFocusContainment:
    """Tab / Shift+Tab must keep focus inside #stats-modal."""

    def test_shift_tab_from_first_to_last_keeps_focus_inside(self, server, page):
        """Shift+Tab on #close-stats-btn must move to #reset-stats-btn, not outside."""
        url = f"{server}/domains/korean/index.html"

        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        clear_storage(page)
        page.wait_for_selector("#question", state="visible", timeout=5000)

        open_modal(page)
        page.wait_for_selector("#close-stats-btn", state="visible", timeout=5000)

        # Verify initial focus is on close button
        active = page.evaluate("() => document.activeElement.id")
        assert active == "close-stats-btn", (
            f"Expected initial focus on #close-stats-btn, got '{active}'"
        )

        # Shift+Tab from first tabbable should wrap to last tabbable
        page.keyboard.press("Shift+Tab")

        active_after = page.evaluate("() => document.activeElement.id")
        assert active_after == "reset-stats-btn", (
            f"Expected Shift+Tab to wrap from #close-stats-btn to #reset-stats-btn, "
            f"but activeElement.id was '{active_after}'"
        )

        # Verify the focused element is still inside #stats-modal
        inside = is_descendant_of_modal(page, active_after)
        assert inside is True, (
            f"Focus after Shift+Tab ({active_after}) must be inside #stats-modal"
        )

    def test_tab_from_last_to_first_keeps_focus_inside(self, server, page):
        """Tab on #reset-stats-btn must move to #close-stats-btn, not outside."""
        url = f"{server}/domains/korean/index.html"

        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        clear_storage(page)
        page.wait_for_selector("#question", state="visible", timeout=5000)

        open_modal(page)
        page.wait_for_selector("#close-stats-btn", state="visible", timeout=5000)

        # Move focus to #reset-stats-btn via Tab
        page.keyboard.press("Tab")
        active = page.evaluate("() => document.activeElement.id")
        assert active == "reset-stats-btn", (
            f"Expected Tab to move from #close-stats-btn to #reset-stats-btn, "
            f"but activeElement.id was '{active}'"
        )

        # Tab from last tabbable should wrap back to first
        page.keyboard.press("Tab")

        active_after = page.evaluate("() => document.activeElement.id")
        assert active_after == "close-stats-btn", (
            f"Expected Tab to wrap from #reset-stats-btn to #close-stats-btn, "
            f"but activeElement.id was '{active_after}'"
        )

        # Verify the focused element is still inside #stats-modal
        inside = is_descendant_of_modal(page, active_after)
        assert inside is True, (
            f"Focus after Tab ({active_after}) must be inside #stats-modal"
        )
