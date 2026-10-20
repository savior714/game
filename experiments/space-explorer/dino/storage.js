/** Validated local persistence for Dino Escape settings and records. */

import { QUALITY, STORAGE_KEY } from "./constants.js";
import { clamp } from "./util.js";

function prefersReducedMotion() {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches === true;
}

export function createDefaultProfile() {
  return {
    bestDistance: 0,
    bestCombo: 0,
    runs: 0,
    settings: {
      sound: true,
      music: true,
      sfxVolume: 0.7,
      musicVolume: 0.5,
      // Respect the OS motion preference out of the box; the in-game toggle
      // still lets a player opt back in.
      shake: !prefersReducedMotion(),
      quality: QUALITY.auto,
    },
  };
}

function normalizeNumber(value, fallback, min, max) {
  return typeof value === "number" && Number.isFinite(value) ? clamp(value, min, max) : fallback;
}

function normalizeBoolean(value, fallback) {
  return typeof value === "boolean" ? value : fallback;
}

function normalizeQuality(value) {
  return value === QUALITY.high || value === QUALITY.low ? value : QUALITY.auto;
}

/** Accepts persisted data from any older/unknown shape and returns a valid profile. */
export function normalizeProfile(raw) {
  const fallback = createDefaultProfile();
  if (!raw || typeof raw !== "object") {
    return fallback;
  }
  const settings = raw.settings && typeof raw.settings === "object" ? raw.settings : {};
  return {
    bestDistance: Math.floor(normalizeNumber(raw.bestDistance, 0, 0, 100000)),
    bestCombo: Math.floor(normalizeNumber(raw.bestCombo, 0, 0, 999)),
    runs: Math.floor(normalizeNumber(raw.runs, 0, 0, 1000000)),
    settings: {
      sound: normalizeBoolean(settings.sound, fallback.settings.sound),
      music: normalizeBoolean(settings.music, fallback.settings.music),
      sfxVolume: normalizeNumber(settings.sfxVolume, fallback.settings.sfxVolume, 0, 1),
      musicVolume: normalizeNumber(settings.musicVolume, fallback.settings.musicVolume, 0, 1),
      shake: normalizeBoolean(settings.shake, fallback.settings.shake),
      quality: normalizeQuality(settings.quality),
    },
  };
}

export function loadProfile() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return createDefaultProfile();
    }
    return normalizeProfile(JSON.parse(raw));
  } catch (error) {
    console.warn("Dino Escape: could not read saved profile", error);
    return createDefaultProfile();
  }
}

export function saveProfile(profile) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(normalizeProfile(profile)));
    return true;
  } catch (error) {
    console.warn("Dino Escape: could not save profile", error);
    return false;
  }
}
