(function () {
  var root = window.OceanRescue = window.OceanRescue || {};

  function freeze(value) {
    return Object.freeze(value);
  }

  var Bounds = freeze({
    minY: 120,
    maxY: 600,
    startY: 360
  });

  var AutoForwardSpeed = 120;
  var TapSpeed = 360;

  var state = {
    active: false,
    distance: 0,
    y: Bounds.startY,
    tapTargetY: null,
    dragging: false,
    pointerId: null
  };

  var dragPointerId = null;
  var dragPrevStageY = 0;

  function clampY(value) {
    if (value < Bounds.minY) {
      return Bounds.minY;
    }
    if (value > Bounds.maxY) {
      return Bounds.maxY;
    }
    return value;
  }

  function isFiniteNumber(value) {
    return typeof value === "number" && isFinite(value);
  }

  function getSnapshot() {
    return freeze({
      active: state.active,
      distance: state.distance,
      y: state.y,
      tapTargetY: state.tapTargetY,
      dragging: state.dragging,
      pointerId: state.pointerId
    });
  }

  function start() {
    state.active = true;
    state.distance = 0;
    state.y = Bounds.startY;
    state.tapTargetY = null;
    state.dragging = false;
    state.pointerId = null;
    dragPointerId = null;
    dragPrevStageY = 0;
    return true;
  }

  function stop() {
    if (!state.active) {
      return false;
    }
    state.active = false;
    state.tapTargetY = null;
    state.dragging = false;
    state.pointerId = null;
    dragPointerId = null;
    return true;
  }

  function step(deltaMs, forwardSpeedMultiplier) {
    if (!state.active) {
      return false;
    }
    if (!isFiniteNumber(deltaMs) || deltaMs <= 0) {
      return false;
    }
    var multiplier = 1;
    if (forwardSpeedMultiplier !== undefined) {
      if (!isFiniteNumber(forwardSpeedMultiplier)) {
        return false;
      }
      if (forwardSpeedMultiplier < 0 || forwardSpeedMultiplier > 1) {
        return false;
      }
      multiplier = forwardSpeedMultiplier;
    }
    var applied = deltaMs;
    if (applied > 50) {
      applied = 50;
    }
    state.distance += AutoForwardSpeed * multiplier * (applied / 1000);
    if (state.tapTargetY !== null) {
      var target = state.tapTargetY;
      var movement = TapSpeed * (applied / 1000);
      if (state.y < target) {
        state.y += movement;
        if (state.y >= target) {
          state.y = target;
          state.tapTargetY = null;
        }
      } else if (state.y > target) {
        state.y -= movement;
        if (state.y <= target) {
          state.y = target;
          state.tapTargetY = null;
        }
      } else {
        state.tapTargetY = null;
      }
    }
    return true;
  }

  function beginDrag(pointerId, stageY) {
    if (!state.active) {
      return false;
    }
    if (!isFiniteNumber(pointerId)) {
      return false;
    }
    if (!isFiniteNumber(stageY)) {
      return false;
    }
    if (state.dragging || dragPointerId !== null) {
      return false;
    }
    state.tapTargetY = null;
    dragPointerId = pointerId;
    dragPrevStageY = clampY(stageY);
    state.dragging = true;
    state.pointerId = pointerId;
    return true;
  }

  function moveDrag(pointerId, stageY) {
    if (!state.active) {
      return false;
    }
    if (pointerId !== dragPointerId) {
      return false;
    }
    if (!isFiniteNumber(stageY)) {
      return false;
    }
    state.y = clampY(state.y + (stageY - dragPrevStageY));
    dragPrevStageY = stageY;
    return true;
  }

  function endDrag(pointerId) {
    if (pointerId !== dragPointerId) {
      return false;
    }
    if (!state.dragging) {
      return false;
    }
    state.dragging = false;
    state.pointerId = null;
    dragPointerId = null;
    return true;
  }

  function tapTo(stageY) {
    if (!state.active) {
      return false;
    }
    if (state.dragging) {
      return false;
    }
    if (!isFiniteNumber(stageY)) {
      return false;
    }
    var target = clampY(stageY);
    if (target === state.y) {
      state.tapTargetY = null;
      return true;
    }
    state.tapTargetY = target;
    return true;
  }

  root.Travel = freeze({
    Bounds: Bounds,
    AutoForwardSpeed: AutoForwardSpeed,
    TapSpeed: TapSpeed,
    getSnapshot: getSnapshot,
    start: start,
    stop: stop,
    step: step,
    beginDrag: beginDrag,
    moveDrag: moveDrag,
    endDrag: endDrag,
    tapTo: tapTo
  });
})();
