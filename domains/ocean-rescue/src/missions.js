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

  var STORAGE_KEY = "aidengame.oceanRescue.progression";
  var SCHEMA_VERSION = 1;

  function catalogIndexOf(missionId) {
    for (var i = 0; i < CATALOG.length; i += 1) {
      if (CATALOG[i].id === missionId) {
        return i;
      }
    }
    return -1;
  }

  function resolveStorage() {
    if (typeof window === "undefined") {
      return null;
    }
    var storage = window.localStorage;
    if (!storage) {
      return null;
    }
    if (typeof storage.getItem !== "function") {
      return null;
    }
    if (typeof storage.setItem !== "function") {
      return null;
    }
    return storage;
  }

  function bestEffortRemoveStoredPayload() {
    var storage = resolveStorage();
    if (storage === null) {
      return;
    }
    try {
      if (typeof storage.removeItem === "function") {
        storage.removeItem(STORAGE_KEY);
      }
    } catch (error) {
      return;
    }
  }

  function sanitizeStoredPayload(payload) {
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
      return null;
    }
    if (payload.schemaVersion !== SCHEMA_VERSION) {
      return null;
    }
    var completed = payload.completedMissionIds;
    var storedNew = payload.newMissionIds;
    if (!Array.isArray(completed)) {
      return null;
    }
    if (!Array.isArray(storedNew)) {
      return null;
    }
    var completedIndex = {};
    for (var i = 0; i < completed.length; i += 1) {
      var completedId = completed[i];
      if (typeof completedId !== "string") {
        return null;
      }
      if (catalogIndexOf(completedId) === -1) {
        return null;
      }
      if (completedIndex[completedId]) {
        return null;
      }
      completedIndex[completedId] = true;
    }
    var storedNewIndex = {};
    for (var j = 0; j < storedNew.length; j += 1) {
      var newId = storedNew[j];
      if (typeof newId !== "string") {
        return null;
      }
      if (catalogIndexOf(newId) === -1) {
        return null;
      }
      if (storedNewIndex[newId]) {
        return null;
      }
      storedNewIndex[newId] = true;
    }
    var orderedCompleted = completed.slice().sort(function (a, b) {
      return catalogIndexOf(a) - catalogIndexOf(b);
    });
    for (var k = 0; k < orderedCompleted.length; k += 1) {
      if (orderedCompleted[k] !== CATALOG[k].id) {
        return null;
      }
    }
    var unlocked = ["sea-turtle"];
    for (var u = 0; u < orderedCompleted.length; u += 1) {
      var index = catalogIndexOf(orderedCompleted[u]);
      var next = CATALOG[index + 1];
      if (next && unlocked.indexOf(next.id) === -1) {
        unlocked.push(next.id);
      }
    }
    var restoredNew = [];
    for (var m = 0; m < CATALOG.length; m += 1) {
      var candidate = CATALOG[m].id;
      if (unlocked.indexOf(candidate) === -1) {
        continue;
      }
      if (completedIndex[candidate]) {
        continue;
      }
      if (storedNewIndex[candidate]) {
        restoredNew.push(candidate);
      }
    }
    return {
      unlockedMissionIds: unlocked,
      completedMissionIds: orderedCompleted,
      newMissionIds: restoredNew
    };
  }

  function readStoredPayload() {
    var storage = resolveStorage();
    if (storage === null) {
      return null;
    }
    var raw;
    try {
      raw = storage.getItem(STORAGE_KEY);
    } catch (error) {
      return null;
    }
    if (typeof raw !== "string" || raw === "") {
      return null;
    }
    var parsed;
    try {
      parsed = JSON.parse(raw);
    } catch (error) {
      bestEffortRemoveStoredPayload();
      return null;
    }
    var sanitized = sanitizeStoredPayload(parsed);
    if (sanitized === null) {
      bestEffortRemoveStoredPayload();
      return null;
    }
    return sanitized;
  }

  function hydrate() {
    var stored = readStoredPayload();
    if (stored === null) {
      return;
    }
    state.unlockedMissionIds = stored.unlockedMissionIds;
    state.completedMissionIds = stored.completedMissionIds;
    state.newMissionIds = stored.newMissionIds;
  }

  function persist() {
    var storage = resolveStorage();
    if (storage === null) {
      return;
    }
    var payload = {
      schemaVersion: SCHEMA_VERSION,
      completedMissionIds: state.completedMissionIds.slice(),
      newMissionIds: state.newMissionIds.slice()
    };
    try {
      storage.setItem(STORAGE_KEY, JSON.stringify(payload));
    } catch (error) {
      return;
    }
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
    persist();
    return freeze({ changed: true, newlyUnlockedMissionId: newlyUnlockedMissionId });
  }

  function markMissionViewed(missionId) {
    var index = state.newMissionIds.indexOf(missionId);
    if (index === -1) {
      return false;
    }
    state.newMissionIds.splice(index, 1);
    persist();
    return true;
  }

  hydrate();

  root.Missions = freeze({
    Catalog: CATALOG,
    getSnapshot: getSnapshot,
    isUnlocked: isUnlocked,
    selectMission: selectMission,
    completeMission: completeMission,
    markMissionViewed: markMissionViewed
  });
})();
