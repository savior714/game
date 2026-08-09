/**
 * @fileoverview YouTube atomic session start — entry point contract test
 *
 * RewardSystem.startYouTubeSession() 진입점이 FreeTimeSessionStartTransaction.attemptStart()를
 * 통해 원자적 트랜잭션을 수행하는지 검증한다.
 *
 * reward.js는 browser-only IIFE 패턴이라 Node에서 require/eval로 로드하기 어렵다.
 * 따라서 startYouTubeSession이 전달하는 deps와 동일한 구조로 attemptStart를 직접 호출하여
 * 진입점의 동작을 결정적으로 검증한다.
 *
 * 실행: node tests/test_reward_start_youtube_session.mjs
 */

import { strict as assert } from "node:assert";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { createRequire } from "node:module";

const __dirname = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

const FREE_TIME_SESSION_PATH = resolve(
  __dirname, "..", "shared", "domain", "free-time-session.js",
);
const TX_PATH = resolve(
  __dirname, "..", "domains", "reward", "free-time-session-start-transaction.js",
);

const REWARD_KEY = "study_rewards";
const SESSION_KEY = "study_youtube_free_time_session_v1";

let FreeTimeSession;
let TxModule;

function loadModule(path) {
  try {
    return require(path);
  } catch (e) {
    const code = readFileSync(path, "utf-8");
    const moduleObj = { exports: {} };
    const fn = new Function("module", "exports", "self", code);
    fn(moduleObj, moduleObj.exports, globalThis);
    return moduleObj.exports;
  }
}

try {
  FreeTimeSession = loadModule(FREE_TIME_SESSION_PATH);
} catch (e) {
  console.error("Failed to load FreeTimeSession:", e.message);
  process.exit(1);
}

try {
  TxModule = loadModule(TX_PATH);
} catch (e) {
  console.error("FAIL: production module not found:", TX_PATH);
  console.error("  ", e.message);
  process.exit(1);
}

// ── Fake Storage ──────────────────────────────────────────────

class FakeStorage {
  constructor(initial = {}) {
    this._store = new Map();
    for (const [k, v] of Object.entries(initial)) {
      this._store.set(k, v);
    }
    this._setItemFailSet = new Set();
  }

  getItem(key) {
    return this._store.has(key) ? this._store.get(key) : null;
  }

  setItem(key, value) {
    if (this._setItemFailSet.has(`${key}:${this._setItemCount(key)}`)) {
      throw new Error(`Injected setItem failure: ${key}`);
    }
    this._store.set(key, value);
  }

  removeItem(key) {
    this._store.delete(key);
  }

  _setItemCount(key) {
    let count = 0;
    for (const v of this._store.values()) {
      if (v === key) count++;
    }
    return count + 1;
  }

  failSetItem(key, count) {
    this._setItemFailSet.add(`${key}:${count}`);
  }

  raw(key) {
    return this._store.has(key) ? this._store.get(key) : null;
  }
}

// ── Fake ExternalTabLauncher (matches createOpenExternal contract) ──

class FakeExternalTabLauncher {
  constructor() {
    this._callCount = 0;
    this._handle = { close: () => {} };
    this._returnNull = false;
    this._throw = false;
    this._lastUrl = null;
  }

  launch(targetUrl) {
    this._lastUrl = targetUrl;
    this._callCount++;
    if (this._throw) throw new Error("Injected launcher failure");
    if (this._returnNull) return null;
    return this._handle;
  }

  get callCount() { return this._callCount; }
  get lastUrl() { return this._lastUrl; }
  setReturnNull() { this._returnNull = true; }
  setThrow() { this._throw = true; }
}

// ── Test Harness ──────────────────────────────────────────────

function testCase(name, fn) {
  try {
    fn();
    console.log(`  PASS: ${name}`);
    return true;
  } catch (e) {
    console.error(`  FAIL: ${name}`);
    console.error(`    ${e.message}`);
    return false;
  }
}

let passed = 0;
let failed = 0;

function run(name, fn) {
  if (testCase(name, fn)) {
    passed++;
  } else {
    failed++;
  }
}

// ── Dep builder matching startYouTubeSession internals ─────────

function makeStartDeps(storage, launcher) {
  const openExternal = function() {
    return launcher.launch("https://www.youtube.com/");
  };
  const sessionId = "yt-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8);
  return {
    storage: storage,
    openExternal: openExternal,
    now: 1000000,
    sessionId: sessionId,
    FreeTimeSession: FreeTimeSession,
  };
}

console.log("YouTube atomic session start (entry point contract)\n");

// ── A. 성공: 초기 youtube_minutes=30 → 20 ─────────────────────

run("A: successful start returns started", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const launcher = new FakeExternalTabLauncher();
  const result = TxModule.attemptStart(makeStartDeps(storage, launcher));
  assert.equal(result.code, "started");
});

run("A: opener called exactly once on success", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const launcher = new FakeExternalTabLauncher();
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  assert.equal(launcher.callCount, 1);
});

run("A: target URL is https://www.youtube.com/", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const launcher = new FakeExternalTabLauncher();
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  assert.equal(launcher.lastUrl, "https://www.youtube.com/");
});

run("A: reward decreased by exactly 10", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const launcher = new FakeExternalTabLauncher();
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  const reward = JSON.parse(storage.raw(REWARD_KEY));
  assert.equal(reward.youtube_minutes, 20);
});

run("A: running session stored", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const launcher = new FakeExternalTabLauncher();
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  const session = JSON.parse(storage.raw(SESSION_KEY));
  assert.equal(session.status, "running");
});

