/**
 * @fileoverview 자유시간 세션 순수 상태 계약 — focused runtime test
 *
 * JavaScript 함수를 실제로 호출하여 반환 상태를 검증한다.
 * 브라우저 API나 저장소에 의존하지 않는다.
 *
 * 실행: node tests/test_free_time_session_pure_state.mjs
 */

import { strict as assert } from "node:assert";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { createRequire } from "node:module";

const __dirname = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

const MODULE_PATH = resolve(
  __dirname,
  "..",
  "shared",
  "domain",
  "free-time-session.js",
);

let FreeTimeSession;

try {
  // ESM .js with module.exports — load via createRequire
  FreeTimeSession = require(MODULE_PATH);
} catch (e) {
  // Fallback: read file and eval in CJS context
  const code = readFileSync(MODULE_PATH, "utf-8");
  const moduleObj = { exports: {} };
  const fn = new Function("module", "exports", "self", code);
  fn(moduleObj, moduleObj.exports, globalThis);
  FreeTimeSession = moduleObj.exports;
}

const NOW = 1000000;

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

console.log("FreeTimeSession pure state contract tests\n");

// ── 사례 A — 정확한 10분 시작 ───────────────────────────────

run("A: startedAt equals injected now", () => {
  const session = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  assert.equal(session.startedAt, NOW);
});

run("A: endsAt is startedAt + 600000", () => {
  const session = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  assert.equal(session.endsAt, 1600000);
});

run("A: chargedMinutes is 10", () => {
  const session = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  assert.equal(session.chargedMinutes, 10);
});

run("A: status is running", () => {
  const session = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  assert.equal(session.status, "running");
});

run("A: sessionId and source preserved", () => {
  const session = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-abc",
    source: "reward",
  });
  assert.equal(session.sessionId, "sess-abc");
  assert.equal(session.source, "reward");
});

run("A: schemaVersion is 1", () => {
  const session = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  assert.equal(session.schemaVersion, 1);
});

// ── 사례 B — 활성 세션 중복 시작 차단 ─────────────────────────

run("B: second start is rejected when session active", () => {
  const first = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  const result = FreeTimeSession.startIfInactive({
    currentSession: first,
    now: NOW + 1000,
    sessionId: "sess-002",
    source: "reward",
  });
  assert.equal(result.started, false);
});

run("B: original sessionId preserved on duplicate", () => {
  const first = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  const result = FreeTimeSession.startIfInactive({
    currentSession: first,
    now: NOW + 1000,
    sessionId: "sess-002",
    source: "reward",
  });
  assert.equal(result.session.sessionId, "sess-001");
});

run("B: original startedAt preserved on duplicate", () => {
  const first = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  const result = FreeTimeSession.startIfInactive({
    currentSession: first,
    now: NOW + 1000,
    sessionId: "sess-002",
    source: "reward",
  });
  assert.equal(result.session.startedAt, NOW);
});

run("B: original endsAt preserved on duplicate", () => {
  const first = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  const result = FreeTimeSession.startIfInactive({
    currentSession: first,
    now: NOW + 1000,
    sessionId: "sess-002",
    source: "reward",
  });
  assert.equal(result.session.endsAt, 1600000);
});

run("B: no 10min extension on duplicate", () => {
  const first = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  const result = FreeTimeSession.startIfInactive({
    currentSession: first,
    now: NOW + 1000,
    sessionId: "sess-002",
    source: "reward",
  });
  assert.ok(result.session.endsAt <= 1600000);
  assert.ok(result.session.endsAt === 1600000);
});

// ── 사례 C — 마감 전 복원 ───────────────────────────────────

run("C: restore before deadline keeps active status", () => {
  const original = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  const restored = FreeTimeSession.restore({
    savedSession: original,
    now: 1599999,
  });
  assert.equal(restored.status, "running");
});

run("C: restore before deadline preserves sessionId", () => {
  const original = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  const restored = FreeTimeSession.restore({
    savedSession: original,
    now: 1599999,
  });
  assert.equal(restored.sessionId, "sess-001");
});

run("C: restore before deadline preserves startedAt", () => {
  const original = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  const restored = FreeTimeSession.restore({
    savedSession: original,
    now: 1599999,
  });
  assert.equal(restored.startedAt, NOW);
});

