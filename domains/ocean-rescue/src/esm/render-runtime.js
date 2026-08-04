// @ts-check
/// <reference path="../contracts/ocean-rescue-global.d.ts" />
import "./render-assets.js";
import "../render-runtime.js";

const RenderRuntime = window.OceanRescue?.RenderRuntime;

if (!RenderRuntime) {
  throw new Error("OceanRescue.RenderRuntime was not registered");
}

if (
  typeof RenderRuntime.isReady !== "function" ||
  typeof RenderRuntime.mapClientToLogical !== "function"
) {
  throw new Error("OceanRescue.RenderRuntime coordinate mapper contract is incomplete");
}

export { RenderRuntime };
