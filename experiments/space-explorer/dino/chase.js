/**
 * Chase director — the visual language of the pursuit.
 *
 * The simulation tracks a real gap in metres, but a camera that simply trails
 * the runner cannot show a predator 15 m behind. This module turns the run
 * state into two composed camera moves:
 *
 *   • a chase camera that trails the runner and frames the road ahead, and
 *   • a staging rig that keeps the T-Rex just inside the right edge of frame,
 *     moving closer as the gap closes.
 *
 * Everything here is pure math (no three.js, no DOM) so the framing rules can
 * be checked headlessly: `scripts/dino/frame-check.mjs` samples the rig and
 * asserts the predator stays inside the camera frustum.
 */

import { clamp, clamp01, damp, lerp, smoothstep } from "./util.js";

/** Visual constants. Tuned against rendered frames, not guessed. */
export const CHASE = Object.freeze({
  // Camera rig.
  back: 13.2,
  backSpeed: 1.8,
  backSprint: 0.35,
  backDanger: 0.55,
  height: 4.55,
  heightDanger: 0.3,
  lookAhead: 13.4,
  lookHeight: 1.4,
  fovBase: 55,
  fovSpeed: 7,
  fovDanger: 2.5,
  fovSlide: 60,
  fovMin: 50,
  fovMax: 72,
  lateralFollow: 0.44, // how much of the runner's lane offset the camera keeps
  lateralLook: 0.9,

  // Predator staging, in metres relative to the runner.
  rexBehind: 7.4,
  rexBehindDanger: 2.4,
  rexLateral: 4.15,
  rexLateralDanger: 1.05,
  rexMenuBehind: 6.4,
  rexMenuLateral: -0.95,

  // Cinematics.
  swingTime: 1.25,
  catchOrbitTime: 2.4,
});

/**
 * Where the predator stands relative to the runner.
 *
 * `lateral` is measured toward −x (screen right for a camera looking down +z),
 * `behind` is how many metres back down the track it runs.
 *
 * @param {number} danger 0 (safe) … 1 (about to be caught)
 * @param {"menu"|"running"|"caught"|"gameover"} mode
 * @param {{t?:number, eat?:number}} [options]
 */
export function rexStaging(danger, mode, options = {}) {
  const d = clamp01(danger);
  if (mode === "menu") {
    const t = options.t ?? 0;
    return {
      behind: CHASE.rexMenuBehind + Math.sin(t * 0.31) * 0.12,
      lateral: CHASE.rexMenuLateral + Math.sin(t * 0.42) * 0.1,
      lean: 0,
      bite: 0,
    };
  }
  if (mode === "caught" || mode === "gameover") {
    return { behind: 2.45, lateral: 2.35, lean: 1, bite: 1 };
  }
  // Running: the closer the measured gap, the further the predator leans in.
  const reveal = smoothstep(0.15, 1, d);
  const eating = clamp01(options.eat ?? 0);
  return {
    behind: CHASE.rexBehind - CHASE.rexBehindDanger * reveal + eating * 1.6,
    lateral: CHASE.rexLateral - CHASE.rexLateralDanger * reveal - eating * 0.5,
    lean: reveal,
    bite: d > 0.72 ? smoothstep(0.72, 1, d) : 0,
  };
}

/** Yaw (radians) that turns a +z-facing rig toward a point. */
export function yawToward(fromX, fromZ, toX, toZ) {
  return Math.atan2(toX - fromX, toZ - fromZ);
}

/**
 * Stateful camera rig. Feed it one frame at a time and read `pose`.
 */
