/**
 * Shared runtime ABI boundary types for Ocean Rescue (WP-32A).
 *
 * This module is the single type-only authority for the temporary
 * `window.OceanRescue` compatibility ABI consumed by the legacy `src/app.js`
 * orchestration hub. It composes the actual exported API types from the typed
 * canonical modules and models the mission/GUP controller facades from the
 * unchanged legacy controller behavior (`src/missions.js`, `src/gups.js`).
 *
 * The module emits no runtime JavaScript: every import is type-only and every
 * export is a type. It must never appear as a runtime module in the production
 * bundle.
 */
import type { GupCatalog, GupId } from "../gups/catalog";
import type { LaunchApi } from "../launch/launch";
import type {
  MissionCatalog,
  MissionId,
} from "../missions/catalog";
import type { ProfileApi } from "../profile/profile";
import type { StateApi } from "../state/state";
import type { TravelApi } from "../travel/travel";

export type {
  ProfileApi,
  LaunchApi,
  StateApi,
  TravelApi,
  MissionCatalog,
  GupCatalog,
  MissionId,
  GupId,
};

export interface MissionProgressionSnapshot {
  readonly selectedMissionId: MissionId | null;
  readonly unlockedMissionIds: readonly MissionId[];
  readonly completedMissionIds: readonly MissionId[];
  readonly newMissionIds: readonly MissionId[];
}

export interface MissionCompletionResult {
  readonly changed: boolean;
  readonly newlyUnlockedMissionId: MissionId | null;
}

export interface MissionsApi {
  readonly Catalog: MissionCatalog;
  readonly getSnapshot: () => MissionProgressionSnapshot;
  readonly isUnlocked: (missionId: unknown) => boolean;
  readonly selectMission: (missionId: unknown) => boolean;
  readonly completeMission: (missionId: unknown) => MissionCompletionResult;
  readonly markMissionViewed: (missionId: unknown) => boolean;
}

export interface GupSelectionSnapshot {
  readonly selectedGupId: GupId;
  readonly lastGupId: GupId;
}

export interface GupsApi {
  readonly Catalog: GupCatalog;
  readonly getSnapshot: () => GupSelectionSnapshot;
  readonly isValidGup: (gupId: unknown) => boolean;
  readonly prepareSelection: () => GupId;
  readonly selectGup: (gupId: unknown) => boolean;
  readonly confirmSelection: () => GupId;
}

export interface OceanRescueNamespace {
  Profile?: ProfileApi;
  Missions?: MissionsApi;
  Gups?: GupsApi;
  Launch?: LaunchApi;
  State?: StateApi;
  Travel?: TravelApi;
}
