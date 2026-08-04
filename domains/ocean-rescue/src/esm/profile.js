// @ts-check
/// <reference path="../contracts/ocean-rescue-global.d.ts" />
import { Profile } from "../profile/profile";

const registered = window.OceanRescue?.Profile;

if (!registered) {
  throw new Error("OceanRescue.Profile was not registered");
}

if (registered !== Profile) {
  throw new Error("OceanRescue.Profile global must reference the typed profile API");
}

export { Profile };
