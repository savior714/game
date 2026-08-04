/**
 * Typed canonical core state machine for Ocean Rescue (WP-31C).
 *
 * This module is the strictly typed canonical implementation of the legacy
 * `src/state.js`. The legacy file is retained byte-for-byte as the operational
 * rollback authority referenced only by `build-manifest.legacy.json`; the
 * canonical graph no longer executes it.
 *
 * The module preserves the legacy observable runtime contract exactly: the
 * frozen `Phases` map, the frozen transition allow-list, initial
 * `BOOT`/`ready === false` state, transition locking, monotonically increasing
 * transition IDs, frozen `{ id, from, to }` tokens, stale/forged token
 * rejection, same-phase and invalid-phase rejection, the frozen snapshot
 * shape, `forcePhase` lock/token cleanup, the frozen public API shape, and the
 * temporary `window.OceanRescue.State` compatibility ABI consumed by
 * `src/app.js`.
 */

export type Phase =
  | "BOOT"
  | "PROFILE_CHOICE"
  | "MISSION_SELECT"
  | "GUP_SELECT"
  | "LAUNCH"
  | "TRAVEL"
  | "RESCUE_SITE_TRANSITION"
  | "RESCUE_TUTORIAL"
  | "RESCUE_ACTIVE"
  | "RESCUE_SUCCESS"
  | "MISSION_COMPLETE";

export interface PhaseMap {
  readonly BOOT: "BOOT";
  readonly PROFILE_CHOICE: "PROFILE_CHOICE";
  readonly MISSION_SELECT: "MISSION_SELECT";
  readonly GUP_SELECT: "GUP_SELECT";
  readonly LAUNCH: "LAUNCH";
  readonly TRAVEL: "TRAVEL";
  readonly RESCUE_SITE_TRANSITION: "RESCUE_SITE_TRANSITION";
  readonly RESCUE_TUTORIAL: "RESCUE_TUTORIAL";
  readonly RESCUE_ACTIVE: "RESCUE_ACTIVE";
  readonly RESCUE_SUCCESS: "RESCUE_SUCCESS";
  readonly MISSION_COMPLETE: "MISSION_COMPLETE";
}

export type TransitionMap = Readonly<{
  [K in Phase]: readonly Phase[];
}>;

export interface TransitionToken {
  readonly id: number;
  readonly from: Phase;
  readonly to: Phase;
}

export interface StateSnapshot {
  readonly phase: Phase;
  readonly ready: boolean;
  readonly transitionLocked: boolean;
  readonly pendingPhase: Phase | null;
}

export interface StateApi {
  readonly Phases: PhaseMap;
  readonly getSnapshot: () => StateSnapshot;
  readonly markReady: () => boolean;
  readonly canTransition: (nextPhase: unknown) => boolean;
  readonly beginTransition: (nextPhase: unknown) => TransitionToken | null;
  readonly completeTransition: (token: unknown) => boolean;
  readonly forcePhase: (phase: unknown) => boolean;
}

/** Temporary global compatibility slot until WP-32 shares boundary types. */
interface OceanRescueGlobalNamespace {
  OceanRescue?: {
    State?: unknown;
  };
}

function freeze<T>(value: T): Readonly<T> {
  return Object.freeze(value);
}

export const Phases: PhaseMap = freeze({
  BOOT: "BOOT",
  PROFILE_CHOICE: "PROFILE_CHOICE",
  MISSION_SELECT: "MISSION_SELECT",
  GUP_SELECT: "GUP_SELECT",
  LAUNCH: "LAUNCH",
  TRAVEL: "TRAVEL",
  RESCUE_SITE_TRANSITION: "RESCUE_SITE_TRANSITION",
  RESCUE_TUTORIAL: "RESCUE_TUTORIAL",
  RESCUE_ACTIVE: "RESCUE_ACTIVE",
  RESCUE_SUCCESS: "RESCUE_SUCCESS",
  MISSION_COMPLETE: "MISSION_COMPLETE",
});

