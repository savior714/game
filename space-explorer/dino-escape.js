const THREE_MODULE_URL = "https://unpkg.com/three@0.165.0/build/three.module.js";

const WEAPON_TIERS = [
  { id: "stone", unlockScore: 0, damage: 1, cooldownMs: 700, projectileSpeed: 18, projectileSize: 0.2, label: "STONE" },
  { id: "spear", unlockScore: 50, damage: 3, cooldownMs: 500, projectileSpeed: 25, projectileSize: 0.16, label: "SPEAR" },
  { id: "gun", unlockScore: 150, damage: 8, cooldownMs: 150, projectileSpeed: 45, projectileSize: 0.12, label: "GUN" },
];

const DIFFICULTY_WAVE_TABLE = [
  { score: 0, multiplier: 0.82 },    // early relief
  { score: 30, multiplier: 1.0 },    // normal baseline
  { score: 90, multiplier: 1.22 },   // tension rise
  { score: 150, multiplier: 0.97 },  // gun unlock recovery
  { score: 240, multiplier: 1.28 },  // late pressure
  { score: 360, multiplier: 1.45 },  // endgame squeeze
];

const ARENA_LIMIT = 24;
const PLAYER_BASE_SPEED = 8;
const PLAYER_SPRINT_MULTIPLIER = 1.6;
const ENEMY_BASE_SPEED = 3.4;
const ENEMY_SPEED_SCALE_WITH_SCORE = 0.012;
const ENEMY_HIT_RADIUS = 1.25;
const ENEMY_CATCH_RADIUS = 1.8;
const ENEMY_MAX_HEALTH = 28;
const PROJECTILE_LIFETIME = 2.6;
const PROJECTILE_SPAWN_OFFSET = 1.25;

const canvas = document.getElementById("dino-escape-canvas");
const scoreEl = document.getElementById("dino-score");
const currentWeaponEl = document.getElementById("dino-current-weapon");
const nextUnlockEl = document.getElementById("dino-next-unlock");
const nextProgressFillEl = document.getElementById("dino-next-progress-fill");
const statusEl = document.getElementById("dino-status");
const restartButton = document.getElementById("dino-restart-button");
const hitFlashEl = document.getElementById("dino-hit-flash");
const unlockToastEl = document.getElementById("dino-unlock-toast");
const debugMultiplierEl = document.getElementById("dino-debug-multiplier");
const debugEnemySpeedEl = document.getElementById("dino-debug-enemy-speed");

if (
  !canvas ||
  !scoreEl ||
  !currentWeaponEl ||
  !nextUnlockEl ||
  !nextProgressFillEl ||
  !statusEl ||
  !restartButton ||
  !hitFlashEl ||
  !unlockToastEl ||
  !debugMultiplierEl ||
  !debugEnemySpeedEl
) {
  throw new Error("dino-escape page is missing required elements.");
}

function vec3(x = 0, y = 0, z = 0) {
  return { x, y, z };
}

function length2d(vector) {
  return Math.hypot(vector.x, vector.z);
}

function normalize2d(vector) {
  const len = Math.max(0.0001, length2d(vector));
  return vec3(vector.x / len, 0, vector.z / len);
}

function distance2d(a, b) {
  return Math.hypot(a.x - b.x, a.z - b.z);
}

function clampToArena(position) {
  return vec3(
    Math.max(-ARENA_LIMIT, Math.min(ARENA_LIMIT, position.x)),
    0,
    Math.max(-ARENA_LIMIT, Math.min(ARENA_LIMIT, position.z))
  );
}

function cloneVec3(value) {
  return vec3(value.x, value.y, value.z);
}

function createInitialGameState() {
  return {
    running: true,
    score: 0,
    level: 1,
    player: {
      position: vec3(0, 0, 0),
      velocity: vec3(0, 0, 0),
      facing: vec3(0, 0, 1),
      currentWeapon: "stone",
      lastFireTime: -9999,
    },
    enemy: {
      position: vec3(-10, 0, -10),
      velocity: vec3(0, 0, 0),
      speed: ENEMY_BASE_SPEED,
      health: ENEMY_MAX_HEALTH,
      aggression: 0,
    },
    projectiles: [],
  };
}

