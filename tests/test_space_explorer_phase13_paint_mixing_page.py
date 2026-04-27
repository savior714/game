from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT


def test_home_has_paint_mixing_card_below_orbit_card() -> None:
    html = (TEMPLATES / "index.html").read_text(encoding="utf-8")

    assert "공전·자전과 일식/월식" in html
    assert "물감 색 섞기 실험" in html
    assert "paint-mixing.html" in html
    assert html.index("orbit-eclipse.html") < html.index("paint-mixing.html")


def test_paint_mixing_page_has_palette_controls_and_reset_button() -> None:
    html = (TEMPLATES / "paint-mixing.html").read_text(encoding="utf-8")

    assert 'id="paint-result-swatch"' in html
    assert 'id="paint-mix-status"' in html
    assert 'id="paint-reset-button"' in html
    assert 'id="paint-brightness"' in html
    assert 'id="paint-brightness-status"' in html
    assert 'id="paint-beaker"' in html
    assert 'id="paint-liquid-layer"' in html
    assert 'id="paint-drop-layer"' in html
    assert 'id="paint-pipette"' in html
    assert 'data-color="yellow"' in html
    assert 'data-color="blue"' in html
    assert 'data-color="red"' in html
    assert 'id="paint-mixing-three-layer"' in html
    assert 'script type="module" src="./space-explorer/paint-mixing.js"' in html


def test_paint_mixing_script_supports_mix_and_reset() -> None:
    js = (TEMPLATES / "space-explorer" / "paint-mixing.js").read_text(encoding="utf-8")

    assert "const COLOR_LIBRARY = {" in js
    assert "function mixSelectedColors(" in js
    assert "const colorIntensity = new Map();" in js
    assert "function getColorIntensity(" in js
    assert "function increaseColorIntensity(" in js
    assert "function resetSelection(" in js
    assert "function applyBrightness(" in js
    assert "function buildPaintTexture(" in js
    assert "function animatePipetteDrop(" in js
    assert "function spawnDropRipple(" in js
    assert "yellow+blue" in js
    assert "red+blue" in js
    assert "red+yellow" in js
    assert "paint-reset-button" in js
    assert "paint-result-swatch" in js
    assert "paint-brightness" in js
    assert "paint-brightness-status" in js
    assert "paint-liquid-layer" in js
    assert "paint-drop-layer" in js
    assert "paint-pipette" in js
    assert "radial-gradient(" in js
    assert 'import { initializePaintLights } from "./three-backdrop.js";' in js
    assert (
        'const threeLayer = document.getElementById("paint-mixing-three-layer");' in js
    )
    assert "initializePaintLights(threeLayer);" in js
