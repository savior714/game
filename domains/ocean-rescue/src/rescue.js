(function () {
  var root = window.OceanRescue = window.OceanRescue || {};

  function freeze(value) {
    return Object.freeze(value);
  }

  var ArrivalDistance = 6000;
  var SiteTransitionMs = 1500;
  var TutorialDurationMs = 3000;

  // Rescue-site copy is owned here so the spoken bubble, the on-screen bubble
  // and the narration can never drift apart. Every line is plain English: the
  // rescue site is the place where the child hears and reads the target's own
  // request for help.
  var CATALOG = freeze([
    freeze({
      missionId: "sea-turtle",
      targetLabel: "Sea turtle",
      toolLabel: "Cutter",
      situation: "The sea turtle is tangled in three ropes.",
      tutorial: "Start here. Follow the rope to the end!",
      targetLine: "Help! I am tangled in ropes. Please cut them and save me!",
      companionLine: "I found a sea turtle tangled in ropes. Let’s cut them free!"
    }),
    freeze({
      missionId: "crab",
      targetLabel: "Crab",
      toolLabel: "Grabber arm",
      situation: "The crab is trapped under three rocks.",
      tutorial: "Hold the rock. Move it. Release it in the zone!",
      targetLine: "Help! Rocks are on my back. Please move them and save me!",
      companionLine: "A crab is stuck under rocks. Let’s lift them and set it free!"
    }),
    freeze({
      missionId: "young-whale",
      targetLabel: "Young whale",
      toolLabel: "GUP hook",
      situation: "Debris is blocking the young whale’s path.",
      tutorial: "Drag from the debris to the GUP hook!",
      targetLine: "Help! Trash blocks my way. Please tow it away and save me!",
      companionLine: "A young whale is stuck behind debris. Let’s tow it away!"
    })
  ]);

  /**
   * Resolve the spoken line of one rescue-site speaker.
   *
   * @param {string} missionId
   * @param {"target" | "companion"} speaker
   * @returns {string | null}
   */
  function getDialogueLine(missionId, speaker) {
    var content = getMissionContent(missionId);
    if (content === null) {
      return null;
    }
    var line = speaker === "companion" ? content.companionLine : content.targetLine;
    return typeof line === "string" && line.length > 0 ? line : null;
  }

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
    getDialogueLine: getDialogueLine,
    hasArrived: hasArrived
  });
})();
