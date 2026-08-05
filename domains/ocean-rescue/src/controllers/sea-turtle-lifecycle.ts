/**
 * Typed controller for sea-turtle rescue start and pointer lifecycle (WP-33E-B).
 *
 * This controller owns:
 * - sea-turtle rescue start (validation, SeaTurtle.start(), scene activate,
 *   pointer binding request, initial render, root markers)
 * - sea-turtle pointer ID tracking
 * - pointer capture element tracking
 * - pointer down / move / up / cancel handling
 * - pause-time pointer cancellation via SeaTurtle.pauseCancel()
 * - feedback handoff bridge dispatch (narrow host bridge)
 *
 * This controller does NOT own:
 * - feedback timer management
 * - success/failure progression
 * - dialogue and assist escalation
 * - final rope RESCUE_SUCCESS transition
 * - mission-success presentation
 * - crab or young-whale lifecycle
 * - DOM event listener registration (host owns bindRescuePointerInput)
 * - canvas drawing or authored scene graph
 *
 * Host bridge methods (implemented by legacy app.js):
 * - renderSeaTurtleFrame(intent?)
 * - updateSeaTurtleRootMarkers()
 * - hideAssistHand()
 * - ensureRescuePointerInputBound(canvas)
 * - routeSeaTurtleFeedback(result)
 * - syncSeaTurtleScene(intent?)
 */

import type {
  RescueSceneApi,
} from "../contracts/runtime-abi";
import type { PauseTimerResumeAppApi } from "./pause-timer-resume";

/**
 * A single rope segment in the sea-turtle interaction.
 */
export interface SeaTurtleRope {
  readonly id: string;
  readonly order: number;
  readonly start: Readonly<{ readonly x: number; readonly y: number }>;
  readonly end: Readonly<{ readonly x: number; readonly y: number }>;
}

/**
 * Immutable snapshot of the sea-turtle state machine.
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
 * Result of calling finishFeedback() to advance past the current feedback.
 */
export interface SeaTurtleFeedbackCompletion {
  readonly changed: boolean;
  readonly complete: boolean;
  readonly nextRopeId: string | null;
}

/**
 * Typed runtime API for the sea-turtle interaction state machine.
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
 */
export interface SeaTurtleSceneApi extends RescueSceneApi {
  readonly activate: () => boolean;
  readonly sync: (snapshot: SeaTurtleSnapshot, intent: unknown) => boolean;
}

/**
 * Shared pointer-coordinate mapper (WP-32B).
 */
export interface PointerInputApi {
  readonly mapRescuePoint: (
    event: { clientX: number; clientY: number },
    canvas: Element | null,
  ) => { x: number; y: number } | null;
  readonly activeIntent: (point: { x: number; y: number } | null) => unknown;
  readonly inactiveIntent: () => unknown;
}

interface ControllerDependencies {
  readonly SeaTurtle: SeaTurtleApi | null;
  readonly SeaTurtleScene: SeaTurtleSceneApi | null;
  readonly PointerInput: PointerInputApi | null;
}

function resolveDependencies(): ControllerDependencies {
  const namespace = window.OceanRescue;
  return {
    SeaTurtle: (namespace?.SeaTurtle as SeaTurtleApi | undefined) ?? null,
    SeaTurtleScene: (namespace?.SeaTurtleScene as SeaTurtleSceneApi | undefined) ?? null,
    PointerInput: (namespace?.PointerInput as PointerInputApi | undefined) ?? null,
  };
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && isFinite(value);
}

/**
 * Host interface required by the sea-turtle lifecycle controller.
 * Extends the previous layer (WP-33D) with rendering and feedback bridges.
 */
export interface SeaTurtleLifecycleHostApi extends PauseTimerResumeAppApi {
  cancelPausePointerInteractions(): void;
  shutdownActiveRescueForMenu(): void;

  /** Render a single sea-turtle frame, optionally with a pointer intent. */
  renderSeaTurtleFrame(intent?: unknown): void;

  /** Update data-* markers on #ocean-rescue-root from SeaTurtle snapshot. */
  updateSeaTurtleRootMarkers(): void;

