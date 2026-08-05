/**
 * Typed controller boundary for sea-turtle lifecycle (WP-33E-A).
 *
 * This scaffold defines a typed host boundary for sea-turtle lifecycle
 * without owning pointer handling, feedback timing, or progression logic.
 *
 * This controller does NOT:
 * - Own pointer state or handle pointer events directly
 * - Manage feedback timers or success/failure progression
 * - Call state transition APIs or mission completion APIs
 * - Reference other rescue entities
 * - Register DOM event listeners
 *
 * Host bridge methods (implemented by legacy app.js):
 * - renderSeaTurtleFrame(intent?)
 * - updateSeaTurtleRootMarkers()
 * - syncSeaTurtleScene(intent?)
 */

import type { SeaTurtleApi, SeaTurtleSceneApi } from "../contracts/runtime-abi";

/**
 * Host interface required by the sea-turtle lifecycle controller scaffold.
 */
export interface SeaTurtleLifecycleHostApi {
  /** Render a single sea-turtle frame, optionally with a pointer intent. */
  renderSeaTurtleFrame(intent?: unknown): void;

  /** Update data-* markers on #ocean-rescue-root from SeaTurtle snapshot. */
  updateSeaTurtleRootMarkers(): void;

  /** Sync the authored sea-turtle scene with snapshot + intent. */
  syncSeaTurtleScene(intent?: unknown): void;
}

/**
 * App interface exposed by the sea-turtle lifecycle controller scaffold.
 */
export interface SeaTurtleLifecycleAppApi extends SeaTurtleLifecycleHostApi {
  /** Check if sea-turtle rescue is currently active. */
  isSeaTurtleActive(): boolean;

  /** Get the current sea-turtle state snapshot. */
  getSeaTurtleSnapshot(): unknown | null;

  /** Validate preconditions and start the sea-turtle rescue interaction. */
  startSeaTurtleInteraction(): boolean;
}

export function installSeaTurtleLifecycleController(
  host: SeaTurtleLifecycleHostApi,
): SeaTurtleLifecycleAppApi {
  const namespace = window.OceanRescue;
  const SeaTurtle = (namespace?.SeaTurtle as SeaTurtleApi | undefined) ?? null;
  const SeaTurtleScene = (namespace?.SeaTurtleScene as SeaTurtleSceneApi | undefined) ?? null;

  function isSeaTurtleActive(): boolean {
    if (!SeaTurtle) {
      return false;
    }
    const snapshot = SeaTurtle.getSnapshot();
    return snapshot?.active ?? false;
  }

  function getSeaTurtleSnapshot(): unknown | null {
    if (!SeaTurtle) {
      return null;
    }
    return SeaTurtle.getSnapshot();
  }

  function startSeaTurtleInteraction(): boolean {
    if (!SeaTurtle) {
      return false;
    }

    const namespace = window.OceanRescue;
    const State = namespace?.State;
    if (!State) {
      return false;
    }

    const snapshot = State.getSnapshot();
    if (snapshot?.phase !== "RESCUE_ACTIVE") {
      return false;
    }

    const started = SeaTurtle.start();
    if (!started) {
      return false;
    }

    if (SeaTurtleScene && SeaTurtleScene.isMounted()) {
      SeaTurtleScene.activate();
    }

    host.renderSeaTurtleFrame();
    host.updateSeaTurtleRootMarkers();

    return true;
  }

  const controller = host as unknown as SeaTurtleLifecycleAppApi;
  controller.isSeaTurtleActive = isSeaTurtleActive;
  controller.getSeaTurtleSnapshot = getSeaTurtleSnapshot;
  controller.startSeaTurtleInteraction = startSeaTurtleInteraction;

  return controller;
}
