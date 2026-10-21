"""WCAG accessibility and contrast verification for top navigation and headers.

Ensures that text at the top of the interface across dark mode and dark
backgrounds complies with WCAG 2.1 AA (contrast >= 4.5:1 for normal text,
>= 3.0:1 for large text) and WCAG AAA (contrast >= 7.0:1) standards.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _linearize(channel: float) -> float:
    c = channel / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def wcag_relative_luminance(r: int, g: int, b: int) -> float:
    """Compute relative luminance according to WCAG 2.1 specification."""
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def wcag_contrast_ratio(
    rgb1: tuple[int, int, int], rgb2: tuple[int, int, int]
) -> float:
    """Compute WCAG contrast ratio between two RGB colors."""
    l1 = wcag_relative_luminance(*rgb1)
    l2 = wcag_relative_luminance(*rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def parse_hex_color(hex_str: str) -> tuple[int, int, int]:
    clean = hex_str.strip().lstrip("#")
    if len(clean) == 3:
        clean = "".join(c * 2 for c in clean)
    return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))


def test_main_hub_dark_background_contrast_standards() -> None:
    """Verify primary and muted text contrast against dark backgrounds."""
    bg_deep = parse_hex_color("#07090e")
    bg_panel = parse_hex_color("#0e121c")

    # Muted text (#CBD5E1 - Slate-300)
    muted_rgb = parse_hex_color("#CBD5E1")
    ratio_deep_muted = wcag_contrast_ratio(muted_rgb, bg_deep)
    ratio_panel_muted = wcag_contrast_ratio(muted_rgb, bg_panel)

    # Must exceed WCAG AAA (7.0:1) for normal text
    assert ratio_deep_muted >= 7.0, (
        f"Muted text on deep background must satisfy WCAG AAA (>= 7:1), got {ratio_deep_muted:.2f}:1"
    )
    assert ratio_panel_muted >= 7.0, (
        f"Muted text on panel background must satisfy WCAG AAA (>= 7:1), got {ratio_panel_muted:.2f}:1"
    )

    # Subtitle text (#E2E8F0 - Slate-200)
    subtitle_rgb = parse_hex_color("#E2E8F0")
    ratio_deep_subtitle = wcag_contrast_ratio(subtitle_rgb, bg_deep)
    assert ratio_deep_subtitle >= 10.0, (
        f"Subtitle text must have strong contrast on dark background, got {ratio_deep_subtitle:.2f}:1"
    )

    # Neon volt accent (#D7FF00)
    neon_rgb = parse_hex_color("#d7ff00")
    ratio_neon_deep = wcag_contrast_ratio(neon_rgb, bg_deep)
    assert ratio_neon_deep >= 7.0, (
        f"Neon volt on deep background must satisfy WCAG AAA, got {ratio_neon_deep:.2f}:1"
    )


def test_styles_css_top_hud_and_header_readability() -> None:
    """Ensure styles.css contains high-contrast rules for top HUD and arena header."""
    styles = (ROOT / "styles.css").read_text(encoding="utf-8")

    # 1. Global --muted variable updated for dark-mode readability
    assert "--muted: #CBD5E1;" in styles

    # 2. Arena subtitle readability
    assert ".arena-subtitle" in styles
    assert "color: #E2E8F0;" in styles

    # 3. Brand home affordance is styled by the shared HUD sheet
    hud_css = (ROOT / "shared/ui/hud.css").read_text(encoding="utf-8")
    assert ".ag-hud__brand-home" in hud_css
    assert ".ag-hud__brand-home svg" in hud_css
    assert "color: #E2E8F0;" in styles

    # 4. Reward inventory empty slot readability (no unreadable dark text or low opacity)
    assert ".hud-reward-mount #reward-inventory .inventory-item.empty-slot" in styles
    empty_slot_match = re.search(
        r"\.hud-reward-mount #reward-inventory \.inventory-item\.empty-slot\s*\{([^}]+)\}",
        styles,
    )
    assert empty_slot_match is not None, "empty-slot rule missing in styles.css"
    empty_slot_body = empty_slot_match.group(1)
    assert "#CBD5E1" in empty_slot_body, "empty-slot must use high-contrast #CBD5E1"
    assert "opacity: 0.95" in empty_slot_body, "empty-slot opacity must be >= 0.9"

    # 5. Reward inventory active slot (.has-reward and general .val / .unit / auth)
    assert ".hud-reward-mount #reward-inventory .inventory-item .val" in styles
    assert "color: #FFFFFF !important;" in styles
    assert ".hud-reward-mount #reward-inventory .inventory-item .unit" in styles
    assert "color: #E2E8F0 !important;" in styles
    assert ".hud-reward-mount #reward-inventory #inv-auth" in styles


def test_reward_inventory_dark_mode_stylesheet_contrast() -> None:
    """Ensure domains/reward/reward.css enforces high contrast across all inventory items."""
    reward_css = (ROOT / "domains/reward/reward.css").read_text(encoding="utf-8")
    reward_ui = (ROOT / "domains/reward/reward_ui.js").read_text(encoding="utf-8")

    # 1. Dark mode rules in reward.css explicitly prevent #1a1a1a from leaking into dark mode
    assert ".dark #reward-inventory .inventory-item .val" in reward_css
    assert "color: #FFFFFF;" in reward_css
    assert ".dark #reward-inventory .inventory-item .unit" in reward_css
    assert "color: #E2E8F0;" in reward_css
    assert ".dark #reward-inventory #inv-auth" in reward_css

    # 2. Critical styles in reward_ui.js guarantee high-contrast text before external CSS loads
    assert ".dark #reward-inventory .inventory-item .val" in reward_ui
    assert "color: #FFFFFF !important;" in reward_ui
    assert ".dark #reward-inventory #inv-auth" in reward_ui


def test_index_html_top_header_accessibility_markup() -> None:
    """Ensure index.html top header elements meet accessibility and readability standards."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    # 1. Version badge has accessible font size (>= 11px) and high-contrast color
    assert "text-[11px]" in html or "text-xs" in html
    assert "text-slate-100" in html or "text-white" in html

    # 2. HUD brand wordmark is clearly visible
    assert "ag-hud__brand-word" in html
    assert "text-[#d7ff00]" in html
    assert "ag-hud__brand-home" in html

    # 3. Arena header badge has clear contrast
    assert "INTERACTIVE LEARNING PLAYGROUND" in html

    # 4. Arena subtitle has clear guidance text
    assert "오늘은 어떤 배움을 시작해볼까요?" in html


def test_domain_base_stylesheets_muted_contrast() -> None:
    """Ensure domain base.css files use high-contrast text tokens."""
    for domain in ("math", "english", "korean", "science"):
        base_css = (ROOT / f"domains/{domain}/base.css").read_text(encoding="utf-8")
        assert "--muted: #CBD5E1;" in base_css, (
            f"domains/{domain}/base.css must define high-contrast --muted"
        )
        assert ".brand-category" in base_css
        assert "#CBD5E1" in base_css, (
            f"domains/{domain}/base.css brand-category must use #CBD5E1"
        )
