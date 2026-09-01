const root = window.OceanRescue = window.OceanRescue || {};
const baseTravelScene = root.TravelScene;
const RenderRuntime = root.RenderRuntime;

if (!baseTravelScene) {
  throw new Error("OceanRescue.TravelScene must be registered before actor presentation");
}
if (!RenderRuntime) {
  throw new Error("OceanRescue.RenderRuntime must be registered before actor presentation");
}

const BASE_GUP_X = 260;
const BASE_GUP_SCALE = 1.1;
const MAX_PITCH = 0.16;
const ACTOR_MODE = "sprite-actor-canonical-atlas-v1";

let hullSprite = null;
let propulsionSprite = null;
let legacyHullSprite = null;
let mounted = false;
let active = false;
let paused = false;
let frameId = null;
let lastFrameTime = null;
let latestTravelSnapshot = null;
let latestTerrainSnapshot = null;
let lastTravelY = null;
let lastSyncTime = null;
let verticalVelocity = 0;
let visualPitch = 0;
let reducedMotion = false;

function getRootElement() {
  return document.getElementById("ocean-rescue-root");
}

function setDiagnostic(name, value) {
  const element = getRootElement();
  if (element) {
    element.setAttribute(name, String(value));
  }
}

function getContainer(name) {
  return RenderRuntime.getContainer(name);
}

function findChildByLabel(container, label) {
  if (!container || !container.children) {
    return null;
  }
  for (const child of container.children) {
    if (child && child.label === label) {
      return child;
    }
  }
  return null;
}

function applyTrimAnchor(sprite, texture) {
  const trim = texture && texture.trim;
  const orig = texture && texture.orig;
  if (!orig || !Number.isFinite(orig.width) || !Number.isFinite(orig.height) || orig.width <= 0 || orig.height <= 0) {
    sprite.anchor.set(0.5, 0.5);
    return;
  }
  if (trim && Number.isFinite(trim.x) && Number.isFinite(trim.y) && Number.isFinite(trim.width) && Number.isFinite(trim.height)) {
    sprite.anchor.set(
      (trim.x + trim.width / 2) / orig.width,
      (trim.y + trim.height / 2) / orig.height
    );
  } else {
    sprite.anchor.set(0.5, 0.5);
  }
}

