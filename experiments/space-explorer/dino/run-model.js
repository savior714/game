import { BIOMES, RUN } from "./constants.js";
import { clamp, clamp01 } from "./util.js";

/**
 * Deterministic-ish run rules for the chase runner. This module owns every
 * number that decides "can the player survive" — speed, distance, the gap to
 * the T-Rex, stamina, pickups, milestones and the combo chain. The 3D layer
 * feeds it elapsed seconds and inputs, then reacts to the returned events.
 */

export function createRunState() {
  return {
    time: 0,
    distance: 0,
    speed: RUN.baseSpeed,
    gap: RUN.startGap,
    stamina: 1,
    staminaLocked: false,
    sprinting: false,
    amber: 0,
    chain: 0,
    bestChain: 0,
    comboTimer: 0,
    bait: 1,
    shield: 0,
    hits: 0,
    invuln: 0,
    slowTimer: 0,
    eatTimer: 0,
    baitFallback: 0,
    milestone: RUN.milestoneStep,
    biomeIndex: 0,
    caught: false,
  };
}

export function getBaseSpeed(distance) {
  return RUN.baseSpeed + Math.min(RUN.maxSpeed - RUN.baseSpeed, Math.max(0, distance) * RUN.speedPerMeter);
}

export function getGapDrift(distance) {
  return Math.min(RUN.gapDriftMax, RUN.gapDriftBase + Math.max(0, distance) * RUN.gapDriftPerMeter);
}

export function getSpeedKmh(state) {
  return state.speed * 3.6;
}

export function getComboMultiplier(state) {
  return Math.min(RUN.comboMax, 1 + Math.floor(state.chain / RUN.comboStep));
}

export function getDangerLevel(state) {
  return 1 - clamp01((state.gap - RUN.caughtGap) / (7.5 - RUN.caughtGap));
}

export function getBiomeIndex(distance) {
  let index = 0;
  for (let i = 0; i < BIOMES.length; i += 1) {
    if (distance >= BIOMES[i].threshold) {
      index = i;
    }
  }
  return index;
}

export function getBiomeProgress(distance) {
  const index = getBiomeIndex(distance);
  const current = BIOMES[index];
  const next = BIOMES[index + 1] ?? null;
  if (!next) {
    return { index, progress: 1, remaining: 0, next: null };
  }
  const span = Math.max(1, next.threshold - current.threshold);
  const progress = clamp01((distance - current.threshold) / span);
  return { index, progress, remaining: Math.max(0, Math.ceil(next.threshold - distance)), next };
}

/**
 * Advances the run by `dt` seconds.
 * @param {ReturnType<typeof createRunState>} state
 * @param {number} dt
 * @param {{sprintHeld?: boolean}} input
 * @returns {Array<{type: string, [key: string]: unknown}>} events for the presentation layer
 */
export function stepRun(state, dt, input = {}) {
  const events = [];
  if (!Number.isFinite(dt) || dt <= 0) {
    return events;
  }
  const step = Math.min(0.05, dt);
  state.time += step;

  if (state.invuln > 0) {
    state.invuln = Math.max(0, state.invuln - step);
  }
  if (state.slowTimer > 0) {
    state.slowTimer = Math.max(0, state.slowTimer - step);
  }
  if (state.eatTimer > 0) {
    state.eatTimer = Math.max(0, state.eatTimer - step);
  }
  if (state.baitFallback > 0) {
    const fallbackStep = Math.min(state.baitFallback, step);
    state.baitFallback -= fallbackStep;
    state.gap += (RUN.baitGapGain * fallbackStep) / RUN.baitFallbackTime;
  }

  if (state.staminaLocked && state.stamina >= RUN.staminaUnlock) {
    state.staminaLocked = false;
  }

  const wantsSprint = Boolean(input.sprintHeld);
  const canSprint = wantsSprint && !state.staminaLocked && state.stamina > 0 && !state.caught;
  state.sprinting = canSprint;
  if (canSprint) {
    state.stamina = Math.max(0, state.stamina - RUN.staminaDrain * step);
    if (state.stamina <= 0) {
      state.staminaLocked = true;
      state.sprinting = false;
    }
  } else {
    state.stamina = Math.min(1, state.stamina + RUN.staminaRegen * step);
  }

  let targetSpeed = getBaseSpeed(state.distance);
  if (state.slowTimer > 0) {
    const slowBlend = clamp01(state.slowTimer / RUN.hitSlow);
    targetSpeed *= 1 - (1 - RUN.hitSlowFactor) * slowBlend;
  }
  if (state.sprinting) {
    targetSpeed *= RUN.sprintMultiplier;
  }
  state.speed += (targetSpeed - state.speed) * Math.min(1, step * 6.5);

  const previousBiome = state.biomeIndex;
  if (!state.caught) {
    state.distance += state.speed * step;
  }

  if (state.eatTimer <= 0 && !state.caught) {
    state.gap -= getGapDrift(state.distance) * step;
  }
  state.gap = clamp(state.gap, 0, RUN.maxGap);

  if (state.chain > 0) {
    state.comboTimer = Math.max(0, state.comboTimer - step);
    if (state.comboTimer <= 0) {
      state.chain = 0;
      events.push({ type: "combo-end" });
    }
  }

  while (state.distance >= state.milestone) {
    state.gap = Math.min(RUN.maxGap, state.gap + RUN.milestoneGapReward);
    events.push({ type: "milestone", distance: state.milestone });
    state.milestone += RUN.milestoneStep;
  }

  const biomeIndex = getBiomeIndex(state.distance);
  if (biomeIndex !== previousBiome) {
    state.biomeIndex = biomeIndex;
    events.push({ type: "biome", index: biomeIndex, biome: BIOMES[biomeIndex] });
  }

  if (!state.caught && state.gap <= RUN.caughtGap) {
    state.caught = true;
    state.speed = getBaseSpeed(state.distance) * 0.35;
    state.sprinting = false;
    events.push({ type: "caught" });
  }

  return events;
}

