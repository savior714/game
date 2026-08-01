(function () {
  "use strict";

  var root = window.OceanRescue = window.OceanRescue || {};
  var RenderRuntime = root.RenderRuntime || null;
  var Terrain = root.Terrain || null;
  var Gups = root.Gups || null;

  var REQUIRED_ALIASES = [
    "scene.water.far",
    "scene.reef.mid",
    "scene.coral.foreground",
    "scene.submarine",
    "scene.seaweed-loop.01",
    "scene.sand-path",
    "scene.passage",
    "fx.bubbles",
    "fx.caustic"
  ];

  var ENVIRONMENT_PALETTES = {
    "coral-reef": 0x7fb2c4,
    "sandy-reef": 0xc4a37f,
    "rocky-canyon": 0x6b7a8a
  };

  var WIDTH = 1280;
  var HEIGHT = 720;
  var MAX_DELTA_MS = 50;
  var mounted = false;
  var active = false;
  var paused = false;
  var animationFrameId = null;
  var lastTimestamp = null;
  var activeTime = 0;
  var animationRunning = false;
  var reducedMotion = false;
  var nodes = null;
  var snapshot = null;
  var terrainSnapshot = null;
  var missingAliases = [];
  var collisionEffectStart = 0;
  var lastCollisionId = null;

  function getRoot() {
    return document.getElementById("ocean-rescue-root");
  }

  function setDiagnostic(name, value) {
    var element = getRoot();
    if (element) {
      element.setAttribute(name, String(value));
    }
  }

  function setSceneDiagnostics(status) {
    setDiagnostic("data-travel-scene", status);
    setDiagnostic("data-travel-scene-node-count", nodes ? nodeCount() : 0);
    setDiagnostic(
      "data-travel-scene-environment",
      terrainSnapshot && terrainSnapshot.active && Terrain
        ? Terrain.getLayout(terrainSnapshot.missionId)
          ? Terrain.getLayout(terrainSnapshot.missionId).environment
          : ""
        : ""
    );
    setDiagnostic(
      "data-travel-scene-obstacle-count",
      terrainSnapshot && terrainSnapshot.active && Terrain
        ? (Terrain.getLayout(terrainSnapshot.missionId) || {}).obstacles
          ? Terrain.getLayout(terrainSnapshot.missionId).obstacles.length
          : 0
        : 0
    );
    setDiagnostic(
      "data-travel-scene-animation",
      paused && mounted ? "paused" : animationRunning ? "running" : "stopped"
    );
    setDiagnostic(
      "data-travel-scene-legacy-visible",
      RenderRuntime && typeof RenderRuntime.getLegacyBridgeVisible === "function"
        ? RenderRuntime.getLegacyBridgeVisible()
        : true
    );
    setDiagnostic(
      "data-travel-scene-gup-id",
      gupsSnapshot && gupsSnapshot.lastGupId ? gupsSnapshot.lastGupId : ""
    );
  }

  var gupsSnapshot = null;

  function nodeCount() {
    if (!nodes) {
      return 0;
    }
    var count = 0;
    var keys = Object.keys(nodes);
    for (var i = 0; i < keys.length; i += 1) {
      var value = nodes[keys[i]];
      if (Array.isArray(value)) {
        count += value.length;
      } else if (value) {
        count += 1;
      }
    }
    return count;
  }

  function makeSprite(alias, label) {
    var texture = RenderRuntime.getTexture(alias);
    if (!texture) {
      throw new Error("Missing authored texture: " + alias);
    }

    var sprite = new PIXI.Sprite(texture);
    sprite.label = label;
    sprite.name = label;
    sprite.eventMode = "none";
    if (texture.defaultAnchor && sprite.anchor) {
      sprite.anchor.copyFrom(texture.defaultAnchor);
    }
    return sprite;
  }

  function setPosition(displayObject, x, y) {
    displayObject.position.set(x, y);
  }

  function setScale(displayObject, x, y) {
    displayObject.scale.set(x, typeof y === "number" ? y : x);
  }

  function addChild(container, child) {
    if (!container || typeof container.addChild !== "function") {
      throw new Error("Missing canonical scene container");
    }
    container.addChild(child);
  }

  function createSceneGraph() {
    if (nodes) {
      return;
    }
    var far = RenderRuntime.getContainer("farBackground");
    var mid = RenderRuntime.getContainer("midground");
    var gameplayWorld = RenderRuntime.getContainer("gameplayWorld");
    var submarine = RenderRuntime.getContainer("submarine");
    var foreground = RenderRuntime.getContainer("foreground");
    var effects = RenderRuntime.getContainer("effects");
    if (!far || !mid || !gameplayWorld || !submarine || !foreground || !effects) {
      throw new Error("Missing canonical authored scene container");
    }

    nodes = {
      waterFar: makeSprite("scene.water.far", "travel-water-far"),
      reefMid: makeSprite("scene.reef.mid", "travel-reef-mid"),
      coralForeground: makeSprite("scene.coral.foreground", "travel-coral-fg"),
      sandPath: makeSprite("scene.sand-path", "travel-sand-path"),
      passage: makeSprite("scene.passage", "travel-passage"),
      submarine: makeSprite("scene.submarine", "travel-submarine"),
      seaweedLoops: [],
      bubbles: makeSprite("fx.bubbles", "travel-bubbles"),
      caustic: makeSprite("fx.caustic", "travel-caustic"),
      collisionFlash: null,
      obstacleSprites: []
    };

    for (var i = 0; i < 4; i += 1) {
      nodes.seaweedLoops.push(
        makeSprite("scene.seaweed-loop.01", "travel-seaweed-" + (i + 1))
      );
    }

    var flashTexture = RenderRuntime.getTexture("fx.bubbles");
    if (flashTexture) {
      nodes.collisionFlash = new PIXI.Sprite(flashTexture);
      nodes.collisionFlash.label = "travel-collision-flash";
      nodes.collisionFlash.name = "travel-collision-flash";
      nodes.collisionFlash.eventMode = "none";
      nodes.collisionFlash.visible = false;
    }

    addChild(far, nodes.waterFar);
    addChild(mid, nodes.reefMid);
    addChild(mid, nodes.passage);
    addChild(mid, nodes.caustic);
    gameplayWorld.addChildAt(nodes.sandPath, 0);
    addChild(submarine, nodes.submarine);
    for (var loopIndex = 0; loopIndex < nodes.seaweedLoops.length; loopIndex += 1) {
      addChild(gameplayWorld, nodes.seaweedLoops[loopIndex]);
    }
    addChild(foreground, nodes.coralForeground);
    addChild(effects, nodes.bubbles);
    if (nodes.collisionFlash) {
      addChild(effects, nodes.collisionFlash);
    }

    layoutStaticNodes();
  }

  function layoutStaticNodes() {
    setPosition(nodes.waterFar, WIDTH / 2, HEIGHT / 2);
    setScale(nodes.waterFar, 3.2, 2.4);
    nodes.waterFar.alpha = 1;

    setPosition(nodes.reefMid, WIDTH / 2, 480);
    setScale(nodes.reefMid, 1.5, 0.9);
    nodes.reefMid.alpha = 0.55;

    setPosition(nodes.passage, 1100, 350);
    setScale(nodes.passage, 0.8, 0.8);
    nodes.passage.alpha = 0.9;

    setPosition(nodes.caustic, WIDTH / 2, 280);
    setScale(nodes.caustic, 1.8, 1.4);
    nodes.caustic.alpha = 0.35;

    setPosition(nodes.sandPath, WIDTH / 2, HEIGHT);
    setScale(nodes.sandPath, 1.05, 1.05);
    nodes.sandPath.alpha = 1;

    setPosition(nodes.coralForeground, WIDTH / 2, HEIGHT + 40);
    setScale(nodes.coralForeground, 1, 1);
    nodes.coralForeground.alpha = 0.88;

    setPosition(nodes.submarine, 260, 360);
    setScale(nodes.submarine, 1.1, 1.1);

    setPosition(nodes.bubbles, 200, 340);
    setScale(nodes.bubbles, 0.7, 0.7);
    nodes.bubbles.alpha = 0.7;

    for (var i = 0; i < nodes.seaweedLoops.length; i += 1) {
      var loop = nodes.seaweedLoops[i];
      var baseX = 140 + i * 280;
      var baseY = HEIGHT - 60 - (i % 2) * 30;
      setPosition(loop, baseX, baseY);
      setScale(loop, 0.55, 0.55);
      loop.alpha = 0.65;
    }

    if (nodes.collisionFlash) {
      nodes.collisionFlash.visible = false;
      nodes.collisionFlash.alpha = 0;
    }
  }

  function setReducedMotion() {
    reducedMotion = false;
    if (window.matchMedia) {
      reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }
  }

  function showOwnedNodes() {
    if (!nodes) {
      return;
    }
    var keys = Object.keys(nodes);
    for (var i = 0; i < keys.length; i += 1) {
      var value = nodes[keys[i]];
      if (Array.isArray(value)) {
        for (var j = 0; j < value.length; j += 1) {
          value[j].visible = true;
        }
      } else if (value) {
        value.visible = true;
      }
    }
  }

  function finite(value) {
    return typeof value === "number" && isFinite(value);
  }

  function syncBackground() {
    if (!nodes) {
      return;
    }
    var hover = reducedMotion ? 0 : Math.sin(activeTime / 1200) * 3;
    setPosition(nodes.waterFar, WIDTH / 2 + hover * 0.5, HEIGHT / 2);

    var causticDrift = reducedMotion ? 0 : activeTime / 2;
    nodes.caustic.alpha = 0.3 + Math.sin(causticDrift / 600) * 0.1;
    nodes.caustic.position.x = WIDTH / 2 + Math.sin(activeTime / 2600) * 18;
    nodes.caustic.position.y = 280 + Math.cos(activeTime / 3100) * 6;

    var reefSway = reducedMotion ? 0 : Math.sin(activeTime / 1800) * 4;
    setPosition(nodes.reefMid, WIDTH / 2 + reefSway, 480);
  }

  function syncSeaweed() {
    if (!nodes) {
      return;
    }
    for (var i = 0; i < nodes.seaweedLoops.length; i += 1) {
      var loop = nodes.seaweedLoops[i];
      var phase = i * 1.3;
      var sway = reducedMotion ? 0 : Math.sin(activeTime / (800 + phase * 100) + phase) * 8;
      loop.position.x += sway * 0.3;
      loop.rotation = reducedMotion ? 0 : Math.sin(activeTime / (900 + phase * 80) + phase) * 0.06;
      var pulse = reducedMotion ? 1 : 1 + Math.sin(activeTime / 500 + phase) * 0.04;
      loop.scale.set(0.55 * pulse, 0.55 * pulse);
    }
  }

  function syncBubbles() {
    if (!nodes) {
      return;
    }
    var drift = reducedMotion ? 0 : activeTime / 4;
    var cycle = 200;
    var y = 340 - (drift % cycle);
    setPosition(nodes.bubbles, 200 + Math.sin(activeTime / 1800) * 12, y);
    nodes.bubbles.alpha = 0.65 + Math.sin(activeTime / 700) * 0.1;
    var scalePulse = reducedMotion ? 0.7 : 0.7 + Math.sin(activeTime / 600) * 0.05;
    nodes.bubbles.scale.set(scalePulse, scalePulse);
  }

  function syncSubmarine(travelY) {
    if (!nodes || !nodes.submarine) {
      return;
    }
    var hover = reducedMotion ? 0 : Math.sin(activeTime / 900) * 4;
    setPosition(nodes.submarine, 260, travelY + hover);
    nodes.submarine.rotation = reducedMotion ? 0 : Math.sin(activeTime / 1400) * 0.02;
  }

  function syncObstacles(terrainSnap) {
    if (!nodes || !Terrain || !terrainSnap || !terrainSnap.active) {
      return;
    }
    var layout = Terrain.getLayout(terrainSnap.missionId);
    if (!layout || !layout.obstacles) {
      return;
    }
    var env = layout.environment;
    var tint = ENVIRONMENT_PALETTES[env] || ENVIRONMENT_PALETTES["coral-reef"];

    while (nodes.obstacleSprites.length < layout.obstacles.length) {
      var obstacleSprite = new PIXI.Graphics();
      obstacleSprite.label = "travel-obstacle-" + nodes.obstacleSprites.length;
      obstacleSprite.name = obstacleSprite.label;
      obstacleSprite.eventMode = "none";
      obstacleSprite.visible = false;
      RenderRuntime.getContainer("gameplayWorld").addChild(obstacleSprite);
      nodes.obstacleSprites.push(obstacleSprite);
    }

    for (var i = 0; i < layout.obstacles.length; i += 1) {
      var obstacle = layout.obstacles[i];
      var sprite = nodes.obstacleSprites[i];
      var screenX = obstacle.worldX - terrainSnap.distance;
      if (screenX < -obstacle.width || screenX > WIDTH + obstacle.width) {
        sprite.visible = false;
        continue;
      }
      sprite.visible = true;
      sprite.clear();
      sprite.beginFill(tint, 0.85);
      sprite.drawRoundedRect(
        screenX - obstacle.width / 2,
        obstacle.y - obstacle.height / 2,
        obstacle.width,
        obstacle.height,
        12
      );
      sprite.endFill();
      sprite.beginFill(0x0a1e33, 0.4);
      sprite.drawRoundedRect(
        screenX - obstacle.width / 2 + 10,
        obstacle.y - obstacle.height / 2 + 10,
        obstacle.width - 20,
        obstacle.height - 20,
        8
      );
      sprite.endFill();
      sprite.x = 0;
      sprite.y = 0;
    }

    for (var j = layout.obstacles.length; j < nodes.obstacleSprites.length; j += 1) {
      nodes.obstacleSprites[j].visible = false;
    }
  }

  function syncCollisionFeedback(terrainSnap) {
    if (!nodes || !nodes.collisionFlash) {
      return;
    }
    var collisionActive = terrainSnap && terrainSnap.collisionActive;
    if (collisionActive && lastCollisionId !== terrainSnap.lastCollisionObstacleId) {
      collisionEffectStart = activeTime;
      lastCollisionId = terrainSnap.lastCollisionObstacleId;
    }
    if (collisionActive) {
      var elapsed = activeTime - collisionEffectStart;
      var progress = Math.min(1, elapsed / 400);
      nodes.collisionFlash.visible = true;
      nodes.collisionFlash.alpha = 1 - progress * 0.85;
      var flashScale = 0.6 + progress * 0.5;
      nodes.collisionFlash.scale.set(flashScale, flashScale);
      var gupY = snapshot ? snapshot.y : 360;
      setPosition(nodes.collisionFlash, 260, gupY + (terrainSnap.shakeOffsetY || 0));
    } else {
      nodes.collisionFlash.visible = false;
      lastCollisionId = null;
    }
  }

  function updateScene() {
    if (!nodes) {
      return;
    }
    var travelSnap = snapshot || { y: 360, distance: 0 };
    var terrainSnap = terrainSnapshot || { active: false };
    syncBackground();
    syncSeaweed();
    syncBubbles();
    syncSubmarine(travelSnap.y);
    syncObstacles(terrainSnap);
    syncCollisionFeedback(terrainSnap);
  }

  function render() {
    if (RenderRuntime && typeof RenderRuntime.renderSceneFrame === "function") {
      RenderRuntime.renderSceneFrame();
    }
  }

  function requestFrame() {
    if (!active || paused || animationFrameId !== null) {
      return;
    }
    if (typeof window.requestAnimationFrame !== "function") {
      animationRunning = false;
      setSceneDiagnostics("active");
      return;
    }
    animationRunning = true;
    animationFrameId = window.requestAnimationFrame(animationFrame);
  }

  function animationFrame(timestamp) {
    animationFrameId = null;
    if (!active || paused || !mounted) {
      return;
    }
    if (lastTimestamp !== null) {
      var delta = Math.max(0, Math.min(MAX_DELTA_MS, timestamp - lastTimestamp));
      activeTime += delta;
    }
    lastTimestamp = timestamp;
    updateScene();
    render();
    requestFrame();
  }

  function cancelFrame() {
    if (animationFrameId !== null && typeof window.cancelAnimationFrame === "function") {
      window.cancelAnimationFrame(animationFrameId);
    }
    animationFrameId = null;
    animationRunning = false;
    lastTimestamp = null;
  }

  function validateAliases() {
    missingAliases = [];
    for (var i = 0; i < REQUIRED_ALIASES.length; i += 1) {
      if (!RenderRuntime.hasTexture(REQUIRED_ALIASES[i])) {
        missingAliases.push(REQUIRED_ALIASES[i]);
      }
    }
    return missingAliases.length === 0;
  }

  function prepare() {
    if (!RenderRuntime || !RenderRuntime.isReady()) {
      setSceneDiagnostics("failed");
      throw new Error("Travel authored scene runtime is unavailable");
    }
    if (!validateAliases()) {
      setSceneDiagnostics("failed");
      throw new Error("Missing authored textures: " + missingAliases.join(", "));
    }
    setReducedMotion();
    createSceneGraph();
    showOwnedNodes();
    mounted = true;
    active = false;
    paused = false;
    snapshot = null;
    terrainSnapshot = null;
    gupsSnapshot = Gups ? Gups.getSnapshot() : null;
    RenderRuntime.setLegacyBridgeVisible(false);
    updateScene();
    render();
    setSceneDiagnostics("prepared");
    return true;
  }

  function activate() {
    if (!mounted) {
      throw new Error("Travel authored scene is not prepared");
    }
    if (active) {
      return true;
    }
    active = true;
    paused = false;
    lastTimestamp = null;
    updateScene();
    render();
    requestFrame();
    setSceneDiagnostics("active");
    return true;
  }

  function sync(travelSnap, terrainSnap) {
    if (!mounted || !travelSnap) {
      return false;
    }
    snapshot = travelSnap;
    terrainSnapshot = terrainSnap || null;
    gupsSnapshot = Gups ? Gups.getSnapshot() : gupsSnapshot;
    updateScene();
    render();
    setSceneDiagnostics(active ? "active" : "prepared");
    return true;
  }

  function pause() {
    if (!mounted) {
      return;
    }
    paused = true;
    cancelFrame();
    if (active) {
      setSceneDiagnostics("paused");
    }
  }

  function resume() {
    if (!mounted) {
      return;
    }
    paused = false;
    lastTimestamp = null;
    if (active) {
      requestFrame();
      setSceneDiagnostics("active");
    }
  }

  function hideOwnedNodes() {
    if (!nodes) {
      return;
    }
    var keys = Object.keys(nodes);
    for (var i = 0; i < keys.length; i += 1) {
      var value = nodes[keys[i]];
      if (Array.isArray(value)) {
        for (var j = 0; j < value.length; j += 1) {
          value[j].visible = false;
        }
      } else if (value) {
        value.visible = false;
      }
    }
  }

  function exit() {
    cancelFrame();
    active = false;
    paused = false;
    mounted = false;
    hideOwnedNodes();
    if (RenderRuntime) {
      RenderRuntime.setLegacyBridgeVisible(true);
    }
    setSceneDiagnostics("unmounted");
  }

  function removeOwnedChild(container, child) {
    if (container && child && typeof container.removeChild === "function") {
      container.removeChild(child);
    }
  }

  function destroy() {
    cancelFrame();
    if (nodes && RenderRuntime) {
      removeOwnedChild(RenderRuntime.getContainer("farBackground"), nodes.waterFar);
      removeOwnedChild(RenderRuntime.getContainer("midground"), nodes.reefMid);
      removeOwnedChild(RenderRuntime.getContainer("midground"), nodes.passage);
      removeOwnedChild(RenderRuntime.getContainer("midground"), nodes.caustic);
      removeOwnedChild(RenderRuntime.getContainer("gameplayWorld"), nodes.sandPath);
      removeOwnedChild(RenderRuntime.getContainer("submarine"), nodes.submarine);
      for (var i = 0; i < nodes.seaweedLoops.length; i += 1) {
        removeOwnedChild(RenderRuntime.getContainer("gameplayWorld"), nodes.seaweedLoops[i]);
      }
      removeOwnedChild(RenderRuntime.getContainer("foreground"), nodes.coralForeground);
      removeOwnedChild(RenderRuntime.getContainer("effects"), nodes.bubbles);
      if (nodes.collisionFlash) {
        removeOwnedChild(RenderRuntime.getContainer("effects"), nodes.collisionFlash);
      }
      for (var j = 0; j < nodes.obstacleSprites.length; j += 1) {
        removeOwnedChild(RenderRuntime.getContainer("gameplayWorld"), nodes.obstacleSprites[j]);
      }
    }
    nodes = null;
    mounted = false;
    active = false;
    paused = false;
    snapshot = null;
    terrainSnapshot = null;
    setSceneDiagnostics("unmounted");
  }

  function getDiagnostics() {
    return Object.freeze({
      mounted: mounted,
      active: active,
      paused: paused,
      nodeCount: nodeCount(),
      obstacleCount: terrainSnapshot && terrainSnapshot.active && Terrain
        ? (Terrain.getLayout(terrainSnapshot.missionId) || {}).obstacles
          ? Terrain.getLayout(terrainSnapshot.missionId).obstacles.length
          : 0
        : 0,
      environment: terrainSnapshot && terrainSnapshot.active && Terrain
        ? (Terrain.getLayout(terrainSnapshot.missionId) || {}).environment || ""
        : "",
      animationRunning: animationRunning,
      legacyBridgeVisible: RenderRuntime && typeof RenderRuntime.getLegacyBridgeVisible === "function"
        ? RenderRuntime.getLegacyBridgeVisible()
        : true,
      requiredAliasCount: REQUIRED_ALIASES.length,
      missingAliases: Object.freeze(missingAliases.slice()),
      selectedGupId: gupsSnapshot ? (gupsSnapshot.lastGupId || "") : ""
    });
  }

  root.TravelScene = Object.freeze({
    prepare: prepare,
    activate: activate,
    sync: sync,
    pause: pause,
    resume: resume,
    exit: exit,
    destroy: destroy,
    isMounted: function () { return mounted; },
    getDiagnostics: getDiagnostics,
    REQUIRED_ALIASES: Object.freeze(REQUIRED_ALIASES.slice())
  });
})();
