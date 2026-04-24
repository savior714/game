import { initialAngles, planets, state } from "./state.js";
import { createRenderer } from "./renderer.js";
import { attachControls } from "./controls.js";

const canvas = document.getElementById("solar-system-canvas");
const ctx = canvas ? canvas.getContext("2d") : null;

function init() {
  if (!canvas || !ctx) return;

  const { resizeCanvas, render } = createRenderer(canvas, ctx, state, planets);
  attachControls({ state, planets, initialAngles, render });

  function tick(ts) {
    if (!state.lastTs) {
      state.lastTs = ts;
    }
    const dt = (ts - state.lastTs) / 1000;
    state.lastTs = ts;

    if (state.isPlaying) {
      state.elapsedTime += dt * state.timeScale;
      for (const planet of planets) {
        planet.angle += dt * planet.orbitSpeed * state.timeScale;
      }
    }

    render();
    state.rafId = requestAnimationFrame(tick);
  }

  resizeCanvas();
  render();
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
