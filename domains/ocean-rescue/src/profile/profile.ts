/**
 * Typed canonical profile module for Ocean Rescue (WP-31A).
 *
 * This module is the strictly typed canonical implementation of the legacy
 * `src/profile.js`. The legacy file is retained byte-for-byte as the
 * operational rollback authority referenced only by
 * `build-manifest.legacy.json`.
 *
 * The module preserves the legacy observable runtime contract exactly:
 * constants, catalog order and value immutability, initial state, hydration,
 * selection, confirmation, storage-boundary exception behavior, malformed
 * payload cleanup, persistence-failure semantics, snapshot immutability, and
 * the temporary `window.OceanRescue.Profile` compatibility ABI consumed by
 * `src/app.js`.
 */

import type { OceanRescueNamespace } from "../contracts/runtime-abi";

export type ProfileAnimalId = "arctic-fox" | "beaver" | "red-panda";

export interface ProfileAnimal {
  readonly id: ProfileAnimalId;
  readonly name: string;
}

export interface ProfileSnapshot {
  readonly playerName: "Aiden";
  readonly selectedAnimalId: ProfileAnimalId | null;
  readonly chosenAnimalId: ProfileAnimalId | null;
  readonly complete: boolean;
}

export interface ProfileStoredPayloadV1 {
  readonly schemaVersion: 1;
  readonly playerName: "Aiden";
  readonly animalId: ProfileAnimalId;
}

export interface SanitizedProfilePayload {
  readonly playerName: "Aiden";
  readonly animalId: ProfileAnimalId;
}

/** Narrow storage capability required by the profile module. */
export interface ProfileStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem?(key: string): void;
}

export interface ProfileApi {
  readonly Catalog: readonly ProfileAnimal[];
  readonly getSnapshot: () => ProfileSnapshot;
  readonly selectAnimal: (animalId: unknown) => boolean;
  readonly confirmSelection: () => boolean;
}

const STORAGE_KEY = "aidengame.oceanRescue.profile";
const SCHEMA_VERSION = 1;
const PLAYER_NAME = "Aiden";

function freeze<T>(value: T): Readonly<T> {
  return Object.freeze(value);
}

const CATALOG: readonly ProfileAnimal[] = freeze([
  freeze<ProfileAnimal>({ id: "arctic-fox", name: "Arctic fox" }),
  freeze<ProfileAnimal>({ id: "beaver", name: "Beaver" }),
  freeze<ProfileAnimal>({ id: "red-panda", name: "Red panda" }),
]);

const validAnimalIds: Record<string, boolean> = {};
for (let i = 0; i < CATALOG.length; i += 1) {
  validAnimalIds[CATALOG[i].id] = true;
}

interface MutableProfileState {
  selectedAnimalId: ProfileAnimalId | null;
  chosenAnimalId: ProfileAnimalId | null;
  complete: boolean;
}

const state: MutableProfileState = {
  selectedAnimalId: null,
  chosenAnimalId: null,
  complete: false,
};

let confirmedCount = 0;
let persistCount = 0;

function resolveStorage(): ProfileStorage | null {
  if (typeof window === "undefined") {
    return null;
  }
  const storage: unknown = window.localStorage;
  if (!storage) {
    return null;
  }
  if (typeof (storage as ProfileStorage).getItem !== "function") {
    return null;
  }
  if (typeof (storage as ProfileStorage).setItem !== "function") {
    return null;
  }
  return storage as ProfileStorage;
}

function bestEffortRemoveStoredPayload(): void {
  const storage = resolveStorage();
  if (storage === null) {
    return;
  }
  try {
    if (typeof storage.removeItem === "function") {
      storage.removeItem(STORAGE_KEY);
    }
  } catch (error) {
    return;
  }
}

function isValidAnimalId(animalId: unknown): animalId is ProfileAnimalId {
  if (typeof animalId !== "string") {
    return false;
  }
  return validAnimalIds[animalId] === true;
}

function sanitizeStoredPayload(
  payload: unknown,
): SanitizedProfilePayload | null {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return null;
  }
  const record = payload as Record<string, unknown>;
  if (record.schemaVersion !== SCHEMA_VERSION) {
    return null;
  }
  if (record.playerName !== PLAYER_NAME) {
    return null;
  }
  if (!isValidAnimalId(record.animalId)) {
    return null;
  }
  return {
    playerName: PLAYER_NAME,
    animalId: record.animalId,
  };
}

function readStoredPayload(): SanitizedProfilePayload | null {
  const storage = resolveStorage();
  if (storage === null) {
    return null;
  }
  let raw: string | null;
  try {
    raw = storage.getItem(STORAGE_KEY);
  } catch (error) {
    return null;
  }
  if (typeof raw !== "string" || raw === "") {
    return null;
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (error) {
    bestEffortRemoveStoredPayload();
    return null;
  }
  const sanitized = sanitizeStoredPayload(parsed);
  if (sanitized === null) {
    bestEffortRemoveStoredPayload();
    return null;
  }
  return sanitized;
}

function persist(): boolean {
  const storage = resolveStorage();
  if (storage === null) {
    return false;
  }
  if (!isValidAnimalId(state.chosenAnimalId)) {
    return false;
  }
  const payload: ProfileStoredPayloadV1 = {
    schemaVersion: SCHEMA_VERSION,
    playerName: PLAYER_NAME,
    animalId: state.chosenAnimalId,
  };
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(payload));
    persistCount += 1;
    return true;
  } catch (error) {
    return false;
  }
}

function hydrate(): void {
  const stored = readStoredPayload();
  if (stored === null) {
    return;
  }
  state.chosenAnimalId = stored.animalId;
  state.complete = true;
}

function getSnapshot(): ProfileSnapshot {
  return freeze({
    playerName: PLAYER_NAME,
    selectedAnimalId: state.selectedAnimalId,
    chosenAnimalId: state.chosenAnimalId,
    complete: state.complete,
  });
}

function selectAnimal(animalId: unknown): boolean {
  if (!isValidAnimalId(animalId)) {
    return false;
  }
  state.selectedAnimalId = animalId;
  return true;
}

function confirmSelection(): boolean {
  if (state.complete) {
    return false;
  }
  if (!isValidAnimalId(state.selectedAnimalId)) {
    return false;
  }
  state.chosenAnimalId = state.selectedAnimalId;
  const persisted = persist();
  if (persisted) {
    state.complete = true;
    confirmedCount += 1;
  }
  return true;
}

hydrate();

const Profile: ProfileApi = freeze({
  Catalog: CATALOG,
  getSnapshot,
  selectAnimal,
  confirmSelection,
});

const win = window as Window & { OceanRescue?: OceanRescueNamespace };
const root = win.OceanRescue || {};
win.OceanRescue = root;
root.Profile = Profile;

export { Profile };
