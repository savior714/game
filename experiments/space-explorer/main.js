// 태양계 3D 탐험대 — 앱 엔트리
// 상태, 카메라 연출, UI, 상호작용, 렌더 루프를 연결한다.

import * as THREE from "three";

import { createUiController } from "./controls.js";
import { DEFAULT_SPEED_ID } from "./data.js";
import { attachSceneInteractions } from "./interactions.js";
import { createSolarScene } from "./renderer.js";
import { createAppState } from "./state.js";
import {
  advanceSimulation,
  clearFollow,
  resetToToday,
  setFollow,
  setSpeed,
  stepDays as advanceDays,
  toggleEffects,
  toggleLabels,
  toggleOrbits,
  togglePaused,
} from "./state.js";
import { speedLabel } from "./simulation.js";

const MAX_ORBIT_RADIUS = 172;
const OVERVIEW_ELEVATION = 0.62;

const state = createAppState();
const canvas = document.getElementById("space-canvas");
const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ?? false;

let scene = null;
let ui = null;
let interactions = null;
let cameraTween = null;
let uiTimer = 0;
let performanceWindow = { elapsed: 0, frames: 0 };
let lowPerformanceWindows = 0;
let lastFrameTime = performance.now();
let ready = false;
let viewShiftKey = "";

function syncViewShift() {
  if (!scene) return;
  const narrow = window.innerWidth <= 700;
  const wide = window.innerWidth > 980;
  const focused = Boolean(state.followId);
  // 모바일: 하단 시트 위로 장면을 올린다. 와이드: 우측 정보 카드 왼쪽으로 장면을 민다.
  const shift = !focused
    ? { x: 0, y: 0 }
    : narrow
      ? { x: 0, y: 0.12 }
      : wide
        ? { x: 0.085, y: 0.015 }
        : { x: 0, y: 0.02 };
  const key = `${shift.x.toFixed(3)}:${shift.y.toFixed(3)}`;
  if (key === viewShiftKey) return;
  viewShiftKey = key;
  scene.setViewShift(shift);
}

const followPrevious = new THREE.Vector3();
const scratchOffset = new THREE.Vector3();
const poleScratch = new THREE.Vector3();
const sunFacingScratch = new THREE.Vector3();
const tangentScratch = new THREE.Vector3();
const scratchTarget = new THREE.Vector3();

