/**
 * Dino Escape — 3D chase runner.
 *
 * The page is a thin shell: all simulation rules live in ./dino/run-model.js,
 * the world in ./dino/world.js, and this file wires the renderer, the HUD,
 * input, audio and persistence into a run loop.
 */

import * as THREE from "./vendor/three/build/three.module.min.js";
import {
  BIOMES,
  GAME_VERSION,
  HAZARD,
  PARTICLE_LIMITS,
  QUALITY,
  REX_LAYER,
  ROAD,
  RUN,
} from "./dino/constants.js";
import {
  clamp,
  clamp01,
  damp,
  dampAngle,
  formatMeters,
  lerp,
  randRange,
} from "./dino/util.js";
import {
  applyHit,
  collectAmber,
  collectBait,
  collectShield,
  createRunState,
  getBiomeProgress,
  getBiomeIndex,
  getComboMultiplier,
  getDangerLevel,
  getRunSummary,
  getSpeedKmh,
  stepRun,
  throwBait,
} from "./dino/run-model.js";
import { createExplorer, createShieldBubble, createTRex } from "./dino/models.js";
import { createWorld } from "./dino/world.js";
import { createParticlePool } from "./dino/particles.js";
import { createAudioEngine } from "./dino/audio.js";
import { createInput } from "./dino/input.js";
import { createHud } from "./dino/hud.js";
import { loadProfile, saveProfile } from "./dino/storage.js";
import { createEntityLayer } from "./dino/entities.js";
import { createSpawner } from "./dino/spawner.js";
import { createChaseDirector, rexStaging, yawToward } from "./dino/chase.js";
import {
  createPlayerState,
  hitTest,
  resetPlayer,
  stepPlayer,
} from "./dino/player.js";

// Plain symbols only: these are drawn with the page's own fonts so a device
// without an emoji font can never turn a toast into a tofu box.
const TOAST_ICONS = Object.freeze({
  amber: "★",
  bait: "◆",
  shield: "✚",
  danger: "!",
  good: "▲",
  info: "·",
});

function resolveQuality(setting) {
  if (setting === QUALITY.high || setting === QUALITY.low) {
    return setting;
  }
  const cores = navigator.hardwareConcurrency ?? 8;
  const memory = navigator.deviceMemory ?? 8;
  if (memory <= 4 || cores <= 4) {
    return QUALITY.low;
  }
  return QUALITY.high;
}

function pixelRatioFor(quality) {
  const raw = window.devicePixelRatio || 1;
  if (quality === QUALITY.low) {
    return Math.min(raw, 1);
  }
  return Math.min(raw, 2);
}

function dustColorFor(biome) {
  return new THREE.Color(biome.road).lerp(new THREE.Color(0xffffff), 0.18);
}

