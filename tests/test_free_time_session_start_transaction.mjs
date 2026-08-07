/**
 * @fileoverview 자유시간 시작 트랜잭션 — focused runtime test
 *
 * 외부 탭 생성, 15분 차감, 세션 저장이 하나의 복구 가능한 트랜잭션 경계에서
 * 수행되는지 검증한다. 브라우저 API나 실제 저장소에 의존하지 않는다.
 *
 * 실행: node tests/test_free_time_session_start_transaction.mjs
 */

import { strict as assert } from "node:assert";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { createRequire } from "node:module";

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

const REWARD_KEY = "study_rewards";
const SESSION_KEY = "study_youtube_free_time_session_v1";
const JOURNAL_KEY = "study_youtube_free_time_start_tx_v1";

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

const NOW = 1000000;

// ── Fake Storage ──────────────────────────────────────────────

class FakeStorage {
  constructor(initial = {}) {
    this._store = new Map();
    for (const [k, v] of Object.entries(initial)) {
      this._store.set(k, v);
    }
    this._calls = [];
    this._setItemFailSet = new Set();
    this._removeItemFailSet = new Set();
    this._opCounts = new Map();
  }

  getItem(key) {
    this._calls.push({ op: "getItem", key });
    return this._store.has(key) ? this._store.get(key) : null;
  }

  setItem(key, value) {
    const count = (this._opCounts.get(key) || 0) + 1;
    this._opCounts.set(key, count);
    this._calls.push({ op: "setItem", key, value, count });
    if (this._setItemFailSet.has(`${key}:${count}`)) {
      throw new Error(`Injected setItem failure: ${key} #${count}`);
    }
    this._store.set(key, value);
  }

  removeItem(key) {
    this._calls.push({ op: "removeItem", key });
    if (this._removeItemFailSet.has(key)) {
      throw new Error(`Injected removeItem failure: ${key}`);
    }
    this._store.delete(key);
  }

  failSetItem(key, count) {
    this._setItemFailSet.add(`${key}:${count}`);
  }

  failRemoveItem(key) {
    this._removeItemFailSet.add(key);
  }

  raw(key) {
    return this._store.has(key) ? this._store.get(key) : null;
  }

  get calls() {
    return this._calls;
  }
}

// ── Fake Opener ───────────────────────────────────────────────

class FakeOpener {
  constructor() {
    this._callCount = 0;
    this._handle = { close: () => { this._closeCount++; } };
    this._closeCount = 0;
    this._returnNull = false;
    this._throw = false;
  }

  open() {
    this._callCount++;
    if (this._throw) throw new Error("Injected opener failure");
    if (this._returnNull) return null;
    return this._handle;
  }

  get callCount() {
    return this._callCount;
  }
  get closeCount() {
    return this._closeCount;
  }
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

function makeDeps(storage, opener, opts = {}) {
  return {
    storage: storage,
    openExternal: typeof opener === "function" ? opener : (() => opener.open()),
    now: opts.now !== undefined ? opts.now : NOW,
    sessionId: opts.sessionId || "sess-001",
    FreeTimeSession: FreeTimeSession,
  };
}

console.log("FreeTimeSession Start Transaction tests\n");

// ── A. 활성 세션 중복 시작 ───────────────────────────────────

run("A: active session blocks new start with already_active", () => {
  const session = FreeTimeSession.start({ now: NOW, sessionId: "sess-existing", source: "reward" });
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
    [SESSION_KEY]: JSON.stringify(session),
  });
  const opener = new FakeOpener();
  const result = TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(result.code, "already_active");
});

run("A: opener not called when session already active", () => {
  const session = FreeTimeSession.start({ now: NOW, sessionId: "sess-existing", source: "reward" });
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
    [SESSION_KEY]: JSON.stringify(session),
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(opener.callCount, 0);
});

