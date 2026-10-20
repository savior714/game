"""태양계 3D 탐험대 — 카메라 조작/프레임 예산 회귀 가드."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPACE_DIR = ROOT / "experiments" / "space-explorer"


def read(name: str) -> str:
    return (SPACE_DIR / name).read_text(encoding="utf-8")


def test_orbit_controls_handle_wheel_pinch_and_rotation() -> None:
    renderer = read("renderer.js")
    interactions = read("interactions.js")

    assert (
        'import { OrbitControls } from "three/addons/controls/OrbitControls.js";'
        in renderer
    )
    assert "controls.enableDamping = true;" in renderer
    assert "controls.minDistance" in renderer
    assert "controls.maxDistance" in renderer
    assert "ONE: THREE.TOUCH.ROTATE" in renderer
    assert "TWO: THREE.TOUCH.DOLLY_ROTATE" in renderer
    # 휠/핀치 확대는 OrbitControls가 처리하고, 상호작용 레이어는 클릭과 드래그를 구분한다.
    assert (
        'canvas.addEventListener("wheel", onUserInteract, { passive: true });'
        in interactions
    )
    assert "const DRAG_THRESHOLD_PX = 7;" in interactions


def test_pointer_hover_raycasts_are_frame_batched() -> None:
    interactions = read("interactions.js")

    assert "let hoverFrame = 0;" in interactions
    assert "requestAnimationFrame(() => {" in interactions
    assert "cancelAnimationFrame(hoverFrame)" in interactions
    assert "function onPointerDown(event)" in interactions
    assert "function onPointerUp(event)" in interactions


def test_render_budget_guards_exist() -> None:
    renderer = read("renderer.js")
    main = read("main.js")

    # 픽셀 비율 상한과 자동 화질 하향
    assert "Math.min(window.devicePixelRatio || 1, 1.85)" in renderer
    assert "function setPixelRatioCap(cap)" in renderer
    assert "if (lowPerformanceWindows >= 3) {" in main
    assert "scene?.setPixelRatioCap(1.25);" in main
    # 화면이 가려진 동안에는 시뮬레이션과 렌더를 멈춘다.
    assert "if (scene && !document.hidden) {" in main
    assert 'document.addEventListener("visibilitychange"' in main


def test_frame_delta_is_clamped_to_avoid_planet_jumps() -> None:
    main = read("main.js")

    assert (
        "const dt = Math.min(0.1, Math.max(0, (now - lastFrameTime) / 1000));" in main
    )
    assert "export const MAX_FRAME_STEP_SECONDS = 0.1;" in read("state.js")
