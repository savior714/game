(function () {
  var root = window.OceanRescue = window.OceanRescue || {};

  function freeze(value) {
    return Object.freeze(value);
  }

  var MissionId = "sea-turtle";

  var Constants = freeze({
    baseEndpointRadius: 54,
    assistedEndpointRadius: 74,
    basePathTolerance: 70,
    assistedPathTolerance: 100,
    tapMovementThreshold: 10,
    minimumTraceProgress: 0.85,
    maxBackwardProgress: 0.12,
    successFeedbackMs: 400,
    failureFeedbackMs: 300
  });

  var Ropes = freeze([
    freeze({
      id: "rope-1",
      order: 1,
      start: freeze({ x: 760, y: 300 }),
      end: freeze({ x: 1040, y: 330 })
    }),
    freeze({
      id: "rope-2",
      order: 2,
      start: freeze({ x: 750, y: 420 }),
      end: freeze({ x: 1050, y: 440 })
    }),
    freeze({
      id: "rope-3",
      order: 3,
      start: freeze({ x: 770, y: 540 }),
      end: freeze({ x: 1030, y: 570 })
    })
  ]);

  var Dialogues = freeze([
    "Good start, Aiden! Two ropes left.",
    "Well done! One rope left.",
    "Great work, Aiden! The turtle is free!"
  ]);

  var state = {
    active: false,
    activeRopeId: null,
    completedRopeIds: [],
    failureCount: 0,
    helpLevel: 0,
    tapStartArmed: false,
    pointerActive: false,
    pointerId: null,
    pointerX: null,
    pointerY: null,
    gestureStartX: null,
    gestureStartY: null,
    gestureMoved: false,
    gestureTraceFailed: false,
    gestureMaxProjection: 0,
    inputLocked: true,
    feedback: null,
    feedbackRopeId: null,
    complete: false
  };

  function isFiniteNumber(value) {
    return typeof value === "number" && isFinite(value);
  }

  function ropeById(ropeId) {
    if (typeof ropeId !== "string") {
      return null;
    }
    for (var i = 0; i < Ropes.length; i += 1) {
      if (Ropes[i].id === ropeId) {
        return Ropes[i];
      }
    }
    return null;
  }

  function ropeAfter(ropeId) {
    for (var i = 0; i < Ropes.length - 1; i += 1) {
      if (Ropes[i].id === ropeId) {
        return Ropes[i + 1];
      }
    }
    return null;
  }

  function currentRope() {
    return ropeById(state.activeRopeId);
  }

  function endpointRadius() {
    if (state.helpLevel >= 2) {
      return Constants.assistedEndpointRadius;
    }
    return Constants.baseEndpointRadius;
  }

  function pathTolerance() {
    if (state.helpLevel >= 3) {
      return Constants.assistedPathTolerance;
    }
    return Constants.basePathTolerance;
  }

  function distanceBetween(x1, y1, x2, y2) {
    var dx = x2 - x1;
    var dy = y2 - y1;
    return Math.sqrt(dx * dx + dy * dy);
  }

  function insideStartRadius(rope, x, y) {
    return distanceBetween(x, y, rope.start.x, rope.start.y) <= endpointRadius();
  }

  function insideEndpointRadius(rope, x, y) {
    return distanceBetween(x, y, rope.end.x, rope.end.y) <= endpointRadius();
  }

  function traceMetrics(rope, x, y) {
    var dx = rope.end.x - rope.start.x;
    var dy = rope.end.y - rope.start.y;
    var lengthSq = dx * dx + dy * dy;
    var dot = (x - rope.start.x) * dx + (y - rope.start.y) * dy;
    var projection = lengthSq === 0 ? 0 : dot / lengthSq;
    var perpX = (x - rope.start.x) - projection * dx;
    var perpY = (y - rope.start.y) - projection * dy;
    return {
      projection: projection,
      perpDistance: Math.sqrt(perpX * perpX + perpY * perpY)
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
    state.activeRopeId = null;
    state.completedRopeIds = [];
    state.failureCount = 0;
    state.helpLevel = 0;
    state.tapStartArmed = false;
    state.inputLocked = true;
    state.feedback = null;
    state.feedbackRopeId = null;
    state.complete = false;
    resetGesture();
  }

  function updateTraceMetrics(rope, x, y) {
    var metrics = traceMetrics(rope, x, y);
    if (metrics.perpDistance > pathTolerance()) {
      state.gestureTraceFailed = true;
      return;
    }
    if (metrics.projection < state.gestureMaxProjection - Constants.maxBackwardProgress) {
      state.gestureTraceFailed = true;
      return;
    }
    if (metrics.projection > state.gestureMaxProjection) {
      state.gestureMaxProjection = metrics.projection;
    }
  }

  function completeRope(rope) {
    if (state.completedRopeIds.indexOf(rope.id) === -1) {
      state.completedRopeIds.push(rope.id);
    }
    state.feedback = "success";
    state.feedbackRopeId = rope.id;
    state.inputLocked = true;
    state.tapStartArmed = false;
    resetGesture();
    return freeze({ accepted: true, outcome: "success", ropeId: rope.id });
  }

  function failRope(rope) {
    state.failureCount += 1;
    if (state.failureCount >= 3) {
      state.helpLevel = 3;
    } else {
      state.helpLevel = state.failureCount;
    }
    state.feedback = "failure";
    state.feedbackRopeId = rope.id;
    state.inputLocked = true;
    state.tapStartArmed = false;
    resetGesture();
    return freeze({ accepted: true, outcome: "failure", ropeId: rope.id });
  }

  function finishTap(rope, x, y) {
    if (!state.tapStartArmed) {
      if (insideStartRadius(rope, x, y)) {
        state.tapStartArmed = true;
        resetGesture();
        return freeze({ accepted: true, outcome: "none", ropeId: rope.id });
      }
      return failRope(rope);
    }
    if (insideEndpointRadius(rope, x, y)) {
      return completeRope(rope);
    }
    state.tapStartArmed = false;
    return failRope(rope);
  }

  function finishTrace(rope) {
    if (!state.gestureTraceFailed) {
      if (!insideStartRadius(rope, state.gestureStartX, state.gestureStartY)) {
        state.gestureTraceFailed = true;
      }
    }
    if (!state.gestureTraceFailed) {
      var metrics = traceMetrics(rope, state.pointerX, state.pointerY);
      if (metrics.perpDistance > pathTolerance()) {
        state.gestureTraceFailed = true;
      }
      if (metrics.projection > state.gestureMaxProjection) {
        state.gestureMaxProjection = metrics.projection;
      }
    }
    if (!state.gestureTraceFailed) {
      if (!insideEndpointRadius(rope, state.pointerX, state.pointerY)) {
        state.gestureTraceFailed = true;
      }
    }
    if (!state.gestureTraceFailed) {
      if (state.gestureMaxProjection < Constants.minimumTraceProgress) {
        state.gestureTraceFailed = true;
      }
    }
    if (state.gestureTraceFailed) {
      return failRope(rope);
    }
    return completeRope(rope);
  }

  function start() {
    resetAllInteractionState();
    state.active = true;
    state.activeRopeId = Ropes[0].id;
    state.inputLocked = false;
    return true;
  }

  function stop() {
    if (!state.active) {
      return false;
    }
    state.active = false;
    state.activeRopeId = null;
    state.tapStartArmed = false;
    state.feedback = null;
    state.feedbackRopeId = null;
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
    state.pointerX = x;
    state.pointerY = y;
    var rope = currentRope();
    if (rope === null) {
      return false;
    }
    if (!state.gestureMoved) {
      var displacement = distanceBetween(x, y, state.gestureStartX, state.gestureStartY);
      if (displacement > Constants.tapMovementThreshold) {
        state.gestureMoved = true;
        if (!insideStartRadius(rope, state.gestureStartX, state.gestureStartY)) {
          state.gestureTraceFailed = true;
        }
      }
    }
    if (state.gestureMoved && !state.gestureTraceFailed) {
      updateTraceMetrics(rope, x, y);
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
    var rope = currentRope();
    if (rope === null) {
      resetGesture();
      return freeze({ accepted: false, outcome: "none", ropeId: null });
    }
    var displacement = distanceBetween(x, y, state.gestureStartX, state.gestureStartY);
    if (displacement > Constants.tapMovementThreshold && !state.gestureMoved) {
      state.gestureMoved = true;
      if (!insideStartRadius(rope, state.gestureStartX, state.gestureStartY)) {
        state.gestureTraceFailed = true;
      }
    }
    if (state.gestureMoved) {
      return finishTrace(rope);
    }
    return finishTap(rope, x, y);
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
    if (state.feedback === null || state.feedbackRopeId === null) {
      return freeze({ changed: false, complete: state.complete, nextRopeId: null });
    }
    var kind = state.feedback;
    var ropeId = state.feedbackRopeId;
    state.feedback = null;
    state.feedbackRopeId = null;
    if (kind === "failure") {
      state.inputLocked = false;
      return freeze({ changed: true, complete: false, nextRopeId: ropeId });
    }
    if (kind === "success") {
      var next = ropeAfter(ropeId);
      if (next === null) {
        state.complete = true;
        state.active = false;
        state.activeRopeId = null;
        state.inputLocked = true;
        return freeze({ changed: true, complete: true, nextRopeId: null });
      }
      state.activeRopeId = next.id;
      state.failureCount = 0;
      state.helpLevel = 0;
      state.inputLocked = false;
      return freeze({ changed: true, complete: false, nextRopeId: next.id });
    }
    return freeze({ changed: false, complete: state.complete, nextRopeId: null });
  }

  function getSnapshot() {
    return freeze({
      active: state.active,
      activeRopeId: state.activeRopeId,
      completedRopeIds: freeze(state.completedRopeIds.slice()),
      failureCount: state.failureCount,
      helpLevel: state.helpLevel,
      tapStartArmed: state.tapStartArmed,
      pointerActive: state.pointerActive,
      inputLocked: state.inputLocked,
      feedback: state.feedback,
      complete: state.complete
    });
  }

  root.SeaTurtle = freeze({
    MissionId: MissionId,
    Constants: Constants,
    Ropes: Ropes,
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
