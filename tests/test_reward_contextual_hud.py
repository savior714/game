"""Structural contract tests for contextual single-owner HUD and reward surface opt-in.

Verifies:
1. Main hub (index.html) has full reward surface mount.
2. Core learning screens (math, korean, english, science) have compact single-owner HUD with gem-only surface.
3. No old large branding or nested HUD anchors exist in learning screens.
4. RewardSystemUI has NO document.body.prepend fallback when mount is absent.
5. In gem-only mode, only the gem item is rendered, pointing to main hub reward surface.
6. Body padding manipulation is removed from applyBodyTopOffset.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REWARD_UI_PATH = REPO_ROOT / "domains" / "reward" / "reward_ui.js"
REWARD_CSS_PATH = REPO_ROOT / "domains" / "reward" / "reward.css"


class ElementFinder(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.elements: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.elements.append((tag, dict(attrs)))


def test_main_hub_has_full_reward_mount() -> None:
    """Main hub index.html must retain its full reward surface mount."""
    index_html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
    parser = ElementFinder()
    parser.feed(index_html)

    mounts = [
        attrs
        for tag, attrs in parser.elements
        if tag == "div" and attrs.get("id") == "reward-inventory-mount"
    ]
    assert len(mounts) == 1, "index.html must have exactly one #reward-inventory-mount"
    assert mounts[0].get("data-reward-surface") == "full"


def test_core_learning_screens_have_compact_hud_and_gem_only_mount() -> None:
    """Core learning screens must have compact HUD with single owner and gem-only reward mount."""
    expected_subjects = {
        "domains/math/index.html": "수학 놀이",
        "domains/korean/index.html": "국어 놀이",
        "domains/english/index.html": "영어 놀이",
        "domains/science/index.html": "과학 놀이",
    }

    for rel_path, subject_title in expected_subjects.items():
        file_path = REPO_ROOT / rel_path
        assert file_path.exists(), f"File {rel_path} does not exist"
        html = file_path.read_text(encoding="utf-8")

        # 1. Must contain study-compact-hud header
        assert (
            'class="study-compact-hud"' in html or "class='study-compact-hud'" in html
        ), f'{rel_path} must have <header class="study-compact-hud">'

        # 2. Must NOT contain the old large brand badge / console-hud
        assert 'class="home-link console-hud"' not in html, (
            f'{rel_path} still has old <a class="home-link console-hud"> wrapper'
        )
        # Extract header content
        header_start = html.find('<header class="study-compact-hud"')
        header_end = html.find("</header>", header_start)
        assert header_start != -1 and header_end != -1, f"{rel_path} header not found"
        header_html = html[header_start:header_end]

        assert "brand-badge" not in header_html, f"{rel_path} header has brand-badge"
        assert "v2.0" not in header_html, f"{rel_path} header has v2.0"
        assert "AIDEN GAME LABS" not in header_html, (
            f"{rel_path} should not display large 'AIDEN GAME LABS' branding in learning HUD"
        )

        # 3. Must have compact home button with data-action="go-home"
        assert 'data-action="go-home"' in html, (
            f'{rel_path} compact home link must have data-action="go-home"'
        )
        assert "compact-hud-home" in html, f"{rel_path} must use .compact-hud-home"

        # 4. Must have the exact subject title in h1.compact-hud-title
        assert f'<h1 class="compact-hud-title">{subject_title}</h1>' in html, (
            f'{rel_path} must have <h1 class="compact-hud-title">{subject_title}</h1>'
        )

        # 5. Must have gem-only reward mount
        parser = ElementFinder()
        parser.feed(html)
        mounts = [
            attrs
            for tag, attrs in parser.elements
            if tag == "div" and attrs.get("id") == "reward-inventory-mount"
        ]
        assert len(mounts) == 1, (
            f"{rel_path} must have exactly one #reward-inventory-mount"
        )
        assert mounts[0].get("data-reward-surface") == "gem-only", (
            f'{rel_path} #reward-inventory-mount must declare data-reward-surface="gem-only"'
        )


def test_reward_ui_no_mount_fallback_removed() -> None:
    """RewardSystemUI must not inject global fixed inventory bar into body when mount is missing."""
    code = REWARD_UI_PATH.read_text(encoding="utf-8")

    # Ensure document.body.prepend(bar) is completely gone
    assert "document.body.prepend" not in code, (
        "RewardSystemUI should not use document.body.prepend() to force a global top bar"
    )

    # In injectInventoryBar, there must be an early return if mountTarget is missing
    start = code.find("function injectInventoryBar(state)")
    assert start != -1, "injectInventoryBar function not found"
    block = code[start : start + 600]

    assert "if (!mountTarget)" in block, (
        "injectInventoryBar must check if (!mountTarget) and return early"
    )
    assert "return;" in block, (
        "injectInventoryBar must return when mountTarget is absent"
    )


def test_reward_ui_gem_only_surface_mode() -> None:
    """RewardSystemUI must support gem-only surface mode rendering only the gem navigation link."""
    code = REWARD_UI_PATH.read_text(encoding="utf-8")

    assert (
        "surfaceMode === 'gem-only'" in code or 'surfaceMode === "gem-only"' in code
    ), "injectInventoryBar must handle gem-only surface mode"
    assert "compact-gem-link" in code, "gem-only mode must use compact-gem-link"
    assert "resolveMainHubUrl" in code, (
        "gem-only mode must resolve main hub URL for navigation"
    )


def test_apply_body_top_offset_does_not_modify_body_padding() -> None:
    """applyBodyTopOffset should not dynamically push body padding down."""
    code = REWARD_UI_PATH.read_text(encoding="utf-8")

    start = code.find("function applyBodyTopOffset()")
    assert start != -1, "applyBodyTopOffset function not found"
    block = code[start : start + 400]

    assert "document.body.style.paddingTop" not in block, (
        "applyBodyTopOffset must not manipulate document.body.style.paddingTop"
    )


def test_no_mount_pages_do_not_have_reward_mount() -> None:
    """Immersive and game pages should not have #reward-inventory-mount by default."""
    no_mount_pages = [
        "ocean-rescue/index.html",
        "experiments/bubble/index.html",
        "experiments/marble/index.html",
        "domains/english/weekly-test/index.html",
    ]

    for rel_path in no_mount_pages:
        html = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert 'id="reward-inventory-mount"' not in html, (
            f"{rel_path} should not have #reward-inventory-mount"
        )
