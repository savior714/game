from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"


def test_quality_controls_and_accessibility_markup_exist() -> None:
    html = (TEMPLATES / "space-explorer.html").read_text(encoding="utf-8")
    assert 'id="render-quality"' in html
    assert 'option value="high"' in html
    assert 'option value="low"' in html
    assert 'aria-describedby="simulation-status"' in html


def test_phase4_performance_helpers_exist() -> None:
    js = (TEMPLATES / "space-explorer" / "main.js").read_text(encoding="utf-8")
    controls_js = (TEMPLATES / "space-explorer" / "controls.js").read_text(encoding="utf-8")
    assert "function setQualityLevel(" in controls_js
    assert "document.addEventListener(\"visibilitychange\"" in js
    assert "requestAnimationFrame(() => {" in js
