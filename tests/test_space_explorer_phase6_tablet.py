"""태양계 3D 탐험대 — 태블릿/터치 입력 계약."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPACE_DIR = ROOT / "experiments" / "space-explorer"


def read(name: str) -> str:
    return (SPACE_DIR / name).read_text(encoding="utf-8")


def test_touch_and_pointer_input_is_wired() -> None:
    interactions = read("interactions.js")

    assert 'canvas.addEventListener("pointerdown", onPointerDown);' in interactions
    assert 'canvas.addEventListener("pointermove", onPointerMove);' in interactions
    assert 'canvas.addEventListener("pointerup", onPointerUp);' in interactions
    assert 'canvas.addEventListener("pointercancel", onPointerLeave);' in interactions
    assert 'canvas.addEventListener("pointerleave", onPointerLeave);' in interactions
    assert "export function attachSceneInteractions(" in interactions


def test_pinch_zoom_uses_orbit_controls_touch_mapping() -> None:
    renderer = read("renderer.js")
    css = read("space-explorer.css")

    assert "controls.touches = {" in renderer
    assert "ONE: THREE.TOUCH.ROTATE" in renderer
    assert "TWO: THREE.TOUCH.DOLLY_ROTATE" in renderer
    assert "touch-action: none;" in css
    assert "#space-canvas" in css


def test_clicks_are_distinguished_from_drags() -> None:
    interactions = read("interactions.js")

    assert "const CLICK_MAX_MS = 520;" in interactions
    assert "start.moved = true;" in interactions
    assert "if (wasClick) {" in interactions
    assert "onPick(id);" in interactions


def test_keyboard_shortcuts_exist_for_zoom_and_pause() -> None:
    interactions = read("interactions.js")
    main = read("main.js")
    html = read("index.html")

    assert 'event.key === "+"' in interactions
    assert 'event.key === "-"' in interactions
    assert 'event.code === "Space"' in main
    assert "actions.togglePause();" in main
    assert "키보드" in html
