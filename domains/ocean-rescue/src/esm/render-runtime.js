import "./render-assets.js";
import "../render-runtime.js";

const RenderRuntime = window.OceanRescue?.RenderRuntime;

if (!RenderRuntime) {
  throw new Error("OceanRescue.RenderRuntime was not registered");
}

export { RenderRuntime };