function getCurrentWeapon(score) {
  let selected = WEAPON_TIERS[0];
  for (const tier of WEAPON_TIERS) {
    if (score >= tier.unlockScore) {
      selected = tier;
    }
  }
  return selected;
}

function getNextWeapon(score) {
  return WEAPON_TIERS.find((tier) => score < tier.unlockScore) ?? null;
}

function getDifficultyMultiplier(score) {
  const normalizedScore = Math.max(0, score);
  let lower = DIFFICULTY_WAVE_TABLE[0];
  let upper = DIFFICULTY_WAVE_TABLE[DIFFICULTY_WAVE_TABLE.length - 1];

  for (let i = 0; i < DIFFICULTY_WAVE_TABLE.length - 1; i += 1) {
    const current = DIFFICULTY_WAVE_TABLE[i];
    const next = DIFFICULTY_WAVE_TABLE[i + 1];
    if (normalizedScore >= current.score && normalizedScore <= next.score) {
      lower = current;
      upper = next;
      break;
    }
  }

  if (normalizedScore <= lower.score) {
    return lower.multiplier;
  }
  if (normalizedScore >= upper.score) {
    return upper.multiplier;
  }

  const t = (normalizedScore - lower.score) / Math.max(1, upper.score - lower.score);
  return lower.multiplier + (upper.multiplier - lower.multiplier) * t;
}

const inputState = {
  moveX: 0,
  moveZ: 0,
  sprint: false,
  fireQueued: false,
};

const keyState = new Set();
window.addEventListener("keydown", (event) => {
  keyState.add(event.code);
});
window.addEventListener("keyup", (event) => {
  keyState.delete(event.code);
});
canvas.addEventListener("click", () => {
  inputState.fireQueued = true;
});

function readInput() {
  const x = (keyState.has("KeyD") ? 1 : 0) - (keyState.has("KeyA") ? 1 : 0);
  const z = (keyState.has("KeyS") ? 1 : 0) - (keyState.has("KeyW") ? 1 : 0);
  inputState.moveX = x;
  inputState.moveZ = z;
  inputState.sprint = keyState.has("ShiftLeft") || keyState.has("ShiftRight");
}

function updatePlayerMovement(gameState, delta) {
  const raw = vec3(inputState.moveX, 0, inputState.moveZ);
  const hasMoveInput = length2d(raw) > 0;
  const dir = hasMoveInput ? normalize2d(raw) : gameState.player.facing;
  const speed = PLAYER_BASE_SPEED * (inputState.sprint ? PLAYER_SPRINT_MULTIPLIER : 1);

  gameState.player.velocity = vec3(dir.x * speed, 0, dir.z * speed);
  gameState.player.position = clampToArena(vec3(
    gameState.player.position.x + gameState.player.velocity.x * delta,
    0,
    gameState.player.position.z + gameState.player.velocity.z * delta
  ));

  if (hasMoveInput) {
    gameState.player.facing = dir;
  }
}

function updateEnemyChase(gameState, delta) {
  const toPlayer = vec3(
    gameState.player.position.x - gameState.enemy.position.x,
    0,
    gameState.player.position.z - gameState.enemy.position.z
  );
  const dir = normalize2d(toPlayer);
  const difficultyMultiplier = getDifficultyMultiplier(gameState.score);
  gameState.enemy.speed = (ENEMY_BASE_SPEED + gameState.score * ENEMY_SPEED_SCALE_WITH_SCORE) * difficultyMultiplier;
  gameState.enemy.velocity = vec3(dir.x * gameState.enemy.speed, 0, dir.z * gameState.enemy.speed);
  gameState.enemy.position = clampToArena(vec3(
    gameState.enemy.position.x + gameState.enemy.velocity.x * delta,
    0,
    gameState.enemy.position.z + gameState.enemy.velocity.z * delta
  ));
  gameState.enemy.aggression = Math.min(1, Math.max(0, 1 - distance2d(gameState.player.position, gameState.enemy.position) / 18));
}