run("C: restore before deadline preserves endsAt exactly", () => {
  const original = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  const restored = FreeTimeSession.restore({
    savedSession: original,
    now: 1599999,
  });
  assert.equal(restored.endsAt, 1600000);
});

run("C: restore before deadline — remaining time is 1ms", () => {
  const original = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  const restored = FreeTimeSession.restore({
    savedSession: original,
    now: 1599999,
  });
  const sel = FreeTimeSession.select(restored, 1599999);
  assert.equal(sel.remainingMs, 1);
});

// ── 사례 D — 마감 시각 복원 ─────────────────────────────────

run("D: restore at exactly endsAt is expired", () => {
  const original = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  const restored = FreeTimeSession.restore({
    savedSession: original,
    now: 1600000,
  });
  assert.equal(restored.status, "expired");
});

run("D: restore at exactly endsAt is not active", () => {
  const original = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  const restored = FreeTimeSession.restore({
    savedSession: original,
    now: 1600000,
  });
  const sel = FreeTimeSession.select(restored, 1600000);
  assert.equal(sel.active, false);
});

run("D: restore at exactly endsAt — remaining time is 0", () => {
  const original = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  const restored = FreeTimeSession.restore({
    savedSession: original,
    now: 1600000,
  });
  const sel = FreeTimeSession.select(restored, 1600000);
  assert.equal(sel.remainingMs, 0);
});

// ── 사례 E — 마감 이후 복원 ─────────────────────────────────

run("E: restore after deadline is expired", () => {
  const original = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  const restored = FreeTimeSession.restore({
    savedSession: original,
    now: 2000000,
  });
  assert.equal(restored.status, "expired");
});

run("E: restore after deadline — remaining time is 0", () => {
  const original = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  const restored = FreeTimeSession.restore({
    savedSession: original,
    now: 2000000,
  });
  const sel = FreeTimeSession.select(restored, 2000000);
  assert.equal(sel.remainingMs, 0);
});

run("E: restore after deadline does not recalculate endsAt", () => {
  const original = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  const restored = FreeTimeSession.restore({
    savedSession: original,
    now: 2000000,
  });
  assert.equal(restored.endsAt, 1600000);
});

// ── 사례 F — Selector 무부작용성 ─────────────────────────────

run("F: repeated select returns same result", () => {
  const session = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  const sel1 = FreeTimeSession.select(session, NOW + 5000);
  const sel2 = FreeTimeSession.select(session, NOW + 5000);
  assert.deepEqual(sel1, sel2);
});

run("F: select does not mutate input state", () => {
  const session = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  const before = JSON.stringify(session);
  FreeTimeSession.select(session, NOW + 5000);
  FreeTimeSession.select(session, NOW + 5000);
  FreeTimeSession.select(session, NOW + 5000);
  const after = JSON.stringify(session);
  assert.equal(before, after);
});

run("F: select does not change startedAt, endsAt, status", () => {
  const session = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  FreeTimeSession.select(session, NOW + 100000);
  assert.equal(session.startedAt, NOW);
  assert.equal(session.endsAt, 1600000);
  assert.equal(session.status, "running");
});

// ── 사례 G — 남은 시간 절대 마감 계산 ───────────────────────

run("G: remainingMs equals endsAt - now before deadline", () => {
  const session = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  const sel = FreeTimeSession.select(session, 1400000);
  assert.equal(sel.remainingMs, 200000);
});

run("G: remainingMs is 0 at or after deadline", () => {
  const session = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  const sel1 = FreeTimeSession.select(session, 1600000);
  const sel2 = FreeTimeSession.select(session, 2500000);
  assert.equal(sel1.remainingMs, 0);
  assert.equal(sel2.remainingMs, 0);
});

run("G: no internal mutable counter needed", () => {
  const session = FreeTimeSession.start({
    now: NOW,
    sessionId: "sess-001",
    source: "reward",
  });
  const sel1 = FreeTimeSession.select(session, NOW + 1000);
  const sel2 = FreeTimeSession.select(session, NOW + 2000);
  const sel3 = FreeTimeSession.select(session, NOW + 3000);
  assert.equal(sel1.remainingMs, 599000);
  assert.equal(sel2.remainingMs, 598000);
  assert.equal(sel3.remainingMs, 597000);
});

