/**
 * Typed canonical controller for the GUP-selection, launch, and travel flow
 * (WP-33B).
 *
 * The canonical ESM lane installs this controller after the WP-33A
 * profile/mission controller. The legacy ordered-script lane keeps the
 * implementation in `src/app.js` as its rollback authority.
 *
 * Pause/timer infrastructure remains owned by WP-33D through narrow host
 * bridges. Rescue-site orchestration remains owned by WP-33C through one
 * arrival-handoff bridge.
 */

import type {
  GupId,
  GupsApi,
  LaunchApi,
  MissionId,
  MissionsApi,
  PointerInputApi,
  RescueApi,
  StateApi,
  TerrainApi,
  TravelApi,
  TravelProgressResult,
  TravelSceneApi,
  RenderRuntimeTravelApi,
} from "../contracts/runtime-abi";
import type { ProfileMissionSelectionAppApi } from "./profile-mission-selection";

export type PauseableTimerOwner =
  | "launch"
  | "goal-banner"
  | "site-transition"
  | "tutorial";

export interface LaunchTravelHostApi extends ProfileMissionSelectionAppApi {
  schedulePauseableTimer(
    owner: PauseableTimerOwner,
    durationMs: number,
    callback: () => void,
  ): number | null;
  cancelPauseableTimer(owner: PauseableTimerOwner): void;
  isPauseActive(): boolean;
  syncPauseButton(): void;
  handoffTravelArrival(): boolean;
  resolveVisibleInputCanvas(): HTMLCanvasElement | null;
  resolvePaintCanvas(): HTMLCanvasElement | null;
  resolvePaintContext(): CanvasRenderingContext2D | null;
  skipLaunch(): boolean;
  cancelLaunchRuntime(): boolean;
  pauseTravelRuntime(): boolean;
  resumeTravelRuntime(): boolean;
  stopTravelRuntime(): boolean;
}

export interface LaunchTravelAppApi extends LaunchTravelHostApi {
  computeTravelProgress(travelSnapshot: unknown): TravelProgressResult;
}

interface ControllerDependencies {
  readonly State: StateApi;
  readonly Missions: MissionsApi;
  readonly Gups: GupsApi;
  readonly Launch: LaunchApi;
  readonly Travel: TravelApi;
  readonly PointerInput: PointerInputApi;
  readonly Rescue: RescueApi;
  readonly Terrain: TerrainApi | null;
  readonly RenderRuntime: RenderRuntimeTravelApi | null;
  readonly TravelScene: TravelSceneApi | null;
}

interface LaunchSequence {
  readonly sequenceId: number;
  readonly missionId: MissionId;
  readonly gupId: GupId;
  readonly missionContent: {
    readonly briefing: string;
    readonly goal: string;
  };
}

interface LaunchElements {
  readonly launchSection: HTMLElement;
  readonly gupName: HTMLElement;
  readonly companion: HTMLElement;
  readonly briefing: HTMLElement;
  readonly goalBanner: HTMLElement;
}

interface TravelProgressElements {
  readonly root: HTMLElement;
  readonly bar: HTMLProgressElement;
  readonly value: HTMLElement;
}

function resolveDependencies(): ControllerDependencies {
  const namespace = window.OceanRescue;
  const State = namespace?.State;
  const Missions = namespace?.Missions;
  const Gups = namespace?.Gups;
  const Launch = namespace?.Launch;
  const Travel = namespace?.Travel;
  const PointerInput = namespace?.PointerInput;
  const Rescue = namespace?.Rescue;
  if (!State || !Missions || !Gups || !Launch || !Travel || !PointerInput || !Rescue) {
    throw new Error("OceanRescue launch/travel controller dependencies are incomplete");
  }
  return {
    State,
    Missions,
    Gups,
    Launch,
    Travel,
    PointerInput,
    Rescue,
    Terrain: namespace?.Terrain ?? null,
    RenderRuntime: namespace?.RenderRuntime ?? null,
    TravelScene: namespace?.TravelScene ?? null,
  };
}

function finiteNumber(value: unknown): value is number {
  return typeof value === "number" && isFinite(value);
}

