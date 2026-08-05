/**
 * Typed controller boundary for the sea-turtle lifecycle characterization
 * baseline (WP-33E-0).
 *
 * This package locks the runtime ABI and controller contract without moving
 * pointer handling, feedback timing, completion routing, or shared rescue
 * listener ownership out of `src/app.js`.
 */

import type {
  PointerIntent,
  SeaTurtleApi,
  SeaTurtleSceneApi,
  SeaTurtleSnapshot,
} from "../contracts/runtime-abi";

export interface SeaTurtleSessionRef {
  readonly rescueSequenceId: number;
  readonly missionId: "sea-turtle";
}

/** Host methods that remain implemented by app.js during WP-33E-0. */
export interface SeaTurtleLifecycleHostApi {
  renderSeaTurtleFrame(intent?: PointerIntent): void;
  updateSeaTurtleRootMarkers(): void;
  syncSeaTurtleScene(intent?: PointerIntent): boolean;
}

/** App methods exposed by the characterization-only controller boundary. */
export interface SeaTurtleLifecycleAppApi extends SeaTurtleLifecycleHostApi {
  isSeaTurtleActive(): boolean;
  getSeaTurtleSnapshot(): SeaTurtleSnapshot | null;
  startSeaTurtleInteraction(): boolean;
}

interface ControllerDependencies {
  readonly SeaTurtle: SeaTurtleApi | null;
  readonly SeaTurtleScene: SeaTurtleSceneApi | null;
}

function resolveDependencies(): ControllerDependencies {
  const namespace = window.OceanRescue;
  return {
    SeaTurtle: namespace?.SeaTurtle ?? null,
    SeaTurtleScene: namespace?.SeaTurtleScene ?? null,
  };
}

export function installSeaTurtleLifecycleController(
  host: SeaTurtleLifecycleHostApi,
): SeaTurtleLifecycleAppApi {
  const { SeaTurtle, SeaTurtleScene } = resolveDependencies();

  function isSeaTurtleActive(): boolean {
    return SeaTurtle?.getSnapshot().active ?? false;
  }

  function getSeaTurtleSnapshot(): SeaTurtleSnapshot | null {
    return SeaTurtle?.getSnapshot() ?? null;
  }

  function startSeaTurtleInteraction(): boolean {
    if (!SeaTurtle) {
      return false;
    }

    const State = window.OceanRescue?.State;
    if (!State || State.getSnapshot().phase !== State.Phases.RESCUE_ACTIVE) {
      return false;
    }

    if (!SeaTurtle.start()) {
      return false;
    }

    if (SeaTurtleScene?.isMounted()) {
      SeaTurtleScene.activate();
    }

    host.renderSeaTurtleFrame();
    host.updateSeaTurtleRootMarkers();
    return true;
  }

  const controller: SeaTurtleLifecycleAppApi = Object.assign(host, {
    isSeaTurtleActive,
    getSeaTurtleSnapshot,
    startSeaTurtleInteraction,
  });
  return controller;
}