run("A: reward raw unchanged when session already active", () => {
  const session = FreeTimeSession.start({ now: NOW, sessionId: "sess-existing", source: "reward" });
  const rewardRaw = JSON.stringify({ youtube_minutes: 30 });
  const storage = new FakeStorage({
    [REWARD_KEY]: rewardRaw,
    [SESSION_KEY]: JSON.stringify(session),
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(storage.raw(REWARD_KEY), rewardRaw);
});

run("A: session raw unchanged when session already active", () => {
  const session = FreeTimeSession.start({ now: NOW, sessionId: "sess-existing", source: "reward" });
  const sessionRaw = JSON.stringify(session);
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
    [SESSION_KEY]: sessionRaw,
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(storage.raw(SESSION_KEY), sessionRaw);
});

run("A: no journal created when session already active", () => {
  const session = FreeTimeSession.start({ now: NOW, sessionId: "sess-existing", source: "reward" });
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
    [SESSION_KEY]: JSON.stringify(session),
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(storage.raw(JOURNAL_KEY), null);
});

// ── B. 보유 시간 부족 ─────────────────────────────────────────

run("B: insufficient minutes returns insufficient_time", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 14 }),
  });
  const opener = new FakeOpener();
  const result = TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(result.code, "insufficient_time");
});

run("B: opener not called when insufficient time", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 14 }),
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(opener.callCount, 0);
});

run("B: no storage writes when insufficient time", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 14 }),
  });
  const opener = new FakeOpener();
  const rewardBefore = storage.raw(REWARD_KEY);
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(storage.raw(REWARD_KEY), rewardBefore);
  const writes = storage.calls.filter((c) => c.op === "setItem" || c.op === "removeItem");
  assert.equal(writes.length, 0);
});

// ── C. 팝업 차단 ──────────────────────────────────────────────

run("C: null opener returns popup_blocked", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  opener.setReturnNull();
  const result = TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(result.code, "popup_blocked");
});

run("C: opener called exactly once on popup blocked", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  opener.setReturnNull();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(opener.callCount, 1);
});

run("C: reward stays at 30 after popup blocked", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  opener.setReturnNull();
  TxModule.attemptStart(makeDeps(storage, opener));
  const reward = JSON.parse(storage.raw(REWARD_KEY));
  assert.equal(reward.youtube_minutes, 30);
});

run("C: no session created after popup blocked", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  opener.setReturnNull();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(storage.raw(SESSION_KEY), null);
});

run("C: no journal created after popup blocked", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  opener.setReturnNull();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(storage.raw(JOURNAL_KEY), null);
});

run("C: opener throwing returns popup_blocked", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  opener.setThrow();
  const result = TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(result.code, "popup_blocked");
});

run("C: no storage writes when opener throws", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  opener.setThrow();
  const rewardBefore = storage.raw(REWARD_KEY);
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(storage.raw(REWARD_KEY), rewardBefore);
  assert.equal(storage.raw(SESSION_KEY), null);
  assert.equal(storage.raw(JOURNAL_KEY), null);
});

// ── D. 정상 성공 ──────────────────────────────────────────────

run("D: successful start returns started", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ gems: 5, youtube_minutes: 30, snacks: 2 }),
  });
  const opener = new FakeOpener();
  const result = TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(result.code, "started");
});

run("D: opener called exactly once on success", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(opener.callCount, 1);
});

run("D: reward decreased by exactly 15", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  const reward = JSON.parse(storage.raw(REWARD_KEY));
  assert.equal(reward.youtube_minutes, 15);
});

run("D: running session stored", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  const session = JSON.parse(storage.raw(SESSION_KEY));
  assert.equal(session.status, "running");
});

run("D: session chargedMinutes is 15", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  const session = JSON.parse(storage.raw(SESSION_KEY));
  assert.equal(session.chargedMinutes, 15);
});

run("D: session startedAt equals now", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  const session = JSON.parse(storage.raw(SESSION_KEY));
  assert.equal(session.startedAt, NOW);
});

run("D: session endsAt equals now + 900000", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  const session = JSON.parse(storage.raw(SESSION_KEY));
  assert.equal(session.endsAt, NOW + 900000);
});

