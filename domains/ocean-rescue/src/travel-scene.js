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
    "fx.caustic",
    "terrain.coral-column",
    "terrain.coral-rock",
    "terrain.reef-arch",
    "terrain.reef-spire",
    "terrain.kelp-rock",
    "terrain.sand-rock",
    "terrain.shell-ledge",
    "terrain.low-reef",
    "terrain.rock-stack",
    "terrain.sand-pillar",
    "terrain.canyon-wall",
    "terrain.canyon-ledge",
    "terrain.canyon-pillar",
    "terrain.boulder-stack",
    "terrain.rock-spire"
  ];

  var OBSTACLE_KIND_ALIASES = {
    "coral-column": "terrain.coral-column",
    "reef-arch": "terrain.reef-arch",
    "coral-rock": "terrain.coral-rock",
    "kelp-rock": "terrain.kelp-rock",
    "reef-spire": "terrain.reef-spire",
    "sand-rock": "terrain.sand-rock",
    "shell-ledge": "terrain.shell-ledge",
    "low-reef": "terrain.low-reef",
    "rock-stack": "terrain.rock-stack",
    "sand-pillar": "terrain.sand-pillar",
    "canyon-wall": "terrain.canyon-wall",
    "rock-spire": "terrain.rock-spire",
    "canyon-ledge": "terrain.canyon-ledge",
    "boulder-stack": "terrain.boulder-stack",
    "canyon-pillar": "terrain.canyon-pillar"
  };

  var ENVIRONMENT_PALETTES = {
    "coral-reef": 0x7fb2c4,
    "sandy-reef": 0xc4a37f,
    "rocky-canyon": 0x6b7a8a
  };

  var OBSTACLE_OUTER_TINT = 0x04151F;
  var OBSTACLE_RIM_TINT = 0xFFF7D6;
  var OBSTACLE_BODY_TINT = 0xFFFFFF;
  var OBSTACLE_RIM_SCALE = 1.065;
  var OBSTACLE_OUTER_SCALE = 1.12;
  var OBSTACLE_RIM_ALPHA = 0.82;
  var OBSTACLE_OUTER_ALPHA = 0.9;

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
      obstacleSprites: [],
      obstacleGroups: [],
      obstacleOuters: [],
      obstacleRims: []
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

  function getCollisionVisualOffset(terrainSnap) {
    if (!terrainSnap || !terrainSnap.collisionActive) {
      return { knockbackX: 0, shakeY: 0 };
    }
    if (lastCollisionId !== terrainSnap.lastCollisionObstacleId) {
      collisionEffectStart = activeTime;
      lastCollisionId = terrainSnap.lastCollisionObstacleId;
    }
    var elapsed = activeTime - collisionEffectStart;
    var envelopeDuration = 380;
    var normalized = Math.min(1, elapsed / envelopeDuration);
    var decay = Math.pow(1 - normalized, 2.2);
    var knockbackX = decay * (terrainSnap.knockbackOffsetX || 0);
    var shakeY = reducedMotion ? 0 : (terrainSnap.shakeOffsetY || 0) * decay;
    return { knockbackX: knockbackX, shakeY: shakeY };
  }

  function syncSubmarine(travelY, terrainSnap) {
    if (!nodes || !nodes.submarine) {
      return;
    }
    var hover = reducedMotion ? 0 : Math.sin(activeTime / 900) * 4;
    var offset = getCollisionVisualOffset(terrainSnap);
    var baseX = 260 - offset.knockbackX;
    var baseY = travelY + hover + offset.shakeY;
    setPosition(nodes.submarine, baseX, baseY);
    nodes.submarine.rotation = reducedMotion ? 0 : Math.sin(activeTime / 1400) * 0.02;
  }

  function resolveObstacleAlias(kind) {
    if (!kind || typeof kind !== "string") {
      return null;
    }
    return OBSTACLE_KIND_ALIASES[kind] || null;
  }

  function createObstacleGroup(index, kind) {
    var alias = resolveObstacleAlias(kind);
    if (!alias) {
      throw new Error("Missing obstacle kind alias: " + kind);
    }
    var texture = RenderRuntime.getTexture(alias);
    if (!texture) {
      throw new Error(
        "Missing authored obstacle texture: " + alias
      );
    }

    var group = new PIXI.Container();
    group.label = "travel-obstacle-" + index;
    group.name = "travel-obstacle-" + index;
    group.eventMode = "none";
    group.visible = false;

    var outerSprite = new PIXI.Sprite(texture);
    outerSprite.label = "travel-obstacle-" + index + "-outer";
    outerSprite.name = outerSprite.label;
    outerSprite.eventMode = "none";
    outerSprite.tint = OBSTACLE_OUTER_TINT;
    outerSprite.alpha = OBSTACLE_OUTER_ALPHA;
    if (outerSprite.anchor && texture.defaultAnchor) {
      outerSprite.anchor.copyFrom(texture.defaultAnchor);
    }

    var rimSprite = new PIXI.Sprite(texture);
    rimSprite.label = "travel-obstacle-" + index + "-rim";
    rimSprite.name = rimSprite.label;
    rimSprite.eventMode = "none";
    rimSprite.tint = OBSTACLE_RIM_TINT;
    rimSprite.alpha = OBSTACLE_RIM_ALPHA;
    if (rimSprite.anchor && texture.defaultAnchor) {
      rimSprite.anchor.copyFrom(texture.defaultAnchor);
    }

    var bodySprite = new PIXI.Sprite(texture);
    bodySprite.label = "travel-obstacle-" + index;
    bodySprite.name = bodySprite.label;
    bodySprite.eventMode = "none";
    bodySprite.tint = OBSTACLE_BODY_TINT;
    bodySprite.alpha = 1.0;
    if (bodySprite.anchor && texture.defaultAnchor) {
      bodySprite.anchor.copyFrom(texture.defaultAnchor);
    }

    group.addChild(outerSprite);
    group.addChild(rimSprite);
    group.addChild(bodySprite);

    RenderRuntime.getContainer("gameplayWorld").addChild(group);

    return {
      group: group,
      outer: outerSprite,
      rim: rimSprite,
      body: bodySprite,
      texture: texture
    };
  }

  function syncObstacles(travelSnap, terrainSnap) {
    if (!nodes || !Terrain || !travelSnap || !terrainSnap || !terrainSnap.active) {
      return;
    }
    var layout = Terrain.getLayout(terrainSnap.missionId);
    if (!layout || !layout.obstacles) {
      return;
    }
    var travelDistance = typeof travelSnap.distance === "number" ? travelSnap.distance : 0;

    while (nodes.obstacleGroups.length < layout.obstacles.length) {
      var obstacleKind = layout.obstacles[nodes.obstacleGroups.length]
        ? layout.obstacles[nodes.obstacleGroups.length].kind
        : null;
      var created = createObstacleGroup(nodes.obstacleGroups.length, obstacleKind);
      nodes.obstacleGroups.push(created.group);
      nodes.obstacleOuters.push(created.outer);
      nodes.obstacleRims.push(created.rim);
      nodes.obstacleSprites.push(created.body);
    }

    var visibleCount = 0;
    var nonFiniteCount = 0;
    var firstVisibleId = "";
    var firstVisibleAlias = "";
    var bodyVisibleCount = 0;
    var rimVisibleCount = 0;
    var outerVisibleCount = 0;

    for (var i = 0; i < layout.obstacles.length; i += 1) {
      var obstacle = layout.obstacles[i];
      var group = nodes.obstacleGroups[i];
      var outer = nodes.obstacleOuters[i];
      var rim = nodes.obstacleRims[i];
      var body = nodes.obstacleSprites[i];
      var screenX = obstacle.worldX - travelDistance;
      var screenY = obstacle.y;
      if (!isFinite(screenX) || !isFinite(screenY)) {
        nonFiniteCount += 1;
        group.visible = false;
        outer.visible = false;
        rim.visible = false;
        body.visible = false;
        continue;
      }
      if (screenX < -obstacle.width || screenX > WIDTH + obstacle.width) {
        group.visible = false;
        outer.visible = false;
        rim.visible = false;
        body.visible = false;
        continue;
      }
      var alias = resolveObstacleAlias(obstacle.kind);
      var texture = alias ? RenderRuntime.getTexture(alias) : null;
      if (texture && group instanceof PIXI.Container) {
        outer.texture = texture;
        rim.texture = texture;
        body.texture = texture;
        if (outer.anchor && texture.defaultAnchor) {
          outer.anchor.copyFrom(texture.defaultAnchor);
        } else if (outer.anchor) {
          outer.anchor.set(0.5, 0.5);
        }
        if (rim.anchor && texture.defaultAnchor) {
          rim.anchor.copyFrom(texture.defaultAnchor);
        } else if (rim.anchor) {
          rim.anchor.set(0.5, 0.5);
        }
        if (body.anchor && texture.defaultAnchor) {
          body.anchor.copyFrom(texture.defaultAnchor);
        } else if (body.anchor) {
          body.anchor.set(0.5, 0.5);
        }
      } else if (!texture) {
        group.visible = false;
        outer.visible = false;
        rim.visible = false;
        body.visible = false;
        continue;
      }
      var frameWidth = (body.texture && body.texture.frame) ? body.texture.frame.width : 1;
      var frameHeight = (body.texture && body.texture.frame) ? body.texture.frame.height : 1;
      var scaleX = obstacle.width / frameWidth;
      var scaleY = obstacle.height / frameHeight;
      var scaleRatio = Math.min(scaleX, scaleY);
      var outerScale = scaleRatio * OBSTACLE_OUTER_SCALE;
      var rimScale = scaleRatio * OBSTACLE_RIM_SCALE;
      setScale(outer, scaleRatio * OBSTACLE_OUTER_SCALE, scaleRatio * OBSTACLE_OUTER_SCALE);
      setScale(rim, scaleRatio * OBSTACLE_RIM_SCALE, scaleRatio * OBSTACLE_RIM_SCALE);
      setScale(body, scaleRatio, scaleRatio);
      group.position.set(screenX, screenY);
      body.tint = OBSTACLE_BODY_TINT;
      group.visible = true;
      outer.visible = true;
      rim.visible = true;
      body.visible = true;
      visibleCount += 1;
      bodyVisibleCount += 1;
      rimVisibleCount += 1;
      outerVisibleCount += 1;
      if (!firstVisibleId) {
        firstVisibleId = obstacle.id || "";
        firstVisibleAlias = alias || "";
      }
    }

    for (var j = layout.obstacles.length; j < nodes.obstacleGroups.length; j += 1) {
      nodes.obstacleGroups[j].visible = false;
      nodes.obstacleOuters[j].visible = false;
      nodes.obstacleRims[j].visible = false;
      nodes.obstacleSprites[j].visible = false;
    }

    setDiagnostic("data-travel-scene-obstacle-renderer", "sprite");
    setDiagnostic("data-travel-scene-obstacle-boundary-mode", "dual-silhouette");
    setDiagnostic("data-travel-scene-placeholder-obstacle-count", "0");
    setDiagnostic("data-travel-scene-obstacle-alias-count", String(Object.keys(OBSTACLE_KIND_ALIASES).length));
    setDiagnostic("data-travel-scene-visible-obstacle-count", String(visibleCount));
    setDiagnostic("data-travel-scene-visible-obstacle-body-count", String(bodyVisibleCount));
    setDiagnostic("data-travel-scene-visible-obstacle-rim-count", String(rimVisibleCount));
    setDiagnostic("data-travel-scene-visible-obstacle-outer-count", String(outerVisibleCount));
    setDiagnostic("data-travel-scene-nonfinite-obstacle-count", String(nonFiniteCount));
    setDiagnostic("data-travel-scene-first-visible-obstacle-id", firstVisibleId);
    setDiagnostic("data-travel-scene-first-visible-obstacle-alias", firstVisibleAlias);
    setDiagnostic("data-travel-scene-obstacle-body-tint", "ffffff");
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
    syncSubmarine(travelSnap.y, terrainSnap);
    syncObstacles(travelSnap, terrainSnap);
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
      for (var j = 0; j < nodes.obstacleGroups.length; j += 1) {
        removeOwnedChild(RenderRuntime.getContainer("gameplayWorld"), nodes.obstacleGroups[j]);
        if (nodes.obstacleOuters[j]) {
          removeOwnedChild(nodes.obstacleGroups[j], nodes.obstacleOuters[j]);
        }
        if (nodes.obstacleRims[j]) {
          removeOwnedChild(nodes.obstacleGroups[j], nodes.obstacleRims[j]);
        }
        if (nodes.obstacleSprites[j]) {
          removeOwnedChild(nodes.obstacleGroups[j], nodes.obstacleSprites[j]);
        }
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
