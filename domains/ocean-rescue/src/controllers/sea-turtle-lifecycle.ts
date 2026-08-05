/**
 * Typed controller boundary for the sea-turtle lifecycle characterization
 * baseline (WP-33E-0).
 *
 * This package locks the runtime ABI and controller contract without moving
 * pointer handling, feedback timing, completion routing, or shared rescue
 * listener ownership out of `src/app.js`.
 */

import type {
  PointerInputApi,
  PointerIntent,
  SeaTurtleApi,
  SeaTurtleSceneApi,
  SeaTurtleSnapshot,
  OceanRescueNamespace,
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
  renderLegacySeaTurtleFrame(
    snapshot: SeaTurtleSnapshot,
    intent?: PointerIntent,
  ): void;
}

/** App methods exposed by the characterization-only controller boundary. */
export interface SeaTurtleLifecycleAppApi extends SeaTurtleLifecycleHostApi {
  isSeaTurtleActive(): boolean;
  getSeaTurtleSnapshot(): SeaTurtleSnapshot | null;
  startSeaTurtleInteraction(): boolean;
  syncSeaTurtleProjection(intent?: PointerIntent): boolean;
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

    syncSeaTurtleProjection();
    return true;
  }

  function syncSeaTurtleProjection(intent?: PointerIntent): boolean {
    if (!SeaTurtle) {
      return false;
    }

    const snapshot = SeaTurtle.getSnapshot();
    const root = document.getElementById("ocean-rescue-root");

    if (root) {
      root.setAttribute(
        "data-sea-turtle-active",
        snapshot.active ? "true" : "false",
      );
      root.setAttribute(
        "data-sea-turtle-rope-id",
        snapshot.activeRopeId === null ? "" : snapshot.activeRopeId,
      );
      root.setAttribute(
        "data-sea-turtle-completed-count",
        String(snapshot.completedRopeIds.length),
      );
      root.setAttribute(
        "data-sea-turtle-help-level",
        String(snapshot.helpLevel),
      );
      root.setAttribute(
        "data-sea-turtle-feedback",
        snapshot.feedback === null ? "none" : snapshot.feedback,
      );
      root.setAttribute(
        "data-sea-turtle-complete",
        snapshot.complete ? "true" : "false",
      );
    }

    if (SeaTurtleScene?.isMounted()) {
      const PointerInput = (window.OceanRescue as OceanRescueNamespace)?.PointerInput;
      const resolvedIntent = intent ?? (PointerInput ? PointerInput.inactiveIntent() : { active: false, x: null, y: null });
      return SeaTurtleScene.sync(snapshot, resolvedIntent);
    }

    host.renderLegacySeaTurtleFrame(snapshot, intent);
    return true;
  }

  const controller: SeaTurtleLifecycleAppApi = Object.assign(host, {
    isSeaTurtleActive,
    getSeaTurtleSnapshot,
    startSeaTurtleInteraction,
    syncSeaTurtleProjection,
  });
  return controller;
}
