"""Browser acceptance tests for reward mini-game (Marble/Bubble) responsive modal and top-level home navigation.

Verifies:
- Case A: Marble in landscape viewport (1280x800) opens responsive iframe, clicking "홈으로" navigates top-level to /index.html without nesting, rendering full landscape layout.
- Case B: Bubble in landscape viewport (1280x800) opens responsive iframe, clicking "홈으로" / brand badge navigates top-level to /index.html without nesting, rendering full landscape layout.
- Case C: Close contract (outer "학습으로 돌아가기" button and iframe postMessage closeMarble/closeBubble) dismisses overlay while preserving subject page state.
- Case D: Small viewport (360x640) has no horizontal overflow, iframe fits cleanly, and close control remains visible and accessible.
"""

from __future__ import annotations

import http.server
import socketserver
import threading
import time
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent


class HTTPServerFixture:
    def __init__(self) -> None:
        self.server: socketserver.TCPServer | None = None
        self.thread: threading.Thread | None = None
        self.base_url: str | None = None
        self._port: int | None = None

    def start(self) -> str:
        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

            def log_message(self, format, *args):  # noqa: A002
                pass

        socketserver.TCPServer.allow_reuse_address = True
        self.server = socketserver.TCPServer(("127.0.0.1", 0), QuietHandler)
        self._port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.3)
        self.base_url = f"http://127.0.0.1:{self._port}"
        return self.base_url

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()


@pytest.fixture(scope="module")
def server():
    srv = HTTPServerFixture()
    url = srv.start()
    yield url
    srv.stop()


@pytest.fixture(scope="module")
def playwright_instance():
    with sync_playwright() as p:
        yield p


@pytest.fixture
def browser(playwright_instance):
    b = playwright_instance.chromium.launch(headless=True)
    yield b
    b.close()


