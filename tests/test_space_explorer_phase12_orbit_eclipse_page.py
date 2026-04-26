from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT


def test_home_has_orbit_and_eclipse_learning_card() -> None:
    html = (TEMPLATES / "index.html").read_text(encoding="utf-8")

    assert "공전·자전과 일식/월식" in html
    assert "orbit-eclipse.html" in html
    assert "태양-지구-달 움직임을 눈으로 보는" in html


def test_orbit_eclipse_page_has_scene_and_lesson_controls() -> None:
    html = (TEMPLATES / "orbit-eclipse.html").read_text(encoding="utf-8")

    assert 'id="orbit-eclipse-canvas"' in html
    assert 'id="lesson-mode"' in html
    assert 'id="lesson-render-mode"' in html
    assert 'value="2d"' in html
    assert 'value="3d"' in html
    assert 'value="rotation-revolution"' in html
    assert 'value="solar-eclipse"' in html
    assert 'value="lunar-eclipse"' in html
    assert 'id="lesson-explanation"' in html
    assert 'script src="./space-explorer/orbit-eclipse.js"' in html


def test_orbit_eclipse_script_defines_lesson_states_and_render_loop() -> None:
    js = (TEMPLATES / "space-explorer" / "orbit-eclipse.js").read_text(encoding="utf-8")

    assert "const LESSONS = {" in js
    assert "rotation-revolution" in js
    assert "solar-eclipse" in js
    assert "lunar-eclipse" in js
    assert "function updateLessonText()" in js
    assert "function renderScene(" in js
    assert "renderMode: \"2d\"" in js
    assert "function projectOrbitPosition(" in js
    assert "if (state.renderMode === \"3d\")" in js
    assert "function drawLitSphere(" in js
    assert "function drawEclipseShadow(" in js
    assert "function drawShadowCone(" in js
    assert "function drawAlignmentIndicator(" in js
    assert "function computeLineDistance(" in js
    assert "const lightAngle = Math.atan2(lightY - y, lightX - x);" in js
    assert "const terminatorGradient = ctx.createLinearGradient(" in js
    assert "ctx.setTransform(dpr, 0, 0, dpr, 0, 0);" in js
    assert "renderScene(0);" in js
    assert "requestAnimationFrame(animate);" in js
