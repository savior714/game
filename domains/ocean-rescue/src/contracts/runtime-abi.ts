/**
 * Shared runtime ABI boundary types for Ocean Rescue (WP-32A/WP-33C/WP-33E-0).
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

export interface RescueMissionContent {
  readonly missionId: MissionId;
  readonly targetLabel: string;
  readonly toolLabel: string;
  readonly situation: string;
  readonly tutorial: string;
}

export interface RescueApi {
  readonly ArrivalDistance: number;
  readonly SiteTransitionMs: number;
  readonly TutorialDurationMs: number;
  readonly getMissionContent: (
    missionId: unknown,
  ) => RescueMissionContent | null;
  readonly hasArrived: (travelSnapshot: unknown) => boolean;
}

export interface MissionRuntimeApi {
  readonly MissionId: MissionId;
}

export type SeaTurtleRopeId = "rope-1" | "rope-2" | "rope-3";

export interface SeaTurtlePoint {
  readonly x: number;
  readonly y: number;
}

/** A single rope segment in the sea-turtle interaction. */
export interface SeaTurtleRope {
  readonly id: SeaTurtleRopeId;
  readonly order: 1 | 2 | 3;
  readonly start: Readonly<SeaTurtlePoint>;
  readonly end: Readonly<SeaTurtlePoint>;
}

export interface SeaTurtleConstants {
  readonly baseEndpointRadius: number;
  readonly assistedEndpointRadius: number;
  readonly basePathTolerance: number;
  readonly assistedPathTolerance: number;
  readonly tapMovementThreshold: number;
  readonly minimumTraceProgress: number;
  readonly maxBackwardProgress: number;
  readonly successFeedbackMs: number;
  readonly failureFeedbackMs: number;
}

/** Immutable snapshot of the sea-turtle state machine. */
export interface SeaTurtleSnapshot {
  readonly active: boolean;
  readonly activeRopeId: SeaTurtleRopeId | null;
  readonly completedRopeIds: readonly SeaTurtleRopeId[];
  readonly failureCount: number;
  readonly helpLevel: number;
  readonly tapStartArmed: boolean;
  readonly pointerActive: boolean;
  readonly inputLocked: boolean;
  readonly feedback: "success" | "failure" | null;
  readonly complete: boolean;
}

/** Result of a pointer-up gesture on a sea-turtle rope. */
export interface SeaTurtleRopeResult {
  readonly accepted: boolean;
  readonly outcome: "success" | "failure" | "none";
  readonly ropeId: SeaTurtleRopeId | null;
}

/** Result of calling finishFeedback() to advance past feedback. */
export interface SeaTurtleFeedbackCompletion {
  readonly changed: boolean;
  readonly complete: boolean;
  readonly nextRopeId: SeaTurtleRopeId | null;
}

/** Typed runtime API for the sea-turtle interaction state machine. */
export interface SeaTurtleApi {
  readonly MissionId: "sea-turtle";
  readonly Constants: Readonly<SeaTurtleConstants>;
  readonly Ropes: readonly SeaTurtleRope[];
  readonly Dialogues: readonly [string, string, string];
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

/** Typed scene API for the sea-turtle authored PixiJS scene. */
export interface SeaTurtleSceneApi extends RescueSceneApi {
  readonly activate: () => boolean;
  readonly sync: (
    snapshot: SeaTurtleSnapshot,
    intent?: PointerIntent,
  ) => boolean;
}

export interface RescueSceneDiagnostics {
  readonly missingAliases?: readonly string[];
}

export interface RescueSceneApi {
  readonly prepare: () => boolean;
  readonly isMounted: () => boolean;
  readonly exit: () => void;
  readonly pause: () => void;
  readonly resume: () => void;
  readonly getDiagnostics?: () => RescueSceneDiagnostics;
}

export interface TravelSceneApi {
  readonly prepare: () => boolean;
  readonly activate: () => boolean;
  readonly sync: (travelSnapshot: unknown, terrainSnapshot: unknown) => boolean;
  readonly isMounted: () => boolean;
  readonly exit: () => void;
  readonly pause: () => void;
  readonly resume: () => void;
}

export interface RenderRuntimeTravelApi extends RenderCoordinateMapperApi {
  readonly setLegacyBridgeVisible: (visible: boolean) => void;
  readonly getLegacyCanvas: () => HTMLCanvasElement | null;
  readonly getLegacyContext: () => CanvasRenderingContext2D | null;
  readonly pause: () => void;
  readonly resume: () => void;
}

export type TravelProgressResult =
  | Readonly<{ valid: false }>
  | Readonly<{
      valid: true;
      percent: number;
      distance: number;
      arrivalDistance: number;
    }>;

export type PauseableTimerOwner =
  | "launch"
  | "goal-banner"
  | "site-transition"
  | "tutorial"
  | "sea-turtle-feedback"
  | "crab-feedback"
  | "young-whale-feedback"
  | "mission-success";

export interface OceanRescueNamespace {
  Profile?: ProfileApi;
  Missions?: MissionsApi;
  Gups?: GupsApi;
  Launch?: LaunchApi;
  State?: StateApi;
  Travel?: TravelApi;
  Terrain?: TerrainApi;
  Rescue?: RescueApi;
  SeaTurtle?: SeaTurtleApi;
  SeaTurtleScene?: SeaTurtleSceneApi;
  Crab?: MissionRuntimeApi;
  CrabScene?: RescueSceneApi;
  TravelScene?: TravelSceneApi;
  RenderRuntime?: RenderRuntimeTravelApi;
  PointerInput?: PointerInputApi;
  TravelProgress?: Readonly<{
    compute: (travelSnapshot: unknown) => TravelProgressResult;
  }>;
}
