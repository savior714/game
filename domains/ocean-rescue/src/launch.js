(function () {
  var root = window.OceanRescue = window.OceanRescue || {};

  function freeze(value) {
    return Object.freeze(value);
  }

  var CATALOG = freeze([
    freeze({
      missionId: "sea-turtle",
      briefing:
        "A sea turtle is trapped in a net. Let’s find it and cut the ropes!",
      goal: "Rescue the sea turtle!"
    }),
    freeze({
      missionId: "crab",
      briefing:
        "A crab is trapped under some rocks. Let’s move them with the grabber!",
      goal: "Help the trapped crab!"
    }),
    freeze({
      missionId: "young-whale",
      briefing:
        "A young whale’s path is blocked. Let’s tow the debris away!",
      goal: "Clear a path for the young whale!"
    })
  ]);

  var DurationMs = 6000;
  var GoalDurationMs = 3000;

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

  root.Launch = freeze({
    Catalog: CATALOG,
    DurationMs: DurationMs,
    GoalDurationMs: GoalDurationMs,
    getMissionContent: getMissionContent
  });
})();
