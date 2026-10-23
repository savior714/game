/*!
 * AIDEN POWER ISLAND 3D — 메인 게임 컨트롤러
 * 3D 발전소 섬(world.js), 물리 엔진(PowerPhysics), 사운드 합성기(audio.js),
 * 플로팅 계기판 오실로스코프, 진행 저장(aiden_electricity_lab_v1)을 하나로 연결한다.
 */

import { createSoundEngine } from "./audio.js";

// Load Three.js addons and the full diorama only after the initial page can paint.
let CAMERA_PRESETS = {};

const P = globalThis.PowerPhysics || (typeof window !== "undefined" ? window.PowerPhysics : null);
if (!P) {
  throw new Error("PowerPhysics module is required.");
}

const STORAGE_KEY = "aiden_electricity_lab_v1";
const STATION_IDS = ["circuit", "static", "fruit", "generator", "solar", "wind", "hydro"];
const STATION_TOTAL = STATION_IDS.length;
const TAU = Math.PI * 2;
const DEG = Math.PI / 180;

const doc = document;

function $(selector, root) {
  return (root || doc).querySelector(selector);
}

function $$(selector, root) {
  return Array.prototype.slice.call((root || doc).querySelectorAll(selector));
}

function setText(element, text) {
  if (element && element.textContent !== text) element.textContent = text;
}

function setWidth(element, ratio) {
  if (!element) return;
  const value = Math.round(P.clamp(ratio, 0, 1) * 1000) / 10;
  const next = value + "%";
  if (element.style.width !== next) element.style.width = next;
}

const loadingUi = {
  root: doc.getElementById("world-loading"),
  title: doc.getElementById("world-loading-title"),
  message: doc.getElementById("world-loading-message"),
  progress: doc.getElementById("world-loading-progress"),
  fill: doc.getElementById("world-loading-fill"),
  percent: doc.getElementById("world-loading-percent"),
  retry: doc.getElementById("world-loading-retry"),
};

function setLoadingProgress(value, message) {
  const percent = Math.round(P.clamp(value, 0, 100));
  if (loadingUi.root) loadingUi.root.hidden = false;
  if (loadingUi.progress) loadingUi.progress.setAttribute("aria-valuenow", String(percent));
  if (loadingUi.fill) loadingUi.fill.style.width = percent + "%";
  setText(loadingUi.percent, percent + "%");
  setText(loadingUi.message, message);
}

function finishLoading() {
  if (!loadingUi.root) return;
  loadingUi.root.setAttribute("aria-busy", "false");
  loadingUi.root.classList.add("is-ready");
  window.setTimeout(() => {
    loadingUi.root.hidden = true;
  }, 240);
}

function showBootError() {
  if (!loadingUi.root) return;
  loadingUi.root.hidden = false;
  loadingUi.root.classList.remove("is-ready");
  loadingUi.root.setAttribute("aria-busy", "false");
  setText(loadingUi.title, "발전소를 준비하지 못했어요");
  setText(loadingUi.message, "잠시 후 다시 시도해 주세요.");
  if (loadingUi.retry) {
    loadingUi.retry.hidden = false;
    loadingUi.retry.addEventListener("click", () => window.location.reload(), { once: true });
  }
}

function waitForAuthGate() {
  const gate = window.AidenAuthGate;
  if (!gate || typeof gate.isLocked !== "function") {
    return Promise.reject(new Error("Auth gate is unavailable"));
  }
  if (!gate.isLocked()) return Promise.resolve();
  return new Promise((resolve) => {
    window.addEventListener("auth-gate-unlocked", resolve, { once: true });
  });
}

function yieldForPaint() {
  return new Promise((resolve) => {
    window.setTimeout(() => window.setTimeout(resolve, 0), 0);
  });
}

/* ── 설정: 움직임 줄이기 · 진행 저장 · 사운드 ──────────────────── */

const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
let prefersReducedMotion = motionQuery.matches;
if (typeof motionQuery.addEventListener === "function") {
  motionQuery.addEventListener("change", (event) => {
    prefersReducedMotion = event.matches;
  });
}

const progress = { found: {}, energy: 0, sound: true };

function loadProgress() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const data = JSON.parse(raw);
    if (data && typeof data === "object") {
      if (Array.isArray(data.found)) {
        data.found.forEach((id) => {
          if (STATION_IDS.indexOf(id) !== -1) progress.found[id] = true;
        });
      }
      if (typeof data.energy === "number" && Number.isFinite(data.energy)) {
        progress.energy = Math.max(0, data.energy);
      }
      if (typeof data.sound === "boolean") progress.sound = data.sound;
    }
  } catch {
    /* 저장소 접근이 제한된 환경에서도 그대로 게임을 진행한다 */
  }
}

let saveTimer = 0;
function saveProgress(force) {
  if (!force) {
    if (saveTimer) return;
    saveTimer = window.setTimeout(() => {
      saveTimer = 0;
      saveProgress(true);
    }, 3500);
    return;
  }
  try {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        found: Object.keys(progress.found),
        energy: Math.round(progress.energy * 10) / 10,
        sound: progress.sound,
      })
    );
  } catch {
    /* 저장 실패 무시 */
  }
}

loadProgress();
const sound = createSoundEngine(progress.sound);

/* ── 토스트 & 화면 플래시 연출 ─────────────────────────────────── */

let toastTimer = 0;
function showToast(message) {
  const el = $("#event-toast");
  if (!el) return;
  el.textContent = message;
  el.hidden = false;
  if (toastTimer) window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    el.hidden = true;
  }, 2600);
}

let flashTimer = 0;
function triggerScreenFlash() {
  if (prefersReducedMotion) return;
  const flash = $("#surge-flash");
  if (!flash) return;
  flash.classList.add("is-active");
  if (flashTimer) window.clearTimeout(flashTimer);
  flashTimer = window.setTimeout(() => {
    flash.classList.remove("is-active");
  }, 240);
}

/* ── 미니 오실로스코프 / 터치패드 공통 캔버스 헬퍼 ─────────────── */

function createMiniScope(canvas) {
  const ctx = canvas.getContext("2d");
  const scope = { canvas, ctx, width: 0, height: 0 };

  function resize() {
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.max(220, Math.round(rect.width || canvas.clientWidth || 320));
    const height = Math.max(96, Math.round(rect.height || canvas.clientHeight || 112));
    if (width === scope.width && height === scope.height) return;
    scope.width = width;
    scope.height = height;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  scope.resize = resize;
  resize();
  if (window.ResizeObserver) {
    new window.ResizeObserver(resize).observe(canvas);
  }
  return scope;
}

function scopeBackdrop(ctx, w, h) {
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, "#091731");
  grad.addColorStop(1, "#040a18");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, w, h);

  ctx.strokeStyle = "rgba(120, 165, 255, 0.09)";
  ctx.lineWidth = 1;
  for (let x = 24; x < w; x += 28) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();
  }
  for (let y = 24; y < h; y += 28) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }
}

function pointerPos(canvas, scope, event) {
  const rect = canvas.getBoundingClientRect();
  const sx = rect.width ? scope.width / rect.width : 1;
  const sy = rect.height ? scope.height / rect.height : 1;
  return {
    x: (event.clientX - rect.left) * sx,
    y: (event.clientY - rect.top) * sy,
  };
}

/* ── 통합 월드 상태 ────────────────────────────────────────────── */