// ── 추가: 세션 없음 복원 ─────────────────────────────────────

run("restore with no session returns inactive", () => {
  const restored = FreeTimeSession.restore({
    savedSession: null,
    now: NOW,
  });
  assert.equal(restored.status, "inactive");
  assert.equal(restored.sessionId, null);
});

run("select on inactive session returns inactive", () => {
  const restored = FreeTimeSession.restore({
    savedSession: null,
    now: NOW,
  });
  const sel = FreeTimeSession.select(restored, NOW);
  assert.equal(sel.active, false);
  assert.equal(sel.expired, false);
  assert.equal(sel.remainingMs, 0);
  assert.equal(sel.status, "inactive");
});

// ── 추가: 상수 계약 ───────────────────────────────────────────

run("DURATION_MS is 600000", () => {
  assert.equal(FreeTimeSession.DURATION_MS, 600000);
});

run("CHARGED_MINUTES is 10", () => {
  assert.equal(FreeTimeSession.CHARGED_MINUTES, 10);
});

run("SCHEMA_VERSION is 1", () => {
  assert.equal(FreeTimeSession.SCHEMA_VERSION, 1);
});

// ── 추가: 시작 시 입력 객체 변경 없음 ─────────────────────────

run("start does not mutate input", () => {
  const input = { now: NOW, sessionId: "sess-001", source: "reward" };
  const before = JSON.stringify(input);
  FreeTimeSession.start(input);
  const after = JSON.stringify(input);
  assert.equal(before, after);
});

// ── 사례 H — Acknowledged 세션 복원 및 Select ─────────────────────

run("H: acknowledged restore preserves acknowledged status when endsAt <= now", () => {
  const original = {
    schemaVersion: 1,
    sessionId: "ack-session-001",
    status: "acknowledged",
    startedAt: NOW - 1000000,
    endsAt: NOW - 100000,
    durationMs: 600000,
    chargedMinutes: 10,
    source: "reward",
    warningEmittedAt: null,
    expiredAt: NOW - 100000,
    acknowledgedAt: NOW - 50000,
  };
  const restored = FreeTimeSession.restore({
    savedSession: original,
    now: NOW,
  });
  assert.equal(restored.status, "acknowledged");
});

run("H: acknowledged restore preserves identity and timestamps", () => {
  const original = {
    schemaVersion: 1,
    sessionId: "ack-session-001",
    status: "acknowledged",
    startedAt: NOW - 1000000,
    endsAt: NOW - 100000,
    durationMs: 600000,
    chargedMinutes: 10,
    source: "reward",
    warningEmittedAt: null,
    expiredAt: NOW - 100000,
    acknowledgedAt: NOW - 50000,
  };
  const restored = FreeTimeSession.restore({
    savedSession: original,
    now: NOW,
  });
  assert.equal(restored.sessionId, original.sessionId);
  assert.equal(restored.startedAt, original.startedAt);
  assert.equal(restored.endsAt, original.endsAt);
  assert.equal(restored.expiredAt, original.expiredAt);
  assert.equal(restored.acknowledgedAt, original.acknowledgedAt);
});

run("H: select on acknowledged returns active=false, expired=false, remainingMs=0", () => {
  const original = {
    schemaVersion: 1,
    sessionId: "ack-session-001",
    status: "acknowledged",
    startedAt: NOW - 1000000,
    endsAt: NOW - 100000,
    durationMs: 600000,
    chargedMinutes: 10,
    source: "reward",
    warningEmittedAt: null,
    expiredAt: NOW - 100000,
    acknowledgedAt: NOW - 50000,
  };
  const restored = FreeTimeSession.restore({
    savedSession: original,
    now: NOW,
  });
  const sel = FreeTimeSession.select(restored, NOW);
  assert.equal(sel.active, false);
  assert.equal(sel.expired, false);
  assert.equal(sel.remainingMs, 0);
  assert.equal(sel.status, "acknowledged");
});

// ── 결과 ─────────────────────────────────────────────────────

console.log(`\nResults: ${passed} passed, ${failed} failed`);

if (failed > 0) {
  process.exit(1);
}