const transitions: TransitionMap = freeze({
  BOOT: freeze([Phases.PROFILE_CHOICE, Phases.MISSION_SELECT]),
  PROFILE_CHOICE: freeze([Phases.MISSION_SELECT]),
  MISSION_SELECT: freeze([Phases.GUP_SELECT]),
  GUP_SELECT: freeze([Phases.MISSION_SELECT, Phases.LAUNCH]),
  LAUNCH: freeze([Phases.TRAVEL]),
  TRAVEL: freeze([Phases.RESCUE_SITE_TRANSITION]),
  RESCUE_SITE_TRANSITION: freeze([Phases.RESCUE_TUTORIAL]),
  RESCUE_TUTORIAL: freeze([Phases.RESCUE_ACTIVE]),
  RESCUE_ACTIVE: freeze([Phases.RESCUE_SUCCESS]),
  RESCUE_SUCCESS: freeze([Phases.MISSION_COMPLETE]),
  MISSION_COMPLETE: freeze([Phases.MISSION_SELECT, Phases.LAUNCH]),
});

interface MutableState {
  phase: Phase;
  ready: boolean;
  transitionLocked: boolean;
  pendingPhase: Phase | null;
  activeToken: TransitionToken | null;
  transitionId: number;
}

const state: MutableState = {
  phase: Phases.BOOT,
  ready: false,
  transitionLocked: false,
  pendingPhase: null,
  activeToken: null,
  transitionId: 0,
};

function isPhase(value: unknown): value is Phase {
  if (typeof value !== "string") {
    return false;
  }
  return Object.prototype.hasOwnProperty.call(Phases, value);
}

function canTransition(nextPhase: unknown): nextPhase is Phase {
  if (typeof nextPhase !== "string") {
    return false;
  }
  if (!isPhase(nextPhase)) {
    return false;
  }
  if (state.transitionLocked) {
    return false;
  }
  if (nextPhase === state.phase) {
    return false;
  }
  const allowed = transitions[state.phase];
  if (!allowed) {
    return false;
  }
  return allowed.indexOf(nextPhase) !== -1;
}

function beginTransition(nextPhase: unknown): TransitionToken | null {
  if (!canTransition(nextPhase)) {
    return null;
  }
  state.transitionId += 1;
  const token = freeze<TransitionToken>({
    id: state.transitionId,
    from: state.phase,
    to: nextPhase,
  });
  state.transitionLocked = true;
  state.pendingPhase = nextPhase;
  state.activeToken = token;
  return token;
}

function completeTransition(token: unknown): boolean {
  if (!state.transitionLocked) {
    return false;
  }
  if (!token || typeof token !== "object") {
    return false;
  }
  const active = state.activeToken;
  if (!active) {
    return false;
  }
  const candidate = token as Partial<TransitionToken>;
  if (candidate.id !== active.id) {
    return false;
  }
  if (candidate.from !== active.from) {
    return false;
  }
  if (candidate.to !== active.to) {
    return false;
  }
  state.phase = candidate.to;
  state.pendingPhase = null;
  state.transitionLocked = false;
  state.activeToken = null;
  return true;
}

function markReady(): boolean {
  if (state.ready) {
    return false;
  }
  state.ready = true;
  return true;
}

function getSnapshot(): StateSnapshot {
  return freeze({
    phase: state.phase,
    ready: state.ready,
    transitionLocked: state.transitionLocked,
    pendingPhase: state.pendingPhase,
  });
}

function forcePhase(phase: unknown): boolean {
  if (!isPhase(phase)) {
    return false;
  }
  state.transitionLocked = false;
  state.pendingPhase = null;
  state.activeToken = null;
  state.phase = phase;
  return true;
}

const State: StateApi = freeze({
  Phases: Phases,
  getSnapshot: getSnapshot,
  markReady: markReady,
  canTransition: canTransition,
  beginTransition: beginTransition,
  completeTransition: completeTransition,
  forcePhase: forcePhase,
});

const win = window as OceanRescueGlobalNamespace;
const root = win.OceanRescue || {};
win.OceanRescue = root;
root.State = State;

export { State as OceanRescueState };
export { State };