export function createChaseDirector() {
  const state = {
    x: 0,
    y: CHASE.height,
    z: -CHASE.back,
    lookX: 0,
    lookY: CHASE.lookHeight,
    lookZ: CHASE.lookAhead,
    fov: CHASE.fovBase,
    roll: 0,
    back: CHASE.back,
    swing: 0,
    dip: 0,
    dipVelocity: 0,
    orbit: 0,
    mode: "menu",
  };

  function reset(mode = "menu") {
    state.mode = mode;
    state.swing = 0;
    state.dip = 0;
    state.dipVelocity = 0;
    state.roll = 0;
  }

  /** Start the intro swing from in front of the runner to behind them. */
  function startSwing() {
    state.swing = 1;
  }

  function impulse(amount) {
    state.dipVelocity -= amount;
  }

  /**
   * @param {number} dt
   * @param {{
   *   mode: string,
   *   player: {x:number, y:number, z:number, tilt:number, sliding?:boolean},
   *   danger: number,
   *   speedRatio: number,
   *   sprinting?: boolean,
   *   rex?: {x:number, z:number},
   *   time: number,
   *   shake?: number,
   *   reduceMotion?: boolean,
   * }} input
   */
  function update(dt, input) {
    const step = Math.min(Math.max(dt, 0), 0.05);
    const { player, danger, speedRatio, time } = input;
    const mode = input.mode;
    const reduceMotion = Boolean(input.reduceMotion);
    state.mode = mode;
    const d = clamp01(danger);

    if (mode === "menu") {
      // Hero shot for the start screen: the pair sits in the right column,
      // the layout copy owns the left. Slow drift keeps it alive.
      const drift = Math.sin(time * 0.26) * 0.28;
      const target = {
        x: player.x - 2.85 - drift,
        y: 2.28 + Math.sin(time * 0.42) * 0.05,
        z: player.z + 7.35,
        lookX: player.x - 1.15 - drift * 0.4,
        lookY: 2.1,
        lookZ: player.z - 5.2,
        fov: 43,
      };
      state.x = damp(state.x, target.x, 2.6, step);
      state.y = damp(state.y, target.y, 2.6, step);
      state.z = damp(state.z, target.z, 2.6, step);
      state.lookX = damp(state.lookX, target.lookX, 2.4, step);
      state.lookY = damp(state.lookY, target.lookY, 2.4, step);
      state.lookZ = damp(state.lookZ, target.lookZ, 2.4, step);
      state.fov = damp(state.fov, target.fov, 2.2, step);
      state.roll = damp(state.roll, Math.sin(time * 0.18) * 0.012, 1.5, step);
      return state;
    }

    if (mode === "caught" || mode === "gameover") {
      // Hero orbit around the kill: wide, slow, and always holding both.
      const rex = input.rex ?? { x: player.x - 2.4, z: player.z - 2.4 };
      const focusX = (player.x + rex.x) * 0.5;
      const focusZ = (player.z + rex.z) * 0.5;
      state.orbit += step * (mode === "caught" ? 0.55 : 0.3);
      const radius = mode === "caught" ? 8.2 : 9.4;
      const angle = 0.55 + state.orbit;
      const target = {
        x: focusX + Math.sin(angle) * radius,
        y: 3.9 + Math.sin(state.orbit * 0.8) * 0.3,
        z: focusZ + Math.cos(angle) * radius,
        lookX: focusX,
        lookY: 2.7,
        lookZ: focusZ,
        fov: 54,
      };
      state.x = damp(state.x, target.x, 3.4, step);
      state.y = damp(state.y, target.y, 3.4, step);
      state.z = damp(state.z, target.z, 3.4, step);
      state.lookX = damp(state.lookX, target.lookX, 3.6, step);
      state.lookY = damp(state.lookY, target.lookY, 3.6, step);
      state.lookZ = damp(state.lookZ, target.lookZ, 3.6, step);
      state.fov = damp(state.fov, target.fov, 2.4, step);
      state.roll = damp(state.roll, 0, 3, step);
      return state;
    }

    // ── Running ────────────────────────────────────────────────────────────
    const back = CHASE.back + speedRatio * CHASE.backSpeed + (input.sprinting ? CHASE.backSprint : 0) + d * CHASE.backDanger;
    state.back = damp(state.back, back, 2.2, step);

    // Landing / impact spring keeps the horizon from snapping.
    state.dipVelocity += -state.dip * 46 * step - state.dipVelocity * 9.5 * step;
    state.dip += state.dipVelocity * step;

    const tilt = player.tilt ?? 0;
    const targetX = player.x * CHASE.lateralFollow + tilt * 0.18;
    const targetY = CHASE.height + Math.min(player.y, 2.2) * 0.24 + d * CHASE.heightDanger;
    const targetZ = player.z - state.back;
    const targetLookX = player.x * CHASE.lateralLook;
    const targetLookY = CHASE.lookHeight + Math.min(player.y, 2.2) * 0.12 + d * 0.1;
    const targetLookZ = player.z + CHASE.lookAhead;

    state.x = damp(state.x, targetX, 5.5, step);
    state.z = damp(state.z, targetZ, 9, step);
    state.lookX = damp(state.lookX, targetLookX, 6.5, step);
    state.lookY = damp(state.lookY, targetLookY, 6, step);
    state.lookZ = damp(state.lookZ, targetLookZ, 8, step);
    // The dip is additive so it never fights the smoothed height.
    state.y = damp(state.y, targetY, 5, step) + state.dip;

    const targetFov =
      CHASE.fovBase +
      speedRatio * CHASE.fovSpeed +
      d * CHASE.fovDanger +
      (player.sliding ? CHASE.fovSlide - CHASE.fovBase : 0);
    state.fov = damp(state.fov, clamp(targetFov, CHASE.fovMin, CHASE.fovMax), 3.2, step);

    const runRoll = -tilt * 0.018 + Math.sin(time * 17) * 0.0022 * (0.4 + speedRatio);
    state.roll = damp(state.roll, reduceMotion ? 0 : runRoll, 6, step);

    // Intro swing: start ahead of the runner and arc behind them.
    if (state.swing > 0) {
      state.swing = Math.max(0, state.swing - step / CHASE.swingTime);
      const eased = smoothstep(0, 1, 1 - state.swing);
      const theta = lerp(0.28, Math.PI, eased);
      const radius = lerp(9.2, state.back, eased);
      const swingX = player.x + Math.sin(theta) * radius;
      const swingY = lerp(2.45, state.y, eased);
      const swingZ = player.z + Math.cos(theta) * radius;
      const weight = smoothstep(0, 0.35, 1 - state.swing);
      state.x = lerp(state.x, swingX, weight);
      state.y = lerp(state.y, swingY, weight);
      state.z = lerp(state.z, swingZ, weight);
    }
    return state;
  }

  function setRollOffset(value) {
    state.roll += value;
  }

  return {
    state,
    reset,
    startSwing,
    impulse,
    update,
    setRollOffset,
  };
}
