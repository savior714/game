/*!
 * AIDEN POWER LAB — 전기 발전 실험실
 * 일곱 개 실험대의 캔버스 상호작용, 발전량 계산, 발견 기록 저장.
 */

(function () {
  "use strict";

  const P = window.PowerPhysics;
  if (!P) {
    console.error("PowerPhysics module is required.");
    return;
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

  /* ── 설정: 소리 · 움직임 줄이기 ───────────────────────────────── */

  const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  let prefersReducedMotion = motionQuery.matches;
  if (typeof motionQuery.addEventListener === "function") {
    motionQuery.addEventListener("change", (event) => {
      prefersReducedMotion = event.matches;
    });
  }

  const audio = {
    ctx: null,
    enabled: true,
    ensure() {
      if (!this.enabled) return null;
      if (!this.ctx) {
        const Ctor = window.AudioContext || window.webkitAudioContext;
        if (!Ctor) return null;
        try {
          this.ctx = new Ctor();
        } catch (error) {
          return null;
        }
      }
      if (this.ctx.state === "suspended" && typeof this.ctx.resume === "function") {
        this.ctx.resume();
      }
      return this.ctx;
    },
    tone(options) {
      const ctx = this.ensure();
      if (!ctx) return;
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const startGain = options.gain === undefined ? 0.09 : options.gain;
      osc.type = options.type || "sine";
      osc.frequency.setValueAtTime(options.freq, now);
      if (options.toFreq) osc.frequency.linearRampToValueAtTime(options.toFreq, now + options.dur);
      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.linearRampToValueAtTime(startGain, now + 0.015);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + options.dur);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + options.dur + 0.02);
    },
    tick() {
      this.tone({ freq: 520 + Math.random() * 220, dur: 0.07, type: "triangle", gain: 0.05 });
    },
    pop() {
      this.tone({ freq: 320, toFreq: 720, dur: 0.12, type: "square", gain: 0.05 });
    },
    chime() {
      this.tone({ freq: 660, dur: 0.16, type: "sine", gain: 0.08 });
      window.setTimeout(() => this.tone({ freq: 990, dur: 0.22, type: "sine", gain: 0.07 }), 110);
    },
  };

  /* ── 진행 저장 ────────────────────────────────────────────────── */

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
        if (typeof data.energy === "number" && isFinite(data.energy)) {
          progress.energy = Math.max(0, data.energy);
        }
        if (typeof data.sound === "boolean") progress.sound = data.sound;
      }
    } catch (error) {
      /* 저장된 기록을 읽지 못해도 실험은 계속할 수 있어야 한다 */
    }
  }

  let saveTimer = 0;
  function saveProgress(force) {
    if (!force) {
      if (saveTimer) return;
      saveTimer = window.setTimeout(() => {
        saveTimer = 0;
        saveProgress(true);
      }, 4000);
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
    } catch (error) {
      /* 저장 실패는 실험 진행을 막지 않는다 */
    }
  }

  loadProgress();
  audio.enabled = progress.sound;

  /* ── 캔버스 기본 도구 ─────────────────────────────────────────── */

  function createStage(canvas) {
    const ctx = canvas.getContext("2d");
    const stage = { canvas: canvas, ctx: ctx, width: 0, height: 0, visible: true };

    function resize() {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = Math.max(240, Math.round(rect.width || canvas.clientWidth || 480));
      const height = Math.max(160, Math.round(rect.height || canvas.clientHeight || 300));
      if (width === stage.width && height === stage.height) return;
      stage.width = width;
      stage.height = height;
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    stage.resize = resize;
    resize();
    if (window.ResizeObserver) {
      new window.ResizeObserver(resize).observe(canvas);
    } else {
      window.addEventListener("resize", resize);
    }
    return stage;
  }

  function roundRect(ctx, x, y, w, h, r) {
    const radius = Math.min(r, Math.abs(w) / 2, Math.abs(h) / 2);
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + w - radius, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + radius);
    ctx.lineTo(x + w, y + h - radius);
    ctx.quadraticCurveTo(x + w, y + h, x + w - radius, y + h);
    ctx.lineTo(x + radius, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
  }

  function glow(ctx, x, y, radius, rgb, alpha) {
    if (alpha <= 0.001 || radius <= 0) return;
    const grad = ctx.createRadialGradient(x, y, 0, x, y, radius);
    grad.addColorStop(0, "rgba(" + rgb + ", " + alpha + ")");
    grad.addColorStop(0.55, "rgba(" + rgb + ", " + alpha * 0.35 + ")");
    grad.addColorStop(1, "rgba(" + rgb + ", 0)");
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, TAU);
    ctx.fill();
  }

  function drawWire(ctx, points, width, color) {
    if (points.length < 2) return;
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    ctx.moveTo(points[0][0], points[0][1]);
    for (let i = 1; i < points.length; i += 1) ctx.lineTo(points[i][0], points[i][1]);
    ctx.stroke();
  }

  function drawBulb(ctx, x, y, radius, level, rgb) {
    const lit = P.clamp(level, 0, 1);
    if (lit > 0.01) glow(ctx, x, y, radius * (2.2 + lit * 2.6), rgb, 0.34 * lit + 0.06);
    const glass = ctx.createRadialGradient(x - radius * 0.3, y - radius * 0.32, radius * 0.12, x, y, radius);
    glass.addColorStop(0, lit > 0.04 ? "rgba(255, 252, 226, " + (0.5 + 0.5 * lit) + ")" : "rgba(178, 198, 228, 0.34)");
    glass.addColorStop(1, "rgba(112, 142, 196, 0.16)");
    ctx.fillStyle = glass;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, TAU);
    ctx.fill();
    ctx.lineWidth = Math.max(1.6, radius * 0.09);
    ctx.strokeStyle = "rgba(190, 215, 255, 0.5)";
    ctx.stroke();
    ctx.strokeStyle = lit > 0.04 ? "rgba(" + rgb + ", " + (0.55 + 0.45 * lit) + ")" : "rgba(150, 172, 206, 0.65)";
    ctx.lineWidth = Math.max(1.8, radius * 0.13);
    ctx.beginPath();
    ctx.moveTo(x - radius * 0.32, y - radius * 0.12);
    ctx.lineTo(x - radius * 0.12, y + radius * 0.3);
    ctx.lineTo(x + radius * 0.12, y - radius * 0.12);
    ctx.lineTo(x + radius * 0.32, y + radius * 0.3);
    ctx.stroke();
    ctx.fillStyle = "#7d8aa3";
    roundRect(ctx, x - radius * 0.3, y + radius * 0.7, radius * 0.6, radius * 0.4, radius * 0.12);
    ctx.fill();
  }

  function drawStageBackdrop(ctx, width, height, topColor, bottomColor) {
    const grad = ctx.createLinearGradient(0, 0, 0, height);
    grad.addColorStop(0, topColor);
    grad.addColorStop(1, bottomColor);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, width, height);
  }

  function drawBench(ctx, width, height, y) {
    ctx.fillStyle = "rgba(9, 16, 32, 0.9)";
    ctx.fillRect(0, y, width, height - y);
    ctx.strokeStyle = "rgba(140, 177, 255, 0.18)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }

  function pointerPos(canvas, stage, event) {
    const rect = canvas.getBoundingClientRect();
    const sx = rect.width ? stage.width / rect.width : 1;
    const sy = rect.height ? stage.height / rect.height : 1;
    return { x: (event.clientX - rect.left) * sx, y: (event.clientY - rect.top) * sy };
  }

  /* ── 실험대 등록 ──────────────────────────────────────────────── */

  const stations = [];

  function addStation(config) {
    config.wattsValue = 0;
    stations.push(config);
    return config;
  }

  function markFound(id) {
    if (progress.found[id]) return;
    progress.found[id] = true;
    saveProgress();
    renderFound();
    const stamp = doc.getElementById("stamp-" + id);
    if (stamp) stamp.hidden = false;
    const card = doc.getElementById("station-" + id);
    if (card) {
      card.classList.add("is-found");
      card.classList.remove("just-found");
      void card.offsetWidth;
      card.classList.add("just-found");
    }
    const goal = doc.getElementById("goal-" + id);
    if (goal) goal.classList.add("is-done");
    audio.chime();
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

  /* ────────────────────────────────────────────────────────────────
     01 닫힌 회로
     ──────────────────────────────────────────────────────────────── */

  function createCircuit() {
    const canvas = $("#canvas-circuit");
    if (!canvas) return null;
    const stage = createStage(canvas);
    const state = { material: "copper", voltage: 1.5, closed: true, phase: 0, total: 600, output: null };
    const readEl = $("#read-circuit");
    const meterEl = $("#meter-circuit");

    function compute() {
      state.output = P.circuitState({ material: state.material, voltage: state.voltage, closed: state.closed });
      return state.output;
    }

    function geometry() {
      const w = stage.width;
      const h = stage.height;
      const padX = Math.min(64, w * 0.11);
      const padY = Math.max(34, h * 0.16);
      const x0 = padX;
      const x1 = w - padX;
      const y0 = padY;
      const y1 = h - padY;
      return { w: w, h: h, x0: x0, x1: x1, y0: y0, y1: y1, cx: (x0 + x1) / 2, cy: (y0 + y1) / 2 };
    }

    function drawMaterial(ctx, kind, cx, cy, gap) {
      const half = gap / 2;
      ctx.save();
      if (kind === "copper") {
        ctx.strokeStyle = "#ff9d4d";
        ctx.lineWidth = 7;
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(cx - half, cy);
        ctx.quadraticCurveTo(cx, cy - 16, cx + half, cy);
        ctx.stroke();
        ctx.strokeStyle = "rgba(255, 220, 170, 0.5)";
        ctx.lineWidth = 2;
        ctx.stroke();
      } else if (kind === "coin") {
        const r = Math.min(half * 0.72, 20);
        const grad = ctx.createLinearGradient(cx - r, cy - r, cx + r, cy + r);
        grad.addColorStop(0, "#ffe08a");
        grad.addColorStop(1, "#c98b22");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, TAU);
        ctx.fill();
        ctx.strokeStyle = "rgba(255, 236, 180, 0.7)";
        ctx.lineWidth = 2;
        ctx.stroke();
      } else if (kind === "wood") {
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(-0.12);
        ctx.fillStyle = "#c99a5b";
        roundRect(ctx, -half * 0.9, -6, half * 1.8, 12, 6);
        ctx.fill();
        ctx.fillStyle = "rgba(120, 80, 40, 0.5)";
        roundRect(ctx, -half * 0.9, -6, half * 1.8, 4, 2);
        ctx.fill();
        ctx.restore();
      } else if (kind === "plastic") {
        ctx.save();
        ctx.translate(cx, cy);
        ctx.fillStyle = "rgba(140, 200, 255, 0.42)";
        roundRect(ctx, -half * 0.95, -9, half * 1.9, 18, 4);
        ctx.fill();
        ctx.strokeStyle = "rgba(190, 230, 255, 0.75)";
        ctx.lineWidth = 1.6;
        ctx.stroke();
        ctx.strokeStyle = "rgba(220, 240, 255, 0.7)";
        ctx.lineWidth = 1.4;
        for (let i = -3; i <= 3; i += 1) {
          ctx.beginPath();
          ctx.moveTo(i * (half * 0.26), -9);
          ctx.lineTo(i * (half * 0.26), -3);
          ctx.stroke();
        }
        ctx.restore();
      } else {
        ctx.fillStyle = "#ff8fa6";
        roundRect(ctx, -half * 0.8 + cx, cy - 10, half * 1.6, 20, 6);
        ctx.fill();
        ctx.fillStyle = "rgba(255, 255, 255, 0.28)";
        roundRect(ctx, -half * 0.8 + cx, cy - 10, half * 1.6, 7, 4);
        ctx.fill();
      }
      ctx.restore();
    }

    function draw() {
      const ctx = stage.ctx;
      const g = geometry();
      const out = state.output || compute();
      ctx.clearRect(0, 0, g.w, g.h);
      drawStageBackdrop(ctx, g.w, g.h, "#0a1428", "#060c1a");

      const loop = [
        [g.x0, g.y0],
        [g.x1, g.y0],
        [g.x1, g.y1],
        [g.x0, g.y1],
        [g.x0, g.y0],
      ];
      const segments = [];
      let total = 0;
      for (let i = 1; i < loop.length; i += 1) {
        const len = Math.hypot(loop[i][0] - loop[i - 1][0], loop[i][1] - loop[i - 1][1]);
        segments.push(len);
        total += len;
      }
      state.total = total;

      // 재료를 끼우는 틈은 전선을 그리지 않는다
      const gap = Math.min(96, (g.x1 - g.x0) * 0.22);
      const gapLeft = g.cx - gap / 2;
      const gapRight = g.cx + gap / 2;
      const rightPath = [
        [g.x0, g.y0],
        [g.x1, g.y0],
        [g.x1, g.y1],
        [gapRight, g.y1],
      ];
      const leftPath = [
        [gapLeft, g.y1],
        [g.x0, g.y1],
        [g.x0, g.y0],
      ];
      [rightPath, leftPath].forEach((path) => {
        drawWire(ctx, path, 7, "rgba(120, 150, 200, 0.5)");
        drawWire(ctx, path, 4, "rgba(196, 216, 250, 0.85)");
      });

      // 건전지
      const batteryH = Math.min(66, (g.y1 - g.y0) * 0.34);
      ctx.fillStyle = "#1d2b46";
      roundRect(ctx, g.x0 - 13, g.cy - batteryH / 2, 26, batteryH, 7);
      ctx.fill();
      ctx.strokeStyle = "rgba(215, 255, 0, 0.55)";
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.fillStyle = "#ffd85c";
      roundRect(ctx, g.x0 - 8, g.cy - batteryH / 2 + 5, 16, batteryH * 0.24, 3);
      ctx.fill();
      ctx.fillStyle = "#9fb2d6";
      roundRect(ctx, g.x0 - 12, g.cy + batteryH / 2 - batteryH * 0.2, 24, batteryH * 0.16, 3);
      ctx.fill();
      ctx.fillStyle = "#cfe0ff";
      ctx.font = "700 12px " + "AidenKR, system-ui, sans-serif";
      ctx.textAlign = "right";
      ctx.fillText(String(state.voltage.toFixed(1)) + "V", g.x0 - 20, g.cy + 4);

      // 전구
      const bulbR = Math.min(26, (g.y1 - g.y0) * 0.16);
      drawBulb(ctx, g.cx, g.y0, bulbR, out.brightness, "255, 224, 120");

      // 재료와 스위치
      if (state.closed) {
        drawMaterial(ctx, state.material, g.cx, g.y1, gap);
      } else {
        ctx.strokeStyle = "rgba(196, 216, 250, 0.85)";
        ctx.lineWidth = 5;
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(gapLeft, g.y1);
        ctx.lineTo(gapLeft + gap * 0.62, g.y1 - 22);
        ctx.stroke();
        drawMaterial(ctx, state.material, g.cx + gap * 0.12, g.y1 - 4, gap * 0.7);
      }
      ctx.fillStyle = "#8fa4c8";
      ctx.beginPath();
      ctx.arc(gapLeft, g.y1, 5, 0, TAU);
      ctx.arc(gapRight, g.y1, 5, 0, TAU);
      ctx.fill();

      // 흐르는 전자
      if (out.current > 0) {
        const count = Math.max(10, Math.round(total / 34));
        const spacing = total / count;
        const color = "rgba(215, 255, 0, " + P.clamp(0.35 + out.brightness * 0.6, 0, 1) + ")";
        for (let i = 0; i < count; i += 1) {
          let d = (state.phase + i * spacing) % total;
          let px = loop[0][0];
          let py = loop[0][1];
          for (let s = 0; s < segments.length; s += 1) {
            if (d <= segments[s]) {
              const t = segments[s] ? d / segments[s] : 0;
              px = loop[s][0] + (loop[s + 1][0] - loop[s][0]) * t;
              py = loop[s][1] + (loop[s + 1][1] - loop[s][1]) * t;
              break;
            }
            d -= segments[s];
          }
          glow(ctx, px, py, 9, "215, 255, 0", 0.5);
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(px, py, 3.4, 0, TAU);
          ctx.fill();
        }
      }

      setWidth(meterEl, out.brightness);
      if (!out.closed) {
        setText(readEl, "스위치가 열려 있어요. 길이 끊기면 전기가 흐르지 않아요.");
      } else if (!out.conductive) {
        setText(readEl, out.label + "은 전기가 통하지 않아요. 전구가 꺼졌어요.");
      } else if (out.current < 0.12) {
        setText(readEl, "전기가 아주 조금만 흘러요. 전압을 더 높여 볼까요?");
      } else {
        setText(
          readEl,
          "전류 " + out.current.toFixed(2) + "A · 밝기 " + Math.round(out.brightness * 100) + "%" +
            (out.brightness > 0.99 ? " · 환하게 켜졌어요!" : "")
        );
      }
      if (out.brightness > 0.99) markFound("circuit");
    }

    function sync() {
      compute();
      draw();
    }

    // 컨트롤 연결
    $$("[data-material]").forEach((button) => {
      button.addEventListener("click", () => {
        state.material = button.getAttribute("data-material");
        $$("[data-material]").forEach((other) => {
          other.setAttribute("aria-pressed", other === button ? "true" : "false");
        });
        audio.tick();
        sync();
      });
    });

    const switchButton = $("#switch-circuit");
    if (switchButton) {
      switchButton.addEventListener("click", () => {
        state.closed = !state.closed;
        switchButton.setAttribute("aria-pressed", state.closed ? "true" : "false");
        $(".switch-text", switchButton).textContent = state.closed ? "스위치 닫힘" : "스위치 열림";
        audio.pop();
        sync();
      });
    }

    const voltage = $("#voltage-range");
    if (voltage) {
      voltage.addEventListener("input", () => {
        state.voltage = Number(voltage.value);
        setText($("#voltage-output"), state.voltage.toFixed(1) + " V");
        sync();
      });
    }

    const reset = $("#reset-circuit");
    if (reset) {
      reset.addEventListener("click", () => {
        state.material = "copper";
        state.voltage = 1.5;
        state.closed = true;
        $$("[data-material]").forEach((other) => {
          other.setAttribute("aria-pressed", other.getAttribute("data-material") === "copper" ? "true" : "false");
        });
        if (switchButton) {
          switchButton.setAttribute("aria-pressed", "true");
          $(".switch-text", switchButton).textContent = "스위치 닫힘";
        }
        if (voltage) voltage.value = "1.5";
        setText($("#voltage-output"), "1.5 V");
        sync();
      });
    }

    function update(dt) {
      const out = state.output || compute();
      if (out.current > 0) {
        const speed = P.electronSpeed(out.current) * (prefersReducedMotion ? 0.4 : 1);
        state.phase = (state.phase + speed * dt) % state.total;
      }
    }

    return addStation({ id: "circuit", stage: stage, update: update, draw: draw, sync: sync, watts: () => 0 });
  }

  /* ────────────────────────────────────────────────────────────────
     02 마찰 전기
     ──────────────────────────────────────────────────────────────── */

  function createStatic() {
    const canvas = $("#canvas-static");
    if (!canvas) return null;
    const stage = createStage(canvas);
    const state = {
      charge: 0,
      balloon: { x: 0, y: 0 },
      bits: [],
      sparks: [],
      dragging: false,
      lastPointer: null,
      rubHold: false,
      pointerSpeed: 0,
      placed: false,
    };
    const readEl = $("#read-static");
    const meterEl = $("#meter-static");
    const HIT_BITS = 5;

    function layout() {
      const w = stage.width;
      const h = stage.height;
      return {
        w: w,
        h: h,
        hat: { x: w * 0.17, y: h * 0.46, r: Math.min(w * 0.1, h * 0.17) },
        tableY: h * 0.8,
        balloonR: Math.min(w * 0.075, h * 0.13),
      };
    }

    function seedBits(force) {
      const L = layout();
      if (state.bits.length && !force) return;
      state.bits = [];
      const count = 9;
      for (let i = 0; i < count; i += 1) {
        const t = (i + 0.5) / count;
        state.bits.push({
          x: L.w * 0.42 + t * L.w * 0.5 + (Math.random() - 0.5) * 18,
          y: L.tableY + 12 + Math.random() * (L.h - L.tableY - 24),
          angle: Math.random() * TAU,
          stuck: false,
          holdAngle: 0,
          holdDist: 0,
          vy: 0,
        });
      }
    }

    function placeBalloon() {
      const L = layout();
      if (!state.placed) {
        state.balloon.x = L.w * 0.52;
        state.balloon.y = L.h * 0.44;
        state.placed = true;
      }
      state.balloon.x = P.clamp(state.balloon.x, L.balloonR, L.w - L.balloonR);
      state.balloon.y = P.clamp(state.balloon.y, L.balloonR, L.h - L.balloonR * 0.6);
    }

    function update(dt) {
      const L = layout();
      placeBalloon();
      seedBits(false);

      const nearHat = Math.hypot(state.balloon.x - L.hat.x, state.balloon.y - L.hat.y) < L.hat.r * 1.7;
      let rubbing = 0;

      if (state.rubHold) {
        state.balloon.x += (L.hat.x + L.hat.r * 0.9 - state.balloon.x) * Math.min(1, dt * 9);
        state.balloon.y += (L.hat.y - state.balloon.y) * Math.min(1, dt * 9);
        rubbing = 0.85;
      } else if (nearHat) {
        rubbing = state.pointerSpeed;
      }

      if (rubbing > 0.02) {
        state.charge = P.staticRub(state.charge, rubbing, dt);
        if (!prefersReducedMotion && Math.random() < rubbing * 0.5) {
          state.sparks.push({
            x: state.balloon.x - Math.cos(Math.atan2(state.balloon.y - L.hat.y, state.balloon.x - L.hat.x)) * L.balloonR,
            y: state.balloon.y - Math.sin(Math.atan2(state.balloon.y - L.hat.y, state.balloon.x - L.hat.x)) * L.balloonR,
            vx: (Math.random() - 0.5) * 90,
            vy: -30 - Math.random() * 70,
            life: 0.5,
          });
        }
        if (Math.random() < dt * 6) audio.tick();
      } else {
        state.charge = P.staticDecay(state.charge, dt);
      }
      state.pointerSpeed *= Math.max(0, 1 - dt * 6);

      let stuck = 0;
      for (let i = 0; i < state.bits.length; i += 1) {
        const bit = state.bits[i];
        if (bit.stuck) {
          if (state.charge < P.STATIC_LIMITS.dropCharge) {
            bit.stuck = false;
            bit.vy = 0;
          } else {
            bit.holdDist += ((L.balloonR * 0.92 + 6) - bit.holdDist) * Math.min(1, dt * 8);
            bit.x = state.balloon.x + Math.cos(bit.holdAngle) * bit.holdDist;
            bit.y = state.balloon.y + Math.sin(bit.holdAngle) * bit.holdDist;
            bit.angle += dt * 0.6;
            stuck += 1;
            continue;
          }
        }
        const dx = state.balloon.x - bit.x;
        const dy = state.balloon.y - bit.y;
        const dist = Math.hypot(dx, dy) || 0.0001;
        if (P.staticGrab(state.charge, dist)) {
          bit.stuck = true;
          bit.holdAngle = Math.atan2(-dy, -dx);
          bit.holdDist = dist;
          audio.pop();
          stuck += 1;
          continue;
        }
        const pull = P.staticPull(state.charge, dist);
        if (pull > 0.02) {
          const step = pull * 120 * dt;
          bit.x += (dx / dist) * step;
          bit.y += (dy / dist) * step - pull * 26 * dt;
          bit.angle += pull * dt * 3;
        }
        if (bit.y < L.tableY + 6) {
          bit.y += 220 * dt;
        }
        bit.y = Math.min(bit.y, L.h - 8);
        bit.x = P.clamp(bit.x, 8, L.w - 8);
      }

      for (let i = state.sparks.length - 1; i >= 0; i -= 1) {
        const spark = state.sparks[i];
        spark.life -= dt;
        spark.x += spark.vx * dt;
        spark.y += spark.vy * dt;
        spark.vy += 120 * dt;
        if (spark.life <= 0) state.sparks.splice(i, 1);
      }

      setWidth(meterEl, state.charge / P.STATIC_LIMITS.maxCharge);
      if (stuck >= HIT_BITS) {
        setText(readEl, "와! 종이 조각 " + stuck + "개가 풍선에 붙었어요. 정전기예요!");
        markFound("static");
      } else if (state.charge >= P.STATIC_LIMITS.liftCharge) {
        setText(readEl, "전기가 모였어요! 종이 조각에 가까이 대 볼까요? (" + stuck + "/" + HIT_BITS + ")");
      } else if (state.charge > 6) {
        setText(readEl, "조금 더 세게 문질러 볼까요? (" + Math.round(state.charge) + "%)");
      } else {
        setText(readEl, "풍선을 털모자에 빠르게 문질러 보세요.");
      }
    }

    function draw() {
      const ctx = stage.ctx;
      const L = layout();
      ctx.clearRect(0, 0, L.w, L.h);
      drawStageBackdrop(ctx, L.w, L.h, "#111434", "#070c1c");

      // 책상
      ctx.fillStyle = "rgba(30, 44, 78, 0.75)";
      ctx.fillRect(0, L.tableY, L.w, L.h - L.tableY);
      ctx.strokeStyle = "rgba(140, 177, 255, 0.22)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(0, L.tableY);
      ctx.lineTo(L.w, L.tableY);
      ctx.stroke();

      // 털모자
      ctx.save();
      const hat = L.hat;
      ctx.fillStyle = "#3a4f8a";
      ctx.beginPath();
      ctx.arc(hat.x, hat.y, hat.r, Math.PI, 0);
      ctx.lineTo(hat.x + hat.r, hat.y + hat.r * 0.34);
      ctx.lineTo(hat.x - hat.r, hat.y + hat.r * 0.34);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = "#26356b";
      roundRect(ctx, hat.x - hat.r * 1.16, hat.y + hat.r * 0.26, hat.r * 2.32, hat.r * 0.3, hat.r * 0.14);
      ctx.fill();
      ctx.strokeStyle = "rgba(190, 210, 255, 0.35)";
      ctx.lineWidth = 2;
      for (let i = -3; i <= 3; i += 1) {
        ctx.beginPath();
        ctx.moveTo(hat.x + i * hat.r * 0.26, hat.y - hat.r * 0.1);
        ctx.quadraticCurveTo(
          hat.x + i * hat.r * 0.26 + hat.r * 0.1,
          hat.y - hat.r * 0.5,
          hat.x + i * hat.r * 0.26,
          hat.y - hat.r * 0.86
        );
        ctx.stroke();
      }
      ctx.restore();

      // 종이 조각
      state.bits.forEach((bit) => {
        ctx.save();
        ctx.translate(bit.x, bit.y);
        ctx.rotate(bit.angle);
        ctx.fillStyle = bit.stuck ? "#fff4c2" : "#dbe6ff";
        ctx.fillRect(-6, -5, 12, 10);
        ctx.strokeStyle = "rgba(90, 120, 180, 0.75)";
        ctx.lineWidth = 1.2;
        ctx.strokeRect(-6, -5, 12, 10);
        ctx.restore();
      });

      // 끌어당기는 선
      if (state.charge > 12) {
        state.bits.forEach((bit) => {
          const dist = Math.hypot(state.balloon.x - bit.x, state.balloon.y - bit.y);
          const pull = P.staticPull(state.charge, dist);
          if (pull > 0.04 && !bit.stuck) {
            ctx.strokeStyle = "rgba(183, 155, 255, " + pull * 0.7 + ")";
            ctx.lineWidth = 1.4;
            ctx.setLineDash([4, 5]);
            ctx.beginPath();
            ctx.moveTo(bit.x, bit.y);
            ctx.lineTo(state.balloon.x, state.balloon.y);
            ctx.stroke();
            ctx.setLineDash([]);
          }
        });
      }

      // 불꽃
      state.sparks.forEach((spark) => {
        ctx.fillStyle = "rgba(215, 255, 0, " + P.clamp(spark.life, 0, 1) + ")";
        ctx.beginPath();
        ctx.arc(spark.x, spark.y, 2.4, 0, TAU);
        ctx.fill();
      });

      // 풍선
      const b = state.balloon;
      const chargeRatio = state.charge / P.STATIC_LIMITS.maxCharge;
      glow(ctx, b.x, b.y, L.balloonR * (2 + chargeRatio * 1.6), "183, 155, 255", 0.12 + chargeRatio * 0.4);
      ctx.save();
      ctx.translate(b.x, b.y);
      ctx.fillStyle = "#ff6f8b";
      ctx.beginPath();
      ctx.ellipse(0, 0, L.balloonR * 0.86, L.balloonR, 0, 0, TAU);
      ctx.fill();
      ctx.fillStyle = "rgba(255, 255, 255, 0.35)";
      ctx.beginPath();
      ctx.ellipse(-L.balloonR * 0.3, -L.balloonR * 0.36, L.balloonR * 0.24, L.balloonR * 0.32, -0.5, 0, TAU);
      ctx.fill();
      ctx.strokeStyle = "rgba(255, 255, 255, 0.45)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(0, L.balloonR * 0.98);
      ctx.quadraticCurveTo(L.balloonR * 0.5, L.balloonR * 1.5, 0, L.balloonR * 2);
      ctx.stroke();
      ctx.restore();

      // 처음 안내 화살표
      if (state.charge < 4 && !state.rubHold) {
        const pulse = 0.5 + 0.5 * Math.sin(Date.now() / 320);
        ctx.strokeStyle = "rgba(215, 255, 0, " + (0.25 + pulse * 0.45) + ")";
        ctx.lineWidth = 3;
        ctx.setLineDash([7, 7]);
        ctx.beginPath();
        ctx.moveTo(b.x - L.balloonR * 1.4, b.y);
        ctx.lineTo(L.hat.x + L.hat.r * 0.6, L.hat.y);
        ctx.stroke();
        ctx.setLineDash([]);
      }
    }

    function setPointer(event) {
      const pos = pointerPos(canvas, stage, event);
      if (state.lastPointer) {
        const move = Math.hypot(pos.x - state.lastPointer.x, pos.y - state.lastPointer.y);
        state.pointerSpeed = P.clamp(move / 9, 0, 1);
      }
      state.lastPointer = pos;
      state.balloon.x = pos.x;
      state.balloon.y = pos.y;
      state.placed = true;
    }

    canvas.addEventListener("pointerdown", (event) => {
      canvas.setPointerCapture(event.pointerId);
      state.dragging = true;
      setPointer(event);
      audio.ensure();
    });
    canvas.addEventListener("pointermove", (event) => {
      if (!state.dragging) return;
      setPointer(event);
    });
    canvas.addEventListener("pointerup", () => {
      state.dragging = false;
      state.lastPointer = null;
    });
    canvas.addEventListener("pointercancel", () => {
      state.dragging = false;
      state.lastPointer = null;
    });

    canvas.addEventListener("keydown", (event) => {
      const step = event.shiftKey ? 26 : 12;
      if (event.key === "ArrowLeft") {
        state.balloon.x -= step;
      } else if (event.key === "ArrowRight") {
        state.balloon.x += step;
      } else if (event.key === "ArrowUp") {
        state.balloon.y -= step;
      } else if (event.key === "ArrowDown") {
        state.balloon.y += step;
      } else if (event.key === " " || event.key === "Enter") {
        state.rubHold = !state.rubHold;
      } else {
        return;
      }
      state.placed = true;
      event.preventDefault();
    });

    const rubButton = $("#rub-button");
    if (rubButton) {
      const on = () => {
        state.rubHold = true;
        audio.ensure();
      };
      const off = () => {
        state.rubHold = false;
      };
      rubButton.addEventListener("pointerdown", on);
      rubButton.addEventListener("pointerup", off);
      rubButton.addEventListener("pointerleave", off);
      rubButton.addEventListener("pointercancel", off);
      rubButton.addEventListener("keydown", (event) => {
        if (event.key === " " || event.key === "Enter") on();
      });
      rubButton.addEventListener("keyup", (event) => {
        if (event.key === " " || event.key === "Enter") off();
      });
      rubButton.addEventListener("blur", off);
    }

    const discharge = $("#discharge-button");
    if (discharge) {
      discharge.addEventListener("click", () => {
        state.charge = 0;
        state.bits.forEach((bit) => {
          bit.stuck = false;
        });
        audio.tone({ freq: 420, toFreq: 140, dur: 0.22, type: "sawtooth", gain: 0.05 });
      });
    }

    function sync() {
      seedBits(false);
      placeBalloon();
      draw();
    }

    return addStation({ id: "static", stage: stage, update: update, draw: draw, sync: sync, watts: () => 0 });
  }

  /* ────────────────────────────────────────────────────────────────
     03 과일 전지
     ──────────────────────────────────────────────────────────────── */

  function createFruit() {
    const canvas = $("#canvas-fruit");
    if (!canvas) return null;
    const stage = createStage(canvas);
    const state = { fruit: "lemon", cells: 1, output: null, bubbles: [], time: 0 };
    const readEl = $("#read-fruit");
    const meterEl = $("#meter-fruit");

    function compute() {
      state.output = P.fruitBattery({ fruit: state.fruit, cells: state.cells });
      return state.output;
    }

    function layout() {
      const w = stage.width;
      const h = stage.height;
      const usable = w * 0.66;
      const spacing = Math.min(usable / Math.max(state.cells, 1), 118);
      const r = Math.min(spacing * 0.3, h * 0.12, 34);
      const y = h * 0.58;
      const startX = w * 0.06 + spacing * 0.5;
      return { w: w, h: h, spacing: spacing, r: r, y: y, startX: startX, led: { x: w * 0.88, y: h * 0.3 } };
    }

    function drawFruitBody(ctx, x, y, r, color, kind) {
      ctx.save();
      ctx.translate(x, y);
      if (kind === "potato") {
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.ellipse(0, 0, r * 1.24, r * 0.86, -0.12, 0, TAU);
        ctx.fill();
        ctx.fillStyle = "rgba(90, 60, 30, 0.35)";
        ctx.beginPath();
        ctx.arc(-r * 0.4, r * 0.2, r * 0.14, 0, TAU);
        ctx.arc(r * 0.5, -r * 0.24, r * 0.1, 0, TAU);
        ctx.fill();
      } else if (kind === "vinegar") {
        ctx.fillStyle = "rgba(180, 210, 255, 0.24)";
        roundRect(ctx, -r * 0.86, -r * 0.9, r * 1.72, r * 1.8, r * 0.34);
        ctx.fill();
        ctx.strokeStyle = "rgba(220, 240, 255, 0.6)";
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.fillStyle = color;
        roundRect(ctx, -r * 0.78, -r * 0.14, r * 1.56, r * 1.02, r * 0.22);
        ctx.fill();
      } else if (kind === "apple") {
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(-r * 0.16, 0, r * 0.88, 0, TAU);
        ctx.arc(r * 0.16, 0, r * 0.88, 0, TAU);
        ctx.fill();
        ctx.strokeStyle = "#4c7a2a";
        ctx.lineWidth = Math.max(2, r * 0.09);
        ctx.beginPath();
        ctx.moveTo(0, -r * 0.8);
        ctx.quadraticCurveTo(r * 0.24, -r * 1.06, r * 0.5, -r * 0.96);
        ctx.stroke();
      } else if (kind === "tomato") {
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.ellipse(0, 0, r * 0.98, r * 0.84, 0, 0, TAU);
        ctx.fill();
        ctx.fillStyle = "#3f8f3a";
        for (let i = 0; i < 5; i += 1) {
          const a = (i / 5) * TAU;
          ctx.beginPath();
          ctx.ellipse(Math.cos(a) * r * 0.3, -r * 0.72 + Math.sin(a) * r * 0.12, r * 0.26, r * 0.1, a, 0, TAU);
          ctx.fill();
        }
      } else {
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.ellipse(0, 0, r * 1.16, r * 0.86, -0.08, 0, TAU);
        ctx.fill();
        ctx.fillStyle = "rgba(255, 255, 255, 0.28)";
        ctx.beginPath();
        ctx.ellipse(-r * 0.34, -r * 0.3, r * 0.34, r * 0.18, -0.5, 0, TAU);
        ctx.fill();
      }
      ctx.restore();
    }

    function draw() {
      const ctx = stage.ctx;
      const L = layout();
      const out = state.output || compute();
      ctx.clearRect(0, 0, L.w, L.h);
      drawStageBackdrop(ctx, L.w, L.h, "#0b1a2e", "#060c1a");
      drawBench(ctx, L.w, L.h, L.h * 0.82);

      const fruit = P.FRUITS[state.fruit];
      const cells = [];
      for (let i = 0; i < state.cells; i += 1) {
        cells.push({ x: L.startX + i * L.spacing, y: L.y, r: L.r });
      }

      // 과일과 전극
      cells.forEach((cell, index) => {
        drawFruitBody(ctx, cell.x, cell.y, cell.r, fruit.color, state.fruit);
        const plateH = cell.r * 1.3;
        // 아연판 (왼쪽)
        ctx.fillStyle = "#b8c2d0";
        roundRect(ctx, cell.x - cell.r * 0.72, cell.y - plateH / 2, cell.r * 0.2, plateH, 2);
        ctx.fill();
        ctx.fillStyle = "#7d879c";
        ctx.fillRect(cell.x - cell.r * 0.72, cell.y + plateH / 2 - 4, cell.r * 0.2, 4);
        // 구리판 (오른쪽)
        ctx.fillStyle = "#e08a3c";
        roundRect(ctx, cell.x + cell.r * 0.52, cell.y - plateH / 2, cell.r * 0.2, plateH, 2);
        ctx.fill();
        ctx.fillStyle = "#a55f22";
        ctx.fillRect(cell.x + cell.r * 0.52, cell.y + plateH / 2 - 4, cell.r * 0.2, 4);
        if (index === 0) {
          ctx.fillStyle = "rgba(215, 255, 0, 0.85)";
          ctx.font = "700 10px AidenKR, system-ui, sans-serif";
          ctx.textAlign = "center";
          ctx.fillText("Zn", cell.x - cell.r * 0.62, cell.y - plateH / 2 - 6);
          ctx.fillStyle = "rgba(255, 190, 120, 0.9)";
          ctx.fillText("Cu", cell.x + cell.r * 0.62, cell.y - plateH / 2 - 6);
        }
      });

      // 직렬 연결선
      const wireColor = out.lit ? "rgba(255, 216, 120, 0.95)" : "rgba(180, 200, 235, 0.7)";
      for (let i = 0; i < cells.length - 1; i += 1) {
        const a = cells[i];
        const b = cells[i + 1];
        drawWire(
          ctx,
          [
            [a.x + a.r * 0.62, a.y - a.r * 0.6],
            [a.x + a.r * 0.62, a.y - a.r * 1.5],
            [b.x - b.r * 0.82, b.y - b.r * 1.5],
            [b.x - b.r * 0.82, b.y - b.r * 0.6],
          ],
          3.5,
          wireColor
        );
      }
      if (cells.length) {
        const first = cells[0];
        const last = cells[cells.length - 1];
        drawWire(
          ctx,
          [
            [first.x - first.r * 0.62, first.y - first.r * 0.6],
            [first.x - first.r * 0.62, L.led.y + 26],
            [L.led.x - 16, L.led.y + 26],
            [L.led.x - 16, L.led.y + 12],
          ],
          3.5,
          wireColor
        );
        drawWire(
          ctx,
          [
            [last.x + last.r * 0.62, last.y - last.r * 0.6],
            [last.x + last.r * 0.62, L.led.y + 38],
            [L.led.x + 16, L.led.y + 38],
            [L.led.x + 16, L.led.y + 12],
          ],
          3.5,
          wireColor
        );
      }

      // 기포
      if (out.lit && !prefersReducedMotion) {
        state.bubbles.forEach((bubble) => {
          ctx.fillStyle = "rgba(220, 245, 255, " + P.clamp(bubble.life, 0, 1) * 0.7 + ")";
          ctx.beginPath();
          ctx.arc(bubble.x, bubble.y, bubble.r, 0, TAU);
          ctx.fill();
        });
      }

      // LED
      drawWire(ctx, [[L.led.x - 16, L.led.y + 12], [L.led.x - 6, L.led.y + 2]], 3, wireColor);
      drawWire(ctx, [[L.led.x + 16, L.led.y + 12], [L.led.x + 6, L.led.y + 2]], 3, wireColor);
      ctx.save();
      ctx.translate(L.led.x, L.led.y - 6);
      ctx.rotate(Math.PI);
      ctx.fillStyle = out.lit ? "rgba(255, 90, 110, 0.9)" : "rgba(120, 130, 150, 0.6)";
      ctx.beginPath();
      ctx.moveTo(-13, 6);
      ctx.lineTo(-13, -2);
      ctx.lineTo(0, -14);
      ctx.lineTo(13, -2);
      ctx.lineTo(13, 6);
      ctx.closePath();
      ctx.fill();
      ctx.restore();
      glow(ctx, L.led.x, L.led.y - 6, 42, "255, 90, 110", out.level * 0.7);

      // 전압 표시
      ctx.fillStyle = "rgba(6, 12, 26, 0.85)";
      roundRect(ctx, L.w - 132, L.h - 44, 118, 32, 10);
      ctx.fill();
      ctx.strokeStyle = "rgba(140, 177, 255, 0.3)";
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.fillStyle = out.lit ? "#d7ff00" : "#9fb2d6";
      ctx.font = "800 15px AidenKR, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(out.volts.toFixed(2) + " V", L.w - 73, L.h - 22);

      setWidth(meterEl, out.level);
      if (!out.lit) {
        setText(
          readEl,
          fruit.label + " " + out.cells + "개 = " + out.volts.toFixed(2) + "V · LED는 " +
            P.LED_LIMITS.forwardVolts.toFixed(1) + "V가 필요해요. 전지를 더 이어 볼까요?"
        );
      } else if (out.full) {
        setText(readEl, fruit.label + " " + out.cells + "개 = " + out.volts.toFixed(2) + "V · LED가 환하게 켜졌어요!");
      } else {
        setText(
          readEl,
          fruit.label + " " + out.cells + "개 = " + out.volts.toFixed(2) + "V · LED가 흐리게 켜졌어요. 하나만 더!"
        );
      }
      if (out.full) markFound("fruit");
    }

    function update(dt) {
      state.time += dt;
      const out = state.output || compute();
      if (out.lit && !prefersReducedMotion) {
        if (state.bubbles.length < 26 && Math.random() < dt * 14 * P.clamp(state.cells / 3, 0.3, 1.6)) {
          const L = layout();
          const index = Math.floor(Math.random() * Math.max(state.cells, 1));
          const cell = { x: L.startX + index * L.spacing, y: L.y, r: L.r };
          state.bubbles.push({
            x: cell.x + (Math.random() - 0.5) * cell.r * 1.2,
            y: cell.y + cell.r * 0.4,
            r: 1.6 + Math.random() * 2.4,
            vy: -14 - Math.random() * 22,
            life: 1,
          });
        }
      }
      for (let i = state.bubbles.length - 1; i >= 0; i -= 1) {
        const bubble = state.bubbles[i];
        bubble.y += bubble.vy * dt;
        bubble.life -= dt * 0.7;
        if (bubble.life <= 0) state.bubbles.splice(i, 1);
      }
    }

    function sync() {
      compute();
      draw();
    }

    $$("[data-fruit]").forEach((button) => {
      button.addEventListener("click", () => {
        state.fruit = button.getAttribute("data-fruit");
        $$("[data-fruit]").forEach((other) => {
          other.setAttribute("aria-pressed", other === button ? "true" : "false");
        });
        audio.tick();
        sync();
      });
    });

    function setCells(next) {
      state.cells = Math.round(P.clamp(next, 1, 8));
      setText($("#cells-count"), state.cells + "개");
      audio.tick();
      sync();
    }

    const minus = $("#cells-minus");
    if (minus) minus.addEventListener("click", () => setCells(state.cells - 1));
    const plus = $("#cells-plus");
    if (plus) plus.addEventListener("click", () => setCells(state.cells + 1));

    return addStation({ id: "fruit", stage: stage, update: update, draw: draw, sync: sync, watts: () => 0 });
  }

  /* ────────────────────────────────────────────────────────────────
     04 손잡이 발전기
     ──────────────────────────────────────────────────────────────── */

  function createGenerator() {
    const canvas = $("#canvas-generator");
    if (!canvas) return null;
    const stage = createStage(canvas);
    const MAGNET_TESLA = { 1: 0.08, 2: 0.18, 3: 0.35 };
    const MAGNET_LABEL = { 1: "약함", 2: "보통", 3: "강함" };
    const state = {
      turns: 240,
      magnet: 2,
      angle: 0,
      rpm: 0,
      manual: false,
      targetRpm: 0,
      lastAngle: 0,
      output: null,
    };
    const readEl = $("#read-generator");
    const meterEl = $("#meter-generator");

    function compute() {
      state.output = P.generatorOutput({
        turns: state.turns,
        fieldTesla: MAGNET_TESLA[state.magnet],
        rpm: state.rpm,
      });
      return state.output;
    }

    function layout() {
      const w = stage.width;
      const h = stage.height;
      return {
        w: w,
        h: h,
        coil: { x: w * 0.34, y: h * 0.54, rx: Math.min(w * 0.17, h * 0.26), ry: Math.min(w * 0.1, h * 0.16) },
        crank: { x: w * 0.72, y: h * 0.62, r: Math.min(w * 0.12, h * 0.22) },
        bulb: { x: w * 0.5, y: h * 0.16, r: Math.min(w * 0.05, h * 0.09) },
      };
    }

    function update(dt) {
      if (!state.manual) {
        if (state.targetRpm > 0) {
          state.rpm += (state.targetRpm - state.rpm) * Math.min(1, dt * 3.2);
        } else {
          state.rpm *= Math.max(0, 1 - dt * 1.6);
          if (state.rpm < 0.4) state.rpm = 0;
        }
      } else {
        state.rpm *= Math.max(0, 1 - dt * 0.6);
      }
      state.angle += (state.rpm * TAU * dt) / 60;
      const out = compute();
      setWidth(meterEl, out.level);
      if (state.rpm < 1) {
        setText(readEl, "손잡이를 돌려 보세요. 지금은 전기가 생기지 않아요.");
      } else if (out.level >= 1) {
        setText(readEl, "발전량 " + out.watts.toFixed(2) + "W · " + Math.round(state.rpm) + "rpm · 전구가 환해요!");
      } else {
        setText(
          readEl,
          "발전량 " + out.watts.toFixed(2) + "W · " + Math.round(state.rpm) + "rpm · 더 빠르게 돌려 볼까요?"
        );
      }
      if (out.level >= 1) markFound("generator");
    }

    function draw() {
      const ctx = stage.ctx;
      const L = layout();
      const out = state.output || compute();
      ctx.clearRect(0, 0, L.w, L.h);
      drawStageBackdrop(ctx, L.w, L.h, "#0c1526", "#060c1a");
      drawBench(ctx, L.w, L.h, L.h * 0.86);

      // 코일
      ctx.save();
      ctx.translate(L.coil.x, L.coil.y);
      const coilRgb = out.level > 0.05 ? "255, 202, 88" : "140, 177, 255";
      glow(ctx, 0, 0, Math.max(L.coil.rx, L.coil.ry) * 1.9, coilRgb, 0.1 + out.level * 0.4);
      const turnCount = Math.max(3, Math.round(state.turns / 90));
      ctx.lineCap = "round";
      for (let i = 0; i < turnCount; i += 1) {
        const t = i / turnCount;
        const rx = L.coil.rx * (0.72 + t * 0.5);
        const ry = L.coil.ry * (0.7 + t * 0.5);
        ctx.strokeStyle = "rgba(224, 138, 60, " + (0.35 + out.level * 0.55) + ")";
        ctx.lineWidth = 2.4;
        ctx.beginPath();
        ctx.ellipse(0, 0, rx, ry, 0, 0, TAU);
        ctx.stroke();
      }
      // 회전하는 자석
      ctx.rotate(state.angle);
      const barW = L.coil.rx * 1.5;
      const barH = Math.max(16, L.coil.ry * 0.5);
      ctx.fillStyle = "#ff5a6e";
      roundRect(ctx, -barW / 2, -barH / 2, barW / 2, barH, 4);
      ctx.fill();
      ctx.fillStyle = "#4c8dff";
      roundRect(ctx, 0, -barH / 2, barW / 2, barH, 4);
      ctx.fill();
      ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
      ctx.font = "800 " + Math.round(barH * 0.6) + "px AidenKR, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("N", -barW * 0.28, barH * 0.22);
      ctx.fillText("S", barW * 0.28, barH * 0.22);
      ctx.restore();

      // 축과 손잡이
      drawWire(
        ctx,
        [[L.coil.x, L.coil.y], [L.crank.x, L.crank.y]],
        6,
        "rgba(150, 172, 206, 0.8)"
      );
      const knobX = L.crank.x + Math.cos(state.angle) * L.crank.r;
      const knobY = L.crank.y + Math.sin(state.angle) * L.crank.r;
      ctx.strokeStyle = "rgba(215, 255, 0, 0.55)";
      ctx.lineWidth = 6;
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(L.crank.x, L.crank.y);
      ctx.lineTo(knobX, knobY);
      ctx.stroke();
      ctx.fillStyle = "rgba(215, 255, 0, 0.22)";
      ctx.beginPath();
      ctx.arc(L.crank.x, L.crank.y, L.crank.r, 0, TAU);
      ctx.strokeStyle = "rgba(215, 255, 0, 0.28)";
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.fillStyle = "#d7ff00";
      ctx.beginPath();
      ctx.arc(knobX, knobY, 11, 0, TAU);
      ctx.fill();
      ctx.fillStyle = "#0b1a2e";
      ctx.beginPath();
      ctx.arc(L.crank.x, L.crank.y, 7, 0, TAU);
      ctx.fill();

      // 전선과 전구
      const lit = out.level;
      drawWire(
        ctx,
        [[L.coil.x + L.coil.rx * 1.1, L.coil.y - L.coil.ry * 0.6], [L.bulb.x - L.bulb.r * 1.6, L.bulb.y + L.bulb.r]],
        3.5,
        lit > 0.05 ? "rgba(255, 216, 120, 0.95)" : "rgba(180, 200, 235, 0.6)"
      );
      drawWire(
        ctx,
        [[L.coil.x + L.coil.rx * 0.4, L.coil.y - L.coil.ry * 1.1], [L.bulb.x + L.bulb.r * 1.6, L.bulb.y + L.bulb.r]],
        3.5,
        lit > 0.05 ? "rgba(255, 216, 120, 0.95)" : "rgba(180, 200, 235, 0.6)"
      );
      drawBulb(ctx, L.bulb.x, L.bulb.y, L.bulb.r, lit, "255, 202, 88");

      ctx.fillStyle = "rgba(6, 12, 26, 0.82)";
      roundRect(ctx, 12, L.h - 40, 150, 30, 9);
      ctx.fill();
      ctx.fillStyle = "#d7ff00";
      ctx.font = "800 14px AidenKR, system-ui, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText(out.watts.toFixed(2) + " W · " + Math.round(state.rpm) + " rpm", 24, L.h - 19);
    }

    function angleAt(event) {
      const L = layout();
      const pos = pointerPos(canvas, stage, event);
      return Math.atan2(pos.y - L.crank.y, pos.x - L.crank.x);
    }

    canvas.addEventListener("pointerdown", (event) => {
      canvas.setPointerCapture(event.pointerId);
      state.manual = true;
      state.lastAngle = angleAt(event);
      audio.ensure();
    });
    canvas.addEventListener("pointermove", (event) => {
      if (!state.manual) return;
      const next = angleAt(event);
      let delta = next - state.lastAngle;
      while (delta > Math.PI) delta -= TAU;
      while (delta < -Math.PI) delta += TAU;
      state.lastAngle = next;
      const instant = (P.clamp(Math.abs(delta), 0, 1.2) * 60) / TAU / 0.016;
      state.rpm = P.clamp(state.rpm * 0.6 + instant * 0.4, 0, 900);
      state.angle = next;
    });
    const endDrag = () => {
      state.manual = false;
    };
    canvas.addEventListener("pointerup", endDrag);
    canvas.addEventListener("pointercancel", endDrag);

    canvas.addEventListener("keydown", (event) => {
      if (event.key === "ArrowRight" || event.key === "ArrowUp") {
        state.angle += 0.32;
        state.rpm = P.clamp(state.rpm + 26, 0, 900);
        state.manual = true;
      } else if (event.key === "ArrowLeft" || event.key === "ArrowDown") {
        state.angle -= 0.32;
        state.rpm = P.clamp(state.rpm + 26, 0, 900);
        state.manual = true;
      } else if (event.key === " ") {
        setSpin(state.targetRpm > 0 ? 0 : 140);
        event.preventDefault();
        return;
      } else {
        return;
      }
      event.preventDefault();
      window.setTimeout(() => {
        state.manual = false;
      }, 220);
    });

    function setSpin(rpm) {
      state.targetRpm = rpm;
      $$("[data-spin]").forEach((button) => {
        button.setAttribute("aria-pressed", Number(button.getAttribute("data-spin")) === rpm ? "true" : "false");
      });
      audio.tick();
    }

    $$("[data-spin]").forEach((button) => {
      button.addEventListener("click", () => setSpin(Number(button.getAttribute("data-spin"))));
    });

    const turns = $("#turns-range");
    if (turns) {
      turns.addEventListener("input", () => {
        state.turns = Number(turns.value);
        setText($("#turns-output"), state.turns + "번");
        compute();
      });
    }
    const magnet = $("#magnet-range");
    if (magnet) {
      magnet.addEventListener("input", () => {
        state.magnet = Number(magnet.value);
        setText($("#magnet-output"), MAGNET_LABEL[state.magnet]);
        compute();
      });
    }

    return addStation({
      id: "generator",
      stage: stage,
      update: update,
      draw: draw,
      sync: function () {
        compute();
        draw();
      },
      watts: () => (state.output ? state.output.watts : 0),
    });
  }

  /* ────────────────────────────────────────────────────────────────
     05 태양광 발전
     ──────────────────────────────────────────────────────────────── */

  function createSolar() {
    const canvas = $("#canvas-solar");
    if (!canvas) return null;
    const stage = createStage(canvas);
    const state = { altitude: 40, tilt: 15, cloud: 0, auto: false, output: null };
    const readEl = $("#read-solar");
    const meterEl = $("#meter-solar");

    function compute() {
      state.output = P.solarOutput({ sunAltitudeDeg: state.altitude, panelTiltDeg: state.tilt, cloudiness: state.cloud / 100 });
      return state.output;
    }

    function layout() {
      const w = stage.width;
      const h = stage.height;
      const horizon = h * 0.84;
      const t = P.clamp((state.altitude - 5) / 85, 0, 1);
      return {
        w: w,
        h: h,
        horizon: horizon,
        sun: { x: w * (0.12 + 0.74 * t), y: horizon - Math.sin(state.altitude * DEG) * (h * 0.66), r: Math.min(w * 0.05, h * 0.08) },
        pivot: { x: w * 0.58, y: horizon - h * 0.05 },
        panelLen: Math.min(w * 0.4, h * 0.5),
      };
    }

    function draw() {
      const ctx = stage.ctx;
      const L = layout();
      const out = state.output || compute();
      ctx.clearRect(0, 0, L.w, L.h);

      // 하늘
      const day = P.clamp(state.altitude / 90, 0, 1);
      const sky = ctx.createLinearGradient(0, 0, 0, L.horizon);
      sky.addColorStop(0, "rgb(" + Math.round(20 + day * 60) + ", " + Math.round(40 + day * 90) + ", " + Math.round(96 + day * 90) + ")");
      sky.addColorStop(1, "rgb(" + Math.round(74 + day * 100) + ", " + Math.round(96 + day * 96) + ", " + Math.round(140 + day * 60) + ")");
      ctx.fillStyle = sky;
      ctx.fillRect(0, 0, L.w, L.horizon);

      // 해
      glow(ctx, L.sun.x, L.sun.y, L.sun.r * 4, "255, 216, 92", 0.4 * (1 - state.cloud / 140));
      ctx.fillStyle = "#ffd85c";
      ctx.beginPath();
      ctx.arc(L.sun.x, L.sun.y, L.sun.r, 0, TAU);
      ctx.fill();
      ctx.strokeStyle = "rgba(255, 216, 92, " + 0.35 * (1 - state.cloud / 120) + ")";
      ctx.lineWidth = 3;
      for (let i = 0; i < 8; i += 1) {
        const a = (i / 8) * TAU;
        ctx.beginPath();
        ctx.moveTo(L.sun.x + Math.cos(a) * L.sun.r * 1.3, L.sun.y + Math.sin(a) * L.sun.r * 1.3);
        ctx.lineTo(L.sun.x + Math.cos(a) * L.sun.r * 1.9, L.sun.y + Math.sin(a) * L.sun.r * 1.9);
        ctx.stroke();
      }

      // 구름
      const cloudAmount = state.cloud / 100;
      if (cloudAmount > 0.02) {
        for (let i = 0; i < 4; i += 1) {
          const cx = L.w * (0.1 + i * 0.24) + Math.sin(Date.now() / 4000 + i) * 8;
          const cy = L.h * (0.12 + (i % 2) * 0.1);
          const cr = Math.min(L.w * 0.09, L.h * 0.14) * (0.8 + (i % 3) * 0.2);
          ctx.fillStyle = "rgba(210, 222, 245, " + 0.25 + cloudAmount * 0.6 + ")";
          ctx.beginPath();
          ctx.arc(cx, cy, cr, 0, TAU);
          ctx.arc(cx + cr * 0.8, cy + cr * 0.1, cr * 0.75, 0, TAU);
          ctx.arc(cx - cr * 0.75, cy + cr * 0.16, cr * 0.6, 0, TAU);
          ctx.fill();
        }
      }

      // 땅
      ctx.fillStyle = "#123024";
      ctx.fillRect(0, L.horizon, L.w, L.h - L.horizon);
      ctx.strokeStyle = "rgba(180, 220, 255, 0.25)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(0, L.horizon);
      ctx.lineTo(L.w, L.horizon);
      ctx.stroke();

      // 햇빛 선
      const dirSign = L.sun.x < L.pivot.x ? -1 : 1;
      const incidence = out.incidence;
      ctx.strokeStyle = "rgba(255, 240, 170, " + 0.14 + incidence * 0.5 + ")";
      ctx.lineWidth = 2.4;
      for (let i = -2; i <= 2; i += 1) {
        const startX = L.sun.x + i * L.sun.r * 0.5;
        const startY = L.sun.y + Math.abs(i) * L.sun.r * 0.24;
        ctx.beginPath();
        ctx.moveTo(startX, startY);
        ctx.lineTo(L.pivot.x + i * L.panelLen * 0.18 * dirSign, L.pivot.y - L.panelLen * 0.34);
        ctx.stroke();
      }

      // 패널
      const tiltRad = state.tilt * DEG;
      const sx = dirSign * Math.cos(tiltRad) * L.panelLen * 0.5;
      const sy = -Math.sin(tiltRad) * L.panelLen * 0.5;
      const p1 = { x: L.pivot.x + sx, y: L.pivot.y + sy };
      const p2 = { x: L.pivot.x - sx, y: L.pivot.y - sy };
      // 지지대
      drawWire(ctx, [[L.pivot.x, L.pivot.y], [L.pivot.x, L.horizon + 4]], 8, "rgba(120, 140, 175, 0.9)");
      // 패널 몸체
      ctx.save();
      ctx.lineCap = "round";
      ctx.strokeStyle = "rgba(30, 62, 120, 0.95)";
      ctx.lineWidth = Math.max(16, L.panelLen * 0.13);
      ctx.beginPath();
      ctx.moveTo(p2.x, p2.y);
      ctx.lineTo(p1.x, p1.y);
      ctx.stroke();
      ctx.strokeStyle = "rgba(90, 150, 255, " + 0.4 + incidence * 0.6 + ")";
      ctx.lineWidth = Math.max(12, L.panelLen * 0.1);
      ctx.stroke();
      // 셀 구분선
      const cells = 5;
      ctx.strokeStyle = "rgba(190, 220, 255, 0.4)";
      ctx.lineWidth = 1.6;
      for (let i = 1; i < cells; i += 1) {
        const t = i / cells;
        ctx.beginPath();
        ctx.moveTo(p2.x + (p1.x - p2.x) * t, p2.y + (p1.y - p2.y) * t);
        ctx.lineTo(p2.x + (p1.x - p2.x) * t + sx * 0.16, p2.y + (p1.y - p2.y) * t + sy * 0.16);
        ctx.stroke();
      }
      ctx.restore();
      if (incidence > 0.85) glow(ctx, L.pivot.x, L.pivot.y - L.panelLen * 0.3, L.panelLen * 0.7, "255, 216, 92", 0.22);

      ctx.fillStyle = "rgba(6, 12, 26, 0.82)";
      roundRect(ctx, 12, 12, 158, 32, 10);
      ctx.fill();
      ctx.fillStyle = "#ffd85c";
      ctx.font = "800 14px AidenKR, system-ui, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText(out.watts.toFixed(2) + " W · " + Math.round(incidence * 100) + "%", 26, 34);

      setWidth(meterEl, out.level);
      if (state.cloud > 70) {
        setText(readEl, "구름이 햇빛을 가리고 있어요. 발전량 " + out.watts.toFixed(2) + "W");
      } else if (incidence > 0.97) {
        setText(readEl, "해와 패널이 딱 맞았어요! " + out.watts.toFixed(2) + "W 만들고 있어요.");
      } else {
        setText(
          readEl,
          "발전량 " + out.watts.toFixed(2) + "W · 해를 정면으로 보려면 " + out.optimalTilt.toFixed(0) + "°쯤이 좋아요."
        );
      }
      if (out.level >= 0.999) markFound("solar");
    }

    function update() {
      if (state.auto) {
        const optimal = Math.round(P.clamp(90 - state.altitude, 0, 90));
        if (optimal !== state.tilt) {
          state.tilt = optimal;
          const tiltInput = $("#tilt-range");
          if (tiltInput) tiltInput.value = String(state.tilt);
          setText($("#tilt-output"), state.tilt + "°");
        }
      }
    }

    function sync() {
      compute();
      draw();
    }

    const sunRange = $("#sun-range");
    if (sunRange) {
      sunRange.addEventListener("input", () => {
        state.altitude = Number(sunRange.value);
        setText($("#sun-output"), state.altitude + "°");
        sync();
      });
    }
    const tiltRange = $("#tilt-range");
    if (tiltRange) {
      tiltRange.addEventListener("input", () => {
        state.tilt = Number(tiltRange.value);
        setText($("#tilt-output"), state.tilt + "°");
        if (state.auto) {
          state.auto = false;
          const auto = $("#tilt-auto");
          if (auto) auto.setAttribute("aria-pressed", "false");
        }
        sync();
      });
    }
    const cloudRange = $("#cloud-range");
    if (cloudRange) {
      cloudRange.addEventListener("input", () => {
        state.cloud = Number(cloudRange.value);
        setText($("#cloud-output"), state.cloud + "%");
        sync();
      });
    }
    const autoButton = $("#tilt-auto");
    if (autoButton) {
      autoButton.addEventListener("click", () => {
        state.auto = !state.auto;
        autoButton.setAttribute("aria-pressed", state.auto ? "true" : "false");
        audio.tick();
      });
    }

    return addStation({
      id: "solar",
      stage: stage,
      update: update,
      draw: draw,
      sync: sync,
      watts: () => (state.output ? state.output.watts : 0),
    });
  }

  /* ────────────────────────────────────────────────────────────────
     06 바람 발전
     ──────────────────────────────────────────────────────────────── */

  function createWind() {
    const canvas = $("#canvas-wind");
    if (!canvas) return null;
    const stage = createStage(canvas);
    const state = { windSpeed: 4, bladeLength: 0.3, blades: 3, spin: 0, output: null, streaks: [] };
    const readEl = $("#read-wind");
    const meterEl = $("#meter-wind");

    function compute() {
      state.output = P.windPower({ windSpeed: state.windSpeed, bladeLength: state.bladeLength, bladeCount: state.blades });
      state.rpm = P.turbineRpm({ windSpeed: state.windSpeed, bladeLength: state.bladeLength, bladeCount: state.blades });
      return state.output;
    }

    function layout() {
      const w = stage.width;
      const h = stage.height;
      const horizon = h * 0.84;
      const towerH = Math.min(h * 0.5, w * 0.32);
      const hub = { x: w * 0.4, y: horizon - towerH };
      const t = (state.bladeLength - 0.15) / 0.35;
      return {
        w: w,
        h: h,
        horizon: horizon,
        hub: hub,
        towerH: towerH,
        blade: P.clamp(towerH * 0.34 + towerH * 0.52 * P.clamp(t, 0, 1), towerH * 0.3, towerH * 0.9),
        house: { x: w * 0.8, y: horizon, size: Math.min(w * 0.13, h * 0.2) },
      };
    }

    function update(dt) {
      const rpm = state.rpm;
      const visualRpm = Math.min(rpm, 260) * (prefersReducedMotion ? 0.35 : 1);
      state.spin += (visualRpm * TAU * dt) / 60;
      const L = layout();
      const want = Math.round(P.clamp(state.windSpeed * 2.2, 0, 18));
      if (!prefersReducedMotion) {
        while (state.streaks.length < want) {
          state.streaks.push({
            x: -Math.random() * L.w * 0.6,
            y: L.h * 0.1 + Math.random() * (L.horizon - L.h * 0.12),
            len: 30 + Math.random() * 70,
            speed: 0.6 + Math.random() * 0.8,
          });
        }
        while (state.streaks.length > want) state.streaks.pop();
      }
      state.streaks.forEach((streak) => {
        streak.x += (40 + state.windSpeed * 46) * streak.speed * dt;
        if (streak.x > L.w + 80) {
          streak.x = -80 - Math.random() * 120;
          streak.y = L.h * 0.1 + Math.random() * (L.horizon - L.h * 0.12);
        }
      });

      const out = state.output || compute();
      setWidth(meterEl, out.level);
      if (state.windSpeed < 0.5) {
        setText(readEl, "바람이 없으면 날개가 돌지 않아요. 바람을 불어 주세요.");
      } else if (out.level >= 1) {
        setText(readEl, "발전량 " + out.watts.toFixed(2) + "W · 최대로 만들고 있어요!");
      } else {
        setText(readEl, "발전량 " + out.watts.toFixed(2) + "W · " + Math.round(state.rpm) + "rpm으로 돌고 있어요.");
      }
      if (out.level >= 1) markFound("wind");
    }

    function draw() {
      const ctx = stage.ctx;
      const L = layout();
      const out = state.output || compute();
      ctx.clearRect(0, 0, L.w, L.h);
      const sky = ctx.createLinearGradient(0, 0, 0, L.horizon);
      sky.addColorStop(0, "#123055");
      sky.addColorStop(1, "#2b5f86");
      ctx.fillStyle = sky;
      ctx.fillRect(0, 0, L.w, L.horizon);

      // 바람 줄무늬
      ctx.lineCap = "round";
      state.streaks.forEach((streak) => {
        ctx.strokeStyle = "rgba(200, 230, 255, " + 0.1 + (state.windSpeed / 10) * 0.3 + ")";
        ctx.lineWidth = 2.4;
        ctx.beginPath();
        ctx.moveTo(streak.x, streak.y);
        ctx.quadraticCurveTo(streak.x + streak.len * 0.5, streak.y - 6, streak.x + streak.len, streak.y);
        ctx.stroke();
      });

      // 땅
      ctx.fillStyle = "#16351f";
      ctx.fillRect(0, L.horizon, L.w, L.h - L.horizon);
      ctx.strokeStyle = "rgba(180, 220, 255, 0.25)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(0, L.horizon);
      ctx.lineTo(L.w, L.horizon);
      ctx.stroke();

      // 집
      const hs = L.house.size;
      ctx.fillStyle = "#26405f";
      ctx.fillRect(L.house.x - hs / 2, L.house.y - hs * 0.7, hs, hs * 0.7);
      ctx.fillStyle = "#1a2c42";
      ctx.beginPath();
      ctx.moveTo(L.house.x - hs * 0.62, L.house.y - hs * 0.68);
      ctx.lineTo(L.house.x, L.house.y - hs * 1.12);
      ctx.lineTo(L.house.x + hs * 0.62, L.house.y - hs * 0.68);
      ctx.closePath();
      ctx.fill();
      const winLevel = out.level;
      glow(ctx, L.house.x, L.house.y - hs * 0.4, hs * 0.8, "255, 216, 92", winLevel * 0.55);
      ctx.fillStyle = winLevel > 0.05 ? "rgba(255, 226, 140, " + (0.4 + 0.6 * winLevel) + ")" : "rgba(90, 110, 140, 0.6)";
      roundRect(ctx, L.house.x - hs * 0.18, L.house.y - hs * 0.56, hs * 0.36, hs * 0.32, 3);
      ctx.fill();

      // 전선
      drawWire(
        ctx,
        [[L.hub.x, L.hub.y + L.towerH * 0.9], [L.house.x - hs * 0.4, L.house.y - hs * 0.2]],
        2.5,
        winLevel > 0.05 ? "rgba(255, 216, 120, 0.9)" : "rgba(180, 200, 235, 0.5)"
      );

      // 타워
      ctx.fillStyle = "#dbe6ff";
      ctx.beginPath();
      ctx.moveTo(L.hub.x - 7, L.hub.y);
      ctx.lineTo(L.hub.x + 7, L.hub.y);
      ctx.lineTo(L.hub.x + L.towerH * 0.1, L.horizon);
      ctx.lineTo(L.hub.x - L.towerH * 0.1, L.horizon);
      ctx.closePath();
      ctx.fill();

      // 날개
      ctx.save();
      ctx.translate(L.hub.x, L.hub.y);
      for (let i = 0; i < state.blades; i += 1) {
        ctx.save();
        ctx.rotate(state.spin + (i / state.blades) * TAU);
        const grad = ctx.createLinearGradient(0, 0, L.blade, 0);
        grad.addColorStop(0, "rgba(240, 248, 255, 0.95)");
        grad.addColorStop(1, "rgba(160, 190, 230, 0.75)");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.moveTo(0, -4);
        ctx.quadraticCurveTo(L.blade * 0.6, -L.blade * 0.16, L.blade, -1.5);
        ctx.lineTo(L.blade, 2.5);
        ctx.quadraticCurveTo(L.blade * 0.6, L.blade * 0.1, 0, 5);
        ctx.closePath();
        ctx.fill();
        ctx.restore();
      }
      ctx.fillStyle = "#f4f8ff";
      ctx.beginPath();
      ctx.arc(0, 0, 8, 0, TAU);
      ctx.fill();
      ctx.restore();
      glow(ctx, L.hub.x, L.hub.y, L.blade * 1.2, "92, 242, 194", out.level * 0.16);

      ctx.fillStyle = "rgba(6, 12, 26, 0.82)";
      roundRect(ctx, 12, 12, 168, 32, 10);
      ctx.fill();
      ctx.fillStyle = "#5cf2c2";
      ctx.font = "800 14px AidenKR, system-ui, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText(out.watts.toFixed(2) + " W · " + Math.round(state.rpm) + " rpm", 26, 34);
    }

    function sync() {
      compute();
      draw();
    }

    const windRange = $("#wind-range");
    if (windRange) {
      windRange.addEventListener("input", () => {
        state.windSpeed = Number(windRange.value);
        setText($("#wind-output"), state.windSpeed.toFixed(1) + " m/s");
        sync();
      });
    }
    const bladeRange = $("#blade-range");
    if (bladeRange) {
      bladeRange.addEventListener("input", () => {
        state.bladeLength = Number(bladeRange.value);
        setText($("#blade-output"), Math.round(state.bladeLength * 100) + " cm");
        sync();
      });
    }
    $$("[data-blades]").forEach((button) => {
      button.addEventListener("click", () => {
        state.blades = Number(button.getAttribute("data-blades"));
        $$("[data-blades]").forEach((other) => {
          other.setAttribute("aria-pressed", other === button ? "true" : "false");
        });
        audio.tick();
        sync();
      });
    });

    return addStation({
      id: "wind",
      stage: stage,
      update: update,
      draw: draw,
      sync: sync,
      watts: () => (state.output ? state.output.watts : 0),
    });
  }

  /* ────────────────────────────────────────────────────────────────
     07 물 발전
     ──────────────────────────────────────────────────────────────── */

  function createHydro() {
    const canvas = $("#canvas-hydro");
    if (!canvas) return null;
    const stage = createStage(canvas);
    const state = { head: 1, flow: 2, spin: 0, output: null, drops: [], splashes: [] };
    const readEl = $("#read-hydro");
    const meterEl = $("#meter-hydro");

    function compute() {
      state.output = P.hydroPower({ headMeters: state.head, flowLitersPerSec: state.flow });
      state.rpm = P.wheelRpm({ headMeters: state.head, flowLitersPerSec: state.flow });
      return state.output;
    }

    function layout() {
      const w = stage.width;
      const h = stage.height;
      const headT = P.clamp((state.head - 0.2) / 2.3, 0, 1);
      const surfY = h * 0.4 - headT * h * 0.32;
      const wheel = { x: w * 0.66, y: h * 0.78, r: Math.min(w * 0.1, h * 0.17) };
      return {
        w: w,
        h: h,
        surfY: surfY,
        tank: { x0: w * 0.04, x1: w * 0.3, bottom: surfY + h * 0.16 },
        nozzle: { x: w * 0.53, y: h * 0.56 },
        wheel: wheel,
        tailY: h * 0.94,
      };
    }

    function update(dt) {
      const visualRpm = Math.min(state.rpm, 300) * (prefersReducedMotion ? 0.35 : 1);
      state.spin += (visualRpm * TAU * dt) / 60;
      const L = layout();
      const flowScale = state.flow / 5;

      if (!prefersReducedMotion) {
        const spawn = dt * (10 + flowScale * 46);
        state.spawnCarry = (state.spawnCarry || 0) + spawn;
        while (state.spawnCarry >= 1) {
          state.spawnCarry -= 1;
          state.drops.push({
            x: L.nozzle.x + (Math.random() - 0.5) * (4 + flowScale * 16),
            y: L.nozzle.y,
            vy: 120 + Math.random() * 60,
            r: 1.6 + Math.random() * 2.2 * (0.5 + flowScale),
          });
        }
      }
      for (let i = state.drops.length - 1; i >= 0; i -= 1) {
        const drop = state.drops[i];
        drop.vy += 900 * dt;
        drop.y += drop.vy * dt;
        const hitX = L.wheel.x - L.wheel.r * 0.5;
        const hitY = L.wheel.y - L.wheel.r * 0.7;
        if (drop.y >= hitY && drop.y < L.tailY) {
          if (Math.abs(drop.x - hitX) < L.wheel.r * 0.6) {
            if (state.splashes.length < 90) {
              state.splashes.push({
                x: drop.x,
                y: hitY,
                vx: (Math.random() - 0.2) * 120,
                vy: -60 - Math.random() * 120,
                life: 0.6,
              });
            }
            state.drops.splice(i, 1);
            continue;
          }
        }
        if (drop.y > L.tailY) state.drops.splice(i, 1);
      }
      for (let i = state.splashes.length - 1; i >= 0; i -= 1) {
        const splash = state.splashes[i];
        splash.life -= dt;
        splash.x += splash.vx * dt;
        splash.y += splash.vy * dt;
        splash.vy += 700 * dt;
        if (splash.life <= 0) state.splashes.splice(i, 1);
      }

      const out = state.output || compute();
      setWidth(meterEl, out.level);
      if (out.level >= 1) {
        setText(readEl, "발전량 " + out.watts.toFixed(2) + "W · 물바퀴가 힘차게 돌아요!");
      } else {
        setText(
          readEl,
          "발전량 " + out.watts.toFixed(2) + "W · " + Math.round(state.rpm) + "rpm · 물 높이나 양을 늘려 볼까요?"
        );
      }
      if (out.level >= 1) markFound("hydro");
    }

    function draw() {
      const ctx = stage.ctx;
      const L = layout();
      const out = state.output || compute();
      ctx.clearRect(0, 0, L.w, L.h);
      const sky = ctx.createLinearGradient(0, 0, 0, L.h);
      sky.addColorStop(0, "#0d2340");
      sky.addColorStop(1, "#071527");
      ctx.fillStyle = sky;
      ctx.fillRect(0, 0, L.w, L.h);

      // 저수지 물
      const waterGrad = ctx.createLinearGradient(0, L.surfY, 0, L.tank.bottom);
      waterGrad.addColorStop(0, "rgba(90, 190, 255, 0.85)");
      waterGrad.addColorStop(1, "rgba(30, 96, 170, 0.9)");
      ctx.fillStyle = waterGrad;
      ctx.fillRect(L.tank.x0, L.surfY, L.tank.x1 - L.tank.x0, L.tank.bottom - L.surfY);
      ctx.strokeStyle = "rgba(200, 240, 255, 0.8)";
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.moveTo(L.tank.x0, L.surfY);
      for (let x = L.tank.x0; x <= L.tank.x1; x += 10) {
        ctx.lineTo(x, L.surfY + Math.sin(x / 14 + Date.now() / 420) * 2.4);
      }
      ctx.stroke();

      // 댐 벽
      ctx.fillStyle = "#3d4a63";
      ctx.fillRect(L.tank.x1, L.surfY - 8, Math.max(10, L.w * 0.03), L.tank.bottom - L.surfY + 8);
      ctx.strokeStyle = "rgba(200, 220, 255, 0.35)";
      ctx.lineWidth = 1.5;
      ctx.strokeRect(L.tank.x1, L.surfY - 8, Math.max(10, L.w * 0.03), L.tank.bottom - L.surfY + 8);

      // 낙차 표시
      ctx.strokeStyle = "rgba(215, 255, 0, 0.5)";
      ctx.setLineDash([5, 5]);
      ctx.lineWidth = 1.6;
      ctx.beginPath();
      ctx.moveTo(L.tank.x1 + L.w * 0.055, L.surfY);
      ctx.lineTo(L.tank.x1 + L.w * 0.055, L.nozzle.y);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = "rgba(215, 255, 0, 0.85)";
      ctx.font = "800 12px AidenKR, system-ui, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText(Math.round(state.head * 100) + "cm", L.tank.x1 + L.w * 0.065, (L.surfY + L.nozzle.y) / 2);

      // 수로(펜스톡)
      const pipe = [
        [L.tank.x1 + L.w * 0.02, L.tank.bottom - L.h * 0.04],
        [L.w * 0.42, L.tank.bottom - L.h * 0.04],
        [L.w * 0.42, L.nozzle.y],
        [L.nozzle.x, L.nozzle.y],
      ];
      drawWire(ctx, pipe, 14, "rgba(90, 108, 138, 0.9)");
      drawWire(ctx, pipe, 8, "rgba(140, 165, 205, 0.85)");

      // 떨어지는 물
      ctx.fillStyle = "rgba(150, 220, 255, 0.9)";
      state.drops.forEach((drop) => {
        ctx.beginPath();
        ctx.ellipse(drop.x, drop.y, drop.r, drop.r * 2.1, 0, 0, TAU);
        ctx.fill();
      });
      state.splashes.forEach((splash) => {
        ctx.fillStyle = "rgba(220, 245, 255, " + P.clamp(splash.life, 0, 1) * 0.8 + ")";
        ctx.beginPath();
        ctx.arc(splash.x, splash.y, 2, 0, TAU);
        ctx.fill();
      });

      // 물바퀴
      ctx.save();
      ctx.translate(L.wheel.x, L.wheel.y);
      ctx.strokeStyle = "rgba(190, 214, 250, 0.85)";
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.arc(0, 0, L.wheel.r, 0, TAU);
      ctx.stroke();
      ctx.strokeStyle = "rgba(140, 170, 220, 0.6)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(0, 0, L.wheel.r * 0.62, 0, TAU);
      ctx.stroke();
      ctx.rotate(state.spin);
      for (let i = 0; i < 8; i += 1) {
        ctx.save();
        ctx.rotate((i / 8) * TAU);
        ctx.fillStyle = i % 2 === 0 ? "rgba(215, 235, 255, 0.95)" : "rgba(120, 160, 215, 0.9)";
        roundRect(ctx, -4, -L.wheel.r, 8, L.wheel.r * 0.42, 3);
        ctx.fill();
        ctx.restore();
      }
      ctx.fillStyle = "#f4f8ff";
      ctx.beginPath();
      ctx.arc(0, 0, 7, 0, TAU);
      ctx.fill();
      ctx.restore();
      glow(ctx, L.wheel.x, L.wheel.y, L.wheel.r * 2, "107, 198, 255", out.level * 0.2);

      // 발전기 상자
      const gen = { x: L.w * 0.86, y: L.h * 0.74, w: Math.min(L.w * 0.14, 76), h: Math.min(L.h * 0.16, 52) };
      ctx.fillStyle = "#22304c";
      roundRect(ctx, gen.x - gen.w / 2, gen.y - gen.h / 2, gen.w, gen.h, 8);
      ctx.fill();
      ctx.strokeStyle = "rgba(140, 177, 255, 0.4)";
      ctx.lineWidth = 2;
      ctx.stroke();
      drawWire(
        ctx,
        [[L.wheel.x + L.wheel.r * 0.3, L.wheel.y], [gen.x - gen.w / 2, gen.y]],
        4,
        out.level > 0.05 ? "rgba(255, 216, 120, 0.9)" : "rgba(180, 200, 235, 0.55)"
      );
      glow(ctx, gen.x, gen.y, gen.w, "255, 216, 92", out.level * 0.5);

      // 아래 물
      ctx.fillStyle = "rgba(40, 120, 190, 0.75)";
      ctx.fillRect(0, L.tailY, L.w, L.h - L.tailY);

      ctx.fillStyle = "rgba(6, 12, 26, 0.85)";
      roundRect(ctx, 12, 12, 158, 32, 10);
      ctx.fill();
      ctx.fillStyle = "#6bc6ff";
      ctx.font = "800 14px AidenKR, system-ui, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText(out.watts.toFixed(2) + " W · " + Math.round(state.rpm) + " rpm", 26, 34);
    }

    function sync() {
      compute();
      draw();
    }

    const headRange = $("#head-range");
    if (headRange) {
      headRange.addEventListener("input", () => {
        state.head = Number(headRange.value);
        setText($("#head-output"), Math.round(state.head * 100) + " cm");
        sync();
      });
    }
    const flowRange = $("#flow-range");
    if (flowRange) {
      flowRange.addEventListener("input", () => {
        state.flow = Number(flowRange.value);
        setText($("#flow-output"), state.flow.toFixed(1) + " L/s");
        sync();
      });
    }

    return addStation({
      id: "hydro",
      stage: stage,
      update: update,
      draw: draw,
      sync: sync,
      watts: () => (state.output ? state.output.watts : 0),
    });
  }

  /* ── 대시보드 · 도움말 · 소리 ─────────────────────────────────── */

  const dashboard = { watts: 0, timer: 0 };
  const statWatts = $("#stat-watts");
  const statEnergy = $("#stat-energy");
  const outroEnergy = $("#outro-energy");

  function renderDashboard() {
    setText(statWatts, dashboard.watts.toFixed(1));
    const joules = Math.round(progress.energy);
    setText(statEnergy, String(joules));
    setText(outroEnergy, String(joules));
  }

  function setupHelp() {
    const dialog = $("#help-dialog");
    const backdrop = $("#help-backdrop");
    const openButton = $("#help-button");
    const closeButton = $("#help-close");
    const okButton = $("#help-ok");
    let lastFocus = null;

    function open() {
      if (!dialog || !backdrop) return;
      lastFocus = doc.activeElement;
      dialog.hidden = false;
      backdrop.hidden = false;
      const focusTarget = okButton || closeButton;
      if (focusTarget) focusTarget.focus();
    }

    function close() {
      if (!dialog || !backdrop) return;
      dialog.hidden = true;
      backdrop.hidden = true;
      if (lastFocus && typeof lastFocus.focus === "function") lastFocus.focus();
    }

    if (openButton) openButton.addEventListener("click", open);
    if (closeButton) closeButton.addEventListener("click", close);
    if (okButton) okButton.addEventListener("click", close);
    if (backdrop) backdrop.addEventListener("click", close);
    doc.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && dialog && !dialog.hidden) close();
    });
  }

  function setupSound() {
    const button = $("#sound-button");
    if (!button) return;

    function render() {
      button.setAttribute("aria-pressed", audio.enabled ? "true" : "false");
      button.setAttribute("aria-label", audio.enabled ? "효과음 끄기" : "효과음 켜기");
      button.textContent = audio.enabled ? "🔊 소리" : "🔇 소리";
    }

    button.addEventListener("click", () => {
      audio.enabled = !audio.enabled;
      progress.sound = audio.enabled;
      saveProgress(true);
      render();
      if (audio.enabled) {
        audio.ensure();
        audio.pop();
      }
    });
    render();
  }

  function setupReset() {
    const button = $("#reset-all");
    if (!button) return;
    button.addEventListener("click", () => {
      progress.found = {};
      progress.energy = 0;
      saveProgress(true);
      STATION_IDS.forEach((id) => {
        const stamp = doc.getElementById("stamp-" + id);
        if (stamp) stamp.hidden = true;
        const card = doc.getElementById("station-" + id);
        if (card) card.classList.remove("is-found", "just-found");
        const goal = doc.getElementById("goal-" + id);
        if (goal) goal.classList.remove("is-done");
      });
      renderFound();
      renderDashboard();
      stations.forEach((station) => {
        if (typeof station.reset === "function") station.reset();
      });
      audio.tone({ freq: 380, toFreq: 180, dur: 0.22, type: "triangle", gain: 0.06 });
    });
  }

  function setupWhyToggles() {
    $$(".why-toggle").forEach((button) => {
      button.addEventListener("click", () => {
        const target = doc.getElementById(button.getAttribute("aria-controls"));
        const expanded = button.getAttribute("aria-expanded") === "true";
        button.setAttribute("aria-expanded", expanded ? "false" : "true");
        if (target) target.hidden = expanded;
      });
    });
  }

  /* ── 실행 ──────────────────────────────────────────────────────── */

  function boot() {
    buildDots();
    STATION_IDS.forEach((id) => {
      if (progress.found[id]) {
        const stamp = doc.getElementById("stamp-" + id);
        if (stamp) stamp.hidden = false;
        const card = doc.getElementById("station-" + id);
        if (card) card.classList.add("is-found");
        const goal = doc.getElementById("goal-" + id);
        if (goal) goal.classList.add("is-done");
      }
    });
    renderFound();
    renderDashboard();

    const created = [
      createCircuit(),
      createStatic(),
      createFruit(),
      createGenerator(),
      createSolar(),
      createWind(),
      createHydro(),
    ];
    created.forEach((station) => {
      if (station && typeof station.sync === "function") station.sync();
    });

    setupHelp();
    setupSound();
    setupReset();
    setupWhyToggles();

    if (window.IntersectionObserver) {
      const observer = new window.IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            stations.forEach((station) => {
              if (station.stage.canvas === entry.target) station.stage.visible = entry.isIntersecting;
            });
          });
        },
        { rootMargin: "140px 0px" }
      );
      stations.forEach((station) => observer.observe(station.stage.canvas));
    }

    let last = 0;
    function frame(now) {
      const dt = last ? Math.min((now - last) / 1000, 0.05) : 0.016;
      last = now;
      let total = 0;
      for (let i = 0; i < stations.length; i += 1) {
        const station = stations[i];
        if (!station.stage.visible) continue;
        station.update(dt);
        station.draw();
        total += station.watts();
      }
      dashboard.watts += (total - dashboard.watts) * Math.min(1, dt * 6);
      if (total > 0) {
        progress.energy += P.energyJoules(total, dt);
        saveProgress();
      }
      dashboard.timer += dt;
      if (dashboard.timer > 0.18) {
        dashboard.timer = 0;
        renderDashboard();
      }
      window.requestAnimationFrame(frame);
    }
    window.requestAnimationFrame(frame);
  }

  if (doc.readyState === "loading") {
    doc.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