function tryFireProjectile(gameState, time) {
  const weapon = getCurrentWeapon(gameState.score);
  if (!inputState.fireQueued) {
    return;
  }
  inputState.fireQueued = false;

  if (time - gameState.player.lastFireTime < weapon.cooldownMs) {
    return;
  }

  const projectile = {
    id: `p-${Math.random().toString(36).slice(2, 9)}`,
    weaponId: weapon.id,
    position: vec3(
      gameState.player.position.x + gameState.player.facing.x * PROJECTILE_SPAWN_OFFSET,
      0.6,
      gameState.player.position.z + gameState.player.facing.z * PROJECTILE_SPAWN_OFFSET
    ),
    velocity: vec3(
      gameState.player.facing.x * weapon.projectileSpeed,
      0,
      gameState.player.facing.z * weapon.projectileSpeed
    ),
    damage: weapon.damage,
    alive: true,
    lifeTime: PROJECTILE_LIFETIME,
  };

  gameState.projectiles.push(projectile);
  gameState.player.lastFireTime = time;
}

function updateProjectiles(gameState, delta) {
  for (const projectile of gameState.projectiles) {
    if (!projectile.alive) {
      continue;
    }
    projectile.position = vec3(
      projectile.position.x + projectile.velocity.x * delta,
      projectile.position.y,
      projectile.position.z + projectile.velocity.z * delta
    );
    projectile.lifeTime -= delta;
    if (
      projectile.lifeTime <= 0 ||
      Math.abs(projectile.position.x) > ARENA_LIMIT + 4 ||
      Math.abs(projectile.position.z) > ARENA_LIMIT + 4
    ) {
      projectile.alive = false;
    }
  }
  gameState.projectiles = gameState.projectiles.filter((projectile) => projectile.alive);
}

function respawnEnemy(gameState) {
  const side = Math.random() > 0.5 ? 1 : -1;
  gameState.enemy.position = vec3(ARENA_LIMIT * side, 0, (Math.random() * 2 - 1) * ARENA_LIMIT * 0.8);
  gameState.enemy.health = ENEMY_MAX_HEALTH;
}

function resolveHitsAndScoring(gameState) {
  for (const projectile of gameState.projectiles) {
    if (!projectile.alive) {
      continue;
    }
    const hitDistance = distance2d(projectile.position, gameState.enemy.position);
    if (hitDistance < ENEMY_HIT_RADIUS) {
      projectile.alive = false;
      gameState.enemy.health -= projectile.damage;
      gameState.score += projectile.damage * 10;
      statusEl.textContent = `명중! +${projectile.damage * 10}점`;
      hitFlashStrength = Math.min(0.55, hitFlashStrength + 0.2);
      cameraShakeStrength = Math.min(0.4, cameraShakeStrength + 0.09);
      hitStopFrames = Math.max(hitStopFrames, 2);
      playHitSound(320 + projectile.damage * 35, 0.065);
    }
  }

  if (gameState.enemy.health <= 0) {
    gameState.score += 20;
    statusEl.textContent = "공룡을 잠시 밀어냈어요! +20 보너스";
    hitFlashStrength = Math.min(0.55, hitFlashStrength + 0.26);
    cameraShakeStrength = Math.min(0.45, cameraShakeStrength + 0.12);
    hitStopFrames = Math.max(hitStopFrames, 4);
    playHitSound(210, 0.12);
    respawnEnemy(gameState);
  }
}

function updateWeaponUnlock(gameState) {
  const unlocked = getCurrentWeapon(gameState.score);
  if (unlocked.id !== gameState.player.currentWeapon) {
    gameState.player.currentWeapon = unlocked.id;
    statusEl.textContent = `${unlocked.label} 해금! 더 빠르게 생존해 보세요.`;
    showUnlockToast(`${unlocked.label} UNLOCKED`);
    playHitSound(520, 0.08);
  }
}

function checkGameOver(gameState) {
  const catchDistance = distance2d(gameState.player.position, gameState.enemy.position);
  if (catchDistance < ENEMY_CATCH_RADIUS) {
    gameState.running = false;
    statusEl.textContent = `게임 오버! 최종 점수 ${gameState.score}`;
  }
}