/**
 * Resolves an obstacle strike. Shield charge absorbs it; otherwise the rex
 * closes in and the runner stumbles.
 */
export function applyHit(state) {
  if (state.caught) {
    return { type: "ignored" };
  }
  if (state.invuln > 0) {
    return { type: "ignored" };
  }
  if (state.shield > 0) {
    state.shield -= 1;
    state.invuln = 0.9;
    state.slowTimer = 0.25;
    return { type: "shielded" };
  }
  state.hits += 1;
  state.invuln = RUN.hitInvuln;
  state.slowTimer = RUN.hitSlow;
  state.gap = Math.max(0, state.gap - RUN.hitGapPenalty);
  if (state.gap <= RUN.caughtGap) {
    state.caught = true;
    state.speed = getBaseSpeed(state.distance) * 0.35;
    state.sprinting = false;
    return { type: "caught" };
  }
  return { type: "hit" };
}

/**
 * Ambers are the run's fuel. Each one pushes the predator back a little, so a
 * player who keeps collecting holds the gap open; a player who only runs is
 * slowly caught. Every `amberStreak` in a row pays a visible bonus on top.
 */
export function collectAmber(state) {
  state.amber += 1;
  state.chain += 1;
  state.bestChain = Math.max(state.bestChain, state.chain);
  state.comboTimer = RUN.comboTimeout;
  let baitAward = false;
  if (state.amber % RUN.amberPerBait === 0 && state.bait < RUN.baitCapacity) {
    state.bait += 1;
    baitAward = true;
  }
  const before = state.gap;
  const streakBonus = state.chain > 0 && state.chain % RUN.amberStreak === 0 ? RUN.amberStreakBonus : 0;
  state.gap = Math.min(RUN.maxGap, state.gap + RUN.amberGapGain + streakBonus);
  return {
    type: "amber",
    chain: state.chain,
    multiplier: getComboMultiplier(state),
    baitAward,
    gapGain: state.gap - before,
    streak: streakBonus > 0,
  };
}

export function collectBait(state) {
  if (state.bait < RUN.baitCapacity) {
    state.bait += 1;
    return { type: "bait", full: false };
  }
  state.amber += 5;
  return { type: "bait", full: true };
}

export function collectShield(state) {
  if (state.shield < RUN.shieldCapacity) {
    state.shield += 1;
    return { type: "shield", full: false };
  }
  state.amber += 5;
  return { type: "shield", full: true };
}

export function throwBait(state) {
  if (state.bait <= 0) {
    return { type: "bait-unavailable", reason: "empty" };
  }
  if (state.eatTimer > 0) {
    return { type: "bait-unavailable", reason: "eating" };
  }
  state.bait -= 1;
  state.eatTimer = RUN.baitEatTime;
  state.baitFallback = RUN.baitFallbackTime;
  return { type: "bait-thrown", bait: state.bait };
}

export function getRunSummary(state) {
  return {
    distance: Math.floor(state.distance),
    amber: state.amber,
    bestChain: state.bestChain,
    hits: state.hits,
    time: state.time,
  };
}
