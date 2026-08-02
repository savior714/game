// Authored crab scene runtime acceptance harness.
//
// Loads the published single HTML (/ocean-rescue/index.html) in a same-origin
// iframe and drives only the public OceanRescue runtime namespaces to prove
// the authored crab scene runtime contract and the canonical interaction
// geometry alignment.
//
// Two flows are supported, selected by the `flow` query parameter:
//   first-rock (default) - one canonical rock rescue accepted by the authored scene
//   complete             - rock-1..rock-3 rescue sequence with a final scene exit
//
// Unknown flow values fail closed.

const TASK_ID = 'AIDENGAME-OCEAN-RESCUE-CRAB-MISSION-INTERACTION-GEOMETRY-ALIGNMENT-01';
const IFRAME_SRC = '/ocean-rescue/index.html';
const READY_TIMEOUT_MS = 10000;

const params = new URLSearchParams(window.location.search);
const flowMode = params.get('flow') || 'first-rock';

const diag = {
  schemaVersion: 1,
  taskId: TASK_ID,
  singleHtmlReady: false,
  renderRuntimeReady: false,
  selectedBackend: null,
  logicalWidth: null,
  logicalHeight: null,
  webglPreflightAvailable: null,
  webglPreflightKind: null,
  flowMode,
  geometry: null,
  initial: null,
  rockTransitions: [],
  finalDomain: null,
  beforeExit: null,
  afterExit: null,
  externalOriginRequestCount: 0,
  externalOriginRequests: [],
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
      } catch (_) {
        /* skip unparseable */
      }
    }
  }
  diag.externalOriginRequests = externals;
  diag.externalOriginRequestCount = externals.length;
}

function computeGeometry(crab) {
  const dz = crab.DropZone;
  const layout = crab.Layout;
  const dzRect = {
    x1: dz.x - dz.width / 2,
    x2: dz.x + dz.width / 2,
    y1: dz.y - dz.height / 2,
    y2: dz.y + dz.height / 2,
  };
  const crabRect = {
    x1: layout.crabCenter.x - layout.crabFootprint.width / 2,
    x2: layout.crabCenter.x + layout.crabFootprint.width / 2,
    y1: layout.crabCenter.y - layout.crabFootprint.height / 2,
    y2: layout.crabCenter.y + layout.crabFootprint.height / 2,
  };
  function circleIntersectsRect(cx, cy, r, rect) {
    const nx = Math.max(rect.x1, Math.min(cx, rect.x2));
    const ny = Math.max(rect.y1, Math.min(cy, rect.y2));
    return Math.hypot(cx - nx, cy - ny) <= r;
  }
  function circleInsideRect(cx, cy, r, rect) {
    return (
      cx - r >= rect.x1 &&
      cx + r <= rect.x2 &&
      cy - r >= rect.y1 &&
      cy + r <= rect.y2
    );
  }
  const rocks = layout.rocks.map((rock) => ({
    id: rock.id,
    start: { x: rock.start.x, y: rock.start.y },
    placed: { x: rock.placed.x, y: rock.placed.y },
    radius: rock.radius,
    startIntersectsDropZone: circleIntersectsRect(
      rock.start.x,
      rock.start.y,
      rock.radius,
      dzRect
    ),
    placedInsideDropZone: circleInsideRect(
      rock.placed.x,
      rock.placed.y,
      rock.radius,
      dzRect
    ),
    startPressesCrab: circleIntersectsRect(
      rock.start.x,
      rock.start.y,
      rock.radius,
      crabRect
    ),
    placedClearOfCrab: !circleIntersectsRect(
      rock.placed.x,
      rock.placed.y,
      rock.radius,
      crabRect
    ),
  }));
  return {
    dropZone: { x: dz.x, y: dz.y, width: dz.width, height: dz.height },
    dropZoneRect: dzRect,
    crabCenter: { x: layout.crabCenter.x, y: layout.crabCenter.y },
    crabFootprint: {
      width: layout.crabFootprint.width,
      height: layout.crabFootprint.height,
    },
    grabberBase: { x: layout.grabberBase.x, y: layout.grabberBase.y },
    rocks,
  };
}

function grabRockToPlaced(crab, scene, rock) {
  const pointerId = 100 + rock.order;
  const startX = rock.start.x + 30;
  const startY = rock.start.y + 20;
  const targetX = rock.placed.x;
  const targetY = rock.placed.y;

  const down = crab.pointerDown(pointerId, startX, startY);
  const hold = crab.finishHold();
  const move = crab.pointerMove(pointerId, targetX, targetY);
  const up = crab.pointerUp(pointerId, targetX, targetY);
  scene.sync(crab.getSnapshot(), { active: false, x: null, y: null });

  return {
    rockId: rock.id,
    down: down === true,
    holdAccepted: hold && hold.accepted === true,
    holdOutcome: hold && hold.outcome,
    releaseAccepted: up && up.accepted === true,
    releaseOutcome: up && up.outcome,
    releaseRockId: up && up.rockId,
  };
}

