/**
 * Typed canonical controller for the rescue-site transition and tutorial flow
 * (WP-33C).
 *
 * The canonical ESM lane installs this controller after WP-33A and WP-33B.
 * The legacy ordered-script lane retains the implementation in `src/app.js`
 * as the operational rollback authority.
 *
 * Pauseable timer storage/freeze/rearm/countdown remains owned by WP-33D.
 * Mission-specific rescue interaction remains owned by WP-33E through WP-33G.
 */

import type {
  GupId,
  GupsApi,
  MissionId,
  MissionsApi,
  MissionRuntimeApi,
  RescueApi,
  RescueMissionContent,
  RescueSceneApi,
  RenderRuntimeTravelApi,
  StateApi,
  TravelApi,
} from "../contracts/runtime-abi";
import type { LaunchTravelAppApi } from "./launch-travel";

export interface RescueSiteSequence {
  readonly sequenceId: number;
  readonly missionId: MissionId;
  readonly gupId: GupId;
  readonly missionContent: RescueMissionContent;
  tutorialComplete: boolean;
  tutorialSkipped: boolean;
  sceneFailed?: boolean;
  sceneFailureReason?: string;
}

export interface RescueSiteTutorialHostApi extends LaunchTravelAppApi {
  getActiveRescueSequence(): RescueSiteSequence | null;
  setActiveRescueSequence(sequence: RescueSiteSequence | null): void;
  renderRescueSiteFrame(
    canvas: HTMLCanvasElement | null,
    context: CanvasRenderingContext2D | null,
  ): void;
  startRescueInteraction(sequence: RescueSiteSequence): boolean;
  skipTutorial(): boolean;
  cancelRescueSiteRuntime(): boolean;
  handleRescueStagePointerDown(event: PointerEvent): boolean;
  cancelPausePointerInteractions(): void;
  clearPauseSensitiveHoldTimer(): void;
  shutdownActiveRescueForMenu(): void;
}

export interface RescueSiteTutorialAppApi extends RescueSiteTutorialHostApi {}

interface RescueElements {
  readonly stage: HTMLElement;
  readonly canvas: HTMLCanvasElement;
  readonly overlay: HTMLElement;
  readonly companion: HTMLElement;
  readonly situation: HTMLElement;
  readonly ready: HTMLElement;
  readonly tutorial: HTMLElement;
  readonly instruction: HTMLElement;
  readonly hand: HTMLElement;
}

interface ControllerDependencies {
  readonly State: StateApi;
  readonly Missions: MissionsApi;
  readonly Gups: GupsApi;
  readonly Travel: TravelApi;
  readonly Rescue: RescueApi;
  readonly RenderRuntime: RenderRuntimeTravelApi | null;
  readonly SeaTurtle: MissionRuntimeApi | null;
  readonly SeaTurtleScene: RescueSceneApi | null;
  readonly Crab: MissionRuntimeApi | null;
  readonly CrabScene: RescueSceneApi | null;
}

function resolveDependencies(): ControllerDependencies {
  const namespace = window.OceanRescue;
  const State = namespace?.State;
  const Missions = namespace?.Missions;
  const Gups = namespace?.Gups;
  const Travel = namespace?.Travel;
  const Rescue = namespace?.Rescue;
  if (!State || !Missions || !Gups || !Travel || !Rescue) {
    throw new Error("OceanRescue rescue-site controller dependencies are incomplete");
  }
  return {
    State,
    Missions,
    Gups,
    Travel,
    Rescue,
    RenderRuntime: namespace?.RenderRuntime ?? null,
    SeaTurtle: namespace?.SeaTurtle ?? null,
    SeaTurtleScene: namespace?.SeaTurtleScene ?? null,
    Crab: namespace?.Crab ?? null,
    CrabScene: namespace?.CrabScene ?? null,
  };
}

