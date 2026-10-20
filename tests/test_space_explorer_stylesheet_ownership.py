from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SPACE_EXPLORER_DIR = ROOT / "experiments" / "space-explorer"


def test_space_explorer_stylesheet_ownership_separation() -> None:
    """Dino Escape owns its stylesheet; sibling mini-games keep the shared shell."""
    index_html = (SPACE_EXPLORER_DIR / "index.html").read_text(encoding="utf-8")
    dino_html = (SPACE_EXPLORER_DIR / "dino-escape.html").read_text(encoding="utf-8")
    orbit_html = (SPACE_EXPLORER_DIR / "orbit-eclipse.html").read_text(encoding="utf-8")
    paint_html = (SPACE_EXPLORER_DIR / "paint-mixing.html").read_text(encoding="utf-8")

    assert 'href="./space-explorer.css"' in index_html or 'href="space-explorer.css"' in index_html
    assert "space-explorer-minigames.css" not in index_html

    # The rebuilt Dino Escape is a standalone full-screen 3D experience.
    assert 'href="./dino-escape.css"' in dino_html
    assert "space-explorer-minigames.css" not in dino_html
    assert 'href="./space-explorer.css"' not in dino_html and 'href="space-explorer.css"' not in dino_html

    for filename, html in [
        ("orbit-eclipse.html", orbit_html),
        ("paint-mixing.html", paint_html),
    ]:
        assert 'href="./space-explorer-minigames.css"' in html or 'href="space-explorer-minigames.css"' in html
        assert 'href="./space-explorer.css"' not in html and 'href="space-explorer.css"' not in html
        assert "dino-escape.css" not in html, f"{filename} must not link the dino stylesheet"


def test_dino_escape_stylesheet_has_required_contracts() -> None:
    """The standalone dino stylesheet must cover the full-screen HUD shell."""
    css_path = SPACE_EXPLORER_DIR / "dino-escape.css"
    assert css_path.exists(), "dino-escape.css must exist"
    css = css_path.read_text(encoding="utf-8")

    required = [
        ".game-canvas",
        ".hud",
        ".hud[data-visible=\"true\"]",
        ".rexcam-window",
        ".rexcam-glass",
        ".toast",
        ".biome-banner",
        ".touch-controls",
        ".screen--start",
        ".screen--panel",
        ".screen--modal",
        ".segmented",
        ".switch",
        "prefers-reduced-motion",
    ]
    for selector in required:
        assert selector in css, f"Missing dino stylesheet contract: {selector}"

    assert "@media (max-width: 860px)" in css
    assert "@media (max-height: 640px) and (orientation: landscape)" in css


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

    # The dino page moved to its own stylesheet; the shared shell keeps the
    # orbit + paint contracts only.
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

    # 3D backdrop layering contract — the starfield/lights overlay must be
    # absolutely positioned inside its scene wrapper and never take flow space
    # (regression guard for the "backdrop playing separately" bug).
    assert re.search(r"\.three-layer\s*\{[^}]*position:\s*absolute", css), (
        ".three-layer must be position: absolute"
    )
    assert re.search(r"\.three-layer\s*\{[^}]*pointer-events:\s*none", css), (
        ".three-layer must be pointer-events: none"
    )
    assert re.search(r"\.three-layer\s*\{[^}]*z-index:\s*1", css), (
        ".three-layer must sit behind the 2D canvas (z-index: 1)"
    )

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
    css = (SPACE_EXPLORER_DIR / "space-explorer-minigames.css").read_text(
        encoding="utf-8"
    )

    # Should not have 'html, body' or 'html,body' with overflow: hidden
    pattern = re.compile(
        r"html\s*,\s*body\s*\{[^}]*overflow\s*:\s*hidden", re.IGNORECASE
    )
    assert not pattern.search(css), (
        "space-explorer-minigames.css must not lock html,body overflow to hidden"
    )
