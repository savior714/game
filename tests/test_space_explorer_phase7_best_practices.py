from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
SPACE_EXPLORER_DIR = TEMPLATES / "space-explorer"


def test_hidpi_and_context_optimization_are_configured() -> None:
    main_js = (SPACE_EXPLORER_DIR / "main.js").read_text(encoding="utf-8")
    renderer_js = (SPACE_EXPLORER_DIR / "renderer.js").read_text(encoding="utf-8")

    assert 'getContext("2d", { alpha: false, desynchronized: true })' in main_js
    assert "window.devicePixelRatio" in renderer_js
    assert "ctx.setTransform(" in renderer_js


def test_cached_starfield_and_pointer_events_exist() -> None:
    renderer_js = (SPACE_EXPLORER_DIR / "renderer.js").read_text(encoding="utf-8")
    interactions_js = (SPACE_EXPLORER_DIR / "interactions.js").read_text(encoding="utf-8")
    html = (TEMPLATES / "space-explorer.html").read_text(encoding="utf-8")

    assert "document.createElement(\"canvas\")" in renderer_js
    assert "ctx.drawImage(" in renderer_js
    assert "canvas.addEventListener(\"pointerdown\"" in interactions_js
    assert "canvas.addEventListener(\"pointermove\"" in interactions_js
    assert "canvas.addEventListener(\"pointerup\"" in interactions_js
    assert "핀치로 확대/축소" in html
