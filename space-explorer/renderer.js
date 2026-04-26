import { BASE_ORBIT, ORBIT_STEP, TWO_PI } from "./state.js";

const ORBIT_TILT = Math.PI / 6;
const ORBIT_FLATTEN = 0.55;
const PERF_MARK_START = "spaceExplorer:render:start";
const PERF_MARK_END = "spaceExplorer:render:end";
const PERF_MEASURE_NAME = "spaceExplorer:render:duration";

export function createRenderer(canvas, ctx, state, planets) {
  let viewportWidth = 0;
  let viewportHeight = 0;
  let dpr = 1;
  let starLayer = null;
  let starLayerMode = "";

  function is3DMode() {
    return state.renderMode === "3d";
  }

  function buildStarLayer(width, height, mode) {
    const cache = document.createElement("canvas");
    cache.width = width;
    cache.height = height;
    const cacheCtx = cache.getContext("2d");
    if (!cacheCtx) return null;

    cacheCtx.fillStyle = mode === "3d" ? "#050918" : "#081326";
    cacheCtx.fillRect(0, 0, width, height);

    const nebula = cacheCtx.createRadialGradient(
      Math.floor(width * 0.72),
      Math.floor(height * 0.22),
      20,
      Math.floor(width * 0.72),
      Math.floor(height * 0.22),
      Math.floor(width * 0.9),
    );
    nebula.addColorStop(0, "rgba(92,133,255,0.22)");
    nebula.addColorStop(0.55, "rgba(110,70,170,0.14)");
    nebula.addColorStop(1, "rgba(4,8,20,0)");
    cacheCtx.fillStyle = nebula;
    cacheCtx.fillRect(0, 0, width, height);

    const stars = mode === "3d" ? 140 : 86;
    for (let i = 0; i < stars; i += 1) {
      const sx = Math.floor((i * 197.3 + i * i * 0.37) % width);
      const sy = Math.floor((i * 89.1 + i * i * 0.21) % height);
      const size = mode === "3d" ? ((i % 3) + 1) : 1;
      cacheCtx.fillStyle = `rgba(255,255,255,${mode === "3d" ? 0.26 : 0.2})`;
      cacheCtx.fillRect(sx, sy, size, size);
    }
    return cache;
  }

  function resizeCanvas() {
    if (!canvas) return;
    const parent = canvas.parentElement;
    if (!parent) return;
    const rect = parent.getBoundingClientRect();
    viewportWidth = Math.max(900, Math.floor(rect.width - 2));
    viewportHeight = Math.max(560, Math.floor(viewportWidth * 0.6));
    dpr = Math.max(1, Math.min(2, window.devicePixelRatio || 1));

    canvas.width = Math.floor(viewportWidth * dpr);
    canvas.height = Math.floor(viewportHeight * dpr);
    canvas.style.width = `${viewportWidth}px`;
    canvas.style.height = `${viewportHeight}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    starLayer = buildStarLayer(viewportWidth, viewportHeight, state.renderMode);
    starLayerMode = state.renderMode;
  }

  function drawOrbit(cx, cy, orbitRadius) {
    ctx.beginPath();
    if (is3DMode()) {
      ctx.ellipse(cx, cy, orbitRadius, orbitRadius * ORBIT_FLATTEN, ORBIT_TILT, 0, TWO_PI);
    } else {
      ctx.arc(cx, cy, orbitRadius, 0, TWO_PI);
    }
    ctx.strokeStyle = is3DMode() ? "rgba(255,255,255,0.2)" : "rgba(255,255,255,0.18)";
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  function projectOrbitPosition(cx, cy, orbitRadius, angle) {
    if (!is3DMode()) {
      return {
        x: cx + Math.cos(angle) * orbitRadius,
        y: cy + Math.sin(angle) * orbitRadius,
      };
    }

    const ellipseX = Math.cos(angle) * orbitRadius;
    const ellipseY = Math.sin(angle) * orbitRadius * ORBIT_FLATTEN;
    const x = cx + Math.cos(ORBIT_TILT) * ellipseX - Math.sin(ORBIT_TILT) * ellipseY;
    const y = cy + Math.sin(ORBIT_TILT) * ellipseX + Math.cos(ORBIT_TILT) * ellipseY;
    return { x, y };
  }

  function drawBody(x, y, radius, color, phase = 0) {
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, TWO_PI);
    if (!is3DMode()) {
      ctx.fillStyle = color;
      ctx.fill();
      return;
    }

    const gradient = ctx.createRadialGradient(
      x - radius * 0.35,
      y - radius * 0.4,
      Math.max(1, radius * 0.2),
      x,
      y,
      radius * 1.1,
    );
    gradient.addColorStop(0, "rgba(255,255,255,0.9)");
    gradient.addColorStop(0.22, color);
    gradient.addColorStop(1, "rgba(10,12,20,0.96)");
    ctx.fillStyle = gradient;
    ctx.fill();

    ctx.strokeStyle = `rgba(255,255,255,${0.15 + 0.1 * Math.sin(phase)})`;
    ctx.lineWidth = 0.7;
    ctx.stroke();
  }

  function render() {
    if (!canvas || !ctx) return;
    if (!viewportWidth || !viewportHeight) return;
    if (typeof performance !== "undefined" && typeof performance.mark === "function") {
      performance.mark(PERF_MARK_START);
    }
    if (!starLayer || starLayerMode !== state.renderMode) {
      starLayer = buildStarLayer(viewportWidth, viewportHeight, state.renderMode);
      starLayerMode = state.renderMode;
    }
    const width = viewportWidth;
    const height = viewportHeight;
    const cx = width / 2;
    const cy = height / 2;
    const zoom = state.zoom || 1;
    const viewRotation = state.viewRotation || 0;
    const sceneScale = Math.max(1, Math.min(1.45, Math.min(width / 860, height / 520)));

    ctx.clearRect(0, 0, width, height);
    if (starLayer) {
      ctx.drawImage(starLayer, 0, 0);
    }

    drawBody(cx, cy, (is3DMode() ? 16 : 14) * sceneScale, "#ffd166", state.elapsedTime);

    for (const planet of planets) {
      const orbitRadius = (BASE_ORBIT + planet.orbitIndex * ORBIT_STEP) * zoom * sceneScale;
      drawOrbit(cx, cy, orbitRadius);
      const planetAngle = planet.angle + viewRotation;
      const orbitPoint = projectOrbitPosition(cx, cy, orbitRadius, planetAngle);
      const px = orbitPoint.x;
      const py = orbitPoint.y;
      drawBody(
        px,
        py,
        planet.radius * sceneScale * Math.max(0.85, zoom * 0.95),
        planet.color,
        planet.angle,
      );

      if (state.showLabels) {
        ctx.fillStyle = "#d8e0ff";
        ctx.font = is3DMode() ? "12px sans-serif" : "10px sans-serif";
        ctx.fillText(planet.name, px + planet.radius + 4, py - planet.radius - 2);
      }
    }
    if (typeof performance !== "undefined" && typeof performance.mark === "function") {
      performance.mark(PERF_MARK_END);
    }
    if (typeof performance !== "undefined" && typeof performance.measure === "function") {
      performance.measure(PERF_MEASURE_NAME, PERF_MARK_START, PERF_MARK_END);
    }
  }

  return { resizeCanvas, render };
}
