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

  var impactEffectStart = 0;
  var impactEffectId = null;
  var impactEffectMissionId = null;
  var impactEffectRunning = false;
  var impactObstacleIndex = -1;
  var impactContactX = 0;
  var impactContactY = 0;
  var impactHandledCollisionCount = -1;

  var IMPACT_TOTAL_MS = 420;
  var IMPACT_CORE_PEAK_MS = 90;
  var IMPACT_RAYS_MS = 240;
  var IMPACT_RING_MS = 380;
  var IMPACT_PULSE_MS = 220;
  var IMPACT_OVERLAY_MS = 140;
  var IMPACT_REDUCED_MS = 180;

  var IMPACT_CORE_COLOR = 0xFFFBE6;
  var IMPACT_RING_COLOR = 0xFF9F43;
  var IMPACT_RAYS_COLOR = 0xFFD166;
  var IMPACT_OVERLAY_TINT = 0xFFF2CC;

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
    _applyTrimAnchor(sprite, texture);
    return sprite;
  }

  function _applyTrimAnchor(sprite, texture) {
    var trim = texture.trim;
    var orig = texture.orig;
    if (
      !orig ||
      !finite(orig.width) ||
      !finite(orig.height) ||
      orig.width <= 0 ||
      orig.height <= 0
    ) {
      return;
    }
    if (trim && finite(trim.x) && finite(trim.y) && finite(trim.width) && finite(trim.height)) {
      sprite.anchor.set(
        (trim.x + trim.width / 2) / orig.width,
        (trim.y + trim.height / 2) / orig.height
      );
    } else {
      sprite.anchor.set(0.5, 0.5);
    }
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
      collisionImpactRoot: null,
      collisionImpactCore: null,
      collisionImpactRing: null,
      collisionImpactRays: null,
      collisionSubmarineFlash: null,
      screenFlash: null,
      splashParticles: [],
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

    var impactRoot = new PIXI.Container();
    impactRoot.label = "travel-collision-impact-root";
    impactRoot.name = "travel-collision-impact-root";
    impactRoot.eventMode = "none";
    impactRoot.visible = false;
    impactRoot.alpha = 0;

    var impactCore = new PIXI.Graphics();
    impactCore.label = "travel-collision-impact-core";
    impactCore.name = "travel-collision-impact-core";
    impactCore.eventMode = "none";
    impactCore.circle(0, 0, 12).fill(IMPACT_CORE_COLOR);

    var impactRing = new PIXI.Graphics();
    impactRing.label = "travel-collision-impact-ring";
    impactRing.name = "travel-collision-impact-ring";
    impactRing.eventMode = "none";
    impactRing.circle(0, 0, 30).stroke({ width: 6, color: IMPACT_RING_COLOR });

    var impactRays = new PIXI.Graphics();
    impactRays.label = "travel-collision-impact-rays";
    impactRays.name = "travel-collision-impact-rays";
    impactRays.eventMode = "none";
    for (var rayIndex = 0; rayIndex < 8; rayIndex += 1) {
      var rayAngle = (rayIndex / 8) * Math.PI * 2;
      impactRays.moveTo(Math.cos(rayAngle) * 20, Math.sin(rayAngle) * 20);
      impactRays.lineTo(Math.cos(rayAngle) * 38, Math.sin(rayAngle) * 38);
    }
    impactRays.stroke({ width: 5, color: IMPACT_RAYS_COLOR });

    impactRoot.addChild(impactCore);
    impactRoot.addChild(impactRing);
    impactRoot.addChild(impactRays);

    var submarineTexture = RenderRuntime.getTexture("scene.submarine");
    var submarineFlash = new PIXI.Sprite(submarineTexture);
    submarineFlash.label = "travel-submarine-impact-flash";
    submarineFlash.name = "travel-submarine-impact-flash";
    submarineFlash.eventMode = "none";
    submarineFlash.visible = false;
    submarineFlash.alpha = 0;
    if (submarineTexture) {
      _applyTrimAnchor(submarineFlash, submarineTexture);
    }

    nodes.collisionImpactRoot = impactRoot;
    nodes.collisionImpactCore = impactCore;
    nodes.collisionImpactRing = impactRing;
    nodes.collisionImpactRays = impactRays;
    nodes.collisionSubmarineFlash = submarineFlash;

    var screenFlashContainer = new PIXI.Container();
    screenFlashContainer.label = "travel-screen-flash";
    screenFlashContainer.name = "travel-screen-flash";
    screenFlashContainer.eventMode = "none";
    screenFlashContainer.visible = false;
    screenFlashContainer.alpha = 0;

    var screenFlashRect = new PIXI.Graphics();
    if (typeof screenFlashRect.rect === "function") {
      screenFlashRect.rect(-WIDTH / 2, -HEIGHT / 2, WIDTH, HEIGHT);
    } else if (typeof screenFlashRect.drawRect === "function") {
      screenFlashRect.drawRect(-WIDTH / 2, -HEIGHT / 2, WIDTH, HEIGHT);
    }
    if (typeof screenFlashRect.fill === "function") {
      screenFlashRect.fill(0xFFFFFF);
    } else if (typeof screenFlashRect.beginFill === "function") {
      screenFlashRect.beginFill(0xFFFFFF);
      if (typeof screenFlashRect.endFill === "function") {
        screenFlashRect.endFill();
      }
    }
    screenFlashContainer.addChild(screenFlashRect);

    nodes.screenFlash = screenFlashContainer;
    nodes.splashParticles = [];

    addChild(far, nodes.waterFar);
    addChild(mid, nodes.reefMid);
    addChild(mid, nodes.passage);
    addChild(mid, nodes.caustic);
    gameplayWorld.addChildAt(nodes.sandPath, 0);
    addChild(submarine, nodes.submarine);
    addChild(submarine, nodes.collisionSubmarineFlash);
    for (var loopIndex = 0; loopIndex < nodes.seaweedLoops.length; loopIndex += 1) {
      addChild(gameplayWorld, nodes.seaweedLoops[loopIndex]);
    }
    addChild(foreground, nodes.coralForeground);
    addChild(effects, nodes.bubbles);
    addChild(effects, nodes.collisionImpactRoot);
    if (nodes.collisionFlash) {
      addChild(effects, nodes.collisionFlash);
    }
    addChild(effects, nodes.screenFlash);

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
    if (nodes.collisionImpactRoot) {
      nodes.collisionImpactRoot.visible = false;
      nodes.collisionImpactRoot.alpha = 0;
    }
    if (nodes.collisionSubmarineFlash) {
      nodes.collisionSubmarineFlash.visible = false;
      nodes.collisionSubmarineFlash.alpha = 0;
    }
    if (nodes.screenFlash) {
      nodes.screenFlash.visible = false;
      nodes.screenFlash.alpha = 0;
    }
    var splashArr = nodes.splashParticles || [];
    for (var si = 0; si < splashArr.length; si += 1) {
      splashArr[si].alpha = 0;
      splashArr[si].visible = false;
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
    if (reducedMotion) {
      nodes.submarine.rotation = Math.sin(activeTime / 1400) * 0.02;
    } else if (terrainSnap && terrainSnap.collisionActive) {
      var wobbleSpeed = 180;
      var wobbleAmp = 0.06 * offset.knockbackX / (terrainSnap.knockbackOffsetX || 1);
      var wobble = Math.sin(activeTime / wobbleSpeed) * Math.max(0, wobbleAmp);
      nodes.submarine.rotation = Math.sin(activeTime / 1400) * 0.02 + wobble;
    } else {
      nodes.submarine.rotation = Math.sin(activeTime / 1400) * 0.02;
    }
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
    _applyTrimAnchor(outerSprite, texture);

    var rimSprite = new PIXI.Sprite(texture);
    rimSprite.label = "travel-obstacle-" + index + "-rim";
    rimSprite.name = rimSprite.label;
    rimSprite.eventMode = "none";
    rimSprite.tint = OBSTACLE_RIM_TINT;
    rimSprite.alpha = OBSTACLE_RIM_ALPHA;
    _applyTrimAnchor(rimSprite, texture);

    var bodySprite = new PIXI.Sprite(texture);
    bodySprite.label = "travel-obstacle-" + index;
    bodySprite.name = bodySprite.label;
    bodySprite.eventMode = "none";
    bodySprite.tint = OBSTACLE_BODY_TINT;
    bodySprite.alpha = 1.0;
    _applyTrimAnchor(bodySprite, texture);

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
        _applyTrimAnchor(outer, texture);
        _applyTrimAnchor(rim, texture);
        _applyTrimAnchor(body, texture);
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

  function findImpactObstacle(terrainSnap) {
    if (!Terrain || !terrainSnap || !terrainSnap.missionId) {
      return null;
    }
    var layout = Terrain.getLayout(terrainSnap.missionId);
    if (!layout || !layout.obstacles) {
      return null;
    }
    var collisionId = terrainSnap.lastCollisionObstacleId;
    if (!collisionId) {
      return null;
    }
    for (var i = 0; i < layout.obstacles.length; i += 1) {
      if (layout.obstacles[i].id === collisionId) {
        return { index: i, obstacle: layout.obstacles[i] };
      }
    }
    return null;
  }

  function computeImpactContact(obstacle, travelSnap) {
    var distance =
      travelSnap && typeof travelSnap.distance === "number" ? travelSnap.distance : 0;
    var gupCenterX = Terrain.Constants.gupScreenX;
    var gupRight = gupCenterX + Terrain.Constants.gupHalfWidth;
    var obstacleCenterX = obstacle.worldX - distance;
    var obstacleLeft = obstacleCenterX - obstacle.width / 2;
    var contactX = (gupRight + obstacleLeft) / 2;
    var halfHeight = obstacle.height / 2;
    var contactY = Math.max(
      obstacle.y - halfHeight,
      Math.min(travelSnap.y, obstacle.y + halfHeight)
    );
    if (!finite(contactX) || !finite(contactY)) {
      return null;
    }
    return { x: contactX, y: contactY };
  }

  function resetImpactEffect() {
    if (nodes) {
      if (nodes.collisionImpactRoot) {
        nodes.collisionImpactRoot.visible = false;
        nodes.collisionImpactRoot.alpha = 0;
        setScale(nodes.collisionImpactRoot, 1, 1);
        nodes.collisionImpactRoot.rotation = 0;
      }
      if (nodes.collisionImpactCore) {
        nodes.collisionImpactCore.visible = true;
        nodes.collisionImpactCore.alpha = 1;
        setScale(nodes.collisionImpactCore, 1, 1);
      }
      if (nodes.collisionImpactRing) {
        nodes.collisionImpactRing.visible = true;
        nodes.collisionImpactRing.alpha = 1;
        setScale(nodes.collisionImpactRing, 1, 1);
      }
      if (nodes.collisionImpactRays) {
        nodes.collisionImpactRays.visible = true;
        nodes.collisionImpactRays.alpha = 1;
        setScale(nodes.collisionImpactRays, 1, 1);
      }
      if (nodes.collisionFlash) {
        nodes.collisionFlash.visible = false;
        nodes.collisionFlash.alpha = 0;
      }
      if (nodes.collisionSubmarineFlash) {
        nodes.collisionSubmarineFlash.visible = false;
        nodes.collisionSubmarineFlash.alpha = 0;
        nodes.collisionSubmarineFlash.tint = 0xFFFFFF;
      }
      if (
        impactObstacleIndex >= 0 &&
        impactObstacleIndex < nodes.obstacleGroups.length
      ) {
        var group = nodes.obstacleGroups[impactObstacleIndex];
        if (group) {
          setScale(group, 1, 1);
        }
        var outer = nodes.obstacleOuters[impactObstacleIndex];
        var rim = nodes.obstacleRims[impactObstacleIndex];
        if (outer) {
          outer.alpha = OBSTACLE_OUTER_ALPHA;
          outer.tint = OBSTACLE_OUTER_TINT;
        }
        if (rim) {
          rim.alpha = OBSTACLE_RIM_ALPHA;
          rim.tint = OBSTACLE_RIM_TINT;
        }
      }
    }
    impactEffectRunning = false;
    impactEffectId = null;
    impactEffectMissionId = null;
    impactObstacleIndex = -1;
    impactContactX = 0;
    impactContactY = 0;
  }

  function startImpactEffect(terrainSnap, travelSnap) {
    var found = findImpactObstacle(terrainSnap);
    if (!found) {
      resetImpactEffect();
      return;
    }
    var contact = computeImpactContact(found.obstacle, travelSnap);
    if (!contact) {
      resetImpactEffect();
      return;
    }
    resetImpactEffect();
    impactEffectId = terrainSnap.lastCollisionObstacleId;
    impactEffectStart = activeTime;
    impactEffectMissionId = terrainSnap.missionId;
    impactEffectRunning = true;
    impactObstacleIndex = found.index;
    impactContactX = contact.x;
    impactContactY = contact.y;
    if (typeof terrainSnap.collisionCount === "number") {
      impactHandledCollisionCount = terrainSnap.collisionCount;
    }
    spawnSplashParticles(impactContactX, impactContactY);
  }

  function syncSubmarineFlashOverlay(elapsed) {
    var overlay = nodes.collisionSubmarineFlash;
    var sub = nodes.submarine;
    if (!overlay || !sub) {
      return;
    }
    overlay.position.set(sub.position.x, sub.position.y);
    overlay.scale.set(sub.scale.x, sub.scale.y);
    overlay.rotation = sub.rotation;
    overlay.visible = true;
    if (overlay.blendMode !== undefined && overlay.blendMode !== "add") {
      overlay.blendMode = "add";
    }
    overlay.tint = IMPACT_OVERLAY_TINT;
    if (reducedMotion) {
      var reducedProgress = Math.min(1, elapsed / IMPACT_REDUCED_MS);
      overlay.alpha = Math.max(0, 0.65 * (1 - reducedProgress));
    } else {
      var overlayProgress = Math.min(1, elapsed / IMPACT_OVERLAY_MS);
      overlay.alpha = Math.max(0, 0.65 * (1 - overlayProgress));
    }
  }

  function syncImpactPulse(elapsed) {
    if (
      reducedMotion ||
      impactObstacleIndex < 0 ||
      !nodes ||
      impactObstacleIndex >= nodes.obstacleGroups.length
    ) {
      return;
    }
    var group = nodes.obstacleGroups[impactObstacleIndex];
    if (!group) {
      return;
    }
    var pulseProgress = Math.min(1, elapsed / IMPACT_PULSE_MS);
    var pulse = Math.sin(pulseProgress * Math.PI);
    var factor = 1 + 0.05 * pulse;
    setScale(group, factor, factor);
    var outer = nodes.obstacleOuters[impactObstacleIndex];
    var rim = nodes.obstacleRims[impactObstacleIndex];
    if (outer) {
      outer.alpha = Math.min(1, OBSTACLE_OUTER_ALPHA + 0.12 * pulse);
    }
    if (rim) {
      rim.alpha = Math.min(1, OBSTACLE_RIM_ALPHA + 0.12 * pulse);
    }
  }

  function syncScreenFlash(elapsed) {
    var flash = nodes.screenFlash;
    if (!flash) {
      return;
    }
    var flashDuration = reducedMotion ? 120 : 160;
    var progress = Math.min(1, elapsed / flashDuration);
    var alpha = (1 - progress) * 0.35;
    flash.visible = true;
    flash.alpha = Math.max(0, alpha);
  }

  function syncSplashParticles(elapsed) {
    var pool = nodes.splashParticles;
    if (!pool || !impactEffectRunning) {
      return;
    }
    var activeSplash = false;
    for (var i = 0; i < pool.length; i += 1) {
      var p = pool[i];
      if (!p.active) {
        continue;
      }
      p.life += elapsed;
      if (p.life >= p.lifetime) {
        p.active = false;
        p.visible = false;
        continue;
      }
      activeSplash = true;
      var t = p.life / p.lifetime;
      var ease = 1 - t;
      p.x = p.originX + p.vx * p.life * 0.06;
      p.y = p.originY + p.vy * p.life * 0.06 + 0.15 * p.life * 0.06;
      p.scale.set(p.baseScale * ease, p.baseScale * ease);
      p.alpha = Math.max(0, ease * p.startAlpha);
    }
  }

  function spawnSplashParticles(x, y) {
    var pool = nodes.splashParticles;
    if (!pool) {
      return;
    }
    var count = reducedMotion ? 6 : 12;
    for (var i = 0; i < count; i += 1) {
      var p = null;
      for (var j = 0; j < pool.length; j += 1) {
        if (!pool[j].active) {
          p = pool[j];
          break;
        }
      }
      if (!p) {
        p = new PIXI.Graphics();
        p.circle(0, 0, 3).fill(0xFFFFFF);
        p.eventMode = "none";
        pool.push(p);
        addChild(RenderRuntime.getContainer("effects"), p);
      }
      var angle = (i / count) * Math.PI * 2 + (Math.random() - 0.5) * 0.6;
      var speed = 1.5 + Math.random() * 2.5;
      p.active = true;
      p.life = 0;
      p.lifetime = 250 + Math.random() * 200;
      p.originX = x;
      p.originY = y;
      p.vx = Math.cos(angle) * speed;
      p.vy = Math.sin(angle) * speed - 1.2;
      p.baseScale = 0.6 + Math.random() * 0.8;
      p.scale.set(p.baseScale, p.baseScale);
      p.alpha = 1;
      p.startAlpha = 1;
      p.visible = true;
    }
  }

  function setImpactDiagnostics() {
    var running = impactEffectRunning;
    setDiagnostic("data-travel-scene-impact-mode", "contact-burst-v1");
    setDiagnostic("data-travel-scene-impact-active", running ? "true" : "false");
    var phase = "idle";
    if (running) {
      var elapsed = activeTime - impactEffectStart;
      if (elapsed < IMPACT_CORE_PEAK_MS) {
        phase = "core";
      } else if (elapsed < IMPACT_RAYS_MS) {
        phase = "rays";
      } else if (elapsed < IMPACT_RING_MS) {
        phase = "ring";
      } else {
        phase = "bubble";
      }
    }
    setDiagnostic("data-travel-scene-impact-phase", phase);
    setDiagnostic(
      "data-travel-scene-impact-obstacle-id",
      running && impactEffectId ? String(impactEffectId) : ""
    );
    setDiagnostic(
      "data-travel-scene-impact-contact-x",
      running ? String(impactContactX) : ""
    );
    setDiagnostic(
      "data-travel-scene-impact-contact-y",
      running ? String(impactContactY) : ""
    );
    setDiagnostic(
      "data-travel-scene-impact-core-visible",
      running && nodes && nodes.collisionImpactCore
        ? String(nodes.collisionImpactCore.visible)
        : "false"
    );
    setDiagnostic(
      "data-travel-scene-impact-ring-visible",
      running && nodes && nodes.collisionImpactRing
        ? String(nodes.collisionImpactRing.visible)
        : "false"
    );
    setDiagnostic(
      "data-travel-scene-impact-rays-visible",
      running && nodes && nodes.collisionImpactRays
        ? String(nodes.collisionImpactRays.visible)
        : "false"
    );
    setDiagnostic(
      "data-travel-scene-impact-bubbles-visible",
      running && nodes && nodes.collisionFlash
        ? String(nodes.collisionFlash.visible)
        : "false"
    );
    setDiagnostic(
      "data-travel-scene-impact-target-pulse",
      running && impactObstacleIndex >= 0 ? "true" : "false"
    );
    setDiagnostic(
      "data-travel-scene-impact-submarine-flash",
      running && nodes && nodes.collisionSubmarineFlash
        ? String(nodes.collisionSubmarineFlash.visible)
        : "false"
    );
  }

  function syncImpactEffect(travelSnap, terrainSnap) {
    if (!nodes) {
      return;
    }
    var collisionActive = terrainSnap && terrainSnap.collisionActive;
    var collisionCount =
      terrainSnap && typeof terrainSnap.collisionCount === "number"
        ? terrainSnap.collisionCount
        : -1;

    if (
      collisionActive &&
      impactHandledCollisionCount !== collisionCount
    ) {
      startImpactEffect(terrainSnap, travelSnap);
    }

    if (
      impactEffectRunning &&
      terrainSnap &&
      terrainSnap.active &&
      impactEffectMissionId &&
      impactEffectMissionId !== terrainSnap.missionId
    ) {
      resetImpactEffect();
    }

    if (!impactEffectRunning) {
      setImpactDiagnostics();
      return;
    }

    var elapsed = activeTime - impactEffectStart;
    var totalDuration = reducedMotion ? IMPACT_REDUCED_MS : IMPACT_TOTAL_MS;
    if (elapsed >= totalDuration) {
      resetImpactEffect();
      setImpactDiagnostics();
      return;
    }

    var root = nodes.collisionImpactRoot;
    root.visible = true;
    setPosition(root, impactContactX, impactContactY);

    var burst = nodes.collisionFlash;
    var core = nodes.collisionImpactCore;
    var ring = nodes.collisionImpactRing;
    var rays = nodes.collisionImpactRays;

    if (reducedMotion) {
      var reducedProgress = Math.min(1, elapsed / IMPACT_REDUCED_MS);
      var reducedAlpha = 1 - reducedProgress * 0.85;
      root.alpha = reducedAlpha;
      core.visible = true;
      setScale(core, 1, 1);
      core.alpha = reducedAlpha;
      ring.visible = true;
      setScale(ring, 1, 1);
      ring.alpha = reducedAlpha;
      rays.visible = false;
      if (burst) {
        burst.visible = false;
      }
    } else {
      var coreProgress = Math.min(1, elapsed / IMPACT_CORE_PEAK_MS);
      core.visible = true;
      setScale(core, 1 - coreProgress * 0.25, 1 - coreProgress * 0.25);
      core.alpha = 1 - coreProgress * 0.9;

      var ringProgress = Math.min(1, elapsed / IMPACT_RING_MS);
      ring.visible = true;
      setScale(ring, 1 + ringProgress * 1.5, 1 + ringProgress * 1.5);
      ring.alpha = 1 - ringProgress * 0.92;

      var raysProgress = Math.min(1, elapsed / IMPACT_RAYS_MS);
      rays.visible = true;
      setScale(rays, 1 + raysProgress * 0.55, 1 + raysProgress * 0.55);
      rays.alpha = 1 - raysProgress * 0.9;

      if (burst) {
        burst.visible = true;
        setPosition(burst, impactContactX, impactContactY);
        var burstScale = 0.35 + (elapsed / IMPACT_TOTAL_MS) * 0.55;
        burst.scale.set(burstScale, burstScale);
        burst.alpha = Math.max(0, 1 - (elapsed / IMPACT_TOTAL_MS) * 0.95);
      }
    }

    syncImpactPulse(elapsed);
    syncSubmarineFlashOverlay(elapsed);
    syncScreenFlash(elapsed);
    syncSplashParticles(elapsed);

    setImpactDiagnostics();
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
    syncImpactEffect(travelSnap, terrainSnap);
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
    resetImpactEffect();
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
    resetImpactEffect();
    setImpactDiagnostics();
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
    resetImpactEffect();
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
      if (nodes.collisionImpactRoot) {
        removeOwnedChild(RenderRuntime.getContainer("effects"), nodes.collisionImpactRoot);
      }
      if (nodes.collisionSubmarineFlash) {
        removeOwnedChild(RenderRuntime.getContainer("submarine"), nodes.collisionSubmarineFlash);
      }
      if (nodes.collisionFlash) {
        removeOwnedChild(RenderRuntime.getContainer("effects"), nodes.collisionFlash);
      }
      if (nodes.screenFlash) {
        removeOwnedChild(RenderRuntime.getContainer("effects"), nodes.screenFlash);
      }
      var splashArr = nodes.splashParticles || [];
      for (var sj = 0; sj < splashArr.length; sj += 1) {
        if (splashArr[sj] && splashArr[sj].parent) {
          removeOwnedChild(RenderRuntime.getContainer("effects"), splashArr[sj]);
        }
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