run("D: session source is reward", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  const session = JSON.parse(storage.raw(SESSION_KEY));
  assert.equal(session.source, "reward");
});

run("D: session sessionId preserved", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener, { sessionId: "sess-xyz" }));
  const session = JSON.parse(storage.raw(SESSION_KEY));
  assert.equal(session.sessionId, "sess-xyz");
});

run("D: journal removed after success", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(storage.raw(JOURNAL_KEY), null);
});

run("D: other reward fields preserved", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ gems: 5, youtube_minutes: 30, snacks: 2, marble_plays: 1 }),
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  const reward = JSON.parse(storage.raw(REWARD_KEY));
  assert.equal(reward.gems, 5);
  assert.equal(reward.snacks, 2);
  assert.equal(reward.marble_plays, 1);
});

run("D: result includes stored session", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  const result = TxModule.attemptStart(makeDeps(storage, opener));
  assert.ok(result.session);
  assert.equal(result.session.status, "running");
});

// ── E. 성공 후 동일 세션 재시도 ─────────────────────────────

run("E: retry after success returns already_active", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener, { sessionId: "sess-001" }));
  const opener2 = new FakeOpener();
  const result = TxModule.attemptStart(makeDeps(storage, opener2, { sessionId: "sess-002" }));
  assert.equal(result.code, "already_active");
});

run("E: retry does not call opener again", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener, { sessionId: "sess-001" }));
  const opener2 = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener2, { sessionId: "sess-002" }));
  assert.equal(opener2.callCount, 0);
});

run("E: reward stays at 15 after retry", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener, { sessionId: "sess-001" }));
  const opener2 = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener2, { sessionId: "sess-002" }));
  const reward = JSON.parse(storage.raw(REWARD_KEY));
  assert.equal(reward.youtube_minutes, 15);
});

run("E: original sessionId preserved on retry", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener, { sessionId: "sess-001" }));
  const opener2 = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener2, { sessionId: "sess-002" }));
  const session = JSON.parse(storage.raw(SESSION_KEY));
  assert.equal(session.sessionId, "sess-001");
});

run("E: original endsAt preserved on retry", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener, { sessionId: "sess-001" }));
  const originalEndsAt = JSON.parse(storage.raw(SESSION_KEY)).endsAt;
  const opener2 = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener2, { sessionId: "sess-002" }));
  const session = JSON.parse(storage.raw(SESSION_KEY));
  assert.equal(session.endsAt, originalEndsAt);
});

// ── F. reward 저장 실패 ───────────────────────────────────────

run("F: reward write failure returns commit_failed", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  storage.failSetItem(REWARD_KEY, 1);
  const opener = new FakeOpener();
  const result = TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(result.code, "commit_failed");
});

run("F: reward raw restored after reward write failure", () => {
  const originalRaw = JSON.stringify({ youtube_minutes: 30 });
  const storage = new FakeStorage({ [REWARD_KEY]: originalRaw });
  storage.failSetItem(REWARD_KEY, 1);
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(storage.raw(REWARD_KEY), originalRaw);
});

run("F: session raw stays null after reward write failure", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  storage.failSetItem(REWARD_KEY, 1);
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(storage.raw(SESSION_KEY), null);
});

run("F: journal removed after reward write failure", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  storage.failSetItem(REWARD_KEY, 1);
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(storage.raw(JOURNAL_KEY), null);
});

run("F: handle close called exactly once after reward write failure", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  storage.failSetItem(REWARD_KEY, 1);
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(opener.closeCount, 1);
});

// ── G. session 저장 실패 ──────────────────────────────────────

run("G: session write failure returns commit_failed", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  storage.failSetItem(SESSION_KEY, 1);
  const opener = new FakeOpener();
  const result = TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(result.code, "commit_failed");
});

run("G: reward raw restored after session write failure", () => {
  const originalRaw = JSON.stringify({ youtube_minutes: 30 });
  const storage = new FakeStorage({ [REWARD_KEY]: originalRaw });
  storage.failSetItem(SESSION_KEY, 1);
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(storage.raw(REWARD_KEY), originalRaw);
});

