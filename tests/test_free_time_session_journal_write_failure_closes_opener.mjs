/**
 * Regression: journal write failure must close an already-opened external tab.
 *
 * Run: node tests/test_free_time_session_journal_write_failure_closes_opener.mjs
 */

import { strict as assert } from "node:assert";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

const FreeTimeSession = require(resolve(
  __dirname,
  "..",
  "shared",
  "domain",
  "free-time-session.js",
));
const StartTransaction = require(resolve(
  __dirname,
  "..",
  "domains",
  "reward",
  "free-time-session-start-transaction.js",
));

const REWARD_KEY = "study_rewards";
const SESSION_KEY = "study_youtube_free_time_session_v1";
const JOURNAL_KEY = "study_youtube_free_time_start_tx_v1";
const rewardRaw = JSON.stringify({ youtube_minutes: 30 });

class JournalWriteFailingStorage {
  constructor() {
    this.values = new Map([[REWARD_KEY, rewardRaw]]);
  }

  getItem(key) {
    return this.values.has(key) ? this.values.get(key) : null;
  }

  setItem(key, value) {
    if (key === JOURNAL_KEY) {
      throw new Error("injected journal write failure");
    }
    this.values.set(key, value);
  }

  removeItem(key) {
    this.values.delete(key);
  }
}

const storage = new JournalWriteFailingStorage();
let openCount = 0;
let closeCount = 0;

const result = StartTransaction.attemptStart({
  storage,
  openExternal() {
    openCount += 1;
    return {
      close() {
        closeCount += 1;
      },
    };
  },
  now: 1_000_000,
  sessionId: "journal-write-failure",
  FreeTimeSession,
});

assert.equal(result.code, StartTransaction.RESULT.COMMIT_FAILED);
assert.equal(openCount, 1);
assert.equal(closeCount, 1);
assert.equal(storage.getItem(REWARD_KEY), rewardRaw);
assert.equal(storage.getItem(SESSION_KEY), null);
assert.equal(storage.getItem(JOURNAL_KEY), null);

console.log("PASS: journal write failure closes opener and preserves storage");
