// @ts-check
/// <reference path="../contracts/ocean-rescue-global.d.ts" />
import { Catalog } from "../gups/catalog";
import "../gups.js";

const registered = window.OceanRescue?.Gups;

if (!registered) {
  throw new Error("OceanRescue.Gups was not registered");
}

if (typeof registered.getSnapshot !== "function") {
  throw new Error("OceanRescue.Gups controller is missing getSnapshot");
}

if (typeof registered.isValidGup !== "function") {
  throw new Error("OceanRescue.Gups controller is missing isValidGup");
}

if (typeof registered.prepareSelection !== "function") {
  throw new Error("OceanRescue.Gups controller is missing prepareSelection");
}

if (typeof registered.selectGup !== "function") {
  throw new Error("OceanRescue.Gups controller is missing selectGup");
}

if (typeof registered.confirmSelection !== "function") {
  throw new Error("OceanRescue.Gups controller is missing confirmSelection");
}

if (registered.Catalog === Catalog) {
  throw new Error("OceanRescue.Gups.Catalog must reference the typed GUP catalog");
}

if (registered.Catalog.length !== Catalog.length) {
  throw new Error("OceanRescue.Gups.Catalog length parity mismatch");
}

for (let i = 0; i < Catalog.length; i += 1) {
  const legacyEntry = registered.Catalog[i];
  const typedEntry = Catalog[i];
  if (
    !legacyEntry ||
    typedEntry.id !== legacyEntry.id ||
    typedEntry.name !== legacyEntry.name ||
    typedEntry.description !== legacyEntry.description
  ) {
    throw new Error("OceanRescue.Gups.Catalog value parity mismatch");
  }
}

const Gups = Object.freeze({
  Catalog: Catalog,
  getSnapshot: registered.getSnapshot,
  isValidGup: registered.isValidGup,
  prepareSelection: registered.prepareSelection,
  selectGup: registered.selectGup,
  confirmSelection: registered.confirmSelection
});

/** @type {Window & { OceanRescue: import("../contracts/runtime-abi").OceanRescueNamespace }} */
(window).OceanRescue.Gups = Gups;

export { Catalog };
export { Gups };
