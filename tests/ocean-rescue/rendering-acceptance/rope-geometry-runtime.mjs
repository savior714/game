// Sea turtle rope visual/hit geometry alignment runtime harness.
//
// Loads the published single HTML (/ocean-rescue/index.html) in a same-origin
// iframe and drives only the public OceanRescue runtime namespaces, then probes
// the retained PIXI nodes exposed through RenderRuntime.getContainer() to prove
// that the visible active rope stays on the canonical SeaTurtle.Ropes
// start/end axis (midpoint, rotation, cut ring, drag arrow) regardless of
// pointer intent, and that the input rules still resolve success/failure.
//
// All assertions are computed here as deltas against canonical ropes read from
// turtle.Ropes[i]; the Python runner asserts the deltas. No rope coordinates
// are hardcoded in this module.

const TASK_ID = 'AIDENGAME-OCEAN-RESCUE-SEA-TURTLE-ROPE-VISUAL-HIT-GEOMETRY-ALIGNMENT-01';
const IFRAME_SRC = '/ocean-rescue/index.html';
const READY_TIMEOUT_MS = 10000;
const REFERENCE_PREFIX = '/docs/reference/ocean-rescue/';

const diag = {
  schemaVersion: 1,
  taskId: TASK_ID,
  singleHtmlReady: false,
  renderRuntimeReady: false,
  selectedBackend: null,
  logicalWidth: null,
  logicalHeight: null,
  canvasRect: null,
  initial: null,
  pointerInactive: null,
  pointerActive: null,
  pointerInactiveAfter: null,
  traceSuccess: null,
  traceOffPath: null,
  tapSuccess: null,
  threeRope: null,
  cssScaled: null,
  externalOriginRequestCount: 0,
  externalOriginRequests: [],
  referenceImageRequestCount: 0,
  referenceImageRequests: [],
  uncaughtErrorCount: 0,
  unhandledRejectionCount: 0,
  securityPolicyViolationCount: 0,
  error: null,
  complete: false,
};

function writeDiagnostics() {
  const el = document.getElementById('diagnostics');
  if (el) {
    el.textContent = JSON.stringify(diag, null, 2);
  }
}

window.addEventListener('error', () => {
  diag.uncaughtErrorCount += 1;
  writeDiagnostics();
});

window.addEventListener('unhandledrejection', () => {
  diag.unhandledRejectionCount += 1;
  writeDiagnostics();
});

window.addEventListener('securitypolicyviolation', () => {
  diag.securityPolicyViolationCount += 1;
  writeDiagnostics();
});

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function iframeReady(frame) {
  try {
    const doc = frame.contentDocument;
    if (!doc || doc.readyState !== 'complete') {
      return false;
    }
    const win = frame.contentWindow;
    if (!win || !win.OceanRescue) {
      return false;
    }
    const runtime = win.OceanRescue.RenderRuntime;
    if (!runtime || typeof runtime.isReady !== 'function' || !runtime.isReady()) {
      return false;
    }
    const root = doc.getElementById('ocean-rescue-root');
    if (!root) {
      return false;
    }
    return (
      root.getAttribute('data-render-runtime') === 'ready' &&
      root.getAttribute('data-ocean-rescue-ready') === 'true'
    );
  } catch (_) {
    return false;
  }
}

async function waitForReady(frame) {
  const deadline = Date.now() + READY_TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (iframeReady(frame)) {
      return;
    }
    await sleep(50);
  }
  throw new Error('iframe runtime not ready within 10s');
}

function webglPreflight() {
  const names = ['webgl2', 'webgl'];
  const offscreen = document.createElement('canvas');
  for (const name of names) {
    try {
      const ctx = offscreen.getContext(name, { failIfMajorPerformanceCaveat: false });
      if (ctx) {
        diag.webglPreflightAvailable = true;
        diag.webglPreflightKind = name;
        if (ctx.getExtension && ctx.getExtension('WEBGL_lose_context')) {
          ctx.getExtension('WEBGL_lose_context').loseContext();
        }
        return;
      }
    } catch (_) {
      /* continue */
    }
  }
  diag.webglPreflightAvailable = false;
}

function collectNetwork() {
  const frame = document.getElementById('game-frame');
  const frames = frame && frame.contentWindow ? [window, frame.contentWindow] : [window];
  const externals = [];
  const references = [];
  const fixtureOrigin = window.location.origin;
  for (const win of frames) {
    let entries = [];
    try {
      entries = win.performance.getEntriesByType('resource');
    } catch (_) {
      entries = [];
    }
    for (const entry of entries) {
      try {
        const url = new URL(entry.name);
        if (url.protocol === 'data:' || url.protocol === 'blob:') {
          continue;
        }
        if (url.origin !== fixtureOrigin) {
          externals.push(entry.name);
        }
        if (entry.name.indexOf(REFERENCE_PREFIX) !== -1) {
          references.push(entry.name);
        }
      } catch (_) {
        /* skip unparseable */
      }
    }
  }
  diag.externalOriginRequests = externals;
  diag.externalOriginRequestCount = externals.length;
  diag.referenceImageRequests = references;
  diag.referenceImageRequestCount = references.length;
}