  /** Hide the assist hand element. */
  hideAssistHand(): void;

  /** Ensure pointer input listeners are bound to the given canvas. */
  ensureRescuePointerInputBound(canvas: Element): void;

  /** Narrow bridge: dispatch accepted pointer-up result to legacy feedback. */
  routeSeaTurtleFeedback(result: SeaTurtleRopeResult): void;

  /** Sync the authored sea-turtle scene with snapshot + intent. */
  syncSeaTurtleScene(intent?: unknown): void;
}

/**
 * App interface exposed by the sea-turtle lifecycle controller.
 */
export interface SeaTurtleLifecycleAppApi extends SeaTurtleLifecycleHostApi {
  isSeaTurtleActive(): boolean;
  getSeaTurtleSnapshot(): SeaTurtleSnapshot | null;

  /** Validate preconditions and start the sea-turtle rescue interaction. */
  startSeaTurtleInteraction(): boolean;

  /** Handle a pointerdown event for the sea-turtle rescue. */
  handleSeaTurtlePointerDown(event: PointerEvent): void;

  /** Handle a pointermove event for the sea-turtle rescue. */
  handleSeaTurtlePointerMove(event: PointerEvent): void;

  /** Handle a pointerup event for the sea-turtle rescue. */
  handleSeaTurtlePointerUp(event: PointerEvent): void;

  /** Handle a pointercancel event for the sea-turtle rescue. */
  handleSeaTurtlePointerCancel(event: PointerEvent): void;

  /** Release pointer capture and call SeaTurtle.pauseCancel() for pause. */
  cancelSeaTurtlePointerForPause(): void;

  /** Full shutdown of sea-turtle pointer state (for menu return). */
  shutdownSeaTurtlePointer(): void;
}

