from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT


def test_render_mode_controls_and_accessibility_markup_exist() -> None:
    html = (TEMPLATES / "experiments" / "space-explorer" / "index.html").read_text(
        encoding="utf-8"
    )
    assert 'id="render-quality"' in html
    assert 'option value="2d"' in html
    assert 'option value="3d"' in html
    assert "2D" in html
    assert "3D" in html
    assert 'aria-describedby="simulation-status"' in html


def test_phase4_performance_helpers_exist() -> None:
    js = (TEMPLATES / "experiments" / "space-explorer" / "main.js").read_text(
        encoding="utf-8"
    )
    controls_js = (
        TEMPLATES / "experiments" / "space-explorer" / "controls.js"
    ).read_text(encoding="utf-8")
    assert "function setRenderMode(" in controls_js
    assert 'document.addEventListener("visibilitychange"' in js
    assert "requestAnimationFrame(() => {" in js