export function installLaunchTravelController(
  host: LaunchTravelHostApi,
): LaunchTravelAppApi {
  const {
    State,
    Missions,
    Gups,
    Launch,
    Travel,
    PointerInput,
    Rescue,
    Terrain,
    RenderRuntime,
    TravelScene,
  } = resolveDependencies();

  let launchSequenceCounter = 0;
  let activeLaunchSequence: LaunchSequence | null = null;
  let goalSequenceId: number | null = null;

  let travelRunIdCounter = 0;
  let activeTravelRunId: number | null = null;
  let travelFrameId: number | null = null;
  let travelLastTimestamp: number | null = null;
  let travelCanvas: HTMLCanvasElement | null = null;

  let pointerActive = false;
  let pointerId: number | null = null;
  let pointerStartClientY: number | null = null;
  let pointerStartStageY: number | null = null;
  let pointerDragging = false;

  const boundTravelCanvases = new WeakSet<HTMLCanvasElement>();

  function missionById(missionId: unknown) {
    for (let index = 0; index < Missions.Catalog.length; index += 1) {
      const mission = Missions.Catalog[index];
      if (mission.id === missionId) {
        return mission;
      }
    }
    return null;
  }

  function gupById(gupId: unknown) {
    for (let index = 0; index < Gups.Catalog.length; index += 1) {
      const gup = Gups.Catalog[index];
      if (gup.id === gupId) {
        return gup;
      }
    }
    return null;
  }

  function renderGupSelect(): boolean {
    if (State.getSnapshot().phase !== State.Phases.GUP_SELECT) {
      return false;
    }
    const mission = missionById(Missions.getSnapshot().selectedMissionId);
    if (mission === null) {
      return false;
    }
    const section = document.getElementById("ocean-rescue-gup-select");
    const list = document.getElementById("ocean-rescue-gup-list");
    if (!section || !list) {
      return false;
    }
    list.innerHTML = "";
    const gupSnapshot = Gups.getSnapshot();
    for (let index = 0; index < Gups.Catalog.length; index += 1) {
      const gup = Gups.Catalog[index];
      const button = document.createElement("button");
      button.type = "button";
      button.setAttribute("data-gup-id", gup.id);
      button.setAttribute(
        "aria-pressed",
        gup.id === gupSnapshot.selectedGupId ? "true" : "false",
      );
      button.disabled = false;

      const name = document.createElement("span");
      name.className = "ocean-rescue-gup-name";
      name.textContent = gup.name;
      const description = document.createElement("span");
      description.className = "ocean-rescue-gup-description";
      description.textContent = gup.description;
      button.append(name, description);
      button.addEventListener("click", () => {
        selectGup(gup.id);
      });
      list.appendChild(button);
    }
    const missionSection = document.getElementById("ocean-rescue-mission-select");
    if (missionSection) {
      missionSection.style.display = "none";
    }
    const missionText = document.getElementById("ocean-rescue-gup-mission");
    if (missionText) {
      missionText.textContent = "Mission: " + mission.title;
    }
    section.hidden = false;
    return true;
  }

  function selectGup(gupId: unknown): boolean {
    if (State.getSnapshot().phase !== State.Phases.GUP_SELECT) {
      return false;
    }
    if (!Gups.selectGup(gupId)) {
      return false;
    }
    const gup = gupById(gupId);
    if (gup === null) {
      return false;
    }
    const section = document.getElementById("ocean-rescue-gup-select");
    const list = document.getElementById("ocean-rescue-gup-list");
    if (section && typeof gupId === "string") {
      section.setAttribute("data-selected-gup-id", gupId);
    }
    if (list) {
      const buttons = list.querySelectorAll("button");
      for (let index = 0; index < buttons.length; index += 1) {
        const id = buttons[index].getAttribute("data-gup-id");
        buttons[index].setAttribute(
          "aria-pressed",
          id === gupId ? "true" : "false",
        );
      }
    }
    const launch = document.getElementById(
      "ocean-rescue-gup-launch",
    ) as HTMLButtonElement | null;
    if (launch) {
      launch.disabled = false;
    }
    const status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = "Selected GUP: " + gup.name;
    }
    return true;
  }

  function backToMissionSelect(): boolean {
    if (State.getSnapshot().phase !== State.Phases.GUP_SELECT) {
      return false;
    }
    const token = State.beginTransition(State.Phases.MISSION_SELECT);
    if (token === null || !State.completeTransition(token)) {
      return false;
    }
    const gupSection = document.getElementById("ocean-rescue-gup-select");
    if (gupSection) {
      gupSection.hidden = true;
      gupSection.removeAttribute("data-selected-gup-id");
    }
    const root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.removeAttribute("data-launch-mission-id");
      root.removeAttribute("data-launch-gup-id");
      root.removeAttribute("data-launch-ready");
    }
    const status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = "Choose a mission";
    }
    host.renderMissionSelect();
    return true;
  }

  function resolveLaunchElements(): LaunchElements | null {
    const launchSection = document.getElementById("ocean-rescue-launch");
    const gupName = document.getElementById("ocean-rescue-launch-gup-name");
    const companion = document.getElementById(
      "ocean-rescue-launch-companion",
    );
    const briefing = document.getElementById("ocean-rescue-launch-briefing");
    const goalBanner = document.getElementById("ocean-rescue-goal-banner");
    if (!launchSection || !gupName || !companion || !briefing || !goalBanner) {
      return null;
    }
    return { launchSection, gupName, companion, briefing, goalBanner };
  }

  function setLaunchActiveClass(
    launchSection: HTMLElement,
    active: boolean,
  ): void {
    if (active) {
      launchSection.classList.add("ocean-rescue-launch-active");
    } else {
      launchSection.classList.remove("ocean-rescue-launch-active");
    }
  }

  function clearLaunchTimer(): void {
    host.cancelPauseableTimer("launch");
  }

  function clearGoalTimer(): void {
    host.cancelPauseableTimer("goal-banner");
    goalSequenceId = null;
  }

  function clearGoalBanner(goalBanner: HTMLElement | null): void {
    if (!goalBanner) {
      return;
    }
    goalBanner.hidden = true;
    goalBanner.textContent = "";
  }

  function scheduleLaunchCompletion(
    sequence: LaunchSequence,
    overrideDurationMs?: number,
  ): void {
    clearLaunchTimer();
    const duration =
      typeof overrideDurationMs === "number"
        ? overrideDurationMs
        : Launch.DurationMs;
    host.schedulePauseableTimer("launch", duration, () => {
      completeLaunchPresentation(sequence);
    });
  }

  function startLaunchPresentation(
    mission: NonNullable<ReturnType<typeof missionById>>,
    gup: NonNullable<ReturnType<typeof gupById>>,
    content: NonNullable<ReturnType<LaunchApi["getMissionContent"]>>,
    elements: LaunchElements,
  ): void {
    launchSequenceCounter += 1;
    const sequence: LaunchSequence = {
      sequenceId: launchSequenceCounter,
      missionId: mission.id,
      gupId: gup.id,
      missionContent: content,
    };
    activeLaunchSequence = sequence;
    clearGoalTimer();

    const gupSection = document.getElementById("ocean-rescue-gup-select");
    if (gupSection) {
      gupSection.hidden = true;
    }
    clearGoalBanner(elements.goalBanner);
    elements.gupName.textContent = gup.name;
    elements.companion.textContent = mission.companion + ":";
    elements.briefing.textContent = content.briefing;
    elements.launchSection.hidden = false;
    setLaunchActiveClass(elements.launchSection, true);

    const root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-launch-sequence", "active");
      root.setAttribute("data-launch-skipped", "false");
    }
    const status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = content.briefing;
    }
    scheduleLaunchCompletion(sequence);
  }

  function launchSelectedGup(): boolean {
    if (State.getSnapshot().phase !== State.Phases.GUP_SELECT) {
      return false;
    }
    const mission = missionById(Missions.getSnapshot().selectedMissionId);
    if (mission === null) {
      return false;
    }
    const gup = gupById(Gups.getSnapshot().selectedGupId);
    if (gup === null) {
      return false;
    }
    const token = State.beginTransition(State.Phases.LAUNCH);
    if (token === null || !State.completeTransition(token)) {
      return false;
    }
    Gups.confirmSelection();

    const list = document.getElementById("ocean-rescue-gup-list");
    if (list) {
      const buttons = list.querySelectorAll("button");
      for (let index = 0; index < buttons.length; index += 1) {
        (buttons[index] as HTMLButtonElement).disabled = true;
      }
    }
    const back = document.getElementById(
      "ocean-rescue-gup-back",
    ) as HTMLButtonElement | null;
    const launch = document.getElementById(
      "ocean-rescue-gup-launch",
    ) as HTMLButtonElement | null;
    if (back) {
      back.disabled = true;
    }
    if (launch) {
      launch.disabled = true;
    }
    const root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-launch-mission-id", mission.id);
      root.setAttribute("data-launch-gup-id", gup.id);
      root.setAttribute("data-launch-ready", "true");
    }
    const status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = "Launch ready: " + gup.name + " — " + mission.title;
    }
    const elements = resolveLaunchElements();
    const content = Launch.getMissionContent(mission.id);
    if (elements !== null && content !== null) {
      startLaunchPresentation(mission, gup, content, elements);
    }
    return true;
  }

  function showGoalBanner(
    goalBanner: HTMLElement,
    sequence: LaunchSequence,
    overrideDurationMs?: number,
  ): void {
    clearGoalTimer();
    goalSequenceId = sequence.sequenceId;
    goalBanner.hidden = false;
    goalBanner.textContent = sequence.missionContent.goal;
    const duration =
      typeof overrideDurationMs === "number"
        ? overrideDurationMs
        : Launch.GoalDurationMs;
    host.schedulePauseableTimer("goal-banner", duration, () => {
      hideGoalBanner(sequence.sequenceId);
    });
  }

  function hideGoalBanner(sequenceId: number): void {
    if (goalSequenceId !== sequenceId || activeLaunchSequence !== null) {
      return;
    }
    const goalBanner = document.getElementById("ocean-rescue-goal-banner");
    if (!goalBanner) {
      return;
    }
    goalBanner.hidden = true;
    goalBanner.textContent = "";
    goalSequenceId = null;
  }

  function completeLaunchPresentation(sequence: LaunchSequence): boolean {
    if (
      activeLaunchSequence === null ||
      sequence.sequenceId !== activeLaunchSequence.sequenceId ||
      State.getSnapshot().phase !== State.Phases.LAUNCH
    ) {
      return false;
    }
    return finalizeLaunch(sequence, false);
  }

  function skipLaunch(): boolean {
    const sequence = activeLaunchSequence;
    if (sequence === null || State.getSnapshot().phase !== State.Phases.LAUNCH) {
      return false;
    }
    clearLaunchTimer();
    return finalizeLaunch(sequence, true);
  }

  function cancelLaunchRuntime(): boolean {
    const changed = activeLaunchSequence !== null;
    activeLaunchSequence = null;
    clearLaunchTimer();
    clearGoalTimer();
    return changed;
  }

  function startTerrainRuntime(): void {
    if (!Terrain) {
      return;
    }
    const root = document.getElementById("ocean-rescue-root");
    let missionId: unknown = root?.getAttribute("data-travel-mission-id");
    if (typeof missionId !== "string") {
      missionId = Missions.getSnapshot().selectedMissionId;
    }
    if (typeof missionId === "string") {
      Terrain.start(missionId);
    }
  }

  function resolveTravelProgressElements(): TravelProgressElements | null {
    const root = document.getElementById("ocean-rescue-travel-progress");
    const bar = document.getElementById(
      "ocean-rescue-travel-progress-bar",
    ) as HTMLProgressElement | null;
    const value = document.getElementById(
      "ocean-rescue-travel-progress-value",
    );
    if (!root || !bar || !value) {
      return null;
    }
    return { root, bar, value };
  }

  function computeTravelProgress(travelSnapshot: unknown): TravelProgressResult {
    const arrivalDistance = Rescue.ArrivalDistance;
    if (!finiteNumber(arrivalDistance) || arrivalDistance <= 0) {
      return { valid: false };
    }
    if (!travelSnapshot || typeof travelSnapshot !== "object") {
      return { valid: false };
    }
    const distance = (travelSnapshot as { distance?: unknown }).distance;
    if (!finiteNumber(distance) || distance < 0) {
      return { valid: false };
    }
    let ratio = distance / arrivalDistance;
    if (ratio < 0) {
      ratio = 0;
    }
    if (ratio > 1) {
      ratio = 1;
    }
    return {
      valid: true,
      percent: Math.round(ratio * 100),
      distance,
      arrivalDistance,
    };
  }

  function setTravelProgressDiagnostics(
    root: HTMLElement,
    state: "hidden" | "invalid" | "active",
    progress: TravelProgressResult,
  ): void {
    root.setAttribute("data-travel-progress-state", state);
    if (progress.valid) {
      root.setAttribute("data-travel-progress-percent", String(progress.percent));
      root.setAttribute("data-travel-progress-distance", String(progress.distance));
      root.setAttribute(
        "data-travel-progress-arrival-distance",
        String(progress.arrivalDistance),
      );
    } else {
      root.removeAttribute("data-travel-progress-percent");
      root.removeAttribute("data-travel-progress-distance");
      root.removeAttribute("data-travel-progress-arrival-distance");
    }
  }

  function hideTravelProgress(): boolean {
    const elements = resolveTravelProgressElements();
    if (elements === null) {
      return false;
    }
    elements.root.hidden = true;
    elements.bar.max = 100;
    elements.bar.value = 0;
    elements.value.textContent = "0%";
    setTravelProgressDiagnostics(elements.root, "hidden", { valid: false });
    return true;
  }

  function syncTravelProgress(travelSnapshot: unknown): boolean {
    const elements = resolveTravelProgressElements();
    if (elements === null) {
      return false;
    }
    if (State.getSnapshot().phase !== State.Phases.TRAVEL) {
      hideTravelProgress();
      return false;
    }
    const progress = computeTravelProgress(travelSnapshot);
    if (!progress.valid) {
      elements.root.hidden = true;
      setTravelProgressDiagnostics(elements.root, "invalid", progress);
      return false;
    }
    elements.root.hidden = false;
    elements.bar.max = 100;
    elements.bar.value = progress.percent;
    elements.value.textContent = String(progress.percent) + "%";
    setTravelProgressDiagnostics(elements.root, "active", progress);
    return true;
  }

  function resetPointerGesture(): void {
    pointerActive = false;
    pointerId = null;
    pointerStartClientY = null;
    pointerStartStageY = null;
    pointerDragging = false;
  }

  function acceptPointerEvent(event: PointerEvent): boolean {
    if (host.isPauseActive()) {
      return false;
    }
    if (State.getSnapshot().phase !== State.Phases.TRAVEL) {
      return false;
    }
    if (!Travel.getSnapshot().active) {
      return false;
    }
    if (event.isPrimary === false) {
      return false;
    }
    return event.button !== 0 ? false : true;
  }

  function mapClientYToStage(event: PointerEvent): number | null {
    return PointerInput.mapTravelStageY(event, travelCanvas);
  }

  function onPointerDown(event: PointerEvent): void {
    if (!acceptPointerEvent(event) || pointerActive) {
      return;
    }
    const stageY = mapClientYToStage(event);
    if (stageY === null) {
      return;
    }
    pointerActive = true;
    pointerId = event.pointerId;
    pointerStartClientY = event.clientY;
    pointerStartStageY = stageY;
    pointerDragging = false;
    travelCanvas?.setPointerCapture(event.pointerId);
    event.preventDefault();
  }

  function onPointerMove(event: PointerEvent): void {
    if (!acceptPointerEvent(event) || !pointerActive || event.pointerId !== pointerId) {
      return;
    }
    const stageY = mapClientYToStage(event);
    if (stageY === null) {
      return;
    }
    if (!pointerDragging) {
      if (
        pointerStartClientY === null ||
        pointerStartStageY === null ||
        Math.abs(event.clientY - pointerStartClientY) < 8
      ) {
        return;
      }
      pointerDragging = true;
      Travel.beginDrag(pointerId, pointerStartStageY);
      Travel.moveDrag(pointerId, stageY);
    } else {
      Travel.moveDrag(pointerId, stageY);
    }
    event.preventDefault();
  }

  function onPointerUp(event: PointerEvent): void {
    if (!acceptPointerEvent(event) || !pointerActive || event.pointerId !== pointerId) {
      return;
    }
    const stageY = mapClientYToStage(event);
    if (pointerDragging) {
      if (stageY !== null) {
        Travel.moveDrag(pointerId, stageY);
      }
      Travel.endDrag(pointerId);
    } else if (stageY !== null) {
      Travel.tapTo(stageY);
    }
    resetPointerGesture();
    travelCanvas?.releasePointerCapture(event.pointerId);
    event.preventDefault();
  }

  function onPointerCancel(event: PointerEvent): void {
    if (!pointerActive || event.pointerId !== pointerId) {
      return;
    }
    if (pointerDragging) {
      Travel.endDrag(pointerId);
    }
    resetPointerGesture();
  }

  function bindTravelPointerInput(canvas: HTMLCanvasElement | null): void {
    if (!canvas || boundTravelCanvases.has(canvas)) {
      return;
    }
    canvas.addEventListener("pointerdown", onPointerDown);
    canvas.addEventListener("pointermove", onPointerMove);
    canvas.addEventListener("pointerup", onPointerUp);
    canvas.addEventListener("pointercancel", onPointerCancel);
    boundTravelCanvases.add(canvas);
  }

  function shutdownActivePointer(): void {
    if (pointerActive && pointerDragging && pointerId !== null) {
      Travel.endDrag(pointerId);
    }
    if (pointerId !== null && travelCanvas) {
      try {
        travelCanvas.releasePointerCapture(pointerId);
      } catch {
        // Preserve cleanup when the browser already released capture.
      }
    }
    resetPointerGesture();
  }

  function scheduleTravelFrame(runId: number): void {
    if (typeof window.requestAnimationFrame !== "function") {
      return;
    }
    travelFrameId = window.requestAnimationFrame((timestamp) => {
      travelAnimationFrame(runId, timestamp);
    });
  }

  function travelAnimationFrame(runId: number, timestamp: number): void {
    if (runId !== activeTravelRunId) {
      return;
    }
    travelFrameId = null;
    if (host.isPauseActive()) {
      return;
    }
    if (State.getSnapshot().phase !== State.Phases.TRAVEL) {
      return;
    }
    const travel = Travel.getSnapshot();
    if (!travel.active) {
      return;
    }
    if (travelLastTimestamp !== null) {
      const deltaMs = timestamp - travelLastTimestamp;
      if (deltaMs > 0) {
        if (Terrain?.getSnapshot().active) {
          Terrain.step(deltaMs, Travel.getSnapshot());
          Travel.step(deltaMs, Terrain.getSnapshot().forwardSpeedMultiplier);
        } else {
          Travel.step(deltaMs);
        }
      }
    }
    travelLastTimestamp = timestamp;
    syncTravelProgress(Travel.getSnapshot());
    if (host.handoffTravelArrival()) {
      return;
    }
    if (TravelScene?.isMounted()) {
      TravelScene.sync(Travel.getSnapshot(), Terrain?.getSnapshot() ?? null);
    }
    scheduleTravelFrame(runId);
  }

  function startTravelRuntime(): boolean {
    if (RenderRuntime?.isReady() && TravelScene) {
      try {
        TravelScene.prepare();
        TravelScene.activate();
      } catch {
        RenderRuntime.setLegacyBridgeVisible(true);
      }
    }
    Travel.start();
    startTerrainRuntime();
    hideTravelProgress();
    syncTravelProgress(Travel.getSnapshot());
    travelRunIdCounter += 1;
    const runId = travelRunIdCounter;
    activeTravelRunId = runId;
    travelLastTimestamp = null;
    if (travelFrameId !== null) {
      window.cancelAnimationFrame(travelFrameId);
    }
    travelFrameId = null;
    travelCanvas = host.resolveVisibleInputCanvas();
    host.resolvePaintCanvas();
    bindTravelPointerInput(travelCanvas);
    scheduleTravelFrame(runId);

    const root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-travel-runtime", "active");
      root.setAttribute("data-travel-input", "enabled");
    }
    return true;
  }

  function pauseTravelRuntime(): boolean {
    const wasActive = activeTravelRunId !== null;
    if (travelFrameId !== null) {
      window.cancelAnimationFrame(travelFrameId);
    }
    travelFrameId = null;
    shutdownActivePointer();
    return wasActive;
  }

  function resumeTravelRuntime(): boolean {
    if (activeTravelRunId === null || !Travel.getSnapshot().active) {
      return false;
    }
    travelLastTimestamp = null;
    if (travelFrameId !== null) {
      window.cancelAnimationFrame(travelFrameId);
    }
    travelFrameId = null;
    scheduleTravelFrame(activeTravelRunId);
    return true;
  }

  function stopTravelRuntime(): boolean {
    const changed = activeTravelRunId !== null || Travel.getSnapshot().active;
    activeTravelRunId = null;
    if (travelFrameId !== null) {
      window.cancelAnimationFrame(travelFrameId);
    }
    travelFrameId = null;
    travelLastTimestamp = null;
    shutdownActivePointer();
    if (Travel.getSnapshot().active) {
      Travel.stop();
    }
    if (Terrain?.getSnapshot().active) {
      Terrain.stop();
    }
    if (TravelScene?.isMounted()) {
      TravelScene.exit();
    }
    hideTravelProgress();
    const root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-travel-runtime", "stopped");
      root.setAttribute("data-travel-input", "disabled");
    }
    return changed;
  }

  function finalizeLaunch(sequence: LaunchSequence, skipped: boolean): boolean {
    const token = State.beginTransition(State.Phases.TRAVEL);
    if (token === null || !State.completeTransition(token)) {
      return false;
    }
    activeLaunchSequence = null;
    clearLaunchTimer();
    const launchSection = document.getElementById("ocean-rescue-launch");
    if (launchSection) {
      launchSection.hidden = true;
      setLaunchActiveClass(launchSection, false);
    }
    const stage = document.getElementById("ocean-rescue-stage");
    if (stage) {
      stage.hidden = false;
      stage.setAttribute("aria-hidden", "false");
    }
    const goalBanner = document.getElementById("ocean-rescue-goal-banner");
    if (goalBanner) {
      showGoalBanner(goalBanner, sequence);
    }
    const root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-travel-mission-id", sequence.missionId);
      root.setAttribute("data-travel-gup-id", sequence.gupId);
      root.setAttribute("data-travel-ready", "true");
      root.setAttribute("data-launch-skipped", skipped ? "true" : "false");
      root.removeAttribute("data-launch-ready");
      root.removeAttribute("data-launch-sequence");
    }
    const status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = "Travel ready: " + sequence.missionContent.goal;
    }
    startTravelRuntime();
    host.syncPauseButton();
    return true;
  }

  const controller = host as LaunchTravelAppApi;
  controller.renderGupSelect = renderGupSelect;
  controller.selectGup = selectGup;
  controller.backToMissionSelect = backToMissionSelect;
  controller.launchSelectedGup = launchSelectedGup;
  controller.skipLaunch = skipLaunch;
  controller.cancelLaunchRuntime = cancelLaunchRuntime;
  controller.pauseTravelRuntime = pauseTravelRuntime;
  controller.resumeTravelRuntime = resumeTravelRuntime;
  controller.stopTravelRuntime = stopTravelRuntime;
  controller.computeTravelProgress = computeTravelProgress;

  const win = window as Window & {
    OceanRescue?: typeof window.OceanRescue & {
      TravelProgress?: Readonly<{
        compute: (travelSnapshot: unknown) => TravelProgressResult;
      }>;
    };
  };
  if (win.OceanRescue) {
    win.OceanRescue.TravelProgress = Object.freeze({
      compute: computeTravelProgress,
    });
  }

  return controller;
}
