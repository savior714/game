(function () {
  var root = window.OceanRescue = window.OceanRescue || {};

  function freeze(value) {
    return Object.freeze(value);
  }

  var SuccessAnimationMs = 4000;
  var EcologyDurationMs = 3000;
  var NarrationSentenceMs = 3000;

  var Catalog = freeze([
    freeze({
      missionId: "sea-turtle",
      animationKey: "sea-turtle-swim-free",
      ecology:
        "Sea turtles can get tangled in ocean trash. Keep ropes and nets out of the sea!",
      companionLine:
        "Wonderful rescue, Aiden! You freed every rope safely.",
      animalLine:
        "The sea turtle is swimming calmly through the clean coral reef."
    }),
    freeze({
      missionId: "crab",
      animationKey: "crab-to-burrow",
      ecology:
        "Crabs need safe spaces under rocks and sand. Let’s keep their homes clean!",
      companionLine:
        "Great job, Aiden! You moved every rock carefully.",
      animalLine:
        "The crab is safe again in its clean sandy home."
    }),
    freeze({
      missionId: "young-whale",
      animationKey: "young-whale-to-family",
      ecology:
        "Whales need space to swim safely. Clear the way and watch from a distance!",
      companionLine:
        "Well done, Aiden! You cleared the path and gave the young whale space.",
      animalLine:
        "The young whale is swimming safely with its family."
    })
  ]);

  function catalogIndexOf(missionId) {
    if (typeof missionId !== "string") {
      return -1;
    }
    for (var i = 0; i < Catalog.length; i += 1) {
      if (Catalog[i].missionId === missionId) {
        return i;
      }
    }
    return -1;
  }

  function getContent(missionId) {
    var index = catalogIndexOf(missionId);
    if (index === -1) {
      return null;
    }
    return Catalog[index];
  }

  root.MissionSuccess = freeze({
    Catalog: Catalog,
    SuccessAnimationMs: SuccessAnimationMs,
    EcologyDurationMs: EcologyDurationMs,
    NarrationSentenceMs: NarrationSentenceMs,
    getContent: getContent
  });
})();
