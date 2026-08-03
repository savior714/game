import "../sea-turtle.js";

const SeaTurtle = window.OceanRescue?.SeaTurtle;

if (!SeaTurtle) {
  throw new Error("OceanRescue.SeaTurtle was not registered");
}

export { SeaTurtle };