run("G: session raw stays null after session write failure", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  storage.failSetItem(SESSION_KEY, 1);
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(storage.raw(SESSION_KEY), null);
});

run("G: journal removed after session write failure", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  storage.failSetItem(SESSION_KEY, 1);
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(storage.raw(JOURNAL_KEY), null);
});

run("G: handle close called exactly once after session write failure", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  storage.failSetItem(SESSION_KEY, 1);
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(opener.closeCount, 1);
});

// ── H. 중간 crash 복구 (반쪽 상태 → rollback) ───────────────

run("H: incomplete transaction rolled back via recover", () => {
  const previousRewardRaw = JSON.stringify({ youtube_minutes: 30 });
  const previousSessionRaw = null;
  const targetRewardRaw = JSON.stringify({ youtube_minutes: 15 });
  const targetSessionRaw = JSON.stringify(
    FreeTimeSession.start({ now: NOW, sessionId: "sess-001", source: "reward" })
  );
  const storage = new FakeStorage({
    [REWARD_KEY]: targetRewardRaw,
    [SESSION_KEY]: previousSessionRaw,
    [JOURNAL_KEY]: JSON.stringify({
      version: 1,
      transactionId: "sess-001",
      previousRewardRaw,
      previousSessionRaw,
      targetRewardRaw,
      targetSessionRaw,
    }),
  });
  const result = TxModule.recoverPendingTransaction({ storage });
  assert.equal(result.code, "rolled_back_incomplete_transaction");
});

run("H: reward restored to previous after incomplete rollback", () => {
  const previousRewardRaw = JSON.stringify({ youtube_minutes: 30 });
  const targetRewardRaw = JSON.stringify({ youtube_minutes: 15 });
  const targetSessionRaw = JSON.stringify(
    FreeTimeSession.start({ now: NOW, sessionId: "sess-001", source: "reward" })
  );
  const storage = new FakeStorage({
    [REWARD_KEY]: targetRewardRaw,
    [SESSION_KEY]: null,
    [JOURNAL_KEY]: JSON.stringify({
      version: 1,
      transactionId: "sess-001",
      previousRewardRaw,
      previousSessionRaw: null,
      targetRewardRaw,
      targetSessionRaw,
    }),
  });
  TxModule.recoverPendingTransaction({ storage });
  assert.equal(storage.raw(REWARD_KEY), previousRewardRaw);
});

run("H: journal removed after incomplete rollback", () => {
  const previousRewardRaw = JSON.stringify({ youtube_minutes: 30 });
  const targetRewardRaw = JSON.stringify({ youtube_minutes: 15 });
  const targetSessionRaw = JSON.stringify(
    FreeTimeSession.start({ now: NOW, sessionId: "sess-001", source: "reward" })
  );
  const storage = new FakeStorage({
    [REWARD_KEY]: targetRewardRaw,
    [SESSION_KEY]: null,
    [JOURNAL_KEY]: JSON.stringify({
      version: 1,
      transactionId: "sess-001",
      previousRewardRaw,
      previousSessionRaw: null,
      targetRewardRaw,
      targetSessionRaw,
    }),
  });
  TxModule.recoverPendingTransaction({ storage });
  assert.equal(storage.raw(JOURNAL_KEY), null);
});

// ── I. commit 후 journal 제거 전 crash ────────────────────────

run("I: finalized committed transaction preserved on recovery", () => {
  const previousRewardRaw = JSON.stringify({ youtube_minutes: 30 });
  const targetRewardRaw = JSON.stringify({ youtube_minutes: 15 });
  const targetSessionRaw = JSON.stringify(
    FreeTimeSession.start({ now: NOW, sessionId: "sess-001", source: "reward" })
  );
  const storage = new FakeStorage({
    [REWARD_KEY]: targetRewardRaw,
    [SESSION_KEY]: targetSessionRaw,
    [JOURNAL_KEY]: JSON.stringify({
      version: 1,
      transactionId: "sess-001",
      previousRewardRaw,
      previousSessionRaw: null,
      targetRewardRaw,
      targetSessionRaw,
    }),
  });
  const result = TxModule.recoverPendingTransaction({ storage });
  assert.equal(result.code, "finalized_committed_transaction");
});