function updateHud(gameState) {
  scoreEl.textContent = String(gameState.score);
  const activeWeapon = getCurrentWeapon(gameState.score);
  currentWeaponEl.textContent = activeWeapon.label;
  const next = getNextWeapon(gameState.score);
  if (next) {
    const previousUnlockScore = activeWeapon.unlockScore;
    const neededRange = Math.max(1, next.unlockScore - previousUnlockScore);
    const gained = Math.max(0, gameState.score - previousUnlockScore);
    const ratio = Math.max(0, Math.min(1, gained / neededRange));
    nextUnlockEl.textContent = `${next.label} at ${next.unlockScore}`;
    nextProgressFillEl.style.width = `${Math.round(ratio * 100)}%`;
  } else {
    nextUnlockEl.textContent = "ALL UNLOCKED";
    nextProgressFillEl.style.width = "100%";
  }
}

function updateDebugHud(gameState) {
  const difficultyMultiplier = getDifficultyMultiplier(gameState.score);
  debugMultiplierEl.textContent = `Difficulty x${difficultyMultiplier.toFixed(2)}`;
  debugEnemySpeedEl.textContent = `Enemy Speed ${gameState.enemy.speed.toFixed(2)}`;
}

let gameState = createInitialGameState();
let hitFlashStrength = 0;
let cameraShakeStrength = 0;
let unlockToastTimer = 0;
let hitStopFrames = 0;
let audioContext = null;

function updateHitFlash(delta) {
  hitFlashStrength = Math.max(0, hitFlashStrength - delta * 3.2);
  hitFlashEl.style.opacity = String(Math.min(0.55, hitFlashStrength));
}

function playHitSound(frequency = 320, duration = 0.06) {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) {
    return;
  }
  if (!audioContext) {
    audioContext = new AudioContextClass();
  }
  const oscillator = audioContext.createOscillator();
  const gainNode = audioContext.createGain();
  oscillator.type = "triangle";
  oscillator.frequency.value = frequency;
  gainNode.gain.value = 0.0001;
  oscillator.connect(gainNode);
  gainNode.connect(audioContext.destination);
  const now = audioContext.currentTime;
  gainNode.gain.exponentialRampToValueAtTime(0.14, now + 0.01);
  gainNode.gain.exponentialRampToValueAtTime(0.0001, now + duration);
  oscillator.start(now);
  oscillator.stop(now + duration + 0.01);
}

function showUnlockToast(message) {
  unlockToastEl.textContent = message;
  unlockToastTimer = 1.5;
  unlockToastEl.style.opacity = "1";
  unlockToastEl.style.transform = "translateX(-50%) translateY(0)";
}

function updateUnlockToast(delta) {
  if (unlockToastTimer <= 0) {
    unlockToastEl.style.opacity = "0";
    unlockToastEl.style.transform = "translateX(-50%) translateY(-8px)";
    return;
  }
  unlockToastTimer = Math.max(0, unlockToastTimer - delta);
}

function applyCameraShake() {
  if (cameraShakeStrength <= 0.0001) {
    return;
  }
  const jitterX = (Math.random() * 2 - 1) * cameraShakeStrength;
  const jitterY = (Math.random() * 2 - 1) * cameraShakeStrength * 0.5;
  const jitterZ = (Math.random() * 2 - 1) * cameraShakeStrength;
  camera.position.x += jitterX;
  camera.position.y += jitterY;
  camera.position.z += jitterZ;
}

restartButton.addEventListener("click", () => {
  gameState = createInitialGameState();
  hitFlashStrength = 0;
  cameraShakeStrength = 0;
  unlockToastTimer = 0;
  hitStopFrames = 0;
  hitFlashEl.style.opacity = "0";
  unlockToastEl.style.opacity = "0";
  statusEl.textContent = "새 게임 시작! 공룡에게 잡히지 않게 도망치세요.";
});

const THREE = await import(THREE_MODULE_URL);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x101826);

const camera = new THREE.PerspectiveCamera(58, 16 / 9, 0.1, 200);
camera.position.set(0, 10, 14);

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));

