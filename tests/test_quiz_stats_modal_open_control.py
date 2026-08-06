"""
Focused browser test: clicking #stats-btn opens the stats modal.

Verifies that the actual user path — clicking the #stats-btn element via
Playwright — opens the #stats-modal in all four quiz domains (math, korean,
english, science). This is a parameterized test that runs the same scenario
against each domain.

Production change scope: only shared/ui/quiz-ui-core.js wires the button
click to the core's openStats() at creation time. No per-domain ui.js file
is touched.
"""

import http.server
import socketserver
import threading
import time
import pytest
from pathlib import Path
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).parent.parent

DOMAINS = ["math", "korean", "english", "science"]


class HTTPServerFixture:
    """Static HTTP server using an OS-assigned ephemeral port."""

    def __init__(self):
        self.server = None
        self.thread = None
        self.base_url = None
        self._port = None

    def start(self):
        os_chdir = __import__("os").chdir
        os_chdir(REPO_ROOT)

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

            def log_message(self, format, *args):
                pass

        socketserver.TCPServer.allow_reuse_address = True
        self.server = socketserver.TCPServer(("127.0.0.1", 0), QuietHandler)
        self._port = self.server.server_address[1]
        self.thread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        self.thread.start()
        time.sleep(0.3)
        self.base_url = f"http://127.0.0.1:{self._port}"
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
class TestStatsButtonClickOpensModal:
    """Real user click on #stats-btn must open #stats-modal in every domain."""

    @pytest.mark.parametrize("domain", DOMAINS)
    def test_stats_button_click_opens_modal(self, server, page, domain):
        """Clicking #stats-btn via Playwright opens the stats modal."""
        url = f"{server}/domains/{domain}/index.html"

        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        clear_storage(page)

        # Wait for the question area to render (confirms page loaded fully).
        page.wait_for_selector("#question", state="visible", timeout=8000)

        # Step 1: #stats-modal must be hidden initially.
        modal = page.locator("#stats-modal")
        initial_display = modal.evaluate(
            "el => getComputedStyle(el).display"
        )
        assert initial_display != "flex", (
            f"[{domain}] #stats-modal should be hidden on load, "
            f"but display was '{initial_display}'"
        )

        # Step 2: #stats-btn must be present in the DOM.
        stats_btn = page.locator("#stats-btn")
        stats_btn.wait_for(state="visible", timeout=5000)

        # Step 3: Actual user click — no JS evaluation to open the modal.
        stats_btn.click()

        # Step 4: #stats-modal must now be visible (display: flex).
        final_display = modal.evaluate("el => getComputedStyle(el).display")
        assert final_display == "flex", (
            f"[{domain}] After clicking #stats-btn, #stats-modal display "
            f"was '{final_display}', expected 'flex'"
        )
