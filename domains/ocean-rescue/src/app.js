(function () {
  var State = window.OceanRescue.State;

  var App = {
    boot: function () {
      var root = document.getElementById("ocean-rescue-root");
      var status = document.getElementById("ocean-rescue-status");
      if (!root || !status) {
        return;
      }
      if (root.getAttribute("data-ocean-rescue-ready") === "true") {
        return;
      }
      window.OceanRescue.State.ready = true;
      root.setAttribute("data-ocean-rescue-ready", "true");
      status.textContent = "Ocean Rescue scaffold ready";
    }
  };

  window.OceanRescue.App = App;

  document.addEventListener("DOMContentLoaded", function () {
    App.boot();
  });
})();
