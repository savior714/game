(function () {
  var State = window.OceanRescue.State;

  var App = {
    boot: function () {
      var root = document.getElementById("ocean-rescue-root");
      var status = document.getElementById("ocean-rescue-status");
      if (!root || !status) {
        return false;
      }
      if (root.getAttribute("data-ocean-rescue-ready") === "true") {
        return true;
      }
      var snapshot = State.getSnapshot();
      if (snapshot.phase === State.Phases.BOOT) {
        var token = State.beginTransition(State.Phases.MISSION_SELECT);
        if (token === null) {
          return false;
        }
        if (!State.completeTransition(token)) {
          return false;
        }
      }
      State.markReady();
      root.setAttribute("data-ocean-rescue-ready", "true");
      status.textContent = "Ocean Rescue ready";
      return true;
    }
  };

  window.OceanRescue.App = App;

  document.addEventListener("DOMContentLoaded", function () {
    App.boot();
  });
})();