run("A: session chargedMinutes is 10", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const launcher = new FakeExternalTabLauncher();
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  const session = JSON.parse(storage.raw(SESSION_KEY));
  assert.equal(session.chargedMinutes, 10);
});

run("A: journal removed after success", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const launcher = new FakeExternalTabLauncher();
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  assert.equal(storage.raw("study_youtube_free_time_start_tx_v1"), null);
});

run("A: other reward fields preserved", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ gems: 5, youtube_minutes: 30, snacks: 2 }),
  });
  const launcher = new FakeExternalTabLauncher();
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  const reward = JSON.parse(storage.raw(REWARD_KEY));
  assert.equal(reward.gems, 5);
  assert.equal(reward.snacks, 2);
});

// ── B. popup_blocked ──────────────────────────────────────────

run("B: popup blocked returns popup_blocked", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const launcher = new FakeExternalTabLauncher();
  launcher.setReturnNull();
  const result = TxModule.attemptStart(makeStartDeps(storage, launcher));
  assert.equal(result.code, "popup_blocked");
});

run("B: opener attempted exactly once on popup blocked", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const launcher = new FakeExternalTabLauncher();
  launcher.setReturnNull();
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  assert.equal(launcher.callCount, 1);
});

run("B: reward unchanged after popup blocked", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const launcher = new FakeExternalTabLauncher();
  launcher.setReturnNull();
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  const reward = JSON.parse(storage.raw(REWARD_KEY));
  assert.equal(reward.youtube_minutes, 30);
});

run("B: no session created after popup blocked", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const launcher = new FakeExternalTabLauncher();
  launcher.setReturnNull();
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  assert.equal(storage.raw(SESSION_KEY), null);
});

run("B: no journal after popup blocked", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const launcher = new FakeExternalTabLauncher();
  launcher.setReturnNull();
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  assert.equal(storage.raw("study_youtube_free_time_start_tx_v1"), null);
});

// ── C. already_active ────────────────────────────────────────

run("C: existing active session returns already_active", () => {
  const session = FreeTimeSession.start({ now: 1000000, sessionId: "sess-existing", source: "reward" });
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
    [SESSION_KEY]: JSON.stringify(session),
  });
  const launcher = new FakeExternalTabLauncher();
  const result = TxModule.attemptStart(makeStartDeps(storage, launcher));
  assert.equal(result.code, "already_active");
});

run("C: opener not called when already active", () => {
  const session = FreeTimeSession.start({ now: 1000000, sessionId: "sess-existing", source: "reward" });
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
    [SESSION_KEY]: JSON.stringify(session),
  });
  const launcher = new FakeExternalTabLauncher();
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  assert.equal(launcher.callCount, 0);
});

run("C: reward unchanged when already active", () => {
  const session = FreeTimeSession.start({ now: 1000000, sessionId: "sess-existing", source: "reward" });
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
    [SESSION_KEY]: JSON.stringify(session),
  });
  const launcher = new FakeExternalTabLauncher();
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  const reward = JSON.parse(storage.raw(REWARD_KEY));
  assert.equal(reward.youtube_minutes, 30);
});

run("C: original session preserved on already_active", () => {
  const session = FreeTimeSession.start({ now: 1000000, sessionId: "sess-existing", source: "reward" });
  const sessionRaw = JSON.stringify(session);
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
    [SESSION_KEY]: sessionRaw,
  });
  const launcher = new FakeExternalTabLauncher();
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  assert.equal(storage.raw(SESSION_KEY), sessionRaw);
});

// ── D. insufficient_time ─────────────────────────────────────

run("D: insufficient minutes returns insufficient_time", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 9 }),
  });
  const launcher = new FakeExternalTabLauncher();
  const result = TxModule.attemptStart(makeStartDeps(storage, launcher));
  assert.equal(result.code, "insufficient_time");
});

run("D: opener not called when insufficient time", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 9 }),
  });
  const launcher = new FakeExternalTabLauncher();
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  assert.equal(launcher.callCount, 0);
});

run("D: reward unchanged when insufficient time", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 9 }),
  });
  const launcher = new FakeExternalTabLauncher();
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  const reward = JSON.parse(storage.raw(REWARD_KEY));
  assert.equal(reward.youtube_minutes, 9);
});

// ── E. 중복 클릭 (double-click) — 두 번 시도 시 두 번째는 already_active ──

run("E: double click first returns started", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const launcher = new FakeExternalTabLauncher();
  const r1 = TxModule.attemptStart(makeStartDeps(storage, launcher));
  assert.equal(r1.code, "started");
});

run("E: double click second returns already_active", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const launcher1 = new FakeExternalTabLauncher();
  TxModule.attemptStart(makeStartDeps(storage, launcher1));
  const launcher2 = new FakeExternalTabLauncher();
  const r2 = TxModule.attemptStart(makeStartDeps(storage, launcher2));
  assert.equal(r2.code, "already_active");
});

run("E: double click — opener called exactly once total", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const launcher = new FakeExternalTabLauncher();
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  assert.equal(launcher.callCount, 1);
});

run("E: double click — reward decreased exactly once (20)", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const launcher = new FakeExternalTabLauncher();
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  const reward = JSON.parse(storage.raw(REWARD_KEY));
  assert.equal(reward.youtube_minutes, 20);
});

run("E: double click — exactly one session", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const launcher = new FakeExternalTabLauncher();
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  TxModule.attemptStart(makeStartDeps(storage, launcher));
  const session = JSON.parse(storage.raw(SESSION_KEY));
  assert.equal(session.status, "running");
});

// ── 결과 ─────────────────────────────────────────────────────

console.log(`\nResults: ${passed} passed, ${failed} failed`);

if (failed > 0) {
  process.exit(1);
}
