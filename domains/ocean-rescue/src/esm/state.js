import "../state.js";

const State = window.OceanRescue?.State;

if (!State) {
  throw new Error("OceanRescue.State was not registered");
}

export { State };
