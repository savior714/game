(function () {
  var root = window.OceanRescue = window.OceanRescue || {};

  function freeze(value) {
    return Object.freeze(value);
  }

  var CATALOG = freeze([
    freeze({
      id: "sea-turtle",
      order: 1,
      title: "Sea Turtle Rescue",
      companion: "Peso",
      summary: "Cut the ropes and free the trapped sea turtle."
    }),
    freeze({
      id: "crab",
      order: 2,
      title: "Crab Rescue",
      companion: "Tweak",
      summary: "Move the rocks and help the trapped crab."
    }),
    freeze({
      id: "young-whale",
      order: 3,
      title: "Young Whale Rescue",
      companion: "Captain Barnacles",
      summary: "Tow the debris and clear a path for the young whale."
    })
  ]);

  var state = {
    selectedMissionId: null,
    unlockedMissionIds: ["sea-turtle"],
    completedMissionIds: [],
    newMissionIds: []
  };

  function catalogIndexOf(missionId) {
    for (var i = 0; i < CATALOG.length; i += 1) {
      if (CATALOG[i].id === missionId) {
        return i;
      }
    }
    return -1;
  }

  function isUnlocked(missionId) {
    if (typeof missionId !== "string") {
      return false;
    }
    if (catalogIndexOf(missionId) === -1) {
      return false;
    }
    return state.unlockedMissionIds.indexOf(missionId) !== -1;
  }

  function getSnapshot() {
    return freeze({
      selectedMissionId: state.selectedMissionId,
      unlockedMissionIds: freeze(state.unlockedMissionIds.slice()),
      completedMissionIds: freeze(state.completedMissionIds.slice()),
      newMissionIds: freeze(state.newMissionIds.slice())
    });
  }

  function selectMission(missionId) {
    if (!isUnlocked(missionId)) {
      return false;
    }
    state.selectedMissionId = missionId;
    return true;
  }

  function completeMission(missionId) {
    if (!isUnlocked(missionId)) {
      return freeze({ changed: false, newlyUnlockedMissionId: null });
    }
    if (state.completedMissionIds.indexOf(missionId) !== -1) {
      return freeze({ changed: false, newlyUnlockedMissionId: null });
    }
    state.completedMissionIds.push(missionId);
    var index = catalogIndexOf(missionId);
    var next = CATALOG[index + 1];
    var newlyUnlockedMissionId = null;
    if (next) {
      if (state.unlockedMissionIds.indexOf(next.id) === -1) {
        state.unlockedMissionIds.push(next.id);
        state.newMissionIds.push(next.id);
        newlyUnlockedMissionId = next.id;
      }
    }
    return freeze({ changed: true, newlyUnlockedMissionId: newlyUnlockedMissionId });
  }

  function markMissionViewed(missionId) {
    var index = state.newMissionIds.indexOf(missionId);
    if (index === -1) {
      return false;
    }
    state.newMissionIds.splice(index, 1);
    return true;
  }

  root.Missions = freeze({
    Catalog: CATALOG,
    getSnapshot: getSnapshot,
    isUnlocked: isUnlocked,
    selectMission: selectMission,
    completeMission: completeMission,
    markMissionViewed: markMissionViewed
  });
})();
