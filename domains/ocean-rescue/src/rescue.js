(function () {
  var root = window.OceanRescue = window.OceanRescue || {};

  function freeze(value) {
    return Object.freeze(value);
  }

  var ArrivalDistance = 6000;
  var SiteTransitionMs = 1500;
  var TutorialDurationMs = 3000;

  var CATALOG = freeze([
    freeze({
      missionId: "sea-turtle",
      targetLabel: "Sea turtle",
      toolLabel: "Cutter",
      situation: "The sea turtle is tangled in three ropes.",
      tutorial: "Start here. Follow the rope to the end!"
    }),
    freeze({
      missionId: "crab",
      targetLabel: "Crab",
      toolLabel: "Grabber arm",
      situation: "The crab is trapped under three rocks.",
      tutorial: "Hold the rock. Move it. Release it in the zone!"
    }),
    freeze({
      missionId: "young-whale",
      targetLabel: "Young whale",
      toolLabel: "GUP hook",
      situation: "Debris is blocking the young whale’s path.",
      tutorial: "Drag from the debris to the GUP hook!"
    })
  ]);

  function getMissionContent(missionId) {
    if (typeof missionId !== "string") {
      return null;
    }
    for (var i = 0; i < CATALOG.length; i += 1) {
      if (CATALOG[i].missionId === missionId) {
        return CATALOG[i];
      }
    }
    return null;
  }

  function isFiniteNonNegative(value) {
    return typeof value === "number" && isFinite(value) && value >= 0;
  }

  function hasArrived(travelSnapshot) {
    if (!travelSnapshot || typeof travelSnapshot !== "object") {
      return false;
    }
    if (travelSnapshot.active !== true) {
      return false;
    }
    if (!isFiniteNonNegative(travelSnapshot.distance)) {
      return false;
    }
    return travelSnapshot.distance >= ArrivalDistance;
  }

  root.Rescue = freeze({
    Catalog: CATALOG,
    ArrivalDistance: ArrivalDistance,
    SiteTransitionMs: SiteTransitionMs,
    TutorialDurationMs: TutorialDurationMs,
    getMissionContent: getMissionContent,
    hasArrived: hasArrived
  });
})();
