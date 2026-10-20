// 태양계 3D 탐험대 — 포인터/키보드 상호작용
// OrbitControls가 회전·줌을 담당하고, 여기서는 "클릭과 드래그 구분", 호버 표시,
// 키보드 줌 보조를 담당한다.

const DRAG_THRESHOLD_PX = 7;
const CLICK_MAX_MS = 520;

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function isTypingTarget(target) {
  if (!target) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
}

/**
 * @param {{
 *   canvas: HTMLCanvasElement,
 *   camera: import("three").PerspectiveCamera,
 *   controls: import("three/addons/controls/OrbitControls.js").OrbitControls,
 *   raycast: (event: PointerEvent) => string | null,
 *   onPick: (bodyId: string) => void,
 *   onHover: (bodyId: string | null) => void,
 *   onUserInteract?: () => void
 * }} options
 */
export function attachSceneInteractions({ canvas, camera, controls, raycast, onPick, onHover, onUserInteract = () => {} }) {
  let start = null;
  let hoveredId = null;
  let hoverFrame = 0;
  let pendingHoverEvent = null;

  function emitHover(event) {
    pendingHoverEvent = event;
    if (hoverFrame) return;
    hoverFrame = requestAnimationFrame(() => {
      hoverFrame = 0;
      if (!pendingHoverEvent) return;
      const id = raycast(pendingHoverEvent);
      pendingHoverEvent = null;
      if (id !== hoveredId) {
        hoveredId = id;
        canvas.style.cursor = id ? "pointer" : "grab";
        onHover(id);
      }
    });
  }

  function onPointerDown(event) {
    if (event.button !== undefined && event.button !== 0) return;
    start = {
      x: event.clientX,
      y: event.clientY,
      time: performance.now(),
    };
    canvas.style.cursor = "grabbing";
    onUserInteract();
  }

  function onPointerMove(event) {
    if (start) {
      const moved = Math.hypot(event.clientX - start.x, event.clientY - start.y);
      if (moved > DRAG_THRESHOLD_PX) start.moved = true;
      return;
    }
    if (event.pointerType === "mouse" || event.pointerType === "pen") emitHover(event);
  }

  function onPointerUp(event) {
    const wasClick =
      start &&
      !start.moved &&
      Math.hypot(event.clientX - start.x, event.clientY - start.y) <= DRAG_THRESHOLD_PX &&
      performance.now() - start.time <= CLICK_MAX_MS;
    start = null;
    canvas.style.cursor = hoveredId ? "pointer" : "grab";
    if (wasClick) {
      const id = raycast(event);
      if (id) onPick(id);
    }
  }

  function onPointerLeave() {
    start = null;
    if (hoveredId) {
      hoveredId = null;
      onHover(null);
    }
  }

  function dolly(factor) {
    const offset = camera.position.clone().sub(controls.target);
    const distance = clamp(offset.length() * factor, controls.minDistance, controls.maxDistance);
    camera.position.copy(controls.target).add(offset.setLength(distance));
    controls.update();
    onUserInteract();
  }

  function onKeyDown(event) {
    if (isTypingTarget(event.target)) return;
    if (event.key === "+" || event.key === "=") {
      event.preventDefault();
      dolly(0.88);
    } else if (event.key === "-" || event.key === "_") {
      event.preventDefault();
      dolly(1.14);
    }
  }

  canvas.addEventListener("pointerdown", onPointerDown);
  canvas.addEventListener("pointermove", onPointerMove);
  canvas.addEventListener("pointerup", onPointerUp);
  canvas.addEventListener("pointercancel", onPointerLeave);
  canvas.addEventListener("pointerleave", onPointerLeave);
  canvas.addEventListener("wheel", onUserInteract, { passive: true });
  window.addEventListener("keydown", onKeyDown);

  return {
    detach() {
      canvas.removeEventListener("pointerdown", onPointerDown);
      canvas.removeEventListener("pointermove", onPointerMove);
      canvas.removeEventListener("pointerup", onPointerUp);
      canvas.removeEventListener("pointercancel", onPointerLeave);
      canvas.removeEventListener("pointerleave", onPointerLeave);
      canvas.removeEventListener("wheel", onUserInteract);
      window.removeEventListener("keydown", onKeyDown);
      if (hoverFrame) cancelAnimationFrame(hoverFrame);
    },
    zoomIn() {
      dolly(0.88);
    },
    zoomOut() {
      dolly(1.14);
    },
  };
}
