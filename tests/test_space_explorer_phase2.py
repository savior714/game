from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT


def test_space_explorer_script_is_connected() -> None:
    html = (TEMPLATES / "space-explorer.html").read_text(encoding="utf-8")
    assert 'script type="module" src="./space-explorer/main.js"' in html


def test_space_explorer_core_symbols_exist() -> None:
    renderer_js = (TEMPLATES / "space-explorer" / "renderer.js").read_text(encoding="utf-8")
    state_js = (TEMPLATES / "space-explorer" / "state.js").read_text(encoding="utf-8")
    main_js = (TEMPLATES / "space-explorer" / "main.js").read_text(encoding="utf-8")
    assert "requestAnimationFrame" in main_js
    assert "resizeCanvas" in renderer_js
    assert "export const planets = [" in state_js
    assert state_js.count("name:") >= 8
