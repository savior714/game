import "../missions.js";

const Missions = window.OceanRescue?.Missions;

if (!Missions) {
  throw new Error("OceanRescue.Missions was not registered");
}

export { Missions };
