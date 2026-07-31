import { Application, Graphics, WebGLRenderer, CanvasRenderer } from 'pixi.js';

const params = new URLSearchParams(window.location.search);
const caseId = params.get('case') || 'normal-auto';

const CASE_PREFERENCE = {
  'normal-auto': ['webgl', 'canvas'],
  'disabled-webgl-fallback': ['webgl', 'canvas'],
  'forced-canvas': 'canvas',
};

const preference = CASE_PREFERENCE[caseId] || ['webgl', 'canvas'];

const diag = {
  schemaVersion: 1,
  caseId,
  requestedPreference: preference,
  pixiVersion: '8.19.0',
  webglPreflightAvailable: false,
  webglPreflightKind: null,
  selectedBackend: null,
  applicationCount: 0,
  rendererCount: 0,
  canvasCount: 0,
  stageChildCount: 0,
  initializationSucceeded: false,
  renderSucceeded: false,
  destroySucceeded: false,
  uncaughtErrorCount: 0,
  unhandledRejectionCount: 0,
  externalOriginRequestCount: 0,
  externalOriginRequests: [],
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

function recordExternalRequests() {
  const entries = performance.getEntriesByType('resource');
  const fixtureOrigin = window.location.origin;
  const externals = [];
  for (const entry of entries) {
    try {
      const url = new URL(entry.name);
      if (url.origin !== fixtureOrigin && url.protocol !== 'data:' && url.protocol !== 'blob:') {
        externals.push(entry.name);
      }
    } catch (_) {
      /* skip unparseable */
    }
  }
  diag.externalOriginRequestCount = externals.length;
  diag.externalOriginRequests = externals;
}

window.addEventListener('error', () => {
  diag.uncaughtErrorCount++;
  writeDiagnostics();
});

window.addEventListener('unhandledrejection', () => {
  diag.unhandledRejectionCount++;
  writeDiagnostics();
});

window.addEventListener('securitypolicyviolation', () => {
  diag.securityPolicyViolationCount++;
  writeDiagnostics();
});

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
}

async function run() {
  webglPreflight();

  let app = null;
  try {
    app = new Application();
    diag.applicationCount = 1;

    await app.init({
      width: 64,
      height: 64,
      resolution: 1,
      autoStart: false,
      sharedTicker: false,
      preference,
    });

    diag.initializationSucceeded = true;

    if (app.renderer) {
      diag.rendererCount = 1;
      if (app.renderer instanceof WebGLRenderer) {
        diag.selectedBackend = 'webgl';
      } else if (app.renderer instanceof CanvasRenderer) {
        diag.selectedBackend = 'canvas';
      }
    }

    document.body.appendChild(app.canvas);
    if (app.canvas) {
      diag.canvasCount = 1;
    }

    const rect = new Graphics();
    rect.rect(0, 0, 64, 64);
    rect.fill({ color: 0xff6600 });
    app.stage.addChild(rect);
    diag.stageChildCount = app.stage.children.length;

    app.render();
    diag.renderSucceeded = true;

    app.destroy(true);
    diag.destroySucceeded = true;
  } catch (err) {
    diag.error = String(err);
    if (app && !diag.destroySucceeded) {
      try {
        app.destroy(true);
        diag.destroySucceeded = true;
      } catch (_) {
        /* already failed */
      }
    }
  }

  recordExternalRequests();
  diag.complete = true;
  writeDiagnostics();
}

run();
