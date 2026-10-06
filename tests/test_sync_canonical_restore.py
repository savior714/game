from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNC_ENGINE = ROOT / "domains" / "sync" / "sync-engine.js"

HARNESS = r"""
const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync(process.argv[2], 'utf8');

class Storage {
  constructor() { this.map = new Map(); }
  getItem(key) { return this.map.has(key) ? this.map.get(key) : null; }
  setItem(key, value) { this.map.set(key, String(value)); }
  removeItem(key) { this.map.delete(key); }
}

class Event {
  constructor(type) { this.type = type; }
}
class CustomEvent extends Event {
  constructor(type, init = {}) {
    super(type);
    this.detail = init.detail;
  }
}

function createRuntime(initialRows) {
  const listeners = {};
  const localStorage = new Storage();
  const pushes = [];
  const inCalls = [];
  let rows = initialRows;

  const window = {
    Auth: { getUser() { return { id: 'user-1', email: 'test@example.com' }; } },
    WeeklyVocabularyStore: null,
    addEventListener(type, listener) {
      if (!listeners[type]) listeners[type] = [];
      listeners[type].push(listener);
    },
    dispatchEvent(event) {
      for (const listener of listeners[event.type] || []) listener(event);
      return true;
    },
  };

  function queryBuilder() {
    return {
      select() { return this; },
      eq() { return this; },
      in(_field, keys) {
        inCalls.push([...keys]);
        return Promise.resolve({ data: rows, error: null });
      },
      upsert(payload) {
        pushes.push(JSON.parse(JSON.stringify(payload)));
        return Promise.resolve({ error: null });
      },
    };
  }

  window.supabaseClient = {
    from(table) {
      if (table !== 'user_data') throw new Error('unexpected table: ' + table);
      return queryBuilder();
    },
  };

  const context = vm.createContext({
    window,
    localStorage,
    navigator: { onLine: true },
    Event,
    CustomEvent,
    console,
    setTimeout,
    clearTimeout,
    Map,
    Set,
    Object,
    JSON,
    Date,
  });
  vm.runInContext(source, context);

  return {
    window,
    localStorage,
    pushes,
    inCalls,
    setRows(nextRows) { rows = nextRows; },
  };
}

function statsPayload(marker, updatedAt) {
  return {
    '+': {
      levels: {
        '0': { attempts: marker, correct: marker, totalTime: marker * 10 },
      },
      weaknesses: {},
    },
    _updated_at: updatedAt,
  };
}

(async () => {
  // 1. Auth bootstrap must pull the current canonical keys, while still querying
  // legacy keys as one-time migration inputs.
  const bootstrap = createRuntime([]);
  bootstrap.window.dispatchEvent(new CustomEvent('auth-changed', {
    detail: { user: { id: 'user-1' } },
  }));
  await new Promise((resolve) => setTimeout(resolve, 0));
  const defaultKeys = bootstrap.inCalls.at(-1) || [];

  // 2. Canonical cloud row restores directly into the canonical localStorage key.
  const canonicalPayload = statsPayload(2, 200);
  const canonical = createRuntime([{
    data_key: 'aiden_math_stats',
    payload: canonicalPayload,
    updated_at: '2026-10-06T00:00:00.000Z',
  }]);
  await canonical.window.SyncEngine.pullAndMerge(['aiden_math_stats']);
  const canonicalStored = JSON.parse(canonical.localStorage.getItem('aiden_math_stats'));

  // 3. A legacy-only row is hydrated into the canonical key and queued/upserted
  // under the canonical key. The legacy localStorage key must never be revived.
  const legacyPayload = statsPayload(3, 300);
  const legacy = createRuntime([{
    data_key: 'mathGameStats',
    payload: legacyPayload,
    updated_at: '2026-10-06T00:00:00.000Z',
  }]);
  await legacy.window.SyncEngine.pullAndMerge(['aiden_math_stats', 'mathGameStats']);
  await new Promise((resolve) => setTimeout(resolve, 0));
  const legacyStored = JSON.parse(legacy.localStorage.getItem('aiden_math_stats'));

  // 4. If both rows exist, canonical wins even when the legacy payload looks newer.
  const canonicalWinner = statsPayload(5, 500);
  const staleLegacy = statsPayload(9, 900);
  const both = createRuntime([
    {
      data_key: 'mathGameStats',
      payload: staleLegacy,
      updated_at: '2026-10-06T00:00:00.000Z',
    },
    {
      data_key: 'aiden_math_stats',
      payload: canonicalWinner,
      updated_at: '2026-10-06T00:00:00.000Z',
    },
  ]);
  await both.window.SyncEngine.pullAndMerge(['aiden_math_stats', 'mathGameStats']);
  await new Promise((resolve) => setTimeout(resolve, 0));
  const winnerStored = JSON.parse(both.localStorage.getItem('aiden_math_stats'));

  console.log(JSON.stringify({
    defaultKeys,
    canonicalStored,
    canonicalPushes: canonical.pushes,
    legacyStored,
    legacyLocalRevived: legacy.localStorage.getItem('mathGameStats'),
    legacyPushes: legacy.pushes,
    winnerStored,
    winnerPushes: both.pushes,
  }));
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
"""


def _node() -> str:
    node = shutil.which("node")
    assert node, "node is required"
    return node


def _run_harness(tmp_path: Path) -> dict:
    harness = tmp_path / "sync-canonical-restore-harness.js"
    harness.write_text(HARNESS, encoding="utf-8")
    proc = subprocess.run(
        [_node(), str(harness), str(SYNC_ENGINE)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout.strip())


def test_auth_bootstrap_pulls_current_canonical_and_legacy_fallback_keys(
    tmp_path: Path,
) -> None:
    result = _run_harness(tmp_path)
    keys = set(result["defaultKeys"])

    assert {
        "study_rewards",
        "aiden_math_stats",
        "aiden_english_stats",
        "aiden_korean_stats",
        "aiden_science_stats",
        "aiden_canonical_weekly_vocabulary_v1",
    } <= keys
    assert {
        "mathGameStats",
        "englishGameStats",
        "koreanGameStats",
        "scienceGameStats",
    } <= keys


def test_canonical_subject_stats_restore_without_rewriting_cloud(
    tmp_path: Path,
) -> None:
    result = _run_harness(tmp_path)

    assert result["canonicalStored"]["+"]["levels"]["0"]["attempts"] == 2
    assert result["canonicalStored"]["_updated_at"] == 200
    assert result["canonicalPushes"] == []


def test_legacy_subject_stats_migrate_once_into_canonical_key(tmp_path: Path) -> None:
    result = _run_harness(tmp_path)

    assert result["legacyStored"]["+"]["levels"]["0"]["attempts"] == 3
    assert result["legacyStored"]["_updated_at"] == 300
    assert result["legacyLocalRevived"] is None
    assert [row["data_key"] for row in result["legacyPushes"]] == ["aiden_math_stats"]


def test_existing_canonical_cloud_row_wins_over_legacy_fallback(tmp_path: Path) -> None:
    result = _run_harness(tmp_path)

    assert result["winnerStored"]["+"]["levels"]["0"]["attempts"] == 5
    assert result["winnerStored"]["_updated_at"] == 500
    assert result["winnerPushes"] == []
