import { Catalog } from "../missions/catalog";
import "../missions.js";

const registered = window.OceanRescue?.Missions;

if (!registered) {
  throw new Error("OceanRescue.Missions was not registered");
}

if (typeof registered.getSnapshot !== "function") {
  throw new Error("OceanRescue.Missions controller is missing getSnapshot");
}

if (typeof registered.isUnlocked !== "function") {
  throw new Error("OceanRescue.Missions controller is missing isUnlocked");
}

if (typeof registered.selectMission !== "function") {
  throw new Error("OceanRescue.Missions controller is missing selectMission");
}

if (typeof registered.completeMission !== "function") {
  throw new Error("OceanRescue.Missions controller is missing completeMission");
}

if (typeof registered.markMissionViewed !== "function") {
  throw new Error("OceanRescue.Missions controller is missing markMissionViewed");
}

if (registered.Catalog === Catalog) {
  throw new Error("OceanRescue.Missions.Catalog must reference the typed mission catalog");
}

if (registered.Catalog.length !== Catalog.length) {
  throw new Error("OceanRescue.Missions.Catalog length parity mismatch");
}

for (let i = 0; i < Catalog.length; i += 1) {
  const legacyEntry = registered.Catalog[i];
  const typedEntry = Catalog[i];
  if (
    !legacyEntry ||
    typedEntry.id !== legacyEntry.id ||
    typedEntry.order !== legacyEntry.order ||
    typedEntry.title !== legacyEntry.title ||
    typedEntry.companion !== legacyEntry.companion ||
    typedEntry.summary !== legacyEntry.summary
  ) {
    throw new Error("OceanRescue.Missions.Catalog value parity mismatch");
  }
}

const Missions = Object.freeze({
  Catalog: Catalog,
  getSnapshot: registered.getSnapshot,
  isUnlocked: registered.isUnlocked,
  selectMission: registered.selectMission,
  completeMission: registered.completeMission,
  markMissionViewed: registered.markMissionViewed
});

window.OceanRescue.Missions = Missions;

export { Catalog };
export { Missions };
