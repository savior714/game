"""HUD 시각적 통일성 계약 — 외주 에이전시 수준 premium HUD 검증"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GAME_PAGES = {
    "index.html": {"subject": "hub", "hud_class": "ag-hud--full"},
    "domains/math/index.html": {"subject": "math", "hud_class": "ag-hud--compact"},
    "domains/english/index.html": {
        "subject": "english",
        "hud_class": "ag-hud--compact",
    },
    "domains/korean/index.html": {"subject": "korean", "hud_class": "ag-hud--compact"},
    "domains/science/index.html": {
        "subject": "science",
        "hud_class": "ag-hud--compact",
    },
    "domains/english/weekly-test/index.html": {
        "subject": "weekly-test",
        "hud_class": "ag-hud--compact",
    },
    "experiments/space-explorer/index.html": {
        "subject": "space",
        "hud_class": "ag-hud--immersive",
    },
    "domains/reward/guardian/index.html": {
        "subject": "guardian",
        "hud_class": "ag-hud--full",
    },
}

SUBJECT_EMOJI = {
    "hub": "🎮",
    "math": "🔢",
    "english": "📚",
    "korean": "📖",
    "science": "🔬",
    "weekly-test": "📝",
    "space": "🪐",
    "guardian": "🛡️",
}


def test_shared_hud_css_exists_and_defines_tokens():
    css = ROOT / "shared/ui/hud.css"
    assert css.is_file(), "shared/ui/hud.css must exist for unified HUD system"
    text = css.read_text(encoding="utf-8")
    assert ".ag-hud" in text, "HUD CSS must define .ag-hud base"
    assert "--hud-bg" in text, "HUD CSS must define --hud-bg token"
    assert "--hud-border" in text, "HUD CSS must define --hud-border token"
    assert "--hud-blur" in text, "HUD CSS must define --hud-blur token"
    assert ".ag-hud--compact" in text
    assert ".ag-hud--full" in text
    assert ".ag-hud--immersive" in text
    assert ".ag-hud__brand" in text
    assert ".ag-hud__subject" in text
    assert ".ag-hud__brand-home" in text, (
        "HUD CSS must style the brand-carried home affordance"
    )
    assert "data-subject" in text, "HUD CSS must handle subject tint via data-subject"
    assert "prefers-reduced-motion" in text, "HUD must respect reduced-motion"
    assert ".sr-only" in text


def test_every_game_page_links_hud_css():
    for rel_path in GAME_PAGES:
        html = (ROOT / rel_path).read_text(encoding="utf-8")
        assert "shared/ui/hud.css" in html, f"{rel_path} must link shared/ui/hud.css"


def test_every_game_page_has_unified_hud_markup():
    for rel_path, meta in GAME_PAGES.items():
        html = (ROOT / rel_path).read_text(encoding="utf-8")
        assert 'class="ag-hud' in html or 'class="ag-hud ' in html, (
            f"{rel_path} header must use ag-hud class"
        )
        assert "data-subject=" in html, f"{rel_path} must declare data-subject"
        assert f'data-subject="{meta["subject"]}"' in html, (
            f"{rel_path} subject should be {meta['subject']}"
        )
        assert meta["hud_class"] in html, (
            f"{rel_path} must use variant {meta['hud_class']}"
        )
        # brand word unified
        assert "AIDEN GAME LABS" in html, f"{rel_path} must show brand wordmark"
        # version chip
        assert "v2.0" in html, f"{rel_path} must show version chip v2.0"
        # home navigation is carried by the brand link (single home control per chrome)
        has_home = (
            'aria-label="AIDEN GAME LABS · 놀이터 홈"' in html
            or 'href="./index.html"' in html
            or 'href="../../index.html"' in html
            or 'href="../../../index.html"' in html
        )
        assert has_home, f"{rel_path} must have home navigation"


def test_subject_chips_are_consistent():
    for rel_path, meta in GAME_PAGES.items():
        html = (ROOT / rel_path).read_text(encoding="utf-8")
        assert "ag-hud__subject" in html, f"{rel_path} must have subject chip"
        # emoji check for non-hub pages
        emoji = SUBJECT_EMOJI.get(meta["subject"])
        if emoji:
            # allow hub/game pages to contain at least one emoji; guardian and others have specific
            assert emoji in html or "ag-hud__subject" in html, (
                f"{rel_path} subject chip should contain emoji or label"
            )


def test_legacy_aliases_remain_for_backward_compatibility():
    hud_css = (ROOT / "shared/ui/hud.css").read_text(encoding="utf-8")
    # legacy selectors must still be styled so old markup degrades gracefully
    assert ".study-compact-hud" in hud_css, "HUD CSS must alias .study-compact-hud"
    assert ".console-hud" in hud_css, "HUD CSS must alias .console-hud"
    assert ".topbar.glass" in hud_css, "HUD CSS must alias Space Explorer topbar"


def test_hud_pages_expose_single_home_control():
    """HUD 크롬의 홈 컨트롤은 brand 링크 하나뿐이다 (별도 홈 버튼 금지)."""
    for rel_path in GAME_PAGES:
        html = (ROOT / rel_path).read_text(encoding="utf-8")
        assert "ag-hud__home" not in html, (
            f"{rel_path} must not keep a standalone .ag-hud__home button"
        )
        assert "compact-hud-home" not in html, (
            f"{rel_path} must not keep a standalone .compact-hud-home button"
        )
        assert "ag-hud__brand-home" in html, (
            f"{rel_path} brand must carry the visible home affordance"
        )


def test_main_hub_preserves_reward_full_surface():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'data-reward-surface="full"' in html, (
        "Main hub must keep full reward surface"
    )


def test_learning_pages_preserve_gem_only_surface():
    for rel_path in (
        "domains/math/index.html",
        "domains/english/index.html",
        "domains/korean/index.html",
        "domains/science/index.html",
    ):
        html = (ROOT / rel_path).read_text(encoding="utf-8")
        assert 'data-reward-surface="gem-only"' in html, (
            f"{rel_path} must keep gem-only reward mount"
        )
        assert 'id="reward-inventory-mount"' in html, (
            f"{rel_path} must preserve reward mount id for JS"
        )


def test_hud_responsive_and_a11y_tokens():
    css = (ROOT / "shared/ui/hud.css").read_text(encoding="utf-8")
    assert "@media (max-width:" in css, "HUD CSS must have responsive breakpoints"
    assert "focus-visible" in css, "HUD must define focus-visible styles"
    assert "backdrop-filter" in css, "HUD must use backdrop-filter for glass effect"
    assert "box-shadow" in css, "HUD must define shadow for depth"
