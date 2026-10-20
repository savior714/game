"""태양계 3D 탐험대 — 로딩/실패/접근성 모범 사례 계약."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPACE_DIR = ROOT / "experiments" / "space-explorer"


def read(name: str) -> str:
    return (SPACE_DIR / name).read_text(encoding="utf-8")


def renderer_main() -> str:
    return read("main.js")


def test_texture_loader_reports_progress_and_falls_back() -> None:
    textures = read("textures.js")
    controls = read("controls.js")

    assert (
        "export function createTextureLibrary(renderer, onProgress = () => {})"
        in textures
    )
    assert "function createFallbackTexture(body, renderer)" in textures
    assert "new THREE.TextureLoader()" in textures
    assert (
        "texture.colorSpace = COLOR_MAPS.has(name) ? THREE.SRGBColorSpace : THREE.NoColorSpace;"
        in textures
    )
    assert (
        "onTextureProgress: (loaded, total, name) => ui.setLoadingProgress(loaded, total, name)"
        in renderer_main()
    )
    assert "function setLoadingProgress(loaded, total, name)" in controls
    assert "function finishLoading()" in controls


def test_fatal_error_screen_recovers_with_a_reload() -> None:
    controls = read("controls.js")
    main = read("main.js")
    html = read("index.html")

    assert 'id="fatal-error"' in html
    assert 'id="reload-btn"' in html
    assert "function showFatalError(message)" in controls
    assert "window.location.reload()" in controls
    assert "ui.showFatalError(" in main


def test_screen_reader_and_focus_contracts() -> None:
    html = read("index.html")
    css = read("space-explorer.css")
    controls = read("controls.js")

    assert 'aria-live="polite"' in html
    assert 'role="status"' in html
    assert 'aria-label="3D 태양계 시뮬레이션' in html
    assert 'tabindex="0"' in html
    assert "function announce(message)" in controls
    assert "#space-app button:focus-visible" in css
    assert "outline: 3px solid" in css
    assert "outline-offset: 3px" in css
    assert "box-shadow:" in css


def test_pinch_help_copy_is_still_shown() -> None:
    html = read("index.html")

    assert "핀치로 확대/축소" in html
    assert "드래그" in html
    assert "조작 가이드" in html


def test_prefers_reduced_motion_is_honored() -> None:
    css = read("space-explorer.css")
    main = read("main.js")

    assert "@media (prefers-reduced-motion: reduce)" in css
    assert 'window.matchMedia?.("(prefers-reduced-motion: reduce)")' in main
    assert "reducedMotion ? 0.02" in main
