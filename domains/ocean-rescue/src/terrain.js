(function () {
  var root = window.OceanRescue = window.OceanRescue || {};

  function freeze(value) {
    return Object.freeze(value);
  }

  function isFiniteNumber(value) {
    return typeof value === "number" && isFinite(value);
  }

  var Constants = freeze({
    gupScreenX: 320,
    gupHalfWidth: 70,
    gupHalfHeight: 36,
    obstacleSpacing: 1000,
    slowdownDurationMs: 1000,
    slowdownMultiplier: 0.5,
    sameObstacleCooldownMs: 700,
    shakeDurationMs: 350,
    knockbackDistance: 36
  });

  var GEOMETRY = freeze([
    freeze({ worldX: 1200, y: 220, width: 180, height: 150 }),
    freeze({ worldX: 2200, y: 500, width: 200, height: 160 }),
    freeze({ worldX: 3200, y: 300, width: 160, height: 180 }),
    freeze({ worldX: 4200, y: 470, width: 190, height: 150 }),
    freeze({ worldX: 5200, y: 250, width: 200, height: 170 })
  ]);

  function buildObstacle(index, id, kind, geometry) {
    return freeze({
      id: id,
      worldX: geometry.worldX,
      y: geometry.y,
      width: geometry.width,
      height: geometry.height,
      kind: kind
    });
  }

  function buildLayout(missionId, environment, idsAndKinds) {
    var obstacles = [];
    for (var i = 0; i < GEOMETRY.length; i += 1) {
      obstacles.push(
        buildObstacle(i, idsAndKinds[i][0], idsAndKinds[i][1], GEOMETRY[i])
      );
    }
    return freeze({
      missionId: missionId,
      environment: environment,
      obstacles: freeze(obstacles)
    });
  }

  var Layouts = freeze({
    "sea-turtle": buildLayout("sea-turtle", "coral-reef", [
      ["coral-column-1", "coral-column"],
      ["reef-arch-2", "reef-arch"],
      ["coral-rock-3", "coral-rock"],
      ["kelp-rock-4", "kelp-rock"],
      ["reef-spire-5", "reef-spire"]
    ]),
    "crab": buildLayout("crab", "sandy-reef", [
      ["sand-rock-1", "sand-rock"],
      ["shell-ledge-2", "shell-ledge"],
      ["low-reef-3", "low-reef"],
      ["rock-stack-4", "rock-stack"],
      ["sand-pillar-5", "sand-pillar"]
    ]),
    "young-whale": buildLayout("young-whale", "rocky-canyon", [
      ["canyon-wall-1", "canyon-wall"],
      ["rock-spire-2", "rock-spire"],
      ["canyon-ledge-3", "canyon-ledge"],
      ["boulder-stack-4", "boulder-stack"],
      ["canyon-pillar-5", "canyon-pillar"]
    ])
  });

  var state = {
    active: false,
    missionId: null,
    collisionCount: 0,
    lastCollisionObstacleId: null,
    slowdownRemainingMs: 0,
    shakeRemainingMs: 0
  };

  var activeContacts = {};
  var cooldowns = {};

  function getLayout(missionId) {
    if (typeof missionId !== "string") {
      return null;
    }
    if (Object.prototype.hasOwnProperty.call(Layouts, missionId)) {
      return Layouts[missionId];
    }
    return null;
  }

  function getSnapshot() {
    var slowdownRemainingMs = state.slowdownRemainingMs;
    var shakeRemainingMs = state.shakeRemainingMs;
    var forwardSpeedMultiplier =
      slowdownRemainingMs > 0 ? Constants.slowdownMultiplier : 1;
    var knockbackOffsetX = 0;
    var shakeOffsetY = 0;
    if (shakeRemainingMs > 0) {
      knockbackOffsetX =
        (shakeRemainingMs / Constants.shakeDurationMs) * Constants.knockbackDistance;
      var elapsed = Constants.shakeDurationMs - shakeRemainingMs;
      var tick = Math.floor(elapsed / 50);
      shakeOffsetY = tick % 2 === 0 ? -6 : 6;
    }
    return freeze({
      active: state.active,
      missionId: state.missionId,
      collisionCount: state.collisionCount,
      lastCollisionObstacleId: state.lastCollisionObstacleId,
      slowdownRemainingMs: slowdownRemainingMs,
      forwardSpeedMultiplier: forwardSpeedMultiplier,
      shakeRemainingMs: shakeRemainingMs,
      knockbackOffsetX: knockbackOffsetX,
      shakeOffsetY: shakeOffsetY,
      collisionActive: shakeRemainingMs > 0
    });
  }

  function start(missionId) {
    var layout = getLayout(missionId);
    if (layout === null) {
      return false;
    }
    state.active = true;
    state.missionId = layout.missionId;
    state.collisionCount = 0;
    state.lastCollisionObstacleId = null;
    state.slowdownRemainingMs = 0;
    state.shakeRemainingMs = 0;
    activeContacts = {};
    cooldowns = {};
    return true;
  }

  function stop() {
    if (!state.active) {
      return false;
    }
    state.active = false;
    state.slowdownRemainingMs = 0;
    state.shakeRemainingMs = 0;
    activeContacts = {};
    cooldowns = {};
    return true;
  }

  function isValidTravelSnapshot(snapshot) {
    if (!snapshot || typeof snapshot !== "object") {
      return false;
    }
    if (snapshot.active !== true) {
      return false;
    }
    if (!isFiniteNumber(snapshot.distance)) {
      return false;
    }
    if (!isFiniteNumber(snapshot.y)) {
      return false;
    }
    return true;
  }

  function aabbIntersects(gupX, gupY, obstacle) {
    if (
      Math.abs(gupX - obstacle.worldX) >
        Constants.gupHalfWidth + obstacle.width / 2
    ) {
      return false;
    }
    if (
      Math.abs(gupY - obstacle.y) >
        Constants.gupHalfHeight + obstacle.height / 2
    ) {
      return false;
    }
    return true;
  }

  function triggerCollision(obstacle) {
    state.collisionCount += 1;
    state.lastCollisionObstacleId = obstacle.id;
    state.slowdownRemainingMs = Constants.slowdownDurationMs;
    state.shakeRemainingMs = Constants.shakeDurationMs;
    cooldowns[obstacle.id] = Constants.sameObstacleCooldownMs;
  }

  function step(deltaMs, travelSnapshot) {
    if (!state.active) {
      return false;
    }
    if (!isFiniteNumber(deltaMs) || deltaMs <= 0) {
      return false;
    }
    if (!isValidTravelSnapshot(travelSnapshot)) {
      return false;
    }
    var applied = deltaMs;
    if (applied > 50) {
      applied = 50;
    }
    for (var id in cooldowns) {
      if (Object.prototype.hasOwnProperty.call(cooldowns, id)) {
        cooldowns[id] -= applied;
        if (cooldowns[id] <= 0) {
          delete cooldowns[id];
        }
      }
    }
    if (state.slowdownRemainingMs > 0) {
      state.slowdownRemainingMs -= applied;
      if (state.slowdownRemainingMs < 0) {
        state.slowdownRemainingMs = 0;
      }
    }
    if (state.shakeRemainingMs > 0) {
      state.shakeRemainingMs -= applied;
      if (state.shakeRemainingMs < 0) {
        state.shakeRemainingMs = 0;
      }
    }
    var layout = getLayout(state.missionId);
    if (layout === null) {
      return true;
    }
    var obstacles = layout.obstacles;
    var gupX = travelSnapshot.distance + Constants.gupScreenX;
    var gupY = travelSnapshot.y;
    for (var i = 0; i < obstacles.length; i += 1) {
      var obstacle = obstacles[i];
      if (aabbIntersects(gupX, gupY, obstacle)) {
        if (activeContacts[obstacle.id]) {
          continue;
        }
        activeContacts[obstacle.id] = true;
        if (!cooldowns[obstacle.id]) {
          triggerCollision(obstacle);
          break;
        }
      } else if (activeContacts[obstacle.id]) {
        delete activeContacts[obstacle.id];
      }
    }
    return true;
  }

  root.Terrain = freeze({
    Constants: Constants,
    Layouts: Layouts,
    getLayout: getLayout,
    getSnapshot: getSnapshot,
    start: start,
    stop: stop,
    step: step
  });
})();
