import "../crab.js";

const Crab = window.OceanRescue?.Crab;

if (!Crab) {
  throw new Error("OceanRescue.Crab was not registered");
}

export { Crab };
