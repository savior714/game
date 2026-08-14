/**
 * Typed canonical controller for pause, timer registry, and resume countdown
 * (WP-33D).
 *
 * The canonical ESM lane installs this controller after WP-33A, WP-33B, and
 * WP-33C. The legacy ordered-script lane retains the implementation in
 * `src/app.js` as the operational rollback authority.
 *
 * This controller owns:
 * - pause state (pauseActive, pauseResumeSequenceId)
 * - pauseable timer registry (register/unregister/schedule/cancel/freeze/rearm)
 * - freeze/rearm of all registered timers on pause/resume
 * - 3-2-1-Go countdown with 1000ms intervals and 700ms Go delay
 * - pause overlay/countdown UI management
 * - root data-pause-active marker
 * - pause button sync (visibility based on phase)
 * - menu return orchestration (phase transition to MISSION_SELECT)
 *
 * This controller does NOT own:
 * - sea-turtle rope lifecycle (WP-33E)
 * - crab drag/hold lifecycle (WP-33F)
 * - young-whale connect/tow lifecycle (WP-33G)
 * - mission success stage progression (WP-33H)
 * - scene rendering implementation
 * - mission-specific feedback callbacks
 *
 * Narrow host bridges for mission-specific cleanup:
 * - cancelPausePointerInteractions() — pointer capture + drag cancellation
 * - clearPauseSensitiveHoldTimer() — crab hold timer cleanup
 * - shutdownActiveRescueForMenu() — rescue interaction state shutdown
 * - cancelLaunchRuntime() — launch sequence + timer cleanup (via WP-33B)
 * - stopTravelRuntime() — travel frame loop + Travel/Terrain stop (via WP-33B)
 */

import type {
  StateApi,
  TravelApi,
  TerrainApi,
  RenderRuntimeTravelApi,
  RescueSceneApi,
  TravelSceneApi,
} from "../contracts/runtime-abi";
import type { PauseableTimerOwner } from "../contracts/runtime-abi";
import type { RescueSiteTutorialAppApi } from "./rescue-site-tutorial";

export interface PauseTimerResumeHostApi extends RescueSiteTutorialAppApi {
  cancelPausePointerInteractions(): void;
  clearPauseSensitiveHoldTimer(): void;
  shutdownActiveRescueForMenu(): void;
  cancelMissionSuccessPresentationForMenu(): void;
}

export interface PauseTimerResumeAppApi extends PauseTimerResumeHostApi {
  isPauseActive(): boolean;
  isPauseablePhase(phase: unknown): boolean;
  registerPauseableTimer(owner: PauseableTimerOwner, timerId: number | null): void;
  unregisterPauseableTimer(owner: PauseableTimerOwner): void;
  schedulePauseableTimer(
    owner: PauseableTimerOwner,
    durationMs: number,
    callback: () => void,
  ): number | null;
  cancelPauseableTimer(owner: PauseableTimerOwner): void;
  freezeAllPauseTimers(): void;
  rearmAllPauseTimers(): void;
  syncPauseButton(): void;
  setPauseRootMarkers(active: boolean): void;
  enterPause(): void;
  enterResumeCountdown(): void;
  completeResume(): void;
  exitPauseToMenu(): void;
  cancelMissionSuccessPresentationForMenu(): void;
}

interface ControllerDependencies {
  readonly State: StateApi;
  readonly Travel: TravelApi | null;
  readonly Terrain: TerrainApi | null;
  readonly RenderRuntime: RenderRuntimeTravelApi | null;
  readonly SeaTurtleScene: RescueSceneApi | null;
  readonly CrabScene: RescueSceneApi | null;
  readonly TravelScene: TravelSceneApi | null;
}

interface MutablePauseableTimerEntry {
  owner: PauseableTimerOwner;
  timerId: number | null;
  callback: (() => void) | null;
  duration: number;
  remaining: number;
}

function resolveDependencies(): ControllerDependencies {
  const namespace = window.OceanRescue;
  const State = namespace?.State;
  if (!State) {
    throw new Error("OceanRescue pause controller dependencies are incomplete");
  }
  return {
    State,
    Travel: namespace?.Travel ?? null,
    Terrain: namespace?.Terrain ?? null,
    RenderRuntime: namespace?.RenderRuntime ?? null,
    SeaTurtleScene: namespace?.SeaTurtleScene ?? null,
    CrabScene: namespace?.CrabScene ?? null,
    TravelScene: namespace?.TravelScene ?? null,
  };
}

function monotonicNowMs(): number {
  if (
    typeof window !== "undefined" &&
    window.performance &&
    typeof window.performance.now === "function"
  ) {
    return window.performance.now();
  }
  if (typeof Date !== "undefined" && typeof Date.now === "function") {
    return Date.now();
  }
  return 0;
}

