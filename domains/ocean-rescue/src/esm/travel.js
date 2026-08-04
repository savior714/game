import { Travel } from "../travel/travel";

const registered = window.OceanRescue?.Travel;

if (!registered) {
  throw new Error("OceanRescue.Travel was not registered");
}

if (registered !== Travel) {
  throw new Error("OceanRescue.Travel global must reference the typed travel API");
}

export { Travel };
