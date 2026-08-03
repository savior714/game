import "../launch.js";

const Launch = window.OceanRescue?.Launch;

if (!Launch) {
  throw new Error("OceanRescue.Launch was not registered");
}

export { Launch };
