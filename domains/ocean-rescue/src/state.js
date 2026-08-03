(function () {
  var root = window.OceanRescue = window.OceanRescue || {};

  function freeze(value) {
    return Object.freeze(value);
  }

  var Phases = freeze({
    BOOT: "BOOT",
    PROFILE_CHOICE: "PROFILE_CHOICE",
    MISSION_SELECT: "MISSION_SELECT",
    GUP_SELECT: "GUP_SELECT",
    LAUNCH: "LAUNCH",
    TRAVEL: "TRAVEL",
    RESCUE_SITE_TRANSITION: "RESCUE_SITE_TRANSITION",
    RESCUE_TUTORIAL: "RESCUE_TUTORIAL",
    RESCUE_ACTIVE: "RESCUE_ACTIVE",
    RESCUE_SUCCESS: "RESCUE_SUCCESS",
    MISSION_COMPLETE: "MISSION_COMPLETE"
  });

  var transitions = freeze({
    BOOT: freeze([Phases.PROFILE_CHOICE, Phases.MISSION_SELECT]),
    PROFILE_CHOICE: freeze([Phases.MISSION_SELECT]),
    MISSION_SELECT: freeze([Phases.GUP_SELECT]),
    GUP_SELECT: freeze([Phases.MISSION_SELECT, Phases.LAUNCH]),
    LAUNCH: freeze([Phases.TRAVEL]),
    TRAVEL: freeze([Phases.RESCUE_SITE_TRANSITION]),
    RESCUE_SITE_TRANSITION: freeze([Phases.RESCUE_TUTORIAL]),
    RESCUE_TUTORIAL: freeze([Phases.RESCUE_ACTIVE]),
    RESCUE_ACTIVE: freeze([Phases.RESCUE_SUCCESS]),
    RESCUE_SUCCESS: freeze([Phases.MISSION_COMPLETE]),
    MISSION_COMPLETE: freeze([Phases.MISSION_SELECT, Phases.LAUNCH])
  });

  var state = {
    phase: Phases.BOOT,
    ready: false,
    transitionLocked: false,
    pendingPhase: null,
    activeToken: null,
    transitionId: 0
  };

  function isPhase(value) {
    return (
      typeof value === "string" &&
      Object.prototype.hasOwnProperty.call(Phases, value)
    );
  }

  function canTransition(nextPhase) {
    if (typeof nextPhase !== "string") {
      return false;
    }
    if (!isPhase(nextPhase)) {
      return false;
    }
    if (state.transitionLocked) {
      return false;
    }
    if (nextPhase === state.phase) {
      return false;
    }
    var allowed = transitions[state.phase];
    if (!allowed) {
      return false;
    }
    return allowed.indexOf(nextPhase) !== -1;
  }

  function beginTransition(nextPhase) {
    if (!canTransition(nextPhase)) {
      return null;
    }
    state.transitionId += 1;
    var token = freeze({
      id: state.transitionId,
      from: state.phase,
      to: nextPhase
    });
    state.transitionLocked = true;
    state.pendingPhase = nextPhase;
    state.activeToken = token;
    return token;
  }

  function completeTransition(token) {
    if (!state.transitionLocked) {
      return false;
    }
    if (!token || typeof token !== "object") {
      return false;
    }
    var active = state.activeToken;
    if (!active) {
      return false;
    }
    if (token.id !== active.id) {
      return false;
    }
    if (token.from !== active.from) {
      return false;
    }
    if (token.to !== active.to) {
      return false;
    }
    state.phase = token.to;
    state.pendingPhase = null;
    state.transitionLocked = false;
    state.activeToken = null;
    return true;
  }

  function markReady() {
    if (state.ready) {
      return false;
    }
    state.ready = true;
    return true;
  }

  function getSnapshot() {
    return freeze({
      phase: state.phase,
      ready: state.ready,
      transitionLocked: state.transitionLocked,
      pendingPhase: state.pendingPhase
    });
  }

  function forcePhase(phase) {
    if (!isPhase(phase)) {
      return false;
    }
    state.transitionLocked = false;
    state.pendingPhase = null;
    state.activeToken = null;
    state.phase = phase;
    return true;
  }

  root.State = freeze({
    Phases: Phases,
    getSnapshot: getSnapshot,
    markReady: markReady,
    canTransition: canTransition,
    beginTransition: beginTransition,
    completeTransition: completeTransition,
    forcePhase: forcePhase
  });
})();
