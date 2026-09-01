(function () {
  "use strict";

  const root = window.OceanRescue = window.OceanRescue || {};
  const RenderRuntime = root.RenderRuntime || null;
  const SeaTurtleDiscovery = root.SeaTurtleDiscovery || null;

  let discoveryContainer = null;
  let turtleContainer = null;
  let turtleSprite = null;
  let ropesGraphics = null;
  let scanBeamGraphics = null;
  let bubblesSprite = null;
  let mounted = false;
  let lastReactionState = null;
  let bubblePuffTimer = 0;

  function getRootElement() {
    return document.getElementById("ocean-rescue-root");
  }

  function setDiagnostic(name, value) {
    const element = getRootElement();
    if (element) {
      element.setAttribute(name, String(value));
    }
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

  function installDiscoveryPresentation() {
    if (discoveryContainer) {
      discoveryContainer.visible = true;
      mounted = true;
      return;
    }

    if (!RenderRuntime || !RenderRuntime.isReady()) {
      return;
    }

    const sceneContainer = RenderRuntime.getContainer("scene") || RenderRuntime.getContainer("submarine");
    if (!sceneContainer) {
      return;
    }

    const turtleTexture = RenderRuntime.getTexture("turtle.worried");
    const bubblesTexture = RenderRuntime.getTexture("fx.bubbles");
    if (!turtleTexture) {
      return;
    }

    discoveryContainer = new PIXI.Container();
    discoveryContainer.label = "travel-sea-turtle-discovery";
    discoveryContainer.name = "travel-sea-turtle-discovery";
    discoveryContainer.visible = false;

    turtleContainer = new PIXI.Container();
    turtleContainer.label = "turtle-actor";
    turtleContainer.position.set(960, 360);

    turtleSprite = new PIXI.Sprite(turtleTexture);
    turtleSprite.label = "turtle-sprite";
    applyTrimAnchor(turtleSprite, turtleTexture);
    turtleSprite.scale.set(0.85, 0.85);
    turtleContainer.addChild(turtleSprite);

    // Ropes Graphics representing the 3 entangled ropes
    ropesGraphics = new PIXI.Graphics();
    ropesGraphics.label = "turtle-discovery-ropes";
    turtleContainer.addChild(ropesGraphics);

    // Bubble puff effect for startled reaction
    if (bubblesTexture) {
      bubblesSprite = new PIXI.Sprite(bubblesTexture);
      bubblesSprite.label = "turtle-startled-bubbles";
      applyTrimAnchor(bubblesSprite, bubblesTexture);
      bubblesSprite.scale.set(0.35, 0.35);
      bubblesSprite.position.set(-60, -30);
      bubblesSprite.alpha = 0;
      turtleContainer.addChild(bubblesSprite);
    }

    // Scan beam overlay
    scanBeamGraphics = new PIXI.Graphics();
    scanBeamGraphics.label = "turtle-scan-beam";
    scanBeamGraphics.visible = false;
    turtleContainer.addChild(scanBeamGraphics);

    discoveryContainer.addChild(turtleContainer);
    sceneContainer.addChild(discoveryContainer);

    mounted = true;
    setDiagnostic("data-turtle-discovery-presentation", "ready");
  }

  function removeDiscoveryPresentation() {
    if (discoveryContainer && discoveryContainer.parent) {
      discoveryContainer.parent.removeChild(discoveryContainer);
    }
    discoveryContainer = null;
    turtleContainer = null;
    turtleSprite = null;
    ropesGraphics = null;
    scanBeamGraphics = null;
    bubblesSprite = null;
    mounted = false;
  }

  function renderRopes(reactionState, scanProgress, readyForRescue, time) {
    if (!ropesGraphics) {
      return;
    }
    ropesGraphics.clear();

    const isStartled = reactionState === "startled";
    const isScanning = reactionState === "scanning";
    const isReady = readyForRescue || reactionState === "ready-for-rescue";

    // 3 canonical rope paths relative to turtle center
    const ropeDefs = [
      { id: 1, start: { x: -80, y: -45 }, cp: { x: -20, y: -70 }, end: { x: 80, y: -40 } },
      { id: 2, start: { x: -85, y: 0 }, cp: { x: -10, y: 25 }, end: { x: 85, y: 10 } },
      { id: 3, start: { x: -75, y: 45 }, cp: { x: -15, y: 65 }, end: { x: 75, y: 50 } }
    ];

    for (let i = 0; i < ropeDefs.length; i++) {
      const def = ropeDefs[i];
      let illuminated = false;
      if (isReady) {
        illuminated = true;
      } else if (isScanning) {
        // Sequentially illuminate as scan passes (0..0.33, 0.33..0.66, 0.66..1.0)
        if (scanProgress >= (i + 1) * 0.3) {
          illuminated = true;
        }
      }

      const twitchOffset = isStartled ? Math.sin(time * 0.03 + i * 2) * 4 : Math.sin(time * 0.003 + i) * 1.5;

      if (illuminated) {
        // Glowing gold / scan revealed rope
        ropesGraphics.setStrokeStyle({
          width: 5.5,
          color: 0xFFE57F,
          alpha: 0.95
        });
        ropesGraphics.beginPath();
        ropesGraphics.moveTo(def.start.x, def.start.y + twitchOffset);
        ropesGraphics.quadraticCurveTo(def.cp.x, def.cp.y + twitchOffset, def.end.x, def.end.y + twitchOffset);
        ropesGraphics.stroke();

        // Inner core
        ropesGraphics.setStrokeStyle({
          width: 2.5,
          color: 0xFFFFFF,
          alpha: 0.9
        });
        ropesGraphics.beginPath();
        ropesGraphics.moveTo(def.start.x, def.start.y + twitchOffset);
        ropesGraphics.quadraticCurveTo(def.cp.x, def.cp.y + twitchOffset, def.end.x, def.end.y + twitchOffset);
        ropesGraphics.stroke();
      } else {
        // Regular entangled rope
        const width = isStartled ? 4.5 : 3.5;
        const color = isStartled ? 0x8C4A2F : 0x544332;
        ropesGraphics.setStrokeStyle({
          width: width,
          color: color,
          alpha: 0.85
        });
        ropesGraphics.beginPath();
        ropesGraphics.moveTo(def.start.x, def.start.y + twitchOffset);
        ropesGraphics.quadraticCurveTo(def.cp.x, def.cp.y + twitchOffset, def.end.x, def.end.y + twitchOffset);
        ropesGraphics.stroke();
      }
    }
  }

  function renderScanBeam(scanProgress, active) {
    if (!scanBeamGraphics) {
      return;
    }
    if (!active) {
      scanBeamGraphics.visible = false;
      return;
    }
    scanBeamGraphics.visible = true;
    scanBeamGraphics.clear();

    const beamX = -130 + scanProgress * 260; // sweep from left (-130) to right (+130)

    // Beam cone / vertical sweep
    scanBeamGraphics.setFillStyle({
      color: 0x48CAE4,
      alpha: 0.28
    });
    scanBeamGraphics.beginPath();
    scanBeamGraphics.rect(beamX - 18, -100, 36, 200);
    scanBeamGraphics.fill();

    // Intense center line
    scanBeamGraphics.setStrokeStyle({
      width: 3,
      color: 0xADE8F4,
      alpha: 0.85
    });
    scanBeamGraphics.beginPath();
    scanBeamGraphics.moveTo(beamX, -100);
    scanBeamGraphics.lineTo(beamX, 100);
    scanBeamGraphics.stroke();
  }

  function sync(discoverySnapshot, travelSnapshot) {
    if (!mounted || !discoveryContainer) {
      installDiscoveryPresentation();
    }
    if (!discoveryContainer) {
      return;
    }

    if (!discoverySnapshot || !discoverySnapshot.active || discoverySnapshot.reactionState === "inactive") {
      discoveryContainer.visible = false;
      setDiagnostic("data-turtle-discovery-visible", "false");
      setDiagnostic("data-turtle-discovery-active", "false");
      setDiagnostic("data-turtle-discovery-reaction", "inactive");
      setDiagnostic("data-turtle-discovery-scan-eligible", "false");
      setDiagnostic("data-turtle-discovery-scanning", "false");
      setDiagnostic("data-turtle-discovery-ready", "false");
      return;
    }

    discoveryContainer.visible = true;
    const reaction = discoverySnapshot.reactionState;
    const distance = discoverySnapshot.distance || (travelSnapshot ? travelSnapshot.distance : 0);
    const now = performance.now();

    setDiagnostic("data-turtle-discovery-visible", "true");
    setDiagnostic("data-turtle-discovery-active", "true");
    setDiagnostic("data-turtle-discovery-reaction", reaction);
    setDiagnostic("data-turtle-discovery-scan-eligible", String(Boolean(discoverySnapshot.scanEligible)));
    setDiagnostic("data-turtle-discovery-scanning", String(Boolean(discoverySnapshot.scanning)));
    setDiagnostic("data-turtle-discovery-ready", String(Boolean(discoverySnapshot.readyForRescue)));

    const scanBtn = document.getElementById("ocean-rescue-travel-scan");
    if (scanBtn) {
      const showScan = Boolean(discoverySnapshot.scanEligible && !discoverySnapshot.scanning && !discoverySnapshot.readyForRescue);
      scanBtn.hidden = !showScan;
    }

    // Position turtle based on distance and hold
    // Distance 4800 (x=1150) -> 5800 (x=960)
    const holdProgress = Math.min(1.0, Math.max(0.0, (distance - 4800) / 1000));
    let targetX = 1150 - holdProgress * 190;
    let targetY = 360 + Math.sin(now * 0.002) * 14;
    let targetRotation = 0;
    let targetAlpha = 0.85 + holdProgress * 0.15;

    if (reaction === "distant") {
      targetRotation = Math.sin(now * 0.003) * 0.03;
    } else if (reaction === "awareness") {
      targetRotation = -0.06; // tilt gently toward GUP (left)
    } else if (reaction === "startled") {
      targetX += 28; // recoil backward
      targetRotation = 0.10; // flinch upward
      bubblePuffTimer = 300;
    } else if (reaction === "settling") {
      targetRotation = -0.04;
    } else if (reaction === "scan-eligible") {
      targetRotation = -0.04;
    } else if (reaction === "scanning") {
      targetRotation = -0.02;
      targetY += Math.sin(now * 0.005) * 4;
    } else if (reaction === "ready-for-rescue") {
      targetRotation = -0.03;
    }

    turtleContainer.position.set(targetX, targetY);
    turtleContainer.rotation = targetRotation;
    discoveryContainer.alpha = targetAlpha;

    // Handle bubble puff for startled
    if (bubblesSprite) {
      if (reaction === "startled" || bubblePuffTimer > 0) {
        bubblesSprite.alpha = 0.7;
        bubblesSprite.scale.set(0.4 + Math.sin(now * 0.01) * 0.05);
      } else {
        bubblesSprite.alpha = 0;
      }
    }

    renderRopes(reaction, discoverySnapshot.scanProgress, discoverySnapshot.readyForRescue, now);
    renderScanBeam(discoverySnapshot.scanProgress, discoverySnapshot.scanning);

    lastReactionState = reaction;
  }

  root.SeaTurtleDiscoveryPresentation = Object.freeze({
    install: installDiscoveryPresentation,
    remove: removeDiscoveryPresentation,
    sync: sync,
    isMounted: function () {
      return mounted;
    }
  });
})();