run("I: target reward preserved after finalized recovery", () => {
  const previousRewardRaw = JSON.stringify({ youtube_minutes: 30 });
  const targetRewardRaw = JSON.stringify({ youtube_minutes: 15 });
  const targetSessionRaw = JSON.stringify(
    FreeTimeSession.start({ now: NOW, sessionId: "sess-001", source: "reward" })
  );
  const storage = new FakeStorage({
    [REWARD_KEY]: targetRewardRaw,
    [SESSION_KEY]: targetSessionRaw,
    [JOURNAL_KEY]: JSON.stringify({
      version: 1,
      transactionId: "sess-001",
      previousRewardRaw,
      previousSessionRaw: null,
      targetRewardRaw,
      targetSessionRaw,
    }),
  });
  TxModule.recoverPendingTransaction({ storage });
  assert.equal(storage.raw(REWARD_KEY), targetRewardRaw);
});

run("I: target session preserved after finalized recovery", () => {
  const previousRewardRaw = JSON.stringify({ youtube_minutes: 30 });
  const targetRewardRaw = JSON.stringify({ youtube_minutes: 15 });
  const targetSessionRaw = JSON.stringify(
    FreeTimeSession.start({ now: NOW, sessionId: "sess-001", source: "reward" })
  );
  const storage = new FakeStorage({
    [REWARD_KEY]: targetRewardRaw,
    [SESSION_KEY]: targetSessionRaw,
    [JOURNAL_KEY]: JSON.stringify({
      version: 1,
      transactionId: "sess-001",
      previousRewardRaw,
      previousSessionRaw: null,
      targetRewardRaw,
      targetSessionRaw,
    }),
  });
  TxModule.recoverPendingTransaction({ storage });
  assert.equal(storage.raw(SESSION_KEY), targetSessionRaw);
});

run("I: journal removed after finalized recovery", () => {
  const previousRewardRaw = JSON.stringify({ youtube_minutes: 30 });
  const targetRewardRaw = JSON.stringify({ youtube_minutes: 15 });
  const targetSessionRaw = JSON.stringify(
    FreeTimeSession.start({ now: NOW, sessionId: "sess-001", source: "reward" })
  );
  const storage = new FakeStorage({
    [REWARD_KEY]: targetRewardRaw,
    [SESSION_KEY]: targetSessionRaw,
    [JOURNAL_KEY]: JSON.stringify({
      version: 1,
      transactionId: "sess-001",
      previousRewardRaw,
      previousSessionRaw: null,
      targetRewardRaw,
      targetSessionRaw,
    }),
  });
  TxModule.recoverPendingTransaction({ storage });
  assert.equal(storage.raw(JOURNAL_KEY), null);
});

// ── J. 손상 journal ──────────────────────────────────────────

run("J: unparseable journal returns corrupt_transaction_journal", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
    [JOURNAL_KEY]: "{not valid json",
  });
  const result = TxModule.recoverPendingTransaction({ storage });
  assert.equal(result.code, "corrupt_transaction_journal");
});

run("J: journal with missing fields returns corrupt_transaction_journal", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
    [JOURNAL_KEY]: JSON.stringify({ version: 1 }),
  });
  const result = TxModule.recoverPendingTransaction({ storage });
  assert.equal(result.code, "corrupt_transaction_journal");
});

run("J: corrupt journal does not delete the journal", () => {
  const journalRaw = "{broken";
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
    [JOURNAL_KEY]: journalRaw,
  });
  TxModule.recoverPendingTransaction({ storage });
  assert.equal(storage.raw(JOURNAL_KEY), journalRaw);
});

run("J: corrupt journal blocks attemptStart with fail-closed", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
    [JOURNAL_KEY]: "{broken",
  });
  const opener = new FakeOpener();
  const result = TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(result.code, "corrupt_transaction_journal");
});

