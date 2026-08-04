// @ts-check
/// <reference path="../contracts/ocean-rescue-global.d.ts" />
import { Launch } from "../launch/launch";

const registered = window.OceanRescue?.Launch;

if (!registered) {
  throw new Error("OceanRescue.Launch was not registered");
}

if (registered !== Launch) {
  throw new Error("OceanRescue.Launch global must reference the typed launch API");
}

export { Launch };
