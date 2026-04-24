from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT
SPACE_EXPLORER_DIR = TEMPLATES / "space-explorer"


def test_tablet_gesture_module_is_wired() -> None:
    main_js = (SPACE_EXPLORER_DIR / "main.js").read_text(encoding="utf-8")
    interactions_js = (SPACE_EXPLORER_DIR / "interactions.js").read_text(encoding="utf-8")

    assert "import { attachTouchInteractions } from \"./interactions.js\";" in main_js
    assert "attachTouchInteractions({ canvas, state, render });" in main_js
    assert "canvas.addEventListener(\"touchstart\"" in interactions_js
    assert "canvas.addEventListener(\"touchmove\"" in interactions_js
    assert "canvas.addEventListener(\"touchend\"" in interactions_js


def test_tablet_zoom_and_rotation_state_exist() -> None:
    state_js = (SPACE_EXPLORER_DIR / "state.js").read_text(encoding="utf-8")
    renderer_js = (SPACE_EXPLORER_DIR / "renderer.js").read_text(encoding="utf-8")
    styles_css = (TEMPLATES / "styles.css").read_text(encoding="utf-8")

    assert "zoom:" in state_js
    assert "targetZoom:" in state_js
    assert "viewRotation:" in state_js
    assert "targetRotation:" in state_js
    assert "state.viewRotation" in renderer_js
    assert "state.zoom" in renderer_js
    assert "touch-action: none;" in styles_css
