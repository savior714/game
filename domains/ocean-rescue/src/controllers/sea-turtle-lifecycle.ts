/**
 * Typed controller for sea-turtle session activation, shutdown, and pointer
 * gesture lifecycle (WP-33E-2, WP-33E-3).
 *
 * This controller owns:
 * - active SeaTurtleSessionRef storage
 * - sequence-bound session start with full validation
 * - duplicate start idempotency (same sequence)
 * - wrong/stale sequence rejection
 * - SeaTurtle.start() / SeaTurtle.stop()
 * - authored scene activate / exit
 * - shared pointer listener binding request via host bridge
 * - initial "Rope 1 of 3" progress projection
 * - initial assist hand hide request
 * - initial syncSeaTurtleProjection()
 * - session stop with scene exit and SeaTurtle.stop()
 * - session reference clear
 * - active sea-turtle pointer ID and capture element state
 * - isSeaTurtlePointerTracked(event) validation against active session/phase/pointer
 * - handleSeaTurtlePointerDown(event) with coordinate mapping, capture, projection
 * - handleSeaTurtlePointerMove(event) with coordinate mapping and projection sync
 * - handleSeaTurtlePointerUp(event) with result routing via host bridge
 * - handleSeaTurtlePointerCancel(event) with capture release and projection sync
 * - cancelSeaTurtlePointerForPause() cleanup with SeaTurtle.pauseCancel()
 * - shutdownSeaTurtlePointer() cleanup (idempotent)
 * - stopSeaTurtleSession() triggers pointer shutdown to avoid leftover capture
 *
 * This controller does NOT own:
 * - shared rescue mission router (app.js)
 * - bindRescuePointerInput actual DOM listener registration (app.js)
 * - sea-turtle feedback sequence and timer (app.js)
 * - sea-turtle feedback UI (app.js)
 * - assist escalation (app.js)
 * - RESCUE_SUCCESS transition (app.js)
 * - mission-success handoff (app.js)
 * - crab lifecycle (app.js)
 * - young-whale lifecycle (app.js)
 */

import type { PauseTimerResumeAppApi } from "./pause-timer-resume";
import type { RescueSiteSequence } from "./rescue-site-tutorial";
import type {
  ActivePointerIntent,
  InactivePointerIntent,
} from "../contracts/pointer-input";
import type {
  PointerIntent,
  SeaTurtleApi,
  SeaTurtleFeedbackCompletion,
  SeaTurtleRopeId,
  SeaTurtleRopeResult,
  SeaTurtleSceneApi,
  SeaTurtleSnapshot,
  OceanRescueNamespace,
} from "../contracts/runtime-abi";

export interface SeaTurtleSessionRef {
  readonly rescueSequenceId: number;
  readonly missionId: "sea-turtle";
}

export interface SeaTurtleFeedbackSequence {
  readonly rescueSequenceId: number;
  readonly ropeId: SeaTurtleRopeId;
  readonly kind: "success" | "failure";
}

/**
 * Host methods required by the sea-turtle lifecycle controller.
 * Extends PauseTimerResumeAppApi to inherit phase/timer/pause capabilities
 * without duplicating declarations for methods already provided upstream.
 */
export interface SeaTurtleLifecycleHostApi extends PauseTimerResumeAppApi {
  ensureRescuePointerInputBound(canvas: HTMLCanvasElement): void;
  hideAssistHand(): void;
  renderLegacySeaTurtleFrame(
    snapshot: SeaTurtleSnapshot,
    intent?: PointerIntent,
  ): void;
  renderSeaTurtleFrame(
    snapshot: SeaTurtleSnapshot,
    intent?: PointerIntent,
  ): void;
  updateSeaTurtleRootMarkers(): void;
  syncSeaTurtleScene(intent?: PointerIntent): void;
  routeSeaTurtleFeedback(result: SeaTurtleRopeResult): void;
  onSeaTurtleFeedbackComplete(
    sequence: SeaTurtleFeedbackSequence,
    result: SeaTurtleFeedbackCompletion,
  ): void;
  onSeaTurtleInteractionComplete(session: SeaTurtleSessionRef): void;
  applySeaTurtleFeedbackVisuals(kind: "success" | "failure", ropeId: SeaTurtleRopeId): void;
}

