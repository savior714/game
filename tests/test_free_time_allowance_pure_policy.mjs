/**
 * @fileoverview 자유시간 일일 사용량 정책 순수 계약 테스트
 *
 * 실행: node tests/test_free_time_allowance_pure_policy.mjs
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
  "free-time-allowance.js",
);

let FreeTimeAllowance;

try {
  FreeTimeAllowance = require(MODULE_PATH);
} catch (e) {
  const code = readFileSync(MODULE_PATH, "utf-8");
  const moduleObj = { exports: {} };
  const fn = new Function("module", "exports", "self", code);
  fn(moduleObj, moduleObj.exports, globalThis);
  FreeTimeAllowance = moduleObj.exports;
}

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

console.log("FreeTimeAllowance pure policy contract tests\n");

// Local time helpers
// Construct local timestamp for a specific Y, M, D, H, m
function makeLocalTime(year, monthIndex, day, hour, minute = 0, second = 0) {
  return new Date(year, monthIndex, day, hour, minute, second, 0).getTime();
}

const MORNING_9AM = makeLocalTime(2026, 7, 16, 9, 0); // 2026-08-16 09:00 local
const AFTERNOON_2PM = makeLocalTime(2026, 7, 16, 14, 0); // 2026-08-16 14:00 local
const NEXT_DAY_9AM = makeLocalTime(2026, 7, 17, 9, 0); // 2026-08-17 09:00 local

// ── 1. Fresh morning: 10, 20, 30 allowed ──────────────────────────

run("1.1: fresh morning allows 10 min start", () => {
  const res = FreeTimeAllowance.evaluateStart({
    usage: null,
    now: MORNING_9AM,
    durationMinutes: 10,
  });
  assert.equal(res.allowed, true);
  assert.equal(res.period, "morning");
  assert.equal(res.nextUsage.morningMinutes, 10);
  assert.equal(res.nextUsage.afternoonMinutes, 0);
  assert.equal(res.nextUsage.dateKey, "2026-08-16");
});

run("1.2: fresh morning allows 20 min start", () => {
  const res = FreeTimeAllowance.evaluateStart({
    usage: null,
    now: MORNING_9AM,
    durationMinutes: 20,
  });
  assert.equal(res.allowed, true);
  assert.equal(res.nextUsage.morningMinutes, 20);
});

run("1.3: fresh morning allows 30 min start", () => {
  const res = FreeTimeAllowance.evaluateStart({
    usage: null,
    now: MORNING_9AM,
    durationMinutes: 30,
  });
  assert.equal(res.allowed, true);
  assert.equal(res.nextUsage.morningMinutes, 30);
});

// ── 2. Morning used 20: only 10 additional allowed ─────────────────

run("2.1: morning used 20 allows 10 min start", () => {
  const usage = {
    schemaVersion: 1,
    dateKey: "2026-08-16",
    morningMinutes: 20,
    afternoonMinutes: 0,
  };
  const res = FreeTimeAllowance.evaluateStart({
    usage: usage,
    now: MORNING_9AM,
    durationMinutes: 10,
  });
  assert.equal(res.allowed, true);
  assert.equal(res.nextUsage.morningMinutes, 30);
});

run("2.2: morning used 20 rejects 20 min start (exceeds 30 limit)", () => {
  const usage = {
    schemaVersion: 1,
    dateKey: "2026-08-16",
    morningMinutes: 20,
    afternoonMinutes: 0,
  };
  const res = FreeTimeAllowance.evaluateStart({
    usage: usage,
    now: MORNING_9AM,
    durationMinutes: 20,
  });
  assert.equal(res.allowed, false);
  assert.equal(res.reason, "exceeds_period_allowance");
});

run("2.3: morning used 20 rejects 30 min start", () => {
  const usage = {
    schemaVersion: 1,
    dateKey: "2026-08-16",
    morningMinutes: 20,
    afternoonMinutes: 0,
  };
  const res = FreeTimeAllowance.evaluateStart({
    usage: usage,
    now: MORNING_9AM,
    durationMinutes: 30,
  });
  assert.equal(res.allowed, false);
  assert.equal(res.reason, "exceeds_period_allowance");
});

// ── 3. Morning used 30: further start denied ───────────────────────

run("3.1: morning used 30 denies any further morning start", () => {
  const usage = {
    schemaVersion: 1,
    dateKey: "2026-08-16",
    morningMinutes: 30,
    afternoonMinutes: 0,
  };
  const res = FreeTimeAllowance.evaluateStart({
    usage: usage,
    now: MORNING_9AM,
    durationMinutes: 10,
  });
  assert.equal(res.allowed, false);
  assert.equal(res.reason, "exceeds_period_allowance");
});

// ── 4. Afternoon starts with independent 30 allowance ─────────────

run("4.1: afternoon starts with independent 30 allowance even if morning used 30", () => {
  const usage = {
    schemaVersion: 1,
    dateKey: "2026-08-16",
    morningMinutes: 30,
    afternoonMinutes: 0,
  };
  const res = FreeTimeAllowance.evaluateStart({
    usage: usage,
    now: AFTERNOON_2PM,
    durationMinutes: 30,
  });
  assert.equal(res.allowed, true);
  assert.equal(res.period, "afternoon");
  assert.equal(res.nextUsage.morningMinutes, 30);
  assert.equal(res.nextUsage.afternoonMinutes, 30);
});

// ── 5. Unused morning allowance does not increase afternoon > 30 ───

run("5.1: unused morning allowance (0 used) does not allow > 30 afternoon", () => {
  const usage = {
    schemaVersion: 1,
    dateKey: "2026-08-16",
    morningMinutes: 0,
    afternoonMinutes: 30,
  };
  const res = FreeTimeAllowance.evaluateStart({
    usage: usage,
    now: AFTERNOON_2PM,
    durationMinutes: 10,
  });
  assert.equal(res.allowed, false);
  assert.equal(res.reason, "exceeds_period_allowance");
});

// ── 6. Daily total cannot exceed 60 ───────────────────────────────

run("6.1: daily total cannot exceed 60 (30 morning + 30 afternoon reaches max)", () => {
  const usage = {
    schemaVersion: 1,
    dateKey: "2026-08-16",
    morningMinutes: 30,
    afternoonMinutes: 30,
  };
  const res = FreeTimeAllowance.evaluateStart({
    usage: usage,
    now: AFTERNOON_2PM,
    durationMinutes: 10,
  });
  assert.equal(res.allowed, false);
  assert.equal(res.reason, "exceeds_period_allowance");
});

// ── 7. Single session > 30 rejected ───────────────────────────────

run("7.1: single session > 30 rejected", () => {
  const res = FreeTimeAllowance.evaluateStart({
    usage: null,
    now: MORNING_9AM,
    durationMinutes: 40,
  });
  assert.equal(res.allowed, false);
  assert.equal(res.reason, "invalid_duration");
});

// ── 8. Invalid duration rejected ───────────────────────────────────

run("8.1: invalid duration (5 min) rejected", () => {
  const res = FreeTimeAllowance.evaluateStart({
    usage: null,
    now: MORNING_9AM,
    durationMinutes: 5,
  });
  assert.equal(res.allowed, false);
  assert.equal(res.reason, "invalid_duration");
});

run("8.2: invalid duration (15 min) rejected", () => {
  const res = FreeTimeAllowance.evaluateStart({
    usage: null,
    now: MORNING_9AM,
    durationMinutes: 15,
  });
  assert.equal(res.allowed, false);
  assert.equal(res.reason, "invalid_duration");
});

run("8.3: invalid duration (-10 min) rejected", () => {
  const res = FreeTimeAllowance.evaluateStart({
    usage: null,
    now: MORNING_9AM,
    durationMinutes: -10,
  });
  assert.equal(res.allowed, false);
  assert.equal(res.reason, "invalid_duration");
});

run("8.4: invalid duration (NaN / string) rejected", () => {
  const res = FreeTimeAllowance.evaluateStart({
    usage: null,
    now: MORNING_9AM,
    durationMinutes: "10",
  });
  assert.equal(res.allowed, false);
  assert.equal(res.reason, "invalid_duration");
});

// ── 9. Session cannot cross 12:00 boundary ────────────────────────

run("9.1: morning session starting at 11:45 with 30 min crosses noon (12:15 > 12:00) -> rejected", () => {
  const time1145 = makeLocalTime(2026, 7, 16, 11, 45);
  const res = FreeTimeAllowance.evaluateStart({
    usage: null,
    now: time1145,
    durationMinutes: 30,
  });
  assert.equal(res.allowed, false);
  assert.equal(res.reason, "crosses_boundary");
});

run("9.2: morning session starting at 11:45 with 20 min crosses noon (12:05 > 12:00) -> rejected", () => {
  const time1145 = makeLocalTime(2026, 7, 16, 11, 45);
  const res = FreeTimeAllowance.evaluateStart({
    usage: null,
    now: time1145,
    durationMinutes: 20,
  });
  assert.equal(res.allowed, false);
  assert.equal(res.reason, "crosses_boundary");
});

run("9.3: morning session starting at 11:45 with 10 min ends at 11:55 (<= 12:00) -> allowed", () => {
  const time1145 = makeLocalTime(2026, 7, 16, 11, 45);
  const res = FreeTimeAllowance.evaluateStart({
    usage: null,
    now: time1145,
    durationMinutes: 10,
  });
  assert.equal(res.allowed, true);
});

run("9.4: morning session starting at exactly 11:30 with 30 min ends at exactly 12:00 -> allowed", () => {
  const time1130 = makeLocalTime(2026, 7, 16, 11, 30);
  const res = FreeTimeAllowance.evaluateStart({
    usage: null,
    now: time1130,
    durationMinutes: 30,
  });
  assert.equal(res.allowed, true);
});

run("9.5: afternoon session starting at 23:45 with 30 min crosses midnight -> rejected", () => {
  const time2345 = makeLocalTime(2026, 7, 16, 23, 45);
  const res = FreeTimeAllowance.evaluateStart({
    usage: null,
    now: time2345,
    durationMinutes: 30,
  });
  assert.equal(res.allowed, false);
  assert.equal(res.reason, "crosses_boundary");
});

run("9.6: afternoon session starting at 23:45 with 10 min ends at 23:55 -> allowed", () => {
  const time2345 = makeLocalTime(2026, 7, 16, 23, 45);
  const res = FreeTimeAllowance.evaluateStart({
    usage: null,
    now: time2345,
    durationMinutes: 10,
  });
  assert.equal(res.allowed, true);
});

// ── 10. Next local date sees fresh quota ──────────────────────────

run("10.1: next local date resets quota to 0/0 and allows 30 min", () => {
  const yesterdayUsage = {
    schemaVersion: 1,
    dateKey: "2026-08-16",
    morningMinutes: 30,
    afternoonMinutes: 30,
  };
  const res = FreeTimeAllowance.evaluateStart({
    usage: yesterdayUsage,
    now: NEXT_DAY_9AM,
    durationMinutes: 30,
  });
  assert.equal(res.allowed, true);
  assert.equal(res.nextUsage.dateKey, "2026-08-17");
  assert.equal(res.nextUsage.morningMinutes, 30);
  assert.equal(res.nextUsage.afternoonMinutes, 0);
});

// ── 11. restoreUsage helper ───────────────────────────────────────

run("11.1: restoreUsage returns fresh usage on corrupt / outdated data", () => {
  const restored1 = FreeTimeAllowance.restoreUsage({ savedUsage: null, now: MORNING_9AM });
  assert.equal(restored1.dateKey, "2026-08-16");
  assert.equal(restored1.morningMinutes, 0);
  assert.equal(restored1.afternoonMinutes, 0);

  const restored2 = FreeTimeAllowance.restoreUsage({
    savedUsage: { schemaVersion: 1, dateKey: "2026-08-15", morningMinutes: 30, afternoonMinutes: 30 },
    now: MORNING_9AM,
  });
  assert.equal(restored2.dateKey, "2026-08-16");
  assert.equal(restored2.morningMinutes, 0);
  assert.equal(restored2.afternoonMinutes, 0);
});

// ── 12. getRemainingQuota helper ───────────────────────────────────

run("12.1: getRemainingQuota computes accurate numbers", () => {
  const usage = {
    schemaVersion: 1,
    dateKey: "2026-08-16",
    morningMinutes: 10,
    afternoonMinutes: 0,
  };
  const q = FreeTimeAllowance.getRemainingQuota({ usage: usage, now: MORNING_9AM });
  assert.equal(q.morningMinutes, 10);
  assert.equal(q.morningRemaining, 20);
  assert.equal(q.afternoonRemaining, 30);
  assert.equal(q.periodRemaining, 20);
  assert.equal(q.dailyRemaining, 50);
});

console.log(`\nResults: ${passed} passed, ${failed} failed`);

if (failed > 0) {
  process.exit(1);
}
