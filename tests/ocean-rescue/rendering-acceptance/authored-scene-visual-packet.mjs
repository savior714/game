// Authored sea-turtle scene four-state visual evidence packet harness.
//
// Loads the published single HTML (/ocean-rescue/index.html) in a same-origin
// iframe and drives only the public OceanRescue runtime namespaces to construct
// one of four deterministic states:
//   worried    - initial state, no ropes completed
//   relief-1   - rope-1 completed
//   relief-2   - rope-1 and rope-2 completed
//   free       - all three ropes completed
//
// The state is selected via the `state` query parameter. Unknown states fail
// closed. Diagnostics are emitted as a single JSON line prefixed with
// `DIAGNOSTICS:` for the capture script to consume.

const TASK_ID = 'AIDENGAME-OCEAN-RESCUE-FOUR-STATE-VISUAL-EVIDENCE-PACKET-01';
const IFRAME_SRC = '/ocean-rescue/index.html';
const READY_TIMEOUT_MS = 12000;
const REFERENCE_PREFIX = '/docs/reference/ocean-rescue/';

const ALLOWED_STATES = ['worried', 'relief-1', 'relief-2', 'free'];

const params = new URLSearchParams(window.location.search);
const requestedState = params.get('state') || '';

const diag = {
  schemaVersion: 1,
  taskId: TASK_ID,
  requestedState: requestedState,
  singleHtmlReady: false,
  renderRuntimeReady: false,
  selectedBackend: null,
  logicalWidth: null,
  logicalHeight: null,
  deviceScaleFactor: 1,
  webglPreflightAvailable: null,
  webglPreflightKind: null,
  mounted: false,
  active: false,
  paused: false,
  animationRunning: false,
  activeRopeId: null,
  completedCount: 0,
  complete: false,
  reliefStage: null,
  missingAliases: [],
  legacyBridgeVisible: false,
  externalOriginRequestCount: 0,
  referenceImageRequestCount: 0,
  uncaughtErrorCount: 0,
  unhandledRejectionCount: 0,
  securityPolicyViolationCount: 0,
  error: null,
  ready: false
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
  throw new Error('iframe runtime not ready within 12s');
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
      const url = entry.name || '';
      try {
        const u = new URL(url);
        if (u.origin !== fixtureOrigin && u.origin !== 'null') {
          externals.push(url);
        }
        if (url.startsWith(REFERENCE_PREFIX)) {
          references.push(url);
        }
      } catch (_) {
        /* skip */
      }
    }
  }
  diag.externalOriginRequestCount = externals.length;
  diag.referenceImageRequestCount = references.length;
}

function releaseRope(turtle, rope, pointerId) {
  const midX = (rope.start.x + rope.end.x) / 2;
  const midY = (rope.start.y + rope.end.y) / 2;
  turtle.pointerDown(pointerId, rope.start.x, rope.start.y);
  turtle.pointerMove(pointerId, midX, midY);
  turtle.pointerMove(pointerId, rope.end.x, rope.end.y);
  const upResult = turtle.pointerUp(pointerId, rope.end.x, rope.end.y);
  return upResult;
}

