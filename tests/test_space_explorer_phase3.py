from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT


def test_controls_have_stable_action_selectors() -> None:
    html = (TEMPLATES / "space-explorer.html").read_text(encoding="utf-8")
    assert 'data-action="play"' in html
    assert 'data-action="pause"' in html
    assert 'data-action="reset"' in html
    assert 'id="simulation-status"' in html


def test_interaction_helpers_exist_in_script() -> None:
    js = (TEMPLATES / "space-explorer" / "controls.js").read_text(encoding="utf-8")
    assert "function setPlaying(" in js
    assert "function updateStatusText(" in js
    assert "function applyResetState(" in js