function easeInOutCubic(t) {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

function overviewPosition() {
  if (!scene) return new THREE.Vector3(0, 150, 250);
  const camera = scene.camera;
  const tanVertical = Math.tan((camera.fov * Math.PI) / 360);
  const horizontal = Math.max(0.5, Math.min(2.6, camera.aspect || 1));
  // 원형 궤도가 화면 가로 폭의 88% 안에 들어오도록 거리를 정한다.
  const fitted = MAX_ORBIT_RADIUS / (0.44 * tanVertical * horizontal);
  // 세로 화면에서는 너무 멀어지지 않도록 상한을 둔다.
  const distance = Math.max(230, Math.min(560, fitted));
  return new THREE.Vector3(0, distance * OVERVIEW_ELEVATION * 0.62, distance * 0.79);
}

const actions = {
  focusBody(id) {
    if (!scene || !ready) return;
    const body = scene.getBody(id);
    if (!body) return;

    setFollow(state, id);
    scene.setOrbitHighlight(id);

    const baseDistance = body.data.focusDistance ?? Math.max(body.radius * 4.2, 6);
    // 작은 화면에서는 천체가 화면을 가득 채우지 않도록 조금 더 멀리서 본다.
    const viewportScale = scene.camera.aspect < 1 ? 1.35 : scene.camera.aspect < 1.4 ? 1.08 : 1;
    const distance = baseDistance * viewportScale;

    // 자전축을 기준으로 적도면에 가까운 시점을 만든다.
    // 고리가 있는 행성은 거의 적도면에서 봐야 고리가 얇은 띠로 보인다.
    const pole = scene.getBodyPole(id, poleScratch);
    const sunDirection = body.position.lengthSq() > 1e-6
      ? sunFacingScratch.copy(body.position).multiplyScalar(-1).normalize()
      : sunFacingScratch.set(0, 1, 0);
    // 적도면 안에서 태양 방향에 수직인 축. 카메라를 그 축으로 비껴 둔다.
    const tangent = tangentScratch.crossVectors(sunDirection, pole);
    if (tangent.lengthSq() < 1e-3) tangent.set(0, 0, 1);
    tangent.normalize();
    // 0.55 : 0.8 비율이면 태양 쪽에서 55°쯤 비껴선 위치가 되어
    // 낮/밤 경계가 화면에 남는다.
    const poleWeight = body.data.ringTexture ? 0.16 : 0.26;
    scratchOffset
      .copy(sunDirection)
      .multiplyScalar(0.92)
      .addScaledVector(tangent, 1.32)
      .addScaledVector(pole, poleWeight)
      .normalize()
      .multiplyScalar(distance);

    cameraTween = {
      kind: "focus",
      fromOffset: scene.camera.position.clone().sub(body.position),
      toOffset: scratchOffset.clone(),
      elapsed: 0,
      duration: reducedMotion ? 0.02 : 1.05,
    };
    followPrevious.copy(body.position);
    ui.showDetail(body.data);
    syncViewShift();
  },

  overview() {
    if (!scene) return;
    clearFollow(state);
    scene.controls.minDistance = 3.2;
    scene.setOrbitHighlight(null);
    ui.hideDetail();
    cameraTween = {
      kind: "overview",
      fromPosition: scene.camera.position.clone(),
      fromTarget: scene.controls.target.clone(),
      toPosition: overviewPosition(),
      toTarget: new THREE.Vector3(0, 0, 0),
      elapsed: 0,
      duration: reducedMotion ? 0.02 : 1.15,
    };
    syncViewShift();
    ui.announce("태양계 전체 보기로 돌아왔어요.");
  },

  togglePause() {
    togglePaused(state);
    ui.syncTime();
    ui.announce(state.paused ? "시간을 멈췄어요." : "시간이 다시 흘러요.");
  },

  setSpeed(presetId) {
    setSpeed(state, presetId);
    ui.syncTime();
    ui.announce(`시간 속도를 ${speedLabel(state.daysPerSecond)}로 바꿨어요.`);
  },

  stepDays(delta) {
    advanceDays(state, delta);
    ui.syncTime();
    ui.announce(delta > 0 ? "10일 뒤로 이동했어요." : "10일 전으로 이동했어요.");
  },

  goToday() {
    resetToToday(state);
    ui.syncTime();
    ui.announce("오늘 날짜로 돌아왔어요.");
  },

  toggleOrbits() {
    toggleOrbits(state);
    scene?.setOrbitsVisible(state.showOrbits);
    ui.syncToggles();
    ui.announce(state.showOrbits ? "궤도선을 켰어요." : "궤도선을 껐어요.");
  },

  toggleLabels() {
    toggleLabels(state);
    ui.syncToggles();
    ui.announce(state.showLabels ? "이름표를 켰어요." : "이름표를 껐어요.");
  },

  toggleEffects() {
    toggleEffects(state);
    scene?.setBloomEnabled(state.effects);
    ui.syncToggles();
    ui.announce(state.effects ? "빛 번짐 효과를 켰어요." : "빛 번짐 효과를 껐어요.");
  },
};

function updateCamera(dt) {
  if (!scene) return;
  const camera = scene.camera;
  const controls = scene.controls;

  if (cameraTween) {
    cameraTween.elapsed += dt;
    const progress = Math.min(1, cameraTween.elapsed / Math.max(0.01, cameraTween.duration));
    const eased = easeInOutCubic(progress);

    if (cameraTween.kind === "focus") {
      const body = scene.getBody(state.followId);
      if (!body) {
        cameraTween = null;
        return;
      }
      const offset = cameraTween.fromOffset.clone().lerp(cameraTween.toOffset, eased);
      camera.position.copy(body.position).add(offset);
      controls.target.copy(body.position);
      followPrevious.copy(body.position);
    } else {
      camera.position.lerpVectors(cameraTween.fromPosition, cameraTween.toPosition, eased);
      controls.target.lerpVectors(cameraTween.fromTarget, cameraTween.toTarget, eased);
    }

    if (progress >= 1) cameraTween = null;
    return;
  }

  if (state.followId) {
    const body = scene.getBody(state.followId);
    if (!body) return;
    scratchTarget.copy(body.position).sub(followPrevious);
    camera.position.add(scratchTarget);
    controls.target.copy(body.position);
    followPrevious.copy(body.position);
    // 추적 중에는 천체 표면까지 충분히 다가갈 수 있게 최소 거리를 천체 크기에 맞춘다.
    const minDistance = body.data.parent ? body.radius * 2.1 : Math.max(2.4, body.radius * 1.35);
    if (controls.minDistance !== minDistance) controls.minDistance = minDistance;
  }
}

function monitorPerformance(dt) {
  if (!state.effects || reducedMotion) return;
  performanceWindow.elapsed += dt;
  performanceWindow.frames += 1;
  if (performanceWindow.elapsed < 1.4) return;

  const fps = performanceWindow.frames / performanceWindow.elapsed;
  performanceWindow = { elapsed: 0, frames: 0 };

  if (fps < 27) {
    lowPerformanceWindows += 1;
  } else {
    lowPerformanceWindows = 0;
  }

  if (lowPerformanceWindows >= 3) {
    actions.toggleEffects();
    scene?.setPixelRatioCap(1.25);
    ui.announce("화면이 부드러워지도록 빛 번짐 효과를 자동으로 줄였어요.");
    lowPerformanceWindows = 0;
  }
}

function frame(now) {
  const dt = Math.min(0.1, Math.max(0, (now - lastFrameTime) / 1000));
  lastFrameTime = now;

  if (scene && !document.hidden) {
    advanceSimulation(state, dt);
    scene.update(state.days, state.paused ? 0 : dt);
    updateCamera(dt);
    scene.controls.update();
    scene.render();
    ui.updateLabels(scene);
    monitorPerformance(dt);

    uiTimer += dt;
    if (uiTimer >= 0.12) {
      ui.syncTime();
      uiTimer = 0;
    }
  }

  requestAnimationFrame(frame);
}

function bindKeyboard() {
  document.addEventListener("keydown", (event) => {
    const target = event.target;
    const tag = target?.tagName;
    const typing = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target?.isContentEditable;
    if (typing) return;

    if (event.key === "Escape") {
      if (ui?.isHelpOpen()) {
        ui.closeHelp();
      } else if (state.followId) {
        actions.overview();
      }
      return;
    }

    if (tag === "BUTTON" || tag === "A") return;

    if (event.code === "Space") {
      event.preventDefault();
      actions.togglePause();
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      actions.stepDays(1);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      actions.stepDays(-1);
    }
  });
}

function bindResize() {
  const onResize = () => {
    if (!scene) return;
    scene.resize();
    viewShiftKey = "";
    syncViewShift();
    if (!state.followId && !cameraTween) {
      scene.camera.position.copy(overviewPosition());
      scene.controls.target.set(0, 0, 0);
      scene.controls.update();
    }
  };
  window.addEventListener("resize", onResize, { passive: true });
  window.addEventListener("orientationchange", onResize, { passive: true });
  if (typeof ResizeObserver === "function") {
    const observer = new ResizeObserver(onResize);
    observer.observe(document.getElementById("space-app"));
  }
  return onResize;
}

async function boot() {
  ui = createUiController({ state, actions });

  if (!canvas) {
    ui.showFatalError("화면을 준비하지 못했어요. 새로고침을 눌러 주세요.");
    return;
  }

  const loadingStartedAt = performance.now();

  try {
    scene = await createSolarScene({
      canvas,
      onTextureProgress: (loaded, total, name) => ui.setLoadingProgress(loaded, total, name),
    });
  } catch (error) {
    console.error("[space-explorer] scene init failed", error);
    ui.showFatalError(
      "3D 우주선을 띄우지 못했어요. WebGL을 지원하는 최신 브라우저인지 확인한 뒤 새로고침을 눌러 주세요.",
    );
    return;
  }

  scene.update(state.days, 0);
  scene.setOrbitsVisible(state.showOrbits);
  scene.setBloomEnabled(state.effects);

  scene.camera.position.copy(overviewPosition());
  scene.controls.target.set(0, 0, 0);
  scene.controls.update();

  const minimumLoadingTime = 520;
  const elapsed = performance.now() - loadingStartedAt;
  if (elapsed < minimumLoadingTime) {
    await new Promise((resolve) => window.setTimeout(resolve, minimumLoadingTime - elapsed));
  }

  ui.finishLoading();
  ui.syncTime();
  ui.syncToggles();
  bindResize();
  bindKeyboard();

  ui.announce("태양계 탐험 준비 완료! 행성을 눌러 가까이에서 관찰해 보세요.");

  interactions = attachSceneInteractions({
    canvas,
    camera: scene.camera,
    controls: scene.controls,
    raycast: (event) => scene.raycastFromEvent(event),
    onPick: (id) => actions.focusBody(id),
    onHover: (id) => scene.setOrbitHighlight(id ?? state.followId),
    onUserInteract: () => {
      cameraTween = null;
    },
  });

  scene.controls.addEventListener("start", () => {
    cameraTween = null;
  });

  document.addEventListener("visibilitychange", () => {
    lastFrameTime = performance.now();
  });

  ready = true;
  lastFrameTime = performance.now();
  requestAnimationFrame(frame);

  // 디버그/확장용 최소 노출 (테스트와 개발자 도구에서 확인)
  window.__spaceExplorer = {
    state,
    scene,
    ui,
    actions,
    speedPreset: DEFAULT_SPEED_ID,
    detach: () => interactions?.detach(),
  };
}

boot();
