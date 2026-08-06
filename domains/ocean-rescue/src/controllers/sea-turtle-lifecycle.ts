/**
 * Typed controller for sea-turtle session activation and shutdown ownership
 * (WP-33E-2).
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
 *
 * This controller does NOT own:
 * - shared rescue mission router (app.js)
 * - bindRescuePointerInput actual DOM listener registration (app.js)
 * - sea-turtle pointer ID / capture element (app.js)
 * - pointer down/move/up/cancel handlers (app.js)
 * - feedback sequence and timer (app.js)
 * - feedback UI (app.js)
 * - assist escalation (app.js)
 * - RESCUE_SUCCESS transition (app.js)
 * - mission-success handoff (app.js)
 * - crab lifecycle (app.js)
 * - young-whale lifecycle (app.js)
 */

import type { PauseTimerResumeAppApi } from "./pause-timer-resume";
import type { RescueSiteSequence } from "./rescue-site-tutorial";
import type {
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
  stopSeaTurtleSession(): boolean;
  getActiveSeaTurtleSession(): SeaTurtleSessionRef | null;
  isSeaTurtleSessionActive(): boolean;
  syncSeaTurtleProjection(intent?: PointerIntent): boolean;
  beginSeaTurtlePointer(pointerId: number, captureElement: Element): boolean;
  isTrackedSeaTurtlePointer(pointerId: number): boolean;
  hasTrackedSeaTurtlePointer(): boolean;
  takeSeaTurtlePointer(pointerId: number): SeaTurtlePointerRef | null;
  clearSeaTurtlePointer(): SeaTurtlePointerRef | null;
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

  function stopSeaTurtleSession(): boolean {
    const hadSession = activeSession !== null;

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

  const controller: SeaTurtleLifecycleAppApi = Object.assign(host, {
    isSeaTurtleActive,
    getSeaTurtleSnapshot,
    getActiveSeaTurtleSession,
    isSeaTurtleSessionActive,
    startSeaTurtleSession,
    stopSeaTurtleSession,
    syncSeaTurtleProjection,
    beginSeaTurtlePointer,
    isTrackedSeaTurtlePointer,
    hasTrackedSeaTurtlePointer,
    takeSeaTurtlePointer,
    clearSeaTurtlePointer,
  });
  return controller;
}