function snapshotFingerprint(snapshot) {
  return JSON.stringify({
    active: snapshot.active,
    activeRockId: snapshot.activeRockId,
    completedRockIds: snapshot.completedRockIds || [],
    failureCount: snapshot.failureCount,
    helpLevel: snapshot.helpLevel,
    pointerActive: snapshot.pointerActive,
    holding: snapshot.holding,
    grabbed: snapshot.grabbed,
    inputLocked: snapshot.inputLocked,
    feedback: snapshot.feedback,
    complete: snapshot.complete,
  });
}

function runCompleteFlow(game, crab, scene) {
  const noPointerIntent = { active: false, x: null, y: null };
  diag.rockTransitions = [];
  for (let i = 0; i < 3; i += 1) {
    const rock = crab.Layout.rocks[i];
    const before = scene.getDiagnostics();
    const result = grabRockToPlaced(crab, scene, rock);
    const afterReleaseScene = scene.getDiagnostics();
    const transition = {
      rockId: result.rockId,
      activeRockBefore: before.activeRockId,
      holdAccepted: result.holdAccepted,
      holdOutcome: result.holdOutcome,
      releaseAccepted: result.releaseAccepted,
      releaseOutcome: result.releaseOutcome,
      completedCountAfterRelease: afterReleaseScene.completedCount,
      crabStateAfterRelease: afterReleaseScene.crabState,
    };
    const feedback = crab.finishFeedback();
    scene.sync(crab.getSnapshot(), noPointerIntent);
    transition.feedbackChanged = feedback.changed === true;
    transition.feedbackComplete = feedback.complete === true;
    transition.nextRockId = feedback.nextRockId;
    diag.rockTransitions.push(transition);
  }

  const finalSnapshot = crab.getSnapshot();
  diag.finalDomain = {
    active: finalSnapshot.active,
    activeRockId: finalSnapshot.activeRockId,
    completedRockIds: finalSnapshot.completedRockIds.slice(),
    completedCount: finalSnapshot.completedRockIds.length,
    complete: finalSnapshot.complete,
    inputLocked: finalSnapshot.inputLocked,
  };
  diag.beforeExit = scene.getDiagnostics();

  scene.exit();
  diag.afterExit = scene.getDiagnostics();
}

async function run() {
  const frame = document.getElementById('game-frame');
  try {
    webglPreflight();

    if (flowMode !== 'first-rock' && flowMode !== 'complete') {
      diag.error = 'unknown flow mode: ' + flowMode;
      collectNetwork();
      diag.complete = true;
      writeDiagnostics();
      return;
    }

    await waitForReady(frame);

    const win = frame.contentWindow;
    const game = win.OceanRescue;
    const crab = game.Crab;
    const scene = game.CrabScene;

    win.addEventListener('error', () => {
      diag.uncaughtErrorCount += 1;
      writeDiagnostics();
    });

    win.addEventListener('unhandledrejection', () => {
      diag.unhandledRejectionCount += 1;
      writeDiagnostics();
    });

    const root = frame.contentDocument.getElementById('ocean-rescue-root');
    diag.singleHtmlReady =
      root.getAttribute('data-render-runtime') === 'ready' &&
      root.getAttribute('data-ocean-rescue-ready') === 'true';
    diag.renderRuntimeReady = game.RenderRuntime.isReady() === true;
    diag.selectedBackend = root.getAttribute('data-render-backend');
    diag.logicalWidth = Number(root.getAttribute('data-render-logical-width'));
    diag.logicalHeight = Number(root.getAttribute('data-render-logical-height'));

    crab.start();
    scene.prepare();
    scene.activate();
    scene.sync(crab.getSnapshot(), { active: false, x: null, y: null });
    diag.geometry = computeGeometry(crab);
    diag.initial = scene.getDiagnostics();

    if (flowMode === 'complete') {
      runCompleteFlow(game, crab, scene);
    } else {
      const rock = crab.Layout.rocks[0];
      const result = grabRockToPlaced(crab, scene, rock);
      diag.firstRock = result;
      diag.feedback = crab.finishFeedback();
      scene.sync(crab.getSnapshot(), { active: false, x: null, y: null });
      diag.afterFirstRock = scene.getDiagnostics();

      scene.exit();
      diag.afterExit = scene.getDiagnostics();
    }

    collectNetwork();
    diag.complete = true;
  } catch (err) {
    diag.error = String((err && err.message) || err);
    collectNetwork();
    diag.complete = true;
  }
  writeDiagnostics();
}

run();
