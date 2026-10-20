from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT


def test_home_has_orbit_and_eclipse_learning_card() -> None:
    html = (TEMPLATES / "index.html").read_text(encoding="utf-8")

    assert "공전·자전과 일식/월식" in html
    assert "orbit-eclipse.html" in html
    assert "태양-지구-달 움직임을 눈으로 보는" in html


def test_orbit_eclipse_page_has_scene_and_lesson_controls() -> None:
    html = (
        TEMPLATES / "experiments" / "space-explorer" / "orbit-eclipse.html"
    ).read_text(encoding="utf-8")

    assert 'id="orbit-eclipse-canvas"' in html
    assert 'id="lesson-mode"' in html
    assert 'id="lesson-render-mode"' in html
    assert 'value="2d"' in html
    assert 'value="3d"' in html
    assert 'value="rotation-revolution"' in html
    assert 'value="solar-eclipse"' in html
    assert 'value="lunar-eclipse"' in html
    assert 'id="lesson-explanation"' in html
    assert 'id="orbit-eclipse-three-layer"' in html
    assert 'script type="module" src="./orbit-eclipse.js"' in html


def test_orbit_eclipse_scene_layers_backdrop_inside_wrapper() -> None:
    """3D 별 배경이 장면 컨테이너 안에 오버레이로 깔려야 한다 (별도 블록으로 떠다니면 안 됨)."""
    html = (
        TEMPLATES / "experiments" / "space-explorer" / "orbit-eclipse.html"
    ).read_text(encoding="utf-8")

    assert 'class="scene-wrap"' in html
    assert 'class="three-layer"' in html
    # 존재하지 않는 래퍼 클래스로 다시 회귀하지 않도록 감시
    assert "lesson-scene-wrap" not in html
    assert 'id="lesson-pause-button"' in html
    assert 'aria-pressed="false"' in html


def test_orbit_eclipse_script_defines_lesson_states_and_render_loop() -> None:
    js = (TEMPLATES / "experiments" / "space-explorer" / "orbit-eclipse.js").read_text(
        encoding="utf-8"
    )

    assert "const LESSONS = {" in js
    assert "rotation-revolution" in js
    assert "solar-eclipse" in js
    assert "lunar-eclipse" in js
    assert "function updateLessonText()" in js
    assert "function renderScene(" in js
    assert 'renderMode: "2d"' in js
    assert "function projectOrbitPosition(" in js
    assert 'if (state.renderMode === "3d")' in js
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
    assert 'import { initializeSpaceBackdrop } from "./three-backdrop.js";' in js
    assert (
        'const threeLayer = document.getElementById("orbit-eclipse-three-layer");' in js
    )
    assert "initializeSpaceBackdrop(threeLayer, { intensity: 1.05 });" in js


def test_orbit_eclipse_scene_composites_with_backdrop_and_single_moon() -> None:
    """2D 장면은 투명 배경으로 별 레이어와 합성되고, 일식·월식은 궤도 위의 하나의 달로 설명한다."""
    js = (TEMPLATES / "experiments" / "space-explorer" / "orbit-eclipse.js").read_text(
        encoding="utf-8"
    )

    # 투명 합성: 장면이 불투명 배경으로 별 레이어를 가리면 안 된다
    assert "ctx.clearRect(0, 0, width, height);" in js
    assert 'ctx.fillStyle = "#060b21"' not in js

    # 일식·월식 모드는 실제 궤도 위의 하나의 달이 정렬선을 지나가며 발생한다
    assert "function computeMoonAngle(" in js
    assert "earthAngle + Math.PI + wobble" in js
    assert "earthAngle + wobble" in js

    # 자전 시각화(대륙·자전축·회전 화살표)와 일식 그림자·혈월 표현
    assert "function drawEarthContinents(" in js
    assert "function drawEarthAxis(" in js
    assert "function drawSpinArrow(" in js
    assert "function drawEarthShadowSpot(" in js
    assert "혈월" in js

    # 일시정지 컨트롤과 탭 전환 등으로 인한 시간 점프 방지
    assert "paused: false" in js
    assert "lessonPauseButton" in js
    assert "Math.min(0.1, Math.max(0, (ts - state.lastTs) / 1000))" in js
