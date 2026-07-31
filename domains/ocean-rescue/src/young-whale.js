(function () {
  var root = window.OceanRescue = window.OceanRescue || {};

  function freeze(value) {
    return Object.freeze(value);
  }

  var MissionId = "young-whale";

  var Constants = freeze({
    connectionStartRadius: 60,
    assistedConnectionStartRadius: 82,
    hookRadius: 60,
    assistedHookRadius: 82,
    connectionPathTolerance: 90,
    assistedConnectionPathTolerance: 130,
    minimumConnectionProgress: 0.88,
    maxBackwardProgress: 0.12,

    gupHitRadius: 72,
    assistedGupHitRadius: 94,
    safeSpotRadius: 72,
    assistedSafeSpotRadius: 104,
    towingPathTolerance: 130,
    assistedTowingPathTolerance: 180,
    wrongDirectionDistance: 80,

    pointerMovementThreshold: 10,
    successFeedbackMs: 400,
    failureFeedbackMs: 300
  });

  var Instructions = freeze({
    connection: "Drag from the debris to the GUP hook!",
    towing: "Drag the GUP to the safe spot!"
  });

  var GupStart = freeze({ x: 340, y: 420 });
  var GupHook = freeze({ x: 275, y: 420 });

  var Debris = freeze([
    freeze({
      id: "debris-1",
      order: 1,
      radius: 44,
      start: freeze({ x: 820, y: 260 }),
      connection: freeze({ x: 780, y: 260 }),
      safeSpot: freeze({ x: 180, y: 190 }),
      cleared: freeze({ x: 680, y: 30 })
    }),
    freeze({
      id: "debris-2",
      order: 2,
      radius: 52,
      start: freeze({ x: 880, y: 420 }),
      connection: freeze({ x: 830, y: 420 }),
      safeSpot: freeze({ x: 160, y: 420 }),
      cleared: freeze({ x: 700, y: 420 })
    }),
    freeze({
      id: "debris-3",
      order: 3,
      radius: 60,
      start: freeze({ x: 930, y: 550 }),
      connection: freeze({ x: 875, y: 550 }),
      safeSpot: freeze({ x: 180, y: 610 }),
      cleared: freeze({ x: 770, y: 740 })
    })
  ]);

  var Dialogues = freeze([
    "Good work, Aiden! Two pieces left. The whale knows we\u2019re here.",
    "Just one more! The whale is moving toward the opening.",
    "The path is clear! Let\u2019s give the whale room to swim."
  ]);

  var state = {
    active: false,
    activeDebrisId: null,
    completedDebrisIds: [],
    stage: null,
    connected: false,
    failureCount: 0,
    helpLevel: 0,
    pointerActive: false,
    pointerId: null,
    pointerX: null,
    pointerY: null,
    gestureStartX: null,
    gestureStartY: null,
    gestureMoved: false,
    gestureTraceFailed: false,
    gestureMaxProjection: 0,
    currentGupCenter: null,
    currentDebrisCenter: null,
    inputLocked: true,
    feedback: null,
    feedbackDebrisId: null,
    complete: false
  };

  function isFiniteNumber(value) {
    return typeof value === "number" && isFinite(value);
  }

  function debrisById(debrisId) {
    if (typeof debrisId !== "string") {
      return null;
    }
    for (var i = 0; i < Debris.length; i += 1) {
      if (Debris[i].id === debrisId) {
        return Debris[i];
      }
    }
    return null;
  }

  function debrisAfter(debrisId) {
    for (var i = 0; i < Debris.length - 1; i += 1) {
      if (Debris[i].id === debrisId) {
        return Debris[i + 1];
      }
    }
    return null;
  }

  function activeDebris() {
    return debrisById(state.activeDebrisId);
  }

  function distanceBetween(x1, y1, x2, y2) {
    var dx = x2 - x1;
    var dy = y2 - y1;
    return Math.sqrt(dx * dx + dy * dy);
  }

  function connectionStartRadius() {
    if (state.helpLevel >= 2) {
      return Constants.assistedConnectionStartRadius;
    }
    return Constants.connectionStartRadius;
  }

  function hookRadius() {
    if (state.helpLevel >= 2) {
      return Constants.assistedHookRadius;
    }
    return Constants.hookRadius;
  }

  function connectionPathTolerance() {
    if (state.helpLevel >= 3) {
      return Constants.assistedConnectionPathTolerance;
    }
    return Constants.connectionPathTolerance;
  }

  function gupHitRadius() {
    if (state.helpLevel >= 2) {
      return Constants.assistedGupHitRadius;
    }
    return Constants.gupHitRadius;
  }

  function safeSpotRadius() {
    if (state.helpLevel >= 3) {
      return Constants.assistedSafeSpotRadius;
    }
    return Constants.safeSpotRadius;
  }

  function towingPathTolerance() {
    if (state.helpLevel >= 3) {
      return Constants.assistedTowingPathTolerance;
    }
    return Constants.towingPathTolerance;
  }

  function insideConnectionStartRadius(debris, x, y) {
    return (
      distanceBetween(x, y, debris.connection.x, debris.connection.y) <=
      connectionStartRadius()
    );
  }

  function insideHookRadius(x, y) {
    return distanceBetween(x, y, GupHook.x, GupHook.y) <= hookRadius();
  }

  function insideGupHitRadius(x, y) {
    return distanceBetween(x, y, GupStart.x, GupStart.y) <= gupHitRadius();
  }

  function insideSafeSpot(debris, x, y) {
    return (
      distanceBetween(x, y, debris.safeSpot.x, debris.safeSpot.y) <=
      safeSpotRadius()
    );
  }

  function connectionTraceMetrics(debris, x, y) {
    var dx = GupHook.x - debris.connection.x;
    var dy = GupHook.y - debris.connection.y;
    var lengthSq = dx * dx + dy * dy;
    var dot = (x - debris.connection.x) * dx + (y - debris.connection.y) * dy;
    var projection = lengthSq === 0 ? 0 : dot / lengthSq;
    var perpX = x - debris.connection.x - projection * dx;
    var perpY = y - debris.connection.y - projection * dy;
    return {
      projection: projection,
      perpDistance: Math.sqrt(perpX * perpX + perpY * perpY)
    };
  }

  function towingMetrics(debris, x, y) {
    var dx = debris.safeSpot.x - GupStart.x;
    var dy = debris.safeSpot.y - GupStart.y;
    var lengthSq = dx * dx + dy * dy;
    var length = Math.sqrt(lengthSq) || 1;
    var dot = (x - GupStart.x) * dx + (y - GupStart.y) * dy;
    var projection = lengthSq === 0 ? 0 : dot / lengthSq;
    var perpX = x - GupStart.x - projection * dx;
    var perpY = y - GupStart.y - projection * dy;
    return {
      projection: projection,
      perpDistance: Math.sqrt(perpX * perpX + perpY * perpY),
      forward: projection * length
    };
  }

  function resetGesture() {
    state.pointerActive = false;
    state.pointerId = null;
    state.pointerX = null;
    state.pointerY = null;
    state.gestureStartX = null;
    state.gestureStartY = null;
    state.gestureMoved = false;
    state.gestureTraceFailed = false;
    state.gestureMaxProjection = 0;
  }

  function resetAllInteractionState() {
    state.active = false;
    state.activeDebrisId = null;
    state.completedDebrisIds = [];
    state.stage = null;
    state.connected = false;
    state.failureCount = 0;
    state.helpLevel = 0;
    state.currentGupCenter = null;
    state.currentDebrisCenter = null;
    state.inputLocked = true;
    state.feedback = null;
    state.feedbackDebrisId = null;
    state.complete = false;
    resetGesture();
  }

  function updateConnectionTrace(debris, x, y) {
    var metrics = connectionTraceMetrics(debris, x, y);
    if (metrics.perpDistance > connectionPathTolerance()) {
      state.gestureTraceFailed = true;
      return;
    }
    if (
      metrics.projection <
      state.gestureMaxProjection - Constants.maxBackwardProgress
    ) {
      state.gestureTraceFailed = true;
      return;
    }
    if (metrics.projection > state.gestureMaxProjection) {
      state.gestureMaxProjection = metrics.projection;
    }
  }

  function updateTowingMetrics(debris, x, y) {
    var metrics = towingMetrics(debris, x, y);
    if (metrics.perpDistance > towingPathTolerance()) {
      state.gestureTraceFailed = true;
      return;
    }
    if (metrics.forward < -Constants.wrongDirectionDistance) {
      state.gestureTraceFailed = true;
    }
  }

  function failConnection(debris) {
    state.failureCount += 1;
    if (state.failureCount >= 3) {
      state.helpLevel = 3;
    } else {
      state.helpLevel = state.failureCount;
    }
    state.feedback = "failure";
    state.feedbackDebrisId = debris.id;
    state.inputLocked = true;
    state.connected = false;
    resetGesture();
    return freeze({ accepted: true, outcome: "failure", debrisId: debris.id });
  }

  function failTowing(debris) {
    state.failureCount += 1;
    if (state.failureCount >= 3) {
      state.helpLevel = 3;
    } else {
      state.helpLevel = state.failureCount;
    }
    state.feedback = "failure";
    state.feedbackDebrisId = debris.id;
    state.inputLocked = true;
    state.currentGupCenter = { x: GupStart.x, y: GupStart.y };
    state.currentDebrisCenter = { x: debris.start.x, y: debris.start.y };
    resetGesture();
    return freeze({ accepted: true, outcome: "failure", debrisId: debris.id });
  }

  function completeConnection(debris) {
    state.feedback = "success";
    state.feedbackDebrisId = debris.id;
    state.inputLocked = true;
    state.connected = true;
    resetGesture();
    return freeze({ accepted: true, outcome: "success", debrisId: debris.id });
  }

  function completeTow(debris) {
    if (state.completedDebrisIds.indexOf(debris.id) === -1) {
      state.completedDebrisIds.push(debris.id);
    }
    state.feedback = "success";
    state.feedbackDebrisId = debris.id;
    state.inputLocked = true;
    state.connected = true;
    state.currentDebrisCenter = { x: debris.cleared.x, y: debris.cleared.y };
    resetGesture();
    return freeze({ accepted: true, outcome: "success", debrisId: debris.id });
  }

  function finishConnection(debris, x, y) {
    if (!state.gestureMoved) {
      return failConnection(debris);
    }
    if (state.gestureTraceFailed) {
      return failConnection(debris);
    }
    if (!insideConnectionStartRadius(debris, state.gestureStartX, state.gestureStartY)) {
      return failConnection(debris);
    }
    var metrics = connectionTraceMetrics(debris, x, y);
    if (metrics.projection > state.gestureMaxProjection) {
      state.gestureMaxProjection = metrics.projection;
    }
    if (metrics.perpDistance > connectionPathTolerance()) {
      return failConnection(debris);
    }
    if (!insideHookRadius(x, y)) {
      return failConnection(debris);
    }
    if (state.gestureMaxProjection < Constants.minimumConnectionProgress) {
      return failConnection(debris);
    }
    return completeConnection(debris);
  }

  function finishTowing(debris, x, y) {
    if (!state.gestureMoved) {
      return failTowing(debris);
    }
    if (state.gestureTraceFailed) {
      return failTowing(debris);
    }
    if (!insideGupHitRadius(state.gestureStartX, state.gestureStartY)) {
      return failTowing(debris);
    }
    var metrics = towingMetrics(debris, x, y);
    if (metrics.perpDistance > towingPathTolerance()) {
      return failTowing(debris);
    }
    if (metrics.forward < -Constants.wrongDirectionDistance) {
      return failTowing(debris);
    }
    if (!insideSafeSpot(debris, x, y)) {
      return failTowing(debris);
    }
    return completeTow(debris);
  }

  function start() {
    resetAllInteractionState();
    state.active = true;
    state.activeDebrisId = Debris[0].id;
    state.stage = "connection";
    state.currentDebrisCenter = {
      x: Debris[0].start.x,
      y: Debris[0].start.y
    };
    state.inputLocked = false;
    return true;
  }

  function stop() {
    if (!state.active) {
      return false;
    }
    state.active = false;
    state.activeDebrisId = null;
    state.stage = null;
    state.connected = false;
    state.currentGupCenter = null;
    state.currentDebrisCenter = null;
    state.feedback = null;
    state.feedbackDebrisId = null;
    state.inputLocked = true;
    resetGesture();
    return true;
  }

  function pointerDown(pointerId, x, y) {
    if (!state.active) {
      return false;
    }
    if (state.inputLocked) {
      return false;
    }
    if (state.pointerActive) {
      return false;
    }
    if (!isFiniteNumber(pointerId)) {
      return false;
    }
    if (!isFiniteNumber(x) || !isFiniteNumber(y)) {
      return false;
    }
    state.pointerActive = true;
    state.pointerId = pointerId;
    state.pointerX = x;
    state.pointerY = y;
    state.gestureStartX = x;
    state.gestureStartY = y;
    state.gestureMoved = false;
    state.gestureTraceFailed = false;
    state.gestureMaxProjection = 0;
    return true;
  }

  function pointerMove(pointerId, x, y) {
    if (!state.active) {
      return false;
    }
    if (state.inputLocked) {
      return false;
    }
    if (!state.pointerActive) {
      return false;
    }
    if (!isFiniteNumber(pointerId)) {
      return false;
    }
    if (pointerId !== state.pointerId) {
      return false;
    }
    if (!isFiniteNumber(x) || !isFiniteNumber(y)) {
      return false;
    }
    var prevX = state.pointerX;
    var prevY = state.pointerY;
    state.pointerX = x;
    state.pointerY = y;
    var debris = activeDebris();
    if (debris === null) {
      return false;
    }
    if (state.stage === "connection") {
      if (!state.gestureMoved) {
        var displacement = distanceBetween(
          x,
          y,
          state.gestureStartX,
          state.gestureStartY
        );
        if (displacement > Constants.pointerMovementThreshold) {
          state.gestureMoved = true;
          if (
            !insideConnectionStartRadius(
              debris,
              state.gestureStartX,
              state.gestureStartY
            )
          ) {
            state.gestureTraceFailed = true;
          }
        }
      }
      if (state.gestureMoved && !state.gestureTraceFailed) {
        updateConnectionTrace(debris, x, y);
      }
      return true;
    }
    if (state.stage === "towing") {
      if (!state.gestureMoved) {
        var towingDisplacement = distanceBetween(
          x,
          y,
          state.gestureStartX,
          state.gestureStartY
        );
        if (towingDisplacement > Constants.pointerMovementThreshold) {
          state.gestureMoved = true;
          if (!insideGupHitRadius(state.gestureStartX, state.gestureStartY)) {
            state.gestureTraceFailed = true;
          }
        }
      }
      if (state.gestureMoved && !state.gestureTraceFailed) {
        var dx = x - prevX;
        var dy = y - prevY;
        if (state.currentGupCenter !== null) {
          state.currentGupCenter = { x: x, y: y };
        }
        if (state.currentDebrisCenter !== null) {
          state.currentDebrisCenter = {
            x: state.currentDebrisCenter.x + dx,
            y: state.currentDebrisCenter.y + dy
          };
        }
        updateTowingMetrics(debris, x, y);
      }
      return true;
    }
    return true;
  }

  function pointerUp(pointerId, x, y) {
    if (!state.active) {
      return false;
    }
    if (state.inputLocked) {
      return false;
    }
    if (!state.pointerActive) {
      return false;
    }
    if (!isFiniteNumber(pointerId)) {
      return false;
    }
    if (pointerId !== state.pointerId) {
      return false;
    }
    if (!isFiniteNumber(x) || !isFiniteNumber(y)) {
      return false;
    }
    state.pointerX = x;
    state.pointerY = y;
    var debris = activeDebris();
    if (debris === null || state.stage === null) {
      resetGesture();
      return freeze({ accepted: false, outcome: "none", debrisId: null });
    }
    if (state.stage === "connection") {
      return finishConnection(debris, x, y);
    }
    if (state.stage === "towing") {
      return finishTowing(debris, x, y);
    }
    resetGesture();
    return freeze({ accepted: false, outcome: "none", debrisId: null });
  }

  function pointerCancel(pointerId) {
    if (!state.pointerActive) {
      return false;
    }
    if (!isFiniteNumber(pointerId)) {
      return false;
    }
    if (pointerId !== state.pointerId) {
      return false;
    }
    resetGesture();
    return true;
  }

  function finishFeedback() {
    if (state.feedback === null || state.feedbackDebrisId === null) {
      return freeze({
        changed: false,
        complete: state.complete,
        nextDebrisId: null
      });
    }
    var kind = state.feedback;
    var debrisId = state.feedbackDebrisId;
    state.feedback = null;
    state.feedbackDebrisId = null;
    var debris = debrisById(debrisId);
    if (kind === "failure") {
      state.inputLocked = false;
      if (state.stage === "towing") {
        state.currentGupCenter = { x: GupStart.x, y: GupStart.y };
        state.currentDebrisCenter =
          debris === null
            ? null
            : { x: debris.start.x, y: debris.start.y };
      } else {
        state.connected = false;
      }
      return freeze({ changed: true, complete: false, nextDebrisId: debrisId });
    }
    if (kind === "success") {
      if (state.stage === "connection") {
        state.stage = "towing";
        state.connected = true;
        state.failureCount = 0;
        state.helpLevel = 0;
        state.currentGupCenter = { x: GupStart.x, y: GupStart.y };
        state.inputLocked = false;
        return freeze({ changed: true, complete: false, nextDebrisId: debrisId });
      }
      var next = debrisAfter(debrisId);
      if (next === null) {
        state.complete = true;
        state.active = false;
        state.activeDebrisId = null;
        state.stage = null;
        state.connected = false;
        state.failureCount = 0;
        state.helpLevel = 0;
        state.currentGupCenter = null;
        state.currentDebrisCenter = null;
        state.inputLocked = true;
        return freeze({ changed: true, complete: true, nextDebrisId: null });
      }
      state.stage = "connection";
      state.connected = false;
      state.activeDebrisId = next.id;
      state.failureCount = 0;
      state.helpLevel = 0;
      state.currentGupCenter = null;
      state.currentDebrisCenter = {
        x: next.start.x,
        y: next.start.y
      };
      state.inputLocked = false;
      return freeze({ changed: true, complete: false, nextDebrisId: next.id });
    }
    return freeze({
      changed: false,
      complete: state.complete,
      nextDebrisId: null
    });
  }

  function getSnapshot() {
    return freeze({
      active: state.active,
      activeDebrisId: state.activeDebrisId,
      completedDebrisIds: freeze(state.completedDebrisIds.slice()),
      stage: state.stage,
      connected: state.connected,
      failureCount: state.failureCount,
      helpLevel: state.helpLevel,
      pointerActive: state.pointerActive,
      currentGupCenter:
        state.currentGupCenter === null
          ? null
          : freeze({
              x: state.currentGupCenter.x,
              y: state.currentGupCenter.y
            }),
      currentDebrisCenter:
        state.currentDebrisCenter === null
          ? null
          : freeze({
              x: state.currentDebrisCenter.x,
              y: state.currentDebrisCenter.y
            }),
      inputLocked: state.inputLocked,
      feedback: state.feedback,
      complete: state.complete
    });
  }

  root.YoungWhale = freeze({
    MissionId: MissionId,
    Constants: Constants,
    Instructions: Instructions,
    GupStart: GupStart,
    GupHook: GupHook,
    Debris: Debris,
    Dialogues: Dialogues,
    getSnapshot: getSnapshot,
    start: start,
    stop: stop,
    pointerDown: pointerDown,
    pointerMove: pointerMove,
    pointerUp: pointerUp,
    pointerCancel: pointerCancel,
    finishFeedback: finishFeedback
  });
})();
