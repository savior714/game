/**
 * @fileoverview 손상된 자유시간 시작 journal의 previous raw 타입 경계 회귀 테스트
 *
 * 실행: node tests/test_free_time_session_corrupt_journal_raw_types.mjs
 */

import { strict as assert } from "node:assert";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const TxModule = require(resolve(
  __dirname,
  "..",
  "domains",
  "reward",
  "free-time-session-start-transaction.js",
));

const REWARD_KEY = "study_rewards";
const SESSION_KEY = "study_youtube_free_time_session_v1";
const JOURNAL_KEY = "study_youtube_free_time_start_tx_v1";

class RecordingStorage {
  constructor(initial) {
    this.store = new Map(Object.entries(initial));
    this.writes = [];
  }

  getItem(key) {
    return this.store.has(key) ? this.store.get(key) : null;
  }

  setItem(key, value) {
    this.writes.push({ op: "setItem", key, value });
    this.store.set(key, value);
  }

  removeItem(key) {
    this.writes.push({ op: "removeItem", key });
    this.store.delete(key);
  }
}

const validJournal = {
  version: 1,
  transactionId: "tx-corrupt-raw",
  previousRewardRaw: JSON.stringify({ youtube_minutes: 30 }),
  previousSessionRaw: null,
  targetRewardRaw: JSON.stringify({ youtube_minutes: 15 }),
  targetSessionRaw: JSON.stringify({ sessionId: "tx-corrupt-raw", status: "running" }),
};

for (const [field, invalidValue] of [
  ["previousRewardRaw", 42],
  ["previousSessionRaw", { unexpected: true }],
]) {
  const journal = { ...validJournal, [field]: invalidValue };
  const storage = new RecordingStorage({
    [REWARD_KEY]: JSON.stringify({ youtube_minutes: 99 }),
    [SESSION_KEY]: JSON.stringify({ sessionId: "unrelated", status: "expired" }),
    [JOURNAL_KEY]: JSON.stringify(journal),
  });

  const result = TxModule.recoverPendingTransaction({ storage });

  assert.equal(
    result.code,
    TxModule.RESULT.CORRUPT_TRANSACTION_JOURNAL,
    `${field} must reject non-string/non-null values`,
  );
  assert.deepEqual(storage.writes, [], `${field} corruption must not mutate storage`);
}

console.log("PASS: corrupt journal previous raw types are rejected without storage mutation");
