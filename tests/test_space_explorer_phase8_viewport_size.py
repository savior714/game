from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT
SPACE_EXPLORER_DIR = TEMPLATES / "experiments" / "space-explorer"


def test_space_explorer_layout_is_wider_than_default_container() -> None:
    css = (
        TEMPLATES / "experiments" / "space-explorer" / "space-explorer.css"
    ).read_text(encoding="utf-8")

    assert ".explorer-layout" in css
    assert "max-width: 1320px" in css


def test_renderer_uses_larger_minimum_canvas_size() -> None:
    renderer_js = (SPACE_EXPLORER_DIR / "renderer.js").read_text(encoding="utf-8")

    assert "Math.max(900" in renderer_js
    assert "Math.max(560" in renderer_js
