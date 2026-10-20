import { initializeSpaceBackdrop } from "./three-backdrop.js";

const canvas = document.getElementById("orbit-eclipse-canvas");
const threeLayer = document.getElementById("orbit-eclipse-three-layer");
const lessonModeSelect = document.getElementById("lesson-mode");
const lessonSpeedSelect = document.getElementById("lesson-speed");
const lessonRenderModeSelect = document.getElementById("lesson-render-mode");
const lessonPauseButton = document.getElementById("lesson-pause-button");
const lessonExplanation = document.getElementById("lesson-explanation");

if (!canvas || !lessonModeSelect || !lessonSpeedSelect || !lessonRenderModeSelect || !lessonExplanation) {
  throw new Error("orbit-eclipse page is missing required elements.");
}

const ctx = canvas.getContext("2d");
if (!ctx) {
  throw new Error("2D canvas context is required.");
}

const TAU = Math.PI * 2;
const EARTH_ORBIT_RATE = 0.35; // 지구 공전 각속도 (rad/s)
const MOON_ORBIT_RATE = 1.3; // 자전·공전 모드에서 달의 공전 각속도 (rad/s)
const EARTH_SPIN_RATE = 3.4; // 지구 자전 각속도 — 보기 쉽게 실제보다 많이 느리게
const EARTH_AXIS_TILT = (Math.PI / 180) * 23.4; // 지구 자전축 기울기
const ORBIT_FLATTEN = 0.56; // 3D 보기 모드 궤도 원근
const ORBIT_TILT = Math.PI / 6;

const LESSONS = {
  "rotation-revolution": {
    title: "자전과 공전",
    text: "지구는 스스로 빙글빙글 자전하고(하루), 태양 주위를 한 바퀴 공전해요(1년). 달은 지구 주위를 공전해요.",
  },
  "solar-eclipse": {
    title: "일식",
    text: "달이 태양과 지구 사이에 정확히 오면 달의 그림자가 지구에 드리워져서, 낮에도 해가 어둡게 가려져요.",
  },
  "lunar-eclipse": {
    title: "월식",
    text: "지구가 태양과 달 사이에 오면 지구 그림자에 들어간 달이 어둡다가 붉게 물들어요. 바로 혈월이에요.",
  },
};

const state = {
  elapsed: 0,
  speed: 1,
  lessonMode: "rotation-revolution",
  renderMode: "2d",
  paused: false,
  lastTs: 0,
};

let viewportWidth = canvas.width;
let viewportHeight = canvas.height;

