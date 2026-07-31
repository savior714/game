// Authored sea-turtle scene runtime acceptance harness.
//
// Loads the published single HTML (/ocean-rescue/index.html) in a same-origin
// iframe and drives only the public OceanRescue runtime namespaces to prove
// the authored scene runtime contract.
//
// Two flows are supported, selected by the `flow` query parameter:
//   first-rope  - one canonical rope release (default, preserved behavior)
//   complete    - rope-1..rope-3 with a pause/resume cycle between rope-1 and
//                 rope-2 and a final scene exit
//
// Unknown flow values fail closed.

const TASK_ID = 'AIDENGAME-OCEAN-RESCUE-AUTHORED-SCENE-RUNTIME-ACCEPTANCE-01';
const IFRAME_SRC = '/ocean-rescue/index.html';
const READY_TIMEOUT_MS = 10000;
const REFERENCE_PREFIX = '/docs/reference/ocean-rescue/';

const params = new URLSearchParams(window.location.search);
const flowMode = params.get('flow') || 'first-rope';

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
  initial: null,
  releaseResult: null,
  afterReleaseInterim: null,
  feedback: null,
  afterRelease: null,
  afterExit: null,
  ropeTransitions: [],
  pauseCycle: null,
  finalDomain: null,
  beforeExit: null,
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

function releaseCanonicalRope(turtle, scene, ropeIndex) {
  const rope = turtle.Ropes[ropeIndex];
  const pointerId = 100 + ropeIndex;

  const down = turtle.pointerDown(
    pointerId,
    rope.start.x,
    rope.start.y,
  );

  const move1 = turtle.pointerMove(
    pointerId,
    (rope.start.x + rope.end.x) / 2,
    (rope.start.y + rope.end.y) / 2,
  );

  const move2 = turtle.pointerMove(
    pointerId,
    rope.end.x,
    rope.end.y,
  );

  const up = turtle.pointerUp(
    pointerId,
    rope.end.x,
    rope.end.y,
  );

  scene.sync(turtle.getSnapshot(), {
    active: false,
    x: null,
    y: null,
  });

  return {
    ropeId: rope.id,
    down,
    move1,
    move2,
    release: up,
    domainAfterRelease: turtle.getSnapshot(),
    sceneAfterRelease: scene.getDiagnostics(),
  };
}

function snapshotFingerprint(snapshot) {
  return JSON.stringify({
    active: snapshot.active,
    activeRopeId: snapshot.activeRopeId,
    completedRopeIds: snapshot.completedRopeIds || [],
    failureCount: snapshot.failureCount,
    helpLevel: snapshot.helpLevel,
    tapStartArmed: snapshot.tapStartArmed,
    pointerActive: snapshot.pointerActive,
    inputLocked: snapshot.inputLocked,
    feedback: snapshot.feedback,
    complete: snapshot.complete,
  });
}

function runCompleteFlow(game, turtle, scene) {
  const noPointerIntent = { active: false, x: null, y: null };

  diag.ropeTransitions = [];
  for (let i = 0; i < 3; i += 1) {
    const before = scene.getDiagnostics();
    const result = releaseCanonicalRope(turtle, scene, i);
    const afterReleaseScene = scene.getDiagnostics();
    const transition = {
      ropeId: result.ropeId,
      activeRopeBefore: before.activeRopeId,
      releaseAccepted: result.release.accepted === true,
      releaseOutcome: result.release.outcome,
      completedCountAfterRelease: afterReleaseScene.completedCount,
      reliefAfterRelease: afterReleaseScene.reliefStage,
    };
    const feedback = turtle.finishFeedback();
    scene.sync(turtle.getSnapshot(), noPointerIntent);
    transition.feedbackChanged = feedback.changed === true;
    transition.feedbackComplete = feedback.complete === true;
    transition.nextRopeId = feedback.nextRopeId;
    diag.ropeTransitions.push(transition);

    if (i === 0) {
      const domainBeforePause = turtle.getSnapshot();

      turtle.pauseCancel();
      game.RenderRuntime.pause();
      scene.pause();

      const pausedScene = scene.getDiagnostics();
      const domainDuringPause = turtle.getSnapshot();
      const runtimePausedDuringPause = game.RenderRuntime.isPaused() === true;

      game.RenderRuntime.resume();
      scene.resume();

      const resumedScene = scene.getDiagnostics();
      const domainAfterResume = turtle.getSnapshot();
      const runtimePausedAfterResume = game.RenderRuntime.isPaused() === true;

      diag.pauseCycle = {
        paused: runtimePausedDuringPause,
        scenePaused: pausedScene.paused === true,
        animationStopped: pausedScene.animationRunning === false,
        domainUnchanged:
          snapshotFingerprint(domainBeforePause) ===
            snapshotFingerprint(domainDuringPause) &&
          snapshotFingerprint(domainDuringPause) ===
            snapshotFingerprint(domainAfterResume),
        activeRopeIdDuringPause: domainDuringPause.activeRopeId,
        completedIdsDuringPause: (domainDuringPause.completedRopeIds || []).slice(),
        resumed: !runtimePausedAfterResume,
        sceneActiveAfterResume: resumedScene.active === true,
        scenePausedAfterResume: resumedScene.paused === true,
      };
    }
  }

  const finalSnapshot = turtle.getSnapshot();
  diag.finalDomain = {
    active: finalSnapshot.active,
    activeRopeId: finalSnapshot.activeRopeId,
    completedRopeIds: finalSnapshot.completedRopeIds.slice(),
    completedCount: finalSnapshot.completedRopeIds.length,
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

    if (flowMode !== 'first-rope' && flowMode !== 'complete') {
      diag.error = 'unknown flow mode: ' + flowMode;
      collectNetwork();
      diag.complete = true;
      writeDiagnostics();
      return;
    }

    await waitForReady(frame);

    const win = frame.contentWindow;
    const game = win.OceanRescue;
    const turtle = game.SeaTurtle;
    const scene = game.SeaTurtleScene;

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

    turtle.start();
    scene.prepare();
    scene.activate();
    scene.sync(turtle.getSnapshot(), { active: false, x: null, y: null });
    diag.initial = scene.getDiagnostics();

    if (flowMode === 'complete') {
      runCompleteFlow(game, turtle, scene);
    } else {
      const rope = turtle.Ropes[0];
      const pointerId = 1;

      turtle.pointerDown(pointerId, rope.start.x, rope.start.y);
      turtle.pointerMove(
        pointerId,
        (rope.start.x + rope.end.x) / 2,
        (rope.start.y + rope.end.y) / 2,
      );
      turtle.pointerMove(pointerId, rope.end.x, rope.end.y);
      diag.releaseResult = turtle.pointerUp(pointerId, rope.end.x, rope.end.y);

      scene.sync(turtle.getSnapshot(), { active: false, x: null, y: null });
      diag.afterReleaseInterim = scene.getDiagnostics();

      diag.feedback = turtle.finishFeedback();
      scene.sync(turtle.getSnapshot(), { active: false, x: null, y: null });
      diag.afterRelease = scene.getDiagnostics();

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