export function installRescueSiteTutorialController(
  host: RescueSiteTutorialHostApi,
): RescueSiteTutorialAppApi {
  const {
    State,
    Missions,
    Gups,
    Travel,
    Rescue,
    RenderRuntime,
    SeaTurtle,
    SeaTurtleScene,
    Crab,
    CrabScene,
  } = resolveDependencies();

  let rescueSequenceCounter = 0;

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

  function resolveRescueElements(): RescueElements | null {
    const stage = document.getElementById("ocean-rescue-stage");
    const canvas = host.resolveVisibleInputCanvas();
    const overlay = document.getElementById("ocean-rescue-rescue-overlay");
    const companion = document.getElementById("ocean-rescue-rescue-companion");
    const situation = document.getElementById("ocean-rescue-rescue-situation");
    const ready = document.getElementById("ocean-rescue-rescue-ready");
    const tutorial = document.getElementById("ocean-rescue-rescue-tutorial");
    const instruction = document.getElementById("ocean-rescue-rescue-instruction");
    const hand = document.getElementById("ocean-rescue-rescue-hand");
    if (
      !stage ||
      !canvas ||
      !overlay ||
      !companion ||
      !situation ||
      !ready ||
      !tutorial ||
      !instruction ||
      !hand
    ) {
      return null;
    }
    return {
      stage,
      canvas,
      overlay,
      companion,
      situation,
      ready,
      tutorial,
      instruction,
      hand,
    };
  }

  function setTutorialClass(
    container: HTMLElement,
    token: string,
    active: boolean,
  ): void {
    if (active) {
      container.classList.add(token);
    } else {
      container.classList.remove(token);
    }
  }

  function setTutorialActiveClass(container: HTMLElement, active: boolean): void {
    setTutorialClass(container, "ocean-rescue-tutorial-active", active);
  }

  function setTutorialHoldClass(container: HTMLElement, active: boolean): void {
    setTutorialClass(container, "ocean-rescue-tutorial-hold", active);
  }

  function sceneFailureReason(scene: RescueSceneApi | null): string | null {
    const diagnostics = scene?.getDiagnostics?.();
    const missingAliases = diagnostics?.missingAliases;
    if (!missingAliases || missingAliases.length === 0) {
      return null;
    }
    return missingAliases.join(", ");
  }

  function markSceneFailure(
    sequence: RescueSiteSequence,
    scene: RescueSceneApi | null,
    kind: "sea-turtle" | "crab",
    fallbackMessage: string,
    error: unknown,
  ): void {
    sequence.sceneFailed = true;
    const diagnosticReason = sceneFailureReason(scene);
    if (diagnosticReason !== null) {
      sequence.sceneFailureReason = diagnosticReason;
    }
    if (error instanceof Error && typeof error.message === "string") {
      sequence.sceneFailureReason = error.message;
    }
    const root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-rescue-input", "disabled");
      root.setAttribute(`data-${kind}-scene-failure`, "true");
    }
    const status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = fallbackMessage;
    }
  }

  function prepareAuthoredScenes(sequence: RescueSiteSequence): void {
    const renderReady = RenderRuntime?.isReady() === true;

    if (
      SeaTurtle &&
      sequence.missionId === SeaTurtle.MissionId &&
      renderReady
    ) {
      if (!SeaTurtleScene) {
        markSceneFailure(
          sequence,
          null,
          "sea-turtle",
          "This device could not start the authored sea-turtle rescue scene.",
          new Error("Sea-turtle authored scene module is unavailable"),
        );
      } else {
        try {
          SeaTurtleScene.prepare();
        } catch (error) {
          markSceneFailure(
            sequence,
            SeaTurtleScene,
            "sea-turtle",
            "This device could not start the authored sea-turtle rescue scene.",
            error,
          );
        }
      }
    } else if (SeaTurtleScene?.isMounted()) {
      SeaTurtleScene.exit();
    }

    if (Crab && sequence.missionId === Crab.MissionId && renderReady) {
      if (!CrabScene) {
        markSceneFailure(
          sequence,
          null,
          "crab",
          "This device could not start the authored crab rescue scene.",
          new Error("Crab authored scene module is unavailable"),
        );
      } else {
        try {
          CrabScene.prepare();
        } catch (error) {
          markSceneFailure(
            sequence,
            CrabScene,
            "crab",
            "This device could not start the authored crab rescue scene.",
            error,
          );
        }
      }
    } else if (CrabScene?.isMounted()) {
      CrabScene.exit();
    }
  }

  function clearSiteTransitionTimer(): void {
    host.cancelPauseableTimer("site-transition");
  }

  function clearTutorialTimer(): void {
    host.cancelPauseableTimer("tutorial");
  }

  function scheduleSiteTransitionCompletion(
    sequence: RescueSiteSequence,
    overrideDurationMs?: number,
  ): void {
    clearSiteTransitionTimer();
    const duration =
      typeof overrideDurationMs === "number"
        ? overrideDurationMs
        : Rescue.SiteTransitionMs;
    host.schedulePauseableTimer("site-transition", duration, () => {
      completeSiteTransition(sequence);
    });
  }

  function scheduleTutorialCompletion(
    sequence: RescueSiteSequence,
    overrideDurationMs?: number,
  ): void {
    clearTutorialTimer();
    const duration =
      typeof overrideDurationMs === "number"
        ? overrideDurationMs
        : Rescue.TutorialDurationMs;
    host.schedulePauseableTimer("tutorial", duration, () => {
      completeTutorial(sequence);
    });
  }

  function beginRescueArrival(
    mission: NonNullable<ReturnType<typeof missionById>>,
    gup: NonNullable<ReturnType<typeof gupById>>,
    content: RescueMissionContent,
    elements: RescueElements,
  ): boolean {
    const token = State.beginTransition(State.Phases.RESCUE_SITE_TRANSITION);
    if (token === null || !State.completeTransition(token)) {
      return false;
    }

    rescueSequenceCounter += 1;
    const sequence: RescueSiteSequence = {
      sequenceId: rescueSequenceCounter,
      missionId: mission.id,
      gupId: gup.id,
      missionContent: content,
      tutorialComplete: false,
      tutorialSkipped: false,
    };
    host.setActiveRescueSequence(sequence);
    host.stopTravelRuntime();
    prepareAuthoredScenes(sequence);

    const root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-travel-runtime", "stopped");
      root.setAttribute("data-travel-input", "disabled");
      root.setAttribute("data-rescue-sequence", "active");
      root.setAttribute("data-rescue-phase", "site-transition");
      root.setAttribute("data-rescue-input", "disabled");
      root.setAttribute("data-rescue-mission-id", mission.id);
      root.setAttribute("data-rescue-gup-id", gup.id);
    }

    elements.overlay.hidden = false;
    elements.companion.textContent = mission.companion + ":";
    elements.situation.textContent = content.situation;
    elements.ready.hidden = false;
    elements.tutorial.hidden = true;

    const status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = "Rescue site: " + content.situation;
    }

    scheduleSiteTransitionCompletion(sequence);
    host.syncPauseButton();
    return true;
  }

  function handoffTravelArrival(): boolean {
    if (host.getActiveRescueSequence() !== null) {
      return false;
    }
    if (State.getSnapshot().phase !== State.Phases.TRAVEL) {
      return false;
    }
    const travelSnapshot = Travel.getSnapshot();
    if (!travelSnapshot.active || !Rescue.hasArrived(travelSnapshot)) {
      return false;
    }
    const mission = missionById(Missions.getSnapshot().selectedMissionId);
    const content = mission === null ? null : Rescue.getMissionContent(mission.id);
    const gup = gupById(Gups.getSnapshot().lastGupId);
    const elements = resolveRescueElements();
    if (mission === null || content === null || gup === null || elements === null) {
      return false;
    }
    if (!beginRescueArrival(mission, gup, content, elements)) {
      return false;
    }
    host.renderRescueSiteFrame(
      host.resolvePaintCanvas(),
      host.resolvePaintContext(),
    );
    return true;
  }

  function completeSiteTransition(sequence: RescueSiteSequence): boolean {
    const active = host.getActiveRescueSequence();
    if (
      active === null ||
      sequence.sequenceId !== active.sequenceId ||
      State.getSnapshot().phase !== State.Phases.RESCUE_SITE_TRANSITION
    ) {
      return false;
    }
    const elements = resolveRescueElements();
    if (elements === null) {
      return false;
    }
    const token = State.beginTransition(State.Phases.RESCUE_TUTORIAL);
    if (token === null || !State.completeTransition(token)) {
      return false;
    }
    clearSiteTransitionTimer();
    elements.ready.hidden = true;
    elements.tutorial.hidden = false;
    elements.instruction.textContent = sequence.missionContent.tutorial;
    setTutorialActiveClass(elements.tutorial, true);
    setTutorialHoldClass(elements.tutorial, sequence.missionId === "crab");

    const root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-rescue-phase", "tutorial");
      root.setAttribute("data-rescue-input", "disabled");
    }
    const status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = sequence.missionContent.tutorial;
    }
    scheduleTutorialCompletion(sequence);
    return true;
  }

  function completeTutorial(sequence: RescueSiteSequence): boolean {
    const active = host.getActiveRescueSequence();
    if (
      active === null ||
      sequence.sequenceId !== active.sequenceId ||
      State.getSnapshot().phase !== State.Phases.RESCUE_TUTORIAL
    ) {
      return false;
    }
    return finalizeTutorial(sequence, false);
  }

  function skipTutorial(): boolean {
    const sequence = host.getActiveRescueSequence();
    if (
      sequence === null ||
      sequence.tutorialComplete ||
      State.getSnapshot().phase !== State.Phases.RESCUE_TUTORIAL
    ) {
      return false;
    }
    clearTutorialTimer();
    return finalizeTutorial(sequence, true);
  }

  function finalizeTutorial(
    sequence: RescueSiteSequence,
    skipped: boolean,
  ): boolean {
    const active = host.getActiveRescueSequence();
    if (
      active === null ||
      sequence.sequenceId !== active.sequenceId ||
      sequence.tutorialComplete ||
      State.getSnapshot().phase !== State.Phases.RESCUE_TUTORIAL
    ) {
      return false;
    }
    const elements = resolveRescueElements();
    if (elements === null) {
      return false;
    }
    const token = State.beginTransition(State.Phases.RESCUE_ACTIVE);
    if (token === null || !State.completeTransition(token)) {
      return false;
    }
    sequence.tutorialComplete = true;
    sequence.tutorialSkipped = skipped;
    clearTutorialTimer();
    setTutorialActiveClass(elements.tutorial, false);
    setTutorialHoldClass(elements.tutorial, false);
    elements.hand.hidden = true;

    const root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-rescue-phase", "active");
      root.setAttribute("data-rescue-input", "enabled");
      root.setAttribute(
        "data-rescue-tutorial-skipped",
        skipped ? "true" : "false",
      );
    }
    const status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = "Rescue controls ready";
    }
    host.startRescueInteraction(sequence);
    host.syncPauseButton();
    return true;
  }

  function consumeStagePointerEvent(event: PointerEvent): void {
    event.preventDefault?.();
    event.stopPropagation?.();
  }

  function handleRescueStagePointerDown(event: PointerEvent): boolean {
    const phase = State.getSnapshot().phase;
    if (host.isPauseActive() || phase === State.Phases.RESCUE_SITE_TRANSITION) {
      consumeStagePointerEvent(event);
      return true;
    }
    if (phase === State.Phases.RESCUE_TUTORIAL) {
      consumeStagePointerEvent(event);
      skipTutorial();
      return true;
    }
    return false;
  }

  function cancelRescueSiteRuntime(): boolean {
    const sequence = host.getActiveRescueSequence();
    clearSiteTransitionTimer();
    clearTutorialTimer();
    host.setActiveRescueSequence(null);
    if (SeaTurtleScene?.isMounted()) {
      SeaTurtleScene.exit();
    }
    if (CrabScene?.isMounted()) {
      CrabScene.exit();
    }
    const elements = resolveRescueElements();
    if (elements) {
      setTutorialActiveClass(elements.tutorial, false);
      setTutorialHoldClass(elements.tutorial, false);
      elements.hand.hidden = true;
    }
    return sequence !== null;
  }

  function cancelPausePointerInteractions(): void {
    // Pointer capture and drag cancellation are handled by WP-33D's
    // cancelPausePointerInteractions which delegates to each mission's
    // pointer state via the legacy closure. This bridge exists for the
    // typed controller boundary; the actual cleanup runs through the
    // legacy App.cancelPausePointerInteractions path.
  }

  function clearPauseSensitiveHoldTimer(): void {
    // Crab hold timer cleanup is owned by WP-33F. This bridge is a no-op
    // placeholder for the typed controller boundary.
  }

  function shutdownActiveRescueForMenu(): void {
    const sequence = host.getActiveRescueSequence();
    clearSiteTransitionTimer();
    clearTutorialTimer();
    host.setActiveRescueSequence(null);
    if (SeaTurtleScene?.isMounted()) {
      SeaTurtleScene.exit();
    }
    if (CrabScene?.isMounted()) {
      CrabScene.exit();
    }
    const elements = resolveRescueElements();
    if (elements) {
      setTutorialActiveClass(elements.tutorial, false);
      setTutorialHoldClass(elements.tutorial, false);
      elements.hand.hidden = true;
    }
  }

  const controller = host as RescueSiteTutorialAppApi;
  controller.handoffTravelArrival = handoffTravelArrival;
  controller.skipTutorial = skipTutorial;
  controller.cancelRescueSiteRuntime = cancelRescueSiteRuntime;
  controller.handleRescueStagePointerDown = handleRescueStagePointerDown;
  return controller;
}