function resizeCanvas() {
  const parent = canvas.parentElement;
  const baseWidth = parent ? Math.floor(parent.getBoundingClientRect().width - 2) : 960;
  // 좁은 화면에서는 카드 폭을 그대로 사용한다 (760px 강제 최소폭은 모바일에서 넘친다).
  viewportWidth = Math.max(320, baseWidth || 960);
  viewportHeight = Math.max(280, Math.floor(viewportWidth * 0.56));

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

function computeMoonAngle(progress, earthAngle) {
  // 일식·월식 모드에서는 실제 궤도 위의 하나의 달이 태양–지구 정렬선을 주기적으로 지나간다.
  const wobble = Math.sin(progress * 0.9) * 0.38;
  if (state.lessonMode === "solar-eclipse") {
    return earthAngle + Math.PI + wobble; // 달이 태양 쪽(태양–지구 사이)으로 정렬
  }
  if (state.lessonMode === "lunar-eclipse") {
    return earthAngle + wobble; // 달이 태양 반대쪽(지구 그림자)으로 정렬
  }
  return progress * MOON_ORBIT_RATE;
}

function drawOrbit(cx, cy, radius, color = "rgba(148,163,184,0.28)") {
  ctx.save();
  ctx.setLineDash([5, 7]);
  ctx.beginPath();
  if (state.renderMode === "3d") {
    ctx.ellipse(cx, cy, radius, radius * ORBIT_FLATTEN, ORBIT_TILT, 0, Math.PI * 2);
  } else {
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  }
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.2;
  ctx.stroke();
  ctx.restore();
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

function pathRoundRect(x, y, width, height, radius) {
  ctx.beginPath();
  if (typeof ctx.roundRect === "function") {
    ctx.roundRect(x, y, width, height, radius);
    return;
  }
  const r = Math.min(radius, width / 2, height / 2);
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + width, y, x + width, y + height, r);
  ctx.arcTo(x + width, y + height, x, y + height, r);
  ctx.arcTo(x, y + height, x, y, r);
  ctx.arcTo(x, y, x + width, y, r);
  ctx.closePath();
}

function mixColor(from, to, t) {
  const clamped = Math.max(0, Math.min(1, t));
  const r = Math.round(from[0] + (to[0] - from[0]) * clamped);
  const g = Math.round(from[1] + (to[1] - from[1]) * clamped);
  const b = Math.round(from[2] + (to[2] - from[2]) * clamped);
  return `rgb(${r}, ${g}, ${b})`;
}

function drawVignette(cx, cy, width, height) {
  const inner = Math.min(width, height) * 0.42;
  const outer = Math.max(width, height) * 0.74;
  const vignette = ctx.createRadialGradient(cx, cy, inner, cx, cy, outer);
  vignette.addColorStop(0, "rgba(2, 6, 23, 0)");
  vignette.addColorStop(1, "rgba(2, 6, 23, 0.4)");
  ctx.fillStyle = vignette;
  ctx.fillRect(0, 0, width, height);
}

function drawSun(x, y, radius, progress) {
  const pulse = 1 + Math.sin(progress * 2.1) * 0.02;
  const r = radius * pulse;

  const halo = ctx.createRadialGradient(x, y, r * 0.5, x, y, r * 3.4);
  halo.addColorStop(0, "rgba(251, 191, 36, 0.34)");
  halo.addColorStop(0.45, "rgba(245, 158, 11, 0.12)");
  halo.addColorStop(1, "rgba(245, 158, 11, 0)");
  ctx.fillStyle = halo;
  ctx.beginPath();
  ctx.arc(x, y, r * 3.4, 0, TAU);
  ctx.fill();

  const core = ctx.createRadialGradient(x - r * 0.28, y - r * 0.28, r * 0.12, x, y, r);
  core.addColorStop(0, "#fffbeb");
  core.addColorStop(0.38, "#fde68a");
  core.addColorStop(0.72, "#f59e0b");
  core.addColorStop(1, "#ea580c");
  ctx.fillStyle = core;
  ctx.beginPath();
  ctx.arc(x, y, r, 0, TAU);
  ctx.fill();
}

function drawLitSphere(x, y, radius, baseColor, lightX, lightY, options = {}) {
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

  if (typeof options.detail === "function") {
    options.detail();
  }

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

  if (options.atmosphere) {
    ctx.save();
    ctx.shadowColor = options.atmosphere;
    ctx.shadowBlur = 10;
    ctx.strokeStyle = options.atmosphere;
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  }
}

function drawEarthContinents(x, y, radius, spinAngle) {
  ctx.save();
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, TAU);
  ctx.clip();
  ctx.fillStyle = "rgba(74, 222, 128, 0.55)";
  const blobs = [
    [0, 0.62, -0.28, 0.36],
    [Math.PI * 0.8, 0.44, 0.3, 0.28],
    [Math.PI * 1.6, 0.32, -0.05, 0.22],
  ];
  for (const [phase, size, offsetY, squash] of blobs) {
    const bx = x + Math.cos(spinAngle + phase) * radius * 0.78;
    const by = y + offsetY * radius;
    ctx.beginPath();
    ctx.ellipse(bx, by, radius * size * 0.5, radius * size * 0.5 * squash, 0, 0, TAU);
    ctx.fill();
  }
  ctx.restore();
}

