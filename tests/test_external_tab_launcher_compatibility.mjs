/**
 * @fileoverview ExternalTabLauncher × FreeTimeSessionStartTransaction 호환 검증
 *
 * 어댑터의 createOpenExternal 결과를 attemptStart의 openExternal로 전달하여
 * 기존 트랜잭션 계약이 그대로 통과하는지 검증한다.
 *
 * 실행: node tests/test_external_tab_launcher_compatibility.mjs
 */

import { strict as assert } from "node:assert";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

const FREE_TIME_SESSION_PATH = resolve(
  __dirname,
  "..",
  "shared",
  "domain",
  "free-time-session.js",
);
const TX_PATH = resolve(
  __dirname,
  "..",
  "domains",
  "reward",
  "free-time-session-start-transaction.js",
);
const LAUNCHER_PATH = resolve(
  __dirname,
  "..",
  "shared",
  "domain",
  "external-tab-launcher.js",
);

let FreeTimeSession, TxModule, Launcher;
try {
  FreeTimeSession = require(FREE_TIME_SESSION_PATH);
} catch (e) {
  console.error("FAIL: FreeTimeSession not found:", e.message);
  process.exit(1);
}
try {
  TxModule = require(TX_PATH);
} catch (e) {
  console.error("FAIL: transaction not found:", e.message);
  process.exit(1);
}
try {
  Launcher = require(LAUNCHER_PATH);
} catch (e) {
  console.error("FAIL: launcher not found:", e.message);
  process.exit(1);
}

const REWARD_KEY = "study_rewards";
const SESSION_KEY = "study_youtube_free_time_session_v1";
const JOURNAL_KEY = "study_youtube_free_time_start_tx_v1";
const NOW = 1000000;

// ── Fake Storage (same as existing tests) ──────────────────────

class FakeStorage {
  constructor(initial = {}) {
    this._store = new Map();
    for (const [k, v] of Object.entries(initial)) this._store.set(k, v);
    this._opCounts = new Map();
  }
  getItem(key) { return this._store.has(key) ? this._store.get(key) : null; }
  setItem(key, value) {
    const c = (this._opCounts.get(key) || 0) + 1;
    this._opCounts.set(key, c);
    this._store.set(key, value);
  }
  removeItem(key) { this._store.delete(key); }
  raw(key) { return this._store.has(key) ? this._store.get(key) : null; }
}

// ── Fake window for launcher ───────────────────────────────────

function makeFakeWindow(openResult) {
  return { open() { return openResult; } };
}

function makeFakeHandle() {
  let closeCount = 0;
  return {
    close() { closeCount++; },
    get _closeCount() { return closeCount; },
    set opener(_v) { /* noop — success path */ },
    get location() {
      return { set href(_u) { /* noop — success path */ } };
    },
  };
}

// ── Test harness ───────────────────────────────────────────────

let passed = 0, failed = 0;
function run(name, fn) {
  try { fn(); console.log(`  PASS: ${name}`); passed++; }
  catch (e) { console.error(`  FAIL: ${name}\n    ${e.message}`); failed++; }
}

console.log("ExternalTabLauncher × FreeTimeSessionStartTransaction compatibility\n");

// ── 1. 성공 핸들 → started ─────────────────────────────────────

run("1: adapter success handle → transaction returns started", () => {
  const handle = makeFakeHandle();
  const win = makeFakeWindow(handle);
  const openExternal = Launcher.createOpenExternal(win, "https://example.com");
  const storage = new FakeStorage({ [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }) });
  const result = TxModule.attemptStart({
    storage, openExternal, now: NOW, sessionId: "compat-001", FreeTimeSession,
  });
  assert.equal(result.code, "started");
});