/** Read-only handle to the controller-managed sea-turtle pointer state. */
export interface SeaTurtlePointerRef {
  readonly pointerId: number;
  readonly captureElement: Element;
}

/** Public API exposed by the sea-turtle lifecycle controller. */
export interface SeaTurtleLifecycleAppApi extends SeaTurtleLifecycleHostApi {
  isSeaTurtleActive(): boolean;
  getSeaTurtleSnapshot(): SeaTurtleSnapshot | null;
  startSeaTurtleSession(sequence: RescueSiteSequence): boolean;
  startSeaTurtleInteraction(sequence: RescueSiteSequence): boolean;
  stopSeaTurtleSession(): boolean;
  getActiveSeaTurtleSession(): SeaTurtleSessionRef | null;
  isSeaTurtleSessionActive(): boolean;
  syncSeaTurtleProjection(intent?: PointerIntent): boolean;
  isSeaTurtlePointerTracked(event: PointerEvent): boolean;
  handleSeaTurtlePointerDown(event: PointerEvent): boolean;
  handleSeaTurtlePointerMove(event: PointerEvent): boolean;
  handleSeaTurtlePointerUp(event: PointerEvent): boolean;
  handleSeaTurtlePointerCancel(event: PointerEvent): boolean;
  cancelSeaTurtlePointerForPause(): boolean;
  shutdownSeaTurtlePointer(): boolean;
  beginSeaTurtlePointer(pointerId: number, captureElement: Element): boolean;
  isTrackedSeaTurtlePointer(pointerId: number): boolean;
  hasTrackedSeaTurtlePointer(): boolean;
  takeSeaTurtlePointer(pointerId: number): SeaTurtlePointerRef | null;
  clearSeaTurtlePointer(): SeaTurtlePointerRef | null;
  beginSeaTurtleFeedback(result: SeaTurtleRopeResult): boolean;
  clearSeaTurtleFeedback(): void;
  /** Test-only hook: invoke the pending sea-turtle-feedback timer callback. */
  __testFlushSeaTurtleFeedback(): void;
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

  let activeSession: SeaTurtleSessionRef | null = null;
  let activePointerId: number | null = null;
  let activePointerCaptureElement: Element | null = null;
  let activeFeedback: SeaTurtleFeedbackSequence | null = null;
  let pendingFeedbackTimer = false;
  let feedbackFlushHook: (() => void) | null = null;

  function isSeaTurtleActive(): boolean {
    return SeaTurtle?.getSnapshot().active ?? false;
  }

  function getSeaTurtleSnapshot(): SeaTurtleSnapshot | null {
    return SeaTurtle?.getSnapshot() ?? null;
  }

  function getActiveSeaTurtleSession(): SeaTurtleSessionRef | null {
    return activeSession;
  }

  function isSeaTurtleSessionActive(): boolean {
    return activeSession !== null;
  }

  function startSeaTurtleSession(sequence: RescueSiteSequence): boolean {
    if (!SeaTurtle) {
      return false;
    }
    if (!sequence || typeof sequence !== "object") {
      return false;
    }
    if (sequence.missionId !== SeaTurtle.MissionId) {
      return false;
    }

    const activeSequence = host.getActiveRescueSequence();
    if (activeSequence === null) {
      return false;
    }
    if (activeSequence.sequenceId !== sequence.sequenceId) {
      return false;
    }
    if (activeSequence.missionId !== "sea-turtle") {
      return false;
    }

    const State = window.OceanRescue?.State;
    if (!State || State.getSnapshot().phase !== State.Phases.RESCUE_ACTIVE) {
      return false;
    }

    const canvas = host.resolveVisibleInputCanvas();
    if (!(canvas instanceof HTMLCanvasElement)) {
      return false;
    }

    const overlay = document.getElementById("ocean-rescue-rescue-overlay");
    if (!overlay) {
      return false;
    }

    if (activeSession !== null) {
      if (
        activeSession.rescueSequenceId === sequence.sequenceId &&
        SeaTurtle?.getSnapshot().active === true
      ) {
        return true;
      }
      return false;
    }

    if (!SeaTurtle.start()) {
      return false;
    }

    activeSession = {
      rescueSequenceId: sequence.sequenceId,
      missionId: "sea-turtle",
    };

    if (SeaTurtleScene?.isMounted()) {
      SeaTurtleScene.activate();
    }

    host.ensureRescuePointerInputBound(canvas);

    const progress = document.getElementById("ocean-rescue-rescue-progress");
    if (progress) {
      progress.textContent = "Rope 1 of 3";
    }

    host.hideAssistHand();
    syncSeaTurtleProjection();
    host.syncPauseButton();

    return true;
  }

