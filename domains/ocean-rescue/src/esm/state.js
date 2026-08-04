// @ts-check
/// <reference path="../contracts/ocean-rescue-global.d.ts" />
import { State } from "../state/state";

const registered = window.OceanRescue?.State;

if (!registered) {
  throw new Error("OceanRescue.State was not registered");
}

if (registered !== State) {
  throw new Error("OceanRescue.State global must reference the typed state API");
}

export { State };
