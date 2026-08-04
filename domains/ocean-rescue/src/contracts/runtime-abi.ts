/**
 * Shared runtime ABI boundary types for Ocean Rescue (WP-32A/WP-33B).
 * This module is type-only and must emit no runtime JavaScript.
 */
import type { GupCatalog, GupId } from "../gups/catalog";
import type { LaunchApi } from "../launch/launch";
import type { MissionCatalog, MissionId } from "../missions/catalog";
import type {
  LogicalPoint,
  PointerInputApi,
  RenderCoordinateMapperApi,
  RenderMappedPoint,
  PointerIntent,
} from "./pointer-input";
import type { ProfileApi } from "../profile/profile";
import type { StateApi } from "../state/state";
import type { TravelApi, TravelSnapshot } from "../travel/travel";

export type {
  ProfileApi,
  LaunchApi,
  StateApi,
  TravelApi,
  TravelSnapshot,
  MissionCatalog,
  GupCatalog,
  MissionId,
  GupId,
  LogicalPoint,
  RenderMappedPoint,
  RenderCoordinateMapperApi,
  PointerIntent,
  PointerInputApi,
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

export interface TerrainSnapshot {
  readonly active: boolean;
  readonly missionId: MissionId | null;
  readonly forwardSpeedMultiplier: number;
}

export interface TerrainApi {
  readonly getSnapshot: () => TerrainSnapshot;
  readonly start: (missionId: unknown) => boolean;
  readonly stop: () => boolean;
  readonly step: (deltaMs: unknown, travelSnapshot: unknown) => boolean;
}

export interface RescueApi {
  readonly ArrivalDistance: number;
  readonly hasArrived: (travelSnapshot: unknown) => boolean;
}

export interface TravelSceneApi {
  readonly prepare: () => boolean;
  readonly activate: () => boolean;
  readonly sync: (travelSnapshot: unknown, terrainSnapshot: unknown) => boolean;
  readonly isMounted: () => boolean;
  readonly exit: () => void;
}

export interface RenderRuntimeTravelApi extends RenderCoordinateMapperApi {
  readonly setLegacyBridgeVisible: (visible: boolean) => void;
  readonly getLegacyCanvas: () => HTMLCanvasElement | null;
  readonly getLegacyContext: () => CanvasRenderingContext2D | null;
}

export type TravelProgressResult =
  | Readonly<{ valid: false }>
  | Readonly<{
      valid: true;
      percent: number;
      distance: number;
      arrivalDistance: number;
    }>;

export interface OceanRescueNamespace {
  Profile?: ProfileApi;
  Missions?: MissionsApi;
  Gups?: GupsApi;
  Launch?: LaunchApi;
  State?: StateApi;
  Travel?: TravelApi;
  Terrain?: TerrainApi;
  Rescue?: RescueApi;
  TravelScene?: TravelSceneApi;
  RenderRuntime?: RenderRuntimeTravelApi;
  PointerInput?: PointerInputApi;
  TravelProgress?: Readonly<{
    compute: (travelSnapshot: unknown) => TravelProgressResult;
  }>;
}