const MAGNET_TESLA = { 1: 0.08, 2: 0.18, 3: 0.35 };
const MAGNET_LABEL = { 1: "약함", 2: "보통", 3: "강력" };

const game = {
  weather: "night",
  activeStation: "generator",
  activeCam: "overview",
  drawerOpen: true,
  surgeWatts: 0,
  time: 0,

  circuit: {
    material: "copper",
    voltage: 1.5,
    closed: true,
    phase: 0,
    output: null,
  },
  staticState: {
    charge: 0,
    balloon: { x: 165, y: 52 },
    worldX: 0.6,
    worldY: 3.8,
    worldZ: 0.6,
    rubbing: 0,
    rubHold: false,
    dragging: false,
    lastPointer: null,
    pointerSpeed: 0,
    bits: [],
  },
  fruit: {
    kind: "lemon",
    cells: 1,
    output: null,
  },
  generator: {
    turns: 240,
    magnet: 2,
    angle: 0,
    rpm: 0,
    targetRpm: 0,
    manual: false,
    lastAngle: 0,
    crankHold: false,
    output: null,
  },
  solar: {
    altitude: 40,
    tilt: 15,
    cloud: 10,
    auto: false,
    output: null,
  },
  wind: {
    windSpeed: 5,
    bladeLength: 0.3,
    blades: 3,
    rpm: 0,
    gustBoost: 0,
    output: null,
  },
  hydro: {
    head: 1.1,
    flow: 2,
    rpm: 0,
    output: null,
  },
  grid: null,
  litMask: {},
};

// 12개의 종이 별 조각 시드 초기화 (2D 패드 + 3D 부두 공유)
for (let i = 0; i < 12; i += 1) {
  game.staticState.bits.push({
    x: 150 + ((i * 29) % 165),
    y: 82 + (i % 3) * 9,
    stuck: false,
    pull: 0,
    holdAngle: (i / 12) * TAU,
  });
}

/* ── 발견 도감 & 마일스톤 관리 ────────────────────────────────── */

function buildDots() {
  const dots = $("#found-dots");
  if (!dots) return;
  dots.innerHTML = "";
  STATION_IDS.forEach((id) => {
    const dot = doc.createElement("span");
    dot.className = "found-dot";
    dot.setAttribute("data-dot", id);
    dots.appendChild(dot);
  });
}

function renderFound() {
  let count = 0;
  STATION_IDS.forEach((id) => {
    if (progress.found[id]) count += 1;
  });
  setText($("#stat-found"), String(count));
  const dots = $("#found-dots");
  if (dots && dots.children.length === STATION_TOTAL) {
    STATION_IDS.forEach((id, index) => {
      dots.children[index].classList.toggle("is-on", Boolean(progress.found[id]));
    });
  }
}

function markFound(id, toastLabel) {
  if (progress.found[id]) return;
  progress.found[id] = true;
  saveProgress();
  renderFound();
  const stamp = doc.getElementById("stamp-" + id);
  if (stamp) stamp.hidden = false;
  const card = doc.getElementById("station-" + id);
  if (card) card.classList.add("is-found");
  const goal = doc.getElementById("goal-" + id);
  if (goal) goal.classList.add("is-done");
  sound.chime();
  if (toastLabel) showToast("🏅 발견 완료! " + toastLabel);
}

/* ── 스테이션 전환 & 3D 카메라 연동 ───────────────────────────── */

let world = null;

const ZONE_META = {
  generator: { icon: "🔄", title: "크랭크 발전기" },
  wind: { icon: "🌬️", title: "바람 절벽" },
  solar: { icon: "☀️", title: "태양광 언덕" },
  hydro: { icon: "💧", title: "폭포 수력댐" },
  circuit: { icon: "🔌", title: "중앙 변전소" },
  static: { icon: "🎈", title: "정전기 부두" },
  fruit: { icon: "🍋", title: "과일 전지" },
  village: { icon: "🎡", title: "네온 밤마을" },
};

const scopes = {};

function setDrawerOpen(open) {
  game.drawerOpen = Boolean(open);
  const drawer = $("#station-drawer");
  const toggleBtn = $("#drawer-toggle-btn");
  if (drawer) drawer.setAttribute("data-open", game.drawerOpen ? "true" : "false");
  if (toggleBtn) toggleBtn.setAttribute("aria-expanded", game.drawerOpen ? "true" : "false");
  if (game.drawerOpen && scopes[game.activeStation]) {
    scopes[game.activeStation].resize();
  }
}

function selectZone(zoneId, options = {}) {
  game.activeCam = zoneId;
  $$(".lab-jump a").forEach((link) => {
    link.classList.toggle("is-current", link.getAttribute("data-cam") === zoneId);
  });

  if (STATION_IDS.indexOf(zoneId) !== -1) {
    game.activeStation = zoneId;
    $$(".station").forEach((card) => {
      card.classList.toggle("is-active", card.getAttribute("data-station") === zoneId);
    });
    const meta = ZONE_META[zoneId];
    if (meta) {
      setText($("#drawer-zone-label"), meta.icon + " " + meta.title + " 계기판");
    }
    if (!options.keepDrawerState) {
      setDrawerOpen(true);
    }
    if (scopes[zoneId]) scopes[zoneId].resize();
  }

  if (world && !options.skipCamera) {
    world.focusZone(zoneId);
  }
}

/* ── 물리 연산 통합 갱신 ──────────────────────────────────────── */

function computeAllPhysics() {
  game.circuit.output = P.circuitState({
    material: game.circuit.material,
    voltage: game.circuit.voltage,
    closed: game.circuit.closed,
  });

  game.fruit.output = P.fruitBattery({
    fruit: game.fruit.kind,
    cells: game.fruit.cells,
  });

  game.generator.output = P.generatorOutput({
    turns: game.generator.turns,
    fieldTesla: MAGNET_TESLA[game.generator.magnet],
    rpm: game.generator.rpm,
  });

  game.solar.output = P.solarOutput({
    sunAltitudeDeg: game.solar.altitude,
    panelTiltDeg: game.solar.tilt,
    cloudiness: game.solar.cloud / 100,
  });

  const effectiveWind = Math.min(25, game.wind.windSpeed + game.wind.gustBoost);
  game.wind.output = P.windPower({
    windSpeed: effectiveWind,
    bladeLength: game.wind.bladeLength,
    bladeCount: game.wind.blades,
  });
  game.wind.rpm = P.turbineRpm({
    windSpeed: effectiveWind,
    bladeLength: game.wind.bladeLength,
    bladeCount: game.wind.blades,
  });

  game.hydro.output = P.hydroPower({
    headMeters: game.hydro.head,
    flowLitersPerSec: game.hydro.flow,
  });
  game.hydro.rpm = P.wheelRpm({
    headMeters: game.hydro.head,
    flowLitersPerSec: game.hydro.flow,
  });

  game.grid = P.islandGridState({
    generatorWatts: game.generator.output.gridWatts,
    solarWatts: game.solar.output.watts,
    windWatts: game.wind.output.watts,
    hydroWatts: game.hydro.output.watts,
    fruitWatts: game.fruit.output.watts,
    surgeWatts: game.surgeWatts,
    circuit: game.circuit.output,
  });
  updateHudDashboard();
}

/* ── 일곱 개 스테이션 계기판 렌더링 & 판정 ─────────────────────── */

