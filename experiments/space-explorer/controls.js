// 태양계 3D 탐험대 — 화면 UI 바인딩
// 리본, 시간 조작, 천체 정보 카드, 이름표, 로딩/가이드/오류 화면을 담당한다.

import * as THREE from "three";

import { MOONS, PLANETS, SPEED_PRESETS, SUN, TEXTURE_BASE } from "./data.js";
import { currentDateLabel, speedBadgeText } from "./state.js";

const MOON_LABEL_DISTANCE = 26;

function el(id) {
  return document.getElementById(id);
}

function textureUrl(name) {
  return `${TEXTURE_BASE}${name}`;
}

export function createUiController({ state, actions }) {
  const elements = {
    dateDisplay: el("date-display"),
    speedBadge: el("speed-badge"),
    planetRibbon: el("planet-ribbon"),
    speedControls: el("speed-controls"),
    pauseBtn: el("pause-btn"),
    todayBtn: el("today-btn"),
    prevDayBtn: el("prev-day-btn"),
    nextDayBtn: el("next-day-btn"),
    orbitsBtn: el("orbits-btn"),
    labelsBtn: el("labels-btn"),
    effectsBtn: el("effects-btn"),
    helpBtn: el("help-btn"),
    helpModal: el("help-modal"),
    helpClose: el("help-close"),
    overviewBtn: el("overview-btn"),
    detailCard: el("detail-card"),
    detailClose: el("detail-close"),
    detailPreview: el("detail-preview"),
    detailPreviewImage: el("detail-preview-image"),
    detailPreviewIcon: el("detail-preview-icon"),
    detailName: el("detail-name"),
    detailEn: el("detail-en"),
    detailCategory: el("detail-category"),
    detailHighlight: el("detail-highlight"),
    detailOverview: el("detail-overview"),
    detailStats: el("detail-stats"),
    detailFacts: el("detail-facts"),
    labelsLayer: el("labels-layer"),
    loadingScreen: el("loading-screen"),
    loadingBar: el("loading-bar"),
    loadingPercent: el("loading-percent"),
    loadingLabel: el("loading-label"),
    fatalError: el("fatal-error"),
    fatalErrorMessage: el("fatal-error-message"),
    reloadBtn: el("reload-btn"),
    liveStatus: el("live-status"),
  };

  const labels = new Map();
  let lastDateText = "";
  let lastSpeedText = "";
  let selectedBodyId = null;

  // ── 리본 ────────────────────────────────────────────────
  function buildRibbon() {
    const items = [SUN, ...PLANETS];
    elements.planetRibbon.innerHTML = items
      .map(
        (body) =>
          `<button type="button" data-body="${body.id}" aria-label="${body.name} 보기">` +
          `<span class="ribbon-dot" style="color:${body.color};background:${body.color}" aria-hidden="true"></span>` +
          `<span aria-hidden="true">${body.icon}</span>${body.name}</button>`,
      )
      .join("");
    elements.planetRibbon.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-body]");
      if (button) actions.focusBody(button.dataset.body);
    });
  }

  function buildSpeedControls() {
    elements.speedControls.innerHTML = SPEED_PRESETS.map(
      (preset) =>
        `<button type="button" class="speed-btn" data-speed="${preset.id}" aria-pressed="false">${preset.label}</button>`,
    ).join("");
    elements.speedControls.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-speed]");
      if (button) actions.setSpeed(button.dataset.speed);
    });
  }

  // ── 시간 UI ─────────────────────────────────────────────
  function syncTime() {
    const dateText = `📅 ${currentDateLabel(state)}`;
    if (dateText !== lastDateText) {
      elements.dateDisplay.textContent = dateText;
      lastDateText = dateText;
    }

    const speedText = speedBadgeText(state);
    if (speedText !== lastSpeedText) {
      elements.speedBadge.textContent = speedText;
      elements.pauseBtn.textContent = state.paused ? "▶ 계속" : "⏸ 일시정지";
      elements.pauseBtn.setAttribute("aria-pressed", String(state.paused));
      lastSpeedText = speedText;
    }

    for (const button of elements.speedControls.querySelectorAll(".speed-btn")) {
      const active = !state.paused && button.dataset.speed === state.speedId;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    }
  }

  // ── 정보 카드 ───────────────────────────────────────────
  function showDetail(body) {
    if (!body) return;
    selectedBodyId = body.id;

    elements.detailName.textContent = body.name;
    elements.detailEn.textContent = body.en ?? "";
    elements.detailCategory.textContent = body.category ?? "";
    elements.detailHighlight.textContent = `🌟 ${body.highlight ?? body.overview ?? ""}`;
    elements.detailOverview.textContent = body.overview ?? "";

    const stats = body.stats ?? [];
    elements.detailStats.innerHTML = stats
      .map(([label, value]) => `<div><span>${label}</span><strong>${value}</strong></div>`)
      .join("");

    const facts = body.facts ?? [];
    elements.detailFacts.innerHTML = facts.length
      ? facts.map((fact) => `<li>${fact}</li>`).join("")
      : `<li>${body.name}을(를) 가까이에서 관찰해 보세요.</li>`;

    const textureName = body.texture ?? (body.id === "earth" ? "earth_day.jpg" : null);
    if (textureName) {
      elements.detailPreviewImage.src = textureUrl(textureName);
      elements.detailPreviewImage.alt = `${body.name} 표면`;
      elements.detailPreview.classList.add("detail-preview--texture");
    } else {
      elements.detailPreviewImage.removeAttribute("src");
      elements.detailPreview.classList.remove("detail-preview--texture");
      elements.detailPreviewIcon.textContent = body.icon ?? "🪐";
    }

    elements.detailCard.classList.remove("hidden");
    elements.overviewBtn.classList.remove("hidden");
    document.querySelectorAll("#planet-ribbon button").forEach((button) => {
      const selected = button.dataset.body === body.id;
      button.classList.toggle("selected", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
    announce(`${body.name} 정보를 열었어요.`);
  }

  function hideDetail() {
    selectedBodyId = null;
    elements.detailCard.classList.add("hidden");
    elements.overviewBtn.classList.add("hidden");
    document.querySelectorAll("#planet-ribbon button").forEach((button) => {
      button.classList.remove("selected");
      button.setAttribute("aria-pressed", "false");
    });
  }

  // ── 이름표 ──────────────────────────────────────────────
  function buildLabels() {
    const bodies = [SUN, ...PLANETS, ...MOONS];
    elements.labelsLayer.innerHTML = "";
    labels.clear();
    for (const body of bodies) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `space-label${body.parent ? " space-label--moon" : ""}`;
      button.dataset.body = body.id;
      button.innerHTML =
        `<span class="space-label__dot" style="color:${body.color}" aria-hidden="true"></span>` +
        `<strong>${body.name}</strong>`;
      button.addEventListener("click", () => actions.focusBody(body.id));
      elements.labelsLayer.appendChild(button);
      labels.set(body.id, button);
    }
  }

  const projectedVector = new THREE.Vector3();

  function updateLabels(scene) {
    if (!state.showLabels) {
      if (elements.labelsLayer.classList.contains("hidden") === false) {
        elements.labelsLayer.classList.add("hidden");
      }
      return;
    }
    elements.labelsLayer.classList.remove("hidden");

    const width = scene.renderer.domElement.clientWidth;
    const height = scene.renderer.domElement.clientHeight;
    const camera = scene.camera;

    // 하나의 이름표가 다른 천체를 가리지 않도록 가까운 천체부터 배치한다.
    const ordered = [...labels.entries()].sort((a, b) => {
      const aBody = scene.getBody(a[0]);
      const bBody = scene.getBody(b[0]);
      const aDistance = aBody ? camera.position.distanceTo(aBody.position) : Infinity;
      const bDistance = bBody ? camera.position.distanceTo(bBody.position) : Infinity;
      return aDistance - bDistance;
    });

    let stack = 0;
    for (const [id, button] of ordered) {
      const body = scene.getBody(id);
      if (!body) continue;

      const data = body.data;
      const distanceToCamera = camera.position.distanceTo(body.position);
      const isMoon = Boolean(data.parent);
      let visible = true;

      if (isMoon) {
        const parent = scene.getBody(data.parent);
        const parentDistance = parent ? camera.position.distanceTo(parent.position) : Infinity;
        visible = parentDistance < MOON_LABEL_DISTANCE || state.followId === id || state.followId === data.parent;
      }

      projectedVector.copy(body.position).project(camera);

      if (
        !visible ||
        projectedVector.z < -1 ||
        projectedVector.z > 1 ||
        Math.abs(projectedVector.x) > 1.12 ||
        Math.abs(projectedVector.y) > 1.12
      ) {
        button.style.opacity = "0";
        button.style.pointerEvents = "none";
        continue;
      }

      const x = (projectedVector.x * 0.5 + 0.5) * width;
      const y = (-projectedVector.y * 0.5 + 0.5) * height;
      const scale = Math.max(0.62, Math.min(1, 1.22 - distanceToCamera / 900));
      const dimmed = selectedBodyId && selectedBodyId !== id;
      button.style.zIndex = String(40 - Math.min(30, stack));
      stack += 1;
      button.style.transform = `translate3d(${x}px, ${y}px, 0) translate(-50%, -50%) scale(${scale})`;
      button.style.opacity = dimmed ? "0.38" : isMoon ? "0.85" : "1";
      button.style.pointerEvents = "auto";
      button.classList.toggle("selected", selectedBodyId === id);
    }
  }

  // ── 토글/모달 ───────────────────────────────────────────
  function syncToggles() {
    elements.orbitsBtn.setAttribute("aria-pressed", String(state.showOrbits));
    elements.labelsBtn.setAttribute("aria-pressed", String(state.showLabels));
    elements.effectsBtn.setAttribute("aria-pressed", String(state.effects));
  }

  function openHelp() {
    elements.helpModal.classList.remove("hidden");
    elements.helpClose.focus({ preventScroll: true });
  }

  function closeHelp() {
    elements.helpModal.classList.add("hidden");
    elements.helpBtn.focus({ preventScroll: true });
  }

  function announce(message) {
    elements.liveStatus.textContent = message;
  }

  // ── 로딩/오류 ───────────────────────────────────────────
  function setLoadingProgress(loaded, total, name) {
    const ratio = total > 0 ? Math.min(1, loaded / total) : 0;
    elements.loadingBar.style.width = `${Math.round(ratio * 100)}%`;
    elements.loadingPercent.textContent = `${Math.round(ratio * 100)}%`;
    if (name) {
      elements.loadingLabel.innerHTML = `행성 텍스처 불러오는 중 · <strong>${Math.round(ratio * 100)}%</strong>`;
    }
  }

  function finishLoading() {
    elements.loadingBar.style.width = "100%";
    elements.loadingPercent.textContent = "100%";
    elements.loadingScreen.classList.add("loading-screen--done");
    window.setTimeout(() => {
      elements.loadingScreen.classList.add("hidden");
    }, 560);
  }

  function showFatalError(message) {
    elements.loadingScreen.classList.add("hidden");
    elements.fatalErrorMessage.textContent = message;
    elements.fatalError.classList.remove("hidden");
  }

  // ── 이벤트 ──────────────────────────────────────────────
  function bind() {
    elements.pauseBtn.addEventListener("click", () => actions.togglePause());
    elements.todayBtn.addEventListener("click", () => actions.goToday());
    elements.prevDayBtn.addEventListener("click", () => actions.stepDays(-10));
    elements.nextDayBtn.addEventListener("click", () => actions.stepDays(10));
    elements.orbitsBtn.addEventListener("click", () => actions.toggleOrbits());
    elements.labelsBtn.addEventListener("click", () => actions.toggleLabels());
    elements.effectsBtn.addEventListener("click", () => actions.toggleEffects());
    elements.helpBtn.addEventListener("click", openHelp);
    elements.helpClose.addEventListener("click", closeHelp);
    elements.helpModal.addEventListener("click", (event) => {
      if (event.target === elements.helpModal) closeHelp();
    });
    elements.overviewBtn.addEventListener("click", () => actions.overview());
    elements.detailClose.addEventListener("click", () => actions.overview());
    elements.reloadBtn.addEventListener("click", () => window.location.reload());
  }

  buildRibbon();
  buildSpeedControls();
  buildLabels();
  bind();
  syncTime();
  syncToggles();

  return {
    labels,
    syncTime,
    syncToggles,
    showDetail,
    hideDetail,
    updateLabels,
    setLoadingProgress,
    finishLoading,
    showFatalError,
    announce,
    openHelp,
    closeHelp,
    isHelpOpen: () => !elements.helpModal.classList.contains("hidden"),
  };
}
