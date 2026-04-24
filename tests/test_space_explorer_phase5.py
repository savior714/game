from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT
SPACE_EXPLORER_DIR = TEMPLATES / "space-explorer"


def test_space_explorer_uses_module_entrypoint() -> None:
    html = (TEMPLATES / "space-explorer.html").read_text(encoding="utf-8")
    assert 'script type="module" src="./space-explorer/main.js"' in html


def test_space_explorer_is_split_into_core_modules() -> None:
    state_js = (SPACE_EXPLORER_DIR / "state.js").read_text(encoding="utf-8")
    renderer_js = (SPACE_EXPLORER_DIR / "renderer.js").read_text(encoding="utf-8")
    controls_js = (SPACE_EXPLORER_DIR / "controls.js").read_text(encoding="utf-8")
    main_js = (SPACE_EXPLORER_DIR / "main.js").read_text(encoding="utf-8")

    assert "export const state" in state_js
    assert "export function createRenderer(" in renderer_js
    assert "export function attachControls(" in controls_js
    assert "attachControls(" in main_js
