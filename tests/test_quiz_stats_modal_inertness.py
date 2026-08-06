"""
Focused browser test: inert background while stats modal is open.

Verifies that #stats-modal open/close lifecycle correctly sets inert on
background elements and restores per-element prior inert state on close.
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
class TestStatsModalInertness:
    """Background must be inert while stats modal is open, and restored per-element on close."""

    def test_inert_lifecycle(self, server, page):
        url = f"{server}/domains/korean/index.html"

        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        clear_storage(page)
        page.wait_for_selector("#question", state="visible", timeout=5000)

        # Step 1: focus the stats button
        page.focus("#stats-btn")
        active_before = page.evaluate("() => document.activeElement.id")
        assert active_before == "stats-btn", (
            f"Expected stats-btn focused before open, got '{active_before}'"
        )

        # Step 2: verify background elements are NOT inert by default
        home_link_inert = page.evaluate("() => document.querySelector('.home-link').inert")
        h1_inert = page.evaluate("() => document.body.children[1].inert")
        score_board_inert = page.evaluate("() => document.getElementById('score-board').inert")
        main_area_inert = page.evaluate("() => document.getElementById('main-area').inert")
        assert home_link_inert is False, f".home-link should not be inert before open, got {home_link_inert}"
        assert h1_inert is False, f"body > h1 should not be inert before open, got {h1_inert}"
        assert score_board_inert is False, f"#score-board should not be inert before open, got {score_board_inert}"
        assert main_area_inert is False, f"#main-area should not be inert before open, got {main_area_inert}"

        # Step 3: set #main-area to inert = true to prove per-element restoration
        page.evaluate("() => { document.getElementById('main-area').inert = true; }")
        main_area_inert_pre = page.evaluate("() => document.getElementById('main-area').inert")
        assert main_area_inert_pre is True, "#main-area must be inert=true before open to test restoration"

        # Step 4: create stats modal core instance and open
        modal_core = page.evaluate_handle(
            "() => window.QuizUICore.createStatsModalCore({renderStatsTable: function(){}})"
        )
        modal_core.evaluate("core => core.openStats()")

        # Step 5: verify background elements ARE inert after open
        home_link_inert_open = page.evaluate("() => document.querySelector('.home-link').inert")
        h1_inert_open = page.evaluate("() => document.body.children[1].inert")
        score_board_inert_open = page.evaluate("() => document.getElementById('score-board').inert")
        main_area_inert_open = page.evaluate("() => document.getElementById('main-area').inert")

        assert home_link_inert_open is True, (
            f".home-link should be inert after open, got {home_link_inert_open}"
        )
        assert h1_inert_open is True, (
            f"body > h1 should be inert after open, got {h1_inert_open}"
        )
        assert score_board_inert_open is True, (
            f"#score-board should be inert after open, got {score_board_inert_open}"
        )
        assert main_area_inert_open is True, (
            f"#main-area should be inert after open, got {main_area_inert_open}"
        )

        # Step 6: verify stats modal itself is NOT inert
        stats_modal_inert = page.evaluate("() => document.getElementById('stats-modal').inert")
        assert stats_modal_inert is False, (
            f"#stats-modal must NOT be inert while open, got {stats_modal_inert}"
        )

        # Step 7: verify close button is focused
        active_after_open = page.evaluate("() => document.activeElement.id")
        assert active_after_open == "close-stats-btn", (
            f"Expected focus on #close-stats-btn after open, got '{active_after_open}'"
        )

        # Step 8: close the modal using the same instance
        modal_core.evaluate("core => core.closeStats()")

        # Step 9: verify background elements are restored to their pre-open state
        home_link_inert_close = page.evaluate("() => document.querySelector('.home-link').inert")
        h1_inert_close = page.evaluate("() => document.body.children[1].inert")
        score_board_inert_close = page.evaluate("() => document.getElementById('score-board').inert")
        main_area_inert_close = page.evaluate("() => document.getElementById('main-area').inert")

        assert home_link_inert_close is False, (
            f".home-link should be inert=false after close, got {home_link_inert_close}"
        )
        assert h1_inert_close is False, (
            f"body > h1 should be inert=false after close, got {h1_inert_close}"
        )
        assert score_board_inert_close is False, (
            f"#score-board should be inert=false after close, got {score_board_inert_close}"
        )
        assert main_area_inert_close is True, (
            f"#main-area should remain inert=true after close (was set true before open), got {main_area_inert_close}"
        )

        # Step 10: verify focus returned to stats-btn
        active_after_close = page.evaluate("() => document.activeElement.id")
        assert active_after_close == "stats-btn", (
            f"Expected focus on #stats-btn after close, got '{active_after_close}'"
        )

    def test_inert_restore_tracks_element_identity_after_reorder(self, server, page):
        url = f"{server}/domains/korean/index.html"

        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        clear_storage(page)
        page.wait_for_selector("#question", state="visible", timeout=5000)

        # Confirm target elements have no id so string-key snapshot would fail
        ids = page.evaluate(
            "() => ({ home: document.querySelector('.home-link').id, h1: document.querySelector('body > h1').id })"
        )
        assert ids["home"] == "", f".home-link should have no id, got '{ids['home']}'"
        assert ids["h1"] == "", f"body > h1 should have no id, got '{ids['h1']}'"

        # Step 1: set distinct prior inert states
        page.evaluate(
            "() => { document.querySelector('.home-link').inert = false; document.querySelector('body > h1').inert = true; }"
        )
        home_link_inert_pre = page.evaluate("() => document.querySelector('.home-link').inert")
        h1_inert_pre = page.evaluate("() => document.querySelector('body > h1').inert")
        assert home_link_inert_pre is False, (
            f".home-link must be inert=false before open, got {home_link_inert_pre}"
        )
        assert h1_inert_pre is True, (
            f"body > h1 must be inert=true before open, got {h1_inert_pre}"
        )

        # Step 2: focus stats-btn and open the modal
        page.focus("#stats-btn")
        modal_core = page.evaluate_handle(
            "() => window.QuizUICore.createStatsModalCore({renderStatsTable: function(){}})"
        )
        modal_core.evaluate("core => core.openStats()")

        # Step 3: verify both are inert while modal is open
        home_link_inert_open = page.evaluate("() => document.querySelector('.home-link').inert")
        h1_inert_open = page.evaluate("() => document.querySelector('body > h1').inert")
        assert home_link_inert_open is True, (
            f".home-link should be inert after open, got {home_link_inert_open}"
        )
        assert h1_inert_open is True, (
            f"body > h1 should be inert after open, got {h1_inert_open}"
        )
        active_after_open = page.evaluate("() => document.activeElement.id")
        assert active_after_open == "close-stats-btn", (
            f"Expected focus on #close-stats-btn after open, got '{active_after_open}'"
        )

        # Step 4: reorder DOM siblings while modal is open (swap positions)
        page.evaluate(
            "() => { const home = document.querySelector('.home-link'); const h1 = document.querySelector('body > h1'); home.parentElement.insertBefore(h1, home); }"
        )

        # Step 5: close the modal using the same instance
        modal_core.evaluate("core => core.closeStats()")

        # Step 6: verify each element is restored to its own prior inert state
        home_link_inert_close = page.evaluate("() => document.querySelector('.home-link').inert")
        h1_inert_close = page.evaluate("() => document.querySelector('body > h1').inert")
        assert home_link_inert_close is False, (
            f".home-link should be inert=false after close (was false before open), got {home_link_inert_close}"
        )
        assert h1_inert_close is True, (
            f"body > h1 should be inert=true after close (was true before open), got {h1_inert_close}"
        )

        # Step 7: verify focus returned to stats-btn
        active_after_close = page.evaluate("() => document.activeElement.id")
        assert active_after_close == "stats-btn", (
            f"Expected focus on #stats-btn after close, got '{active_after_close}'"
        )
