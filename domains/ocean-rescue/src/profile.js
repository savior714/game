(function () {
  var root = window.OceanRescue = window.OceanRescue || {};

  function freeze(value) {
    return Object.freeze(value);
  }

  var STORAGE_KEY = "aidengame.oceanRescue.profile";
  var SCHEMA_VERSION = 1;
  var PLAYER_NAME = "Aiden";

  var CATALOG = freeze([
    freeze({ id: "arctic-fox", name: "Arctic fox" }),
    freeze({ id: "beaver", name: "Beaver" }),
    freeze({ id: "red-panda", name: "Red panda" })
  ]);

  var validAnimalIds = {};
  for (var i = 0; i < CATALOG.length; i += 1) {
    validAnimalIds[CATALOG[i].id] = true;
  }

  var state = {
    selectedAnimalId: null,
    chosenAnimalId: null,
    complete: false
  };

  var confirmedCount = 0;
  var persistCount = 0;

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

  function isValidAnimalId(animalId) {
    if (typeof animalId !== "string") {
      return false;
    }
    return validAnimalIds[animalId] === true;
  }

  function sanitizeStoredPayload(payload) {
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
      return null;
    }
    if (payload.schemaVersion !== SCHEMA_VERSION) {
      return null;
    }
    if (payload.playerName !== PLAYER_NAME) {
      return null;
    }
    if (!isValidAnimalId(payload.animalId)) {
      return null;
    }
    return {
      playerName: payload.playerName,
      animalId: payload.animalId
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

  function persist() {
    var storage = resolveStorage();
    if (storage === null) {
      return false;
    }
    if (!isValidAnimalId(state.chosenAnimalId)) {
      return false;
    }
    var payload = {
      schemaVersion: SCHEMA_VERSION,
      playerName: PLAYER_NAME,
      animalId: state.chosenAnimalId
    };
    try {
      storage.setItem(STORAGE_KEY, JSON.stringify(payload));
      persistCount += 1;
      return true;
    } catch (error) {
      return false;
    }
  }

  function hydrate() {
    var stored = readStoredPayload();
    if (stored === null) {
      return;
    }
    state.chosenAnimalId = stored.animalId;
    state.complete = true;
  }

  function getSnapshot() {
    return freeze({
      playerName: PLAYER_NAME,
      selectedAnimalId: state.selectedAnimalId,
      chosenAnimalId: state.chosenAnimalId,
      complete: state.complete
    });
  }

  function selectAnimal(animalId) {
    if (!isValidAnimalId(animalId)) {
      return false;
    }
    state.selectedAnimalId = animalId;
    return true;
  }

  function confirmSelection() {
    if (state.complete) {
      return false;
    }
    if (!isValidAnimalId(state.selectedAnimalId)) {
      return false;
    }
    state.chosenAnimalId = state.selectedAnimalId;
    var persisted = persist();
    if (persisted) {
      state.complete = true;
      confirmedCount += 1;
    }
    return true;
  }

  hydrate();

  root.Profile = freeze({
    Catalog: CATALOG,
    getSnapshot: getSnapshot,
    selectAnimal: selectAnimal,
    confirmSelection: confirmSelection
  });
})();
