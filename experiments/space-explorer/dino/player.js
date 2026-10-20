/** Runner physics: strafing, jumping, sliding and hazard hit tests. */

import { PLAYER, ROAD } from "./constants.js";
import { clamp, damp } from "./util.js";

export function createPlayerState() {
  const state = {
    x: 0,
    z: 0,
    y: 0,
    vx: 0,
    vy: 0,
    grounded: true,
    sliding: false,
    slideTimer: 0,
    slideCooldown: 0,
    tilt: 0,
    stumble: 0,
    landImpact: 0,
    stepTravel: 0,
    strideParity: 0,
    distanceRun: 0,
    coyote: 0,
    jumpBuffer: 0,
  };
  return state;
}

export function resetPlayer(state, x = 0) {
  state.x = x;
  state.z = 0;
  state.y = 0;
  state.vx = 0;
  state.vy = 0;
  state.grounded = true;
  state.sliding = false;
  state.slideTimer = 0;
  state.slideCooldown = 0;
  state.tilt = 0;
  state.stumble = 0;
  state.landImpact = 0;
  state.stepTravel = 0;
  state.strideParity = 0;
  state.distanceRun = 0;
  state.coyote = 0;
  state.jumpBuffer = 0;
}

/**
 * Advances the runner one frame.
 * @param {ReturnType<typeof createPlayerState>} state
 * @param {number} dt
 * @param {{axis?:number, jump?:boolean, slide?:boolean, sprint?:boolean, speed?:number}} controls
 * @returns {{jumped:boolean, landed:boolean, slideStarted:boolean, slideStopped:boolean, fastFell:boolean, footstep:boolean, stepSide:number}}
 */
export function stepPlayer(state, dt, controls = {}) {
  const events = {
    jumped: false,
    landed: false,
    slideStarted: false,
    slideStopped: false,
    fastFell: false,
    footstep: false,
    stepSide: 0,
  };
  if (!(dt > 0)) {
    return events;
  }
  const step = Math.min(dt, 0.05);
  const speed = Math.max(6, controls.speed ?? 13.5);
  // Input reports +1 for "go right" as the player sees it. The chase camera
  // sits behind the runner looking down +z, which makes world −x the right-hand
  // side of the screen, so the screen-space axis is flipped once, here. Every
  // input source (keyboard, drag, gamepad, touch pad) and the runner's lean
  // inherit the correction from this single conversion.
  const screenAxis = clamp(controls.axis ?? 0, -1, 1);
  const axis = -screenAxis;
  const sprinting = Boolean(controls.sprint);

  state.landImpact = 0;
  state.stumble = Math.max(0, state.stumble - step);
  state.slideCooldown = Math.max(0, state.slideCooldown - step);

  // Horizontal steering: quick but not instant, slightly wider while sliding.
  const strafeTarget = axis * PLAYER.strafeSpeed * (sprinting ? 1.06 : 1) * (state.sliding ? 1.15 : 1);
  state.vx = damp(state.vx, strafeTarget, PLAYER.strafeAccel, step);
  if (Math.abs(state.vx) > 0.01) {
    state.x = clamp(state.x + state.vx * step, ROAD.playerMinX, ROAD.playerMaxX);
  }
  state.tilt = damp(state.tilt, axis * 0.85 + state.vx / PLAYER.strafeSpeed * 0.25, 9, step);

  // Slide timer.
  if (state.sliding) {
    state.slideTimer -= step;
    if (state.slideTimer <= 0) {
      state.sliding = false;
      state.slideCooldown = PLAYER.slideCooldown;
      events.slideStopped = true;
    }
  }

  // Start a slide (ground only).
  if (controls.slide && !state.sliding && state.grounded && state.slideCooldown <= 0) {
    state.sliding = true;
    state.slideTimer = PLAYER.slideDuration;
    state.slideCooldown = 0;
    events.slideStarted = true;
  } else if (controls.slide && !state.grounded && state.vy < -2) {
    // Air-slide becomes a fast fall.
    state.vy = Math.max(-PLAYER.maxFallSpeed, state.vy - 14);
    events.fastFell = true;
  }

  // Jump with a forgiveness window in both directions: a press just before
  // landing still fires (buffer), and a press just after leaving an edge still
  // counts (coyote). Small hands miss frames; the game should not.
  state.jumpBuffer = controls.jump ? PLAYER.jumpBuffer : Math.max(0, state.jumpBuffer - step);
  state.coyote = state.grounded ? PLAYER.coyoteTime : Math.max(0, state.coyote - step);
  if (state.jumpBuffer > 0 && (state.grounded || state.coyote > 0)) {
    if (state.sliding) {
      state.sliding = false;
      state.slideCooldown = PLAYER.slideCooldown;
      events.slideStopped = true;
    }
    state.vy = PLAYER.jumpVelocity;
    state.grounded = false;
    state.coyote = 0;
    state.jumpBuffer = 0;
    events.jumped = true;
  }

  // Gravity + ground collision.
  if (!state.grounded) {
    state.vy = Math.max(-PLAYER.maxFallSpeed, state.vy - PLAYER.gravity * step);
    state.y += state.vy * step;
    if (state.y <= 0) {
      const impact = Math.abs(state.vy);
      state.y = 0;
      state.vy = 0;
      state.grounded = true;
      state.landImpact = clamp(impact / 12, 0.25, 1);
      if (impact > 4) {
        events.landed = true;
      }
    }
  }

  // Footstep rhythm scales with ground speed.
  if (state.grounded && !state.sliding) {
    state.stepTravel += speed * step;
    const stride = 2.55;
    if (state.stepTravel >= stride) {
      state.stepTravel -= stride;
      state.strideParity = state.strideParity === 0 ? 1 : 0;
      events.footstep = true;
      events.stepSide = state.strideParity === 0 ? -1 : 1;
    }
  } else {
    state.stepTravel = Math.min(state.stepTravel, 1.2);
  }

  state.distanceRun += speed * step;
  return events;
}

/** Vertical span the hitbox occupies, in world units above the ground. */
export function getPlayerHitbox(state) {
  const height = state.sliding ? PLAYER.slideHeight : PLAYER.height;
  return {
    x: state.x,
    z: state.z,
    bottom: state.y,
    top: state.y + height,
    height,
  };
}

/**
 * True when the runner overlaps a hazard. Hazard descriptors come from
 * spawner.js and carry their own width / vertical band / eruption state.
 */
export function hitTest(state, hazard, z) {
  if (!hazard || hazard.disabled) {
    return false;
  }
  const playerZ = z ?? state.z;
  if (Math.abs(playerZ - hazard.z) > (hazard.depth ?? 0.9)) {
    return false;
  }
  if (Math.abs(state.x - hazard.x) > (hazard.halfWidth ?? 1) + PLAYER.halfWidth) {
    return false;
  }
  if (hazard.type === "geyser" && !hazard.erupting) {
    return false;
  }
  const box = getPlayerHitbox(state);
  const bottom = hazard.bottom ?? 0;
  const top = hazard.top ?? hazard.height ?? 1.4;
  if (hazard.avoid === "jump" && box.bottom >= top - PLAYER.hitboxGrace) {
    return false;
  }
  if (hazard.avoid === "slide" && box.top <= bottom + PLAYER.hitboxGrace) {
    return false;
  }
  return box.bottom < top && box.top > bottom;
}