function boot() {
  const hud = createHud();
  const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches === true;
  const profile = loadProfile();
  hud.syncProfile(profile);

  const canvas = hud.elements.canvas;
  const biomeDust = BIOMES.map(dustColorFor);
  const amberSparkColor = new THREE.Color(0xffb52e);
  const dangerSparkColor = new THREE.Color(0xff5a2c);
  const shieldSparkColor = new THREE.Color(0x76f3ff);
  const fireflyColor = new THREE.Color(0xffe9a8);

  let renderer;
  let scene;
  let camera;
  let chase;
  let rexCamera;
  let world;
  let explorer;
  let rex;
  let shieldBubble;
  let dust;
  let sparks;
  let entities;
  let spawner;
  let audio;
  let input;

  const runState = { current: createRunState() };
  const player = createPlayerState();
  const hazards = [];
  const ambers = [];
  const pickups = [];

  const game = {
    mode: "boot",
    time: 0,
    startSwing: 0,
    caughtTimer: 0,
    rexGap: 4.2,
    rexX: 0,
    rexZ: -4.2,
    camBack: 8.6,
    shake: 0,
    dustTimer: 0,
    ambientTimer: 0,
    rexStepTimer: 0,
    roarTimer: 7,
    dangerToastTimer: 0,
    glance: { active: false, t: 0, duration: 1, weight: 0 },
    staminaToastArmed: true,
    recordAnnounced: false,
    firstBaitHint: false,
    firstShieldHint: false,
    chomped: false,
    tutorialSeen: new Set(),
    quality: QUALITY.auto,
    pixelRatio: 1,
    frameCount: 0,
    autoQualityTimer: 0,
    autoQualityFrames: 0,
    autoQualityTime: 0,
    rexYaw: 0,
    lastZ: 0,
  };

  const view = {
    distance: 0,
    best: profile.bestDistance,
    gap: RUN.startGap,
    amber: 0,
    comboMultiplier: 1,
    chain: 0,
    comboRatio: 0,
    shield: 0,
    bait: 0,
    speedKmh: 0,
    sprinting: false,
    stamina: 1,
    staminaLocked: false,
    danger: 0,
    biomeName: BIOMES[0].name,
    biomeAccent: BIOMES[0].accent,
    nextBiome: null,
    nextBiomeDistance: 0,
    biomeProgress: 0,
    eating: false,
  };

  let saveTimer = 0;
  function scheduleSave() {
    window.clearTimeout(saveTimer);
    saveTimer = window.setTimeout(() => saveProfile(profile), 220);
  }

  function currentBiome() {
    return BIOMES[Math.min(BIOMES.length - 1, runState.current.biomeIndex)] ?? BIOMES[0];
  }

  /* ------------------------------------------------------------------ */
  /* Audio                                                               */
  /* ------------------------------------------------------------------ */

  function createAudio() {
    audio = createAudioEngine({
      sound: profile.settings.sound,
      music: profile.settings.music,
      sfxVolume: profile.settings.sfxVolume,
      musicVolume: profile.settings.musicVolume,
    });
    audio.setMode("menu");
    audio.setBiome("jungle");
    return audio;
  }

  async function unlockAudio() {
    if (!audio || audio.isUnlocked) {
      return;
    }
    const ok = await audio.unlock();
    if (ok) {
      audio.setSettings(profile.settings);
      audio.setBiome(currentBiome().id);
    }
  }

  function playSfx(name, ...args) {
    if (!audio || !audio.isUnlocked) {
      return;
    }
    const fn = audio[name];
    if (typeof fn === "function") {
      fn.apply(audio, args);
    }
  }

  /* ------------------------------------------------------------------ */
  /* Stage                                                               */
  /* ------------------------------------------------------------------ */

  function initStage() {
    renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: false,
      stencil: false,
      powerPreference: "high-performance",
    });
    renderer.setClearColor(0x0a1214, 1);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.shadowMap.autoUpdate = true;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.autoClear = false;

    scene = new THREE.Scene();

    camera = new THREE.PerspectiveCamera(55, 1, 0.1, 640);
    camera.layers.enable(REX_LAYER);
    camera.position.set(-2.85, 2.28, 7.35);
    chase = createChaseDirector();

    rexCamera = new THREE.PerspectiveCamera(46, 1.6, 0.1, 640);
    rexCamera.layers.set(REX_LAYER);

    world = createWorld(scene, renderer, { quality: resolveQuality(profile.settings.quality) });

    explorer = createExplorer();
    explorer.root.traverse((object) => object.layers.enable(REX_LAYER));
    scene.add(explorer.root);

    rex = createTRex();
    rex.root.traverse((object) => object.layers.enable(REX_LAYER));
    scene.add(rex.root);

    shieldBubble = createShieldBubble();
    shieldBubble.root.traverse((object) => object.layers.enable(REX_LAYER));
    scene.add(shieldBubble.root);

    dust = createParticlePool(scene, { max: PARTICLE_LIMITS.dust });
    sparks = createParticlePool(scene, { max: PARTICLE_LIMITS.sparks, additive: true });

    entities = createEntityLayer(scene);
    spawner = createSpawner();

    resize();
    applyQuality(profile.settings.quality);
  }

  function applyQuality(setting) {
    game.quality = resolveQuality(setting);
    game.pixelRatio = pixelRatioFor(game.quality);
    renderer.setPixelRatio(game.pixelRatio);
    world.setQuality(game.quality);
    resize();
  }

  function resize() {
    if (!renderer) {
      return;
    }
    const width = Math.max(320, window.innerWidth);
    const height = Math.max(240, window.innerHeight);
    renderer.setPixelRatio(game.pixelRatio);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    world.setViewportSize(width, height, game.pixelRatio);
    if (dust) {
      dust.setViewport(height, game.pixelRatio);
    }
    if (sparks) {
      sparks.setViewport(height, game.pixelRatio);
    }
    hud.measureRexCam();
  }

  /* ------------------------------------------------------------------ */
  /* Run lifecycle                                                       */
  /* ------------------------------------------------------------------ */

  function resetRun() {
    runState.current = createRunState();
    resetPlayer(player, 0);
    player.z = 0;
    hazards.length = 0;
    ambers.length = 0;
    pickups.length = 0;
    entities.clear();
    spawner.reset();
    game.rexGap = 9.4;
    game.rexX = player.x;
    game.rexZ = -9.4;
    game.caughtTimer = 0;
    game.startSwing = 0;
    game.shake = 0;
    game.chomped = false;
    game.lastZ = 0;
    game.recordAnnounced = false;
    game.firstBaitHint = false;
    game.firstShieldHint = false;
    game.staminaToastArmed = true;
    game.tutorialSeen.clear();
    game.roarTimer = 6;
    game.dangerToastTimer = 0;
    game.rexYaw = 0;
    game.rexStepTimer = 0;
    chase.reset("menu");
    world.setBiome(0);
    spawnAhead();
    updateHud();
  }

  function startRun() {
    if (game.mode === "running" || game.mode === "caught") {
      return;
    }
    resetRun();
    game.mode = "running";
    game.startSwing = reduceMotion ? 0 : 1;
    if (reduceMotion) {
      chase.reset("running");
    } else {
      chase.startSwing();
    }
    hud.hideBoot();
    hud.hideAllScreens();
    hud.setHudVisible(true);
    hud.blurActive();
    hud.setTutorial(window.matchMedia?.("(pointer: coarse)")?.matches ? "화면을 좌우로 드래그해 방향을 바꿔요" : "A / D 또는 ← → 로 좌우 이동");
    hud.announce("탈출 시작. 렉스가 뒤쫓아옵니다.");
    profile.runs += 1;
    scheduleSave();
    input.setEnabled(true);
    audio.setMode("running");
    audio.setThreat(0);
    void unlockAudio();
  }

  function pauseRun() {
    if (game.mode !== "running") {
      return;
    }
    game.mode = "paused";
    hud.updatePause(view);
    hud.showScreen("pause");
    hud.focusPrimary();
    audio.setMode("paused");
    audio.setThreat(0);
    playSfx("uiBack");
    hud.announce("일시정지");
  }

  function resumeRun() {
    if (game.mode !== "paused") {
      return;
    }
    game.mode = "running";
    hud.hideAllScreens();
    hud.blurActive();
    input.setEnabled(false);
    input.setEnabled(true);
    audio.setMode("running");
    playSfx("uiClick");
  }

  function goToMenu() {
    if (game.mode === "running" || game.mode === "caught" || game.mode === "boot") {
      return;
    }
    resetRun();
    game.mode = "menu";
    hud.setHudVisible(false);
    hud.closeSettings();
    hud.showScreen("start");
    hud.syncProfile(profile);
    input.setEnabled(false);
    audio.setMode("menu");
    audio.setThreat(0);
  }

  function finishRun() {
    if (game.mode !== "caught") {
      return;
    }
    const summary = getRunSummary(runState.current);
    const previousBest = profile.bestDistance;
    const newRecord = summary.distance > previousBest;
    profile.bestDistance = Math.max(profile.bestDistance, summary.distance);
    profile.bestCombo = Math.max(profile.bestCombo, summary.bestChain);
    saveProfile(profile);
    hud.syncProfile(profile);
    hud.setHudVisible(false);
    hud.showGameOver({
      distance: summary.distance,
      amber: summary.amber,
      bestChain: summary.bestChain,
      hits: summary.hits,
      best: profile.bestDistance,
      newRecord,
    });
    game.mode = "gameover";
    playSfx("gameOver");
    audio.setMode("caught");
    hud.announce(
      newRecord
        ? `새 기록. ${formatMeters(summary.distance)}미터.`
        : `${formatMeters(summary.distance)}미터에서 잡혔습니다.`,
    );
  }

  function beginCaught() {
    if (game.mode !== "running") {
      return;
    }
    game.mode = "caught";
    game.caughtTimer = 0;
    game.chomped = false;
    game.shake = 1;
    input.setEnabled(false);
    hud.flash("danger", 700);
    hud.toast("렉스에게 잡혔다!", { tone: "danger", icon: "☠", duration: 2200 });
    hud.setTutorial("");
    audio.setMode("caught");
    audio.setThreat(1);
    playSfx("roar", 1.4);
    popParticles(player.x, 1.1, player.z, 18, dangerSparkColor, 6, sparks);
    hud.announce("잡혔습니다.");
  }

  /* ------------------------------------------------------------------ */
  /* Spawning + collisions                                               */
  /* ------------------------------------------------------------------ */

  function addDescriptor(descriptor) {
    if (descriptor.kind === "hazard") {
      hazards.push(descriptor);
    } else if (descriptor.kind === "amber") {
      ambers.push(descriptor);
    } else {
      pickups.push(descriptor);
    }
    entities.add(descriptor);
  }

  function spawnAhead() {
    const spawnedNow = spawner.update(runState.current.distance, HAZARD.spawnAhead);
    for (const descriptor of spawnedNow) {
      addDescriptor(descriptor);
    }
  }

  function pruneFrom(list, behind = HAZARD.despawnBehind) {
    for (let i = list.length - 1; i >= 0; i -= 1) {
      const descriptor = list[i];
      if (descriptor.dead || descriptor.z < player.z - behind) {
        entities.remove(descriptor);
        list.splice(i, 1);
      }
    }
  }

  // The chase camera rides ~13 m behind the runner, so a missed collectible
  // drifts toward the lens for a while. entities.js shrinks it out between
  // 6.5 m and 10.5 m behind the runner; prune just after that window closes.
  const PICKUP_DESPAWN_BEHIND = 10.6;

  function updateEntities(dt) {
    pruneFrom(hazards, HAZARD.despawnBehind);
    pruneFrom(ambers, PICKUP_DESPAWN_BEHIND);
    pruneFrom(pickups, PICKUP_DESPAWN_BEHIND);
    entities.update(dt, game.time, player.z);
  }

  function updateGeysers(dt) {
    for (const hazard of hazards) {
      if (hazard.type !== "geyser") {
        continue;
      }
      const relative = hazard.z - player.z;
      if (!hazard.started && relative < 44 && relative > 8) {
        hazard.started = true;
        hazard.timer = 0;
      }
      if (hazard.started) {
        hazard.timer += dt;
        const wasErupting = hazard.erupting;
        hazard.warning = hazard.timer < 1.15;
        hazard.erupting = hazard.timer >= 1.15 && hazard.timer < 4.2;
        if (hazard.erupting && !wasErupting && relative < 50 && relative > -4) {
          playSfx("geyser");
          popParticles(hazard.x, 0.4, hazard.z, 10, biomeDust[runState.current.biomeIndex], 4, dust);
        }
        if (hazard.timer > 5.2) {
          hazard.started = false;
        }
      }
    }
  }

  function sweptNear(hazard, previousZ) {
    const travel = Math.max(0, player.z - previousZ);
    const pad = Math.max(0, hazard.depth ?? 0.9) + travel * 0.75;
    return hazard.z > previousZ - pad - 0.3 && hazard.z < player.z + pad + 0.3;
  }

  function collectNearbyPickups() {
    const run = runState.current;
    const centerY = player.y + (player.sliding ? 0.36 : 0.9);
    for (let i = pickups.length - 1; i >= 0; i -= 1) {
      const item = pickups[i];
      const dz = item.z - player.z;
      if (dz > 1.6 || dz < -1.4) {
        continue;
      }
      if (Math.abs(item.x - player.x) > 1.25) {
        continue;
      }
      if (Math.abs((item.y ?? 1.15) - centerY) > 1.9) {
        continue;
      }
      const result = item.kind === "shield" ? collectShield(run) : collectBait(run);
      if (result.type === "shield") {
        if (result.full) {
          hud.toast("방패 가득 · 호박 +5", { tone: "cyan", icon: TOAST_ICONS.amber });
        } else {
          hud.toast("방패 +1", { tone: "cyan", icon: TOAST_ICONS.shield });
          if (!game.firstShieldHint) {
            game.firstShieldHint = true;
            hud.setTutorial("방패는 충돌 한 번을 막아줘요");
          }
        }
        playSfx("shieldPickup");
        popParticles(item.x, item.y ?? 1.1, item.z, 12, shieldSparkColor, 3.2, sparks);
        hud.announce(result.full ? "방패가 가득 찼습니다." : "방패를 얻었습니다.");
      } else {
        if (result.full) {
          hud.toast("미끼 가득 · 호박 +5", { tone: "amber", icon: TOAST_ICONS.amber });
        } else {
          hud.toast("미끼 +1", { tone: "amber", icon: TOAST_ICONS.bait });
          if (!game.firstBaitHint) {
            game.firstBaitHint = true;
            hud.setTutorial("E 또는 고기 버튼으로 미끼를 던져 렉스를 멈춰요");
          }
        }
        playSfx("baitPickup");
        popParticles(item.x, item.y ?? 1.1, item.z, 10, amberSparkColor, 2.6, sparks);
        hud.announce(result.full ? "미끼가 가득 찼습니다." : "미끼를 얻었습니다.");
      }
      item.collected = true;
      item.dead = true;
      entities.remove(item);
      pickups.splice(i, 1);
    }
  }

  function collectNearbyAmber() {
    const run = runState.current;
    const centerY = player.y + (player.sliding ? 0.36 : 0.9);
    for (let i = ambers.length - 1; i >= 0; i -= 1) {
      const amber = ambers[i];
      const dz = amber.z - player.z;
      if (dz > 1.5 || dz < -1.5) {
        continue;
      }
      if (Math.abs(amber.x - player.x) > 1.15) {
        continue;
      }
      if (Math.abs(amber.y - centerY) > 1.05) {
        continue;
      }
      const beforeMultiplier = getComboMultiplier(run);
      const result = collectAmber(run);
      amber.collected = true;
      amber.dead = true;
      entities.remove(amber);
      ambers.splice(i, 1);
      playSfx("amber", result.chain);
      popParticles(amber.x, amber.y, amber.z, 7, amberSparkColor, 2.2, sparks);
      const multiplier = getComboMultiplier(run);
      if (multiplier > beforeMultiplier) {
        hud.toast(`콤보 x${multiplier}`, { tone: "amber", icon: TOAST_ICONS.amber, duration: 1200 });
        hud.announce(`콤보 ${multiplier}배`);
      }
      if (result.baitAward) {
        hud.toast("미끼 +1", { tone: "cyan", icon: TOAST_ICONS.bait });
      }
    }
  }

  function resolveHazards(previousZ) {
    const run = runState.current;
    if (run.invuln > 0) {
      return;
    }
    for (const hazard of hazards) {
      if (!sweptNear(hazard, previousZ)) {
        continue;
      }
      if (hazard.type === "geyser" && !hazard.erupting) {
        continue;
      }
      const testZ = clamp(hazard.z, previousZ, player.z);
      if (!hitTest(player, hazard, testZ)) {
        continue;
      }
      const result = applyHit(run);
      if (result.type === "ignored") {
        continue;
      }
      if (result.type === "shielded") {
        shieldBubble.shatter();
        game.shake = Math.max(game.shake, 0.55);
        hud.flash("cyan", 320);
        hud.toast("방패가 막아냈다!", { tone: "cyan", icon: TOAST_ICONS.shield });
        hud.announce("방패로 충돌을 막았습니다.");
        playSfx("shieldBreak");
        popParticles(player.x, 1.0, player.z, 16, shieldSparkColor, 5, sparks);
        popParticles(hazard.x, 0.8, hazard.z, 14, biomeDust[runState.current.biomeIndex], 4, dust);
        continue;
      }
      if (result.type === "caught") {
        beginCaught();
        return;
      }
      // Normal hit: stumble, dust, rex lunges closer. There is deliberately
      // no camera cut here — the player needs the road in frame to recover.
      game.shake = Math.max(game.shake, 0.95);
      player.stumble = 0.7;
      hud.flash("danger", 420);
      hud.toast("렉스가 따라붙었다!", { tone: "danger", icon: TOAST_ICONS.danger, duration: 1500 });
      hud.setTutorial("");
      hud.announce("장애물에 부딪혔습니다. 렉스가 가까워졌습니다.");
      playSfx("hit");
      playSfx("roar", 0.5);
      popParticles(player.x, player.y + (player.sliding ? 0.3 : 0.8), player.z, 22, biomeDust[runState.current.biomeIndex], 6, dust);
      popParticles(hazard.x, 0.7, hazard.z, 14, dangerSparkColor, 4.5, sparks);
    }
  }

  /* ------------------------------------------------------------------ */
  /* Particles                                                           */
  /* ------------------------------------------------------------------ */

  function popParticles(x, y, z, count, color, speed, pool = dust) {
    if (!pool) {
      return;
    }
    for (let i = 0; i < count; i += 1) {
      const angle = Math.random() * Math.PI * 2;
      const force = randRange(speed * 0.35, speed);
      pool.spawn({
        x: x + Math.cos(angle) * 0.22,
        y: y + randRange(-0.1, 0.35),
        z: z + Math.sin(angle) * 0.22,
        vx: Math.cos(angle) * force,
        vy: randRange(0.6, speed * 0.9),
        vz: Math.sin(angle) * force,
        life: randRange(0.45, 1.1),
        size: randRange(0.09, 0.24),
        color,
        drag: 1.3,
        gravity: 7,
        floor: 0.02,
      });
    }
  }

  function updateAmbientParticles(dt) {
    const biome = currentBiome();
    game.ambientTimer -= dt;
    if (game.ambientTimer > 0) {
      return;
    }
    game.ambientTimer = game.quality === QUALITY.low ? 0.22 : 0.12;
    if (biome.id === "volcano") {
      sparks.spawn({
        x: player.x + randRange(-16, 16),
        y: randRange(0.2, 1.6),
        z: player.z + randRange(8, 60),
        vx: randRange(-0.8, 0.8),
        vy: randRange(1.1, 2.6),
        vz: randRange(-1.4, 0.6),
        life: randRange(1.6, 3.4),
        size: randRange(0.08, 0.2),
        color: dangerSparkColor,
        drag: 0.2,
        gravity: -0.5,
      });
    } else if (biome.id === "desert") {
      dust.spawn({
        x: player.x + randRange(-20, 20),
        y: randRange(0.4, 3.6),
        z: player.z + randRange(10, 70),
        vx: randRange(-1.2, 1.2),
        vy: randRange(-0.2, 0.5),
        vz: randRange(-3.4, -1.2),
        life: randRange(2.4, 4.4),
        size: randRange(0.12, 0.32),
        color: biomeDust[1],
        drag: 0.1,
        gravity: 0,
      });
    } else if (Math.random() < 0.65) {
      sparks.spawn({
        x: player.x + randRange(-14, 14),
        y: randRange(0.9, 3.4),
        z: player.z + randRange(12, 55),
        vx: randRange(-0.5, 0.5),
        vy: randRange(-0.15, 0.35),
        vz: randRange(-0.6, 0.2),
        life: randRange(2.2, 4.2),
        size: randRange(0.08, 0.16),
        color: fireflyColor,
        drag: 0.3,
        gravity: -0.05,
      });
    }
  }

  function emitRunParticles(dt, events) {
    const color = biomeDust[runState.current.biomeIndex] ?? biomeDust[0];
    game.dustTimer -= dt;
    const running = game.mode === "running";
    if (running && game.dustTimer <= 0) {
      game.dustTimer = player.sliding ? 0.035 : 0.11;
      const count = player.sliding ? 3 : 1;
      for (let i = 0; i < count; i += 1) {
        dust.spawn({
          x: player.x + randRange(-0.3, 0.3),
          y: 0.06 + randRange(0, 0.14),
          z: player.z - randRange(0.1, 0.7),
          vx: randRange(-1.4, 1.4),
          vy: randRange(0.3, player.sliding ? 1.8 : 0.9),
          vz: randRange(-4.5, -1.4),
          life: randRange(0.35, player.sliding ? 0.85 : 0.55),
          size: randRange(0.08, player.sliding ? 0.3 : 0.2),
          color,
          drag: 2.1,
          gravity: 1.6,
          floor: 0.02,
        });
      }
    }
    if (events.jumped) {
      popParticles(player.x, 0.1, player.z, 8, color, 2.4, dust);
      playSfx("jump");
    }
    if (events.landed) {
      popParticles(player.x, 0.08, player.z, 12, color, 3.2, dust);
      playSfx("land", 0.9);
    }
    if (events.slideStarted) {
      playSfx("slideStart");
    }
    if (events.slideStopped) {
      playSfx("slideStop");
    }
    if (events.footstep) {
      playSfx("footstep", player.sliding ? 0.55 : 1, (player.x / ROAD.halfWidth) * 0.35);
    }
    if (running && game.rexGap < 26) {
      game.rexStepTimer -= dt * (0.8 + runState.current.speed / 24);
      if (game.rexStepTimer <= 0) {
        game.rexStepTimer = 0.5;
        playSfx("footstep", 0.8, clamp(game.rexX / 6, -0.7, 0.7), true);
        // Close behind: each stomp kicks the camera and the dust.
        if (view.danger > 0.35) {
          const weight = clamp01((view.danger - 0.35) / 0.65);
          game.shake = Math.max(game.shake, 0.18 + weight * 0.32);
          chase.impulse(0.05 + weight * 0.09);
          popParticles(game.rexX, 0.08, game.rexZ, 4 + Math.round(weight * 4), color, 2.6, dust);
        }
        if (game.glance.weight > 0.05) {
          popParticles(game.rexX, 0.08, game.rexZ, 5, color, 2.2, dust);
        }
      }
    }
  }

  /* ------------------------------------------------------------------ */
  /* Run events                                                          */
  /* ------------------------------------------------------------------ */

  function handleRunEvents(events) {
    const run = runState.current;
    for (const event of events) {
      if (event.type === "milestone") {
        playSfx("milestone");
        hud.toast(`${formatMeters(event.distance)} M 돌파`, { tone: "good", icon: TOAST_ICONS.good, duration: 1300 });
        popParticles(player.x, 0.8, player.z + 1, 14, amberSparkColor, 3, sparks);
      } else if (event.type === "biome") {
        world.setBiome(event.index);
        audio.setBiome(event.biome.id);
        hud.showBiomeBanner(event.biome);
        hud.announce(`${event.biome.name} 진입`);
        playSfx("biomeShift");
        playSfx("roar", 0.8);
        game.shake = Math.max(game.shake, 0.22);
        popParticles(player.x, 1.2, player.z + 2, 24, amberSparkColor, 5, sparks);
        game.roarTimer = randRange(8, 14);
      } else if (event.type === "combo-end" && run.chain === 0) {
        // Silent by design: the HUD chip simply fades out.
      } else if (event.type === "caught") {
        beginCaught();
      }
    }
  }

  function throwBaitNow() {
    const run = runState.current;
    const result = throwBait(run);
    if (result.type !== "bait-thrown") {
      hud.toast(result.reason === "eating" ? "렉스가 이미 먹고 있어요" : "미끼가 없어요", {
        tone: "info",
        icon: TOAST_ICONS.bait,
        duration: 1100,
      });
      playSfx("uiBack");
      return;
    }
    playSfx("baitThrow");
    triggerGlance(0.95);
    const from = new THREE.Vector3(player.x, 1.15, player.z + 0.4);
    const to = new THREE.Vector3(game.rexX, 1.9, game.rexZ + 2.4);
    entities.throwBait(from, to, () => {
      playSfx("chomp");
      popParticles(game.rexX, 2.1, game.rexZ + 2.2, 16, dangerSparkColor, 4, sparks);
    });
    popParticles(player.x, 1.2, player.z + 0.6, 8, amberSparkColor, 2, sparks);
    hud.announce(`미끼를 던졌습니다. 남은 미끼 ${result.bait}개.`);
    if (!game.firstBaitHint) {
      game.firstBaitHint = true;
      hud.setTutorial("미끼를 먹는 동안 렉스와의 거리가 벌어져요");
    }
  }

  /* ------------------------------------------------------------------ */
  /* Update                                                              */
  /* ------------------------------------------------------------------ */

  function updateHud() {
    const run = runState.current;
    const biome = currentBiome();
    const progress = getBiomeProgress(run.distance);
    view.distance = run.distance;
    view.best = profile.bestDistance;
    view.gap = run.gap;
    view.amber = run.amber;
    view.comboMultiplier = getComboMultiplier(run);
    view.chain = run.chain;
    view.comboRatio = RUN.comboTimeout > 0 ? clamp01(run.comboTimer / RUN.comboTimeout) : 0;
    view.shield = run.shield;
    view.bait = run.bait;
    view.speedKmh = getSpeedKmh(run);
    view.sprinting = run.sprinting;
    view.stamina = run.stamina;
    view.staminaLocked = run.staminaLocked;
    view.danger = getDangerLevel(run);
    view.biomeName = biome.name;
    view.biomeAccent = biome.accent;
    view.nextBiome = progress.next;
    view.nextBiomeDistance = progress.remaining;
    view.biomeProgress = progress.progress;
    view.eating = run.eatTimer > 0;
    hud.updateRun(view);
    hud.setSpeedFx(clamp01((run.speed - 15) / 11));
  }

  function updateRunning(dt) {
    const run = runState.current;
    const previousZ = player.z;
    const axis = input.getAxis();
    const jump = input.consumeJump();
    const slideEdge = input.consumeSlide();
    const sprint = input.getSprintHeld();
    if (input.consumeBait()) {
      throwBaitNow();
    }
    if (slideEdge && player.sliding) {
      // Tapping slide again refreshes the slide.
      player.slideTimer = Math.min(0.9, player.slideTimer + 0.18);
    }
    const events = stepPlayer(player, dt, { axis, jump, slide: slideEdge, sprint, speed: run.speed });
    emitRunParticles(dt, events);
    if (!game.staminaToastArmed && !run.staminaLocked && run.stamina > 0.5) {
      game.staminaToastArmed = true;
    }

    const runEvents = stepRun(run, dt, { sprintHeld: sprint });
    player.z = run.distance;
    handleRunEvents(runEvents);
    if (game.mode !== "running") {
      return;
    }
    const dangerNow = getDangerLevel(run);

    // Stamina feedback.
    if (run.staminaLocked && game.staminaToastArmed) {
      game.staminaToastArmed = false;
      hud.toast("질주 게이지 소진", { tone: "info", icon: "≈", duration: 1200 });
    }

    updateGeysers(dt);
    collectNearbyPickups();
    collectNearbyAmber();
    resolveHazards(previousZ);
    if (game.mode !== "running") {
      return;
    }

    spawnAhead();
    updateEntities(dt);

    // Tutorial hints for the first encounter with each hazard type.
    for (const hazard of hazards) {
      if (hazard.type === "geyser" && !hazard.warning) {
        continue;
      }
      const ahead = hazard.z - player.z;
      if (ahead > 2 && ahead < 34 && !game.tutorialSeen.has(hazard.type)) {
        game.tutorialSeen.add(hazard.type);
        hud.setTutorial(hazard.hint);
      }
    }

    if (run.distance > profile.bestDistance && profile.bestDistance > 0 && !game.recordAnnounced) {
      game.recordAnnounced = true;
      hud.toast("신기록 페이스!", { tone: "good", icon: TOAST_ICONS.good, duration: 1600 });
    }

    // Rex roar cadence ramps up with danger.
    const danger = dangerNow;
    game.roarTimer -= dt;
    if (game.roarTimer <= 0) {
      game.roarTimer = randRange(9, 17) - danger * 4;
      rex.roar();
      playSfx("roar", 0.7 + danger * 0.5);
      game.shake = Math.max(game.shake, 0.18 + danger * 0.25);
    }
    game.dangerToastTimer = Math.max(0, game.dangerToastTimer - dt);
    if (danger > 0.86 && game.dangerToastTimer === 0) {
      game.dangerToastTimer = 9;
      hud.toast("렉스가 코앞이야!", { tone: "danger", icon: TOAST_ICONS.danger, duration: 1500 });
      playSfx("hit");
    }

    audio.setThreat(danger);
    updateHud();
    world.setBiome(run.biomeIndex);
    updateRex(dt, "running");
    updatePlayerVisual(dt, events);
    updateCamera(dt);
    game.autoQualityTime += dt;
    game.autoQualityFrames += 1;
    if (profile.settings.quality === QUALITY.auto && game.autoQualityTime > 5) {
      const average = game.autoQualityTime / game.autoQualityFrames;
      if (average > 0.026 && game.pixelRatio > 1) {
        game.pixelRatio = 1;
        renderer.setPixelRatio(1);
        world.setQuality(QUALITY.low);
        resize();
      }
      game.autoQualityFrames = 0;
      game.autoQualityTime = 0;
    }
  }

  function updatePlayerVisual(dt, events = {}) {
    explorer.root.position.set(player.x, player.y, player.z);
    explorer.root.rotation.y = player.tilt * 0.13;
    explorer.update(dt, {
      mode:
        game.mode === "menu"
          ? "intro"
          : game.mode === "caught" || game.mode === "gameover"
            ? "caught"
            : "running",
      speed: game.mode === "running" ? runState.current.speed : 0,
      sliding: player.sliding ? 1 : 0,
      tilt: player.tilt,
      grounded: player.grounded,
      vy: player.vy,
      landImpact: events.landed ? 1 : 0,
      stumble: player.stumble,
      time: game.time,
    });
    shieldBubble.root.position.set(player.x, player.y, player.z);
    shieldBubble.update(
      dt,
      game.time,
      runState.current.shield > 0 && (game.mode === "running" || game.mode === "paused"),
    );
  }

  /**
   * The gap is a real distance in metres, but a camera that trails the runner
   * cannot show a predator that far back. The director compresses the chase
   * onto a staged track (./dino/chase.js): the rex runs alongside and behind,
   * stays inside the right edge of frame, and leans in as the gap closes.
   */
  function updateRex(dt, mode) {
    const run = runState.current;
    const danger =
      mode === "running" ? clamp01(view.danger) : mode === "menu" ? 0.18 : 1;
    const stage = rexStaging(danger, mode, { t: game.time, eat: clamp01(run.eatTimer > 0 ? 1 : 0) });
    const targetX = mode === "menu" ? player.x - stage.lateral : clamp(player.x - stage.lateral, -9, 9);

    // Lateral / depth easing: fast enough to read as a lunge, slow enough that
    // lane changes do not teleport the predator across the track.
    game.rexX = damp(game.rexX, targetX, mode === "caught" ? 6.5 : 2.1, dt);
    game.rexGap = damp(game.rexGap, stage.behind, mode === "caught" ? 6 : 2.6, dt);
    game.rexZ = player.z - game.rexGap;

    rex.root.position.set(game.rexX, 0, game.rexZ);

    // Turn the body toward the runner so the chase reads as pursuit, not a race.
    const targetYaw = yawToward(game.rexX, game.rexZ, player.x, player.z + 0.6);
    game.rexYaw = dampAngle(game.rexYaw, targetYaw, mode === "caught" ? 7 : 3.2, dt);
    rex.root.rotation.y = game.rexYaw + Math.sin(game.time * 0.9) * 0.015;
    rex.root.rotation.z = -stage.lean * 0.05 + Math.sin(game.time * 2.1) * 0.008;

    const speed = mode === "running" ? run.speed : mode === "menu" ? 0 : 0;
    rex.update(dt, {
      mode,
      speed,
      danger,
      eating: run.eatTimer > 0,
      caught: mode === "caught" || mode === "gameover",
      time: game.time,
    });
    rex.setLunge(stage.bite);
    game.rexForwardness = stage.lean;
  }

  /* ------------------------------------------------------------------ */
  /* Camera                                                              */
  /* ------------------------------------------------------------------ */

  function applyCameraShake(dt) {
    game.shake = Math.max(0, game.shake - dt * 1.9);
    const amount = profile.settings.shake ? game.shake : 0;
    if (amount <= 0.001) {
      return 0;
    }
    camera.position.x += Math.sin(game.time * 71) * 0.17 * amount;
    camera.position.y += Math.sin(game.time * 93 + 1.7) * 0.14 * amount;
    camera.position.z += Math.sin(game.time * 57 + 0.6) * 0.09 * amount;
    return Math.sin(game.time * 47) * 0.03 * amount;
  }

  function updateCamera(dt) {
    const run = runState.current;
    const speedRatio = clamp01((run.speed - RUN.baseSpeed) / (RUN.maxSpeed - RUN.baseSpeed));
    const mode =
      game.mode === "running" || game.mode === "menu" || game.mode === "caught" || game.mode === "gameover"
        ? game.mode
        : "menu";
    const pose = chase.update(dt, {
      mode,
      player,
      danger: mode === "running" ? view.danger : mode === "menu" ? 0.18 : 1,
      speedRatio,
      sprinting: run.sprinting,
      rex: { x: game.rexX, z: game.rexZ },
      time: game.time,
      reduceMotion,
    });

    camera.position.set(pose.x, pose.y, pose.z);
    camera.lookAt(pose.lookX, pose.lookY, pose.lookZ);
    camera.fov = pose.fov;
    camera.updateProjectionMatrix();

    const glance = updateGlance(dt);
    applyGlancePose(glance);
    const roll = applyCameraShake(dt) + pose.roll;
    if (roll) {
      camera.rotateZ(roll);
    }
  }

  /**
   * Cinematic "look back" insert: a short reverse tracking shot from ahead of
   * the runner that frames the explorer's shoulder with the charging T-Rex.
   */
  function triggerGlance(duration = 1.3) {
    if (reduceMotion) {
      return;
    }
    game.glance.active = true;
    game.glance.t = 0;
    game.glance.duration = duration;
    game.glance.weight = 0;
  }

  function updateGlance(dt) {
    if (!game.glance.active) {
      game.glance.weight = 0;
      return 0;
    }
    game.glance.t += dt;
    const progress = clamp01(game.glance.t / game.glance.duration);
    game.glance.weight = Math.sin(progress * Math.PI) ** 0.85;
    if (progress >= 1) {
      game.glance.active = false;
      game.glance.weight = 0;
      return 0;
    }
    return game.glance.weight;
  }

  function applyGlancePose(weight) {
    if (weight <= 0.001) {
      return;
    }
    // Stand ahead and to the right of the runner, looking back down the trail
    // at both of them. The wide lens keeps the predator inside the frame.
    const insert = new THREE.Vector3(
      player.x + 4.35,
      2.55 + Math.sin(game.time * 1.7) * 0.04,
      player.z + 8.2,
    );
    camera.position.lerp(insert, weight);
    const focus = new THREE.Vector3(
      lerp(player.x, game.rexX, 0.55),
      lerp(player.y + 1.05, 2.55, 0.55),
      lerp(player.z, game.rexZ, 0.55),
    );
    camera.lookAt(focus);
    camera.fov = lerp(camera.fov, 54, weight);
    camera.updateProjectionMatrix();
  }

  function updateRexCamera() {
    // Counter-shot: sit ahead of the predator along its own heading so the
    // PiP always shows its face and jaws, never just its back.
    const forwardX = Math.sin(game.rexYaw);
    const forwardZ = Math.cos(game.rexYaw);
    const rightX = -forwardZ;
    const rightZ = forwardX;
    const sway = Math.sin(game.time * 1.1) * 0.18;
    rexCamera.position.set(
      game.rexX + forwardX * 7.4 + rightX * (2.5 + sway),
      2.75 + Math.sin(game.time * 0.9) * 0.12,
      game.rexZ + forwardZ * 7.4 + rightZ * (2.5 + sway),
    );
    rexCamera.lookAt(game.rexX + forwardX * 1.4, 3.05, game.rexZ + forwardZ * 1.4);
    const rect = hud.getRexCamRect();
    if (rect && rect.visible && rect.height > 8) {
      const aspect = rect.width / rect.height;
      if (Math.abs(rexCamera.aspect - aspect) > 0.01) {
        rexCamera.aspect = aspect;
        rexCamera.updateProjectionMatrix();
      }
    }
  }

  /* ------------------------------------------------------------------ */
  /* Render                                                              */
  /* ------------------------------------------------------------------ */

  function renderFrame() {
    const width = Math.max(320, window.innerWidth);
    const height = Math.max(240, window.innerHeight);
    renderer.setScissorTest(false);
    renderer.setViewport(0, 0, width, height);
    renderer.clear(true, true, true);
    renderer.render(scene, camera);

    const rect = hud.getRexCamRect();
    if (rect && rect.visible && rect.width > 12 && rect.height > 8) {
      const x = clamp(rect.x, 0, width);
      const y = clamp(height - rect.y - rect.height, 0, height);
      const w = Math.min(rect.width, width - x);
      const h = Math.min(rect.height, height - y);
      if (w > 4 && h > 4) {
        renderer.setScissorTest(true);
        renderer.setViewport(x, y, w, h);
        renderer.setScissor(x, y, w, h);
        renderer.clearDepth();
        renderer.render(scene, rexCamera);
        renderer.setScissorTest(false);
        renderer.setViewport(0, 0, width, height);
        renderer.setScissor(0, 0, width, height);
      }
    }
  }

  /* ------------------------------------------------------------------ */
  /* Frame                                                               */
  /* ------------------------------------------------------------------ */

  function updateMenu(dt) {
    player.z = 0;
    player.x = damp(player.x, 0, 3, dt);
    player.y = 0;
    player.sliding = false;
    world.setBiome(0);
    updatePlayerVisual(dt, {});
    updateRex(dt, "menu");
    updateEntities(dt);
    updateAmbientParticles(dt);
    updateCamera(dt);
  }

  function updatePaused() {
    // Keep the last frame's scene state; only the HUD overlay changes.
  }

  function updateCaught(dt) {
    game.caughtTimer += dt;
    player.stumble = Math.max(0, player.stumble - dt);
    updateHud();
    updatePlayerVisual(dt, {});
    updateRex(dt, "caught");
    updateEntities(dt);
    updateCamera(dt);
    updateAmbientParticles(dt);
    if (game.caughtTimer > 0.38 && !game.chomped) {
      game.chomped = true;
      playSfx("chomp");
      popParticles(game.rexX, 2.3, game.rexZ + 2.2, 24, dangerSparkColor, 5, sparks);
      game.shake = 1;
    }
    if (game.caughtTimer > 1.8) {
      game.chomped = false;
      finishRun();
    }
  }

  function updateGameOver(dt) {
    updatePlayerVisual(dt, {});
    updateRex(dt, "gameover");
    updateEntities(dt);
    updateCamera(dt);
    updateAmbientParticles(dt);
  }

  function update(dt) {
    if (game.mode === "paused") {
      updatePaused(dt);
      return;
    }
    game.time += dt;
    if (game.mode === "running") {
      updateRunning(dt);
    } else if (game.mode === "menu") {
      updateMenu(dt);
    } else if (game.mode === "caught") {
      updateCaught(dt);
    } else if (game.mode === "gameover") {
      updateGameOver(dt);
    }
    if (dust) {
      dust.update(dt);
    }
    if (sparks) {
      sparks.update(dt);
    }
    if (world) {
      world.update(dt, {
        playerX: player.x,
        playerZ: player.z,
        time: game.time,
        camera,
        speed: game.mode === "running" ? runState.current.speed : 0,
      });
    }
    updateRexCamera();
    game.frameCount += 1;
    if (game.frameCount % 20 === 0) {
      hud.measureRexCam();
    }
  }

  let previousTime = performance.now();
  let raf = 0;

  function frame(now) {
    raf = requestAnimationFrame(frame);
    let dt = (now - previousTime) / 1000;
    previousTime = now;
    if (!Number.isFinite(dt) || dt <= 0) {
      return;
    }
    dt = Math.min(dt, 0.05);
    if (document.hidden) {
      return;
    }
    input.update(dt);
    update(dt);
    renderFrame();
  }

  /* ------------------------------------------------------------------ */
  /* Actions                                                             */
  /* ------------------------------------------------------------------ */

  function toggleSound() {
    profile.settings.sound = !profile.settings.sound;
    hud.setSoundState(profile.settings.sound);
    audio.setSettings(profile.settings);
    if (profile.settings.sound) {
      void unlockAudio();
      audio.setMode(game.mode === "running" ? "running" : game.mode === "paused" ? "paused" : game.mode === "menu" ? "menu" : "caught");
      playSfx("uiClick");
    }
    scheduleSave();
  }

  function toggleMusic() {
    profile.settings.music = !profile.settings.music;
    hud.setMusicState(profile.settings.music);
    audio.setSettings(profile.settings);
    if (profile.settings.music) {
      void unlockAudio();
    }
    scheduleSave();
  }

  function toggleShake() {
    profile.settings.shake = !profile.settings.shake;
    hud.setShakeState(profile.settings.shake);
    scheduleSave();
  }

  function setQuality(setting) {
    profile.settings.quality = setting;
    hud.setQualityState(setting);
    applyQuality(setting);
    scheduleSave();
    playSfx("uiClick");
  }

  function setVolume(kind, value) {
    if (kind === "sfx") {
      profile.settings.sfxVolume = clamp01(value);
    } else {
      profile.settings.musicVolume = clamp01(value);
    }
    hud.setVolumes(profile.settings.sfxVolume, profile.settings.musicVolume);
    audio.setSettings(profile.settings);
    scheduleSave();
  }

  function openSettings() {
    if (game.mode === "running") {
      pauseRun();
    }
    void unlockAudio();
    hud.openSettings();
    playSfx("uiClick");
  }

  function handleAction(action, payload) {
    if (game.mode === "boot") {
      return;
    }
    switch (action) {
      case "start":
        startRun();
        break;
      case "pause":
        if (game.mode === "running") {
          pauseRun();
        } else if (game.mode === "paused") {
          resumeRun();
        }
        break;
      case "resume":
        resumeRun();
        break;
      case "retry":
        startRun();
        break;
      case "restart":
        if (game.mode !== "caught") {
          startRun();
        }
        break;
      case "menu":
        goToMenu();
        break;
      case "open-settings":
        openSettings();
        break;
      case "close-settings":
        hud.closeSettings();
        playSfx("uiBack");
        break;
      case "toggle-sound":
        void unlockAudio();
        toggleSound();
        break;
      case "toggle-music":
        toggleMusic();
        break;
      case "toggle-shake":
        toggleShake();
        break;
      case "quality":
        if (payload === QUALITY.auto || payload === QUALITY.high || payload === QUALITY.low) {
          setQuality(payload);
        }
        break;
      case "sfx-volume":
        setVolume("sfx", payload);
        break;
      case "music-volume":
        setVolume("music", payload);
        break;
      case "reload":
        window.location.reload();
        break;
      default:
        break;
    }
  }

  function handleGlobalKeys(event) {
    if (event.defaultPrevented || event.repeat) {
      return;
    }
    const target = event.target;
    if (target instanceof HTMLElement) {
      const tag = target.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable) {
        return;
      }
    }
    if (hud.isSettingsOpen()) {
      return;
    }
    if (game.mode === "menu") {
      if (target instanceof HTMLButtonElement) {
        return;
      }
      if (event.code === "Space" || event.code === "Enter") {
        event.preventDefault();
        startRun();
      }
      return;
    }
    if (game.mode === "gameover" || game.mode === "paused") {
      if (target instanceof HTMLButtonElement) {
        return;
      }
      if (event.code === "KeyR" || (game.mode === "gameover" && event.code === "Enter")) {
        event.preventDefault();
        startRun();
      }
    }
  }

  /* ------------------------------------------------------------------ */
  /* Bootstrap                                                           */
  /* ------------------------------------------------------------------ */

  try {
    initStage();
    createAudio();
    spawner = spawner ?? createSpawner();
    resetRun();
    game.mode = "menu";
    hud.showScreen("start");
    hud.setHudVisible(false);
    hud.syncProfile(profile);

    input = createInput({
      canvas,
      callbacks: {
        onPause() {
          if (hud.isSettingsOpen()) {
            return;
          }
          if (game.mode === "running") {
            pauseRun();
          } else if (game.mode === "paused") {
            resumeRun();
          }
        },
        onMute() {
          void unlockAudio();
          toggleSound();
        },
        onConfirm() {
          if (game.mode === "paused") {
            resumeRun();
          } else if (game.mode === "gameover") {
            startRun();
          }
        },
        onRestart() {
          if (game.mode === "paused" || game.mode === "gameover") {
            startRun();
          }
        },
        onGamepadConnected() {
          hud.toast("게임패드가 연결됐어요", { tone: "info", icon: "◉" });
          playSfx("uiClick");
        },
      },
      buttons: hud.touchButtons,
    });
    input.setEnabled(false);

    hud.bindActions(handleAction);
    window.addEventListener("resize", resize, { passive: true });
    window.addEventListener("orientationchange", () => {
      window.setTimeout(resize, 180);
    });
    window.addEventListener("keydown", handleGlobalKeys);
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) {
        audio?.suspend();
        if (game.mode === "running") {
          pauseRun();
        }
      } else {
        audio?.resume();
        previousTime = performance.now();
      }
    });
    window.addEventListener("pagehide", () => {
      saveProfile(profile);
      audio?.dispose();
    });
    canvas.addEventListener("webglcontextlost", (event) => {
      event.preventDefault();
      cancelAnimationFrame(raf);
      hud.showError("3D 그래픽이 중단됐어요. 다시 시도해 주세요.");
      audio?.dispose();
    });

    if (new URLSearchParams(window.location.search).has("debug")) {
      window.__dinoEscape = {
        THREE,
        scene,
        renderer,
        game,
        view,
        run: runState,
        player,
        hazards,
        ambers,
        pickups,
        rex,
        rexCamera,
        camera,
        world,
        entities,
        spawner,
        hud,
        step(seconds = 1, dt = 1 / 60, render = true) {
          const frames = Math.max(1, Math.round(seconds / dt));
          for (let i = 0; i < frames; i += 1) {
            update(dt);
          }
          if (render) {
            renderFrame();
          }
          return { distance: runState.current.distance, mode: game.mode, gap: runState.current.gap };
        },
        warp(meters) {
          const run = runState.current;
          run.distance = Math.max(0, meters);
          run.biomeIndex = getBiomeIndex(run.distance);
          run.milestone = Math.ceil(run.distance / RUN.milestoneStep) * RUN.milestoneStep;
          player.z = run.distance;
          world.setBiome(run.biomeIndex);
          for (const list of [hazards, ambers, pickups]) {
            for (const item of list) {
              entities.remove(item);
            }
            list.length = 0;
          }
          entities.clear();
          spawner.reset(run.distance);
          spawnAhead();
          updateHud();
          renderFrame();
        },
        startRun,
        pauseRun,
        resumeRun,
        finishRun,
        beginCaught,
      };
    }

    // First render, then reveal the menu.
    requestAnimationFrame(() => {
      renderFrame();
      hud.hideBoot();
      hud.showScreen("start");
      console.info(`Dino Escape v${GAME_VERSION} ready`);
    });
    raf = requestAnimationFrame(frame);
  } catch (error) {
    console.error("Dino Escape failed to start", error);
    hud.showError(
      "3D 화면을 열 수 없어요. 브라우저가 WebGL을 지원하는지 확인한 뒤 다시 시도해 주세요.",
    );
    audio?.dispose();
  }
}

boot();
