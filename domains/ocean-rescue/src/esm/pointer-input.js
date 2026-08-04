// @ts-check
/// <reference path="../contracts/ocean-rescue-global.d.ts" />
import "../pointer-input.js";

const PointerInput = window.OceanRescue?.PointerInput;

if (!PointerInput) {
  throw new Error("OceanRescue.PointerInput was not registered");
}

if (
  typeof PointerInput.mapTravelStageY !== "function" ||
  typeof PointerInput.mapRescuePoint !== "function" ||
  typeof PointerInput.activeIntent !== "function" ||
  typeof PointerInput.inactiveIntent !== "function"
) {
  throw new Error("OceanRescue.PointerInput contract is incomplete");
}

export { PointerInput };