function constructState(turtle, turtleScene, stateName) {
  const ROPE_IDS = ['rope-1', 'rope-2', 'rope-3'];
  let completedCount = 0;
  let activeRopeId = null;
  let complete = false;
  let reliefStage = 'worried';

  if (stateName === 'worried') {
    turtle.start();
    const snap = turtle.getSnapshot();
    turtleScene.prepare();
    turtleScene.activate();
    turtleScene.sync(snap, { active: false, x: null, y: null });
    turtleScene.pause();
    activeRopeId = snap.activeRopeId;
    completedCount = snap.completedRopeIds.length;
    complete = snap.complete;
    reliefStage = turtleScene.getDiagnostics().reliefStage;
  } else if (stateName === 'relief-1') {
    turtle.start();
    releaseRope(turtle, turtle.Ropes[0], 1001);
    const fb1 = turtle.finishFeedback();
    const snap1 = turtle.getSnapshot();
    turtleScene.prepare();
    turtleScene.activate();
    turtleScene.sync(snap1, { active: false, x: null, y: null });
    turtleScene.pause();
    activeRopeId = snap1.activeRopeId;
    completedCount = snap1.completedRopeIds.length;
    complete = snap1.complete;
    reliefStage = turtleScene.getDiagnostics().reliefStage;
  } else if (stateName === 'relief-2') {
    turtle.start();
    releaseRope(turtle, turtle.Ropes[0], 1001);
    turtle.finishFeedback();
    releaseRope(turtle, turtle.Ropes[1], 1002);
    const fb2 = turtle.finishFeedback();
    const snap2 = turtle.getSnapshot();
    turtleScene.prepare();
    turtleScene.activate();
    turtleScene.sync(snap2, { active: false, x: null, y: null });
    turtleScene.pause();
    activeRopeId = snap2.activeRopeId;
    completedCount = snap2.completedRopeIds.length;
    complete = snap2.complete;
    reliefStage = turtleScene.getDiagnostics().reliefStage;
  } else if (stateName === 'free') {
    turtle.start();
    releaseRope(turtle, turtle.Ropes[0], 1001);
    turtle.finishFeedback();
    releaseRope(turtle, turtle.Ropes[1], 1002);
    turtle.finishFeedback();
    releaseRope(turtle, turtle.Ropes[2], 1003);
    const fb3 = turtle.finishFeedback();
    const snap3 = turtle.getSnapshot();
    turtleScene.prepare();
    turtleScene.activate();
    turtleScene.sync(snap3, { active: false, x: null, y: null });
    turtleScene.pause();
    activeRopeId = snap3.activeRopeId;
    completedCount = snap3.completedRopeIds.length;
    complete = snap3.complete;
    reliefStage = turtleScene.getDiagnostics().reliefStage;
  } else {
    throw new Error('Unknown state: ' + stateName);
  }

  const diags = turtleScene.getDiagnostics();
  return {
    activeRopeId: activeRopeId,
    completedCount: completedCount,
    complete: complete,
    reliefStage: reliefStage,
    mounted: diags.mounted,
    active: diags.active,
    paused: diags.paused,
    animationRunning: diags.animationRunning,
    missingAliases: diags.missingAliases,
    legacyBridgeVisible: diags.legacyBridgeVisible
  };
}

async function main() {
  const frame = document.getElementById('game-frame');
  if (!frame) {
    diag.error = 'iframe element missing';
    writeDiagnostics();
    return;
  }

  if (!ALLOWED_STATES.includes(requestedState)) {
    diag.error = 'Unknown state: ' + requestedState;
    writeDiagnostics();
    return;
  }

  try {
    await waitForReady(frame);
    diag.singleHtmlReady = true;

    const win = frame.contentWindow;
    const doc = frame.contentDocument;
    const root = doc.getElementById('ocean-rescue-root');
    diag.selectedBackend = root ? root.getAttribute('data-render-backend') : null;
    diag.logicalWidth = frame.clientWidth;
    diag.logicalHeight = frame.clientHeight;
    diag.deviceScaleFactor = window.devicePixelRatio || 1;

    webglPreflight();

    const game = win.OceanRescue;
    const turtle = game.SeaTurtle;
    const turtleScene = game.SeaTurtleScene;

    if (!turtle || !turtleScene) {
      diag.error = 'SeaTurtle or SeaTurtleScene namespace missing';
      writeDiagnostics();
      return;
    }

    const result = constructState(turtle, turtleScene, requestedState);

    diag.mounted = result.mounted;
    diag.active = result.active;
    diag.paused = result.paused;
    diag.animationRunning = result.animationRunning;
    diag.activeRopeId = result.activeRopeId;
    diag.completedCount = result.completedCount;
    diag.complete = result.complete;
    diag.reliefStage = result.reliefStage;
    diag.missingAliases = result.missingAliases;
    diag.legacyBridgeVisible = result.legacyBridgeVisible;

    collectNetwork();

    diag.ready = true;
    diag.error = null;

    writeDiagnostics();

    if (win.OceanRescue && win.OceanRescue.RenderRuntime && typeof win.OceanRescue.RenderRuntime.renderSceneFrame === 'function') {
      win.OceanRescue.RenderRuntime.renderSceneFrame();
      win.OceanRescue.RenderRuntime.renderSceneFrame();
      win.OceanRescue.RenderRuntime.renderSceneFrame();
    }

    let rafCount = 0;
    const settleRaf = () => {
      rafCount += 1;
      if (rafCount >= 3) {
        document.documentElement.dataset.visualPacketReady = 'true';
      } else {
        window.requestAnimationFrame(settleRaf);
      }
    };
    window.requestAnimationFrame(settleRaf);
  } catch (err) {
    diag.error = err.message;
  }

  writeDiagnostics();
}

main().catch((err) => {
  diag.error = 'Unhandled error: ' + err.message;
  writeDiagnostics();
});
