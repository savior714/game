"""보상 초기화 기준점 및 획득/사용 감사 신뢰도 — 런타임 통합 계약 검증.

고정하는 계약:
0. 이전(Epoch 0) 누적 보상 스냅샷 및 부속 자유시간 세션은 초기화 기준점 적용 시 모두 0으로 정리된다.
1. 초기화 이후 획득한 보상을 사용한 뒤에는 어떤 경로로도(클라우드 pull, 다른 탭, 재로드) 되살아나지 않는다.
2. 실제 획득 이벤트가 있을 때만 그만큼 증가하며 초 단위 시각·사유·전후 잔액이 감사 리포트에 남는다.
3. 같은 영수증(receipt)은 몇 번을 지급 시도해도 한 번만 지급된다.
4. 자유시간(YouTube) 시작 차감도 원장에 상세 감사 이벤트로 남고, 되살아나지 않는다.
5. 보호자 수동 전체 초기화(resetAllRewards) 실행 시 Epoch가 증가하며 구 Epoch 데이터가 부활하지 않는다.
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

function createSharedStore(initial, extras = {}) {
  const map = new Map();
  if (initial) map.set('study_rewards', JSON.stringify(initial));
  for (const [k, v] of Object.entries(extras)) {
    map.set(k, typeof v === 'string' ? v : JSON.stringify(v));
  }
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
    location: { href: 'https://example.test/index.html', pathname: '/index.html', reload() {} },
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
    get length() { return store.size; },
    key(idx) { return Array.from(store.keys())[idx] || null; },
    getItem(key) { return store.has(key) ? store.get(key) : null; },
    setItem(key, value) { store.set(key, String(value)); },
    removeItem(key) { store.delete(key); },
  };

  const context = vm.createContext({
    window,
    document,
    location: window.location,
    localStorage,
    self: window,
    navigator: { onLine: true, userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0)' },
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

  // ── 0. 이전 누적 데이터(Epoch 0) 및 이전 자유시간 세션은 부팅 즉시 0/inactive로 초기화된다 ──
  const preResetStore = createSharedStore(
    {
      gems: 19,
      youtube_minutes: 50,
      snacks: 4,
      marble_plays: 2,
      bubble_plays: 1,
      _updated_at: 1000,
    },
    {
      study_youtube_free_time_session_v1: {
        schemaVersion: 1,
        status: 'running',
        sessionId: 'old-session-1',
        startedAt: 900,
        endsAt: 9999999999999,
      },
      'aiden_receipt_old-1': { receiptId: 'old-1', gems: 2 },
    }
  );
  const cutoverTab = makeTab(preResetStore);
  report.cutoverBalances = fieldSummary(cutoverTab.rs.getState());
  report.cutoverSession = JSON.parse(preResetStore.get('study_youtube_free_time_session_v1'));
  report.cutoverOldReceiptExists = preResetStore.has('aiden_receipt_old-1');

  // ── A. 초기화 후 적립한 보상을 모두 사용한 뒤 오래된 클라우드/탭 스냅샷이 되살리지 못한다 ──
  const storeA = createSharedStore();
  const tabSeed = makeTab(storeA);
  tabSeed.rs.add('gems', 7, { reason: 'math_daily_goal', source: 'math', detail: '수학 목표 보상' });
  tabSeed.rs.add('youtube', 3, { reason: 'math_daily_goal', source: 'math', detail: '자유시간 보상' });
  tabSeed.rs.add('snack', 3, { reason: 'gem_reward', source: 'hub', detail: '간식 지급' });
  tabSeed.rs.add('marble', 2);
  tabSeed.rs.add('bubble', 1);

  const tabOld = makeTab(storeA); // 소비 이전에 열려 있던 탭
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
  tabOld.rs.add('gems', 1, { reason: 'rocket_launch', source: 'english', detail: '로켓 발사 보상 (영어)' });
  report.afterStaleTabWrite = fieldSummary(tabMain.rs.getState());
  const storedAfterStaleTab = tabMain.readRewards();
  report.storedAfterStaleTab = fieldSummary(storedAfterStaleTab);

  // 클라우드 pull: 서버에는 소비 이전의 스냅샷이 남아 있다.
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

  const tabReloaded = makeTab(storeA);
  report.afterReload = fieldSummary(tabReloaded.rs.getState());

  // ── A-2. 구버전 페이지가 원장 없이 스냅샷을 통째로 덮어써도 복구 저널이 지킨다 ──
  const overwriteStore = createSharedStore();
  const overwriteTab = makeTab(overwriteStore);
  overwriteTab.rs.add('gems', 7);
  overwriteTab.rs.add('youtube', 3);
  overwriteTab.rs.add('snack', 3);
  overwriteTab.rs.consumeInternal('snack', null, 3);
  overwriteTab.rs.consumeInternal('youtube', null, 3);
  for (let i = 0; i < 7; i += 1) overwriteTab.rs.exchangeGem('snack');
  overwriteTab.rs.consumeInternal('snack', null, 7);
  report.overwriteEmptied = fieldSummary(overwriteTab.rs.getState());

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
  const receiptStore = createSharedStore();
  const tabReceiptA = makeTab(receiptStore);
  const tabReceiptB = makeTab(receiptStore);
  report.receiptFirst = tabReceiptA.rs.grantOnce('reward.diversity.2026-10-23', 'gems', 2, {
    reason: 'diversity',
    source: 'english',
    detail: '다과목 학습 보상 (수학·영어 2과목 달성)',
  });
  report.receiptSecond = tabReceiptB.rs.grantOnce('reward.diversity.2026-10-23', 'gems', 2);
  report.receiptGems = tabReceiptA.readRewards().gems;

  // ── C. 자유시간 시작 차감도 원장 사용 이벤트 + 상세 사유로 남고 되살아나지 않는다 ──
  const freeTimeStore = createSharedStore();
  const tabFree = makeTab(freeTimeStore);
  tabFree.rs.add('youtube', 3, { reason: 'math_daily_goal', source: 'math', detail: '자유시간 적립' });
  const startResult = tabFree.rs.startYouTubeSession(10);
  report.freeTimeStartCode = startResult.code;
  report.freeTimeAfterStart = JSON.parse(tabFree.localStorage.getItem('study_rewards')).youtube_minutes;
  const freeTimeAudit = tabFree.rs.getAuditReport({});
  report.freeTimeConsumeEvent = freeTimeAudit.entries.some(
    (event) => event.reason === 'free_time_session'
      && event.key === 'youtube_minutes'
      && event.delta === -10
      && event.balanceBefore === 30
      && event.balanceAfter === 20
      && /유튜브 브라우저 타이머 시작/.test(event.detail)
  );

  tabFree.window.Auth = { getUser() { return { id: 'user-1' }; } };
  tabFree.window.supabaseClient = tabMain.window.supabaseClient;
  vm.runInContext(syncSrc, tabFree.context);
  if (tabFree.window.SyncEngine) {
    await tabFree.window.SyncEngine.pullAndMerge(['study_rewards']);
  }
  report.freeTimeAfterPull = JSON.parse(tabFree.localStorage.getItem('study_rewards')).youtube_minutes;

  // ── D. 보호자 수동 전체 초기화(resetAllRewards) 실행 시 Epoch가 2로 오르고 모든 잔액/세션이 0이 된다 ──
  tabFree.rs.resetAllRewards({ note: '보호자 정산 완료' });
  const postManualResetAudit = tabFree.rs.getAuditReport({});
  report.manualResetEpoch = postManualResetAudit.epoch;
  report.manualResetBalances = fieldSummary(tabFree.rs.getState());
  report.manualResetHasCheckpoint = postManualResetAudit.entries.some(
    (entry) => entry.type === 'reset' && /보호자 정산 완료/.test(entry.detail)
  );

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


def test_pre_cutover_rewards_and_sessions_reset_cleanly_to_zero(tmp_path: Path) -> None:
    result = _run_harness(tmp_path)

    assert result["cutoverBalances"] == {
        "gems": 0,
        "youtube_minutes": 0,
        "snacks": 0,
        "marble_plays": 0,
        "bubble_plays": 0,
    }
    assert result["cutoverSession"]["status"] == "inactive"
    assert result["cutoverSession"]["resetEpoch"] == 1
    assert result["cutoverOldReceiptExists"] is False


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
    }
    assert result["verifyAfterConsume"]["ok"] is True
    assert result["ledgerEvents"] > 0

    assert result["storedAfterStaleTab"] == {
        "gems": 1,
        "youtube_minutes": 0,
        "snacks": 0,
        "marble_plays": 0,
        "bubble_plays": 0,
    }
    assert result["afterCloudPull"] == result["storedAfterStaleTab"]
    assert result["afterReload"] == result["storedAfterStaleTab"]


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
    assert result["journalPreserved"] is True
    assert result["afterLegacyOverwrite"] == result["overwriteEmptied"]


def test_receipt_grant_is_idempotent_across_tabs(tmp_path: Path) -> None:
    result = _run_harness(tmp_path)

    assert result["receiptFirst"]["success"] is True
    assert result["receiptSecond"]["success"] is False
    assert result["receiptSecond"]["alreadyClaimed"] is True
    assert result["receiptGems"] == 2


def test_free_time_start_consumption_and_guardian_reset_are_audited_and_durable(
    tmp_path: Path,
) -> None:
    result = _run_harness(tmp_path)

    assert result["freeTimeStartCode"] == "started"
    assert result["freeTimeAfterStart"] == 20
    assert result["freeTimeConsumeEvent"] is True
    assert result["freeTimeAfterPull"] == 20
    assert result["manualResetEpoch"] == 2
    assert result["manualResetBalances"] == {
        "gems": 0,
        "youtube_minutes": 0,
        "snacks": 0,
        "marble_plays": 0,
        "bubble_plays": 0,
    }
    assert result["manualResetHasCheckpoint"] is True
