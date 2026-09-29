"""Browser acceptance tests for contextual single-owner HUD and opt-in reward surface.

Verifies runtime behaviors across desktop, tablet, and mobile viewports:
1. Main hub displays full reward inventory surface with operable controls.
2. Core learning screens render compact 1-line HUD with only gem count visible.
3. Non-gem reward items, shop buttons, and guardian controls are hidden on learning screens.
4. No fixed top overlay or body padding mutation occurs; header does not overlap page content.
5. Clicking the gem link navigates to the main hub's reward surface.
6. Screens without reward mounts (e.g. bubble minigame, weekly test) do not receive any injected reward bar.
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


@pytest.mark.browser
def test_main_hub_full_reward_surface_browser(server: str) -> None:
    """Main hub must render the full reward surface inside #reward-inventory-mount."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{server}/index.html", wait_until="networkidle")

        mount = page.locator("#reward-inventory-mount")
        assert mount.is_visible(), "#reward-inventory-mount must be visible in main hub"
        assert mount.get_attribute("data-reward-surface") == "full"

        inventory = page.locator("#reward-inventory")
        assert inventory.is_visible(), "#reward-inventory must be visible in main hub"

        # Verify multiple reward inventory items are present in full mode
        assert page.locator("#inv-gems").is_visible(), "Gems count must be visible"
        assert page.locator("#reward-inventory [data-type='youtube']").count() >= 1, (
            "YouTube reward slot must exist in full surface"
        )
        assert page.locator("#reward-inventory [data-type='snack']").count() >= 1, (
            "Snack reward slot must exist in full surface"
        )

        browser.close()


@pytest.mark.browser
@pytest.mark.parametrize(
    "path, expected_title, next_content_selector",
    [
        ("domains/math/index.html", "수학 놀이", "#daily-goal-banner"),
        ("domains/korean/index.html", "국어 놀이", "#score-board"),
        ("domains/english/index.html", "영어 놀이", "#score-board"),
        ("domains/science/index.html", "과학 놀이", "#score-board"),
    ],
)
def test_learning_screens_compact_hud_browser(
    server: str, path: str, expected_title: str, next_content_selector: str
) -> None:
    """Core learning screens must render 1-line compact HUD without overlay or content overlap."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1024, "height": 768})
        page.goto(f"{server}/{path}", wait_until="networkidle")

        hud = page.locator("header.study-compact-hud")
        assert hud.is_visible(), f"{path} must show header.study-compact-hud"

        # Verify title
        title_el = hud.locator("h1.compact-hud-title")
        assert title_el.inner_text().strip() == expected_title

        # Verify home button
        home_btn = hud.locator("a.compact-hud-home")
        assert home_btn.is_visible()
        assert home_btn.get_attribute("data-action") == "go-home"

        # Verify gem-only reward surface
        gem_link = hud.locator("a.compact-gem-link")
        assert gem_link.is_visible(), f"{path} must show .compact-gem-link"
        assert page.locator("#inv-gems").is_visible(), "Gem count must be visible"

        # Verify non-gem items are NOT rendered in the HUD
        assert page.locator("#reward-inventory [data-type='youtube']").count() == 0, (
            f"{path} must not render YouTube slot in gem-only mode"
        )
        assert page.locator("#reward-inventory [data-type='snack']").count() == 0, (
            f"{path} must not render Snack slot in gem-only mode"
        )
        assert (
            page.locator("#reward-inventory [data-action='open-shop-modal']").count()
            == 0
        ), f"{path} must not render shop button in compact HUD"

        # Verify position is static/integrated (not fixed viewport overlay)
        inv = page.locator("#reward-inventory")
        computed_pos = inv.evaluate("el => window.getComputedStyle(el).position")
        assert computed_pos != "fixed", (
            f"{path} #reward-inventory must not be fixed overlay"
        )

        # Verify header does not overlap the next content section
        hud_box = hud.bounding_box()
        content_box = page.locator(next_content_selector).bounding_box()
        assert hud_box is not None and content_box is not None
        assert hud_box["y"] + hud_box["height"] <= content_box["y"] + 2, (
            f"{path}: compact HUD (bottom={hud_box['y'] + hud_box['height']}) overlaps "
            f"with content {next_content_selector} (top={content_box['y']})"
        )

        # Verify compact HUD height is thin (single line chrome <= 55px)
        assert hud_box["height"] <= 55, (
            f"{path}: compact HUD height is {hud_box['height']}px, exceeding 55px limit"
        )

        # Verify clicking gem link navigates to main hub reward surface
        gem_link.click()
        page.wait_for_load_state("networkidle")
        assert "index.html" in page.url, "Clicking gem must navigate to main hub"
        assert "#reward-inventory-mount" in page.url or "reward-inventory" in page.url

        browser.close()


@pytest.mark.browser
def test_no_mount_surface_does_not_inject_bar_browser(server: str) -> None:
    """Pages without #reward-inventory-mount must not have any reward bar injected into DOM."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        for no_mount_path in [
            "experiments/bubble/index.html",
            "domains/english/weekly-test/index.html",
        ]:
            page.goto(f"{server}/{no_mount_path}", wait_until="networkidle")
            assert page.locator("#reward-inventory").count() == 0, (
                f"{no_mount_path} should not have #reward-inventory injected"
            )

        browser.close()


@pytest.mark.browser
@pytest.mark.parametrize(
    "viewport_name, width, height",
    [
        ("desktop", 1280, 800),
        ("tablet_landscape", 1024, 768),
        ("tablet_portrait", 768, 1024),
        ("mobile_narrow", 390, 844),
    ],
)
def test_compact_hud_responsive_single_line_browser(
    server: str, viewport_name: str, width: int, height: int
) -> None:
    """Compact HUD must maintain a single line across desktop, tablet, and mobile."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(f"{server}/domains/math/index.html", wait_until="networkidle")

        hud = page.locator("header.study-compact-hud")
        box = hud.bounding_box()
        assert box is not None
        assert box["height"] <= 55, (
            f"At viewport {viewport_name} ({width}x{height}), HUD height was {box['height']}px (expected <= 55px)"
        )

        home = hud.locator("a.compact-hud-home")
        gem = hud.locator("a.compact-gem-link")
        title = hud.locator("h1.compact-hud-title")

        home_box = home.bounding_box()
        gem_box = gem.bounding_box()
        title_box = title.bounding_box()

        assert home_box and gem_box and title_box
        # Check all three elements are within viewport width
        assert home_box["x"] >= 0
        assert gem_box["x"] + gem_box["width"] <= width + 5

        browser.close()