function drawEarthAxis(x, y, radius) {
  const ax = Math.cos(EARTH_AXIS_TILT);
  const ay = Math.sin(EARTH_AXIS_TILT);
  ctx.save();
  ctx.strokeStyle = "rgba(226, 232, 240, 0.5)";
  ctx.lineWidth = 1;
  ctx.setLineDash([3, 4]);
  ctx.beginPath();
  ctx.moveTo(x - ax * radius * 1.6, y - ay * radius * 1.6);
  ctx.lineTo(x + ax * radius * 1.6, y + ay * radius * 1.6);
  ctx.stroke();
  ctx.restore();
}

function drawMoonCraters(x, y, radius, moonAngle) {
  ctx.save();
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, TAU);
  ctx.clip();
  ctx.fillStyle = "rgba(100, 116, 139, 0.42)";
  const craters = [
    [0.3, -0.18, 0.3],
    [Math.PI * 0.75, 0.26, 0.2],
    [Math.PI * 1.35, -0.32, 0.16],
  ];
  for (const [phase, offsetY, size] of craters) {
    const craterX = x + Math.cos(moonAngle + phase) * radius * 0.62;
    const craterY = y + offsetY * radius;
    ctx.beginPath();
    ctx.arc(craterX, craterY, radius * size, 0, TAU);
    ctx.fill();
  }
  ctx.restore();
}

function drawSpinArrow(x, y, radius, spinAngle) {
  const arrowRadius = radius * 1.95;
  const sweep = 1.5;
  const start = spinAngle % TAU;
  const end = start + sweep;
  ctx.save();
  ctx.strokeStyle = "rgba(125, 211, 252, 0.6)";
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.arc(x, y, arrowRadius, start, end);
  ctx.stroke();

  const tipX = x + Math.cos(end) * arrowRadius;
  const tipY = y + Math.sin(end) * arrowRadius;
  const dir = end + Math.PI / 2;
  ctx.beginPath();
  ctx.moveTo(tipX + Math.cos(dir + Math.PI - 0.45) * 8, tipY + Math.sin(dir + Math.PI - 0.45) * 8);
  ctx.lineTo(tipX, tipY);
  ctx.lineTo(tipX + Math.cos(dir + Math.PI + 0.45) * 8, tipY + Math.sin(dir + Math.PI + 0.45) * 8);
  ctx.stroke();
  ctx.restore();
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

function drawAlignmentGuide(sunX, sunY, earthX, earthY, extend) {
  const dx = earthX - sunX;
  const dy = earthY - sunY;
  const length = Math.max(1, Math.hypot(dx, dy));
  const ux = dx / length;
  const uy = dy / length;
  ctx.save();
  ctx.strokeStyle = "rgba(226, 232, 240, 0.16)";
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 8]);
  ctx.beginPath();
  ctx.moveTo(sunX - ux * 48, sunY - uy * 48);
  ctx.lineTo(earthX + ux * extend, earthY + uy * extend);
  ctx.stroke();
  ctx.restore();
}