function onResize() {
  const width = Math.max(1, canvas.clientWidth || canvas.width);
  const height = Math.max(1, canvas.clientHeight || canvas.height);
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}
onResize();
window.addEventListener("resize", onResize, { passive: true });

scene.add(new THREE.AmbientLight(0xffffff, 0.6));
const keyLight = new THREE.DirectionalLight(0xffffff, 1.1);
keyLight.position.set(5, 8, 3);
scene.add(keyLight);

const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(62, 62),
  new THREE.MeshStandardMaterial({ color: 0x1f2937, roughness: 0.95 })
);
ground.rotation.x = -Math.PI / 2;
scene.add(ground);

const playerMesh = new THREE.Mesh(
  new THREE.BoxGeometry(0.9, 1.2, 0.9),
  new THREE.MeshStandardMaterial({ color: 0x60a5fa })
);
playerMesh.position.y = 0.6;
scene.add(playerMesh);

const enemyMesh = new THREE.Mesh(
  new THREE.BoxGeometry(1.2, 1.2, 1.6),
  new THREE.MeshStandardMaterial({ color: 0xef4444 })
);
enemyMesh.position.y = 0.6;
scene.add(enemyMesh);

const projectileMeshes = new Map();

function syncRenderObjectsFromState() {
  playerMesh.position.set(gameState.player.position.x, 0.6, gameState.player.position.z);
  playerMesh.rotation.y = Math.atan2(gameState.player.facing.x, gameState.player.facing.z);

  enemyMesh.position.set(gameState.enemy.position.x, 0.6, gameState.enemy.position.z);
  enemyMesh.rotation.y = Math.atan2(gameState.player.position.x - gameState.enemy.position.x, gameState.player.position.z - gameState.enemy.position.z);

  const activeIds = new Set(gameState.projectiles.map((projectile) => projectile.id));

  for (const projectile of gameState.projectiles) {
    let mesh = projectileMeshes.get(projectile.id);
    if (!mesh) {
      const tier = WEAPON_TIERS.find((item) => item.id === projectile.weaponId) ?? WEAPON_TIERS[0];
      mesh = new THREE.Mesh(
        new THREE.SphereGeometry(tier.projectileSize, 12, 12),
        new THREE.MeshStandardMaterial({ color: 0xfbbf24 })
      );
      projectileMeshes.set(projectile.id, mesh);
      scene.add(mesh);
    }
    mesh.position.set(projectile.position.x, projectile.position.y, projectile.position.z);
  }

  for (const [id, mesh] of projectileMeshes.entries()) {
    if (!activeIds.has(id)) {
      scene.remove(mesh);
      projectileMeshes.delete(id);
    }
  }
}

function updateCameraFollow(delta) {
  const desired = new THREE.Vector3(
    gameState.player.position.x - gameState.player.facing.x * 7,
    7.5,
    gameState.player.position.z - gameState.player.facing.z * 7
  );
  camera.position.lerp(desired, Math.min(1, delta * 3.2));
  cameraShakeStrength = Math.max(0, cameraShakeStrength - delta * 1.65);
  applyCameraShake();
  camera.lookAt(gameState.player.position.x, 0.8, gameState.player.position.z);
}

let previousMs = performance.now();
renderer.setAnimationLoop((timeMs) => {
  const delta = Math.min(0.05, (timeMs - previousMs) / 1000);
  previousMs = timeMs;

  if (hitStopFrames > 0) {
    hitStopFrames -= 1;
    updateHitFlash(delta);
    updateUnlockToast(delta);
    syncRenderObjectsFromState();
    updateCameraFollow(delta);
    renderer.render(scene, camera);
    return;
  }

  if (gameState.running) {
    readInput();
    updatePlayerMovement(gameState, delta);
    updateEnemyChase(gameState, delta);
    updateWeaponUnlock(gameState);
    tryFireProjectile(gameState, timeMs);
    updateProjectiles(gameState, delta);
    resolveHitsAndScoring(gameState);
    checkGameOver(gameState);
  }

  updateHud(gameState);
  updateDebugHud(gameState);
  updateHitFlash(delta);
  updateUnlockToast(delta);
  syncRenderObjectsFromState();
  updateCameraFollow(delta);
  renderer.render(scene, camera);
});
