/**
 * Typed canonical travel runtime contract for Ocean Rescue (WP-31C).
 *
 * This module is the strictly typed canonical implementation of the legacy
 * `src/travel.js`. The legacy file is retained byte-for-byte as the operational
 * rollback authority referenced only by `build-manifest.legacy.json`; the
 * canonical graph no longer executes it.
 *
 * The module preserves the legacy observable runtime contract exactly: the
 * frozen `Bounds`, `AutoForwardSpeed === 120`, `TapSpeed === 360`, initial
 * snapshot, `start`/`stop` reset scope, the 50ms delta cap, the forward
 * multiplier default (1) and 0..1 range with exact rejection, distance
 * accumulation, tap-target movement and clear timing, drag pointer ownership,
 * begin-drag `dragPrevStageY` clamping, move-drag previous-stage ordering,
 * clamp ordering, inactive-state rejection, exact invalid-input return values,
 * frozen snapshot/API/Bounds, and the temporary `window.OceanRescue.Travel`
 * compatibility ABI consumed by `src/app.js`.
 */

export interface TravelBounds {
  readonly minY: number;
  readonly maxY: number;
  readonly startY: number;
}

export interface TravelSnapshot {
  readonly active: boolean;
  readonly distance: number;
  readonly y: number;
  readonly tapTargetY: number | null;
  readonly dragging: boolean;
  readonly pointerId: number | null;
}

export interface TravelApi {
  readonly Bounds: TravelBounds;
  readonly AutoForwardSpeed: number;
  readonly TapSpeed: number;
  readonly getSnapshot: () => TravelSnapshot;
  readonly start: () => boolean;
  readonly stop: () => boolean;
  readonly step: (deltaMs: unknown, forwardSpeedMultiplier?: unknown) => boolean;
  readonly beginDrag: (pointerId: unknown, stageY: unknown) => boolean;
  readonly moveDrag: (pointerId: unknown, stageY: unknown) => boolean;
  readonly endDrag: (pointerId: unknown) => boolean;
  readonly tapTo: (stageY: unknown) => boolean;
}

/** Temporary global compatibility slot until WP-32 shares boundary types. */
interface OceanRescueGlobalNamespace {
  OceanRescue?: {
    Travel?: unknown;
  };
}

function freeze<T>(value: T): Readonly<T> {
  return Object.freeze(value);
}

export const Bounds: TravelBounds = freeze({
  minY: 120,
  maxY: 600,
  startY: 360,
});

const AutoForwardSpeed = 120;
const TapSpeed = 360;

interface MutableTravelState {
  active: boolean;
  distance: number;
  y: number;
  tapTargetY: number | null;
  dragging: boolean;
  pointerId: number | null;
}

const state: MutableTravelState = {
  active: false,
  distance: 0,
  y: Bounds.startY,
  tapTargetY: null,
  dragging: false,
  pointerId: null,
};

let dragPointerId: number | null = null;
let dragPrevStageY = 0;

function clampY(value: number): number {
  if (value < Bounds.minY) {
    return Bounds.minY;
  }
  if (value > Bounds.maxY) {
    return Bounds.maxY;
  }
  return value;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && isFinite(value);
}

function getSnapshot(): TravelSnapshot {
  return freeze({
    active: state.active,
    distance: state.distance,
    y: state.y,
    tapTargetY: state.tapTargetY,
    dragging: state.dragging,
    pointerId: state.pointerId,
  });
}

function start(): boolean {
  state.active = true;
  state.distance = 0;
  state.y = Bounds.startY;
  state.tapTargetY = null;
  state.dragging = false;
  state.pointerId = null;
  dragPointerId = null;
  dragPrevStageY = 0;
  return true;
}

function stop(): boolean {
  if (!state.active) {
    return false;
  }
  state.active = false;
  state.tapTargetY = null;
  state.dragging = false;
  state.pointerId = null;
  dragPointerId = null;
  return true;
}

function step(deltaMs: unknown, forwardSpeedMultiplier?: unknown): boolean {
  if (!state.active) {
    return false;
  }
  if (!isFiniteNumber(deltaMs) || deltaMs <= 0) {
    return false;
  }
  let multiplier = 1;
  if (forwardSpeedMultiplier !== undefined) {
    if (!isFiniteNumber(forwardSpeedMultiplier)) {
      return false;
    }
    if (forwardSpeedMultiplier < 0 || forwardSpeedMultiplier > 1) {
      return false;
    }
    multiplier = forwardSpeedMultiplier;
  }
  let applied = deltaMs;
  if (applied > 50) {
    applied = 50;
  }
  state.distance += AutoForwardSpeed * multiplier * (applied / 1000);
  if (state.tapTargetY !== null) {
    const target = state.tapTargetY;
    const movement = TapSpeed * (applied / 1000);
    if (state.y < target) {
      state.y += movement;
      if (state.y >= target) {
        state.y = target;
        state.tapTargetY = null;
      }
    } else if (state.y > target) {
      state.y -= movement;
      if (state.y <= target) {
        state.y = target;
        state.tapTargetY = null;
      }
    } else {
      state.tapTargetY = null;
    }
  }
  return true;
}

function beginDrag(pointerId: unknown, stageY: unknown): boolean {
  if (!state.active) {
    return false;
  }
  if (!isFiniteNumber(pointerId)) {
    return false;
  }
  if (!isFiniteNumber(stageY)) {
    return false;
  }
  if (state.dragging || dragPointerId !== null) {
    return false;
  }
  state.tapTargetY = null;
  dragPointerId = pointerId;
  dragPrevStageY = clampY(stageY);
  state.dragging = true;
  state.pointerId = pointerId;
  return true;
}

function moveDrag(pointerId: unknown, stageY: unknown): boolean {
  if (!state.active) {
    return false;
  }
  if (pointerId !== dragPointerId) {
    return false;
  }
  if (!isFiniteNumber(stageY)) {
    return false;
  }
  state.y = clampY(state.y + (stageY - dragPrevStageY));
  dragPrevStageY = stageY;
  return true;
}

function endDrag(pointerId: unknown): boolean {
  if (pointerId !== dragPointerId) {
    return false;
  }
  if (!state.dragging) {
    return false;
  }
  state.dragging = false;
  state.pointerId = null;
  dragPointerId = null;
  return true;
}

function tapTo(stageY: unknown): boolean {
  if (!state.active) {
    return false;
  }
  if (state.dragging) {
    return false;
  }
  if (!isFiniteNumber(stageY)) {
    return false;
  }
  const target = clampY(stageY);
  if (target === state.y) {
    state.tapTargetY = null;
    return true;
  }
  state.tapTargetY = target;
  return true;
}

const Travel: TravelApi = freeze({
  Bounds: Bounds,
  AutoForwardSpeed: AutoForwardSpeed,
  TapSpeed: TapSpeed,
  getSnapshot: getSnapshot,
  start: start,
  stop: stop,
  step: step,
  beginDrag: beginDrag,
  moveDrag: moveDrag,
  endDrag: endDrag,
  tapTo: tapTo,
});

const win = window as OceanRescueGlobalNamespace;
const root = win.OceanRescue || {};
win.OceanRescue = root;
root.Travel = Travel;

export { Travel as OceanRescueTravel };
export { Travel };