function rectOf(el) {
  if (!el || typeof el.getBoundingClientRect !== 'function') {
    return null;
  }
  const r = el.getBoundingClientRect();
  return { left: r.left, top: r.top, width: r.width, height: r.height };
}

function boundsOf(obj) {
  let error = null;
  try {
    obj.updateTransform();
    const b = obj.getBounds();
    let local = null;
    try {
      const lb = obj.getLocalBounds();
      local = { x: lb.x, y: lb.y, width: lb.width, height: lb.height };
    } catch (localError) {
      error = String((localError && localError.message) || localError);
    }
    return {
      x: b.x,
      y: b.y,
      width: b.width,
      height: b.height,
      local,
      anchor: obj.anchor ? { x: obj.anchor.x, y: obj.anchor.y } : null,
      error,
    };
  } catch (boundsError) {
    return {
      error: String((boundsError && boundsError.message) || boundsError),
      anchor: obj.anchor ? { x: obj.anchor.x, y: obj.anchor.y } : null,
    };
  }
}

function logicalToClient(canvas, x, y, logicalWidth, logicalHeight) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: rect.left + (x / logicalWidth) * rect.width,
    y: rect.top + (y / logicalHeight) * rect.height,
  };
}

function normalizeAngleDelta(delta) {
  return Math.atan2(Math.sin(delta), Math.cos(delta));
}