run("1: adapter success handle → reward decreased", () => {
  const handle = makeFakeHandle();
  const win = makeFakeWindow(handle);
  const openExternal = Launcher.createOpenExternal(win, "https://example.com");
  const storage = new FakeStorage({ [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }) });
  TxModule.attemptStart({ storage, openExternal, now: NOW, sessionId: "compat-002", FreeTimeSession });
  const reward = JSON.parse(storage.raw(REWARD_KEY));
  assert.equal(reward.youtube_minutes, 20);
});

run("1: adapter success handle → session stored", () => {
  const handle = makeFakeHandle();
  const win = makeFakeWindow(handle);
  const openExternal = Launcher.createOpenExternal(win, "https://example.com");
  const storage = new FakeStorage({ [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }) });
  TxModule.attemptStart({ storage, openExternal, now: NOW, sessionId: "compat-003", FreeTimeSession });
  assert.ok(storage.raw(SESSION_KEY));
});

run("1: adapter success handle → journal removed", () => {
  const handle = makeFakeHandle();
  const win = makeFakeWindow(handle);
  const openExternal = Launcher.createOpenExternal(win, "https://example.com");
  const storage = new FakeStorage({ [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }) });
  TxModule.attemptStart({ storage, openExternal, now: NOW, sessionId: "compat-004", FreeTimeSession });
  assert.equal(storage.raw(JOURNAL_KEY), null);
});

// ── 2. 차단 결과 → popup_blocked, reward/session/journal unchanged ─

run("2: adapter popup blocked → popup_blocked", () => {
  const win = makeFakeWindow(null);
  const openExternal = Launcher.createOpenExternal(win, "https://example.com");
  const storage = new FakeStorage({ [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }) });
  const result = TxModule.attemptStart({
    storage, openExternal, now: NOW, sessionId: "compat-005", FreeTimeSession,
  });
  assert.equal(result.code, "popup_blocked");
});

run("2: adapter popup blocked → reward unchanged", () => {
  const originalRaw = JSON.stringify({ youtube_minutes: 30 });
  const win = makeFakeWindow(null);
  const openExternal = Launcher.createOpenExternal(win, "https://example.com");
  const storage = new FakeStorage({ [REWARD_KEY]: originalRaw });
  TxModule.attemptStart({ storage, openExternal, now: NOW, sessionId: "compat-006", FreeTimeSession });
  assert.equal(storage.raw(REWARD_KEY), originalRaw);
});

run("2: adapter popup blocked → no session created", () => {
  const win = makeFakeWindow(null);
  const openExternal = Launcher.createOpenExternal(win, "https://example.com");
  const storage = new FakeStorage({ [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }) });
  TxModule.attemptStart({ storage, openExternal, now: NOW, sessionId: "compat-007", FreeTimeSession });
  assert.equal(storage.raw(SESSION_KEY), null);
});

run("2: adapter popup blocked → no journal created", () => {
  const win = makeFakeWindow(null);
  const openExternal = Launcher.createOpenExternal(win, "https://example.com");
  const storage = new FakeStorage({ [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }) });
  TxModule.attemptStart({ storage, openExternal, now: NOW, sessionId: "compat-008", FreeTimeSession });
  assert.equal(storage.raw(JOURNAL_KEY), null);
});

// ── 3. opener 예외 → popup_blocked ─────────────────────────────

run("3: adapter opener throws → popup_blocked", () => {
  const handle = makeFakeHandle();
  let openerThrow = false;
  Object.defineProperty(handle, "opener", {
    set(v) { if (!openerThrow) { openerThrow = true; throw new Error("opener blocked"); } },
  });
  const win = makeFakeWindow(handle);
  const openExternal = Launcher.createOpenExternal(win, "https://example.com");
  const storage = new FakeStorage({ [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }) });
  const result = TxModule.attemptStart({
    storage, openExternal, now: NOW, sessionId: "compat-009", FreeTimeSession,
  });
  assert.equal(result.code, "popup_blocked");
});

// ── 결과 ───────────────────────────────────────────────────────

console.log(`\nResults: ${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
