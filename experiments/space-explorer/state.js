// 태양계 3D 탐험대 — 시뮬레이션 상태
// DOM/THREE에 의존하지 않으므로 Node 테스트에서 그대로 검증할 수 있다.

import { DEFAULT_SPEED_ID, SPEED_PRESETS } from "./data.js";
import { daysSinceJ2000, formatSimDate, speedLabel } from "./simulation.js";

export const MAX_FRAME_STEP_SECONDS = 0.1;

export function findSpeedPreset(id) {
  return SPEED_PRESETS.find((preset) => preset.id === id) || SPEED_PRESETS.find((preset) => preset.id === DEFAULT_SPEED_ID);
}

/**
 * @param {{ now?: Date }} options
 */
export function createAppState({ now = new Date() } = {}) {
  const todayDays = daysSinceJ2000(now.toISOString());
  const preset = findSpeedPreset(DEFAULT_SPEED_ID);

  return {
    days: todayDays,
    todayDays,
    speedId: preset.id,
    daysPerSecond: preset.daysPerSecond,
    paused: false,
    followId: null,
    showOrbits: true,
    showLabels: true,
    effects: true,
    lastSpeedId: preset.id,
  };
}

export function setSpeed(state, presetId) {
  const preset = findSpeedPreset(presetId);
  if (!preset) return state;
  state.speedId = preset.id;
  state.daysPerSecond = preset.daysPerSecond;
  state.paused = false;
  if (preset.daysPerSecond > 0) state.lastSpeedId = preset.id;
  return state;
}

export function togglePaused(state) {
  state.paused = !state.paused;
  return state;
}

export function stepDays(state, deltaDays) {
  if (!Number.isFinite(deltaDays)) return state;
  state.days += deltaDays;
  return state;
}

export function resetToToday(state) {
  state.days = state.todayDays;
  return state;
}

/** 프레임 경과 시간만큼 시뮬레이션 날짜를 진행한다. */
export function advanceSimulation(state, dtSeconds) {
  const dt = Math.min(MAX_FRAME_STEP_SECONDS, Math.max(0, dtSeconds));
  if (state.paused || !Number.isFinite(state.daysPerSecond)) return state.days;
  state.days += dt * state.daysPerSecond;
  return state.days;
}

export function currentDateLabel(state) {
  return formatSimDate(state.days);
}

export function speedBadgeText(state) {
  if (state.paused) return "일시정지";
  return speedLabel(state.daysPerSecond);
}

export function setFollow(state, bodyId) {
  state.followId = bodyId;
  return state;
}

export function clearFollow(state) {
  state.followId = null;
  return state;
}

export function toggleOrbits(state) {
  state.showOrbits = !state.showOrbits;
  return state.showOrbits;
}

export function toggleLabels(state) {
  state.showLabels = !state.showLabels;
  return state.showLabels;
}

export function toggleEffects(state) {
  state.effects = !state.effects;
  return state.effects;
}
