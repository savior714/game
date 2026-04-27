from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT


def test_home_has_dino_escape_card_below_paint_mixing_card() -> None:
    html = (TEMPLATES / "index.html").read_text(encoding="utf-8")

    assert "물감 색 섞기 실험" in html
    assert "공룡 추격 탈출 게임" in html
    assert "dino-escape.html" in html
    assert html.index("paint-mixing.html") < html.index("dino-escape.html")


def test_dino_escape_page_has_canvas_hud_and_controls() -> None:
    html = (TEMPLATES / "dino-escape.html").read_text(encoding="utf-8")

    assert 'id="dino-escape-canvas"' in html
    assert 'id="dino-score"' in html
    assert 'id="dino-current-weapon"' in html
    assert 'id="dino-next-unlock"' in html
    assert 'id="dino-next-progress-track"' in html
    assert 'id="dino-next-progress-fill"' in html
    assert 'id="dino-status"' in html
    assert 'id="dino-hit-flash"' in html
    assert 'id="dino-unlock-toast"' in html
    assert 'id="dino-debug-multiplier"' in html
    assert 'id="dino-debug-enemy-speed"' in html
    assert 'id="dino-restart-button"' in html
    assert "WASD Move | Click Throw | Shift Sprint" in html
    assert 'script type="module" src="./space-explorer/dino-escape.js"' in html


def test_dino_escape_script_supports_core_game_loop_and_unlocks() -> None:
    js = (TEMPLATES / "space-explorer" / "dino-escape.js").read_text(encoding="utf-8")

    assert "const WEAPON_TIERS = [" in js
    assert 'id: "stone"' in js
    assert 'id: "spear"' in js
    assert 'id: "gun"' in js
    assert "const DIFFICULTY_WAVE_TABLE = [" in js
    assert "function createInitialGameState(" in js
    assert "function updatePlayerMovement(" in js
    assert "function updateEnemyChase(" in js
    assert "function getDifficultyMultiplier(" in js
    assert "function tryFireProjectile(" in js
    assert "function updateProjectiles(" in js
    assert "function resolveHitsAndScoring(" in js
    assert "function updateWeaponUnlock(" in js
    assert "function checkGameOver(" in js
    assert "function updateDebugHud(" in js
    assert "function updateHitFlash(" in js
    assert "function applyCameraShake(" in js
    assert "function playHitSound(" in js
    assert "function updateUnlockToast(" in js
    assert "let hitStopFrames = 0;" in js
    assert "if (hitStopFrames > 0)" in js
    assert "renderer.setAnimationLoop(" in js
