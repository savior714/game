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
    assert 'id="dino-enemy-health-track"' in html
    assert 'id="dino-enemy-health-fill"' in html
    assert 'id="dino-enemy-health-label"' in html
    assert 'id="dino-status"' in html
    assert 'id="dino-hit-flash"' in html
    assert 'id="dino-unlock-toast"' in html
    assert 'id="dino-debug-multiplier"' in html
    assert 'id="dino-debug-enemy-speed"' in html
    assert 'id="dino-restart-button"' in html
    assert 'id="dino-touch-controls"' in html
    assert "캔버스 터치 방향 이동" in html
    assert 'id="dino-touch-sprint"' in html
    assert 'id="dino-chase-settings"' in html
    assert 'id="dino-enemy-base-speed-input"' in html
    assert 'id="dino-enemy-accel-input"' in html
    assert "WASD Move | Auto Throw | Shift Sprint" in html
    assert 'script src="./space-explorer/dino-escape.js"' in html


def test_dino_escape_script_supports_core_game_loop_and_unlocks() -> None:
    js = (TEMPLATES / "space-explorer" / "dino-escape.js").read_text(encoding="utf-8")

    assert "const WEAPON_TIERS = [" in js
    assert 'id: "stone"' in js
    assert 'id: "spear"' in js
    assert 'id: "gun"' in js
    assert "const DIFFICULTY_WAVE_TABLE = [" in js
    assert "function createInitialGameState(" in js
    assert "function updatePlayerMovement(" in js
    assert 'const touchControls = document.getElementById("dino-touch-controls");' in js
    assert "function updateTouchDirectionFromPointer(" in js
    assert 'canvas.addEventListener("pointerdown"' in js
    assert 'canvas.addEventListener("pointermove"' in js
    assert 'canvas.addEventListener("pointerup"' in js
    assert (
        'const touchSprintButton = document.getElementById("dino-touch-sprint");' in js
    )
    assert "clearTouchDirection()" in js
    assert "touchState.up" in js
    assert "function updateEnemyChase(" in js
    assert "function getDifficultyMultiplier(" in js
    assert "const DEFAULT_ENEMY_BASE_SPEED = 2.4;" in js
    assert "const DEFAULT_ENEMY_SPEED_SCALE_WITH_SCORE = 0.001;" in js
    assert "const chaseSettings = {" in js
    assert "function syncChaseSettingsFromControls()" in js
    assert 'enemyBaseSpeedInput.addEventListener("input"' in js
    assert 'enemyAccelInput.addEventListener("input"' in js
    assert "const ENEMY_BASE_SPEED = DEFAULT_ENEMY_BASE_SPEED;" in js
    assert (
        "const ENEMY_SPEED_SCALE_WITH_SCORE = DEFAULT_ENEMY_SPEED_SCALE_WITH_SCORE;"
        in js
    )
    assert "const ENEMY_START_SPEED_RATIO = 0.72;" in js
    assert "const ENEMY_CATCH_RADIUS = 1.4;" in js
    assert "const ENEMY_MAX_HEALTH = 50;" in js
    assert "const AUTO_FIRE_RANGE = 22;" in js
    assert "function getAutoFireDirection(" in js
    assert "function tryFireProjectile(" in js
    assert "function updateProjectiles(" in js
    assert "function resolveHitsAndScoring(" in js
    assert "function updateWeaponUnlock(" in js
    assert "function checkGameOver(" in js
    assert "enemyHealthFillEl.style.width" in js
    assert "enemyHealthLabelEl.textContent" in js
    assert "function updateDebugHud(" in js
    assert "function updateHitFlash(" in js
    assert "function applyCameraShake(camera)" in js
    assert "function playHitSound(" in js
    assert "function updateUnlockToast(" in js
    assert "new THREE.CapsuleGeometry(" in js
    assert "const stoneScale = 1 + Math.random() * 0.45;" in js
    assert (
        "const baseStoneGeometry = new THREE.DodecahedronGeometry(WEAPON_TIERS[0].projectileSize);"
        in js
    )
    assert (
        "const baseStoneMaterial = new THREE.MeshStandardMaterial({ color: 0x6b7280, roughness: 0.98, metalness: 0.02, flatShading: true });"
        in js
    )
    assert "const backSpikeGeometry = new THREE.ConeGeometry(0.16, 0.52, 7);" in js
    assert "const eyeGeometry = new THREE.SphereGeometry(0.08, 8, 8);" in js
    assert "new THREE.DodecahedronGeometry(" in js
    assert "new THREE.ConeGeometry(" in js
    assert "let hitStopFrames = 0;" in js
    assert "if (hitStopFrames > 0)" in js
    assert "camera.position.lerp(desired, Math.min(1, delta * 0.8));" in js
    assert "renderer.setAnimationLoop(" in js


def test_dino_escape_script_has_initial_camera_zoom_guard() -> None:
    js = (TEMPLATES / "space-explorer" / "dino-escape.js").read_text(encoding="utf-8")

    assert "const CAMERA_MIN_FOCUS_DISTANCE = 9.5;" in js
    assert "const CAMERA_FOLLOW_DISTANCE_NEAR = 8.8;" in js
    assert "const CAMERA_FOLLOW_DISTANCE_FAR = 12.8;" in js
    assert "const CAMERA_HEIGHT_NEAR = 8.6;" in js
    assert "const CAMERA_HEIGHT_FAR = 10.4;" in js
    assert "const CAMERA_DYNAMIC_ZOOM_DISTANCE = 26;" in js
    assert "function ensureMinimumFocusDistance(" in js
    assert "if (distance >= CAMERA_MIN_FOCUS_DISTANCE)" in js
    assert "return cameraPosition.clone().add(toFocus.multiplyScalar(scale));" in js
    assert (
        "const enemyDistance = distance2d(gameState.player.position, gameState.enemy.position);"
        in js
    )
    assert (
        "const zoomRatio = Math.max(0, Math.min(1, enemyDistance / CAMERA_DYNAMIC_ZOOM_DISTANCE));"
        in js
    )
    assert (
        "const followDistance = CAMERA_FOLLOW_DISTANCE_NEAR + (CAMERA_FOLLOW_DISTANCE_FAR - CAMERA_FOLLOW_DISTANCE_NEAR) * zoomRatio;"
        in js
    )
    assert (
        "const cameraHeight = CAMERA_HEIGHT_NEAR + (CAMERA_HEIGHT_FAR - CAMERA_HEIGHT_NEAR) * zoomRatio;"
        in js
    )
    assert (
        "const focusX = gameState.player.position.x * 0.82 + gameState.enemy.position.x * 0.18;"
        in js
    )
    assert "speedBonusMultiplier: 1" in js
    assert (
        "const speedBonusMultiplier = Math.max(1, gameState.player.speedBonusMultiplier || 1);"
        in js
    )
    assert (
        "const speed = PLAYER_BASE_SPEED * speedBonusMultiplier * (inputState.sprint ? PLAYER_SPRINT_MULTIPLIER : 1);"
        in js
    )
