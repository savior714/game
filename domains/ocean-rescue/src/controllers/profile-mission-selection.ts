/**
 * Typed canonical controller for the profile and mission-selection flow (WP-33A).
 *
 * The canonical ESM lane installs this controller over the temporary legacy
 * `OceanRescue.App` facade before DOMContentLoaded. The legacy ordered-script
 * rollback lane continues to execute `src/app.js` unchanged.
 */

import type {
  MissionId,
  MissionsApi,
  ProfileApi,
  StateApi,
} from "../contracts/runtime-abi";

export interface MissionSelectOptions {
  readonly focusMissionId?: MissionId | null;
}

export interface LegacyAppApi {
  boot(): boolean;
  renderMissionSelect(options?: unknown): boolean;
  selectMission(missionId: unknown): boolean;
  renderGupSelect(): boolean;
  selectGup(gupId: unknown): boolean;
  backToMissionSelect(): boolean;
  launchSelectedGup(): boolean;
}

export interface ProfileMissionSelectionAppApi extends LegacyAppApi {
  renderProfileChoice(): boolean;
  selectProfileAnimal(animalId: unknown): boolean;
  confirmProfileSelection(): boolean;
}

interface ControllerDependencies {
  readonly State: StateApi;
  readonly Profile: ProfileApi;
  readonly Missions: MissionsApi;
}

const boundProfileContinueButtons = new WeakSet<EventTarget>();

function resolveDependencies(): ControllerDependencies {
  const namespace = window.OceanRescue;
  const State = namespace?.State;
  const Profile = namespace?.Profile;
  const Missions = namespace?.Missions;
  if (!State || !Profile || !Missions) {
    throw new Error(
      "OceanRescue profile/mission-selection controller dependencies are incomplete",
    );
  }
  return { State, Profile, Missions };
}

function missionTitleById(
  Missions: MissionsApi,
  missionId: unknown,
): string | null {
  for (let index = 0; index < Missions.Catalog.length; index += 1) {
    const mission = Missions.Catalog[index];
    if (mission.id === missionId) {
      return mission.title;
    }
  }
  return null;
}

function readFocusMissionId(options: unknown): MissionId | null {
  if (!options || typeof options !== "object") {
    return null;
  }
  const candidate = (options as { focusMissionId?: unknown }).focusMissionId;
  return typeof candidate === "string" ? (candidate as MissionId) : null;
}

function suppressLegacyProfileContinueBinding<T>(run: () => T): T {
  const continueButton = document.getElementById(
    "ocean-rescue-profile-continue",
  );
  if (!continueButton) {
    return run();
  }
  type MutableEventTarget = {
    addEventListener: EventTarget["addEventListener"];
  };
  const target = continueButton as unknown as MutableEventTarget;
  const originalAddEventListener = target.addEventListener;
  target.addEventListener = function (
    type: string,
    callback: EventListenerOrEventListenerObject | null,
    options?: boolean | AddEventListenerOptions,
  ): void {
    if (type === "click") {
      return;
    }
    originalAddEventListener.call(continueButton, type, callback, options);
  };
  try {
    return run();
  } finally {
    target.addEventListener = originalAddEventListener;
  }
}

