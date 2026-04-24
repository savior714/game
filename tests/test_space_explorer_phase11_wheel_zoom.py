from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPACE_EXPLORER_DIR = ROOT / "space-explorer"


def test_wheel_zoom_is_supported_on_canvas() -> None:
    interactions_js = (SPACE_EXPLORER_DIR / "interactions.js").read_text(encoding="utf-8")

    assert "function onWheel(event)" in interactions_js
    assert "const wheelDelta = -event.deltaY;" in interactions_js
    assert "state.targetZoom = clamp(state.targetZoom + zoomStep, MIN_ZOOM, MAX_ZOOM);" in interactions_js
    assert 'canvas.addEventListener("wheel", onWheel, { passive: false });' in interactions_js


def test_high_frequency_interactions_are_raf_batched() -> None:
    interactions_js = (SPACE_EXPLORER_DIR / "interactions.js").read_text(encoding="utf-8")

    assert "let rafScheduled = false;" in interactions_js
    assert "function scheduleRender()" in interactions_js
    assert "if (rafScheduled) return;" in interactions_js
    assert "requestAnimationFrame(() => {" in interactions_js
    assert "rafScheduled = false;" in interactions_js
    assert "render();" in interactions_js
    assert "scheduleRender();" in interactions_js