  function startSeaTurtleInteraction(sequence: RescueSiteSequence): boolean {
    return startSeaTurtleSession(sequence);
  }

  function stopSeaTurtleSession(): boolean {
    const hadSession = activeSession !== null;

    clearSeaTurtleFeedback();
    shutdownSeaTurtlePointer();

    if (SeaTurtleScene?.isMounted()) {
      SeaTurtleScene.exit();
    }

    if (SeaTurtle?.getSnapshot().active === true) {
      SeaTurtle.stop();
    }

    activeSession = null;

    if (hadSession) {
      return true;
    }
    return false;
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

  function validateSeaTurtlePointerEvent(
    event: PointerEvent,
  ): { valid: boolean; mapped: { x: number; y: number } | null } {
    if (!event || typeof event !== "object") {
      return { valid: false, mapped: null };
    }
    if (!activeSession) {
      return { valid: false, mapped: null };
    }
    const activeSequence = host.getActiveRescueSequence();
    if (activeSequence === null) {
      return { valid: false, mapped: null };
    }
    if (activeSequence.sequenceId !== activeSession.rescueSequenceId) {
      return { valid: false, mapped: null };
    }
    if (activeSequence.missionId !== "sea-turtle") {
      return { valid: false, mapped: null };
    }
    const State = window.OceanRescue?.State;
    if (!State || State.getSnapshot().phase !== State.Phases.RESCUE_ACTIVE) {
      return { valid: false, mapped: null };
    }
    if (!SeaTurtle) {
      return { valid: false, mapped: null };
    }
    const snapshot = SeaTurtle.getSnapshot();
    if (!snapshot.active) {
      return { valid: false, mapped: null };
    }
    if (typeof event.pointerId !== "number" || !isFinite(event.pointerId)) {
      return { valid: false, mapped: null };
    }
    if (typeof event.clientX !== "number" || !isFinite(event.clientX)) {
      return { valid: false, mapped: null };
    }
    if (typeof event.clientY !== "number" || !isFinite(event.clientY)) {
      return { valid: false, mapped: null };
    }
    return { valid: true, mapped: null };
  }

  function isSeaTurtlePointerTracked(event: PointerEvent): boolean {
    const validation = validateSeaTurtlePointerEvent(event);
    if (!validation.valid) {
      return false;
    }
    if (activePointerId === null) {
      return false;
    }
    if (event.pointerId !== activePointerId) {
      return false;
    }
    return true;
  }

  function handleSeaTurtlePointerDown(event: PointerEvent): boolean {
    if (!event || typeof event !== "object") {
      return false;
    }
    if (activePointerId !== null) {
      return false;
    }
    if (event.isPrimary === false) {
      return false;
    }
    if (typeof event.button === "number" && event.button !== 0) {
      return false;
    }

    const validation = validateSeaTurtlePointerEvent(event);
    if (!validation.valid) {
      return false;
    }

    const canvas = host.resolveVisibleInputCanvas();
    if (!(canvas instanceof HTMLCanvasElement)) {
      return false;
    }

    const PointerInput = (window.OceanRescue as OceanRescueNamespace)?.PointerInput;
    const mapped = PointerInput
      ? PointerInput.mapRescuePoint(event, canvas)
      : null;

    if (!mapped || typeof mapped.x !== "number" || !isFinite(mapped.x) ||
        typeof mapped.y !== "number" || !isFinite(mapped.y)) {
      return false;
    }

    if (!SeaTurtle?.pointerDown(event.pointerId, mapped.x, mapped.y)) {
      return false;
    }

    const captureElement =
      (event.currentTarget instanceof HTMLCanvasElement
        ? event.currentTarget
        : canvas) as Element;

    activePointerId = event.pointerId;
    activePointerCaptureElement = captureElement;

    if (
      captureElement &&
      typeof captureElement.setPointerCapture === "function"
    ) {
      captureElement.setPointerCapture(event.pointerId);
    }

    host.hideAssistHand();

    const activeIntent: PointerIntent = PointerInput
      ? PointerInput.activeIntent(mapped)
      : { active: true, x: mapped.x, y: mapped.y };
    syncSeaTurtleProjection(activeIntent);

    if (typeof event.preventDefault === "function") {
      event.preventDefault();
    }
    if (typeof event.stopPropagation === "function") {
      event.stopPropagation();
    }

    return true;
  }

  function handleSeaTurtlePointerMove(event: PointerEvent): boolean {
    if (!isSeaTurtlePointerTracked(event)) {
      return false;
    }

    const validation = validateSeaTurtlePointerEvent(event);
    if (!validation.valid) {
      return false;
    }

    const canvas = host.resolveVisibleInputCanvas();
    if (!(canvas instanceof HTMLCanvasElement)) {
      return false;
    }

    const PointerInput = (window.OceanRescue as OceanRescueNamespace)?.PointerInput;
    const mapped = PointerInput
      ? PointerInput.mapRescuePoint(event, canvas)
      : null;

    if (!mapped || typeof mapped.x !== "number" || !isFinite(mapped.x) ||
        typeof mapped.y !== "number" || !isFinite(mapped.y)) {
      return false;
    }

    SeaTurtle?.pointerMove(event.pointerId, mapped.x, mapped.y);

    const activeIntent: PointerIntent = PointerInput
      ? PointerInput.activeIntent(mapped)
      : { active: true, x: mapped.x, y: mapped.y };
    syncSeaTurtleProjection(activeIntent);

    if (typeof event.preventDefault === "function") {
      event.preventDefault();
    }
    if (typeof event.stopPropagation === "function") {
      event.stopPropagation();
    }

    return true;
  }

  function handleSeaTurtlePointerUp(event: PointerEvent): boolean {
    if (!isSeaTurtlePointerTracked(event)) {
      return false;
    }

    const validation = validateSeaTurtlePointerEvent(event);
    if (!validation.valid) {
      return false;
    }

    const canvas = host.resolveVisibleInputCanvas();
    if (!(canvas instanceof HTMLCanvasElement)) {
      return false;
    }

    const PointerInput = (window.OceanRescue as OceanRescueNamespace)?.PointerInput;
    const mapped = PointerInput
      ? PointerInput.mapRescuePoint(event, canvas)
      : null;

    let result: SeaTurtleRopeResult | null = null;
    if (mapped !== null && typeof mapped.x === "number" && typeof mapped.y === "number") {
      result = SeaTurtle?.pointerUp(event.pointerId, mapped.x, mapped.y) ?? null;
    } else {
      SeaTurtle?.pointerCancel(event.pointerId);
    }

    releaseActivePointerCapture();

    const cleared = clearSeaTurtlePointerState();
    if (!cleared) {
      return false;
    }

    if (result && result.accepted) {
      const inactiveIntent: PointerIntent = PointerInput
        ? PointerInput.inactiveIntent()
        : { active: false, x: null, y: null };
      syncSeaTurtleProjection(inactiveIntent);
      if (result.outcome === "success" || result.outcome === "failure") {
        beginSeaTurtleFeedback(result);
      }
    }

    if (typeof event.preventDefault === "function") {
      event.preventDefault();
    }
    if (typeof event.stopPropagation === "function") {
      event.stopPropagation();
    }

    return true;
  }

  function handleSeaTurtlePointerCancel(event: PointerEvent): boolean {
    if (!event || typeof event !== "object") {
      return false;
    }
    if (activePointerId === null) {
      return false;
    }
    if (typeof event.pointerId !== "number" || !isFinite(event.pointerId)) {
      return false;
    }
    if (event.pointerId !== activePointerId) {
      return false;
    }

    SeaTurtle?.pointerCancel(event.pointerId);

    releaseActivePointerCapture();

    const cleared = clearSeaTurtlePointerState();
    if (!cleared) {
      return false;
    }

    const PointerInput = (window.OceanRescue as OceanRescueNamespace)?.PointerInput;
    const inactiveIntent: PointerIntent = PointerInput
      ? PointerInput.inactiveIntent()
      : { active: false, x: null, y: null };
    syncSeaTurtleProjection(inactiveIntent);

    if (typeof event.preventDefault === "function") {
      event.preventDefault();
    }
    if (typeof event.stopPropagation === "function") {
      event.stopPropagation();
    }

    return true;
  }

  function releaseActivePointerCapture(): void {
    if (
      activePointerCaptureElement &&
      typeof activePointerCaptureElement.releasePointerCapture === "function"
    ) {
      activePointerCaptureElement.releasePointerCapture(activePointerId ?? 0);
    }
  }

  function clearSeaTurtlePointerState(): boolean {
    if (activePointerId === null) {
      return false;
    }
    activePointerId = null;
    activePointerCaptureElement = null;
    return true;
  }

  function cancelSeaTurtlePointerForPause(): boolean {
    releaseActivePointerCapture();
    clearSeaTurtlePointerState();

    if (SeaTurtle && typeof SeaTurtle.pauseCancel === "function") {
      SeaTurtle.pauseCancel();
    }

    const PointerInput = (window.OceanRescue as OceanRescueNamespace)?.PointerInput;
    const inactiveIntent: PointerIntent = PointerInput
      ? PointerInput.inactiveIntent()
      : { active: false, x: null, y: null };
    syncSeaTurtleProjection(inactiveIntent);

    return true;
  }

  function shutdownSeaTurtlePointer(): boolean {
    releaseActivePointerCapture();
    clearSeaTurtlePointerState();
    return true;
  }

  function beginSeaTurtlePointer(
    pointerId: number,
    captureElement: Element,
  ): boolean {
    if (activePointerId !== null) {
      return false;
    }
    activePointerId = pointerId;
    activePointerCaptureElement = captureElement;
    return true;
  }

  function isTrackedSeaTurtlePointer(pointerId: number): boolean {
    return activePointerId === pointerId;
  }

  function hasTrackedSeaTurtlePointer(): boolean {
    return activePointerId !== null;
  }

  function takeSeaTurtlePointer(pointerId: number): SeaTurtlePointerRef | null {
    if (activePointerId !== pointerId) {
      return null;
    }
    const ref: SeaTurtlePointerRef = {
      pointerId: activePointerId,
      captureElement: activePointerCaptureElement as Element,
    };
    activePointerId = null;
    activePointerCaptureElement = null;
    return ref;
  }

  function clearSeaTurtlePointer(): SeaTurtlePointerRef | null {
    if (activePointerId === null) {
      return null;
    }
    const ref: SeaTurtlePointerRef = {
      pointerId: activePointerId,
      captureElement: activePointerCaptureElement as Element,
    };
    activePointerId = null;
    activePointerCaptureElement = null;
    return ref;
  }

  function clearSeaTurtleFeedback(): void {
    host.cancelPauseableTimer("sea-turtle-feedback");
    pendingFeedbackTimer = false;
    feedbackFlushHook = null;
    activeFeedback = null;
  }

  function beginSeaTurtleFeedback(result: SeaTurtleRopeResult): boolean {
    if (!SeaTurtle) {
      return false;
    }
    if (!result || typeof result !== "object") {
      return false;
    }
    if (result.accepted !== true) {
      return false;
    }
    if (result.outcome !== "success" && result.outcome !== "failure") {
      return false;
    }
    if (result.ropeId === null) {
      return false;
    }
    if (!activeSession) {
      return false;
    }
    const activeSequence = host.getActiveRescueSequence();
    if (!activeSequence) {
      return false;
    }
    if (activeSequence.sequenceId !== activeSession.rescueSequenceId) {
      return false;
    }
    if (activeSequence.missionId !== "sea-turtle") {
      return false;
    }

    clearSeaTurtleFeedback();

    const sequence: SeaTurtleFeedbackSequence = {
      rescueSequenceId: activeSession.rescueSequenceId,
      ropeId: result.ropeId,
      kind: result.outcome,
    };
    activeFeedback = sequence;
    pendingFeedbackTimer = true;

    host.applySeaTurtleFeedbackVisuals(result.outcome, result.ropeId);

    const capturedSequence = sequence;
    const durationMs =
      result.outcome === "success"
        ? SeaTurtle.Constants.successFeedbackMs
        : SeaTurtle.Constants.failureFeedbackMs;

    host.schedulePauseableTimer(
      "sea-turtle-feedback",
      durationMs,
      function (): void {
        pendingFeedbackTimer = false;
        feedbackFlushHook = null;
        finishActiveFeedback(capturedSequence);
      },
    );
    feedbackFlushHook = function (): void {
      pendingFeedbackTimer = false;
      feedbackFlushHook = null;
      finishActiveFeedback(capturedSequence);
    };

    return true;
  }

  function finishActiveFeedback(
    sequence: SeaTurtleFeedbackSequence,
  ): void {
    if (!SeaTurtle) {
      return;
    }
    if (!activeFeedback) {
      return;
    }
    if (activeFeedback !== sequence) {
      return;
    }
    if (!activeSession) {
      return;
    }
    if (activeSession.rescueSequenceId !== sequence.rescueSequenceId) {
      return;
    }
    const activeSequence = host.getActiveRescueSequence();
    if (!activeSequence) {
      return;
    }
    if (activeSequence.sequenceId !== sequence.rescueSequenceId) {
      return;
    }
    const snapshot = SeaTurtle.getSnapshot();
    if (snapshot.feedback === null) {
      return;
    }
    if (snapshot.feedback !== sequence.kind) {
      return;
    }
    if (snapshot.activeRopeId !== sequence.ropeId) {
      return;
    }

    activeFeedback = null;
    const session = activeSession;
    const result = SeaTurtle.finishFeedback();
    if (!result.changed) {
      return;
    }
    syncSeaTurtleProjection();
    if (result.complete === true) {
      if (session) {
        host.onSeaTurtleInteractionComplete(session);
      }
      return;
    }
    if (result.complete === false) {
      host.onSeaTurtleFeedbackComplete(sequence, result);
    }
  }

  function __testFlushSeaTurtleFeedback(): void {
    if (typeof feedbackFlushHook === "function") {
      const hook = feedbackFlushHook;
      feedbackFlushHook = null;
      pendingFeedbackTimer = false;
      hook();
    }
  }

  const controller: SeaTurtleLifecycleAppApi = Object.assign(host, {
    isSeaTurtleActive,
    getSeaTurtleSnapshot,
    getActiveSeaTurtleSession,
    isSeaTurtleSessionActive,
    startSeaTurtleInteraction,
    startSeaTurtleSession,
    stopSeaTurtleSession,
    syncSeaTurtleProjection,
    isSeaTurtlePointerTracked,
    handleSeaTurtlePointerDown,
    handleSeaTurtlePointerMove,
    handleSeaTurtlePointerUp,
    handleSeaTurtlePointerCancel,
    cancelSeaTurtlePointerForPause,
    shutdownSeaTurtlePointer,
    beginSeaTurtlePointer,
    isTrackedSeaTurtlePointer,
    hasTrackedSeaTurtlePointer,
    takeSeaTurtlePointer,
    clearSeaTurtlePointer,
    beginSeaTurtleFeedback,
    clearSeaTurtleFeedback,
    __testFlushSeaTurtleFeedback,
  });
  return controller;
}
