import { installLaunchTravelController } from "../controllers/launch-travel";
import { installPauseTimerResumeController } from "../controllers/pause-timer-resume";
import { installRescueSiteTutorialController } from "../controllers/rescue-site-tutorial";
import { installProfileMissionSelectionController } from "../controllers/profile-mission-selection";
import { installSeaTurtleLifecycleController } from "../controllers/sea-turtle-lifecycle";
import "./state.js";
import "./render-runtime.js";
import "./pointer-input.js";
import "./profile.js";
import "./missions.js";
import "./gups.js";
import "./launch.js";
import "./travel.js";
import "./terrain.js";
import "./rescue.js";
import "./sea-turtle.js";
import "./sea-turtle-scene.js";
import "./crab.js";
import "./travel-scene.js";
import "./crab-scene.js";
import "./young-whale.js";
import "./mission-success.js";
import "../app.js";

const registeredApp = window.OceanRescue?.App;

if (!registeredApp) {
  throw new Error("OceanRescue.App was not registered");
}

const profileMissionApp = installProfileMissionSelectionController(registeredApp);
const launchTravelApp = installLaunchTravelController(profileMissionApp);
const rescueSiteApp = installRescueSiteTutorialController(launchTravelApp);
const pauseTimerApp = installPauseTimerResumeController(rescueSiteApp);
const App = installSeaTurtleLifecycleController(pauseTimerApp);

export { App };