function updateStationUI(dt) {
  // 01 중앙 변전소
  const cOut = game.circuit.output;
  if (cOut.current > 0) {
    game.circuit.phase = (game.circuit.phase + P.electronSpeed(cOut.current) * dt) % 240;
  }
  setWidth($("#meter-circuit"), cOut.brightness);
  if (!cOut.closed) {
    setText($("#read-circuit"), "주 스위치가 열려 온 마을이 정전됐어요! 스위치를 닫아 보세요.");
  } else if (!cOut.conductive) {
    setText($("#read-circuit"), cOut.label + " 때문에 전기가 막혔어요! 도체로 바꿔 보세요.");
  } else {
    setText(
      $("#read-circuit"),
      "전류 " +
        cOut.current.toFixed(2) +
        "A · 전달 효율 " +
        Math.round(cOut.transmission * 100) +
        "% · 마을 공급 " +
        game.grid.deliveredWatts.toFixed(1) +
        "W"
    );
  }
  if (cOut.brightness > 0.99) {
    markFound("circuit", "닫힌 회로와 도체의 원리");
  }

  // 02 정전기 부두 물리
  const st = game.staticState;
  const scopeStatic = scopes.static;
  const sw = scopeStatic ? scopeStatic.width : 320;
  const sh = scopeStatic ? scopeStatic.height : 112;
  const hatX = sw * 0.19;
  const hatY = sh * 0.52;
  const hatR = 34;

  const nearHat = Math.hypot(st.balloon.x - hatX, st.balloon.y - hatY) < hatR * 1.9;
  let rubbing = 0;
  if (st.rubHold) {
    st.balloon.x += (hatX + 18 - st.balloon.x) * Math.min(1, dt * 9);
    st.balloon.y += (hatY - st.balloon.y) * Math.min(1, dt * 9);
    rubbing = 0.92;
  } else if (nearHat) {
    rubbing = st.pointerSpeed;
  }
  st.rubbing = rubbing;

  if (rubbing > 0.02) {
    st.charge = P.staticRub(st.charge, rubbing, dt);
    sound.rubSqueak(rubbing);
  } else {
    st.charge = P.staticDecay(st.charge, dt);
  }
  st.pointerSpeed *= Math.max(0, 1 - dt * 5.5);

  // 2D 패드 좌표 → 3D 부두 월드 오프셋 동기화
  st.worldX = ((st.balloon.x / Math.max(1, sw)) - 0.45) * 7.2;
  st.worldY = P.clamp(4.6 - (st.balloon.y / Math.max(1, sh)) * 2.2, 2.2, 5.4);
  st.worldZ = ((st.balloon.y / Math.max(1, sh)) - 0.5) * 4.5;

  let stuckCount = 0;
  for (let i = 0; i < st.bits.length; i += 1) {
    const bit = st.bits[i];
    if (bit.stuck) {
      if (st.charge < P.STATIC_LIMITS.dropCharge) {
        bit.stuck = false;
      } else {
        stuckCount += 1;
        continue;
      }
    }
    const dist = Math.hypot(st.balloon.x - bit.x, st.balloon.y - bit.y);
    bit.pull = P.staticPull(st.charge, dist);
    if (P.staticGrab(st.charge, dist)) {
      bit.stuck = true;
      sound.staticSnap();
      stuckCount += 1;
    } else if (bit.pull > 0.03) {
      bit.x += ((st.balloon.x - bit.x) / Math.max(1, dist)) * bit.pull * 130 * dt;
      bit.y += ((st.balloon.y - bit.y) / Math.max(1, dist)) * bit.pull * 130 * dt;
    } else if (bit.y < sh - 16) {
      bit.y = Math.min(sh - 14, bit.y + 120 * dt);
    }
  }

  setWidth($("#meter-static"), st.charge / P.STATIC_LIMITS.maxCharge);
  if (stuckCount >= 5) {
    setText($("#read-static"), "와! 별 종이 " + stuckCount + "개가 3D 풍선 주위를 맴돌아요!");
    markFound("static", "마찰 정전기 인력");
  } else if (st.charge >= P.STATIC_LIMITS.liftCharge) {
    setText($("#read-static"), "전하 충전 완료! 풍선을 오른쪽 별 조각 위로 옮겨 보세요 (" + stuckCount + "/5)");
  } else {
    setText($("#read-static"), "풍선을 왼쪽 양모 구름 패드에 문질러 전하를 모아요 (" + Math.round(st.charge) + "%)");
  }

  // 03 과일 전지
  const fOut = game.fruit.output;
  setWidth($("#meter-fruit"), fOut.level);
  if (!fOut.lit) {
    setText(
      $("#read-fruit"),
      fOut.label + " " + fOut.cells + "개 = " + fOut.volts.toFixed(2) + "V · 1.8V가 넘어야 비컨이 켜져요!"
    );
  } else if (fOut.full) {
    setText(
      $("#read-fruit"),
      fOut.label + " " + fOut.cells + "개 직렬 = " + fOut.volts.toFixed(2) + "V · 루비 비컨 최대 발광!"
    );
    markFound("fruit", "화학 전지 직렬 연결");
  } else {
    setText(
      $("#read-fruit"),
      fOut.label + " " + fOut.cells + "개 = " + fOut.volts.toFixed(2) + "V · 비컨이 켜지기 시작했어요!"
    );
  }

  // 04 손잡이 발전기 회전 물리
  const gen = game.generator;
  const prevStep = Math.floor(gen.angle / 0.55);
  if (gen.crankHold) {
    gen.rpm += (185 - gen.rpm) * Math.min(1, dt * 5.2);
  } else if (!gen.manual) {
    if (gen.targetRpm > 0) {
      gen.rpm += (gen.targetRpm - gen.rpm) * Math.min(1, dt * 3.4);
    } else {
      gen.rpm *= Math.max(0, 1 - dt * 1.45);
      if (gen.rpm < 0.4) gen.rpm = 0;
    }
  } else {
    gen.rpm *= Math.max(0, 1 - dt * 0.7);
  }
  gen.angle += (gen.rpm * TAU * dt) / 60;
  if (gen.rpm > 8 && Math.floor(gen.angle / 0.55) !== prevStep) {
    sound.crankTick(gen.rpm);
  }

  const gOut = P.generatorOutput({
    turns: gen.turns,
    fieldTesla: MAGNET_TESLA[gen.magnet],
    rpm: gen.rpm,
  });
  gen.output = gOut;
  setWidth($("#meter-generator"), gOut.level);
  if (gen.rpm < 1) {
    setText($("#read-generator"), "정지 중 · 크랭크 바퀴를 직접 돌리거나 고속 버튼을 눌러 보세요!");
  } else if (gOut.level >= 1) {
    setText(
      $("#read-generator"),
      "유도 전력 " + gOut.watts.toFixed(2) + "W (" + Math.round(gen.rpm) + "rpm) · 최고 출력 달성!"
    );
    markFound("generator", "패러데이 전자기 유도");
  } else {
    setText(
      $("#read-generator"),
      "발전 " + gOut.watts.toFixed(2) + "W · " + Math.round(gen.rpm) + "rpm · 더 빠르게 돌려 보세요!"
    );
  }

  // 05 태양광 발전
  if (game.solar.auto) {
    const optimal = Math.round(P.clamp(90 - game.solar.altitude, 0, 90));
    if (optimal !== game.solar.tilt) {
      game.solar.tilt = optimal;
      const tiltInput = $("#tilt-range");
      if (tiltInput) tiltInput.value = String(optimal);
      setText($("#tilt-output"), optimal + "°");
    }
  }
  const sOut = game.solar.output;
  setWidth($("#meter-solar"), sOut.level);
  if (sOut.level >= 0.999) {
    setText($("#read-solar"), "수직 입사 성공! " + sOut.watts.toFixed(2) + "W 최대 태양광 발전 중!");
    markFound("solar", "태양광 최적 입사각");
  } else {
    setText(
      $("#read-solar"),
      "발전 " + sOut.watts.toFixed(2) + "W · 최적 기울기 " + sOut.optimalTilt.toFixed(0) + "°에 맞춰 보세요!"
    );
  }

  // 06 바람 발전
  game.wind.gustBoost = Math.max(0, game.wind.gustBoost - dt * 1.9);
  const wOut = game.wind.output;
  setWidth($("#meter-wind"), wOut.level);
  if (wOut.level >= 1) {
    setText($("#read-wind"), "해안 강풍 " + wOut.watts.toFixed(1) + "W! 세 기의 터빈이 풀가동 중이에요!");
    markFound("wind", "풍속 세제곱 발전 법칙");
  } else {
    setText(
      $("#read-wind"),
      "발전 " + wOut.watts.toFixed(2) + "W · 로터 " + Math.round(game.wind.rpm) + "rpm 회전 중"
    );
  }

  // 07 수력 발전
  const hOut = game.hydro.output;
  setWidth($("#meter-hydro"), hOut.level);
  if (hOut.level >= 1) {
    setText($("#read-hydro"), "만수위 폭포 " + hOut.watts.toFixed(1) + "W! 대형 수차가 힘차게 돌아요!");
    markFound("hydro", "수력 낙차와 위치 에너지");
  } else {
    setText(
      $("#read-hydro"),
      "발전 " + hOut.watts.toFixed(2) + "W · 수차 " + Math.round(game.hydro.rpm) + "rpm 회전 중"
    );
  }
}