function setReducedMotion() {
  reducedMotion = Boolean(
    window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

function installActor() {
  const submarineContainer = getContainer("submarine");
  if (!submarineContainer) {
    throw new Error("Canonical submarine container is unavailable");
  }

  if (hullSprite && propulsionSprite) {
    hullSprite.visible = true;
    propulsionSprite.visible = true;
    if (legacyHullSprite) {
      legacyHullSprite.visible = false;
    }
    return;
  }

  const hullTexture = RenderRuntime.getTexture("scene.submarine");
  const propulsionTexture = RenderRuntime.getTexture("fx.bubbles");
  if (!hullTexture || !propulsionTexture) {
    throw new Error("Canonical travel actor textures are unavailable");
  }

  legacyHullSprite = findChildByLabel(submarineContainer, "travel-submarine");
  if (legacyHullSprite) {
    legacyHullSprite.label = "travel-submarine-legacy-hidden";
    legacyHullSprite.name = "travel-submarine-legacy-hidden";
    legacyHullSprite.visible = false;
  }

  propulsionSprite = new PIXI.Sprite(propulsionTexture);
  propulsionSprite.label = "travel-gup-propulsion";
  propulsionSprite.name = "travel-gup-propulsion";
  propulsionSprite.eventMode = "none";
  applyTrimAnchor(propulsionSprite, propulsionTexture);
  propulsionSprite.position.set(BASE_GUP_X - 92, 364);
  propulsionSprite.scale.set(0.32, 0.24);
  propulsionSprite.alpha = 0.38;
  submarineContainer.addChild(propulsionSprite);

  hullSprite = new PIXI.Sprite(hullTexture);
  hullSprite.label = "travel-submarine";
  hullSprite.name = "travel-submarine";
  hullSprite.eventMode = "none";
  applyTrimAnchor(hullSprite, hullTexture);
  hullSprite.position.set(BASE_GUP_X, 360);
  hullSprite.scale.set(BASE_GUP_SCALE, BASE_GUP_SCALE);
  submarineContainer.addChild(hullSprite);

  setDiagnostic("data-travel-scene-gup-actor-mode", ACTOR_MODE);
  setDiagnostic("data-travel-scene-gup-actor-hull", "sprite");
  setDiagnostic("data-travel-scene-gup-actor-propulsion", "sprite");
}

function removeActor() {
  for (const sprite of [hullSprite, propulsionSprite]) {
    if (sprite && sprite.parent && typeof sprite.parent.removeChild === "function") {
      sprite.parent.removeChild(sprite);
    }
  }
  hullSprite = null;
  propulsionSprite = null;
  legacyHullSprite = null;
}

function updateSyncVelocity(travelSnapshot) {
  if (!travelSnapshot || !Number.isFinite(travelSnapshot.y)) {
    return;
  }
  const now = performance.now();
  if (lastTravelY !== null && lastSyncTime !== null) {
    const deltaMs = Math.max(1, now - lastSyncTime);
    const instantaneous = (travelSnapshot.y - lastTravelY) / deltaMs;
    verticalVelocity += (instantaneous - verticalVelocity) * 0.45;
  }
  lastTravelY = travelSnapshot.y;
  lastSyncTime = now;
}

function collisionOffset(terrainSnapshot, timeMs) {
  if (!terrainSnapshot || !terrainSnapshot.collisionActive) {
    return { x: 0, y: 0, wobble: 0 };
  }
  const knockback = Number.isFinite(terrainSnapshot.knockbackOffsetX)
    ? terrainSnapshot.knockbackOffsetX
    : 0;
  const shake = Number.isFinite(terrainSnapshot.shakeOffsetY)
    ? terrainSnapshot.shakeOffsetY
    : 0;
  const wobble = reducedMotion ? 0 : Math.sin(timeMs / 75) * 0.055;
  return { x: -knockback, y: reducedMotion ? 0 : shake, wobble };
}

function syncParallax(travelSnapshot) {
  const distance = travelSnapshot && Number.isFinite(travelSnapshot.distance)
    ? travelSnapshot.distance
    : 0;
  const far = getContainer("farBackground");
  const mid = getContainer("midground");
  const foreground = getContainer("foreground");
  const phase = distance / 180;
  if (far) {
    far.position.x = reducedMotion ? 0 : Math.sin(phase * 0.55) * 5;
  }
  if (mid) {
    mid.position.x = reducedMotion ? 0 : Math.sin(phase * 0.82) * 14;
  }
  if (foreground) {
    foreground.position.x = reducedMotion ? 0 : Math.sin(phase * 1.15) * 28;
  }
  setDiagnostic("data-travel-scene-parallax-layers", "3");
}

function resetParallax() {
  for (const name of ["farBackground", "midground", "foreground"]) {
    const container = getContainer(name);
    if (container) {
      container.position.x = 0;
    }
  }
}

function syncActor(timeMs, deltaMs) {
  if (!hullSprite || !propulsionSprite) {
    return;
  }
  const travelSnapshot = latestTravelSnapshot || { y: 360, distance: 0 };
  const terrainSnapshot = latestTerrainSnapshot || null;
  const y = Number.isFinite(travelSnapshot.y) ? travelSnapshot.y : 360;
  const steering = Boolean(
    travelSnapshot.dragging ||
    travelSnapshot.tapTargetY !== null ||
    Math.abs(verticalVelocity) > 0.015
  );

  const targetPitch = reducedMotion
    ? 0
    : Math.max(-MAX_PITCH, Math.min(MAX_PITCH, verticalVelocity * 6.5));
  visualPitch += (targetPitch - visualPitch) * Math.min(1, deltaMs / 90);

  const collision = collisionOffset(terrainSnapshot, timeMs);
  const hover = reducedMotion ? 0 : Math.sin(timeMs / 880) * 4;
  const x = BASE_GUP_X + collision.x;
  const actorY = y + hover + collision.y;
  const rotation = visualPitch + collision.wobble;

  hullSprite.position.set(x, actorY);
  hullSprite.rotation = rotation;

  const steeringEnergy = Math.min(1, Math.abs(verticalVelocity) * 18);
  const stretch = reducedMotion ? 0 : steeringEnergy * 0.025;
  hullSprite.scale.set(
    BASE_GUP_SCALE * (1 + stretch),
    BASE_GUP_SCALE * (1 - stretch)
  );
  hullSprite.tint = terrainSnapshot && terrainSnapshot.collisionActive ? 0xfff0dc : 0xffffff;

  const localX = -92;
  const localY = 4;
  const cos = Math.cos(rotation);
  const sin = Math.sin(rotation);
  propulsionSprite.position.set(
    x + localX * cos - localY * sin,
    actorY + localX * sin + localY * cos
  );
  propulsionSprite.rotation = rotation;

  const pulse = reducedMotion ? 1 : 1 + Math.sin(timeMs / 95) * 0.08;
  const propulsionScaleX = (steering ? 0.42 : 0.32) * pulse + steeringEnergy * 0.06;
  const propulsionScaleY = (steering ? 0.30 : 0.24) * pulse;
  propulsionSprite.scale.set(propulsionScaleX, propulsionScaleY);
  propulsionSprite.alpha = terrainSnapshot && terrainSnapshot.collisionActive
    ? 0.22
    : steering
      ? 0.72
      : 0.42;

  setDiagnostic(
    "data-travel-scene-gup-actor-state",
    terrainSnapshot && terrainSnapshot.collisionActive
      ? "collision-recovery"
      : steering
        ? "steering"
        : "cruise-hover"
  );
  setDiagnostic("data-travel-scene-gup-actor-pitch", visualPitch.toFixed(4));
  setDiagnostic("data-travel-scene-gup-propulsion-visible", String(propulsionSprite.visible));
  syncParallax(travelSnapshot);
}

function requestActorFrame() {
  if (!active || paused || frameId !== null || typeof window.requestAnimationFrame !== "function") {
    return;
  }
  frameId = window.requestAnimationFrame(actorFrame);
}

function actorFrame(timestamp) {
  frameId = null;
  if (!active || paused || !mounted) {
    return;
  }
  const deltaMs = lastFrameTime === null ? 16 : Math.max(0, Math.min(50, timestamp - lastFrameTime));
  lastFrameTime = timestamp;
  if (legacyHullSprite) {
    legacyHullSprite.visible = false;
  }
  syncActor(timestamp, deltaMs);
  requestActorFrame();
}

function cancelActorFrame() {
  if (frameId !== null && typeof window.cancelAnimationFrame === "function") {
    window.cancelAnimationFrame(frameId);
  }
  frameId = null;
  lastFrameTime = null;
}

function prepare() {
  const result = baseTravelScene.prepare();
  setReducedMotion();
  installActor();
  mounted = true;
  active = false;
  paused = false;
  latestTravelSnapshot = root.Travel ? root.Travel.getSnapshot() : null;
  latestTerrainSnapshot = root.Terrain ? root.Terrain.getSnapshot() : null;
  lastTravelY = latestTravelSnapshot && Number.isFinite(latestTravelSnapshot.y)
    ? latestTravelSnapshot.y
    : null;
  lastSyncTime = performance.now();
  verticalVelocity = 0;
  visualPitch = 0;
  syncActor(performance.now(), 16);
  return result;
}

function activate() {
  const result = baseTravelScene.activate();
  active = true;
  paused = false;
  lastFrameTime = null;
  requestActorFrame();
  return result;
}

function sync(travelSnapshot, terrainSnapshot) {
  latestTravelSnapshot = travelSnapshot || latestTravelSnapshot;
  latestTerrainSnapshot = terrainSnapshot || null;
  updateSyncVelocity(latestTravelSnapshot);
  const result = baseTravelScene.sync(travelSnapshot, terrainSnapshot);
  if (legacyHullSprite) {
    legacyHullSprite.visible = false;
  }
  syncActor(performance.now(), 16);
  return result;
}

function pause() {
  paused = true;
  cancelActorFrame();
  return baseTravelScene.pause();
}

function resume() {
  const result = baseTravelScene.resume();
  paused = false;
  if (active) {
    requestActorFrame();
  }
  return result;
}

function exit() {
  cancelActorFrame();
  active = false;
  paused = false;
  mounted = false;
  resetParallax();
  if (hullSprite) {
    hullSprite.visible = false;
  }
  if (propulsionSprite) {
    propulsionSprite.visible = false;
  }
  return baseTravelScene.exit();
}

function destroy() {
  cancelActorFrame();
  resetParallax();
  removeActor();
  mounted = false;
  active = false;
  paused = false;
  latestTravelSnapshot = null;
  latestTerrainSnapshot = null;
  lastTravelY = null;
  lastSyncTime = null;
  verticalVelocity = 0;
  visualPitch = 0;
  return baseTravelScene.destroy();
}

function getDiagnostics() {
  const base = baseTravelScene.getDiagnostics();
  return Object.freeze({
    ...base,
    actorMode: ACTOR_MODE,
    actorMounted: Boolean(hullSprite),
    actorState: getRootElement()?.getAttribute("data-travel-scene-gup-actor-state") || "",
    parallaxLayers: 3
  });
}

root.TravelScene = Object.freeze({
  prepare,
  activate,
  sync,
  pause,
  resume,
  exit,
  destroy,
  isMounted: () => baseTravelScene.isMounted(),
  getDiagnostics,
  REQUIRED_ALIASES: baseTravelScene.REQUIRED_ALIASES
});