run("J: corrupt journal blocks attemptStart — opener not called", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
    [JOURNAL_KEY]: "{broken",
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(opener.callCount, 0);
});

run("J: corrupt journal blocks attemptStart — no storage changes", () => {
  const rewardRaw = JSON.stringify({ youtube_minutes: 30 });
  const storage = new FakeStorage({
    [REWARD_KEY]: rewardRaw,
    [JOURNAL_KEY]: "{broken",
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(storage.raw(REWARD_KEY), rewardRaw);
  assert.equal(storage.raw(SESSION_KEY), null);
});

// ── K. 입력 무부작용성 ────────────────────────────────────────

run("K: reward object not mutated during success", () => {
  const rewardObj = { gems: 5, youtube_minutes: 30, snacks: 2 };
  const rewardRaw = JSON.stringify(rewardObj);
  const storage = new FakeStorage({ [REWARD_KEY]: rewardRaw });
  const opener = new FakeOpener();
  const before = JSON.stringify(rewardObj);
  TxModule.attemptStart(makeDeps(storage, opener));
  const after = JSON.stringify(rewardObj);
  assert.equal(before, after);
});

run("K: deps structural integrity preserved during attemptStart", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  const deps = makeDeps(storage, new FakeOpener());
  TxModule.attemptStart(deps);
  assert.equal(typeof deps.openExternal, "function");
  assert.equal(typeof deps.FreeTimeSession.start, "function");
  assert.equal(typeof deps.storage.getItem, "function");
  assert.equal(deps.now, NOW);
  assert.equal(deps.sessionId, "sess-001");
});

run("K: existing session object not mutated during already_active check", () => {
  const session = FreeTimeSession.start({ now: NOW, sessionId: "sess-existing", source: "reward" });
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
    [SESSION_KEY]: JSON.stringify(session),
  });
  const opener = new FakeOpener();
  const before = JSON.stringify(session);
  TxModule.attemptStart(makeDeps(storage, opener));
  const after = JSON.stringify(session);
  assert.equal(before, after);
});

// ── 추가: journal 저장 실패 시 아무것도 쓰지 않음 ─────────

run("journal write failure returns commit_failed", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 30 }),
  });
  storage.failSetItem(JOURNAL_KEY, 1);
  const opener = new FakeOpener();
  const result = TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(result.code, "commit_failed");
});

run("journal write failure does not modify reward or session", () => {
  const rewardRaw = JSON.stringify({ youtube_minutes: 30 });
  const storage = new FakeStorage({ [REWARD_KEY]: rewardRaw });
  storage.failSetItem(JOURNAL_KEY, 1);
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(storage.raw(REWARD_KEY), rewardRaw);
  assert.equal(storage.raw(SESSION_KEY), null);
});

// ── 추가: corrupt reward state ────────────────────────────────

run("corrupt reward JSON returns corrupt_reward_state", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: "{broken",
  });
  const opener = new FakeOpener();
  const result = TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(result.code, "corrupt_reward_state");
});

run("non-object reward returns corrupt_reward_state", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: JSON.stringify([1, 2, 3]),
  });
  const opener = new FakeOpener();
  const result = TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(result.code, "corrupt_reward_state");
});

run("corrupt reward does not call opener", () => {
  const storage = new FakeStorage({
    [REWARD_KEY]: "{broken",
  });
  const opener = new FakeOpener();
  TxModule.attemptStart(makeDeps(storage, opener));
  assert.equal(opener.callCount, 0);
});

// ── 추가: recover with no journal ─────────────────────────────

run("recover with no journal returns no_pending_transaction", () => {
  const storage = new FakeStorage({});
  const result = TxModule.recoverPendingTransaction({ storage });
  assert.equal(result.code, "no_pending_transaction");
});

// ── 결과 ─────────────────────────────────────────────────────

console.log(`\nResults: ${passed} passed, ${failed} failed`);

if (failed > 0) {
  process.exit(1);
}
