(function () {
  var root = window.OceanRescue = window.OceanRescue || {};

  function freeze(value) {
    return Object.freeze(value);
  }

  var MissionId = "crab";

  var Constants = freeze({
    holdDurationMs: 400,
    tapMovementThreshold: 10,
    baseHitRadius: 60,
    assistedHitRadius: 82,
    assistedZoneMargin: 48,
    successFeedbackMs: 400,
    failureFeedbackMs: 300
  });

  var Rocks = freeze([
    freeze({
      id: "rock-1",
      order: 1,
      radius: 46,
      start: freeze({ x: 760, y: 300 }),
      placed: freeze({ x: 1000, y: 360 })
    }),
    freeze({
      id: "rock-2",
      order: 2,
      radius: 52,
      start: freeze({ x: 720, y: 420 }),
      placed: freeze({ x: 1090, y: 450 })
    }),
    freeze({
      id: "rock-3",
      order: 3,
      radius: 58,
      start: freeze({ x: 770, y: 540 }),
      placed: freeze({ x: 1000, y: 540 })
    })
  ]);

  var DropZone = freeze({
    x: 900,
    y: 280,
    width: 300,
    height: 320
  });

  var Dialogues = freeze([
    "Great lift! Two rocks left, and the crab can see us.",
    "One more rock! The crab is getting up.",
    "All clear! The crab is free!"
  ]);

  var state = {
    active: false,
    activeRockId: null,
    completedRockIds: [],
    failureCount: 0,
    helpLevel: 0,
    tapRockArmed: false,
    pointerActive: false,
    pointerId: null,
    pointerX: null,
    pointerY: null,
    gestureStartX: null,
    gestureStartY: null,
    gesturePhase: "idle",
    gestureMoved: false,
    gestureFailed: false,
    currentRockCenter: null,
    inputLocked: true,
    feedback: null,
    feedbackRockId: null,
    complete: false
  };

  function isFiniteNumber(value) {
    return typeof value === "number" && isFinite(value);
  }

  function rockById(rockId) {
    if (typeof rockId !== "string") {
      return null;
    }
    for (var i = 0; i < Rocks.length; i += 1) {
      if (Rocks[i].id === rockId) {
        return Rocks[i];
      }
    }
    return null;
  }

  function rockAfter(rockId) {
    for (var i = 0; i < Rocks.length - 1; i += 1) {
      if (Rocks[i].id === rockId) {
        return Rocks[i + 1];
      }
    }
    return null;
  }

  function currentRock() {
    return rockById(state.activeRockId);
  }

  function hitRadius() {
    if (state.helpLevel >= 2) {
      return Constants.assistedHitRadius;
    }
    return Constants.baseHitRadius;
  }

  function distanceBetween(x1, y1, x2, y2) {
    var dx = x2 - x1;
    var dy = y2 - y1;
    return Math.sqrt(dx * dx + dy * dy);
  }

  function insideRockHitRadius(rock, x, y) {
    return distanceBetween(x, y, rock.start.x, rock.start.y) <= hitRadius();
  }

  function pointInDropZone(x, y) {
    var margin = state.helpLevel >= 3 ? Constants.assistedZoneMargin : 0;
    var x1 = DropZone.x - DropZone.width / 2 - margin;
    var x2 = DropZone.x + DropZone.width / 2 + margin;
    var y1 = DropZone.y - DropZone.height / 2 - margin;
    var y2 = DropZone.y + DropZone.height / 2 + margin;
    return x >= x1 && x <= x2 && y >= y1 && y <= y2;
  }

  function resetPointerGesture() {
    state.pointerActive = false;
    state.pointerId = null;
    state.pointerX = null;
    state.pointerY = null;
    state.gestureStartX = null;
    state.gestureStartY = null;
    state.gesturePhase = "idle";
    state.gestureMoved = false;
    state.gestureFailed = false;
    var rock = currentRock();
    if (rock !== null) {
      if (state.completedRockIds.indexOf(rock.id) !== -1) {
        state.currentRockCenter = { x: rock.placed.x, y: rock.placed.y };
      } else {
        state.currentRockCenter = { x: rock.start.x, y: rock.start.y };
      }
    }
  }

  function resetAllInteractionState() {
    state.active = false;
    state.activeRockId = null;
    state.completedRockIds = [];
    state.failureCount = 0;
    state.helpLevel = 0;
    state.tapRockArmed = false;
    state.currentRockCenter = null;
    state.inputLocked = true;
    state.feedback = null;
    state.feedbackRockId = null;
    state.complete = false;
    resetPointerGesture();
  }

  function completeRock(rock) {
    if (state.completedRockIds.indexOf(rock.id) === -1) {
      state.completedRockIds.push(rock.id);
    }
    state.currentRockCenter = { x: rock.placed.x, y: rock.placed.y };
    state.feedback = "success";
    state.feedbackRockId = rock.id;
    state.inputLocked = true;
    state.tapRockArmed = false;
    return freeze({ accepted: true, outcome: "success", rockId: rock.id });
  }

  function failRock(rock) {
    state.failureCount += 1;
    if (state.failureCount >= 3) {
      state.helpLevel = 3;
    } else {
      state.helpLevel = state.failureCount;
    }
    state.feedback = "failure";
    state.feedbackRockId = rock.id;
    state.inputLocked = true;
    state.tapRockArmed = false;
    state.currentRockCenter = { x: rock.start.x, y: rock.start.y };
    return freeze({ accepted: true, outcome: "failure", rockId: rock.id });
  }

  function start() {
    resetAllInteractionState();
    state.active = true;
    state.activeRockId = Rocks[0].id;
    state.currentRockCenter = {
      x: Rocks[0].start.x,
      y: Rocks[0].start.y
    };
    state.inputLocked = false;
    return true;
  }

  function stop() {
    if (!state.active) {
      return false;
    }
    state.active = false;
    state.activeRockId = null;
    state.currentRockCenter = null;
    state.tapRockArmed = false;
    state.feedback = null;
    state.feedbackRockId = null;
    state.inputLocked = true;
    resetPointerGesture();
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
    state.gesturePhase = "idle";
    state.gestureMoved = false;
    state.gestureFailed = false;
    var rock = currentRock();
    if (rock === null) {
      return false;
    }
    if (insideRockHitRadius(rock, x, y)) {
      state.gesturePhase = "holding";
    }
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
    var displacement = distanceBetween(
      x,
      y,
      state.gestureStartX,
      state.gestureStartY
    );
    if (displacement > Constants.tapMovementThreshold) {
      state.gestureMoved = true;
    }
    if (state.gesturePhase === "holding" && state.gestureMoved) {
      state.gestureFailed = true;
    }
    if (state.gesturePhase === "grabbed") {
      state.currentRockCenter = { x: x, y: y };
    }
    return true;
  }

  function finishHold() {
    if (!state.active) {
      return freeze({ accepted: false, outcome: "none", rockId: null });
    }
    if (state.inputLocked) {
      return freeze({ accepted: false, outcome: "none", rockId: null });
    }
    if (!state.pointerActive) {
      return freeze({ accepted: false, outcome: "none", rockId: null });
    }
    if (state.gesturePhase !== "holding") {
      return freeze({ accepted: false, outcome: "none", rockId: null });
    }
    if (state.gestureFailed || state.gestureMoved) {
      return freeze({ accepted: false, outcome: "none", rockId: null });
    }
    var rock = currentRock();
    if (rock === null) {
      return freeze({ accepted: false, outcome: "none", rockId: null });
    }
    state.gesturePhase = "grabbed";
    state.currentRockCenter = { x: state.pointerX, y: state.pointerY };
    return freeze({ accepted: true, outcome: "grabbed", rockId: rock.id });
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
    var rock = currentRock();
    var phase = state.gesturePhase;
    var moved = state.gestureMoved;
    var failed = state.gestureFailed;
    resetPointerGesture();
    if (rock === null) {
      return freeze({ accepted: false, outcome: "none", rockId: null });
    }
    if (phase === "grabbed") {
      if (pointInDropZone(x, y)) {
        return completeRock(rock);
      }
      return failRock(rock);
    }
    if (phase === "holding") {
      if (failed || moved) {
        return failRock(rock);
      }
      if (!state.tapRockArmed) {
        state.tapRockArmed = true;
        return freeze({ accepted: true, outcome: "none", rockId: rock.id });
      }
      return failRock(rock);
    }
    if (moved) {
      if (state.tapRockArmed) {
        return failRock(rock);
      }
      return freeze({ accepted: true, outcome: "none", rockId: rock.id });
    }
    if (state.tapRockArmed) {
      if (pointInDropZone(x, y)) {
        return completeRock(rock);
      }
      return failRock(rock);
    }
    if (pointInDropZone(x, y)) {
      return failRock(rock);
    }
    return freeze({ accepted: true, outcome: "none", rockId: rock.id });
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
    resetPointerGesture();
    return true;
  }

  function pauseCancel() {
    if (!state.active) {
      return;
    }
    state.pointerActive = false;
    state.pointerId = null;
    state.pointerX = null;
    state.pointerY = null;
    state.gestureStartX = null;
    state.gestureStartY = null;
    state.gesturePhase = "idle";
    state.gestureMoved = false;
    state.gestureFailed = false;
    state.tapRockArmed = false;
    var rock = currentRock();
    if (rock !== null) {
      state.currentRockCenter = {
        x: rock.start.x,
        y: rock.start.y
      };
    }
  }

  function finishFeedback() {
    if (state.feedback === null || state.feedbackRockId === null) {
      return freeze({
        changed: false,
        complete: state.complete,
        nextRockId: null
      });
    }
    var kind = state.feedback;
    var rockId = state.feedbackRockId;
    state.feedback = null;
    state.feedbackRockId = null;
    if (kind === "failure") {
      state.inputLocked = false;
      var failedRock = rockById(rockId);
      if (failedRock !== null) {
        state.currentRockCenter = {
          x: failedRock.start.x,
          y: failedRock.start.y
        };
      }
      return freeze({
        changed: true,
        complete: false,
        nextRockId: rockId
      });
    }
    if (kind === "success") {
      state.failureCount = 0;
      state.helpLevel = 0;
      var next = rockAfter(rockId);
      if (next === null) {
        state.complete = true;
        state.active = false;
        state.activeRockId = null;
        state.currentRockCenter = null;
        state.inputLocked = true;
        return freeze({
          changed: true,
          complete: true,
          nextRockId: null
        });
      }
      state.activeRockId = next.id;
      state.failureCount = 0;
      state.helpLevel = 0;
      state.currentRockCenter = {
        x: next.start.x,
        y: next.start.y
      };
      state.inputLocked = false;
      return freeze({
        changed: true,
        complete: false,
        nextRockId: next.id
      });
    }
    return freeze({
      changed: false,
      complete: state.complete,
      nextRockId: null
    });
  }

  function getSnapshot() {
    return freeze({
      active: state.active,
      activeRockId: state.activeRockId,
      completedRockIds: freeze(state.completedRockIds.slice()),
      failureCount: state.failureCount,
      helpLevel: state.helpLevel,
      tapRockArmed: state.tapRockArmed,
      pointerActive: state.pointerActive,
      holding: state.gesturePhase === "holding",
      grabbed: state.gesturePhase === "grabbed",
      currentRockCenter:
        state.currentRockCenter === null
          ? null
          : freeze({
              x: state.currentRockCenter.x,
              y: state.currentRockCenter.y
            }),
      inputLocked: state.inputLocked,
      feedback: state.feedback,
      complete: state.complete
    });
  }

  root.Crab = freeze({
    MissionId: MissionId,
    Constants: Constants,
    Rocks: Rocks,
    DropZone: DropZone,
    Dialogues: Dialogues,
    getSnapshot: getSnapshot,
    start: start,
    stop: stop,
    pointerDown: pointerDown,
    finishHold: finishHold,
    pointerMove: pointerMove,
    pointerUp: pointerUp,
    pointerCancel: pointerCancel,
    finishFeedback: finishFeedback,
    pauseCancel: pauseCancel
  });
})();
