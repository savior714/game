import "./render-runtime.js";
import "./sea-turtle.js";
import "../sea-turtle-scene.js";

const SeaTurtleScene = window.OceanRescue?.SeaTurtleScene;

if (!SeaTurtleScene) {
  throw new Error("OceanRescue.SeaTurtleScene was not registered");
}

export { SeaTurtleScene };