function drawAlignmentIndicator(label, ratio, statusText = "") {
  const x = 16;
  const y = 16;
  const width = Math.min(252, viewportWidth - 32);
  const barHeight = 10;
  const height = statusText ? 68 : 46;
  const clamped = Math.max(0, Math.min(1, ratio));

  ctx.save();
  ctx.fillStyle = "rgba(7, 12, 26, 0.78)";
  pathRoundRect(x, y, width, height, 12);
  ctx.fill();
  ctx.strokeStyle = "rgba(148, 163, 184, 0.26)";
  ctx.lineWidth = 1;
  pathRoundRect(x + 0.5, y + 0.5, width - 1, height - 1, 12);
  ctx.stroke();

  ctx.font = "700 11px 'JetBrains Mono', ui-monospace, monospace";
  ctx.fillStyle = "#93c5fd";
  ctx.textAlign = "left";
  ctx.textBaseline = "alphabetic";
  ctx.fillText(label, x + 14, y + 20);

  const trackX = x + 14;
  const trackY = y + 28;
  const trackWidth = width - 28;
  ctx.fillStyle = "rgba(30, 41, 59, 0.9)";
  pathRoundRect(trackX, trackY, trackWidth, barHeight, 5);
  ctx.fill();

  if (clamped > 0.02) {
    const fill = ctx.createLinearGradient(trackX, trackY, trackX + trackWidth, trackY);
    fill.addColorStop(0, "#60a5fa");
    fill.addColorStop(1, "#22d3ee");
    ctx.fillStyle = fill;
    pathRoundRect(trackX, trackY, Math.max(barHeight, trackWidth * clamped), barHeight, 5);
    ctx.fill();
  }

  if (statusText) {
    ctx.font = "500 11px 'JetBrains Mono', ui-monospace, monospace";
    ctx.fillStyle = "#cbd5e1";
    let text = statusText;
    while (ctx.measureText(text).width > trackWidth && text.length > 5) {
      text = `${text.slice(0, -2)}…`;
    }
    ctx.fillText(text, x + 14, y + 56);
  }
  ctx.restore();
}

function drawEclipseShadow(lessonMode, sunX, sunY, earthX, earthY, moonX, moonY, earthRadius, moonRadius, ratio) {
  const strength = Math.max(0, Math.min(1, ratio));
  if (strength < 0.12) {
    return;
  }
  const alphaScale = (strength - 0.12) / 0.88;

  if (lessonMode === "solar-eclipse") {
    // 달 → 지구: 달의 그림자(본그림자 + 반그림자)가 지구에 드리워진다.
    const distToEarth = Math.max(1, Math.hypot(earthX - moonX, earthY - moonY));
    const ux = (earthX - moonX) / distToEarth;
    const uy = (earthY - moonY) / distToEarth;
    const endX = moonX + ux * distToEarth * 1.12;
    const endY = moonY + uy * distToEarth * 1.12;
    drawShadowCone(moonX, moonY, endX, endY, moonRadius * 0.92, moonRadius * 0.3, 0.55 * alphaScale);
    drawShadowCone(moonX, moonY, endX, endY, moonRadius * 1.9, moonRadius * 1.0, 0.24 * alphaScale);
  } else if (lessonMode === "lunar-eclipse") {
    // 지구 → 태양 반대편: 지구 그림자 원뿔 속으로 달이 들어간다.
    const distToSun = Math.max(1, Math.hypot(earthX - sunX, earthY - sunY));
    const ux = (earthX - sunX) / distToSun;
    const uy = (earthY - sunY) / distToSun;
    const distToMoon = Math.max(1, Math.hypot(moonX - earthX, moonY - earthY));
    const length = distToMoon * 1.45;
    const endX = earthX + ux * length;
    const endY = earthY + uy * length;
    drawShadowCone(earthX, earthY, endX, endY, earthRadius * 0.95, earthRadius * 0.4, 0.5 * alphaScale);
    drawShadowCone(earthX, earthY, endX, endY, earthRadius * 2.0, earthRadius * 1.25, 0.22 * alphaScale);
  }
}

function drawEarthShadowSpot(earthX, earthY, earthRadius, moonX, moonY, ratio) {
  if (ratio < 0.25) {
    return;
  }
  const strength = (ratio - 0.25) / 0.75;
  const dx = moonX - earthX;
  const dy = moonY - earthY;
  const distance = Math.max(1, Math.hypot(dx, dy));
  const spotX = earthX + (dx / distance) * earthRadius * 0.4;
  const spotY = earthY + (dy / distance) * earthRadius * 0.4;
  const spot = ctx.createRadialGradient(spotX, spotY, 0, spotX, spotY, earthRadius * 0.72);
  spot.addColorStop(0, `rgba(2, 6, 23, ${0.72 * strength})`);
  spot.addColorStop(1, "rgba(2, 6, 23, 0)");
  ctx.fillStyle = spot;
  ctx.beginPath();
  ctx.arc(spotX, spotY, earthRadius * 0.72, 0, TAU);
  ctx.fill();
}

