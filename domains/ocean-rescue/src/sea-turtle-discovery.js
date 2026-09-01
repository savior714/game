(function () {
  "use strict";

  var root = window.OceanRescue = window.OceanRescue || {};

  function freeze(value) {
    return Object.freeze(value);
  }

  function isFiniteNumber(value) {
    return typeof value === "number" && isFinite(value);
  }

  var Config = freeze({
    DiscoveryStartDistance: 4800,
    AwarenessDistance: 5100,
    HoldZoneStartDistance: 5400,
    HoldTargetDistance: 5820,
    CalmVelocityThreshold: 180,
    HysteresisVelocityThreshold: 260,
    StartledVelocityThreshold: 380,
    StartledDurationMs: 700,
    SettleDwellMs: 600,
    ScanDurationMs: 1200
  });

  var ReactionStates = freeze({
    INACTIVE: "inactive",
    DISTANT: "distant",
    AWARENESS: "awareness",
    STARTLED: "startled",
    SETTLING: "settling",
    SCAN_ELIGIBLE: "scan-eligible",
    SCANNING: "scanning",
    READY_FOR_RESCUE: "ready-for-rescue"
  });

  var state = {
    active: false,
    reactionState: ReactionStates.INACTIVE,
    dwellTimer: 0,
    settleProgress: 0,
    startledTimer: 0,
    scanEligible: false,
    scanning: false,
    scanElapsed: 0,
    scanProgress: 0,
    readyForRescue: false,
    forwardSpeedMultiplier: 1.0,
    distance: 0,
    lastCollisionCount: 0
  };

  function getSnapshot() {
    return freeze({
      active: state.active,
      reactionState: state.reactionState,
      settleProgress: state.settleProgress,
      scanEligible: state.scanEligible,
      scanning: state.scanning,
      scanProgress: state.scanProgress,
      readyForRescue: state.readyForRescue,
      forwardSpeedMultiplier: state.forwardSpeedMultiplier,
      distance: state.distance
    });
  }

  function start() {
    state.active = true;
    state.reactionState = ReactionStates.INACTIVE;
    state.dwellTimer = 0;
    state.settleProgress = 0;
    state.startledTimer = 0;
    state.scanEligible = false;
    state.scanning = false;
    state.scanElapsed = 0;
    state.scanProgress = 0;
    state.readyForRescue = false;
    state.forwardSpeedMultiplier = 1.0;
    state.distance = 0;
    state.lastCollisionCount = 0;
    return true;
  }

  function stop() {
    if (!state.active) {
      return false;
    }
    state.active = false;
    state.reactionState = ReactionStates.INACTIVE;
    state.scanEligible = false;
    state.scanning = false;
    state.readyForRescue = false;
    state.forwardSpeedMultiplier = 1.0;
    state.lastCollisionCount = 0;
    return true;
  }

  function triggerScan() {
    if (!state.active || !state.scanEligible || state.scanning || state.readyForRescue) {
      return false;
    }
    state.scanning = true;
    state.scanEligible = false;
    state.scanElapsed = 0;
    state.scanProgress = 0;
    state.reactionState = ReactionStates.SCANNING;
    return true;
  }

  function step(deltaMs, travelSnapshot, terrainSnapshot, motionContext) {
    if (!state.active) {
      return false;
    }
    if (!isFiniteNumber(deltaMs) || deltaMs <= 0) {
      return false;
    }
    var applied = deltaMs > 50 ? 50 : deltaMs;

    var distance = travelSnapshot && isFiniteNumber(travelSnapshot.distance) ? travelSnapshot.distance : 0;
    state.distance = distance;

    var currentCollisionCount = terrainSnapshot && isFiniteNumber(terrainSnapshot.collisionCount)
      ? terrainSnapshot.collisionCount
      : 0;

    if (distance < Config.DiscoveryStartDistance) {
      state.reactionState = ReactionStates.INACTIVE;
      state.scanEligible = false;
      state.settleProgress = 0;
      state.dwellTimer = 0;
      state.startledTimer = 0;
      state.forwardSpeedMultiplier = 1.0;
      state.lastCollisionCount = currentCollisionCount;
      return true;
    }

    if (state.readyForRescue) {
      state.reactionState = ReactionStates.READY_FOR_RESCUE;
      state.scanEligible = false;
      state.scanning = false;
      state.scanProgress = 1.0;
      state.forwardSpeedMultiplier = 1.0;
      state.lastCollisionCount = currentCollisionCount;
      return true;
    }

    if (state.scanning) {
      state.scanElapsed += applied;
      state.scanProgress = Math.min(1.0, state.scanElapsed / Config.ScanDurationMs);
      state.reactionState = ReactionStates.SCANNING;
      state.forwardSpeedMultiplier = 0.0;
      state.lastCollisionCount = currentCollisionCount;
      if (state.scanProgress >= 1.0) {
        state.scanning = false;
        state.readyForRescue = true;
        state.reactionState = ReactionStates.READY_FOR_RESCUE;
        state.forwardSpeedMultiplier = 1.0;
      }
      return true;
    }

    // Check abrupt movement / collision
    var derivedVy = motionContext && isFiniteNumber(motionContext.verticalVelocity)
      ? Math.abs(motionContext.verticalVelocity)
      : 0;
    var isNewCollision = currentCollisionCount > state.lastCollisionCount || Boolean(motionContext && motionContext.isColliding);
    state.lastCollisionCount = currentCollisionCount;
    var isAbrupt = derivedVy >= Config.StartledVelocityThreshold || isNewCollision;

    if (isAbrupt) {
      state.startledTimer = Config.StartledDurationMs;
      state.dwellTimer = 0;
      state.settleProgress = 0;
      state.scanEligible = false;
      state.reactionState = ReactionStates.STARTLED;
    } else if (state.startledTimer > 0) {
      state.startledTimer -= applied;
      if (state.startledTimer > 0) {
        state.reactionState = ReactionStates.STARTLED;
      } else {
        state.startledTimer = 0;
        state.reactionState = ReactionStates.SETTLING;
      }
    } else {
      var threshold = state.scanEligible ? Config.HysteresisVelocityThreshold : Config.CalmVelocityThreshold;
      var isCalm = derivedVy <= threshold;

      if (isCalm) {
        state.dwellTimer += applied;
        state.settleProgress = Math.min(1.0, state.dwellTimer / Config.SettleDwellMs);
        if (state.dwellTimer >= Config.SettleDwellMs) {
          state.scanEligible = true;
          state.reactionState = ReactionStates.SCAN_ELIGIBLE;
        } else if (distance >= Config.AwarenessDistance) {
          state.reactionState = state.dwellTimer > 150 ? ReactionStates.SETTLING : ReactionStates.AWARENESS;
        } else {
          state.reactionState = ReactionStates.DISTANT;
        }
      } else {
        state.dwellTimer = Math.max(0, state.dwellTimer - applied * 1.5);
        state.settleProgress = Math.min(1.0, state.dwellTimer / Config.SettleDwellMs);
        state.scanEligible = false;
        if (distance >= Config.AwarenessDistance) {
          state.reactionState = ReactionStates.AWARENESS;
        } else {
          state.reactionState = ReactionStates.DISTANT;
        }
      }
    }

    // Forward speed multiplier composition in hold zone
    if (distance < Config.HoldZoneStartDistance) {
      state.forwardSpeedMultiplier = 1.0;
    } else {
      var remaining = Config.HoldTargetDistance - distance;
      var span = Config.HoldTargetDistance - Config.HoldZoneStartDistance;
      if (remaining <= 0) {
        state.forwardSpeedMultiplier = 0.0;
      } else {
        var ratio = remaining / span;
        state.forwardSpeedMultiplier = Math.max(0.0, Math.min(1.0, ratio));
      }
    }

    return true;
  }

  root.SeaTurtleDiscovery = freeze({
    Config: Config,
    ReactionStates: ReactionStates,
    getSnapshot: getSnapshot,
    start: start,
    stop: stop,
    triggerScan: triggerScan,
    step: step
  });
})();