/* ── 미니 계기판 오실로스코프 그리기 ──────────────────────────── */

function drawActiveMiniScope() {
  const id = game.activeStation;
  const scope = scopes[id];
  if (!scope || !game.drawerOpen) return;
  const { ctx, width: w, height: h } = scope;
  scopeBackdrop(ctx, w, h);

  if (id === "circuit") {
    const out = game.circuit.output;
    ctx.strokeStyle = out.lit ? "#d7ff00" : "rgba(148, 189, 255, 0.35)";
    ctx.lineWidth = 3;
    ctx.strokeRect(26, 20, w - 52, h - 40);
    if (out.current > 0) {
      ctx.fillStyle = "#d7ff00";
      for (let i = 0; i < 8; i += 1) {
        const x = 26 + ((game.circuit.phase + i * 32) % (w - 52));
        ctx.beginPath();
        ctx.arc(x, 20, 4, 0, TAU);
        ctx.fill();
      }
    }
    ctx.fillStyle = out.color;
    ctx.fillRect(w * 0.5 - 22, h - 25, 44, 10);
  } else if (id === "static") {
    const st = game.staticState;
    ctx.fillStyle = "#4f63b8";
    ctx.beginPath();
    ctx.arc(w * 0.19, h * 0.52, 26, 0, TAU);
    ctx.fill();

    st.bits.forEach((bit) => {
      ctx.fillStyle = bit.stuck ? "#ffe066" : "#a9def9";
      ctx.fillRect(bit.x - 4, bit.y - 4, 8, 8);
    });

    ctx.fillStyle = "#ff5c8a";
    ctx.beginPath();
    ctx.ellipse(st.balloon.x, st.balloon.y, 15, 19, 0, 0, TAU);
    ctx.fill();
  } else if (id === "generator") {
    const emf = game.generator.output.emf;
    ctx.strokeStyle = "#ffbe3b";
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    for (let x = 0; x < w; x += 4) {
      const amp = Math.min(h * 0.4, emf * 6.5);
      const y = h * 0.5 + Math.sin(x * 0.06 + game.generator.angle * 2) * amp;
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    const cx = w - 42;
    const cy = h * 0.5;
    ctx.strokeStyle = "rgba(215, 255, 0, 0.7)";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(cx, cy, 24, 0, TAU);
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(game.generator.angle) * 24, cy + Math.sin(game.generator.angle) * 24);
    ctx.stroke();
  } else {
    const levelMap = {
      fruit: game.fruit.output.level,
      solar: game.solar.output.level,
      wind: game.wind.output.level,
      hydro: game.hydro.output.level,
    };
    const lv = levelMap[id] || 0;
    ctx.strokeStyle = "#5cf2c2";
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    for (let x = 0; x < w; x += 5) {
      const y = h * 0.72 - lv * h * 0.46 - Math.sin(x * 0.05 + game.time * 6) * (2 + lv * 10);
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
}

/* ── 3D 월드 플로팅 라벨 & 상단 대시보드 ──────────────────────── */

const worldLabelElements = {};

function initWorldLabels() {
  const layer = $("#world-labels");
  if (!layer) return;
  Object.keys(ZONE_META).forEach((zoneId) => {
    const btn = doc.createElement("button");
    btn.type = "button";
    btn.className = "world-tag";
    btn.setAttribute("data-world-tag", zoneId);
    const meta = ZONE_META[zoneId];
    btn.innerHTML = `<span>${meta.icon} ${meta.title}</span><em data-tag-val="${zoneId}"></em>`;
    btn.addEventListener("click", () => {
      sound.tick();
      selectZone(zoneId);
    });
    layer.appendChild(btn);
    worldLabelElements[zoneId] = {
      el: btn,
      val: btn.querySelector("[data-tag-val]"),
    };
  });
}

function updateWorldLabels() {
  if (!world) return;
  const stageEl = $("#world-stage");
  const w = stageEl ? stageEl.clientWidth || 1280 : 1280;
  const h = stageEl ? stageEl.clientHeight || 800 : 800;
  const projected = world.projectAnchors(w, h);

  const summaries = {
    generator: game.generator.output.watts.toFixed(1) + "W",
    wind: game.wind.output.watts.toFixed(1) + "W",
    solar: game.solar.output.watts.toFixed(1) + "W",
    hydro: game.hydro.output.watts.toFixed(1) + "W",
    circuit: game.circuit.output.transmission > 0 ? "개통" : "차단",
    static: Math.round(game.staticState.charge) + "%",
    fruit: game.fruit.output.volts.toFixed(1) + "V",
    village: game.grid.litCount + "/6 점등",
  };

  Object.keys(worldLabelElements).forEach((key) => {
    const item = worldLabelElements[key];
    const p = projected[key];
    if (!p || !p.visible) {
      item.el.style.opacity = "0";
      return;
    }
    item.el.style.opacity = "1";
    item.el.style.left = Math.round(p.x) + "px";
    item.el.style.top = Math.round(p.y) + "px";
    item.el.classList.toggle("is-focused", game.activeCam === key);
    if (item.val) setText(item.val, summaries[key] || "");
  });
}

const tierIcons = {};
function updateHudDashboard() {
  setText($("#stat-watts"), game.grid.deliveredWatts.toFixed(1));
  const joules = Math.round(progress.energy);
  setText($("#stat-energy"), String(joules));
  setText($("#outro-energy"), String(joules));

  P.VILLAGE_LANDMARKS.forEach((spec, idx) => {
    const on = game.grid.landmarks[spec.id] > 0;
    if (on && !game.litMask[spec.id] && game.time > 0.35) {
      sound.landmarkLit(idx);
      showToast("✨ " + spec.label + " 점등!");
    }
    game.litMask[spec.id] = on;
    const icon = tierIcons[spec.id];
    if (icon) icon.classList.toggle("is-lit", on);
  });
}

/* ── 사용자 입력 바인딩 ───────────────────────────────────────── */

function bindControls() {
  // 구역 리본 클릭
  $$(".lab-jump a").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      sound.tick();
      selectZone(link.getAttribute("data-cam") || "overview");
    });
  });

  // 날씨·시간대 전환
  $$("[data-weather]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const mode = btn.getAttribute("data-weather");
      const preset = P.WEATHER_PRESETS[mode];
      if (!preset) return;
      game.weather = mode;
      $$("[data-weather]").forEach((other) => {
        other.setAttribute("aria-pressed", other === btn ? "true" : "false");
      });
      game.solar.altitude = preset.sunAltitude;
      game.solar.cloud = preset.cloud;
      game.wind.windSpeed = preset.wind;

      const sunInput = $("#sun-range");
      if (sunInput) sunInput.value = String(preset.sunAltitude);
      setText($("#sun-output"), preset.sunAltitude + "°");

      const cloudInput = $("#cloud-range");
      if (cloudInput) cloudInput.value = String(preset.cloud);
      setText($("#cloud-output"), preset.cloud + "%");

      const windInput = $("#wind-range");
      if (windInput) windInput.value = String(preset.wind);
      setText($("#wind-output"), preset.wind.toFixed(1) + " m/s");

      if (mode === "storm") {
        sound.thunderBolt();
        if (world) world.triggerTeslaSpectacle();
        triggerScreenFlash();
        showToast("⛈️ 번개 폭풍이 몰아쳐 풍력과 테슬라 탑이 요동쳐요!");
      } else {
        sound.pop();
        showToast("🌤️ 하늘이 '" + preset.label + "' 모드로 바뀌었어요!");
      }
      computeAllPhysics();
    });
  });

  // 하단 스펙터클 아케이드 버튼들
  const quickCrank = $("#quick-crank-btn");
  if (quickCrank) {
    const startHold = () => {
      game.generator.crankHold = true;
      game.generator.rpm = Math.max(game.generator.rpm, 145);
      sound.crankTick(160);
    };
    const stopHold = () => {
      game.generator.crankHold = false;
    };
    quickCrank.addEventListener("pointerdown", startHold);
    quickCrank.addEventListener("pointerup", stopHold);
    quickCrank.addEventListener("pointerleave", stopHold);
    quickCrank.addEventListener("pointercancel", stopHold);
    quickCrank.addEventListener("click", () => {
      game.generator.rpm = Math.min(260, game.generator.rpm + 95);
      sound.crankTick(game.generator.rpm);
    });
  }

  const teslaBtn = $("#tesla-fire-btn");
  if (teslaBtn) {
    teslaBtn.addEventListener("click", () => {
      game.surgeWatts = 24;
      sound.thunderBolt();
      sound.fireworkBurst();
      triggerScreenFlash();
      if (world) world.triggerTeslaSpectacle();
      showToast("🌩️ 테슬라 슈퍼 번개 발사! 온 섬에 초고압 전류가 흘러요!");
    });
  }

  const fullPowerBtn = $("#full-power-btn");
  if (fullPowerBtn) {
    fullPowerBtn.addEventListener("click", () => {
      // 주 회로 개통
      game.circuit.material = "copper";
      game.circuit.closed = true;
      game.circuit.voltage = 4.5;
      $$("[data-material]").forEach((b) => {
        b.setAttribute("aria-pressed", b.getAttribute("data-material") === "copper" ? "true" : "false");
      });
      const sw = $("#switch-circuit");
      if (sw) {
        sw.setAttribute("aria-pressed", "true");
        $(".switch-text", sw).textContent = "주 스위치 닫힘";
      }
      if ($("#voltage-range")) $("#voltage-range").value = "4.5";
      setText($("#voltage-output"), "4.5 V");

      // 모든 발전기 최대 출력 가동
      game.generator.targetRpm = 175;
      game.generator.turns = 480;
      game.generator.magnet = 3;
      if ($("#turns-range")) $("#turns-range").value = "480";
      setText($("#turns-output"), "480번");
      if ($("#magnet-range")) $("#magnet-range").value = "3";
      setText($("#magnet-output"), "강력");

      game.solar.altitude = 62;
      game.solar.tilt = 28;
      game.solar.cloud = 0;
      game.solar.auto = true;
      if ($("#sun-range")) $("#sun-range").value = "62";
      setText($("#sun-output"), "62°");
      if ($("#tilt-range")) $("#tilt-range").value = "28";
      setText($("#tilt-output"), "28°");
      if ($("#cloud-range")) $("#cloud-range").value = "0";
      setText($("#cloud-output"), "0%");
      if ($("#tilt-auto")) $("#tilt-auto").setAttribute("aria-pressed", "true");

      game.wind.windSpeed = 9.5;
      game.wind.bladeLength = 0.45;
      game.wind.blades = 3;
      if ($("#wind-range")) $("#wind-range").value = "9.5";
      setText($("#wind-output"), "9.5 m/s");
      if ($("#blade-range")) $("#blade-range").value = "0.45";
      setText($("#blade-output"), "45 cm");

      game.hydro.head = 2.4;
      game.hydro.flow = 4.5;
      if ($("#head-range")) $("#head-range").value = "2.4";
      setText($("#head-output"), "240 cm");
      if ($("#flow-range")) $("#flow-range").value = "4.5";
      setText($("#flow-output"), "4.5 L/s");

      game.fruit.cells = 5;
      setText($("#cells-count"), "5개");

      game.surgeWatts = 16;
      selectZone("overview", { keepDrawerState: true });
      sound.switchThrow(true);
      sound.fireworkBurst();
      triggerScreenFlash();
      if (world) world.triggerTeslaSpectacle();
      computeAllPhysics();
      showToast("🚀 풀파워 점등 쇼! 모든 발전소와 6개 밤마을 랜드마크가 깨어납니다!");
    });
  }

  const blackoutBtn = $("#blackout-btn");
  if (blackoutBtn) {
    blackoutBtn.addEventListener("click", () => {
      game.circuit.closed = false;
      const sw = $("#switch-circuit");
      if (sw) {
        sw.setAttribute("aria-pressed", "false");
        $(".switch-text", sw).textContent = "주 스위치 열림";
      }
      sound.switchThrow(false);
      selectZone("circuit", { keepDrawerState: true });
      computeAllPhysics();
      showToast("🌑 주 스위치를 열어 송전을 차단했어요! 마을 불빛이 모두 꺼집니다.");
    });
  }

  const drawerToggleBtn = $("#drawer-toggle-btn");
  if (drawerToggleBtn) {
    drawerToggleBtn.addEventListener("click", () => {
      sound.tick();
      setDrawerOpen(!game.drawerOpen);
    });
  }
  const drawerCloseBtn = $("#drawer-close-btn");
  if (drawerCloseBtn) {
    drawerCloseBtn.addEventListener("click", () => {
      sound.tick();
      setDrawerOpen(false);
    });
  }
  const camResetBtn = $("#cam-reset-btn");
  if (camResetBtn) {
    camResetBtn.addEventListener("click", () => {
      sound.tick();
      selectZone("overview", { keepDrawerState: true });
    });
  }

  // 01 회로 컨트롤
  $$("[data-material]").forEach((button) => {
    button.addEventListener("click", () => {
      game.circuit.material = button.getAttribute("data-material");
      $$("[data-material]").forEach((other) => {
        other.setAttribute("aria-pressed", other === button ? "true" : "false");
      });
      sound.tick();
      computeAllPhysics();
    });
  });

  const switchCircuit = $("#switch-circuit");
  if (switchCircuit) {
    switchCircuit.addEventListener("click", () => {
      game.circuit.closed = !game.circuit.closed;
      switchCircuit.setAttribute("aria-pressed", game.circuit.closed ? "true" : "false");
      $(".switch-text", switchCircuit).textContent = game.circuit.closed
        ? "주 스위치 닫힘"
        : "주 스위치 열림";
      sound.switchThrow(game.circuit.closed);
      computeAllPhysics();
    });
  }

  const voltageRange = $("#voltage-range");
  if (voltageRange) {
    voltageRange.addEventListener("input", () => {
      game.circuit.voltage = Number(voltageRange.value);
      setText($("#voltage-output"), game.circuit.voltage.toFixed(1) + " V");
      computeAllPhysics();
    });
  }

  const resetCircuit = $("#reset-circuit");
  if (resetCircuit) {
    resetCircuit.addEventListener("click", () => {
      game.circuit.material = "copper";
      game.circuit.voltage = 1.5;
      game.circuit.closed = true;
      $$("[data-material]").forEach((other) => {
        other.setAttribute(
          "aria-pressed",
          other.getAttribute("data-material") === "copper" ? "true" : "false"
        );
      });
      if (switchCircuit) {
        switchCircuit.setAttribute("aria-pressed", "true");
        $(".switch-text", switchCircuit).textContent = "주 스위치 닫힘";
      }
      if (voltageRange) voltageRange.value = "1.5";
      setText($("#voltage-output"), "1.5 V");
      sound.tick();
      computeAllPhysics();
    });
  }

  // 02 정전기 패드 & 버튼
  const staticCanvas = $("#canvas-static");
  if (staticCanvas) {
    const moveBalloon = (event) => {
      const scope = scopes.static;
      if (!scope) return;
      const pos = pointerPos(staticCanvas, scope, event);
      if (game.staticState.lastPointer) {
        const move = Math.hypot(
          pos.x - game.staticState.lastPointer.x,
          pos.y - game.staticState.lastPointer.y
        );
        game.staticState.pointerSpeed = P.clamp(move / 8, 0, 1);
      }
      game.staticState.lastPointer = pos;
      game.staticState.balloon.x = P.clamp(pos.x, 16, scope.width - 16);
      game.staticState.balloon.y = P.clamp(pos.y, 16, scope.height - 16);
    };

    staticCanvas.addEventListener("pointerdown", (event) => {
      staticCanvas.setPointerCapture(event.pointerId);
      game.staticState.dragging = true;
      moveBalloon(event);
      sound.unlock();
    });
    staticCanvas.addEventListener("pointermove", (event) => {
      if (game.staticState.dragging) moveBalloon(event);
    });
    const endStatic = () => {
      game.staticState.dragging = false;
      game.staticState.lastPointer = null;
    };
    staticCanvas.addEventListener("pointerup", endStatic);
    staticCanvas.addEventListener("pointercancel", endStatic);

    staticCanvas.addEventListener("keydown", (event) => {
      const step = event.shiftKey ? 24 : 12;
      if (event.key === "ArrowLeft") game.staticState.balloon.x -= step;
      else if (event.key === "ArrowRight") game.staticState.balloon.x += step;
      else if (event.key === "ArrowUp") game.staticState.balloon.y -= step;
      else if (event.key === "ArrowDown") game.staticState.balloon.y += step;
      else if (event.key === " " || event.key === "Enter") {
        game.staticState.rubHold = !game.staticState.rubHold;
      } else {
        return;
      }
      event.preventDefault();
    });
  }

  const rubBtn = $("#rub-button");
  if (rubBtn) {
    const on = () => {
      game.staticState.rubHold = true;
      sound.unlock();
    };
    const off = () => {
      game.staticState.rubHold = false;
    };
    rubBtn.addEventListener("pointerdown", on);
    rubBtn.addEventListener("pointerup", off);
    rubBtn.addEventListener("pointerleave", off);
    rubBtn.addEventListener("pointercancel", off);
    rubBtn.addEventListener("click", () => {
      game.staticState.charge = Math.min(100, game.staticState.charge + 35);
      sound.rubSqueak(0.8);
    });
  }

  const dischargeBtn = $("#discharge-button");
  if (dischargeBtn) {
    dischargeBtn.addEventListener("click", () => {
      game.staticState.charge = 0;
      game.staticState.bits.forEach((b) => {
        b.stuck = false;
      });
      sound.discharge();
    });
  }

  // 03 과일 전지 컨트롤
  $$("[data-fruit]").forEach((btn) => {
    btn.addEventListener("click", () => {
      game.fruit.kind = btn.getAttribute("data-fruit");
      $$("[data-fruit]").forEach((other) => {
        other.setAttribute("aria-pressed", other === btn ? "true" : "false");
      });
      sound.tick();
      computeAllPhysics();
    });
  });

  const setFruitCells = (next) => {
    game.fruit.cells = Math.round(P.clamp(next, 1, 8));
    setText($("#cells-count"), game.fruit.cells + "개");
    sound.tick();
    computeAllPhysics();
  };
  if ($("#cells-minus")) {
    $("#cells-minus").addEventListener("click", () => setFruitCells(game.fruit.cells - 1));
  }
  if ($("#cells-plus")) {
    $("#cells-plus").addEventListener("click", () => setFruitCells(game.fruit.cells + 1));
  }

  // 04 크랭크 발전기 패드 & 컨트롤
  const genCanvas = $("#canvas-generator");
  if (genCanvas) {
    const angleFromEvent = (event) => {
      const scope = scopes.generator;
      const pos = pointerPos(genCanvas, scope, event);
      return Math.atan2(pos.y - scope.height * 0.5, pos.x - (scope.width - 42));
    };
    genCanvas.addEventListener("pointerdown", (event) => {
      genCanvas.setPointerCapture(event.pointerId);
      game.generator.manual = true;
      game.generator.lastAngle = angleFromEvent(event);
      sound.unlock();
    });
    genCanvas.addEventListener("pointermove", (event) => {
      if (!game.generator.manual) return;
      const next = angleFromEvent(event);
      let delta = next - game.generator.lastAngle;
      while (delta > Math.PI) delta -= TAU;
      while (delta < -Math.PI) delta += TAU;
      game.generator.lastAngle = next;
      const instant = (P.clamp(Math.abs(delta), 0, 1.3) * 60) / TAU / 0.016;
      game.generator.rpm = P.clamp(game.generator.rpm * 0.6 + instant * 0.4, 0, 900);
      game.generator.angle = next;
    });
    const endGen = () => {
      game.generator.manual = false;
    };
    genCanvas.addEventListener("pointerup", endGen);
    genCanvas.addEventListener("pointercancel", endGen);

    genCanvas.addEventListener("keydown", (event) => {
      if (event.key === "ArrowRight" || event.key === "ArrowUp") {
        game.generator.angle += 0.36;
        game.generator.rpm = P.clamp(game.generator.rpm + 35, 0, 900);
      } else if (event.key === "ArrowLeft" || event.key === "ArrowDown") {
        game.generator.angle -= 0.36;
        game.generator.rpm = P.clamp(game.generator.rpm + 35, 0, 900);
      } else if (event.key === " ") {
        setSpinTarget(game.generator.targetRpm > 0 ? 0 : 140);
      } else {
        return;
      }
      event.preventDefault();
    });
  }

  function setSpinTarget(rpm) {
    game.generator.targetRpm = rpm;
    $$("[data-spin]").forEach((btn) => {
      btn.setAttribute("aria-pressed", Number(btn.getAttribute("data-spin")) === rpm ? "true" : "false");
    });
    sound.tick();
  }
  $$("[data-spin]").forEach((btn) => {
    btn.addEventListener("click", () => setSpinTarget(Number(btn.getAttribute("data-spin"))));
  });

  if ($("#turns-range")) {
    $("#turns-range").addEventListener("input", (e) => {
      game.generator.turns = Number(e.target.value);
      setText($("#turns-output"), game.generator.turns + "번");
      computeAllPhysics();
    });
  }
  if ($("#magnet-range")) {
    $("#magnet-range").addEventListener("input", (e) => {
      game.generator.magnet = Number(e.target.value);
      setText($("#magnet-output"), MAGNET_LABEL[game.generator.magnet]);
      computeAllPhysics();
    });
  }

  // 05 태양광 컨트롤
  if ($("#sun-range")) {
    $("#sun-range").addEventListener("input", (e) => {
      game.solar.altitude = Number(e.target.value);
      setText($("#sun-output"), game.solar.altitude + "°");
      computeAllPhysics();
    });
  }
  if ($("#tilt-range")) {
    $("#tilt-range").addEventListener("input", (e) => {
      game.solar.tilt = Number(e.target.value);
      setText($("#tilt-output"), game.solar.tilt + "°");
      if (game.solar.auto) {
        game.solar.auto = false;
        if ($("#tilt-auto")) $("#tilt-auto").setAttribute("aria-pressed", "false");
      }
      computeAllPhysics();
    });
  }
  if ($("#cloud-range")) {
    $("#cloud-range").addEventListener("input", (e) => {
      game.solar.cloud = Number(e.target.value);
      setText($("#cloud-output"), game.solar.cloud + "%");
      computeAllPhysics();
    });
  }
  if ($("#tilt-auto")) {
    $("#tilt-auto").addEventListener("click", (e) => {
      game.solar.auto = !game.solar.auto;
      e.currentTarget.setAttribute("aria-pressed", game.solar.auto ? "true" : "false");
      sound.tick();
    });
  }

  // 06 풍력 컨트롤
  if ($("#wind-range")) {
    $("#wind-range").addEventListener("input", (e) => {
      game.wind.windSpeed = Number(e.target.value);
      setText($("#wind-output"), game.wind.windSpeed.toFixed(1) + " m/s");
      computeAllPhysics();
    });
  }
  if ($("#blade-range")) {
    $("#blade-range").addEventListener("input", (e) => {
      game.wind.bladeLength = Number(e.target.value);
      setText($("#blade-output"), Math.round(game.wind.bladeLength * 100) + " cm");
      computeAllPhysics();
    });
  }
  $$("[data-blades]").forEach((btn) => {
    btn.addEventListener("click", () => {
      game.wind.blades = Number(btn.getAttribute("data-blades"));
      $$("[data-blades]").forEach((other) => {
        other.setAttribute("aria-pressed", other === btn ? "true" : "false");
      });
      sound.tick();
      computeAllPhysics();
    });
  });

  // 07 수력 컨트롤
  if ($("#head-range")) {
    $("#head-range").addEventListener("input", (e) => {
      game.hydro.head = Number(e.target.value);
      setText($("#head-output"), Math.round(game.hydro.head * 100) + " cm");
      computeAllPhysics();
    });
  }
  if ($("#flow-range")) {
    $("#flow-range").addEventListener("input", (e) => {
      game.hydro.flow = Number(e.target.value);
      setText($("#flow-output"), game.hydro.flow.toFixed(1) + " L/s");
      computeAllPhysics();
    });
  }

  // 원리 토글
  $$(".why-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = doc.getElementById(btn.getAttribute("aria-controls"));
      const expanded = btn.getAttribute("aria-expanded") === "true";
      btn.setAttribute("aria-expanded", expanded ? "false" : "true");
      if (target) target.hidden = expanded;
      sound.tick();
    });
  });

  // 소리 토글
  const soundBtn = $("#sound-button");
  if (soundBtn) {
    const syncSoundBtn = () => {
      soundBtn.setAttribute("aria-pressed", sound.enabled ? "true" : "false");
      soundBtn.setAttribute("aria-label", sound.enabled ? "효과음 끄기" : "효과음 켜기");
      soundBtn.textContent = sound.enabled ? "🔊 소리" : "🔇 음소거";
    };
    soundBtn.addEventListener("click", () => {
      sound.setEnabled(!sound.enabled);
      progress.sound = sound.enabled;
      saveProgress(true);
      syncSoundBtn();
      if (sound.enabled) sound.pop();
    });
    syncSoundBtn();
  }

  // 도움말 & 도감 모달
  function wireDialog(openBtnId, dialogId, backdropId, closeIds) {
    const openBtn = doc.getElementById(openBtnId);
    const dialog = doc.getElementById(dialogId);
    const backdrop = doc.getElementById(backdropId);
    let lastFocus = null;

    const open = () => {
      if (!dialog || !backdrop) return;
      lastFocus = doc.activeElement;
      dialog.hidden = false;
      backdrop.hidden = false;
      if (openBtn) openBtn.setAttribute("aria-expanded", "true");
    };
    const close = () => {
      if (!dialog || !backdrop) return;
      dialog.hidden = true;
      backdrop.hidden = true;
      if (openBtn) openBtn.setAttribute("aria-expanded", "false");
      if (lastFocus && typeof lastFocus.focus === "function") lastFocus.focus();
    };

    if (openBtn) openBtn.addEventListener("click", open);
    if (backdrop) backdrop.addEventListener("click", close);
    closeIds.forEach((cid) => {
      const el = doc.getElementById(cid);
      if (el) el.addEventListener("click", close);
    });
    doc.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && dialog && !dialog.hidden) close();
    });
  }

  wireDialog("help-button", "help-dialog", "help-backdrop", ["help-close", "help-ok"]);
  wireDialog("codex-button", "codex-dialog", "codex-backdrop", ["codex-close", "codex-ok"]);

  // 전체 초기화
  const resetAll = $("#reset-all");
  if (resetAll) {
    resetAll.addEventListener("click", () => {
      progress.found = {};
      progress.energy = 0;
      saveProgress(true);
      STATION_IDS.forEach((id) => {
        const stamp = doc.getElementById("stamp-" + id);
        if (stamp) stamp.hidden = true;
        const card = doc.getElementById("station-" + id);
        if (card) card.classList.remove("is-found");
        const goal = doc.getElementById("goal-" + id);
        if (goal) goal.classList.remove("is-done");
      });
      renderFound();
      updateHudDashboard();
      sound.discharge();
      showToast("🧹 발견 기록을 초기화했어요. 처음부터 다시 도전해 보세요!");
    });
  }

  // 전역 단축키 (숫자키 1~9 카메라 전환, 스페이스 크랭크 부스트)
  window.addEventListener("keydown", (event) => {
    const activeTag = doc.activeElement && doc.activeElement.tagName;
    if (activeTag === "INPUT" || activeTag === "BUTTON" || activeTag === "CANVAS") return;
    const presetOrder = Object.keys(CAMERA_PRESETS);
    const num = Number(event.key);
    if (num >= 1 && num <= presetOrder.length) {
      selectZone(presetOrder[num - 1]);
    } else if (event.key === " ") {
      event.preventDefault();
      game.generator.rpm = Math.min(260, game.generator.rpm + 85);
      sound.crankTick(game.generator.rpm);
    }
  });
}

