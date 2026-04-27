from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPACE_EXPLORER_DIR = ROOT / "space-explorer"


def test_wheel_zoom_is_supported_on_canvas() -> None:
    interactions_js = (SPACE_EXPLORER_DIR / "interactions.js").read_text(
        encoding="utf-8"
    )

    assert "function onWheel(event)" in interactions_js
    assert "const wheelDelta = -event.deltaY;" in interactions_js
    assert (
        "state.targetZoom = clamp(state.targetZoom + zoomStep, MIN_ZOOM, MAX_ZOOM);"
        in interactions_js
    )
    assert (
        'canvas.addEventListener("wheel", onWheel, { passive: false });'
        in interactions_js
    )


def test_high_frequency_interactions_are_raf_batched() -> None:
    interactions_js = (SPACE_EXPLORER_DIR / "interactions.js").read_text(
        encoding="utf-8"
    )

    assert "let rafScheduled = false;" in interactions_js
    assert "function scheduleRender()" in interactions_js
    assert "if (rafScheduled) return;" in interactions_js
    assert "requestAnimationFrame(() => {" in interactions_js
    assert "rafScheduled = false;" in interactions_js
    assert "render();" in interactions_js
    assert "scheduleRender();" in interactions_js


def test_animation_loop_avoids_unnecessary_idle_renders() -> None:
    main_js = (SPACE_EXPLORER_DIR / "main.js").read_text(encoding="utf-8")

    assert "const SMOOTHING_EPSILON = 0.0008;" in main_js
    assert "let shouldRenderFrame = state.isPlaying;" in main_js
    assert "const zoomDelta = state.targetZoom - state.zoom;" in main_js
    assert "const rotationDelta = state.targetRotation - state.viewRotation;" in main_js
    assert (
        "Math.abs(zoomDelta) > SMOOTHING_EPSILON || Math.abs(rotationDelta) > SMOOTHING_EPSILON"
        in main_js
    )
    assert "if (shouldRenderFrame) {" in main_js
    assert "render();" in main_js


def test_renderer_records_frame_measurements_for_regression_guard() -> None:
    renderer_js = (SPACE_EXPLORER_DIR / "renderer.js").read_text(encoding="utf-8")

    assert 'const PERF_MARK_START = "spaceExplorer:render:start";' in renderer_js
    assert 'const PERF_MARK_END = "spaceExplorer:render:end";' in renderer_js
    assert 'const PERF_MEASURE_NAME = "spaceExplorer:render:duration";' in renderer_js
    assert (
        'if (typeof performance !== "undefined" && typeof performance.mark === "function")'
        in renderer_js
    )
    assert "performance.mark(PERF_MARK_START);" in renderer_js
    assert "performance.mark(PERF_MARK_END);" in renderer_js
    assert (
        "performance.measure(PERF_MEASURE_NAME, PERF_MARK_START, PERF_MARK_END);"
        in renderer_js
    )