function run() {
  const frame = document.getElementById('game-frame');
  const win = frame.contentWindow;
  const game = win.OceanRescue;
  const turtle = game.SeaTurtle;
  const scene = game.SeaTurtleScene;

  function loopNode(index) {
    const container = game.RenderRuntime.getContainer('turtleAndObstacle');
    const name = 'sea-turtle-loop-' + (index + 1);
    for (const child of container.children) {
      if (child && child.name === name) {
        return child;
      }
    }
    return null;
  }

  function effectsNode(name) {
    const container = game.RenderRuntime.getContainer('effects');
    for (const child of container.children) {
      if (child && child.name === name) {
        return child;
      }
    }
    return null;
  }

  function activeRope() {
    const id = scene.getDiagnostics().activeRopeId;
    if (!id) {
      return null;
    }
    for (const rope of turtle.Ropes) {
      if (rope.id === id) {
        return rope;
      }
    }
    return null;
  }

  function ropeGeometry(i) {
    const rope = turtle.Ropes[i];
    const loop = loopNode(i);
    const midpoint = {
      x: (rope.start.x + rope.end.x) / 2,
      y: (rope.start.y + rope.end.y) / 2,
    };
    const canonicalAngle = Math.atan2(
      rope.end.y - rope.start.y,
      rope.end.x - rope.start.x,
    );
    const segmentLength = Math.hypot(
      rope.end.x - rope.start.x,
      rope.end.y - rope.start.y,
    );
    let centerDelta = NaN;
    let angleDelta = NaN;
    let loopTexture = null;
    let footprint = null;
    if (loop) {
      centerDelta = Math.hypot(
        loop.position.x - midpoint.x,
        loop.position.y - midpoint.y,
      );
      angleDelta = normalizeAngleDelta(loop.rotation - canonicalAngle);
      const tex = loop.texture;
      loopTexture = {
        width: tex ? tex.width : null,
        height: tex ? tex.height : null,
        origWidth: tex && tex.orig ? tex.orig.width : null,
        origHeight: tex && tex.orig ? tex.orig.height : null,
        frameWidth: tex && tex.frame ? tex.frame.width : null,
        frameHeight: tex && tex.frame ? tex.frame.height : null,
        frameOffsetX: tex && tex.frame ? tex.frame.x : null,
        frameOffsetY: tex && tex.frame ? tex.frame.y : null,
      };
      const anchor = loop.anchor || { x: 0.5, y: 0.5 };
      const sx = loop.scale ? loop.scale.x : 1;
      const sy = loop.scale ? loop.scale.y : 1;
      if (tex && tex.orig && tex.frame) {
        const anchorX = anchor.x * tex.orig.width;
        const anchorY = anchor.y * tex.orig.height;
        const localX = tex.frame.x - anchorX;
        const localY = tex.frame.y - anchorY;
        const centerX = localX + tex.frame.width / 2;
        const centerY = localY + tex.frame.height / 2;
        const rot = loop.rotation || 0;
        const worldCenterX = loop.position.x + Math.cos(rot) * centerX * sx;
        const worldCenterY = loop.position.y + Math.sin(rot) * centerY * sx;
        footprint = {
          frameWorldWidth: tex.frame.width * sx,
          frameWorldHeight: tex.frame.height * sy,
          frameWorldCenter: { x: worldCenterX, y: worldCenterY },
          anchor: { x: anchor.x, y: anchor.y },
          scale: { x: sx, y: sy },
        };
      }
    }
    return {
      ropeId: rope.id,
      start: { x: rope.start.x, y: rope.start.y },
      end: { x: rope.end.x, y: rope.end.y },
      midpoint,
      canonicalAngle,
      segmentLength,
      loopPresent: !!loop,
      loopVisible: loop ? loop.visible : null,
      loopCenter: loop ? { x: loop.position.x, y: loop.position.y } : null,
      loopRotation: loop ? loop.rotation : null,
      loopScale: loop ? { x: loop.scale.x, y: loop.scale.y } : null,
      loopBounds: loop ? boundsOf(loop) : null,
      footprint,
      loopTexture,
      centerDelta,
      angleDelta,
    };
  }

  function geometrySnapshot() {
    try {
      game.RenderRuntime.renderSceneFrame();
    } catch (_) {
      /* render probe is best effort */
    }
    const ropes = [];
    for (let i = 0; i < 3; i += 1) {
      ropes.push(ropeGeometry(i));
    }
    const cutRing = effectsNode('sea-turtle-cut-ring');
    const dragArrow = effectsNode('sea-turtle-drag-arrow');
    const active = activeRope();
    let cutRingEndDelta = NaN;
    if (cutRing && active) {
      cutRingEndDelta = Math.hypot(
        cutRing.position.x - active.end.x,
        cutRing.position.y - active.end.y,
      );
    }
    return {
      activeRopeId: scene.getDiagnostics().activeRopeId,
      ropes,
      cutRing: cutRing
        ? {
            position: { x: cutRing.position.x, y: cutRing.position.y },
            visible: cutRing.visible,
            endDelta: cutRingEndDelta,
          }
        : null,
      dragArrow: dragArrow
        ? {
            position: { x: dragArrow.position.x, y: dragArrow.position.y },
            rotation: dragArrow.rotation,
            visible: dragArrow.visible,
          }
        : null,
    };
  }

  function noIntent() {
    return { active: false, x: null, y: null };
  }

  function traceRope(rope, pointerId, deviant) {
    turtle.pointerDown(pointerId, rope.start.x, rope.start.y);
    const mid = {
      x: (rope.start.x + rope.end.x) / 2,
      y: (rope.start.y + rope.end.y) / 2,
    };
    turtle.pointerMove(pointerId, mid.x, mid.y);
    if (deviant) {
      turtle.pointerMove(pointerId, deviant.x, deviant.y);
      return turtle.pointerUp(pointerId, deviant.x, deviant.y);
    }
    turtle.pointerMove(pointerId, rope.end.x, rope.end.y);
    return turtle.pointerUp(pointerId, rope.end.x, rope.end.y);
  }

  // --- baseline scene state -------------------------------------------
  turtle.start();
  scene.prepare();
  scene.activate();
  scene.sync(turtle.getSnapshot(), noIntent());
  diag.initial = scene.getDiagnostics();
  diag.pointerInactive = geometrySnapshot();

  // --- pointer-active far intent on rope-1 ----------------------------
  const farIntent = {
    active: true,
    x: turtle.Ropes[0].start.x,
    y: turtle.Ropes[0].start.y + 120,
  };
  scene.sync(turtle.getSnapshot(), farIntent);
  diag.pointerActive = {
    intent: farIntent,
    activeRopeId: scene.getDiagnostics().activeRopeId,
    geometry: geometrySnapshot(),
  };
  scene.sync(turtle.getSnapshot(), noIntent());
  diag.pointerInactiveAfter = geometrySnapshot();

  // --- trace success on rope-1 ----------------------------------------
  const up1 = traceRope(turtle.Ropes[0], 1, null);
  scene.sync(turtle.getSnapshot(), noIntent());
  const during1 = geometrySnapshot();
  const fb1 = turtle.finishFeedback();
  scene.sync(turtle.getSnapshot(), noIntent());
  diag.traceSuccess = {
    result: up1,
    during: during1,
    feedback: fb1,
    afterAdvance: geometrySnapshot(),
    nextActiveRopeId: scene.getDiagnostics().activeRopeId,
  };

  // --- trace off-path failure on rope-2 -------------------------------
  const offPath = {
    x: turtle.Ropes[1].start.x + 100,
    y: turtle.Ropes[1].start.y - 200,
  };
  const up2 = traceRope(turtle.Ropes[1], 2, offPath);
  scene.sync(turtle.getSnapshot(), noIntent());
  const during2 = geometrySnapshot();
  const fb2 = turtle.finishFeedback();
  scene.sync(turtle.getSnapshot(), noIntent());
  diag.traceOffPath = {
    result: up2,
    during: during2,
    feedback: fb2,
    afterReset: geometrySnapshot(),
    nextActiveRopeId: scene.getDiagnostics().activeRopeId,
  };

  // --- tap success on rope-2 ------------------------------------------
  const r2 = turtle.Ropes[1];
  turtle.pointerDown(3, r2.start.x, r2.start.y);
  const armed = turtle.pointerUp(3, r2.start.x, r2.start.y);
  turtle.pointerDown(4, r2.end.x, r2.end.y);
  const done = turtle.pointerUp(4, r2.end.x, r2.end.y);
  scene.sync(turtle.getSnapshot(), noIntent());
  const during3 = geometrySnapshot();
  const fb3 = turtle.finishFeedback();
  scene.sync(turtle.getSnapshot(), noIntent());
  diag.tapSuccess = {
    armed,
    result: done,
    during: during3,
    feedback: fb3,
    afterAdvance: geometrySnapshot(),
    nextActiveRopeId: scene.getDiagnostics().activeRopeId,
  };

  // --- three-rope completion: trace rope-3 ----------------------------
  const up3 = traceRope(turtle.Ropes[2], 5, null);
  scene.sync(turtle.getSnapshot(), noIntent());
  const fb4 = turtle.finishFeedback();
  scene.sync(turtle.getSnapshot(), noIntent());
  const finalDomain = turtle.getSnapshot();
  diag.threeRope = {
    rope3Result: up3,
    feedbackComplete: fb4.complete === true,
    finalDomain: {
      complete: finalDomain.complete,
      active: finalDomain.active,
      activeRopeId: finalDomain.activeRopeId,
      completedRopeIds: finalDomain.completedRopeIds.slice(),
    },
    afterComplete: geometrySnapshot(),
  };

  // --- css-scaled canvas ----------------------------------------------
  const canvas = frame.contentDocument.getElementById('ocean-rescue-canvas');
  diag.canvasRect = rectOf(canvas);
  const beforeRect = rectOf(canvas);
  canvas.style.width = '640px';
  canvas.style.height = '360px';
  const afterRect = rectOf(canvas);

  const roundTrips = [];
  const samplePoints = [];
  for (const rope of turtle.Ropes) {
    samplePoints.push(rope.start);
    samplePoints.push(rope.end);
  }
  for (const p of samplePoints) {
    const client = logicalToClient(canvas, p.x, p.y, diag.logicalWidth, diag.logicalHeight);
    const back = game.RenderRuntime.mapClientToLogical(client.x, client.y);
    roundTrips.push({
      logical: { x: p.x, y: p.y },
      client: { x: client.x, y: client.y },
      mapped: { x: back.x, y: back.y },
      err: Math.hypot(back.x - p.x, back.y - p.y),
    });
  }
  diag.cssScaled = {
    beforeRect,
    afterRect,
    roundTrips,
    geometry: geometrySnapshot(),
  };

  collectNetwork();
  diag.complete = true;
}

