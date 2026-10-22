"""보상 획득/사용 신뢰도 — 런타임 통합 계약 검증.

재현하던 결함:
- 상단 HUD 보상을 모두 사용해 0으로 만든 뒤, 오래된 탭/클라우드 스냅샷이 다시 병합되며
  사용한 보상이 되살아났다(값 기반 `Math.max` 병합 + 저장 시 메모리 스냅샷 덮어쓰기).

고정하는 계약:
1. 소비 후에는 어떤 경로로도(클라우드 pull, 다른 탭, 재로드) 보상이 저절로 채워지지 않는다.
2. 실제 획득 이벤트가 있을 때만 그만큼 증가한다.
3. 같은 영수증(receipt)은 몇 번을 지급 시도해도 한 번만 지급된다.
4. 자유시간(YouTube) 시작 차감도 원장에 사용 이벤트로 남고, 되살아나지 않는다.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HARNESS = r"""
const fs = require('fs');
const vm = require('vm');

const ledgerSrc = fs.readFileSync(process.argv[2], 'utf8');
const rewardSrc = fs.readFileSync(process.argv[3], 'utf8');
const syncSrc = fs.readFileSync(process.argv[4], 'utf8');
const allowanceSrc = fs.readFileSync(process.argv[5], 'utf8');
const sessionSrc = fs.readFileSync(process.argv[6], 'utf8');
const launcherSrc = fs.readFileSync(process.argv[7], 'utf8');
const txSrc = fs.readFileSync(process.argv[8], 'utf8');

function createSharedStore(initial) {
  const map = new Map();
  if (initial) map.set('study_rewards', JSON.stringify(initial));
  return map;
}