export function installSeaTurtleLifecycleController(
  host: SeaTurtleLifecycleHostApi,
): SeaTurtleLifecycleAppApi {
  const { SeaTurtle, SeaTurtleScene, PointerInput } = resolveDependencies();

  let activePointerId: number | null = null;
  let pointerCaptureEl: Element | null = null;

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

  function resolveCanvas(): Element | null {
    return (
      (typeof document !== "undefined"
        ? document.getElementById("ocean-rescue-canvas")
        : null) ?? null
    );
  }

  function mapCoordinates(event: PointerEvent): { x: number; y: number } | null {
    if (!PointerInput) {
      return null;
    }
    const canvas = resolveCanvas();
    return PointerInput.mapRescuePoint(
      { clientX: event.clientX, clientY: event.clientY },
      canvas,
    );
  }

  function releaseCapture(): void {
    if (
      pointerCaptureEl &&
      typeof pointerCaptureEl.releasePointerCapture === "function" &&
      activePointerId !== null
    ) {
      pointerCaptureEl.releasePointerCapture(activePointerId);
    }
  }

  function clearPointerState(): void {
    releaseCapture();
    activePointerId = null;
    pointerCaptureEl = null;
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

    const sequence = (host as unknown as { getActiveRescueSequence(): unknown }).getActiveRescueSequence();
    if (!sequence || typeof sequence !== "object") {
      return false;
    }
    const seq = sequence as { missionId?: unknown };
    if (seq.missionId !== SeaTurtle.MissionId) {
      return false;
    }

    const snapshot = State.getSnapshot();
    if (snapshot.phase !== "RESCUE_ACTIVE") {
      return false;
    }

    if (host.isPauseActive()) {
      return false;
    }

    const canvas = resolveCanvas();
    if (!canvas) {
      return false;
    }

    const renderRuntime = (namespace?.RenderRuntime ?? null);
    if (!(renderRuntime && renderRuntime.isReady())) {
      return false;
    }

    if (SeaTurtleScene && !SeaTurtleScene.isMounted()) {
      const root = typeof document !== "undefined" ? document.getElementById("ocean-rescue-root") : null;
      if (root) {
        root.setAttribute("data-rescue-input", "disabled");
      }
      return false;
    }

    const started = SeaTurtle.start();
    if (!started) {
      return false;
    }

    if (SeaTurtleScene && SeaTurtleScene.isMounted()) {
      SeaTurtleScene.activate();
    }

    host.ensureRescuePointerInputBound(canvas);
    host.renderSeaTurtleFrame();
    host.updateSeaTurtleRootMarkers();

    return true;
  }

  function handleSeaTurtlePointerDown(event: PointerEvent): void {
    if (!event || typeof event !== "object") {
      return;
    }
    if (host.isPauseActive()) {
      if (typeof event.preventDefault === "function") event.preventDefault();
      if (typeof event.stopPropagation === "function") event.stopPropagation();
      return;
    }

    const namespace = window.OceanRescue;
    const State = namespace?.State;
    if (!State) {
      return;
    }
    const stateSnapshot = State.getSnapshot();
    if (stateSnapshot.phase !== "RESCUE_ACTIVE") {
      return;
    }

    const sequence = (host as unknown as { getActiveRescueSequence(): unknown }).getActiveRescueSequence();
    if (!sequence || typeof sequence !== "object") {
      return;
    }
    if (!SeaTurtle) {
      return;
    }
    const seq = sequence as { missionId?: unknown };
    if (seq.missionId !== SeaTurtle.MissionId) {
      return;
    }
    const stSnapshot = SeaTurtle.getSnapshot();
    if (!stSnapshot.active) {
      return;
    }
    if (stSnapshot.inputLocked) {
      return;
    }

    const root = typeof document !== "undefined" ? document.getElementById("ocean-rescue-root") : null;
    if (root && root.getAttribute("data-rescue-input") === "disabled") {
      return;
    }

    if (event.isPrimary === false) {
      return;
    }
    if (typeof event.button === "number" && event.button !== 0) {
      return;
    }
    if (!isFiniteNumber(event.clientX) || !isFiniteNumber(event.clientY)) {
      return;
    }

    if (activePointerId !== null) {
      return;
    }

    const mapped = mapCoordinates(event);
    if (mapped === null) {
      if (typeof event.pointerId === "number" && isFiniteNumber(event.pointerId)) {
        SeaTurtle.pointerCancel(event.pointerId);
      }
      return;
    }

    const pointerId = event.pointerId;
    if (!isFiniteNumber(pointerId)) {
      return;
    }

    const started = SeaTurtle.pointerDown(pointerId, mapped.x, mapped.y);
    if (!started) {
      return;
    }

    activePointerId = pointerId;
    pointerCaptureEl = resolveCanvas();

    if (
      pointerCaptureEl &&
      typeof pointerCaptureEl.setPointerCapture === "function"
    ) {
      pointerCaptureEl.setPointerCapture(pointerId);
    }

    host.hideAssistHand();
    const intent = PointerInput ? PointerInput.activeIntent(mapped) : undefined;
    host.renderSeaTurtleFrame(intent);
    host.updateSeaTurtleRootMarkers();

    if (typeof event.preventDefault === "function") event.preventDefault();
    if (typeof event.stopPropagation === "function") event.stopPropagation();
  }

  function handleSeaTurtlePointerMove(event: PointerEvent): void {
    if (!event || typeof event !== "object") {
      return;
    }
    if (activePointerId === null) {
      return;
    }
    if (host.isPauseActive()) {
      return;
    }

    const namespace = window.OceanRescue;
    const State = namespace?.State;
    if (!State) {
      return;
    }
    const stateSnapshot = State.getSnapshot();
    if (stateSnapshot.phase !== "RESCUE_ACTIVE") {
      return;
    }

    if (!isFiniteNumber(event.pointerId)) {
      return;
    }
    if (event.pointerId !== activePointerId) {
      return;
    }
    if (!isFiniteNumber(event.clientX) || !isFiniteNumber(event.clientY)) {
      return;
    }

    const mapped = mapCoordinates(event);
    if (mapped === null) {
      return;
    }

    if (!SeaTurtle) {
      return;
    }
    SeaTurtle.pointerMove(event.pointerId, mapped.x, mapped.y);

    const intent = PointerInput ? PointerInput.activeIntent(mapped) : undefined;
    host.renderSeaTurtleFrame(intent);
    host.updateSeaTurtleRootMarkers();

    if (typeof event.preventDefault === "function") event.preventDefault();
    if (typeof event.stopPropagation === "function") event.stopPropagation();
  }

  function handleSeaTurtlePointerUp(event: PointerEvent): void {
    if (!event || typeof event !== "object") {
      return;
    }
    if (activePointerId === null) {
      return;
    }
    if (host.isPauseActive()) {
      return;
    }

    const namespace = window.OceanRescue;
    const State = namespace?.State;
    if (!State) {
      return;
    }
    const stateSnapshot = State.getSnapshot();
    if (stateSnapshot.phase !== "RESCUE_ACTIVE") {
      return;
    }

    if (!isFiniteNumber(event.pointerId)) {
      return;
    }
    if (event.pointerId !== activePointerId) {
      return;
    }

    let result: SeaTurtleRopeResult | null = null;
    const mapped = mapCoordinates(event);
    if (mapped !== null) {
      if (!SeaTurtle) {
        clearPointerState();
        return;
      }
      result = SeaTurtle.pointerUp(event.pointerId, mapped.x, mapped.y);
    } else {
      if (!SeaTurtle) {
        clearPointerState();
        return;
      }
      SeaTurtle.pointerCancel(event.pointerId);
    }

    clearPointerState();

    if (result && result.accepted) {
      const inactiveIntent = PointerInput ? PointerInput.inactiveIntent() : undefined;
      host.renderSeaTurtleFrame(inactiveIntent);
      host.updateSeaTurtleRootMarkers();
      host.routeSeaTurtleFeedback(result);
    }

    if (typeof event.preventDefault === "function") event.preventDefault();
    if (typeof event.stopPropagation === "function") event.stopPropagation();
  }

  function handleSeaTurtlePointerCancel(event: PointerEvent): void {
    if (!event || typeof event !== "object") {
      return;
    }
    if (activePointerId === null) {
      return;
    }
    if (!isFiniteNumber(event.pointerId)) {
      return;
    }
    if (event.pointerId !== activePointerId) {
      return;
    }

    if (!SeaTurtle) {
      clearPointerState();
      return;
    }
    SeaTurtle.pointerCancel(event.pointerId);

    clearPointerState();

    if (SeaTurtleScene && SeaTurtleScene.isMounted()) {
      const inactiveIntent = PointerInput ? PointerInput.inactiveIntent() : undefined;
      host.syncSeaTurtleScene(inactiveIntent);
    }
  }

  function cancelSeaTurtlePointerForPause(): void {
    if (activePointerId === null) {
      if (SeaTurtle) {
        SeaTurtle.pauseCancel();
      }
      return;
    }
    releaseCapture();
    const capturedId = activePointerId;
    activePointerId = null;
    pointerCaptureEl = null;
    if (SeaTurtle && typeof SeaTurtle.pauseCancel === "function") {
      SeaTurtle.pauseCancel();
    }
    if (capturedId !== null && SeaTurtle) {
      SeaTurtle.pointerCancel(capturedId);
    }
  }

  function shutdownSeaTurtlePointer(): void {
    clearPointerState();
  }

  const controller = host as unknown as SeaTurtleLifecycleAppApi;
  controller.isSeaTurtleActive = isSeaTurtleActive;
  controller.getSeaTurtleSnapshot = getSeaTurtleSnapshot;
  controller.startSeaTurtleInteraction = startSeaTurtleInteraction;
  controller.handleSeaTurtlePointerDown = handleSeaTurtlePointerDown;
  controller.handleSeaTurtlePointerMove = handleSeaTurtlePointerMove;
  controller.handleSeaTurtlePointerUp = handleSeaTurtlePointerUp;
  controller.handleSeaTurtlePointerCancel = handleSeaTurtlePointerCancel;
  controller.cancelSeaTurtlePointerForPause = cancelSeaTurtlePointerForPause;
  controller.shutdownSeaTurtlePointer = shutdownSeaTurtlePointer;

  return controller;
}
