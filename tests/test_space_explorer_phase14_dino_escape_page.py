"""Contract tests for the rebuilt Dino Escape 3D chase runner.

The game was rebuilt from scratch on top of small ES modules. These tests pin
the integration surface that the page shell and the modules agree on: markup
ids, local-only assets, module boundaries and the persisted data version.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "experiments" / "space-explorer"
PAGE = EXPERIMENTS / "dino-escape.html"
STYLESHEET = EXPERIMENTS / "dino-escape.css"
SCRIPT = EXPERIMENTS / "dino-escape.js"
DINO = EXPERIMENTS / "dino"
ASSETS = EXPERIMENTS / "assets"
FONTS = ASSETS / "fonts"
FRAME_CHECK = ROOT / "scripts" / "dino" / "frame-check.mjs"


def test_home_has_dino_escape_card_below_paint_mixing_card() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    assert "물감 색 섞기 실험" in html
    assert "공룡 추격 탈출 게임" in html
    assert "dino-escape.html" in html
    assert html.index("paint-mixing.html") < html.index("dino-escape.html")


def test_dino_escape_page_has_full_hud_and_screen_contract() -> None:
    html = PAGE.read_text(encoding="utf-8")

    assert 'id="dino-escape-canvas"' in html
    assert 'id="hud"' in html
    assert 'id="rexcam-window"' in html
    assert 'id="toast-layer"' in html
    assert 'id="biome-banner"' in html
    assert 'id="announce"' in html
    assert 'id="boot-screen"' in html

    for screen in ("start", "pause", "gameover", "settings", "error"):
        assert f'id="screen-{screen}"' in html

    for hud_id in (
        "hud-distance",
        "hud-best",
        "hud-gap",
        "hud-gap-fill",
        "hud-amber",
        "hud-combo",
        "hud-shield",
        "hud-bait",
        "hud-biome",
        "hud-biome-next",
        "hud-biome-fill",
        "hud-speed",
        "hud-stamina-fill",
        "rexcam-distance",
        "rexcam-state",
        "tutorial-hint",
        "combo-chip",
        "shield-chip",
        "stamina",
        "biome-chip",
    ):
        assert f'id="{hud_id}"' in html

    for touch_id in ("btn-jump", "btn-slide", "btn-sprint", "btn-bait"):
        assert f'id="{touch_id}"' in html

    for action in (
        "pause",
        "restart",
        "open-settings",
        "close-settings",
        "toggle-sound",
        "toggle-music",
        "toggle-shake",
    ):
        assert f'data-action="{action}"' in html

    assert 'id="setting-quality"' in html
    assert 'data-quality="auto"' in html
    assert 'aria-live="polite"' in html
    assert "<noscript>" in html


def test_dino_escape_page_is_offline_and_module_based() -> None:
    html = PAGE.read_text(encoding="utf-8")

    assert 'href="./dino-escape.css"' in html
    assert "space-explorer.css" not in html
    assert "space-explorer-minigames.css" not in html
    assert '<script type="module" src="./dino-escape.js"></script>' in html
    assert html.count("<script") == 1

    # Nothing at all is fetched at runtime: the 3D engine, the fonts and the
    # stylesheet are all local, so the page renders identically offline.
    for remote in (
        "unpkg.com",
        "cdn.jsdelivr.net",
        "cdnjs.cloudflare.com",
        "three@0.",
        "fonts.googleapis.com",
        "fonts.gstatic.com",
    ):
        assert remote not in html, f"runtime network dependency leaked back: {remote}"
    assert "importmap" not in html

    # Vendored three.js ships its core chunk next to the module entry point.
    assert 'modulepreload" href="./vendor/three/build/three.module.min.js"' in html
    assert 'modulepreload" href="./vendor/three/build/three.core.min.js"' in html
    assert (EXPERIMENTS / "vendor" / "three" / "build" / "three.module.min.js").exists()
    assert (EXPERIMENTS / "vendor" / "three" / "build" / "three.core.min.js").exists()
    assert (EXPERIMENTS / "vendor" / "three" / "LICENSE" / "THREE_LICENSE.txt").exists()


def test_entry_script_only_imports_local_modules() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    assert 'from "./vendor/three/build/three.module.min.js"' in script
    assert "unpkg.com" not in script
    assert "jsdelivr" not in script
    assert "https://" not in script

    for specifier in set(re.findall(r'from "(\.[^"]+)"', script)):
        target = (EXPERIMENTS / specifier).resolve()
        assert target.is_file(), f"unresolved relative import: {specifier}"

    # The old weapon/chase implementation must not survive the rewrite.
    for legacy in (
        "WEAPON_TIERS",
        "ENEMY_CATCH_RADIUS",
        "dino-touch-controls",
        "THREE.CapsuleGeometry",
        "renderer.setAnimationLoop",
    ):
        assert legacy not in script, f"legacy implementation survived: {legacy}"


def test_simulation_modules_stay_dom_free() -> None:
    for name in ("constants.js", "util.js", "run-model.js", "spawner.js", "player.js"):
        source = (DINO / name).read_text(encoding="utf-8")
        assert "document." not in source, f"{name} must stay DOM-free"
        assert "window." not in source, f"{name} must stay DOM-free"

    for name in ("models.js", "world.js", "particles.js", "entities.js"):
        source = (DINO / name).read_text(encoding="utf-8")
        assert 'from "../vendor/three/build/three.module.min.js"' in source


def test_run_model_exposes_events_used_by_the_presentation_layer() -> None:
    source = (DINO / "run-model.js").read_text(encoding="utf-8")

    for event in ("milestone", "biome", "caught", "combo-end"):
        assert f'type: "{event}"' in source

    for export in (
        "createRunState",
        "stepRun",
        "applyHit",
        "collectAmber",
        "collectBait",
        "collectShield",
        "throwBait",
        "getRunSummary",
        "getDangerLevel",
        "getBiomeProgress",
    ):
        assert f"export function {export}" in source


def test_tuning_and_storage_contract() -> None:
    constants = (DINO / "constants.js").read_text(encoding="utf-8")
    storage = (DINO / "storage.js").read_text(encoding="utf-8")

    assert 'export const STORAGE_KEY = "aiden.dinoEscape.v3";' in constants
    assert "export const REX_LAYER = 1;" in constants
    assert "export const RUN = Object.freeze({" in constants
    assert "threshold: 0," in constants
    assert "threshold: 720," in constants
    assert "threshold: 1560," in constants
    assert constants.count("id: \"jungle\"") == 1
    assert constants.count("id: \"desert\"") == 1
    assert constants.count("id: \"volcano\"") == 1

    assert "export function loadProfile()" in storage
    assert "export function saveProfile(profile)" in storage
    assert "localStorage.getItem(STORAGE_KEY)" in storage
    assert "localStorage.setItem(STORAGE_KEY" in storage
    assert "try {" in storage and "catch (error)" in storage


def test_hud_module_only_reads_ids_that_exist_in_the_page() -> None:
    html = PAGE.read_text(encoding="utf-8")
    hud = (DINO / "hud.js").read_text(encoding="utf-8")

    ids = set(re.findall(r'byId\("([^"]+)"\)', hud))
    assert len(ids) >= 40
    missing = sorted(identifier for identifier in ids if f'id="{identifier}"' not in html)
    assert not missing, f"hud.js references missing page ids: {missing}"


def test_presentation_entry_drives_every_required_screen_and_hud_state() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    for method in (
        "showScreen",
        "updateRun",
        "updatePause",
        "showGameOver",
        "showBiomeBanner",
        "setTutorial",
        "setSpeedFx",
        "openSettings",
    ):
        assert f"hud.{method}(" in script, f"entry script never calls hud.{method}()"

    for mode in ('"menu"', '"running"', '"paused"', '"caught"', '"gameover"'):
        assert f"mode = {mode}" in script or f"mode: {mode}" in script


def test_dino_escape_ships_its_own_fonts() -> None:
    """Korean copy must never depend on a reachable CDN or the host's emoji font."""
    html = PAGE.read_text(encoding="utf-8")
    css = STYLESHEET.read_text(encoding="utf-8")

    assert 'href="./assets/fonts/PretendardVariable.woff2"' in html
    assert "fonts.googleapis.com" not in html and "fonts.gstatic.com" not in html
    assert "jsdelivr" not in html

    for family, weight in (
        ("Pretendard", "45 920"),
        ("Outfit", "700"),
        ("Space Grotesk", "700"),
        ("JetBrains Mono", "500"),
    ):
        assert f'font-family: "{family}"' in css, f"missing @font-face for {family}"
    assert 'src: url("./assets/fonts/PretendardVariable.woff2")' in css
    assert "font-display: swap" in css

    for font_file in re.findall(r'url\(\"\./assets/fonts/([^\"]+)\"\)', css):
        assert (FONTS / font_file).is_file(), f"stylesheet references missing font: {font_file}"
    assert (FONTS / "Pretendard-LICENSE.txt").is_file()
    assert (FONTS / "OFL-LICENSE.txt").is_file()

    # Korean glyphs fall back to a Korean-capable family, not to the emoji font.
    assert "--font-body: \"Pretendard\"" in css
    assert '"Apple SD Gothic Neo"' in css and '"Malgun Gothic"' in css


