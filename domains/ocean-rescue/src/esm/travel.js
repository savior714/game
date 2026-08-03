import "../travel.js";

const Travel = window.OceanRescue?.Travel;

if (!Travel) {
  throw new Error("OceanRescue.Travel was not registered");
}

export { Travel };
