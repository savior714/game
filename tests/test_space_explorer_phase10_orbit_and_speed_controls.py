from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPACE_EXPLORER_DIR = ROOT / "experiments" / "space-explorer"


def test_speed_presets_are_rebased_to_half_speed_default() -> None:
    html = (SPACE_EXPLORER_DIR / "index.html").read_text(encoding="utf-8")
    controls_js = (SPACE_EXPLORER_DIR / "controls.js").read_text(encoding="utf-8")
    state_js = (SPACE_EXPLORER_DIR / "state.js").read_text(encoding="utf-8")

    assert 'id="time-scale"' in html
    assert 'value="0.5"' in html
    assert "timeScale: 0.5" in state_js
    assert (
        "status.textContent = `${mode} · ${speedPercent}% · ${renderModeText}`;"
        in controls_js
    )


def test_3d_planet_position_uses_same_rotated_ellipse_as_orbit_line() -> None:
    renderer_js = (SPACE_EXPLORER_DIR / "renderer.js").read_text(encoding="utf-8")

    # 3D mode uses drawPlanetBody with 3D gradient but no separate projectOrbitPosition
    assert "function is3DMode()" in renderer_js
    assert "if (is3DMode()) {" in renderer_js
