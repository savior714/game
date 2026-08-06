"""Focused browser test for quiz focus-visible indicators.

Verifies that the four subject quiz pages (korean, english, science, math)
render a visible keyboard focus indicator on core quiz controls when focused
via keyboard tab navigation.

Acceptance (focus-visible contract):
  - element.matches(':focus-visible') === true
  - computed outline-style === "solid"
  - computed outline-width >= 3px

Hidden controls (#next-btn, #restart-btn, #close-stats-btn, #reset-stats-btn)
are verified via static CSS selector coverage only — the test does not progress
the game to reveal them.
"""

from __future__ import annotations

import http.server
import json
import socketserver
import threading
import time
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
PORT = 18910
SUBJECTS = ["korean", "english", "science", "math"]

PRIMARY_COLORS: dict[str, str] = {
    "korean": "rgb(103, 58, 183)",
    "english": "rgb(45, 125, 210)",
    "science": "rgb(45, 125, 210)",
    "math": "rgb(255, 107, 53)",
}

INITIAL_FOCUS_TARGETS = (".home-link", "#stats-btn", ".answer-btn")

FOCUS_VISIBLE_SELECTORS_BY_SUBJECT: dict[str, tuple[str, ...]] = {
    "korean": (
        ".home-link:focus-visible",
        "#stats-btn:focus-visible",
        "#next-btn:focus-visible",
        "#restart-btn:focus-visible",
        "#close-stats-btn:focus-visible",
        "#reset-stats-btn:focus-visible",
    ),
    "english": (
        ".home-link:focus-visible",
        "#stats-btn:focus-visible",
        "#next-btn:focus-visible",
        "#restart-btn:focus-visible",
        "#close-stats-btn:focus-visible",
        "#reset-stats-btn:focus-visible",
    ),
    "science": (
        ".home-link:focus-visible",
        "#stats-btn:focus-visible",
        "#next-btn:focus-visible",
        "#restart-btn:focus-visible",
        "#close-stats-btn:focus-visible",
        "#reset-stats-btn:focus-visible",
    ),
    "math": (
        ".home-link:focus-visible",
        "#stats-btn:focus-visible",
        "#next-btn:focus-visible",
        "#restart-btn:focus-visible",
        "#close-stats-btn:focus-visible",
        "#reset-stats-btn:focus-visible",
    ),
}


class HTTPServerFixture:
    """Static HTTP server for repo root."""

    def __init__(self) -> None:
        self.server: http.server.HTTPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> str:
        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(REPO_ROOT)

            socketserver.TCPServer.allow_reuse_address = True

            class QuietHandler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
                    super().__init__(  # type: ignore[no-untyped-call]
                        *args, directory=str(REPO_ROOT), **kwargs
                    )

                def log_message(self, format: str, *args: object) -> None:  # type: ignore[override]
                    pass

            self.server = socketserver.TCPServer(
                ("127.0.0.1", PORT), QuietHandler
            )
            self.thread = threading.Thread(
                target=self.server.serve_forever, daemon=True
            )
            self.thread.start()
            time.sleep(0.5)
            return f"http://127.0.0.1:{PORT}"
        finally:
            os.chdir(original_cwd)

    def stop(self) -> None:
        if self.server is not None:
            self.server.shutdown()


@pytest.fixture(scope="session")
def server() -> str:
    srv = HTTPServerFixture()
    url = srv.start()
    yield url
    srv.stop()