@pytest.mark.browser
class TestRewardModalViewportAndNavigation:
    """Acceptance tests for Marble and Bubble reward modals and HUD home navigation."""

    def test_case_a_marble_landscape_responsive_and_top_home(self, server, browser):
        """Case A: Landscape (1280x800) Marble modal is responsive; '홈으로' navigates top-level to /index.html."""
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="ko-KR",
        )
        page = context.new_page()
        try:
            page.goto(f"{server}/domains/math/index.html")
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_selector("#question", state="visible", timeout=7000)

            # 1. Open Marble overlay
            page.evaluate("() => window.RewardSystemUI.openMarbleModal()")
            page.wait_for_selector(
                ".reward-marble-modal", state="visible", timeout=5000
            )

            # 2. Check iframe existence and responsive dimensions
            iframe_el = page.wait_for_selector(
                ".reward-marble-modal iframe.reward-mini-game-frame",
                state="visible",
                timeout=5000,
            )
            assert iframe_el is not None

            box = iframe_el.bounding_box()
            assert box is not None
            # Must NOT be hardcoded 360x560 phone frame
            assert (round(box["width"]), round(box["height"])) != (360, 560)
            # In 1280x800, width is min(94vw, 960px) ~ 960px, height is min(80vh, 680px) ~ 640px
            assert box["width"] >= 700, (
                f"Expected responsive width >= 700, got {box['width']}"
            )
            assert box["height"] >= 580, (
                f"Expected responsive height >= 580, got {box['height']}"
            )

            # 3. Locate home link inside iframe HUD
            marble_frame = page.frame_locator(
                ".reward-marble-modal iframe.reward-mini-game-frame"
            )
            home_link = marble_frame.locator(".home-btn")
            home_link.wait_for(state="visible", timeout=8000)

            # 4. Click '홈으로' in iframe
            home_link.click()

            # 5. Final top-level URL must be main /index.html
            page.wait_for_url(f"{server}/index.html", timeout=7000)
            assert page.url.endswith("/index.html")

            # 6. No reward iframe should be rendered inside page or nested
            assert page.locator("iframe.reward-mini-game-frame").count() == 0
            assert page.locator(".reward-marble-modal").count() == 0

            # 7. Top-level main must use full 1280x800 landscape layout, not 1-column mobile breakpoint
            page.wait_for_selector(".core-subject-grid", state="visible", timeout=5000)
            grid_cols = page.evaluate(
                "() => window.getComputedStyle(document.querySelector('.core-subject-grid')).gridTemplateColumns"
            )
            # 1-column mobile layout would be a single px value; multi-column has multiple columns
            cols = [c for c in grid_cols.strip().split() if c]
            assert len(cols) > 1, (
                f"Expected multi-column layout on 1280x800, got cols: {grid_cols}"
            )
        finally:
            context.close()

    def test_case_b_bubble_landscape_responsive_and_top_home(self, server, browser):
        """Case B: Landscape (1280x800) Bubble modal is responsive; brand badge navigates top-level to /index.html."""
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="ko-KR",
        )
        page = context.new_page()
        try:
            page.goto(f"{server}/domains/math/index.html")
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_selector("#question", state="visible", timeout=7000)

            # 1. Open Bubble overlay
            page.evaluate("() => window.RewardSystemUI.openBubbleModal()")
            page.wait_for_selector(
                ".reward-bubble-modal", state="visible", timeout=5000
            )

            # 2. Check iframe existence and responsive dimensions
            iframe_el = page.wait_for_selector(
                ".reward-bubble-modal iframe.reward-mini-game-frame",
                state="visible",
                timeout=5000,
            )
            assert iframe_el is not None

            box = iframe_el.bounding_box()
            assert box is not None
            assert (round(box["width"]), round(box["height"])) != (360, 560)
            assert box["width"] >= 700, (
                f"Expected responsive width >= 700, got {box['width']}"
            )
            assert box["height"] >= 580, (
                f"Expected responsive height >= 580, got {box['height']}"
            )

            # 3. Locate home link or brand badge inside bubble frame
            bubble_frame = page.frame_locator(
                ".reward-bubble-modal iframe.reward-mini-game-frame"
            )
            home_link = bubble_frame.locator(".home-btn")
            home_link.wait_for(state="visible", timeout=8000)

            # 4. Click '홈으로'
            home_link.click()

            # 5. Final top-level URL is /index.html
            page.wait_for_url(f"{server}/index.html", timeout=7000)
            assert page.url.endswith("/index.html")

            # 6. No reward iframe inside main
            assert page.locator("iframe.reward-mini-game-frame").count() == 0
            assert page.locator(".reward-bubble-modal").count() == 0

            # 7. Multi-column subject grid on landscape
            page.wait_for_selector(".core-subject-grid", state="visible", timeout=5000)
            grid_cols = page.evaluate(
                "() => window.getComputedStyle(document.querySelector('.core-subject-grid')).gridTemplateColumns"
            )
            cols = [c for c in grid_cols.strip().split() if c]
            assert len(cols) > 1, (
                f"Expected multi-column layout on 1280x800, got cols: {grid_cols}"
            )
        finally:
            context.close()

    def test_case_c_close_contract(self, server, browser):
        """Case C: Outer '학습으로 돌아가기' button and postMessage both close overlays without leaving page."""
        context = browser.new_context(
            viewport={"width": 1024, "height": 768},
            locale="ko-KR",
        )
        page = context.new_page()
        try:
            page.goto(f"{server}/domains/math/index.html")
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_selector("#question", state="visible", timeout=7000)

            # Sub-test C1: Marble outer close button
            page.evaluate("() => window.RewardSystemUI.openMarbleModal()")
            page.wait_for_selector(
                ".reward-marble-modal", state="visible", timeout=5000
            )
            outer_close_btn = page.locator(".reward-marble-modal .btn-close-marble")
            outer_close_btn.click()
            page.wait_for_selector(
                ".reward-marble-modal", state="detached", timeout=5000
            )
            assert "/domains/math/index.html" in page.url

            # Sub-test C2: Marble postMessage closeMarble
            page.evaluate("() => window.RewardSystemUI.openMarbleModal()")
            page.wait_for_selector(
                ".reward-marble-modal", state="visible", timeout=5000
            )
            page.evaluate("() => window.postMessage('closeMarble', '*')")
            page.wait_for_selector(
                ".reward-marble-modal", state="detached", timeout=5000
            )
            assert "/domains/math/index.html" in page.url

            # Sub-test C3: Bubble outer close button
            page.evaluate("() => window.RewardSystemUI.openBubbleModal()")
            page.wait_for_selector(
                ".reward-bubble-modal", state="visible", timeout=5000
            )
            bubble_close_btn = page.locator(".reward-bubble-modal .btn-close-marble")
            bubble_close_btn.click()
            page.wait_for_selector(
                ".reward-bubble-modal", state="detached", timeout=5000
            )
            assert "/domains/math/index.html" in page.url

            # Sub-test C4: Bubble postMessage closeBubble
            page.evaluate("() => window.RewardSystemUI.openBubbleModal()")
            page.wait_for_selector(
                ".reward-bubble-modal", state="visible", timeout=5000
            )
            page.evaluate("() => window.postMessage('closeBubble', '*')")
            page.wait_for_selector(
                ".reward-bubble-modal", state="detached", timeout=5000
            )
            assert "/domains/math/index.html" in page.url
        finally:
            context.close()

    def test_case_d_small_portrait_viewport(self, server, browser):
        """Case D: Small portrait viewport (360x640) has no horizontal overflow and close button is operable."""
        context = browser.new_context(
            viewport={"width": 360, "height": 640},
            locale="ko-KR",
        )
        page = context.new_page()
        try:
            page.goto(f"{server}/domains/math/index.html")
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_selector("#question", state="visible", timeout=7000)

            # Test Marble on small viewport
            page.evaluate("() => window.RewardSystemUI.openMarbleModal()")
            page.wait_for_selector(
                ".reward-marble-modal", state="visible", timeout=5000
            )

            # Verify no horizontal page overflow
            has_h_overflow = page.evaluate(
                "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
            )
            assert not has_h_overflow, (
                "Horizontal overflow detected in small viewport for Marble"
            )

            # Check close button is visible and clickable
            close_btn = page.locator(".reward-marble-modal .btn-close-marble")
            assert close_btn.is_visible()
            close_btn.click()
            page.wait_for_selector(
                ".reward-marble-modal", state="detached", timeout=5000
            )

            # Test Bubble on small viewport
            page.evaluate("() => window.RewardSystemUI.openBubbleModal()")
            page.wait_for_selector(
                ".reward-bubble-modal", state="visible", timeout=5000
            )

            has_h_overflow_bubble = page.evaluate(
                "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
            )
            assert not has_h_overflow_bubble, (
                "Horizontal overflow detected in small viewport for Bubble"
            )

            bubble_close_btn = page.locator(".reward-bubble-modal .btn-close-marble")
            assert bubble_close_btn.is_visible()
            bubble_close_btn.click()
            page.wait_for_selector(
                ".reward-bubble-modal", state="detached", timeout=5000
            )
        finally:
            context.close()
