import { TWO_PI } from "./state.js";

const PERF_MARK_START = "spaceExplorer:render:start";
const PERF_MARK_END = "spaceExplorer:render:end";
const PERF_MEASURE_NAME = "spaceExplorer:render:duration";

export function createRenderer(canvas, ctx, state, planets) {
  let viewportWidth = 0;
  let viewportHeight = 0;
  let dpr = 1;
  let starLayer = null;
  let starLayerMode = "";

  // 클릭/호버 검출용 — render()에서 채움
  let planetHitboxes = [];

  // 정렬된 행성 목록 (초기화 시 한 번만 생성, resize 시 불변)
  let sortedPlanets = [];

  function initPlanetOrder() {
    sortedPlanets = [...planets].sort((a, b) => b.orbitRadius - a.orbitRadius);
  }

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
    initPlanetOrder();
  }

  function drawSunGlow(cx, cy, radius) {
    // 외부 글로우 (넓고 희미하게)
    const outerGlow = ctx.createRadialGradient(cx, cy, radius * 0.5, cx, cy, radius * 6);
    outerGlow.addColorStop(0, "rgba(255,200,60,0.18)");
    outerGlow.addColorStop(0.4, "rgba(255,160,30,0.06)");
    outerGlow.addColorStop(1, "rgba(255,100,0,0)");
    ctx.fillStyle = outerGlow;
    ctx.fillRect(cx - radius * 6, cy - radius * 6, radius * 12, radius * 12);

    // 중간 글로우
    const midGlow = ctx.createRadialGradient(cx, cy, radius * 0.3, cx, cy, radius * 3);
    midGlow.addColorStop(0, "rgba(255,220,100,0.35)");
    midGlow.addColorStop(0.5, "rgba(255,180,50,0.12)");
    midGlow.addColorStop(1, "rgba(255,140,20,0)");
    ctx.fillStyle = midGlow;
    ctx.beginPath();
    ctx.arc(cx, cy, radius * 3, 0, TWO_PI);
    ctx.fill();

    // 태양 본체 (그라데이션)
    const sunGrad = ctx.createRadialGradient(
      cx - radius * 0.3,
      cy - radius * 0.3,
      radius * 0.1,
      cx,
      cy,
      radius * 1.2,
    );
    sunGrad.addColorStop(0, "#fff8e0");
    sunGrad.addColorStop(0.25, "#ffe44d");
    sunGrad.addColorStop(0.6, "#ffb820");
    sunGrad.addColorStop(1, "#e87a00");
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, TWO_PI);
    ctx.fillStyle = sunGrad;
    ctx.fill();

    // 태양 표면 질감 (반짝임)
    const pulse = Math.sin(state.elapsedTime * 2) * 0.1 + 0.9;
    ctx.beginPath();
    ctx.arc(cx, cy, radius * 1.05 * pulse, 0, TWO_PI);
    ctx.strokeStyle = "rgba(255,220,100,0.25)";
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }

  function drawOrbit(cx, cy, orbitRadius) {
    ctx.beginPath();
    ctx.ellipse(cx, cy, orbitRadius, orbitRadius * 0.92, 0.08, 0, TWO_PI);
    ctx.strokeStyle = "rgba(255,255,255,0.1)";
    ctx.lineWidth = 0.7;
    ctx.setLineDash([4, 6]);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16),
    } : { r: 170, g: 170, b: 170 };
  }

  function drawTrail(trail, color) {
    if (trail.length < 2) return;
    const rgb = hexToRgb(color);

    const avgAlpha = ((trail.length - 1) / trail.length) * 0.5 * 0.6;
    const avgWidth = ((trail.length - 1) / trail.length) * 2 * 0.6;

    ctx.beginPath();
    for (let i = 1; i < trail.length; i += 1) {
      ctx.moveTo(trail[i - 1].x, trail[i - 1].y);
      ctx.lineTo(trail[i].x, trail[i].y);
    }
    ctx.strokeStyle = `rgba(${rgb.r},${rgb.g},${rgb.b},${avgAlpha})`;
    ctx.lineWidth = avgWidth;
    ctx.stroke();
  }

  function drawSaturnRings(cx, cy, planetRadius, ringInner, ringOuter, angle) {
    const tilt = 0.35;
    const ringWidth = ringOuter - ringInner;

    // 뒤쪽 고리 (행성 뒤에 가려짐)
    ctx.save();
    ctx.beginPath();
    ctx.ellipse(cx, cy, ringOuter, ringOuter * tilt, 0.15, Math.PI, TWO_PI);
    ctx.ellipse(cx, cy, ringInner, ringInner * tilt, 0.15, TWO_PI, Math.PI);
    ctx.closePath();
    ctx.clip();

    for (let r = ringInner; r <= ringOuter; r += 2.5) {
      const ringAlpha = 0.35 + 0.15 * Math.sin((r - ringInner) / ringWidth * Math.PI);
      ctx.beginPath();
      ctx.ellipse(cx, cy, r, r * tilt, 0.15, Math.PI, TWO_PI);
      ctx.strokeStyle = `rgba(210,195,160,${ringAlpha})`;
      ctx.lineWidth = 2;
      ctx.stroke();
    }
    ctx.restore();

    // 앞쪽 고리 (행성 앞에 보임)
    ctx.save();
    ctx.beginPath();
    ctx.ellipse(cx, cy, ringOuter, ringOuter * tilt, 0.15, 0, Math.PI);
    ctx.ellipse(cx, cy, ringInner, ringInner * tilt, 0.15, Math.PI, 0);
    ctx.closePath();
    ctx.clip();

    for (let r = ringInner; r <= ringOuter; r += 2.5) {
      const ringAlpha = 0.35 + 0.15 * Math.sin((r - ringInner) / ringWidth * Math.PI);
      ctx.beginPath();
      ctx.ellipse(cx, cy, r, r * tilt, 0.15, 0, Math.PI);
      ctx.strokeStyle = `rgba(210,195,160,${ringAlpha})`;
      ctx.lineWidth = 2;
      ctx.stroke();
    }
    ctx.restore();
  }

  function drawPlanetBody(x, y, radius, color, gradientStops, phase, isSelected, isHovered) {
    // 선택/호버 시 하이라이트 링
    if (isSelected || isHovered) {
      ctx.beginPath();
      ctx.arc(x, y, radius + 4, 0, TWO_PI);
      ctx.strokeStyle = isSelected ? "rgba(120,200,255,0.7)" : "rgba(255,255,255,0.35)";
      ctx.lineWidth = isSelected ? 2 : 1;
      ctx.setLineDash(isSelected ? [] : [3, 3]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // 3D 그라데이션 (2D에서도 적용)
    const grad = ctx.createRadialGradient(
      x - radius * 0.35,
      y - radius * 0.4,
      Math.max(1, radius * 0.15),
      x,
      y,
      radius * 1.1,
    );
    grad.addColorStop(0, gradientStops[0]);
    grad.addColorStop(0.5, color);
    grad.addColorStop(1, gradientStops[2]);

    ctx.beginPath();
    ctx.arc(x, y, radius, 0, TWO_PI);
    ctx.fillStyle = grad;
    ctx.fill();

    // 3D 모드일 때 추가 효과
    if (is3DMode()) {
      ctx.strokeStyle = `rgba(255,255,255,${0.12 + 0.08 * Math.sin(phase)})`;
      ctx.lineWidth = 0.6;
      ctx.stroke();
    }
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

    planetHitboxes = [];

    // 태양 (가장 먼저 — 배경에 위치)
    const sunRadius = (is3DMode() ? 18 : 15) * sceneScale;
    drawSunGlow(cx, cy, sunRadius);

    // 행성 렌더링 (먼 행성부터 — 오버랩 시 깊이감)
    for (const planet of sortedPlanets) {
      const orbitRadius = planet.orbitRadius * zoom * sceneScale;

      // 궤도선
      drawOrbit(cx, cy, orbitRadius);

      // 궤적 업데이트 및 그리기
      const planetAngle = planet.angle + viewRotation;
      const px = cx + Math.cos(planetAngle) * orbitRadius;
      const py = cy + Math.sin(planetAngle) * orbitRadius * 0.92;

      // 궤적에 현재 위치 추가
      if (state.isPlaying) {
        planet.trail.push({ x: px, y: py });
        if (planet.trail.length > planet.maxTrail) {
          planet.trail.shift();
        }
      }
      drawTrail(planet.trail, planet.color);

      // 행성 크기 (선택/호버 시 약간 커짐)
      let displayRadius = planet.radius * sceneScale * Math.max(0.85, zoom * 0.95);
      const isSelected = state.selectedPlanet === planet;
      const isHovered = state.hoveredPlanet === planet;
      if (isSelected) {
        displayRadius *= 1.2;
      } else if (isHovered) {
        displayRadius *= 1.1;
      }

      // 토성 고리 — 뒤쪽 먼저 그리기
      if (planet.hasRings) {
        drawSaturnRings(px, py, displayRadius, planet.ringInnerRadius, planet.ringOuterRadius, planetAngle);
      }

      // 행성 본체
      drawPlanetBody(px, py, displayRadius, planet.color, planet.gradientStops, planet.angle, isSelected, isHovered);

      // 토성 고리 — 앞쪽 (본체 위에)
      if (planet.hasRings) {
        // 이미 본체 위에 그리는 로직은 drawSaturnRings에서 처리됨
      }

      // 라벨
      if (state.showLabels) {
        ctx.fillStyle = isSelected ? "#ffffff" : isHovered ? "#e8eeff" : "rgba(216,224,255,0.8)";
        ctx.font = `${isSelected ? "bold " : ""}${is3DMode() ? 12 : 10}px sans-serif`;
        ctx.textAlign = "center";
        ctx.fillText(planet.name, px, py - displayRadius - 8);
        ctx.textAlign = "start";
      }

      // 클릭 검출용 히트박스 저장
      planetHitboxes.push({
        x: px,
        y: py,
        radius: displayRadius + 6,
        planet,
      });
    }

    if (typeof performance !== "undefined" && typeof performance.mark === "function") {
      performance.mark(PERF_MARK_END);
    }
    if (typeof performance !== "undefined" && typeof performance.measure === "function") {
      performance.measure(PERF_MEASURE_NAME, PERF_MARK_START, PERF_MARK_END);
    }

  }

  function hitTest(mx, my) {
    // 뒤에서부터 (앞에 있는 행성부터) 체크
    for (let i = planetHitboxes.length - 1; i >= 0; i -= 1) {
      const hb = planetHitboxes[i];
      const dx = mx - hb.x;
      const dy = my - hb.y;
      if (dx * dx + dy * dy <= hb.radius * hb.radius) {
        return hb.planet || planets.find((p) => p.name === hb.planet?.name);
      }
    }
    return null;
  }

  return { resizeCanvas, render, hitTest };
}
