/** Small math / formatting helpers shared by the 3D game modules. */

export const TAU = Math.PI * 2;

export function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

export function clamp01(value) {
  return clamp(value, 0, 1);
}

export function lerp(a, b, t) {
  return a + (b - a) * t;
}

export function invLerp(a, b, value) {
  if (Math.abs(b - a) < 1e-6) {
    return 0;
  }
  return clamp01((value - a) / (b - a));
}

export function damp(current, target, lambda, dt) {
  return lerp(current, target, 1 - Math.exp(-lambda * dt));
}

export function dampAngle(current, target, lambda, dt) {
  let delta = ((target - current + Math.PI) % TAU) - Math.PI;
  if (delta < -Math.PI) {
    delta += TAU;
  }
  return current + delta * (1 - Math.exp(-lambda * dt));
}

export function smoothstep(edge0, edge1, value) {
  const t = invLerp(edge0, edge1, value);
  return t * t * (3 - 2 * t);
}

export function moveTowards(current, target, maxDelta) {
  if (Math.abs(target - current) <= maxDelta) {
    return target;
  }
  return current + Math.sign(target - current) * maxDelta;
}

export function randRange(min, max) {
  return min + Math.random() * (max - min);
}

export function randInt(min, max) {
  return Math.floor(randRange(min, max + 1));
}

export function pick(list) {
  return list[Math.floor(Math.random() * list.length)];
}

export function pickWeighted(entries) {
  let total = 0;
  for (const entry of entries) {
    total += entry.weight;
  }
  let roll = Math.random() * total;
  for (const entry of entries) {
    roll -= entry.weight;
    if (roll <= 0) {
      return entry;
    }
  }
  return entries[entries.length - 1];
}

export function chance(probability) {
  return Math.random() < probability;
}

export function wrap(value, size) {
  return ((value % size) + size) % size;
}

/** Formats a distance in meters with thousands separators, e.g. 1284 -> "1,284". */
export function formatMeters(value) {
  const rounded = Math.max(0, Math.floor(value));
  return rounded.toLocaleString("en-US");
}

export function formatGap(value) {
  return `${Math.max(0, value).toFixed(1)} m`;
}

export function formatSigned(value, digits = 1) {
  const rounded = value.toFixed(digits);
  return value > 0 ? `+${rounded}` : rounded;
}

/** HSL helper used for procedural scenery variety. */
export function varyColor(color, hueJitter = 0.01, lightJitter = 0.05) {
  if (!color || typeof color.getHSL !== "function") {
    return color;
  }
  const hsl = { h: 0, s: 0, l: 0 };
  color.getHSL(hsl);
  color.setHSL(
    (hsl.h + (Math.random() * 2 - 1) * hueJitter + 1) % 1,
    clamp01(hsl.s + (Math.random() * 2 - 1) * 0.05),
    clamp01(hsl.l + (Math.random() * 2 - 1) * lightJitter),
  );
  return color;
}

export function nowSeconds() {
  return (typeof performance !== "undefined" ? performance.now() : Date.now()) / 1000;
}
