import "../rescue.js";

const Rescue = window.OceanRescue?.Rescue;

if (!Rescue) {
  throw new Error("OceanRescue.Rescue was not registered");
}

export { Rescue };
