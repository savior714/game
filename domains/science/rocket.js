if (typeof RocketCore === "undefined") {
  throw new Error("RocketCore is not loaded. Check script order.");
}

RocketCore.install(window);

const _origLaunchRocket = window.launchRocket;
if (_origLaunchRocket && typeof MilestoneTracker !== 'undefined') {
  window.launchRocket = function() {
    _origLaunchRocket.apply(this, arguments);
    MilestoneTracker.onRocketLaunch();
  };
}
