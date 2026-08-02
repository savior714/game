(function () {
  "use strict";

  var root = window.OceanRescue = window.OceanRescue || {};
  var RenderRuntime = root.RenderRuntime || null;
  var Crab = root.Crab || null;
  var Layout = (Crab && Crab.Layout) || null;

  function layoutCrabCenter() {
    return Layout ? Layout.crabCenter : { x: 900, y: 500 };
  }

  function layoutGrabberBase() {
    return Layout
      ? Layout.grabberBase
      : { x: 520, y: Math.floor(HEIGHT * 0.72) };
  }

  function layoutDropZone() {
    return Layout ? Layout.dropZone : (Crab && Crab.DropZone) || null;
  }

  function layoutRocks() {
    return Layout ? Layout.rocks : (Crab && Crab.Rocks) || [];
  }
  var REQUIRED_ALIASES = [
    "crab.trapped",
    "crab.free",
    "rescue.rock.01",
    "rescue.rock.02",
    "rescue.rock.03",
    "tool.grabber.base",
    "tool.grabber.arm",
    "tool.grabber.claw.open",
    "tool.grabber.claw.closed",
    "ui.drop-zone",
    "fx.hold-ring",
    "scene.water.far",
    "scene.reef.mid",
    "scene.coral.foreground",
    "scene.sand-path",
    "fx.caustic",
    "fx.bubbles"
  ];

  var WIDTH = 1280;
  var HEIGHT = 720;
  var MAX_DELTA_MS = 50;
  var MOUNTED = false;
  var ACTIVE = false;
  var PAUSED = false;
  var ANIMATION_FRAME_ID = null;
  var LAST_TIMESTAMP = null;
  var ACTIVE_TIME = 0;
  var ANIMATION_RUNNING = false;
  var REDUCED_MOTION = false;
  var NODES = null;
  var SNAPSHOT = null;
  var POINTER_INTENT = { active: false, x: null, y: null };
  var MISSING_ALIASES = [];
  var FEEDBACK_STARTED_AT = 0;
  var LAST_FEEDBACK = null;

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
    setDiagnostic("data-crab-scene", status);
    setDiagnostic("data-crab-scene-node-count", NODES ? nodeCount() : 0);
    setDiagnostic(
      "data-crab-scene-animation",
      PAUSED && MOUNTED ? "paused" : ANIMATION_RUNNING ? "running" : "stopped"
    );
    setDiagnostic(
      "data-crab-scene-legacy-visible",
      RenderRuntime && typeof RenderRuntime.getLegacyBridgeVisible === "function"
        ? RenderRuntime.getLegacyBridgeVisible()
        : true
    );
    setDiagnostic("data-crab-scene-renderer", "sprite");
    setDiagnostic("data-crab-scene-placeholder-count", 0);
    setDiagnostic("data-crab-scene-nonfinite-count", 0);
    var current = SNAPSHOT || {};
    setDiagnostic(
      "data-crab-scene-active-rock-id",
      current.activeRockId ? current.activeRockId : ""
    );
    var rockCenter = current.currentRockCenter;
    setDiagnostic(
      "data-crab-scene-active-rock-x",
      rockCenter && isFinite(rockCenter.x) ? String(rockCenter.x) : ""
    );
    setDiagnostic(
      "data-crab-scene-active-rock-y",
      rockCenter && isFinite(rockCenter.y) ? String(rockCenter.y) : ""
    );
    setDiagnostic(
      "data-crab-scene-completed-count",
      String(current.completedRockIds ? current.completedRockIds.length : 0)
    );
    setDiagnostic(
      "data-crab-scene-grabbed",
      current.grabbed ? "true" : "false"
    );
    setDiagnostic(
      "data-crab-scene-feedback",
      current.feedback ? current.feedback : "none"
    );
    setDiagnostic(
      "data-crab-scene-crab-state",
      current.complete ? "free" : "trapped"
    );
    setDiagnostic(
      "data-crab-scene-missing-alias-count",
      MISSING_ALIASES.length
    );
  }

  function isFinite(value) {
    return typeof value === "number" && Number.isFinite(value);
  }

  function nodeCount() {
    if (!NODES) {
      return 0;
    }
    var count = 0;
    var keys = Object.keys(NODES);
    for (var i = 0; i < keys.length; i += 1) {
      var value = NODES[keys[i]];
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
    if (NODES) {
      return;
    }
    var far = RenderRuntime.getContainer("farBackground");
    var mid = RenderRuntime.getContainer("midground");
    var gameplayWorld = RenderRuntime.getContainer("gameplayWorld");
    var foreground = RenderRuntime.getContainer("foreground");
    var effects = RenderRuntime.getContainer("effects");
    if (!far || !mid || !gameplayWorld || !foreground || !effects) {
      throw new Error("Missing canonical authored scene container");
    }

    NODES = {
      water: makeSprite("scene.water.far", "crab-water-far"),
      reef: makeSprite("scene.reef.mid", "crab-reef-mid"),
      caustic: makeSprite("fx.caustic", "crab-caustic"),
      sandPath: makeSprite("scene.sand-path", "crab-sand-path"),
      foreground: makeSprite("scene.coral.foreground", "crab-coral-foreground"),
      bubbles: makeSprite("fx.bubbles", "crab-bubbles"),
      crabTrapped: makeSprite("crab.trapped", "crab-trapped"),
      crabFree: makeSprite("crab.free", "crab-free"),
      rocks: [],
      grabberBase: makeSprite("tool.grabber.base", "crab-grabber-base"),
      grabberArm: makeSprite("tool.grabber.arm", "crab-grabber-arm"),
      grabberClawOpen: makeSprite("tool.grabber.claw.open", "crab-grabber-claw-open"),
      grabberClawClosed: makeSprite("tool.grabber.claw.closed", "crab-grabber-claw-closed"),
      dropZone: makeSprite("ui.drop-zone", "crab-drop-zone"),
      holdRing: makeSprite("fx.hold-ring", "crab-hold-ring")
    };

    for (var r = 0; r < 3; r += 1) {
      NODES.rocks.push(makeSprite("rescue.rock." + String(r + 1).padStart(2, "0"), "crab-rock-" + (r + 1)));
    }

    addChild(far, NODES.water);
    addChild(mid, NODES.reef);
    addChild(mid, NODES.caustic);
    addChild(gameplayWorld, NODES.sandPath);
    addChild(foreground, NODES.foreground);
    addChild(effects, NODES.bubbles);
    addChild(gameplayWorld, NODES.crabTrapped);
    addChild(gameplayWorld, NODES.crabFree);
    for (var rockIndex = 0; rockIndex < NODES.rocks.length; rockIndex += 1) {
      addChild(gameplayWorld, NODES.rocks[rockIndex]);
    }
    addChild(gameplayWorld, NODES.grabberBase);
    addChild(gameplayWorld, NODES.grabberArm);
    addChild(gameplayWorld, NODES.grabberClawOpen);
    addChild(gameplayWorld, NODES.grabberClawClosed);
    addChild(gameplayWorld, NODES.dropZone);
    addChild(effects, NODES.holdRing);

    layoutStaticNodes();
  }

  function layoutStaticNodes() {
    setPosition(NODES.water, WIDTH / 2, HEIGHT / 2);
    setScale(NODES.water, 3.2, 2.4);
    NODES.water.alpha = 1;

    setPosition(NODES.reef, WIDTH / 2, 500);
    setScale(NODES.reef, 1.4, 0.85);
    NODES.reef.alpha = 0.55;

    setPosition(NODES.caustic, WIDTH / 2, 300);
    setScale(NODES.caustic, 1.6, 1.3);
    NODES.caustic.alpha = 0.35;

    setPosition(NODES.sandPath, WIDTH / 2, HEIGHT);
    setScale(NODES.sandPath, 1, 1);
    NODES.sandPath.alpha = 1;

    setPosition(NODES.foreground, WIDTH / 2, 790);
    setScale(NODES.foreground, 1, 1);
    NODES.foreground.alpha = 0.9;

    setPosition(NODES.bubbles, 250, 330);
    setScale(NODES.bubbles, 0.8, 0.8);
    NODES.bubbles.alpha = 0.7;

    var crabCenter = layoutCrabCenter();
    setPosition(NODES.crabTrapped, crabCenter.x, crabCenter.y);
    setPosition(NODES.crabFree, crabCenter.x, crabCenter.y);
    setScale(NODES.crabTrapped, 1.0, 1.0);
    setScale(NODES.crabFree, 1.0, 1.0);

    var rocks = layoutRocks();
    for (var r = 0; r < rocks.length; r += 1) {
      var rock = rocks[r];
      setPosition(NODES.rocks[r], rock.start.x, rock.start.y);
      var baseScale = rock.radius / 46;
      setScale(NODES.rocks[r], baseScale, baseScale);
    }

    var grabberBase = layoutGrabberBase();
    setPosition(NODES.grabberBase, grabberBase.x, grabberBase.y);
    setScale(NODES.grabberBase, 0.85, 0.85);
    setPosition(NODES.grabberArm, grabberBase.x, grabberBase.y);
    setScale(NODES.grabberArm, 0.7, 0.7);
    setPosition(NODES.grabberClawOpen, grabberBase.x, grabberBase.y);
    setScale(NODES.grabberClawOpen, 0.85, 0.85);
    setPosition(NODES.grabberClawClosed, grabberBase.x, grabberBase.y);
    setScale(NODES.grabberClawClosed, 0.85, 0.85);

    var dz = layoutDropZone();
    setPosition(NODES.dropZone, dz.x, dz.y);
    var dzScaleX = dz.width / 300;
    var dzScaleY = dz.height / 320;
    setScale(NODES.dropZone, dzScaleX, dzScaleY);

    setPosition(NODES.holdRing, 0, 0);
    setScale(NODES.holdRing, 0.6, 0.6);

    NODES.crabFree.visible = false;
    NODES.grabberClawClosed.visible = false;
    NODES.dropZone.alpha = 0.7;
    NODES.holdRing.visible = false;
  }

  function setReducedMotion() {
    REDUCED_MOTION = false;
    if (window.matchMedia) {
      REDUCED_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }
  }

  function showOwnedNodes() {
    if (!NODES) {
      return;
    }
    var keys = Object.keys(NODES);
    for (var i = 0; i < keys.length; i += 1) {
      var value = NODES[keys[i]];
      if (Array.isArray(value)) {
        for (var j = 0; j < value.length; j += 1) {
          value[j].visible = true;
        }
      } else if (value) {
        value.visible = true;
      }
    }
  }

  function hideOwnedNodes() {
    if (!NODES) {
      return;
    }
    var keys = Object.keys(NODES);
    for (var i = 0; i < keys.length; i += 1) {
      var value = NODES[keys[i]];
      if (Array.isArray(value)) {
        for (var j = 0; j < value.length; j += 1) {
          value[j].visible = false;
        }
      } else if (value) {
        value.visible = false;
      }
    }
  }

  function rockById(rockId) {
    var rocks = layoutRocks();
    if (!Array.isArray(rocks)) {
      return null;
    }
    for (var i = 0; i < rocks.length; i += 1) {
      if (rocks[i].id === rockId) {
        return rocks[i];
      }
    }
    return null;
  }

  function crabState(current) {
    if (!current) {
      return "trapped";
    }
    if (current.complete || current.completedRockIds.length >= 3) {
      return "free";
    }
    if (current.completedRockIds.length >= 2) {
      return "relief-2";
    }
    if (current.completedRockIds.length >= 1) {
      return "relief-1";
    }
    return "trapped";
  }

  function syncCrab(current) {
    var state = crabState(current);
    var free = state === "free";
    var crabCenter = layoutCrabCenter();
    NODES.crabTrapped.visible = !free;
    NODES.crabFree.visible = free;
    if (state === "trapped") {
      NODES.crabTrapped.alpha = 1;
      NODES.crabFree.alpha = 0;
    } else if (state === "relief-1") {
      NODES.crabTrapped.alpha = 0.7;
      NODES.crabFree.alpha = 0.3;
    } else if (state === "relief-2") {
      NODES.crabTrapped.alpha = 0.3;
      NODES.crabFree.alpha = 0.7;
    } else {
      NODES.crabTrapped.alpha = 0;
      NODES.crabFree.alpha = 1;
    }
    var count = current ? current.completedRockIds.length : 0;
    var lift = count * 14;
    NODES.crabTrapped.position.y = crabCenter.y - lift;
    NODES.crabFree.position.y = free ? crabCenter.y - 16 : crabCenter.y - lift;
    var breathe = REDUCED_MOTION ? 1 : 1 + Math.sin(ACTIVE_TIME / 1500) * 0.012;
    NODES.crabTrapped.scale.set(breathe, breathe);
    NODES.crabFree.scale.set(breathe, breathe);
  }

  function syncRocks(current) {
    if (!current) {
      return;
    }
    var rocks = layoutRocks();
    for (var i = 0; i < rocks.length; i += 1) {
      var rock = rocks[i];
      var sprite = NODES.rocks[i];
      var completed = current.completedRockIds.indexOf(rock.id) !== -1;
      var isActive = current.activeRockId === rock.id;
      if (completed) {
        sprite.position.set(rock.placed.x, rock.placed.y);
        sprite.alpha = 1;
        sprite.tint = 0x8fd3a8;
      } else if (isActive) {
        var center = current.currentRockCenter;
        var x = center === null ? rock.start.x : center.x;
        var y = center === null ? rock.start.y : center.y;
        if (current.feedback === "failure") {
          var shake = current.failureCount % 2 === 0 ? -6 : 6;
          x += shake;
        }
        sprite.position.set(x, y);
        sprite.alpha = 1;
        if (current.feedback === "success") {
          sprite.tint = 0x8fd3a8;
          var successProgress = Math.min(1, Math.max(0, (ACTIVE_TIME - FEEDBACK_STARTED_AT) / 400));
          var pulse = 1 + (1 - successProgress) * 0.15;
          sprite.scale.set(pulse, pulse);
          sprite.alpha = 1 - successProgress * 0.4;
        } else if (current.feedback === "failure") {
          sprite.tint = 0xff6b6b;
        } else {
          sprite.tint = 0xffffff;
        }
      } else {
        sprite.position.set(rock.start.x, rock.start.y);
        sprite.alpha = 0.75;
        sprite.tint = 0xffffff;
      }
    }
  }

  function syncGrabber(current) {
    if (!current) {
      return;
    }
    var grabberBase = layoutGrabberBase();
    NODES.grabberBase.visible = true;
    var hasActiveRock = current.activeRockId !== null;
    NODES.grabberArm.visible = hasActiveRock;
    NODES.grabberClawOpen.visible = hasActiveRock && !current.grabbed;
    NODES.grabberClawClosed.visible = hasActiveRock && current.grabbed;

    if (hasActiveRock) {
      var rock = rockById(current.activeRockId);
      if (rock) {
        var center = current.currentRockCenter;
        var targetX = center === null ? rock.start.x : center.x;
        var targetY = center === null ? rock.start.y : center.y;
        var armLength = Math.sqrt(
          Math.pow(targetX - grabberBase.x, 2) + Math.pow(targetY - grabberBase.y, 2)
        ) || 1;
        var armAngle = Math.atan2(targetX - grabberBase.x, targetY - grabberBase.y);
        NODES.grabberArm.position.set(grabberBase.x, grabberBase.y);
        NODES.grabberArm.rotation = armAngle;
        var armScale = armLength / 140;
        setScale(NODES.grabberArm, Math.min(armScale, 1.6), armScale);
        var clawX = targetX;
        var clawY = targetY;
        NODES.grabberClawOpen.position.set(clawX, clawY);
        NODES.grabberClawClosed.position.set(clawX, clawY);
        var clawRot = armAngle;
        NODES.grabberClawOpen.rotation = clawRot;
        NODES.grabberClawClosed.rotation = clawRot;
      }
    }

    if (current.grabbed) {
      NODES.grabberClawOpen.alpha = 0;
      NODES.grabberClawClosed.alpha = 1;
    } else if (current.holding) {
      NODES.grabberClawOpen.alpha = 0.6;
      NODES.grabberClawClosed.alpha = 0;
    } else {
      NODES.grabberClawOpen.alpha = 1;
      NODES.grabberClawClosed.alpha = 0;
    }
  }

  function syncDropZone(current) {
    if (!current) {
      return;
    }
    var helpLevel = current.helpLevel || 0;
    if (current.grabbed) {
      NODES.dropZone.alpha = 1;
      NODES.dropZone.tint = helpLevel >= 2 ? 0xffffb0 : 0xffffff;
    } else if (helpLevel >= 2) {
      NODES.dropZone.alpha = 0.85;
      NODES.dropZone.tint = 0xffffff;
    } else {
      NODES.dropZone.alpha = 0.65;
      NODES.dropZone.tint = 0xffffff;
    }
  }

  function syncHoldRing(current) {
    if (!current || current.activeRockId === null) {
      NODES.holdRing.visible = false;
      return;
    }
    if (!current.holding) {
      NODES.holdRing.visible = false;
      return;
    }
    var rock = rockById(current.activeRockId);
    if (!rock) {
      NODES.holdRing.visible = false;
      return;
    }
    var center = current.currentRockCenter;
    var x = center === null ? rock.start.x : center.x;
    var y = center === null ? rock.start.y : center.y;
    NODES.holdRing.visible = true;
    NODES.holdRing.position.set(x, y);
    var pulse = REDUCED_MOTION ? 1.0 : 1.0 + Math.sin(ACTIVE_TIME / 200) * 0.08;
    NODES.holdRing.scale.set(0.6 * pulse, 0.6 * pulse);
    NODES.holdRing.alpha = 0.5 + Math.sin(ACTIVE_TIME / 250) * 0.2;
  }

  function syncBubbles() {
    var drift = REDUCED_MOTION ? 0 : ACTIVE_TIME / 3;
    var cycle = 170;
    var y = 330 - (drift % cycle);
    NODES.bubbles.position.set(250 + Math.sin(ACTIVE_TIME / 1600) * 10, y);
    NODES.bubbles.alpha = 0.7;
    NODES.bubbles.scale.set(0.8, 0.8);
  }

  function syncCaustic() {
    NODES.caustic.alpha = REDUCED_MOTION ? 0.3 : 0.28 + Math.sin(ACTIVE_TIME / 1500) * 0.1;
    NODES.caustic.position.x = WIDTH / 2 + Math.sin(ACTIVE_TIME / 2400) * 14;
  }

  function updateScene() {
    if (!NODES) {
      return;
    }
    var hover = REDUCED_MOTION ? 0 : Math.sin(ACTIVE_TIME / 900);
    NODES.water.position.y = HEIGHT / 2 + hover * 2;
    syncCrab(SNAPSHOT);
    syncRocks(SNAPSHOT);
    syncGrabber(SNAPSHOT);
    syncDropZone(SNAPSHOT);
    syncHoldRing(SNAPSHOT);
    syncBubbles();
    syncCaustic();
  }

  function render() {
    if (RenderRuntime && typeof RenderRuntime.renderSceneFrame === "function") {
      RenderRuntime.renderSceneFrame();
    }
  }

  function requestFrame() {
    if (!ACTIVE || PAUSED || ANIMATION_FRAME_ID !== null) {
      return;
    }
    if (typeof window.requestAnimationFrame !== "function") {
      ANIMATION_RUNNING = false;
      setSceneDiagnostics("active");
      return;
    }
    ANIMATION_RUNNING = true;
    ANIMATION_FRAME_ID = window.requestAnimationFrame(animationFrame);
  }

  function animationFrame(timestamp) {
    ANIMATION_FRAME_ID = null;
    if (!ACTIVE || PAUSED || !MOUNTED) {
      return;
    }
    if (LAST_TIMESTAMP !== null) {
      var delta = Math.max(0, Math.min(MAX_DELTA_MS, timestamp - LAST_TIMESTAMP));
      ACTIVE_TIME += delta;
    }
    LAST_TIMESTAMP = timestamp;
    updateScene();
    render();
    requestFrame();
  }

  function cancelFrame() {
    if (ANIMATION_FRAME_ID !== null && typeof window.cancelAnimationFrame === "function") {
      window.cancelAnimationFrame(ANIMATION_FRAME_ID);
    }
    ANIMATION_FRAME_ID = null;
    ANIMATION_RUNNING = false;
    LAST_TIMESTAMP = null;
  }

  function validateAliases() {
    MISSING_ALIASES = [];
    for (var i = 0; i < REQUIRED_ALIASES.length; i += 1) {
      if (!RenderRuntime.hasTexture(REQUIRED_ALIASES[i])) {
        MISSING_ALIASES.push(REQUIRED_ALIASES[i]);
      }
    }
    return MISSING_ALIASES.length === 0;
  }

  function prepare() {
    if (!RenderRuntime || !Crab || !RenderRuntime.isReady()) {
      setSceneDiagnostics("failed");
      throw new Error("Crab authored scene runtime is unavailable");
    }
    if (!validateAliases()) {
      setSceneDiagnostics("failed");
      throw new Error("Missing authored textures: " + MISSING_ALIASES.join(", "));
    }
    setReducedMotion();
    createSceneGraph();
    showOwnedNodes();
    MOUNTED = true;
    ACTIVE = false;
    PAUSED = false;
    SNAPSHOT = Crab.getSnapshot();
    POINTER_INTENT.active = false;
    RenderRuntime.setLegacyBridgeVisible(false);
    updateScene();
    render();
    setSceneDiagnostics("prepared");
    return true;
  }

  function activate() {
    if (!MOUNTED) {
      throw new Error("Crab authored scene is not prepared");
    }
    if (ACTIVE) {
      return true;
    }
    ACTIVE = true;
    PAUSED = false;
    SNAPSHOT = Crab.getSnapshot();
    LAST_TIMESTAMP = null;
    updateScene();
    render();
    requestFrame();
    setSceneDiagnostics("active");
    return true;
  }

  function sync(current, intent) {
    if (!MOUNTED || !current) {
      return false;
    }
    if (current.feedback !== LAST_FEEDBACK) {
      if (current.feedback === "success" && current.activeRockId) {
        FEEDBACK_STARTED_AT = ACTIVE_TIME;
      } else if (current.feedback === null) {
        FEEDBACK_STARTED_AT = ACTIVE_TIME;
      }
      LAST_FEEDBACK = current.feedback;
    }
    SNAPSHOT = current;
    if (intent && typeof intent === "object") {
      POINTER_INTENT.active = intent.active === true;
      POINTER_INTENT.x = isFinite(intent.x) ? intent.x : null;
      POINTER_INTENT.y = isFinite(intent.y) ? intent.y : null;
    } else {
      POINTER_INTENT.active = false;
      POINTER_INTENT.x = null;
      POINTER_INTENT.y = null;
    }
    updateScene();
    render();
    setSceneDiagnostics(ACTIVE ? "active" : "prepared");
    return true;
  }

  function pause() {
    if (!MOUNTED) {
      return;
    }
    PAUSED = true;
    cancelFrame();
    if (ACTIVE) {
      setSceneDiagnostics("paused");
    }
  }

  function resume() {
    if (!MOUNTED) {
      return;
    }
    PAUSED = false;
    LAST_TIMESTAMP = null;
    if (ACTIVE) {
      requestFrame();
      setSceneDiagnostics("active");
    }
  }

  function exit() {
    cancelFrame();
    ACTIVE = false;
    PAUSED = false;
    MOUNTED = false;
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
    if (NODES && RenderRuntime) {
      removeOwnedChild(RenderRuntime.getContainer("farBackground"), NODES.water);
      removeOwnedChild(RenderRuntime.getContainer("midground"), NODES.reef);
      removeOwnedChild(RenderRuntime.getContainer("midground"), NODES.caustic);
      removeOwnedChild(RenderRuntime.getContainer("gameplayWorld"), NODES.sandPath);
      removeOwnedChild(RenderRuntime.getContainer("foreground"), NODES.foreground);
      removeOwnedChild(RenderRuntime.getContainer("effects"), NODES.bubbles);
      removeOwnedChild(RenderRuntime.getContainer("gameplayWorld"), NODES.crabTrapped);
      removeOwnedChild(RenderRuntime.getContainer("gameplayWorld"), NODES.crabFree);
      for (var i = 0; i < NODES.rocks.length; i += 1) {
        removeOwnedChild(RenderRuntime.getContainer("gameplayWorld"), NODES.rocks[i]);
      }
      removeOwnedChild(RenderRuntime.getContainer("gameplayWorld"), NODES.grabberBase);
      removeOwnedChild(RenderRuntime.getContainer("gameplayWorld"), NODES.grabberArm);
      removeOwnedChild(RenderRuntime.getContainer("gameplayWorld"), NODES.grabberClawOpen);
      removeOwnedChild(RenderRuntime.getContainer("gameplayWorld"), NODES.grabberClawClosed);
      removeOwnedChild(RenderRuntime.getContainer("gameplayWorld"), NODES.dropZone);
      removeOwnedChild(RenderRuntime.getContainer("effects"), NODES.holdRing);
    }
    NODES = null;
    MOUNTED = false;
    ACTIVE = false;
    PAUSED = false;
    setSceneDiagnostics("unmounted");
  }

  function getDiagnostics() {
    var current = SNAPSHOT || { completedRockIds: [], activeRockId: null };
    return Object.freeze({
      mounted: MOUNTED,
      active: ACTIVE,
      paused: PAUSED,
      nodeCount: nodeCount(),
      activeRockId: current.activeRockId || null,
      completedCount: current.completedRockIds.length,
      crabState: crabState(current),
      grabbed: !!current.grabbed,
      feedback: current.feedback || "none",
      animationRunning: ANIMATION_RUNNING,
      legacyBridgeVisible: RenderRuntime && typeof RenderRuntime.getLegacyBridgeVisible === "function"
        ? RenderRuntime.getLegacyBridgeVisible()
        : true,
      requiredAliasCount: REQUIRED_ALIASES.length,
      missingAliases: Object.freeze(MISSING_ALIASES.slice())
    });
  }

  root.CrabScene = Object.freeze({
    prepare: prepare,
    activate: activate,
    sync: sync,
    pause: pause,
    resume: resume,
    exit: exit,
    destroy: destroy,
    isMounted: function () { return MOUNTED; },
    getDiagnostics: getDiagnostics,
    REQUIRED_ALIASES: Object.freeze(REQUIRED_ALIASES.slice())
  });
})();
