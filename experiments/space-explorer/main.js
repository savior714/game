import { initialAngles, planets, state } from "./state.js";
import { createRenderer } from "./renderer.js";
import { attachControls } from "./controls.js";
import { attachTouchInteractions } from "./interactions.js";
import { initializeSpaceBackdrop } from "./three-backdrop.js";

const canvas = document.getElementById("solar-system-canvas");
const threeLayer = document.getElementById("space-explorer-three-layer");
const ctx = canvas
  ? (canvas.getContext("2d", { alpha: false, desynchronized: true }) || canvas.getContext("2d"))
  : null;
const SMOOTHING_EPSILON = 0.0008;

function init() {
  if (!canvas || !ctx) return;

  const { resizeCanvas, render } = createRenderer(canvas, ctx, state, planets);
  attachControls({ state, planets, initialAngles, render });
  attachTouchInteractions({ canvas, state, render });

  function tick(ts) {
    if (!state.lastTs) {
      state.lastTs = ts;
    }
    const dt = (ts - state.lastTs) / 1000;
    state.lastTs = ts;

    let shouldRenderFrame = state.isPlaying;
    if (state.isPlaying) {
      state.elapsedTime += dt * state.timeScale;
      for (const planet of planets) {
        planet.angle += dt * planet.orbitSpeed * state.timeScale;
      }
    }

    // Smooth target gesture values to reduce touch jitter.
    const zoomDelta = state.targetZoom - state.zoom;
    const rotationDelta = state.targetRotation - state.viewRotation;
    if (Math.abs(zoomDelta) > SMOOTHING_EPSILON || Math.abs(rotationDelta) > SMOOTHING_EPSILON) {
      state.zoom += zoomDelta * 0.18;
      state.viewRotation += rotationDelta * 0.18;
      shouldRenderFrame = true;
    } else {
      state.zoom = state.targetZoom;
      state.viewRotation = state.targetRotation;
    }

    if (shouldRenderFrame) {
      render();
    }
    state.rafId = requestAnimationFrame(tick);
  }

  resizeCanvas();
  render();
  initializeSpaceBackdrop(threeLayer, { intensity: 1.2 });
  state.rafId = requestAnimationFrame(tick);

  let resizeQueued = false;
  window.addEventListener("resize", () => {
    if (resizeQueued) return;
    resizeQueued = true;
    requestAnimationFrame(() => {
      resizeCanvas();
      render();
      resizeQueued = false;
    });
  }, { passive: true });

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      state.lastTs = 0;
    }
  });
}

init();
