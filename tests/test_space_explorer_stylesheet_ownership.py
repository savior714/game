from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SPACE_EXPLORER_DIR = ROOT / "experiments" / "space-explorer"


def test_space_explorer_stylesheet_ownership_separation() -> None:
    """Ensure fullscreen 3D solar system and legacy sibling mini-games have separated stylesheet ownership."""
    index_html = (SPACE_EXPLORER_DIR / "index.html").read_text(encoding="utf-8")
    dino_html = (SPACE_EXPLORER_DIR / "dino-escape.html").read_text(encoding="utf-8")
    orbit_html = (SPACE_EXPLORER_DIR / "orbit-eclipse.html").read_text(encoding="utf-8")
    paint_html = (SPACE_EXPLORER_DIR / "paint-mixing.html").read_text(encoding="utf-8")

    # index.html MUST link space-explorer.css (fullscreen Three.js simulation)
    assert 'href="./space-explorer.css"' in index_html or 'href="space-explorer.css"' in index_html
    assert "space-explorer-minigames.css" not in index_html

    # The 3 sibling minigame pages MUST link space-explorer-minigames.css
    for filename, html in [
        ("dino-escape.html", dino_html),
        ("orbit-eclipse.html", orbit_html),
        ("paint-mixing.html", paint_html),
    ]:
        assert (
            'href="./space-explorer-minigames.css"' in html
            or 'href="space-explorer-minigames.css"' in html
        ), f"{filename} must use space-explorer-minigames.css"
        # Must not re-couple to the fullscreen stylesheet
        assert (
            'href="./space-explorer.css"' not in html
            and 'href="space-explorer.css"' not in html
        ), f"{filename} must NOT link space-explorer.css"


def test_minigames_stylesheet_has_required_contracts() -> None:
    """Ensure space-explorer-minigames.css contains all required UI and responsive contracts."""
    css_path = SPACE_EXPLORER_DIR / "space-explorer-minigames.css"
    assert css_path.exists(), "space-explorer-minigames.css must exist"
    css = css_path.read_text(encoding="utf-8")

    # Shared shell contracts
    required_shell = [
        "body.se-page",
        ".console-bg-glow",
        ".site-header",
        ".hud-left-section",
        ".brand-badge",
        ".brand-dot",
        ".brand-subline",
        ".brand-title",
        ".brand-version",
        ".brand-category",
        ".nav-list",
        ".container",
        ".card",
        ".controls-panel",
    ]
    for selector in required_shell:
        assert selector in css, f"Missing shell contract: {selector}"

    # Layout contracts
    for layout in [".dino-layout", ".lesson-layout", ".mix-layout"]:
        assert layout in css, f"Missing layout contract: {layout}"

    # Dino minigame contracts
    required_dino = [
        ".dino-canvas",
        ".hud-grid",
        ".hud-item",
        "#dino-status",
        ".progress-track",
        ".progress-fill",
        "#dino-restart-button",
        "#dino-touch-controls",
        ".touch-btn",
        ".chase-settings",
        ".chase-settings-grid",
    ]
    for selector in required_dino:
        assert selector in css, f"Missing dino contract: {selector}"

    # Orbit & Eclipse contracts
    required_orbit = [
        ".lesson-canvas",
        "#lesson-explanation",
        ".control-group",
        ".speed-control",
        ".status-badge",
    ]
    for selector in required_orbit:
        assert selector in css, f"Missing orbit contract: {selector}"

    # Paint mixing contracts
    required_paint = [
        ".palette",
        ".color-chip",
        ".result-swatch-wrap",
        ".result-swatch",
        ".beaker",
        ".liquid-layer",
        ".drop-layer",
        ".paint-drop",
        ".drop-ripple",
        ".pipette",
    ]
    for selector in required_paint:
        assert selector in css, f"Missing paint contract: {selector}"

    # Responsive rules
    assert "@media (max-width: 960px)" in css
    assert "@media (max-width: 900px)" in css


def test_minigames_stylesheet_does_not_contain_fullscreen_overflow_lock() -> None:
    """Ensure minigames stylesheet does NOT trap scroll flow with fullscreen html,body { overflow: hidden }."""
    css = (SPACE_EXPLORER_DIR / "space-explorer-minigames.css").read_text(encoding="utf-8")

    # Should not have 'html, body' or 'html,body' with overflow: hidden
    pattern = re.compile(r"html\s*,\s*body\s*\{[^}]*overflow\s*:\s*hidden", re.IGNORECASE)
    assert not pattern.search(css), "space-explorer-minigames.css must not lock html,body overflow to hidden"
