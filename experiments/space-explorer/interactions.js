const MIN_ZOOM = 0.65;
const MAX_ZOOM = 1.85;
const ZOOM_SENSITIVITY = 1;

function getTouchDistance(t1, t2) {
  const x1 = t1.clientX ?? t1.x ?? 0;
  const y1 = t1.clientY ?? t1.y ?? 0;
  const x2 = t2.clientX ?? t2.x ?? 0;
  const y2 = t2.clientY ?? t2.y ?? 0;
  const dx = x2 - x1;
  const dy = y2 - y1;
  return Math.hypot(dx, dy);
}

function getTouchAngle(t1, t2) {
  const x1 = t1.clientX ?? t1.x ?? 0;
  const y1 = t1.clientY ?? t1.y ?? 0;
  const x2 = t2.clientX ?? t2.x ?? 0;
  const y2 = t2.clientY ?? t2.y ?? 0;
  return Math.atan2(y2 - y1, x2 - x1);
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

export function attachTouchInteractions(options) {
  const { canvas, state, render } = options;
  if (!canvas) return;
  const activePointers = new Map();
  let rafScheduled = false;

  let gestureStartDistance = null;
  let gestureStartAngle = null;
  let zoomAtGestureStart = state.targetZoom;
  let rotationAtGestureStart = state.targetRotation;

  function resetGesture() {
    gestureStartDistance = null;
    gestureStartAngle = null;
    zoomAtGestureStart = state.targetZoom;
    rotationAtGestureStart = state.targetRotation;
  }

  function scheduleRender() {
    if (rafScheduled) return;
    rafScheduled = true;
    requestAnimationFrame(() => {
      rafScheduled = false;
      render();
    });
  }

  function onTouchStart(event) {
    if (event.touches.length < 2) return;
    const [t1, t2] = event.touches;
    gestureStartDistance = getTouchDistance(t1, t2);
    gestureStartAngle = getTouchAngle(t1, t2);
    zoomAtGestureStart = state.targetZoom;
    rotationAtGestureStart = state.targetRotation;
    event.preventDefault();
  }

  function onTouchMove(event) {
    if (event.touches.length < 2 || !gestureStartDistance || gestureStartAngle === null) {
      return;
    }

    const [t1, t2] = event.touches;
    const currentDistance = getTouchDistance(t1, t2);
    const currentAngle = getTouchAngle(t1, t2);
    const scaleFactor = currentDistance / gestureStartDistance;

    state.targetZoom = clamp(zoomAtGestureStart * scaleFactor * ZOOM_SENSITIVITY, MIN_ZOOM, MAX_ZOOM);
    state.targetRotation = rotationAtGestureStart + (currentAngle - gestureStartAngle);
    scheduleRender();
    event.preventDefault();
  }

  function onTouchEnd(event) {
    if (event.touches.length >= 2) {
      const [t1, t2] = event.touches;
      gestureStartDistance = getTouchDistance(t1, t2);
      gestureStartAngle = getTouchAngle(t1, t2);
      zoomAtGestureStart = state.targetZoom;
      rotationAtGestureStart = state.targetRotation;
      return;
    }
    resetGesture();
  }

  function getPointerPair() {
    const pointers = Array.from(activePointers.values());
    if (pointers.length < 2) return null;
    return [pointers[0], pointers[1]];
  }

  function onPointerDown(event) {
    activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    const pair = getPointerPair();
    if (!pair) return;
    const [p1, p2] = pair;
    gestureStartDistance = getTouchDistance(p1, p2);
    gestureStartAngle = getTouchAngle(p1, p2);
    zoomAtGestureStart = state.targetZoom;
    rotationAtGestureStart = state.targetRotation;
    event.preventDefault();
  }

  function onPointerMove(event) {
    if (!activePointers.has(event.pointerId)) return;
    activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    const pair = getPointerPair();
    if (!pair || !gestureStartDistance || gestureStartAngle === null) return;

    const [p1, p2] = pair;
    const currentDistance = getTouchDistance(p1, p2);
    const currentAngle = getTouchAngle(p1, p2);
    const scaleFactor = currentDistance / gestureStartDistance;
    state.targetZoom = clamp(zoomAtGestureStart * scaleFactor * ZOOM_SENSITIVITY, MIN_ZOOM, MAX_ZOOM);
    state.targetRotation = rotationAtGestureStart + (currentAngle - gestureStartAngle);
    scheduleRender();
    event.preventDefault();
  }

  function onPointerUp(event) {
    activePointers.delete(event.pointerId);
    const pair = getPointerPair();
    if (pair) {
      const [p1, p2] = pair;
      gestureStartDistance = getTouchDistance(p1, p2);
      gestureStartAngle = getTouchAngle(p1, p2);
      zoomAtGestureStart = state.targetZoom;
      rotationAtGestureStart = state.targetRotation;
      return;
    }
    resetGesture();
  }

  function onWheel(event) {
    const wheelDelta = -event.deltaY;
    const zoomStep = wheelDelta * 0.0015;
    state.targetZoom = clamp(state.targetZoom + zoomStep, MIN_ZOOM, MAX_ZOOM);
    scheduleRender();
    event.preventDefault();
  }

  canvas.addEventListener("touchstart", onTouchStart, { passive: false });
  canvas.addEventListener("touchmove", onTouchMove, { passive: false });
  canvas.addEventListener("touchend", onTouchEnd);
  canvas.addEventListener("touchcancel", onTouchEnd);
  canvas.addEventListener("pointerdown", onPointerDown, { passive: false });
  canvas.addEventListener("pointermove", onPointerMove, { passive: false });
  canvas.addEventListener("pointerup", onPointerUp);
  canvas.addEventListener("pointercancel", onPointerUp);
  canvas.addEventListener("wheel", onWheel, { passive: false });
}
