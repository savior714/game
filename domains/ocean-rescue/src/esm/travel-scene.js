import "./render-runtime.js";
import "./terrain.js";
import "./gups.js";
import "../travel-scene.js";
import "../presentation/travel-actor-presentation.js";

const TravelScene = window.OceanRescue?.TravelScene;

if (!TravelScene) {
  throw new Error("OceanRescue.TravelScene was not registered");
}

export { TravelScene };
