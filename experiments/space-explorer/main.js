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

function formatElapsedTime(earthYears) {
  if (earthYears < 1 / 365.25) {
    const days = earthYears * 365.25;
    return `${Math.max(1, Math.round(days * 24))}시간`;
  } else if (earthYears < 1) {
    const days = earthYears * 365.25;
    return `${Math.round(days)}일`;
  } else if (earthYears < 10) {
    return `${earthYears.toFixed(1)}년`;
  } else if (earthYears < 100) {
    return `${earthYears.toFixed(0)}년`;
  }
  return `${Math.round(earthYears)}년`;
}

function updateInfoPanel(planet) {
  const panel = document.getElementById("planet-info");
  if (!panel) return;

  if (!planet) {
    panel.innerHTML = `
      <p class="info-placeholder">
        행성을 클릭하면 상세 정보를 볼 수 있습니다.
      </p>`;
    return;
  }

  const info = planet.info;
  panel.innerHTML = `
    <h3 class="info-planet-name">${planet.name} <span class="info-planet-en">${planet.nameEn}</span></h3>
    <div class="info-grid">
      <div class="info-item">
        <span class="info-label">지름</span>
        <span class="info-value">${info.diameter}</span>
      </div>
      <div class="info-item">
        <span class="info-label">태양 거리</span>
        <span class="info-value">${info.distance}</span>
      </div>
      <div class="info-item">
        <span class="info-label">공전 주기</span>
        <span class="info-value">${info.orbitalPeriod}</span>
      </div>
      <div class="info-item">
        <span class="info-label">온도</span>
        <span class="info-value">${info.temperature}</span>
      </div>
    </div>
    <p class="info-description">${info.description}</p>`;
}

function init() {
  if (!canvas || !ctx) return;

  const { resizeCanvas, render, hitTest } = createRenderer(canvas, ctx, state, planets);
  attachControls({ state, planets, initialAngles, render });
  attachTouchInteractions({ canvas, state, render });

  // 클릭/호버 처리
  function getCanvasCoords(event) {
    const rect = canvas.getBoundingClientRect();
    return {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    };
  }

  canvas.addEventListener("click", (event) => {
    const coords = getCanvasCoords(event);
    const hit = hitTest(coords.x, coords.y);

    if (hit) {
      state.selectedPlanet = hit;
      updateInfoPanel(hit);
    } else {
      state.selectedPlanet = null;
      updateInfoPanel(null);
    }
    render();
  });

  canvas.addEventListener("mousemove", (event) => {
    const coords = getCanvasCoords(event);
    const hit = hitTest(coords.x, coords.y);

    if (hit !== state.hoveredPlanet) {
      state.hoveredPlanet = hit;
      canvas.style.cursor = hit ? "pointer" : "default";
      render();
    }
  });

  canvas.addEventListener("mouseleave", () => {
    if (state.hoveredPlanet) {
      state.hoveredPlanet = null;
      canvas.style.cursor = "default";
      render();
    }
  });

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

  // 경과 시간 업데이트 (별도 tick)
  setInterval(() => {
    const timeEl = document.getElementById("elapsed-time");
    if (timeEl) {
      timeEl.textContent = formatElapsedTime(state.elapsedTime);
    }
  }, 200);
}

init();