async function main() {
  const frame = document.getElementById('game-frame');
  try {
    webglPreflight();

    const win = frame.contentWindow;
    win.addEventListener('error', () => {
      diag.uncaughtErrorCount += 1;
      writeDiagnostics();
    });
    win.addEventListener('unhandledrejection', () => {
      diag.unhandledRejectionCount += 1;
      writeDiagnostics();
    });
    win.addEventListener('securitypolicyviolation', () => {
      diag.securityPolicyViolationCount += 1;
      writeDiagnostics();
    });

    await waitForReady(frame);

    const root = frame.contentDocument.getElementById('ocean-rescue-root');
    diag.singleHtmlReady =
      root.getAttribute('data-render-runtime') === 'ready' &&
      root.getAttribute('data-ocean-rescue-ready') === 'true';
    diag.renderRuntimeReady = win.OceanRescue.RenderRuntime.isReady() === true;
    diag.selectedBackend = root.getAttribute('data-render-backend');
    diag.logicalWidth = Number(root.getAttribute('data-render-logical-width'));
    diag.logicalHeight = Number(root.getAttribute('data-render-logical-height'));

    run();
  } catch (err) {
    diag.error = String((err && err.message) || err);
    collectNetwork();
    diag.complete = true;
  }
  writeDiagnostics();
}

main();