const PAUSABLE_PHASES = new Set<string>([
  "LAUNCH",
  "TRAVEL",
  "RESCUE_SITE_TRANSITION",
  "RESCUE_TUTORIAL",
  "RESCUE_ACTIVE",
  "RESCUE_SUCCESS",
]);

export function installPauseTimerResumeController(
  host: PauseTimerResumeHostApi,
): PauseTimerResumeAppApi {
  const { State, Travel, Terrain, RenderRuntime, SeaTurtleScene, CrabScene, TravelScene } =
    resolveDependencies();

  let pauseActive = false;
  let pauseResumeSequenceId = 0;
  let pauseCountdownTimerId: number | null = null;

  const pauseableTimers = new Map<PauseableTimerOwner, MutablePauseableTimerEntry>();
  const pauseRemainingByOwner = new Map<PauseableTimerOwner, number>();
  const pauseSavedTimestamps = new Map<PauseableTimerOwner, number>();

  function registerPauseableTimer(
    owner: PauseableTimerOwner,
    timerId: number | null,
  ): void {
    const existing = pauseableTimers.get(owner);
    if (existing) {
      existing.timerId = timerId;
    } else {
      pauseableTimers.set(owner, {
        owner,
        timerId,
        callback: null,
        duration: 0,
        remaining: 0,
      });
    }
  }

  function unregisterPauseableTimer(owner: PauseableTimerOwner): void {
    registerPauseableTimer(owner, null);
  }

  function schedulePauseableTimer(
    owner: PauseableTimerOwner,
    durationMs: number,
    callback: () => void,
  ): number | null {
    if (typeof window.setTimeout !== "function") {
      return null;
    }
    pauseSavedTimestamps.set(owner, monotonicNowMs());
    const entry = pauseableTimers.get(owner) ?? {
      owner,
      timerId: null,
      callback: null,
      duration: 0,
      remaining: 0,
    };
    entry.callback = callback;
    entry.duration = durationMs;
    pauseableTimers.set(owner, entry);

    const id = window.setTimeout(() => {
      const current = pauseableTimers.get(owner);
      if (current) {
        current.timerId = null;
        current.callback = null;
      }
      callback();
    }, durationMs);

    registerPauseableTimer(owner, id);
    return id;
  }

  function cancelPauseableTimer(owner: PauseableTimerOwner): void {
    const entry = pauseableTimers.get(owner);
    if (!entry) {
      return;
    }
    if (entry.timerId !== null && typeof window.clearTimeout === "function") {
      window.clearTimeout(entry.timerId);
    }
    entry.timerId = null;
  }

  function freezeAllPauseTimers(): void {
    for (const [owner, entry] of pauseableTimers) {
      if (entry.timerId === null) {
        continue;
      }
      if (typeof window.clearTimeout === "function") {
        window.clearTimeout(entry.timerId);
      }
      entry.timerId = null;
      const saved = pauseSavedTimestamps.get(owner) ?? monotonicNowMs();
      const elapsed = monotonicNowMs() - saved;
      const remaining = Math.max(0, entry.duration - elapsed);
      pauseRemainingByOwner.set(owner, remaining);
    }
  }

  function rearmAllPauseTimers(): void {
    for (const [owner, remaining] of pauseRemainingByOwner) {
      if (typeof remaining !== "number" || remaining <= 0) {
        continue;
      }
      const entry = pauseableTimers.get(owner);
      if (!entry || typeof entry.callback !== "function") {
        continue;
      }
      pauseSavedTimestamps.set(owner, monotonicNowMs());
      entry.duration = remaining;
      pauseableTimers.set(owner, entry);

      const id = window.setTimeout(() => {
        const current = pauseableTimers.get(owner);
        if (current) {
          current.timerId = null;
          current.callback = null;
        }
        if (typeof entry.callback === "function") {
          entry.callback();
        }
      }, remaining);

      registerPauseableTimer(owner, id);
    }
    pauseRemainingByOwner.clear();
  }

  function isPauseActive(): boolean {
    return pauseActive;
  }

  function isPauseablePhase(phase: unknown): boolean {
    return typeof phase === "string" && PAUSABLE_PHASES.has(phase);
  }

  function syncPauseButton(): void {
    const btn = document.getElementById("ocean-rescue-pause-button");
    if (!btn) {
      return;
    }
    const snapshot = State.getSnapshot();
    if (pauseActive) {
      btn.hidden = true;
      return;
    }
    btn.hidden = !isPauseablePhase(snapshot.phase);
  }

  function setPauseRootMarkers(active: boolean): void {
    const root = document.getElementById("ocean-rescue-root");
    if (!root) {
      return;
    }
    root.setAttribute("data-pause-active", active ? "true" : "false");
  }

  function enterPause(): void {
    if (pauseActive) {
      return;
    }
    const snapshot = State.getSnapshot();
    if (!isPauseablePhase(snapshot.phase)) {
      return;
    }
    pauseActive = true;

    if (RenderRuntime?.isReady()) {
      RenderRuntime.pause();
    }
    if (SeaTurtleScene?.isMounted()) {
      SeaTurtleScene.pause();
    }
    if (CrabScene?.isMounted()) {
      CrabScene.pause();
    }

    freezeAllPauseTimers();
    host.cancelPausePointerInteractions();
    host.clearPauseSensitiveHoldTimer();

    window.OceanRescue?.Audio?.pauseSpeech?.();

    setPauseRootMarkers(true);

    const overlay = document.getElementById("ocean-rescue-pause-overlay");
    const countdown = document.getElementById("ocean-rescue-pause-countdown");
    const resumeBtn = document.getElementById("ocean-rescue-pause-resume") as HTMLButtonElement | null;
    if (overlay) {
      overlay.hidden = false;
    }
    if (countdown) {
      countdown.hidden = true;
      countdown.textContent = "";
    }
    if (resumeBtn) {
      resumeBtn.hidden = false;
      resumeBtn.disabled = false;
    }

    // Sync volume sliders with current Audio settings
    const audioSettings = window.OceanRescue?.Audio?.getSettings?.();
    if (audioSettings) {
      const soundSlider = document.getElementById("ocean-rescue-volume-sound") as HTMLInputElement | null;
      const soundVal = document.getElementById("ocean-rescue-volume-sound-val");
      const voiceSlider = document.getElementById("ocean-rescue-volume-voice") as HTMLInputElement | null;
      const voiceVal = document.getElementById("ocean-rescue-volume-voice-val");
      if (soundSlider) {
        soundSlider.value = String(audioSettings.sound);
      }
      if (soundVal) {
        soundVal.textContent = String(audioSettings.sound);
      }
      if (voiceSlider) {
        voiceSlider.value = String(audioSettings.voice);
      }
      if (voiceVal) {
        voiceVal.textContent = String(audioSettings.voice);
      }
    }

    syncPauseButton();
  }

  function enterResumeCountdown(): void {
    if (!pauseActive) {
      return;
    }
    const resumeBtn = document.getElementById("ocean-rescue-pause-resume") as HTMLButtonElement | null;
    const countdown = document.getElementById("ocean-rescue-pause-countdown");
    const menuBtn = document.getElementById("ocean-rescue-pause-menu-button") as HTMLButtonElement | null;
    if (resumeBtn) {
      resumeBtn.disabled = true;
    }
    if (menuBtn) {
      menuBtn.disabled = true;
    }
    if (countdown) {
      countdown.hidden = false;
    }
    pauseResumeSequenceId += 1;
    const seq = pauseResumeSequenceId;
    runCountdownTick(seq, 3);
  }

  function runCountdownTick(seq: number, n: number): void {
    if (seq !== pauseResumeSequenceId) {
      return;
    }
    if (!pauseActive) {
      return;
    }
    const countdown = document.getElementById("ocean-rescue-pause-countdown");
    if (n > 0) {
      if (countdown) {
        countdown.textContent = String(n);
      }
      pauseCountdownTimerId = window.setTimeout(() => {
        runCountdownTick(seq, n - 1);
      }, 1000);
    } else {
      if (countdown) {
        countdown.textContent = "Go!";
      }
      pauseCountdownTimerId = window.setTimeout(() => {
        completeResume();
      }, 700);
    }
  }

  function completeResume(): void {
    if (!pauseActive) {
      return;
    }
    pauseCountdownTimerId = null;
    pauseActive = false;

    if (RenderRuntime?.isReady()) {
      RenderRuntime.resume();
    }
    if (SeaTurtleScene?.isMounted()) {
      SeaTurtleScene.resume();
    }
    if (CrabScene?.isMounted()) {
      CrabScene.resume();
    }

    const overlay = document.getElementById("ocean-rescue-pause-overlay");
    if (overlay) {
      overlay.hidden = true;
    }
    setPauseRootMarkers(false);

    window.OceanRescue?.Audio?.resumeSpeech?.();

    rearmAllPauseTimers();
    syncPauseButton();

    const snapshot = State.getSnapshot();
    if (snapshot.phase === "TRAVEL") {
      host.resumeTravelRuntime();
    }
  }

  function exitPauseToMenu(): void {
    if (!pauseActive) {
      return;
    }
    pauseActive = false;

    window.OceanRescue?.Audio?.cancelSpeech?.();

    if (RenderRuntime?.isReady()) {
      RenderRuntime.resume();
    }
    if (SeaTurtleScene?.isMounted()) {
      SeaTurtleScene.exit();
    }
    if (pauseCountdownTimerId !== null && typeof window.clearTimeout === "function") {
      window.clearTimeout(pauseCountdownTimerId);
    }
    pauseCountdownTimerId = null;

    const overlay = document.getElementById("ocean-rescue-pause-overlay");
    if (overlay) {
      overlay.hidden = true;
    }
    setPauseRootMarkers(false);
    syncPauseButton();

    const snapshot = State.getSnapshot();
    if (snapshot.phase === "TRAVEL") {
      host.stopTravelRuntime();
      host.cancelLaunchRuntime?.();
    } else if (snapshot.phase === "RESCUE_SUCCESS") {
      host.cancelMissionSuccessPresentationForMenu();
      host.shutdownActiveRescueForMenu();
    } else if (
      snapshot.phase === "RESCUE_SITE_TRANSITION" ||
      snapshot.phase === "RESCUE_TUTORIAL" ||
      snapshot.phase === "RESCUE_ACTIVE"
    ) {
      host.shutdownActiveRescueForMenu();
    } else if (snapshot.phase === "LAUNCH") {
      host.cancelLaunchRuntime?.();
    }

    const root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.removeAttribute("data-travel-runtime");
      root.removeAttribute("data-travel-input");
      root.removeAttribute("data-rescue-sequence");
      root.removeAttribute("data-rescue-phase");
      root.removeAttribute("data-rescue-input");
      root.removeAttribute("data-rescue-mission-id");
      root.removeAttribute("data-rescue-gup-id");
      root.removeAttribute("data-sea-turtle-active");
      root.removeAttribute("data-crab-active");
      root.removeAttribute("data-young-whale-active");
    }

    const stage = document.getElementById("ocean-rescue-stage");
    if (stage) {
      stage.hidden = true;
    }
    const launchSection = document.getElementById("ocean-rescue-launch");
    if (launchSection) {
      launchSection.hidden = true;
      launchSection.classList.remove("ocean-rescue-launch-active");
    }
    const rescueOverlay = document.getElementById("ocean-rescue-rescue-overlay");
    if (rescueOverlay) {
      rescueOverlay.hidden = true;
    }
    const missionSuccess = document.getElementById("ocean-rescue-mission-success");
    if (missionSuccess) {
      missionSuccess.hidden = true;
    }
    const goalBanner = document.getElementById("ocean-rescue-goal-banner");
    if (goalBanner) {
      goalBanner.hidden = true;
      goalBanner.textContent = "";
    }
    const gupSection = document.getElementById("ocean-rescue-gup-select");
    if (gupSection) {
      gupSection.hidden = true;
    }

    const travelProgress = document.getElementById("ocean-rescue-travel-progress");
    if (travelProgress) {
      travelProgress.hidden = true;
    }

    State.forcePhase(State.Phases.MISSION_SELECT);
    host.renderMissionSelect();

    const status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = "Choose a mission";
    }
  }

  const controller = host as unknown as PauseTimerResumeAppApi;
  controller.isPauseActive = isPauseActive;
  controller.isPauseablePhase = isPauseablePhase;
  controller.registerPauseableTimer = registerPauseableTimer;
  controller.unregisterPauseableTimer = unregisterPauseableTimer;
  controller.schedulePauseableTimer = schedulePauseableTimer;
  controller.cancelPauseableTimer = cancelPauseableTimer;
  controller.freezeAllPauseTimers = freezeAllPauseTimers;
  controller.rearmAllPauseTimers = rearmAllPauseTimers;
  controller.syncPauseButton = syncPauseButton;
  controller.setPauseRootMarkers = setPauseRootMarkers;
  controller.enterPause = enterPause;
  controller.enterResumeCountdown = enterResumeCountdown;
  controller.completeResume = completeResume;
  controller.exitPauseToMenu = exitPauseToMenu;
  controller.cancelMissionSuccessPresentationForMenu = () => {
    host.cancelMissionSuccessPresentationForMenu();
  };
  controller.cancelPausePointerInteractions = host.cancelPausePointerInteractions;
  controller.clearPauseSensitiveHoldTimer = host.clearPauseSensitiveHoldTimer;
  controller.shutdownActiveRescueForMenu = host.shutdownActiveRescueForMenu;

  return controller;
}