export function installProfileMissionSelectionController(
  host: LegacyAppApi,
): ProfileMissionSelectionAppApi {
  const { State, Profile, Missions } = resolveDependencies();
  const originalBoot = host.boot.bind(host);

  function renderMissionSelect(options?: unknown): boolean {
    const section = document.getElementById("ocean-rescue-mission-select");
    const list = document.getElementById("ocean-rescue-mission-list");
    if (!section || !list) {
      return false;
    }
    if (State.getSnapshot().phase !== State.Phases.MISSION_SELECT) {
      return false;
    }

    list.innerHTML = "";
    const focusMissionId = readFocusMissionId(options);
    const progression = Missions.getSnapshot();
    let focusCard: HTMLButtonElement | null = null;

    for (let index = 0; index < Missions.Catalog.length; index += 1) {
      const mission = Missions.Catalog[index];
      const unlocked = progression.unlockedMissionIds.includes(mission.id);
      const completed = progression.completedMissionIds.includes(mission.id);
      const isNew = progression.newMissionIds.includes(mission.id);

      const button = document.createElement("button");
      button.type = "button";
      button.setAttribute("data-mission-id", mission.id);
      button.setAttribute(
        "aria-pressed",
        progression.selectedMissionId === mission.id ? "true" : "false",
      );
      button.disabled = !unlocked;

      const title = document.createElement("span");
      title.className = "ocean-rescue-mission-title";
      title.textContent = mission.title;

      const companion = document.createElement("span");
      companion.className = "ocean-rescue-mission-companion";
      companion.textContent = mission.companion;

      const summary = document.createElement("span");
      summary.className = "ocean-rescue-mission-summary";
      summary.textContent = mission.summary;

      const status = document.createElement("span");
      status.className = "ocean-rescue-mission-status";
      status.textContent = completed
        ? "Completed"
        : unlocked
          ? "Available"
          : "Locked";

      button.append(title, companion, summary, status);

      if (isNew) {
        const newBadge = document.createElement("span");
        newBadge.className = "ocean-rescue-mission-new";
        newBadge.textContent = "New!";
        button.appendChild(newBadge);
      }

      if (unlocked) {
        button.addEventListener("click", () => {
          selectMission(mission.id);
        });
      }
      list.appendChild(button);

      if (focusMissionId === mission.id && unlocked && isNew) {
        focusCard = button;
      }
    }

    section.style.display = "block";
    if (progression.selectedMissionId === null) {
      section.removeAttribute("data-selected-mission-id");
    } else {
      section.setAttribute(
        "data-selected-mission-id",
        progression.selectedMissionId,
      );
    }
    focusCard?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    return true;
  }

  function selectMission(missionId: unknown): boolean {
    if (State.getSnapshot().phase !== State.Phases.MISSION_SELECT) {
      return false;
    }
    if (!Missions.isUnlocked(missionId)) {
      return false;
    }
    const token = State.beginTransition(State.Phases.GUP_SELECT);
    if (token === null || !State.completeTransition(token)) {
      return false;
    }
    Missions.selectMission(missionId);
    Missions.markMissionViewed(missionId);

    const gupSection = document.getElementById("ocean-rescue-gup-select");
    if (gupSection) {
      window.OceanRescue?.Gups?.prepareSelection();
      host.renderGupSelect();
      const status = document.getElementById("ocean-rescue-status");
      if (status) {
        const title = missionTitleById(Missions, missionId);
        status.textContent =
          "Choose a GUP for " +
          (title === null ? String(missionId) : title);
      }
      return true;
    }

    const section = document.getElementById("ocean-rescue-mission-select");
    const list = document.getElementById("ocean-rescue-mission-list");
    if (section && typeof missionId === "string") {
      section.setAttribute("data-selected-mission-id", missionId);
    }
    if (list) {
      const buttons = list.querySelectorAll("button");
      for (let index = 0; index < buttons.length; index += 1) {
        buttons[index].disabled = true;
      }
    }
    const status = document.getElementById("ocean-rescue-status");
    if (status) {
      const title = missionTitleById(Missions, missionId);
      status.textContent =
        "Mission selected: " +
        (title === null ? String(missionId) : title);
    }
    return true;
  }

  function renderProfileChoice(): boolean {
    const section = document.getElementById("ocean-rescue-profile-choice");
    const playerName = document.getElementById(
      "ocean-rescue-profile-player-name",
    );
    const animalList = document.getElementById(
      "ocean-rescue-profile-animal-list",
    );
    const continueButton = document.getElementById(
      "ocean-rescue-profile-continue",
    ) as HTMLButtonElement | null;
    if (!section || !playerName || !animalList || !continueButton) {
      return false;
    }

    playerName.textContent = Profile.getSnapshot().playerName;
    animalList.innerHTML = "";
    for (let index = 0; index < Profile.Catalog.length; index += 1) {
      const animal = Profile.Catalog[index];
      const button = document.createElement("button");
      button.type = "button";
      button.setAttribute("data-profile-animal-id", animal.id);
      button.setAttribute("aria-pressed", "false");

      const name = document.createElement("span");
      name.textContent = animal.name;
      button.appendChild(name);
      button.addEventListener("click", () => {
        selectProfileAnimal(animal.id);
      });
      animalList.appendChild(button);
    }

    continueButton.disabled = true;
    if (!boundProfileContinueButtons.has(continueButton)) {
      continueButton.addEventListener("click", () => {
        confirmProfileSelection();
      });
      boundProfileContinueButtons.add(continueButton);
    }
    section.style.display = "block";
    const missionSection = document.getElementById(
      "ocean-rescue-mission-select",
    );
    if (missionSection) {
      missionSection.style.display = "none";
    }
    return true;
  }

  function selectProfileAnimal(animalId: unknown): boolean {
    if (State.getSnapshot().phase !== State.Phases.PROFILE_CHOICE) {
      return false;
    }
    if (!Profile.selectAnimal(animalId)) {
      return false;
    }
    const animalList = document.getElementById(
      "ocean-rescue-profile-animal-list",
    );
    if (animalList) {
      const buttons = animalList.querySelectorAll("button");
      for (let index = 0; index < buttons.length; index += 1) {
        const id = buttons[index].getAttribute("data-profile-animal-id");
        buttons[index].setAttribute(
          "aria-pressed",
          id === animalId ? "true" : "false",
        );
      }
    }
    const continueButton = document.getElementById(
      "ocean-rescue-profile-continue",
    ) as HTMLButtonElement | null;
    if (continueButton) {
      continueButton.disabled = false;
    }
    return true;
  }

  function confirmProfileSelection(): boolean {
    if (State.getSnapshot().phase !== State.Phases.PROFILE_CHOICE) {
      return false;
    }
    if (!Profile.confirmSelection()) {
      return false;
    }
    const token = State.beginTransition(State.Phases.MISSION_SELECT);
    if (token === null || !State.completeTransition(token)) {
      return false;
    }
    const section = document.getElementById("ocean-rescue-profile-choice");
    if (section) {
      section.style.display = "none";
    }
    const missionSection = document.getElementById(
      "ocean-rescue-mission-select",
    );
    const missionList = document.getElementById("ocean-rescue-mission-list");
    if (missionSection && missionList) {
      missionSection.style.display = "block";
      renderMissionSelect();
    }
    return true;
  }

  function boot(): boolean {
    const booted = suppressLegacyProfileContinueBinding(originalBoot);
    if (!booted) {
      return false;
    }
    const phase = State.getSnapshot().phase;
    if (phase === State.Phases.PROFILE_CHOICE) {
      renderProfileChoice();
    } else if (phase === State.Phases.MISSION_SELECT) {
      const profileSection = document.getElementById(
        "ocean-rescue-profile-choice",
      );
      if (profileSection) {
        profileSection.style.display = "none";
      }
      const missionSection = document.getElementById(
        "ocean-rescue-mission-select",
      );
      if (missionSection) {
        missionSection.style.display = "block";
      }
      renderMissionSelect();
    }
    return true;
  }

  const controller = host as ProfileMissionSelectionAppApi;
  controller.boot = boot;
  controller.renderMissionSelect = renderMissionSelect;
  controller.selectMission = selectMission;
  controller.renderProfileChoice = renderProfileChoice;
  controller.selectProfileAnimal = selectProfileAnimal;
  controller.confirmProfileSelection = confirmProfileSelection;
  return controller;
}