function drawLabel(text, x, y, align = "left") {
  ctx.save();
  ctx.font = "700 11px 'JetBrains Mono', ui-monospace, monospace";
  const textWidth = ctx.measureText(text).width;
  const chipWidth = textWidth + 16;
  const chipHeight = 20;
  let chipX = align === "center" ? x - chipWidth / 2 : x;
  chipX = Math.max(6, Math.min(chipX, viewportWidth - chipWidth - 6));
  const chipY = Math.max(6, Math.min(y - chipHeight / 2, viewportHeight - chipHeight - 6));

  ctx.fillStyle = "rgba(7, 12, 26, 0.72)";
  pathRoundRect(chipX, chipY, chipWidth, chipHeight, chipHeight / 2);
  ctx.fill();
  ctx.strokeStyle = "rgba(255, 255, 255, 0.14)";
  ctx.lineWidth = 1;
  pathRoundRect(chipX + 0.5, chipY + 0.5, chipWidth - 1, chipHeight - 1, chipHeight / 2);
  ctx.stroke();
  ctx.fillStyle = "#e2e8f0";
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  ctx.fillText(text, chipX + 8, chipY + chipHeight / 2 + 0.5);
  ctx.restore();
}

function renderScene(progress) {
  const width = viewportWidth;
  const height = viewportHeight;
  const cx = width / 2;
  const cy = height / 2;

  const earthOrbitRadius = Math.min(width * 0.28, height * 0.33);
  const moonOrbitRadius = Math.max(34, Math.min(width * 0.085, height * 0.095));

  const earthAngle = progress * EARTH_ORBIT_RATE;
  const moonAngle = computeMoonAngle(progress, earthAngle);
  const spinAngle = progress * EARTH_SPIN_RATE;

  const earthPoint = projectOrbitPosition(cx, cy, earthOrbitRadius, earthAngle);
  const moonPoint = projectOrbitPosition(earthPoint.x, earthPoint.y, moonOrbitRadius, moonAngle);
  const earthX = earthPoint.x;
  const earthY = earthPoint.y;
  const moonX = moonPoint.x;
  const moonY = moonPoint.y;
  const depthScale = state.renderMode === "3d" ? (0.86 + ((earthY / height) * 0.3)) : 1;
  const sunRadius = Math.max(26, Math.min(40, width * 0.045));
  const earthRadius = Math.max(13, 18 * depthScale);
  const moonRadius = Math.max(8, 10 * depthScale);

  // 2D 장면은 투명하게 그린다 — 뒤쪽 .three-layer 별 배경과 한 장면으로 합쳐진다.
  ctx.clearRect(0, 0, width, height);
  drawVignette(cx, cy, width, height);

  const alignmentDist = computeLineDistance(moonX, moonY, cx, cy, earthX, earthY);
  const ratio = 1 - Math.min(1, alignmentDist / (moonRadius * 2.6));

  if (state.lessonMode !== "rotation-revolution") {
    drawAlignmentGuide(cx, cy, earthX, earthY, moonOrbitRadius * 2.4);
  }

  drawOrbit(cx, cy, earthOrbitRadius);
  drawOrbit(earthX, earthY, moonOrbitRadius, "rgba(147,197,253,0.3)");

  drawSun(cx, cy, sunRadius, progress);

  const drawMoonBody = () => {
    const moonColor =
      state.lessonMode === "lunar-eclipse"
        ? mixColor([211, 214, 221], [185, 64, 56], ratio)
        : "#d1d5db";
    drawLitSphere(moonX, moonY, moonRadius, moonColor, cx, cy, {
      detail: () => drawMoonCraters(moonX, moonY, moonRadius, moonAngle),
    });
    if (state.lessonMode === "lunar-eclipse" && ratio > 0.55) {
      ctx.save();
      ctx.shadowColor = "rgba(239, 68, 68, 0.75)";
      ctx.shadowBlur = 20 * ratio;
      ctx.strokeStyle = "rgba(248, 113, 113, 0.35)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(moonX, moonY, moonRadius, 0, TAU);
      ctx.stroke();
      ctx.restore();
    }
  };

  const drawEarthBody = () => {
    drawLitSphere(earthX, earthY, earthRadius, "#3b82f6", cx, cy, {
      atmosphere: "rgba(96, 165, 250, 0.6)",
      detail: () => drawEarthContinents(earthX, earthY, earthRadius, spinAngle),
    });
    drawEarthAxis(earthX, earthY, earthRadius);
  };

  const moonBehindEarth = state.renderMode === "3d" && moonY > earthY;
  if (moonBehindEarth) {
    drawEarthBody();
    drawMoonBody();
  } else {
    drawMoonBody();
    drawEarthBody();
  }

  drawLabel("태양", cx, cy + sunRadius + 28, "center");
  drawLabel("지구", earthX + earthRadius + 14, earthY - earthRadius - 10);
  drawLabel("달", moonX + moonRadius + 12, moonY - moonRadius - 8);

  if (state.lessonMode === "solar-eclipse") {
    drawEclipseShadow("solar-eclipse", cx, cy, earthX, earthY, moonX, moonY, earthRadius, moonRadius, ratio);
    drawEarthShadowSpot(earthX, earthY, earthRadius, moonX, moonY, ratio);
    const status =
      ratio > 0.85
        ? "개기일식! 달이 태양빛을 가려요"
        : ratio > 0.45
          ? "부분 일식 — 그림자가 지구에 닿았어요"
          : "달이 태양과 지구 사이로 오는 중…";
    drawAlignmentIndicator("일식 정렬도", ratio, status);
  } else if (state.lessonMode === "lunar-eclipse") {
    drawEclipseShadow("lunar-eclipse", cx, cy, earthX, earthY, moonX, moonY, earthRadius, moonRadius, ratio);
    const status =
      ratio > 0.85
        ? "혈월! 달이 온통 붉게 물들어요"
        : ratio > 0.45
          ? "달이 지구 그림자에 들어왔어요"
          : "달이 그림자 쪽으로 다가가는 중…";
    drawAlignmentIndicator("월식 정렬도", ratio, status);
  } else {
    drawSpinArrow(earthX, earthY, earthRadius, spinAngle);
    const yearRatio = (((earthAngle % TAU) + TAU) % TAU) / TAU;
    const spinCount = Math.floor((progress * EARTH_SPIN_RATE) / TAU);
    const orbitCount = Math.floor(earthAngle / TAU);
    drawAlignmentIndicator(
      "지구의 1년 (공전 1바퀴) 진행",
      yearRatio,
      `자전 ${spinCount}회 · 공전 ${orbitCount}바퀴`,
    );
  }
}

function animate(ts) {
  if (!state.lastTs) {
    state.lastTs = ts;
  }
  const dt = Math.min(0.1, Math.max(0, (ts - state.lastTs) / 1000));
  state.lastTs = ts;
  if (!state.paused) {
    state.elapsed += dt * state.speed;
  }

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

  if (lessonPauseButton) {
    lessonPauseButton.addEventListener("click", () => {
      state.paused = !state.paused;
      lessonPauseButton.textContent = state.paused ? "▶ 재생" : "⏸ 일시정지";
      lessonPauseButton.setAttribute("aria-pressed", state.paused ? "true" : "false");
    });
  }

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
