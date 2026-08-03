import "./render-runtime.js";
import "./crab.js";
import "../crab-scene.js";

const CrabScene = window.OceanRescue?.CrabScene;

if (!CrabScene) {
  throw new Error("OceanRescue.CrabScene was not registered");
}

export { CrabScene };
