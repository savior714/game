import { initializeSpaceBackdrop } from "./three-backdrop.js";

const canvas = document.getElementById("orbit-eclipse-canvas");
const threeLayer = document.getElementById("orbit-eclipse-three-layer");
const lessonModeSelect = document.getElementById("lesson-mode");
const lessonSpeedSelect = document.getElementById("lesson-speed");
const lessonRenderModeSelect = document.getElementById("lesson-render-mode");
const lessonExplanation = document.getElementById("lesson-explanation");

if (!canvas || !lessonModeSelect || !lessonSpeedSelect || !lessonRenderModeSelect || !lessonExplanation) {
  throw new Error("orbit-eclipse page is missing required elements.");
}

const ctx = canvas.getContext("2d");
if (!ctx) {
  throw new Error("2D canvas context is required.");
}

const LESSONS = {
  "rotation-revolution": {
    title: "자전과 공전",
    text: "지구는 스스로 빙글빙글 자전하고, 태양 주위를 크게 공전해요. 달은 지구 주위를 돌아요.",
  },
  "solar-eclipse": {
    title: "일식",
    text: "달이 태양과 지구 사이에 오면, 태양빛이 일부 가려져 낮에도 어둡게 보여요.",
  },
  "lunar-eclipse": {
    title: "월식",
    text: "지구가 태양과 달 사이에 오면, 지구 그림자가 달을 가려서 달이 어둡거나 붉게 보여요.",
  },
};

const state = {
  elapsed: 0,
  speed: 1,
  lessonMode: "rotation-revolution",
  renderMode: "2d",
  lastTs: 0,
};

let viewportWidth = canvas.width;
let viewportHeight = canvas.height;

