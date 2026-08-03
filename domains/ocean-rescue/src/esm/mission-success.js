import "../mission-success.js";

const MissionSuccess = window.OceanRescue?.MissionSuccess;

if (!MissionSuccess) {
  throw new Error("OceanRescue.MissionSuccess was not registered");
}

export { MissionSuccess };