@pytest.fixture
def page(server: str):
    """Create a fresh page with fresh storage for each test."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
        )
        pg = context.new_page()
        pg.goto(f"{server}/domains/korean/index.html?v=focus")
        pg.wait_for_load_state("domcontentloaded")
        pg.evaluate(
            "() => { localStorage.clear(); sessionStorage.clear(); }"
        )
        pg.wait_for_selector("#question", state="visible", timeout=5000)
        pg.wait_for_selector(".answer-btn", state="visible", timeout=5000)
        yield pg
        context.close()
        browser.close()


def _focus_via_keyboard_tab(pg, selector: str) -> None:
    """Press Tab until the given selector receives keyboard focus."""
    for _ in range(20):
        pg.keyboard.press("Tab")
        matches = pg.evaluate(
            f"""() => {{
                const el = document.querySelector('{selector}');
                return el === document.activeElement &&
                       el !== null &&
                       el.matches(':focus-visible');
            }}"""
        )
        if matches:
            return
    pytest.fail(f"Could not reach keyboard focus on {selector} via Tab")


def _computed_focus_info(pg, selector: str) -> dict[str, object]:
    """Return computed focus-visible style info for the focused element."""
    raw = pg.evaluate(
        f"""() => {{
            const el = document.querySelector('{selector}');
            if (!el) return null;
            const s = getComputedStyle(el);
            return JSON.stringify({{
                matchesFocusVisible: el.matches(':focus-visible'),
                outlineStyle: s.outlineStyle,
                outlineWidth: s.outlineWidth,
                outlineColor: s.outlineColor,
            }});
        }}"""
    )
    assert raw is not None, f"Element {selector} not found"
    return json.loads(raw)  # type: ignore[return-value]


def _assert_focus_visible_contract(info: dict[str, object]) -> None:
    """Assert the three-part focus-visible contract."""
    assert info["matchesFocusVisible"] is True, (
        f"Element is not :focus-visible; computed={info}"
    )
    assert info["outlineStyle"] == "solid", (
        f"outline-style is not 'solid': {info['outlineStyle']}"
    )
    width_px = int(info["outlineWidth"].replace("px", ""))
    assert width_px >= 3, (
        f"outline-width is {info['outlineWidth']} (< 3px)"
    )


@pytest.mark.browser
class TestQuizFocusVisible:
    """Keyboard focus-visible indicators on quiz controls."""

    @pytest.mark.parametrize("subject", SUBJECTS)
    def test_home_link_has_focus_visible(
        self, server: str, subject: str
    ) -> None:
        """`.home-link` shows solid >=3px outline on keyboard focus."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 720}
            )
            pg = context.new_page()
            url = f"{server}/domains/{subject}/index.html?v=focus-home"
            pg.goto(url)
            pg.wait_for_load_state("domcontentloaded")
            pg.evaluate(
                "() => { localStorage.clear(); sessionStorage.clear(); }"
            )
            pg.wait_for_selector("#question", state="visible", timeout=5000)
            pg.wait_for_selector(".answer-btn", state="visible", timeout=5000)

            _focus_via_keyboard_tab(pg, ".home-link")
            info = _computed_focus_info(pg, ".home-link")
            _assert_focus_visible_contract(info)

            expected_color = PRIMARY_COLORS[subject]
            assert info["outlineColor"] == expected_color, (
                f"outline-color {info['outlineColor']} != "
                f"expected {expected_color}"
            )

            context.close()
            browser.close()

    @pytest.mark.parametrize("subject", SUBJECTS)
    def test_stats_button_has_focus_visible(
        self, server: str, subject: str
    ) -> None:
        """`#stats-btn` shows solid >=3px outline on keyboard focus."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 720}
            )
            pg = context.new_page()
            url = f"{server}/domains/{subject}/index.html?v=focus-stats"
            pg.goto(url)
            pg.wait_for_load_state("domcontentloaded")
            pg.evaluate(
                "() => { localStorage.clear(); sessionStorage.clear(); }"
            )
            pg.wait_for_selector("#question", state="visible", timeout=5000)
            pg.wait_for_selector(".answer-btn", state="visible", timeout=5000)

            _focus_via_keyboard_tab(pg, "#stats-btn")
            info = _computed_focus_info(pg, "#stats-btn")
            _assert_focus_visible_contract(info)

            expected_color = PRIMARY_COLORS[subject]
            assert info["outlineColor"] == expected_color, (
                f"outline-color {info['outlineColor']} != "
                f"expected {expected_color}"
            )

            context.close()
            browser.close()

    @pytest.mark.parametrize("subject", SUBJECTS)
    def test_answer_button_has_focus_visible(
        self, server: str, subject: str
    ) -> None:
        """First `.answer-btn` shows solid >=3px outline on keyboard focus."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 720}
            )
            pg = context.new_page()
            url = f"{server}/domains/{subject}/index.html?v=focus-answer"
            pg.goto(url)
            pg.wait_for_load_state("domcontentloaded")
            pg.evaluate(
                "() => { localStorage.clear(); sessionStorage.clear(); }"
            )
            pg.wait_for_selector("#question", state="visible", timeout=5000)
            pg.wait_for_selector(".answer-btn", state="visible", timeout=5000)

            _focus_via_keyboard_tab(pg, ".answer-btn")
            info = _computed_focus_info(pg, ".answer-btn")
            _assert_focus_visible_contract(info)

            expected_color = PRIMARY_COLORS[subject]
            assert info["outlineColor"] == expected_color, (
                f"outline-color {info['outlineColor']} != "
                f"expected {expected_color}"
            )

            context.close()
            browser.close()


@pytest.mark.browser
class TestQuizFocusVisibleStaticCoverage:
    """Static CSS selector coverage for hidden quiz controls."""

    @pytest.mark.parametrize("subject", SUBJECTS)
    def test_hidden_control_selectors_in_css(
        self, server: str, subject: str
    ) -> None:
        """CSS file declares :focus-visible rules for hidden controls."""
        css_path = (
            REPO_ROOT
            / "domains"
            / subject
            / "base.css"
        )
        css_text = css_path.read_text(encoding="utf-8")

        required = FOCUS_VISIBLE_SELECTORS_BY_SUBJECT[subject]
        for selector in required:
            assert selector in css_text, (
                f"Missing :focus-visible selector '{selector}' "
                f"in {subject}/base.css"
            )

    @pytest.mark.parametrize("subject", SUBJECTS)
    def test_hidden_control_rules_have_outline(
        self, server: str, subject: str
    ) -> None:
        """All hidden control :focus-visible selectors share an outline block."""
        import re

        css_path = (
            REPO_ROOT
            / "domains"
            / subject
            / "base.css"
        )
        css_text = css_path.read_text(encoding="utf-8")

        required = FOCUS_VISIBLE_SELECTORS_BY_SUBJECT[subject]
        for selector in required:
            pattern = re.escape(selector) + r"[^{]*\{([^}]+)\}"
            match = re.search(pattern, css_text)
            assert match is not None, (
                f"Rule block not found for '{selector}' in "
                f"{subject}/base.css"
            )
            body = match.group(1)
            assert "outline" in body, (
                f"'{selector}' block missing 'outline' declaration"
            )
            assert "solid" in body, (
                f"'{selector}' block missing 'solid' outline style"
            )
            width_match = re.search(
                r"outline(?:-width)?\s*:\s*(\d+)px", body
            )
            assert width_match is not None, (
                f"'{selector}' block missing outline width >= 3px"
            )
            assert int(width_match.group(1)) >= 3, (
                f"'{selector}' outline width "
                f"{width_match.group(1)}px < 3px"
            )
