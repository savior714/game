/**
 * Typed canonical launch module for Ocean Rescue (WP-31B).
 *
 * The legacy `src/launch.js` was demonstrably static: a frozen content catalog,
 * `DurationMs`, `GoalDurationMs`, and a pure `getMissionContent()` lookup. This
 * module is the complete strictly typed canonical implementation of that static
 * API. The unchanged legacy `src/launch.js` is retained byte-for-byte as the
 * operational rollback authority referenced only by
 * `build-manifest.legacy.json`; the canonical graph no longer executes it.
 *
 * The module preserves the legacy observable runtime contract exactly: catalog
 * order and value immutability, timing constants, exact lookup semantics for
 * every input, the frozen public API shape, and the temporary
 * `window.OceanRescue.Launch` compatibility ABI consumed by `src/app.js`.
 */

import type { MissionId } from "../contracts/mission";
import type { OceanRescueNamespace } from "../contracts/runtime-abi";

export type LaunchMissionId = MissionId;

export interface LaunchCatalogEntry {
  readonly missionId: MissionId;
  readonly briefing: string;
  readonly goal: string;
}

export type LaunchCatalog = readonly LaunchCatalogEntry[];

export interface LaunchApi {
  readonly Catalog: LaunchCatalog;
  readonly DurationMs: number;
  readonly GoalDurationMs: number;
  readonly getMissionContent: (missionId: unknown) => LaunchCatalogEntry | null;
}

function freeze<T>(value: T): Readonly<T> {
  return Object.freeze(value);
}

export const Catalog: LaunchCatalog = freeze([
  freeze<LaunchCatalogEntry>({
    missionId: "sea-turtle",
    briefing: "A sea turtle is trapped in a net. Let’s find it and cut the ropes!",
    goal: "Rescue the sea turtle!",
  }),
  freeze<LaunchCatalogEntry>({
    missionId: "crab",
    briefing: "A crab is trapped under some rocks. Let’s move them with the grabber!",
    goal: "Help the trapped crab!",
  }),
  freeze<LaunchCatalogEntry>({
    missionId: "young-whale",
    briefing: "A young whale’s path is blocked. Let’s tow the debris away!",
    goal: "Clear a path for the young whale!",
  }),
]);

export const DurationMs = 6000;
export const GoalDurationMs = 3000;

export function getMissionContent(
  missionId: unknown,
): LaunchCatalogEntry | null {
  if (typeof missionId !== "string") {
    return null;
  }
  for (let i = 0; i < Catalog.length; i += 1) {
    if (Catalog[i].missionId === missionId) {
      return Catalog[i];
    }
  }
  return null;
}

export const Launch: LaunchApi = freeze({
  Catalog,
  DurationMs,
  GoalDurationMs,
  getMissionContent,
});

const win = window as Window & { OceanRescue?: OceanRescueNamespace };
const root = win.OceanRescue || {};
win.OceanRescue = root;
root.Launch = Launch;

export { Launch as OceanRescueLaunch };
