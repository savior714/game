from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPACE_EXPLORER_DIR = ROOT / "space-explorer"


def test_speed_presets_are_rebased_to_half_speed_default() -> None:
    html = (ROOT / "space-explorer.html").read_text(encoding="utf-8")
    controls_js = (SPACE_EXPLORER_DIR / "controls.js").read_text(encoding="utf-8")
    state_js = (SPACE_EXPLORER_DIR / "state.js").read_text(encoding="utf-8")

    assert '<option value="0.5" selected>100%</option>' in html
    assert '<option value="0.75">150%</option>' in html
    assert '<option value="1">200%</option>' in html
    assert "timeScale: 0.5" in state_js
    assert (
        "status.textContent = `${mode} · ${Math.round(state.timeScale * 200)}% · ${renderModeText}`;"
        in controls_js
    )


def test_3d_planet_position_uses_same_rotated_ellipse_as_orbit_line() -> None:
    renderer_js = (SPACE_EXPLORER_DIR / "renderer.js").read_text(encoding="utf-8")

    assert "const ORBIT_TILT = Math.PI / 6;" in renderer_js
    assert "function projectOrbitPosition(cx, cy, orbitRadius, angle)" in renderer_js
    assert (
        "const x = cx + Math.cos(ORBIT_TILT) * ellipseX - Math.sin(ORBIT_TILT) * ellipseY;"
        in renderer_js
    )
    assert (
        "const y = cy + Math.sin(ORBIT_TILT) * ellipseX + Math.cos(ORBIT_TILT) * ellipseY;"
        in renderer_js
    )
    assert (
        "const orbitPoint = projectOrbitPosition(cx, cy, orbitRadius, planetAngle);"
        in renderer_js
    )
    assert "if (is3DMode()) {" in renderer_js
