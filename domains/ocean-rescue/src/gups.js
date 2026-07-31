(function () {
  var root = window.OceanRescue = window.OceanRescue || {};

  function freeze(value) {
    return Object.freeze(value);
  }

  var Catalog = freeze([
    freeze({
      id: "gup-c",
      name: "GUP-C",
      description: "Yellow rescue sub"
    }),
    freeze({
      id: "gup-i",
      name: "GUP-I",
      description: "White and blue rescue sub"
    }),
    freeze({
      id: "gup-x",
      name: "GUP-X",
      description: "Red rescue sub"
    })
  ]);

  var state = {
    selectedGupId: "gup-c",
    lastGupId: "gup-c"
  };

  function catalogIndexOf(gupId) {
    for (var i = 0; i < Catalog.length; i += 1) {
      if (Catalog[i].id === gupId) {
        return i;
      }
    }
    return -1;
  }

  function isValidGup(gupId) {
    if (typeof gupId !== "string") {
      return false;
    }
    return catalogIndexOf(gupId) !== -1;
  }

  function getSnapshot() {
    return freeze({
      selectedGupId: state.selectedGupId,
      lastGupId: state.lastGupId
    });
  }

  function prepareSelection() {
    state.selectedGupId = state.lastGupId;
    return state.selectedGupId;
  }

  function selectGup(gupId) {
    if (!isValidGup(gupId)) {
      return false;
    }
    state.selectedGupId = gupId;
    return true;
  }

  function confirmSelection() {
    state.lastGupId = state.selectedGupId;
    return state.selectedGupId;
  }

  root.Gups = freeze({
    Catalog: Catalog,
    getSnapshot: getSnapshot,
    isValidGup: isValidGup,
    prepareSelection: prepareSelection,
    selectGup: selectGup,
    confirmSelection: confirmSelection
  });
})();
