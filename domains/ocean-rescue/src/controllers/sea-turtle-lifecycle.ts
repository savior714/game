/**
 * Typed controller boundary scaffold for sea-turtle rope lifecycle (WP-33E).
 *
 * This controller establishes the typed boundary for sea-turtle interaction
 * ownership. It defines the host/app API interfaces, resolves runtime
 * dependencies from the `window.OceanRescue` namespace, and returns the host
 * augmented with the typed boundary — without overriding any existing behavior.
 *
 * The actual pointer handling, feedback timer management, and mission-success
 * progression logic remain in the legacy `src/app.js` rollback authority.
 * Future WPs (WP-33E-H) will migrate those behaviors into this controller.
 *
 * This controller does NOT own:
 * - pointer event handling (addEventListener)
 * - pointer state storage
 * - feedback timer management
 * - phase transitions
 * - mission completion logic
 * - other mission lifecycles (crab, young-whale)
 */

import type {
  RescueSceneApi,
} from "../contracts/runtime-abi";
import type { PauseTimerResumeAppApi } from "./pause-timer-resume";

/**
 * A single rope segment in the sea-turtle interaction.
 * Each rope has a start and end point; the player must trace or tap-connect
 * from start to end within tolerance.
 */
export interface SeaTurtleRope {
  readonly id: string;
  readonly order: number;
  readonly start: Readonly<{ readonly x: number; readonly y: number }>;
  readonly end: Readonly<{ readonly x: number; readonly y: number }>;
}

/**
 * Immutable snapshot of the sea-turtle state machine.
 * Mirrors the shape produced by `SeaTurtle.getSnapshot()`.
 */
export interface SeaTurtleSnapshot {
  readonly active: boolean;
  readonly activeRopeId: string | null;
  readonly completedRopeIds: readonly string[];
  readonly failureCount: number;
  readonly helpLevel: number;
  readonly tapStartArmed: boolean;
  readonly pointerActive: boolean;
  readonly inputLocked: boolean;
  readonly feedback: "success" | "failure" | null;
  readonly complete: boolean;
}

/**
 * Result of a successful pointer-up gesture on a rope.
 */
export interface SeaTurtleRopeResult {
  readonly accepted: boolean;
  readonly outcome: "success" | "failure" | "none";
  readonly ropeId: string | null;
}

/**
 * Result of calling `finishFeedback()` to advance past the current feedback.
 */
export interface SeaTurtleFeedbackCompletion {
  readonly changed: boolean;
  readonly complete: boolean;
  readonly nextRopeId: string | null;
}

/**
 * Typed runtime API for the sea-turtle interaction state machine.
 * This replaces the untyped `MissionRuntimeApi` slot in the namespace.
 */
export interface SeaTurtleApi {
  readonly MissionId: string;
  readonly Ropes: readonly SeaTurtleRope[];
  readonly getSnapshot: () => SeaTurtleSnapshot;
  readonly start: () => boolean;
  readonly stop: () => boolean;
  readonly pointerDown: (pointerId: number, x: number, y: number) => boolean;
  readonly pointerMove: (pointerId: number, x: number, y: number) => boolean;
  readonly pointerUp: (
    pointerId: number,
    x: number,
    y: number,
  ) => SeaTurtleRopeResult;
  readonly pointerCancel: (pointerId: number) => boolean;
  readonly finishFeedback: () => SeaTurtleFeedbackCompletion;
  readonly pauseCancel: () => void;
}

/**
 * Typed scene API for the sea-turtle authored PixiJS scene.
 * Extends the base RescueSceneApi with scene-specific lifecycle.
 */
export interface SeaTurtleSceneApi extends RescueSceneApi {
  readonly activate: () => boolean;
  readonly sync: (snapshot: SeaTurtleSnapshot) => boolean;
}

interface ControllerDependencies {
  readonly SeaTurtle: SeaTurtleApi | null;
  readonly SeaTurtleScene: SeaTurtleSceneApi | null;
}

function resolveDependencies(): ControllerDependencies {
  const namespace = window.OceanRescue;
  return {
    SeaTurtle: (namespace?.SeaTurtle as SeaTurtleApi | undefined) ?? null,
    SeaTurtleScene: (namespace?.SeaTurtleScene as SeaTurtleSceneApi | undefined) ?? null,
  };
}

/**
 * Host interface required by the sea-turtle lifecycle controller.
 * Extends the previous layer (WP-33D) with pause-integration bridges.
 */
export interface SeaTurtleLifecycleHostApi extends PauseTimerResumeAppApi {
  cancelPausePointerInteractions(): void;
  shutdownActiveRescueForMenu(): void;
}

/**
 * App interface exposed by the sea-turtle lifecycle controller.
 * Declares the methods this controller will own in future WPs.
 */
export interface SeaTurtleLifecycleAppApi extends SeaTurtleLifecycleHostApi {
  isSeaTurtleActive(): boolean;
  getSeaTurtleSnapshot(): SeaTurtleSnapshot | null;
  startSeaTurtleInteraction(): boolean;
  handleSeaTurtlePointerDown(pointerId: number, x: number, y: number): boolean;
  handleSeaTurtlePointerMove(pointerId: number, x: number, y: number): boolean;
  handleSeaTurtlePointerUp(pointerId: number, x: number, y: number): SeaTurtleRopeResult;
  routeSeaTurtleFeedback(result: SeaTurtleRopeResult): void;
  beginSeaTurtleSuccessFeedback(ropeId: string): void;
  beginSeaTurtleFailureFeedback(ropeId: string): void;
  completeSeaTurtleFeedback(): boolean;
  completeSeaTurtleSuccess(): void;
}

export function installSeaTurtleLifecycleController(
  host: SeaTurtleLifecycleHostApi,
): SeaTurtleLifecycleAppApi {
  const { SeaTurtle, SeaTurtleScene } = resolveDependencies();

  function isSeaTurtleActive(): boolean {
    if (!SeaTurtle) {
      return false;
    }
    const snapshot = SeaTurtle.getSnapshot();
    return snapshot.active;
  }

  function getSeaTurtleSnapshot(): SeaTurtleSnapshot | null {
    if (!SeaTurtle) {
      return null;
    }
    return SeaTurtle.getSnapshot();
  }

  const controller = host as unknown as SeaTurtleLifecycleAppApi;
  controller.isSeaTurtleActive = isSeaTurtleActive;
  controller.getSeaTurtleSnapshot = getSeaTurtleSnapshot;

  return controller;
}