def test_dino_escape_hud_does_not_rely_on_emoji_glyphs() -> None:
    """Emoji render as tofu on many Linux/Windows setups; shipped UI uses SVG."""
    html = PAGE.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")

    for emoji in ("🦖", "🍖", "🥩", "🔊", "🔇"):
        assert emoji not in html, f"page shell still depends on emoji glyph {emoji}"
        assert emoji not in script, f"entry script still injects emoji glyph {emoji}"

    for icon in ("gap-rex", "touch-bait", "audio-pill-icon", "boot-mark"):
        block = re.search(rf'class="[^"]*{icon}[^"]*"[^>]*>(.*?)</span>', html, re.S)
        if block is None:
            block = re.search(rf'class="[^"]*{icon}[^"]*"[^>]*>(.*?)</div>', html, re.S)
        assert block is not None, f"missing {icon} markup"
        assert "<svg" in block.group(1), f"{icon} must render as inline SVG, not a glyph"


def test_chase_director_keeps_the_chase_readable() -> None:
    """Static contract for the camera/staging module plus its framing check."""
    chase = (DINO / "chase.js").read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")

    for export in ("createChaseDirector", "rexStaging", "CHASE", "yawToward"):
        assert f"export function {export}" in chase or f"export const {export}" in chase

    assert "chase.update(" in script
    assert "rexStaging(" in script
    # The camera director owns the pose now, not ad-hoc camera math in the entry.
    assert "camera.lookAt(pose.lookX, pose.lookY, pose.lookZ)" in script
    assert FRAME_CHECK.is_file()

    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        return
    result = subprocess.run(
        [node, str(FRAME_CHECK)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "checks passed" in result.stdout