/* ── 부팅 및 애니메이션 루프 ──────────────────────────────────── */

async function boot() {
  await waitForAuthGate();

  buildDots();
  STATION_IDS.forEach((id) => {
    const canvas = doc.getElementById("canvas-" + id);
    if (canvas) scopes[id] = createMiniScope(canvas);
    if (progress.found[id]) {
      const stamp = doc.getElementById("stamp-" + id);
      if (stamp) stamp.hidden = false;
      const card = doc.getElementById("station-" + id);
      if (card) card.classList.add("is-found");
      const goal = doc.getElementById("goal-" + id);
      if (goal) goal.classList.add("is-done");
    }
  });

  $$("[data-tier]").forEach((el) => {
    tierIcons[el.getAttribute("data-tier")] = el;
  });

  initWorldLabels();
  renderFound();
  computeAllPhysics();
  setLoadingProgress(2, "섬과 발전 장치를 준비하고 있어요.");
  await yieldForPaint();

  setLoadingProgress(5, "3D 그래픽 도구를 불러오고 있어요.");
  const [worldModule, textureModule] = await Promise.all([
    import("./world.js"),
    import("./textures.js"),
  ]);
  CAMERA_PRESETS = worldModule.CAMERA_PRESETS;

  setLoadingProgress(8, "섬의 지형과 재질을 만드는 중이에요.");
  let textureSet = await textureModule.createIslandTexturesAsync({
    budgetMs: 6,
    onProgress(ratio) {
      setLoadingProgress(8 + ratio * 49, "섬의 지형과 재질을 만드는 중이에요.");
    },
  });

  setLoadingProgress(60, "발전기와 밤마을을 조립하고 있어요.");
  await yieldForPaint();
  try {
    world = worldModule.createPowerWorld({
      canvas: $("#island-canvas"),
      textureSet,
      reducedMotion: prefersReducedMotion,
      onZoneSelect(zoneId) {
        selectZone(zoneId);
      },
      onCrankDrag(deltaRad, speedPx) {
        game.generator.angle += deltaRad;
        game.generator.rpm = P.clamp(game.generator.rpm * 0.65 + (Math.abs(deltaRad) * 900 + speedPx * 4), 25, 420);
        sound.crankTick(game.generator.rpm);
      },
      onBalloonDrag(dx, dy, speedPx) {
        const scope = scopes.static;
        const sw = scope ? scope.width : 320;
        const sh = scope ? scope.height : 112;
        game.staticState.balloon.x = P.clamp(game.staticState.balloon.x + dx * 26, 16, sw - 16);
        game.staticState.balloon.y = P.clamp(game.staticState.balloon.y - dy * 18, 16, sh - 16);
        game.staticState.pointerSpeed = P.clamp(speedPx / 9, 0, 1);
      },
      onSunDrag(deltaDeg) {
        game.solar.altitude = P.clamp(Math.round(game.solar.altitude + deltaDeg), 5, 90);
        if ($("#sun-range")) $("#sun-range").value = String(game.solar.altitude);
        setText($("#sun-output"), game.solar.altitude + "°");
        computeAllPhysics();
      },
      onPanelDrag(deltaDeg) {
        game.solar.tilt = P.clamp(Math.round(game.solar.tilt + deltaDeg), 0, 90);
        if ($("#tilt-range")) $("#tilt-range").value = String(game.solar.tilt);
        setText($("#tilt-output"), game.solar.tilt + "°");
        computeAllPhysics();
      },
      onWindGust() {
        game.wind.gustBoost = Math.min(8, game.wind.gustBoost + 4.5);
        sound.gust();
        showToast("🌬️ 해안 절벽에 돌풍이 불어 터빈 회전이 빨라졌어요!");
      },
      onHydroToggle() {
        game.hydro.flow = game.hydro.flow >= 4.5 ? 1.5 : 5;
        if ($("#flow-range")) $("#flow-range").value = String(game.hydro.flow);
        setText($("#flow-output"), game.hydro.flow.toFixed(1) + " L/s");
        sound.splash();
        computeAllPhysics();
      },
      onSwitchToggle() {
        const sw = $("#switch-circuit");
        if (sw) sw.click();
      },
      onFruitTap() {
        game.fruit.cells = (game.fruit.cells % 6) + 1;
        setText($("#cells-count"), game.fruit.cells + "개");
        sound.pop();
        computeAllPhysics();
      },
      onTeslaFire() {
        const btn = $("#tesla-fire-btn");
        if (btn) btn.click();
      },
    });
    textureSet = null; // World now owns and disposes the textures.
  } catch (error) {
    if (textureSet) textureSet.dispose();
    throw error;
  }

  setLoadingProgress(74, "빛과 그림자를 준비하고 있어요.");
  await yieldForPaint();
  await world.prepare();
  setLoadingProgress(94, "마지막으로 발전기를 깨우고 있어요.");

  bindControls();
  // 첫 진입 시 섬 전체가 한눈에 들어오도록 와이드 뷰 + 열린 계기판으로 시작
  if (window.innerWidth < 860) setDrawerOpen(false);
  updateHudDashboard();

  let last = 0;
  let hudAccum = 0;
  let visualAccum = 0;
  let firstFrame = true;
  function frame(now) {
    const dt = last ? Math.min((now - last) / 1000, 0.05) : 0.016;
    last = now;
    game.time += dt;
    game.surgeWatts = Math.max(0, game.surgeWatts - dt * 6.5);

    computeAllPhysics();
    updateStationUI(dt);
    if (world) world.step(dt, game);

    visualAccum += dt;
    if (visualAccum >= 1 / 30) {
      visualAccum = 0;
      drawActiveMiniScope();
      updateWorldLabels();
    }

    if (game.grid.deliveredWatts > 0) {
      progress.energy += P.energyJoules(game.grid.deliveredWatts, dt);
      saveProgress();
    }

    hudAccum += dt;
    if (hudAccum >= 0.14) {
      hudAccum = 0;
      updateHudDashboard();
    }

    if (firstFrame) {
      firstFrame = false;
      finishLoading();
    }
    window.requestAnimationFrame(frame);
  }
  window.requestAnimationFrame(frame);
}

function startBoot() {
  const ready = boot();
  window.__electricityReady = ready;
  ready.catch((error) => {
    window.__electricityBootError = error && error.message ? error.message : String(error);
    if (world) {
      world.dispose();
      world = null;
    }
    showBootError();
  });
}

if (doc.readyState === "loading") {
  doc.addEventListener("DOMContentLoaded", startBoot, { once: true });
} else {
  startBoot();
}
