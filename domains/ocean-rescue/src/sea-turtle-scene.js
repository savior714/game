(function () {
  "use strict";

  var root = window.OceanRescue = window.OceanRescue || {};
  var RenderRuntime = root.RenderRuntime || null;
  var SeaTurtle = root.SeaTurtle || null;
  var REQUIRED_ALIASES = [
    "scene.water.far",
    "scene.reef.mid",
    "scene.coral.foreground",
    "scene.submarine",
    "scene.seaweed-loop.01",
    "scene.sand-path",
    "scene.passage",
    "otter.tail",
    "otter.arm.far",
    "otter.torso",
    "otter.head",
    "otter.eyes.open",
    "otter.eyes.closed",
    "otter.mouth.neutral",
    "otter.mouth.concern",
    "otter.mouth.smile",
    "otter.arm.near",
    "turtle.worried",
    "turtle.free",
    "ui.drag-arrow",
    "fx.success-burst",
    "fx.cut-ring",
    "fx.cut-icon",
    "fx.bubbles",
    "fx.caustic",
    "hud.progress-cap",
    "hud.loop-icon"
  ];

  var WIDTH = 1280;
  var HEIGHT = 720;
  var MAX_DELTA_MS = 50;
  var FEEDBACK_MOTION_MS = 400;
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
  var pointerIntent = { active: false, x: null, y: null };
  var missingAliases = [];
  var feedbackStartedAt = 0;
  var lastFeedback = null;
  var lastSuccessRopeId = null;

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
    setDiagnostic("data-sea-turtle-scene", status);
    setDiagnostic("data-sea-turtle-scene-node-count", nodes ? nodeCount() : 0);
    setDiagnostic("data-sea-turtle-scene-loop-count", 3);
    setDiagnostic("data-sea-turtle-scene-relief", reliefStage(snapshot));
    setDiagnostic(
      "data-sea-turtle-scene-active-rope",
      snapshot && snapshot.activeRopeId ? snapshot.activeRopeId : ""
    );
    setDiagnostic(
      "data-sea-turtle-scene-animation",
      paused && mounted ? "paused" : animationRunning ? "running" : "stopped"
    );
    setDiagnostic(
      "data-sea-turtle-scene-legacy-visible",
      RenderRuntime && typeof RenderRuntime.getLegacyBridgeVisible === "function"
        ? RenderRuntime.getLegacyBridgeVisible()
        : true
    );
  }

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

  function spriteCount() {
    return nodes ? 31 : 0;
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
    var turtleAndObstacle = RenderRuntime.getContainer("turtleAndObstacle");
    var seaOtterRig = RenderRuntime.getContainer("seaOtterRig");
    var foreground = RenderRuntime.getContainer("foreground");
    var effects = RenderRuntime.getContainer("effects");
    var hud = RenderRuntime.getContainer("hud");
    if (!far || !mid || !gameplayWorld || !submarine || !turtleAndObstacle || !seaOtterRig || !foreground || !effects || !hud) {
      throw new Error("Missing canonical authored scene container");
    }

    nodes = {
      water: makeSprite("scene.water.far", "sea-turtle-water-far"),
      reef: makeSprite("scene.reef.mid", "sea-turtle-reef-mid"),
      passage: makeSprite("scene.passage", "sea-turtle-passage"),
      caustic: makeSprite("fx.caustic", "sea-turtle-caustic"),
      sandPath: makeSprite("scene.sand-path", "sea-turtle-sand-path"),
      foreground: makeSprite("scene.coral.foreground", "sea-turtle-coral-foreground"),
      submarine: makeSprite("scene.submarine", "sea-turtle-submarine"),
      loops: [],
      turtleWorried: makeSprite("turtle.worried", "sea-turtle-worried"),
      turtleFree: makeSprite("turtle.free", "sea-turtle-free"),
      otterTail: makeSprite("otter.tail", "sea-otter-tail"),
      otterArmFar: makeSprite("otter.arm.far", "sea-otter-arm-far"),
      otterTorso: makeSprite("otter.torso", "sea-otter-torso"),
      otterHead: makeSprite("otter.head", "sea-otter-head"),
      otterEyesOpen: makeSprite("otter.eyes.open", "sea-otter-eyes-open"),
      otterEyesClosed: makeSprite("otter.eyes.closed", "sea-otter-eyes-closed"),
      otterMouthNeutral: makeSprite("otter.mouth.neutral", "sea-otter-mouth-neutral"),
      otterMouthConcern: makeSprite("otter.mouth.concern", "sea-otter-mouth-concern"),
      otterMouthSmile: makeSprite("otter.mouth.smile", "sea-otter-mouth-smile"),
      otterArmNear: makeSprite("otter.arm.near", "sea-otter-arm-near"),
      dragArrow: makeSprite("ui.drag-arrow", "sea-turtle-drag-arrow"),
      cutRing: makeSprite("fx.cut-ring", "sea-turtle-cut-ring"),
      cutIcon: makeSprite("fx.cut-icon", "sea-turtle-cut-icon"),
      bubbles: makeSprite("fx.bubbles", "sea-turtle-bubbles"),
      successBurst: makeSprite("fx.success-burst", "sea-turtle-success-burst"),
      hudCap: makeSprite("hud.progress-cap", "sea-turtle-hud-cap"),
      hudLoops: []
    };
    for (var i = 0; i < 3; i += 1) {
      nodes.loops.push(makeSprite("scene.seaweed-loop.01", "sea-turtle-loop-" + (i + 1)));
    }
    for (var h = 0; h < 3; h += 1) {
      nodes.hudLoops.push(makeSprite("hud.loop-icon", "sea-turtle-hud-loop-" + (h + 1)));
    }

    addChild(far, nodes.water);
    addChild(mid, nodes.reef);
    addChild(mid, nodes.passage);
    addChild(mid, nodes.caustic);
    gameplayWorld.addChildAt(nodes.sandPath, 0);
    addChild(submarine, nodes.submarine);
    addChild(turtleAndObstacle, nodes.turtleWorried);
    addChild(turtleAndObstacle, nodes.turtleFree);
    for (var loopIndex = 0; loopIndex < nodes.loops.length; loopIndex += 1) {
      addChild(turtleAndObstacle, nodes.loops[loopIndex]);
    }
    addChild(seaOtterRig, nodes.otterTail);
    addChild(seaOtterRig, nodes.otterArmFar);
    addChild(seaOtterRig, nodes.otterTorso);
    addChild(seaOtterRig, nodes.otterHead);
    addChild(seaOtterRig, nodes.otterEyesOpen);
    addChild(seaOtterRig, nodes.otterEyesClosed);
    addChild(seaOtterRig, nodes.otterMouthNeutral);
    addChild(seaOtterRig, nodes.otterMouthConcern);
    addChild(seaOtterRig, nodes.otterMouthSmile);
    addChild(seaOtterRig, nodes.otterArmNear);
    addChild(foreground, nodes.foreground);
    addChild(effects, nodes.dragArrow);
    addChild(effects, nodes.cutRing);
    addChild(effects, nodes.cutIcon);
    addChild(effects, nodes.bubbles);
    addChild(effects, nodes.successBurst);
    addChild(hud, nodes.hudCap);
    for (var hudIndex = 0; hudIndex < nodes.hudLoops.length; hudIndex += 1) {
      addChild(hud, nodes.hudLoops[hudIndex]);
    }

    layoutStaticNodes();
  }

  function layoutStaticNodes() {
    setPosition(nodes.water, WIDTH / 2, HEIGHT / 2);
    setScale(nodes.water, 3.2, 2.4);
    nodes.water.alpha = 1;

    setPosition(nodes.reef, WIDTH / 2, 500);
    setScale(nodes.reef, 1.4, 0.85);
    nodes.reef.alpha = 0.6;

    setPosition(nodes.passage, 1200, 330);
    setScale(nodes.passage, 0.85, 0.85);
    nodes.passage.alpha = 1;

    setPosition(nodes.caustic, WIDTH / 2, 300);
    setScale(nodes.caustic, 1.6, 1.3);
    nodes.caustic.alpha = 0.4;

    setPosition(nodes.sandPath, WIDTH / 2, HEIGHT);
    setScale(nodes.sandPath, 1, 1);
    nodes.sandPath.alpha = 1;

    setPosition(nodes.foreground, WIDTH / 2, 790);
    setScale(nodes.foreground, 1, 1);
    nodes.foreground.alpha = 0.9;

    setPosition(nodes.submarine, 220, 390);
    setScale(nodes.submarine, 1, 1);

    setPosition(nodes.turtleWorried, 950, 430);
    setPosition(nodes.turtleFree, 950, 430);
    setScale(nodes.turtleWorried, 0.95, 0.95);
    setScale(nodes.turtleFree, 0.95, 0.95);

    setPosition(nodes.otterTail, -94, 38);
    setPosition(nodes.otterArmFar, -73, -4);
    setPosition(nodes.otterTorso, 0, 22);
    setPosition(nodes.otterHead, 0, -42);
    setPosition(nodes.otterEyesOpen, 0, -55);
    setPosition(nodes.otterEyesClosed, 0, -55);
    setPosition(nodes.otterMouthNeutral, 0, -15);
    setPosition(nodes.otterMouthConcern, 0, -15);
    setPosition(nodes.otterMouthSmile, 0, -15);
    setPosition(nodes.otterArmNear, 73, -4);
    setScale(nodes.otterTail, 0.62, 0.62);
    setScale(nodes.otterArmFar, 0.62, 0.62);
    setScale(nodes.otterTorso, 0.62, 0.62);
    setScale(nodes.otterHead, 0.62, 0.62);
    setScale(nodes.otterEyesOpen, 0.62, 0.62);
    setScale(nodes.otterEyesClosed, 0.62, 0.62);
    setScale(nodes.otterMouthNeutral, 0.62, 0.62);
    setScale(nodes.otterMouthConcern, 0.62, 0.62);
    setScale(nodes.otterMouthSmile, 0.62, 0.62);
    setScale(nodes.otterArmNear, 0.62, 0.62);
    var rig = RenderRuntime.getContainer("seaOtterRig");
    setPosition(rig, 590, 420);

    setPosition(nodes.bubbles, 250, 330);
    setScale(nodes.bubbles, 0.8, 0.8);
    nodes.bubbles.alpha = 0.75;

    setPosition(nodes.hudCap, 150, 48);
    setScale(nodes.hudCap, 1, 1);
    for (var h = 0; h < nodes.hudLoops.length; h += 1) {
      setPosition(nodes.hudLoops[h], 96 + h * 54, 48);
      setScale(nodes.hudLoops[h], 0.9, 0.9);
    }

    nodes.dragArrow.visible = false;
    nodes.successBurst.visible = false;
    nodes.cutRing.visible = false;
    nodes.cutIcon.visible = false;
    nodes.turtleFree.visible = false;
    nodes.otterEyesClosed.visible = false;
    nodes.otterMouthConcern.visible = false;
    nodes.otterMouthSmile.visible = false;
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

  function ropeById(ropeId) {
    if (!SeaTurtle || !Array.isArray(SeaTurtle.Ropes)) {
      return null;
    }
    for (var i = 0; i < SeaTurtle.Ropes.length; i += 1) {
      if (SeaTurtle.Ropes[i].id === ropeId) {
        return SeaTurtle.Ropes[i];
      }
    }
    return null;
  }

  function reliefStage(current) {
    if (!current) {
      return "worried";
    }
    if (current.complete || current.completedRopeIds.length >= 3) {
      return "free";
    }
    if (current.completedRopeIds.length >= 2) {
      return "relief-2";
    }
    if (current.completedRopeIds.length >= 1) {
      return "relief-1";
    }
    return "worried";
  }

  function setFace(eyesClosed, mouth) {
    nodes.otterEyesOpen.visible = !eyesClosed;
    nodes.otterEyesClosed.visible = eyesClosed;
    nodes.otterMouthNeutral.visible = mouth === "neutral";
    nodes.otterMouthConcern.visible = mouth === "concern";
    nodes.otterMouthSmile.visible = mouth === "smile";
  }

  function syncTurtle(current) {
    var stage = reliefStage(current);
    var tenseRotation = stage === "worried" ? -0.035 : stage === "relief-1" ? -0.015 : 0;
    var free = stage === "free";
    nodes.turtleWorried.visible = !free;
    nodes.turtleFree.visible = free;
    if (stage === "worried") {
      nodes.turtleWorried.alpha = 1;
      nodes.turtleFree.alpha = 0;
    } else if (stage === "relief-1") {
      nodes.turtleWorried.alpha = 0.72;
      nodes.turtleFree.alpha = 0.28;
    } else if (stage === "relief-2") {
      nodes.turtleWorried.alpha = 0.38;
      nodes.turtleFree.alpha = 0.62;
    } else {
      nodes.turtleWorried.alpha = 0;
      nodes.turtleFree.alpha = 1;
    }
    nodes.turtleWorried.rotation = tenseRotation;
    nodes.turtleFree.rotation = free ? 0.02 : 0;
    nodes.turtleFree.position.y = free ? 414 : 430;
    var breathe = reducedMotion ? 1 : 1 + Math.sin(activeTime / 1500) * 0.015;
    nodes.turtleWorried.scale.set(0.95 * breathe, 0.95 * breathe);
    nodes.turtleFree.scale.set(0.95 * breathe, 0.95 * breathe);
  }

  function syncOtter(current) {
    var success = current && (current.complete || current.feedback === "success" && current.completedRopeIds.length >= 3);
    var concern = current && current.feedback === "failure";
    var pulling = current && pointerIntent.active;
    var reaching = current && current.activeRopeId !== null;
    var mouth = success ? "smile" : concern ? "concern" : "neutral";
    var closed = !reducedMotion && active && Math.floor(activeTime % 4200) >= 3900;
    setFace(closed, mouth);
    nodes.otterArmFar.rotation = reaching ? -0.08 : 0;
    nodes.otterArmNear.rotation = success ? -0.55 : pulling ? 0.38 : reaching ? 0.16 : 0;
    nodes.otterTorso.rotation = pulling ? -0.035 : success ? -0.02 : 0;
    nodes.otterHead.rotation = concern ? 0.035 : success ? -0.025 : 0;
  }

  function loopBasePosition(rope) {
    return {
      x: (rope.start.x + rope.end.x) / 2,
      y: (rope.start.y + rope.end.y) / 2
    };
  }

  function syncLoops(current) {
    var activeRopeId = current ? current.activeRopeId : null;
    var feedback = current ? current.feedback : null;
    for (var i = 0; i < nodes.loops.length; i += 1) {
      var loop = nodes.loops[i];
      var rope = SeaTurtle.Ropes[i];
      var base = loopBasePosition(rope);
      var completed = current && current.completedRopeIds.indexOf(rope.id) !== -1;
      var isActive = activeRopeId === rope.id;
      loop.visible = !completed || (isActive && feedback === "success");
      loop.alpha = isActive ? 1 : 0.58;
      loop.tint = isActive ? 0xffffb0 : 0x6f9d91;
      loop.scale.set(0.58, 0.58);
      loop.rotation = Math.atan2(rope.end.y - rope.start.y, rope.end.x - rope.start.x);
      loop.position.set(base.x, base.y);
      if (isActive && feedback === "failure") {
        loop.tint = 0xff6b6b;
        if (!reducedMotion) {
          loop.position.x += Math.sin(activeTime / 26) * 7;
        }
      }
      if (isActive && feedback === "success") {
        var successProgress = Math.min(1, Math.max(0, (activeTime - feedbackStartedAt) / FEEDBACK_MOTION_MS));
        loop.position.x += (rope.end.x - rope.start.x) * successProgress * 0.22;
        loop.position.y += (rope.end.y - rope.start.y) * successProgress * 0.22;
        loop.alpha = 1 - successProgress;
      }
      if (isActive && pointerIntent.active && finite(pointerIntent.x) && finite(pointerIntent.y)) {
        loop.position.x += Math.max(-24, Math.min(24, (pointerIntent.x - base.x) * 0.18));
        loop.position.y += Math.max(-24, Math.min(24, (pointerIntent.y - base.y) * 0.18));
      }
      if (isActive && !reducedMotion && feedback === null) {
        var pulse = 1 + Math.sin(activeTime / 260) * 0.035;
        loop.scale.set(0.58 * pulse, 0.58 * pulse);
      }
    }
    var activeRope = ropeById(activeRopeId);
    nodes.dragArrow.visible = !!activeRopeId && !!current && current.feedback !== "success";
    if (activeRope && nodes.dragArrow.visible) {
      var dx = activeRope.end.x - activeRope.start.x;
      var dy = activeRope.end.y - activeRope.start.y;
      nodes.dragArrow.position.set(
        activeRope.start.x + dx * 0.22,
        activeRope.start.y + dy * 0.22
      );
      nodes.dragArrow.rotation = Math.atan2(dy, dx);
      var help = current.helpLevel || 0;
      nodes.dragArrow.alpha = 0.38 + help * 0.18;
      var arrowScale = 0.42 + help * 0.06;
      nodes.dragArrow.scale.set(arrowScale, arrowScale);
      nodes.dragArrow.tint = 0xffe19a;
    }
    var burstRopeId = feedback === "success" ? activeRopeId : null;
    nodes.successBurst.visible = !!burstRopeId;
    if (burstRopeId) {
      var burstRope = ropeById(burstRopeId);
      var burstProgress = Math.min(1, Math.max(0, (activeTime - feedbackStartedAt) / FEEDBACK_MOTION_MS));
      nodes.successBurst.position.set(burstRope.end.x, burstRope.end.y);
      nodes.successBurst.alpha = 1 - burstProgress * 0.55;
      nodes.successBurst.scale.set(0.26 + burstProgress * 0.12, 0.26 + burstProgress * 0.12);
    }
  }

  function syncCutPoint(current) {
    var activeRopeId = current ? current.activeRopeId : null;
    var feedback = current ? current.feedback : null;
    var activeRope = ropeById(activeRopeId);
    var show = !!activeRope && feedback !== "success";
    nodes.cutRing.visible = show;
    nodes.cutIcon.visible = show;
    if (show) {
      nodes.cutRing.position.set(activeRope.end.x, activeRope.end.y);
      var ringPulse = reducedMotion ? 1 : 1 + Math.sin(activeTime / 240) * 0.07;
      nodes.cutRing.scale.set(ringPulse, ringPulse);
      nodes.cutRing.alpha = reducedMotion ? 0.9 : 0.9 + Math.sin(activeTime / 300) * 0.1;
      nodes.cutIcon.position.set(activeRope.end.x - 40, activeRope.end.y + 28);
      nodes.cutIcon.scale.set(0.7, 0.7);
      nodes.cutIcon.rotation = reducedMotion ? 0 : Math.sin(activeTime / 700) * 0.06;
    }
  }

  function syncBubbles() {
    var drift = reducedMotion ? 0 : activeTime / 3;
    var cycle = 170;
    var y = 330 - (drift % cycle);
    nodes.bubbles.position.set(250 + Math.sin(activeTime / 1600) * 10, y);
    nodes.bubbles.alpha = 0.75;
    nodes.bubbles.scale.set(0.8, 0.8);
  }

  function syncCaustic() {
    nodes.caustic.alpha = reducedMotion ? 0.35 : 0.3 + Math.sin(activeTime / 1500) * 0.12;
    nodes.caustic.position.x = WIDTH / 2 + Math.sin(activeTime / 2400) * 14;
  }

  function syncHud(current) {
    var activeRopeId = current ? current.activeRopeId : null;
    var feedback = current ? current.feedback : null;
    for (var i = 0; i < nodes.hudLoops.length; i += 1) {
      var icon = nodes.hudLoops[i];
      var rope = SeaTurtle.Ropes[i];
      var completed = current && current.completedRopeIds.indexOf(rope.id) !== -1;
      var isActive = activeRopeId === rope.id && feedback !== "success";
      if (completed) {
        icon.tint = 0xffc94d;
        icon.alpha = 1;
        icon.scale.set(0.9, 0.9);
      } else if (isActive) {
        icon.tint = 0xffc94d;
        icon.alpha = 0.95;
        var hudPulse = reducedMotion ? 1 : 1 + Math.sin(activeTime / 240) * 0.1;
        icon.scale.set(0.9 * hudPulse, 0.9 * hudPulse);
      } else {
        icon.tint = 0x7fb2c4;
        icon.alpha = 0.7;
        icon.scale.set(0.9, 0.9);
      }
    }
  }

  function updateScene() {
    if (!nodes) {
      return;
    }
    var hover = reducedMotion ? 0 : Math.sin(activeTime / 900);
    var rig = RenderRuntime.getContainer("seaOtterRig");
    var submarine = nodes.submarine;
    setPosition(submarine, 220, 390 + hover * 4);
    rig.position.y = 420 + hover * 3;
    syncTurtle(snapshot);
    syncOtter(snapshot);
    syncLoops(snapshot);
    syncCutPoint(snapshot);
    syncBubbles();
    syncCaustic();
    syncHud(snapshot);
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
    if (!RenderRuntime || !SeaTurtle || !RenderRuntime.isReady()) {
      setSceneDiagnostics("failed");
      throw new Error("Sea-turtle authored scene runtime is unavailable");
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
    snapshot = SeaTurtle.getSnapshot();
    pointerIntent.active = false;
    RenderRuntime.setLegacyBridgeVisible(false);
    updateScene();
    render();
    setSceneDiagnostics("prepared");
    return true;
  }

  function activate() {
    if (!mounted) {
      throw new Error("Sea-turtle authored scene is not prepared");
    }
    if (active) {
      return true;
    }
    active = true;
    paused = false;
    snapshot = SeaTurtle.getSnapshot();
    lastTimestamp = null;
    updateScene();
    render();
    requestFrame();
    setSceneDiagnostics("active");
    return true;
  }

  function sync(current, intent) {
    if (!mounted || !current) {
      return false;
    }
    if (current.feedback !== lastFeedback) {
      if (current.feedback === "success" && current.activeRopeId) {
        lastSuccessRopeId = current.activeRopeId;
        feedbackStartedAt = activeTime;
      } else if (current.feedback === null) {
        feedbackStartedAt = activeTime;
      }
      lastFeedback = current.feedback;
    }
    if (current.feedback === "success" && current.activeRopeId) {
      lastSuccessRopeId = current.activeRopeId;
    }
    snapshot = current;
    if (intent && typeof intent === "object") {
      pointerIntent.active = intent.active === true;
      pointerIntent.x = finite(intent.x) ? intent.x : null;
      pointerIntent.y = finite(intent.y) ? intent.y : null;
    } else {
      pointerIntent.active = false;
      pointerIntent.x = null;
      pointerIntent.y = null;
    }
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
      removeOwnedChild(RenderRuntime.getContainer("farBackground"), nodes.water);
      removeOwnedChild(RenderRuntime.getContainer("midground"), nodes.reef);
      removeOwnedChild(RenderRuntime.getContainer("midground"), nodes.passage);
      removeOwnedChild(RenderRuntime.getContainer("midground"), nodes.caustic);
      removeOwnedChild(RenderRuntime.getContainer("gameplayWorld"), nodes.sandPath);
      removeOwnedChild(RenderRuntime.getContainer("submarine"), nodes.submarine);
      removeOwnedChild(RenderRuntime.getContainer("turtleAndObstacle"), nodes.turtleWorried);
      removeOwnedChild(RenderRuntime.getContainer("turtleAndObstacle"), nodes.turtleFree);
      for (var i = 0; i < nodes.loops.length; i += 1) {
        removeOwnedChild(RenderRuntime.getContainer("turtleAndObstacle"), nodes.loops[i]);
      }
      var rig = RenderRuntime.getContainer("seaOtterRig");
      removeOwnedChild(rig, nodes.otterTail);
      removeOwnedChild(rig, nodes.otterArmFar);
      removeOwnedChild(rig, nodes.otterTorso);
      removeOwnedChild(rig, nodes.otterHead);
      removeOwnedChild(rig, nodes.otterEyesOpen);
      removeOwnedChild(rig, nodes.otterEyesClosed);
      removeOwnedChild(rig, nodes.otterMouthNeutral);
      removeOwnedChild(rig, nodes.otterMouthConcern);
      removeOwnedChild(rig, nodes.otterMouthSmile);
      removeOwnedChild(rig, nodes.otterArmNear);
      removeOwnedChild(RenderRuntime.getContainer("foreground"), nodes.foreground);
      removeOwnedChild(RenderRuntime.getContainer("effects"), nodes.dragArrow);
      removeOwnedChild(RenderRuntime.getContainer("effects"), nodes.cutRing);
      removeOwnedChild(RenderRuntime.getContainer("effects"), nodes.cutIcon);
      removeOwnedChild(RenderRuntime.getContainer("effects"), nodes.bubbles);
      removeOwnedChild(RenderRuntime.getContainer("effects"), nodes.successBurst);
      removeOwnedChild(RenderRuntime.getContainer("hud"), nodes.hudCap);
      for (var hudIndex = 0; hudIndex < nodes.hudLoops.length; hudIndex += 1) {
        removeOwnedChild(RenderRuntime.getContainer("hud"), nodes.hudLoops[hudIndex]);
      }
    }
    nodes = null;
    mounted = false;
    active = false;
    paused = false;
    setSceneDiagnostics("unmounted");
  }

  function getDiagnostics() {
    var current = snapshot || { completedRopeIds: [], activeRopeId: null };
    return Object.freeze({
      mounted: mounted,
      active: active,
      paused: paused,
      nodeCount: nodeCount(),
      spriteCount: spriteCount(),
      loopCount: 3,
      activeRopeId: current.activeRopeId || null,
      completedCount: current.completedRopeIds.length,
      reliefStage: reliefStage(current),
      animationRunning: animationRunning,
      legacyBridgeVisible: RenderRuntime && typeof RenderRuntime.getLegacyBridgeVisible === "function"
        ? RenderRuntime.getLegacyBridgeVisible()
        : true,
      requiredAliasCount: REQUIRED_ALIASES.length,
      missingAliases: Object.freeze(missingAliases.slice())
    });
  }

  root.SeaTurtleScene = Object.freeze({
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