function resizeCanvas() {
  const parent = canvas.parentElement;
  const baseWidth = parent ? Math.floor(parent.getBoundingClientRect().width - 2) : 960;
  viewportWidth = Math.max(760, baseWidth || 960);
  viewportHeight = Math.max(440, Math.floor(viewportWidth * 0.56));

  const dpr = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
  canvas.width = Math.floor(viewportWidth * dpr);
  canvas.height = Math.floor(viewportHeight * dpr);
  canvas.style.width = `${viewportWidth}px`;
  canvas.style.height = `${viewportHeight}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function updateLessonText() {
  const lesson = LESSONS[state.lessonMode];
  lessonExplanation.textContent = `${lesson.title}: ${lesson.text}`;
}

function drawOrbit(cx, cy, radius, color = "rgba(255,255,255,0.18)") {
  ctx.beginPath();
  if (state.renderMode === "3d") {
    ctx.ellipse(cx, cy, radius, radius * 0.56, Math.PI / 6, 0, Math.PI * 2);
  } else {
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  }
  ctx.strokeStyle = color;
  ctx.lineWidth = 1;
  ctx.stroke();
}

function projectOrbitPosition(cx, cy, radius, angle) {
  if (state.renderMode === "3d") {
    const flatten = 0.56;
    const tilt = Math.PI / 6;
    const px = Math.cos(angle) * radius;
    const py = Math.sin(angle) * radius * flatten;
    return {
      x: cx + Math.cos(tilt) * px - Math.sin(tilt) * py,
      y: cy + Math.sin(tilt) * px + Math.cos(tilt) * py,
    };
  }

  return {
    x: cx + Math.cos(angle) * radius,
    y: cy + Math.sin(angle) * radius,
  };
}

function drawBody(x, y, radius, fill, glow = 0) {
  if (glow > 0) {
    ctx.shadowColor = fill;
    ctx.shadowBlur = glow;
  } else {
    ctx.shadowBlur = 0;
  }
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.shadowBlur = 0;
}

function drawLitSphere(x, y, radius, baseColor, lightX, lightY) {
  if (state.renderMode !== "3d") {
    drawBody(x, y, radius, baseColor);
    return;
  }

  const lightAngle = Math.atan2(lightY - y, lightX - x);
  const highlightX = x + Math.cos(lightAngle) * radius * 0.35;
  const highlightY = y + Math.sin(lightAngle) * radius * 0.35;
  const baseGradient = ctx.createRadialGradient(
    highlightX,
    highlightY,
    Math.max(1, radius * 0.2),
    x,
    y,
    radius * 1.05,
  );
  baseGradient.addColorStop(0, "rgba(255,255,255,0.85)");
  baseGradient.addColorStop(0.32, baseColor);
  baseGradient.addColorStop(1, "rgba(8,12,24,0.92)");

  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fillStyle = baseGradient;
  ctx.fill();

  const nx = Math.cos(lightAngle + Math.PI / 2);
  const ny = Math.sin(lightAngle + Math.PI / 2);
  const terminatorGradient = ctx.createLinearGradient(
    x - nx * radius,
    y - ny * radius,
    x + nx * radius,
    y + ny * radius,
  );
  terminatorGradient.addColorStop(0, "rgba(2,4,10,0.58)");
  terminatorGradient.addColorStop(0.45, "rgba(2,4,10,0.15)");
  terminatorGradient.addColorStop(0.55, "rgba(2,4,10,0)");
  terminatorGradient.addColorStop(1, "rgba(2,4,10,0.46)");

  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fillStyle = terminatorGradient;
  ctx.fill();
}

function computeLineDistance(px, py, ax, ay, bx, by) {
  const abx = bx - ax;
  const aby = by - ay;
  const apx = px - ax;
  const apy = py - ay;
  const cross = Math.abs(abx * apy - aby * apx);
  const magnitude = Math.max(1, Math.hypot(abx, aby));
  return cross / magnitude;
}

function drawShadowCone(fromX, fromY, toX, toY, nearRadius, farRadius, alpha) {
  const dx = toX - fromX;
  const dy = toY - fromY;
  const length = Math.max(1, Math.hypot(dx, dy));
  const nx = -dy / length;
  const ny = dx / length;

  const sx1 = fromX + nx * nearRadius;
  const sy1 = fromY + ny * nearRadius;
  const sx2 = fromX - nx * nearRadius;
  const sy2 = fromY - ny * nearRadius;
  const ex1 = toX + nx * farRadius;
  const ey1 = toY + ny * farRadius;
  const ex2 = toX - nx * farRadius;
  const ey2 = toY - ny * farRadius;

  const gradient = ctx.createLinearGradient(fromX, fromY, toX, toY);
  gradient.addColorStop(0, `rgba(8,12,26,${alpha})`);
  gradient.addColorStop(1, "rgba(8,12,26,0)");
  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.moveTo(sx1, sy1);
  ctx.lineTo(ex1, ey1);
  ctx.lineTo(ex2, ey2);
  ctx.lineTo(sx2, sy2);
  ctx.closePath();
  ctx.fill();
}

function drawAlignmentIndicator(label, ratio) {
  const x = 16;
  const y = 16;
  const width = 180;
  const height = 12;
  const clamped = Math.max(0, Math.min(1, ratio));

  ctx.fillStyle = "rgba(10, 18, 36, 0.72)";
  ctx.fillRect(x - 8, y - 8, width + 16, 44);
  ctx.strokeStyle = "rgba(148, 163, 184, 0.32)";
  ctx.strokeRect(x - 8, y - 8, width + 16, 44);

  ctx.fillStyle = "rgba(30, 41, 59, 0.9)";
  ctx.fillRect(x, y + 14, width, height);

  const fill = ctx.createLinearGradient(x, y, x + width, y);
  fill.addColorStop(0, "#60a5fa");
  fill.addColorStop(1, "#22d3ee");
  ctx.fillStyle = fill;
  ctx.fillRect(x, y + 14, width * clamped, height);

  ctx.fillStyle = "#cbd5e1";
  ctx.font = "12px sans-serif";
  ctx.fillText(label, x, y + 8);
}

function drawEclipseShadow(lessonMode, sunX, sunY, earthX, earthY, moonX, moonY, earthRadius, moonRadius) {
  if (lessonMode === "solar-eclipse") {
    const axisX = earthX + (earthX - sunX) * 0.86;
    const axisY = earthY + (earthY - sunY) * 0.86;
    drawShadowCone(moonX, moonY, axisX, axisY, moonRadius * 0.9, moonRadius * 0.2, 0.5);
    drawShadowCone(moonX, moonY, axisX, axisY, moonRadius * 1.8, moonRadius * 0.95, 0.25);
  } else if (lessonMode === "lunar-eclipse") {
    const axisX = moonX + (moonX - sunX) * 0.12;
    const axisY = moonY + (moonY - sunY) * 0.12;
    drawShadowCone(earthX, earthY, axisX, axisY, earthRadius * 0.9, earthRadius * 0.35, 0.45);
    drawShadowCone(earthX, earthY, axisX, axisY, earthRadius * 1.95, earthRadius * 1.15, 0.23);
  }
}

function drawLabel(text, x, y) {
  ctx.fillStyle = "#dbeafe";
  ctx.font = "14px sans-serif";
  ctx.fillText(text, x, y);
}

function renderScene(progress) {
  const width = viewportWidth;
  const height = viewportHeight;
  const cx = width / 2;
  const cy = height / 2;

  const earthOrbitRadius = Math.min(width * 0.28, height * 0.33);
  const moonOrbitRadius = Math.min(width * 0.085, height * 0.095);

  const earthAngle = progress * 0.35;
  const moonAngle = progress * 1.3;

  const earthPoint = projectOrbitPosition(cx, cy, earthOrbitRadius, earthAngle);
  const moonPoint = projectOrbitPosition(earthPoint.x, earthPoint.y, moonOrbitRadius, moonAngle);
  const earthX = earthPoint.x;
  const earthY = earthPoint.y;
  const moonX = moonPoint.x;
  const moonY = moonPoint.y;
  const depthScale = state.renderMode === "3d" ? (0.86 + ((earthY / height) * 0.3)) : 1;
  const sunRadius = 36;
  const earthRadius = 18 * depthScale;
  const moonRadius = 10 * depthScale;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#060b21";
  ctx.fillRect(0, 0, width, height);

  drawOrbit(cx, cy, earthOrbitRadius);
  drawOrbit(earthX, earthY, moonOrbitRadius, "rgba(147,197,253,0.25)");
  drawBody(cx, cy, sunRadius, "#fbbf24", 30);

  const frontFirst = state.renderMode !== "3d" || moonY <= earthY;
  if (frontFirst) {
    drawLitSphere(moonX, moonY, moonRadius, "#d1d5db", cx, cy);
    drawLitSphere(earthX, earthY, earthRadius, "#3b82f6", cx, cy);
  } else {
    drawLitSphere(earthX, earthY, earthRadius, "#3b82f6", cx, cy);
    drawLitSphere(moonX, moonY, moonRadius, "#d1d5db", cx, cy);
  }

  drawLabel("태양", cx - 14, cy + 58);
  drawLabel("지구", earthX + 16, earthY - 16);
  drawLabel("달", moonX + 10, moonY - 10);

  const solarDistance = computeLineDistance(earthX, earthY, cx, cy, moonX, moonY);
  const lunarDistance = computeLineDistance(moonX, moonY, cx, cy, earthX, earthY);

  if (state.lessonMode === "solar-eclipse") {
    const t = (Math.sin(progress * 0.7) + 1) / 2;
    const eclipseMoonX = cx + (earthX - cx) * t;
    const eclipseMoonY = cy + (earthY - cy) * t;
    const eclipseMoonRadius = 11 * (state.renderMode === "3d" ? depthScale : 1);
    drawLitSphere(eclipseMoonX, eclipseMoonY, eclipseMoonRadius, "#9ca3af", cx, cy);
    drawEclipseShadow("solar-eclipse", cx, cy, earthX, earthY, eclipseMoonX, eclipseMoonY, earthRadius, eclipseMoonRadius);
    ctx.fillStyle = "rgba(15, 23, 42, 0.4)";
    ctx.beginPath();
    ctx.arc(cx, cy, sunRadius, 0, Math.PI * 2);
    ctx.fill();
    const ratio = 1 - Math.min(1, computeLineDistance(earthX, earthY, cx, cy, eclipseMoonX, eclipseMoonY) / 35);
    drawAlignmentIndicator("일식 정렬도", ratio);
  } else if (state.lessonMode === "lunar-eclipse") {
    const t = (Math.sin(progress * 0.7) + 1) / 2;
    const eclipseMoonX = earthX + (moonX - earthX) * t;
    const eclipseMoonY = earthY + (moonY - earthY) * t;
    drawEclipseShadow("lunar-eclipse", cx, cy, earthX, earthY, eclipseMoonX, eclipseMoonY, earthRadius, moonRadius);
    drawLitSphere(eclipseMoonX, eclipseMoonY, moonRadius * 0.95, "#f87171", cx, cy);
    const ratio = 1 - Math.min(1, computeLineDistance(eclipseMoonX, eclipseMoonY, cx, cy, earthX, earthY) / 35);
    drawAlignmentIndicator("월식 정렬도", ratio);
  } else {
    drawAlignmentIndicator("자전·공전 정렬도", 1 - Math.min(1, (solarDistance + lunarDistance) / 140));
  }
}

function animate(ts) {
  if (!state.lastTs) {
    state.lastTs = ts;
  }
  const dt = (ts - state.lastTs) / 1000;
  state.lastTs = ts;
  state.elapsed += dt * state.speed;

  renderScene(state.elapsed);
  requestAnimationFrame(animate);
}

function attachHandlers() {
  lessonModeSelect.addEventListener("change", () => {
    state.lessonMode = lessonModeSelect.value;
    updateLessonText();
  });

  lessonSpeedSelect.addEventListener("change", () => {
    state.speed = Number(lessonSpeedSelect.value) || 1;
  });

  lessonRenderModeSelect.addEventListener("change", () => {
    state.renderMode = lessonRenderModeSelect.value === "3d" ? "3d" : "2d";
    renderScene(state.elapsed);
  });

  window.addEventListener("resize", () => {
    resizeCanvas();
    renderScene(state.elapsed);
  }, { passive: true });
}

resizeCanvas();
updateLessonText();
renderScene(0);
initializeSpaceBackdrop(threeLayer, { intensity: 1.05 });
attachHandlers();
requestAnimationFrame(animate);
