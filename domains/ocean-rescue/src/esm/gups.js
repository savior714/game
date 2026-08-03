import "../gups.js";

const Gups = window.OceanRescue?.Gups;

if (!Gups) {
  throw new Error("OceanRescue.Gups was not registered");
}

export { Gups };
