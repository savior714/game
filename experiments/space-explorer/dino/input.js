/**
 * Keyboard, touch (virtual joystick + swipes) and gamepad input for the
 * chase runner. The game polls edge events with consume*() and reads held
 * state for steering / sprint / slide.
 */

const GAME_KEYS = new Set([
  "KeyA",
  "KeyD",
  "KeyW",
  "KeyS",
  "KeyE",
  "KeyQ",
  "ArrowLeft",
  "ArrowRight",
  "ArrowUp",
  "ArrowDown",
  "Space",
  "ShiftLeft",
  "ShiftRight",
]);

function isFormControl(element) {
  if (!element) {
    return false;
  }
  const tag = element.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || element.isContentEditable;
}

function isButton(element) {
  return Boolean(element && (element.tagName === "BUTTON" || element.tagName === "A"));
}

export function createInput(options) {
  const canvas = options.canvas;
  const callbacks = options.callbacks ?? {};
  const buttons = options.buttons ?? {};

  const keys = new Set();
  let jumpQueued = false;
  let slideQueued = false;
  let baitQueued = false;
  let jumpBuffer = 0;
  let slideHeld = false;
  let sprintHeld = false;
  let keyboardAxis = 0;
  let pointerAxis = 0;
  let padAxis = 0;
  let enabled = true;
  let sprintHeldFromTouch = false;
  let slideHeldFromTouch = false;
  let sprintHeldFromPad = false;
  let slideHeldFromPad = false;

  const drag = {
    pointerId: null,
    startX: 0,
    startY: 0,
    active: false,
    verticalAction: null,
  };

  function queueJump() {
    jumpQueued = true;
    jumpBuffer = 0.16;
  }

  function updateHeldKeys() {
    const left = keys.has("KeyA") || keys.has("ArrowLeft");
    const right = keys.has("KeyD") || keys.has("ArrowRight");
    keyboardAxis = (right ? 1 : 0) - (left ? 1 : 0);
    const slide = keys.has("KeyS") || keys.has("ArrowDown");
    if (slide && !slideHeld) {
      slideQueued = true;
    }
    slideHeld = slide || slideHeldFromTouch || slideHeldFromPad;
    const sprint = keys.has("ShiftLeft") || keys.has("ShiftRight");
    sprintHeld = sprint || sprintHeldFromTouch || sprintHeldFromPad;
  }

  function onKeyDown(event) {
    if (!enabled) {
      return;
    }
    if (isFormControl(event.target)) {
      return;
    }
    const code = event.code;
    if (GAME_KEYS.has(code)) {
      if (isButton(document.activeElement) && (code === "Space" || code === "Enter")) {
        return;
      }
      event.preventDefault();
    }
    if (event.repeat) {
      return;
    }
    if (code === "Escape" || code === "KeyP") {
      event.preventDefault();
      callbacks.onPause?.();
      return;
    }
    if (code === "KeyM") {
      callbacks.onMute?.();
      return;
    }
    if (code === "Enter") {
      if (isButton(document.activeElement)) {
        return;
      }
      callbacks.onConfirm?.();
      return;
    }
    if (code === "KeyR") {
      callbacks.onRestart?.();
      return;
    }
    if (code === "Space" || code === "ArrowUp" || code === "KeyW") {
      queueJump();
      keys.add(code);
      return;
    }
    if (code === "KeyE" || code === "KeyQ") {
      baitQueued = true;
      return;
    }
    keys.add(code);
    updateHeldKeys();
  }

  function onKeyUp(event) {
    keys.delete(event.code);
    updateHeldKeys();
  }

  function releaseDrag(pointerId) {
    if (drag.pointerId !== pointerId) {
      return;
    }
    drag.pointerId = null;
    drag.active = false;
    drag.verticalAction = null;
    pointerAxis = 0;
    slideHeldFromTouch = false;
    updateHeldKeys();
  }

  function updateDrag(event) {
    const width = Math.max(320, window.innerWidth);
    const dx = event.clientX - drag.startX;
    const dy = event.clientY - drag.startY;
    if (!drag.verticalAction && Math.abs(dy) > 42 && Math.abs(dy) > Math.abs(dx) * 1.35) {
      if (dy < 0) {
        queueJump();
        drag.verticalAction = "jump";
      } else {
        slideQueued = true;
        slideHeldFromTouch = true;
        drag.verticalAction = "slide";
      }
    }
    if (drag.verticalAction === "slide") {
      pointerAxis = 0;
      return;
    }
    const deadZone = 0.1;
    const raw = Math.max(-1, Math.min(1, dx / (width * 0.16)));
    pointerAxis = Math.abs(raw) < deadZone ? 0 : Math.sign(raw) * ((Math.abs(raw) - deadZone) / (1 - deadZone));
  }

  function onPointerDown(event) {
    if (!enabled) {
      return;
    }
    if (drag.pointerId !== null) {
      return;
    }
    drag.pointerId = event.pointerId;
    drag.startX = event.clientX;
    drag.startY = event.clientY;
    drag.active = true;
    drag.verticalAction = null;
    canvas.setPointerCapture?.(event.pointerId);
    event.preventDefault();
  }

  function onPointerMove(event) {
    if (drag.pointerId !== event.pointerId) {
      return;
    }
    updateDrag(event);
    event.preventDefault();
  }

  function onPointerUp(event) {
    if (drag.pointerId !== event.pointerId) {
      return;
    }
    releaseDrag(event.pointerId);
    event.preventDefault();
  }

  canvas.addEventListener("contextmenu", (event) => event.preventDefault());
  canvas.addEventListener("pointerdown", onPointerDown, { passive: false });
  canvas.addEventListener("pointermove", onPointerMove, { passive: false });
  canvas.addEventListener("pointerup", onPointerUp, { passive: false });
  canvas.addEventListener("pointercancel", onPointerUp, { passive: false });
  window.addEventListener("keydown", onKeyDown, { passive: false });
  window.addEventListener("keyup", onKeyUp);

  function bindPress(element, action, { hold = false } = {}) {
    if (!element) {
      return;
    }
    const down = (event) => {
      if (!enabled) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      element.classList.add("is-pressed");
      element.setPointerCapture?.(event.pointerId);
      action(true);
    };
    const up = (event) => {
      event.preventDefault();
      event.stopPropagation();
      element.classList.remove("is-pressed");
      if (hold) {
        action(false);
      }
    };
    element.addEventListener("pointerdown", down, { passive: false });
    if (hold) {
      element.addEventListener("pointerup", up, { passive: false });
      element.addEventListener("pointercancel", up, { passive: false });
      element.addEventListener("pointerleave", (event) => {
        if (event.buttons === 0) {
          up(event);
        }
      });
    } else {
      element.addEventListener("pointerup", () => {
        element.classList.remove("is-pressed");
      });
      element.addEventListener("pointercancel", () => {
        element.classList.remove("is-pressed");
      });
      element.addEventListener("pointerleave", () => {
        element.classList.remove("is-pressed");
      });
    }
  }

  bindPress(buttons.jump, () => queueJump());
  bindPress(buttons.slide, (pressed) => {
    if (pressed) {
      slideQueued = true;
      slideHeldFromTouch = true;
    } else {
      slideHeldFromTouch = false;
    }
    updateHeldKeys();
  }, { hold: true });
  bindPress(buttons.sprint, (pressed) => {
    sprintHeldFromTouch = pressed;
    updateHeldKeys();
  }, { hold: true });
  bindPress(buttons.bait, () => {
    baitQueued = true;
  });

  let padConnected = false;
  let previousPadButtons = [];

  function pollGamepad() {
    if (!enabled || typeof navigator.getGamepads !== "function") {
      return;
    }
    const pads = navigator.getGamepads();
    let pad = null;
    for (const candidate of pads) {
      if (candidate && candidate.connected) {
        pad = candidate;
        break;
      }
    }
    if (!pad) {
      padConnected = false;
      padAxis = 0;
      return;
    }
    if (!padConnected) {
      padConnected = true;
      callbacks.onGamepadConnected?.(pad.id);
    }
    const axis = Math.abs(pad.axes[0] ?? 0) > 0.18 ? pad.axes[0] : 0;
    padAxis = Math.max(-1, Math.min(1, axis));
    const pressed = pad.buttons.map((button) => button.pressed);
    const edge = (index) => pressed[index] && !previousPadButtons[index];
    if (edge(0) || edge(12)) {
      queueJump();
    }
    if (edge(1) || edge(13)) {
      slideQueued = true;
      slideHeldFromPad = true;
    }
    if (!pressed[1] && previousPadButtons[1]) {
      slideHeldFromPad = false;
    }
    if (edge(2) || edge(3)) {
      baitQueued = true;
    }
    if (edge(9)) {
      callbacks.onPause?.();
    }
    sprintHeldFromPad = Boolean(pressed[6] || pressed[7] || pressed[10]);
    previousPadButtons = pressed;
  }

  function update(dt) {
    pollGamepad();
    if (jumpBuffer > 0) {
      jumpBuffer = Math.max(0, jumpBuffer - dt);
      if (jumpBuffer === 0) {
        jumpQueued = false;
      }
    }
    updateHeldKeys();
  }

  function getAxis() {
    if (Math.abs(pointerAxis) > 0.02) {
      return pointerAxis;
    }
    if (Math.abs(padAxis) > 0.02) {
      return padAxis;
    }
    return keyboardAxis;
  }

  return {
    update,
    getAxis,
    getSlideHeld: () => slideHeld,
    getSprintHeld: () => sprintHeld,
    consumeJump() {
      const value = jumpQueued || jumpBuffer > 0;
      jumpQueued = false;
      jumpBuffer = 0;
      return value;
    },
    consumeSlide() {
      const value = slideQueued;
      slideQueued = false;
      return value;
    },
    consumeBait() {
      const value = baitQueued;
      baitQueued = false;
      return value;
    },
    setEnabled(value) {
      enabled = Boolean(value);
      if (!enabled) {
        keys.clear();
        sprintHeld = false;
        sprintHeldFromTouch = false;
        slideHeld = false;
        slideHeldFromTouch = false;
        slideHeldFromPad = false;
        sprintHeldFromPad = false;
        jumpQueued = false;
        slideQueued = false;
        baitQueued = false;
        jumpBuffer = 0;
        pointerAxis = 0;
        keyboardAxis = 0;
        padAxis = 0;
      }
    },
    destroy() {
      canvas.removeEventListener("pointerdown", onPointerDown);
      canvas.removeEventListener("pointermove", onPointerMove);
      canvas.removeEventListener("pointerup", onPointerUp);
      canvas.removeEventListener("pointercancel", onPointerUp);
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    },
  };
}
