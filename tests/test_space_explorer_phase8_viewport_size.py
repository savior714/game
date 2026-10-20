"""태양계 3D 탐험대 — 전체화면/반응형 레이아웃 계약."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPACE_DIR = ROOT / "experiments" / "space-explorer"


def read(name: str) -> str:
    return (SPACE_DIR / name).read_text(encoding="utf-8")


def test_scene_fills_the_viewport() -> None:
    css = read("space-explorer.css")

    assert "#space-app {" in css
    assert "position: fixed;" in css
    assert "inset: 0;" in css
    assert "#space-canvas {" in css
    assert "width: 100%;" in css
    assert "height: 100%;" in css
    assert "html, body {" in css
    assert "overflow: hidden;" in css


def test_layout_has_tablet_and_phone_breakpoints() -> None:
    css = read("space-explorer.css")

    assert "@media (max-width: 980px)" in css
    assert "@media (max-width: 700px)" in css
    assert ".bottom-suite" in css
    assert ".detail {" in css
    assert "max-height: 40vh;" in css


def test_focus_framing_avoids_panel_overlap() -> None:
    renderer = read("renderer.js")
    main = read("main.js")

    assert "function setViewShift({ y = 0, x = 0 } = {}) {" in renderer
    assert (
        "camera.setViewOffset(width, height, offsetX, offsetY, width, height);"
        in renderer
    )
    assert "function syncViewShift()" in main
    assert "const narrow = window.innerWidth <= 700;" in main
    assert "const wide = window.innerWidth > 980;" in main


def test_resize_and_orientation_changes_are_handled() -> None:
    main = read("main.js")
    renderer = read("renderer.js")

    assert 'window.addEventListener("resize", onResize, { passive: true });' in main
    assert (
        'window.addEventListener("orientationchange", onResize, { passive: true });'
        in main
    )
    assert "new ResizeObserver(onResize)" in main
    assert "camera.aspect = width / height;" in renderer
    assert "camera.updateProjectionMatrix();" in renderer