function makeTab(store) {
  const listeners = {};
  const openedTabs = [];

  const window = {
    addEventListener(type, listener) {
      (listeners[type] = listeners[type] || []).push(listener);
    },
    dispatchEvent(event) {
      (listeners[event.type] || []).forEach((listener) => listener(event));
      return true;
    },
    open() {
      const handle = { opener: undefined, location: { href: '' }, close() {} };
      openedTabs.push(handle);
      return handle;
    },
    location: { href: 'https://example.test/index.html', reload() {} },
  };
  window.self = window;
  window.window = window;

  const document = {
    readyState: 'complete',
    addEventListener() {},
    getElementById() { return null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    createElement() { return { style: {}, classList: { add() {}, remove() {} }, appendChild() {} }; },
    body: { appendChild() {} },
  };

  const localStorage = {
    getItem(key) { return store.has(key) ? store.get(key) : null; },
    setItem(key, value) { store.set(key, String(value)); },
    removeItem(key) { store.delete(key); },
  };

  const context = vm.createContext({
    window,
    document,
    localStorage,
    self: window,
    navigator: { onLine: true },
    console,
    alert() {},
    Date,
    Math,
    Number,
    JSON,
    Object,
    Array,
    Set,
    Map,
    String,
    setTimeout,
    clearTimeout,
  });

  const scripts = [
    [ledgerSrc, 'RewardLedger'],
    [allowanceSrc, 'FreeTimeAllowance'],
    [sessionSrc, 'FreeTimeSession'],
    [launcherSrc, 'ExternalTabLauncher'],
    [txSrc, 'FreeTimeSessionStartTransaction'],
  ];
  for (const [source, globalName] of scripts) {
    vm.runInContext(source, context);
    vm.runInContext(
      `if (typeof ${globalName} === 'undefined' && window.${globalName}) { globalThis.${globalName} = window.${globalName}; }`,
      context
    );
  }

  vm.runInContext(rewardSrc + '\n;globalThis.__RS = RewardSystem;', context);

  return {
    window,
    document,
    localStorage,
    context,
    rs: context.__RS,
    dispatch(type, detail) {
      window.dispatchEvent({ type, detail });
    },
    readRewards() {
      const raw = localStorage.getItem('study_rewards');
      return raw ? JSON.parse(raw) : null;
    },
  };
}

function fieldSummary(state) {
  return {
    gems: state.gems,
    youtube_minutes: state.youtube_minutes,
    snacks: state.snacks,
    marble_plays: state.marble_plays,
    bubble_plays: state.bubble_plays,
  };
}

(async () => {
  const report = {};

  // ── A. 모두 사용한 뒤 오래된 클라우드/탭 스냅샷이 되살리지 못한다 ──
  const storeA = createSharedStore({
    gems: 7,
    youtube_minutes: 30,
    snacks: 3,
    marble_plays: 2,
    bubble_plays: 1,
    _updated_at: 1000,
  });
  const tabOld = makeTab(storeA); // 소비 이전에 열려 있던 오래된 탭
  const tabMain = makeTab(storeA);
  report.beforeConsume = fieldSummary(tabMain.rs.getState());

  tabMain.rs.consumeInternal('snack', null, 3);
  tabMain.rs.consumeInternal('youtube', null, 3);
  tabMain.rs.consumeInternal('marble', null, 2);
  tabMain.rs.consumeInternal('bubble', null, 1);
  for (let i = 0; i < 7; i += 1) tabMain.rs.exchangeGem('snack');
  tabMain.rs.consumeInternal('snack', null, 7);
  report.afterConsume = fieldSummary(tabMain.rs.getState());
  report.verifyAfterConsume = tabMain.rs.verifyIntegrity();
  report.ledgerEvents = tabMain.readRewards().reward_ledger.events.length;

  // 오래된 탭이 (메모리의 옛 잔액을 들고) 보석 1개를 획득했다고 저장을 시도한다.
  tabOld.rs.add('gems', 1);
  report.afterStaleTabWrite = fieldSummary(tabMain.rs.getState());
  const storedAfterStaleTab = tabMain.readRewards();
  report.storedAfterStaleTab = fieldSummary(storedAfterStaleTab);

  // 클라우드 pull: 서버에는 소비 이전의 큰 값이 남아 있다.
  const staleCloudPayload = {
    gems: 7,
    youtube_minutes: 30,
    snacks: 3,
    marble_plays: 2,
    bubble_plays: 1,
    _updated_at: 999999,
  };
  tabMain.window.Auth = { getUser() { return { id: 'user-1' }; } };
  tabMain.window.supabaseClient = {
    from() {
      return {
        select() { return this; },
        eq() { return this; },
        in() {
          return Promise.resolve({
            data: [{
              data_key: 'study_rewards',
              payload: staleCloudPayload,
              updated_at: '2026-10-22T00:00:00.000Z',
            }],
            error: null,
          });
        },
        upsert() { return Promise.resolve({ error: null }); },
      };
    },
  };
  vm.runInContext(syncSrc, tabMain.context);
  report.syncEngineLoaded = Boolean(tabMain.window.SyncEngine);
  if (tabMain.window.SyncEngine) {
    await tabMain.window.SyncEngine.pullAndMerge(['study_rewards']);
  }
  report.afterCloudPull = fieldSummary(tabMain.readRewards());

  // 재로드해도 그대로여야 한다.
  const tabReloaded = makeTab(storeA);
  report.afterReload = fieldSummary(tabReloaded.rs.getState());

  // ── A-2. 구버전 페이지가 원장 없이 스냅샷을 통째로 덮어써도 복구 저널이 지킨다 ──
  const overwriteStore = createSharedStore({
    gems: 7,
    youtube_minutes: 30,
    snacks: 3,
    _updated_at: 1000,
  });
  const overwriteTab = makeTab(overwriteStore);
  overwriteTab.rs.consumeInternal('snack', null, 3);
  overwriteTab.rs.consumeInternal('youtube', null, 3);
  for (let i = 0; i < 7; i += 1) overwriteTab.rs.exchangeGem('snack');
  overwriteTab.rs.consumeInternal('snack', null, 7);
  report.overwriteEmptied = fieldSummary(overwriteTab.rs.getState());

  // 원장을 모르는 구버전 코드가 예전 스냅샷을 그대로 저장한다고 가정.
  overwriteStore.set('study_rewards', JSON.stringify({
    gems: 7,
    youtube_minutes: 30,
    snacks: 3,
    marble_plays: 0,
    bubble_plays: 0,
    _updated_at: 888888,
  }));
  const recoveredTab = makeTab(overwriteStore);
  report.afterLegacyOverwrite = fieldSummary(recoveredTab.rs.getState());
  report.journalPreserved = Boolean(overwriteStore.get('study_rewards_ledger_v1'));

  // ── B. 영수증 지급은 두 탭에서 동시에 시도해도 한 번만 반영된다 ──
  const receiptStore = createSharedStore({ gems: 0, _updated_at: 1000 });
  const tabReceiptA = makeTab(receiptStore);
  const tabReceiptB = makeTab(receiptStore);
  report.receiptFirst = tabReceiptA.rs.grantOnce('reward.diversity.2026-10-22', 'gems', 2);
  report.receiptSecond = tabReceiptB.rs.grantOnce('reward.diversity.2026-10-22', 'gems', 2);
  report.receiptGems = tabReceiptA.readRewards().gems;

  // ── C. 자유시간 시작 차감도 원장 사용 이벤트로 남는다 ──
  const freeTimeStore = createSharedStore({ gems: 0, youtube_minutes: 30, _updated_at: 1000 });
  const tabFree = makeTab(freeTimeStore);
  const startResult = tabFree.rs.startYouTubeSession(10);
  report.freeTimeStartCode = startResult.code;
  report.freeTimeAfterStart = JSON.parse(tabFree.localStorage.getItem('study_rewards')).youtube_minutes;
  const freeTimeEvents = JSON.parse(tabFree.localStorage.getItem('study_rewards')).reward_ledger.events;
  report.freeTimeConsumeEvent = freeTimeEvents.some(
    (event) => event.reason === 'free_time_session' && event.key === 'youtube_minutes' && event.delta === -10
  );

  // 같은 클라우드 스냅샷이 다시 들어와도 차감은 유지된다.
  tabFree.window.Auth = { getUser() { return { id: 'user-1' }; } };
  tabFree.window.supabaseClient = tabMain.window.supabaseClient;
  vm.runInContext(syncSrc, tabFree.context);
  if (tabFree.window.SyncEngine) {
    await tabFree.window.SyncEngine.pullAndMerge(['study_rewards']);
  }
  report.freeTimeAfterPull = JSON.parse(tabFree.localStorage.getItem('study_rewards')).youtube_minutes;

  console.log(JSON.stringify(report));
})().catch((err) => {
  console.error(err && err.stack ? err.stack : err);
  process.exit(1);
});
"""


def _node() -> str:
    node = shutil.which("node")
    assert node, "node is required"
    return node


def _run_harness(tmp_path: Path) -> dict:
    harness = tmp_path / "reward-ledger-integration-harness.js"
    harness.write_text(HARNESS, encoding="utf-8")
    proc = subprocess.run(
        [
            _node(),
            str(harness),
            str(ROOT / "shared" / "domain" / "reward-ledger.js"),
            str(ROOT / "domains" / "reward" / "reward.js"),
            str(ROOT / "domains" / "sync" / "sync-engine.js"),
            str(ROOT / "shared" / "domain" / "free-time-allowance.js"),
            str(ROOT / "shared" / "domain" / "free-time-session.js"),
            str(ROOT / "shared" / "domain" / "external-tab-launcher.js"),
            str(ROOT / "domains" / "reward" / "free-time-session-start-transaction.js"),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, f"{proc.stderr}\n{proc.stdout}"
    return json.loads(proc.stdout.strip())


def test_consumed_rewards_never_refill_from_cloud_or_stale_tab(tmp_path: Path) -> None:
    result = _run_harness(tmp_path)

    assert result["beforeConsume"] == {
        "gems": 7,
        "youtube_minutes": 30,
        "snacks": 3,
        "marble_plays": 2,
        "bubble_plays": 1,
    }
    assert result["afterConsume"] == {
        "gems": 0,
        "youtube_minutes": 0,
        "snacks": 0,
        "marble_plays": 0,
        "bubble_plays": 0,
    }, "모든 보상을 사용한 뒤 잔액이 0이어야 한다."
    assert result["verifyAfterConsume"]["ok"] is True
    assert result["ledgerEvents"] > 0, "획득/사용 이벤트가 원장에 남아야 한다."

    assert result["storedAfterStaleTab"] == {
        "gems": 1,
        "youtube_minutes": 0,
        "snacks": 0,
        "marble_plays": 0,
        "bubble_plays": 0,
    }, "오래된 탭의 저장 시도는 실제 획득분(+1)만 반영해야 한다."

    assert result["afterCloudPull"] == result["storedAfterStaleTab"], (
        "오래된 클라우드 스냅샷이 사용한 보상을 되살리면 안 된다."
    )
    assert result["afterReload"] == result["storedAfterStaleTab"], (
        "재로드 후에도 잔액이 유지되어야 한다."
    )


def test_legacy_snapshot_overwrite_cannot_restore_consumed_rewards(
    tmp_path: Path,
) -> None:
    result = _run_harness(tmp_path)

    assert result["overwriteEmptied"] == {
        "gems": 0,
        "youtube_minutes": 0,
        "snacks": 0,
        "marble_plays": 0,
        "bubble_plays": 0,
    }
    assert result["journalPreserved"] is True, "복구 저널이 유지되어야 한다."
    assert result["afterLegacyOverwrite"] == result["overwriteEmptied"], (
        "원장을 모르는 스냅샷 덮어쓰기도 사용 기록을 되살리지 못해야 한다."
    )


def test_receipt_grant_is_idempotent_across_tabs(tmp_path: Path) -> None:
    result = _run_harness(tmp_path)

    assert result["receiptFirst"]["success"] is True
    assert result["receiptSecond"]["success"] is False
    assert result["receiptSecond"]["alreadyClaimed"] is True
    assert result["receiptGems"] == 2, (
        "같은 영수증은 두 탭에서 시도해도 한 번만 지급되어야 한다."
    )


def test_free_time_start_consumption_is_recorded_and_durable(tmp_path: Path) -> None:
    result = _run_harness(tmp_path)

    assert result["freeTimeStartCode"] == "started"
    assert result["freeTimeAfterStart"] == 20
    assert result["freeTimeConsumeEvent"] is True, (
        "자유시간 시작 차감은 사용 이벤트로 남아야 한다."
    )
    assert result["freeTimeAfterPull"] == 20, (
        "클라우드 재병합 후에도 차감이 유지되어야 한다."
    )
