"""크로스 브라우저·크로스 기기 상단 보상 체계 통합 동기화 검증.

검증 범위:
1. 새 브라우저 첫 보상 획득 후 새로고침(boot) 시 보석이 0으로 증발하지 않는다.
2. 기기 A(기존 보상 보유)와 새 브라우저 B(빈 localStorage)가 같은 계정으로 로그인하면
   양쪽 모두 동일한 잔액·상점 항목·테마로 수렴한다(0 초기화 및 영구 분기 재발 방지).
3. 이미 legacy_snapshot_downward로 오염된 클라우드/로컬 원장도 동기화 시 자동 복구된다.
4. 브라우저 A와 B에서 동시 획득·유튜브 자유시간 세션 시작·수학 오늘의 목표 달성이 일어나도
   pull-merge-before-flush 및 merge-before-upsert를 통해 양쪽 상단 보상/목표가 일치한다.
5. 기존 로컬 보상이 있고 클라우드가 비어 있는 기기가 로그인하면 로컬 보상을 클라우드에 시드하여
   다른 브라우저에서도 즉시 동일하게 보인다.
6. sync-engine.js 로드 전에 Auth 세션 확인이 먼저 끝난 경우(Auth.whenReady resolved)에도
   초기 pullAndMerge가 누락되지 않는다.
7. 동일 브라우저에서 다른 계정(user-1 -> user-2)으로 전환하면 이전 계정의 로컬 캐시가 섞이지 않는다.
8. 모든 학습 진입점(index, english, math, korean, science, weekly-test, guardian)이
   reward-ledger.js 직후 정적으로 sync-engine.js를 로드한다.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_node(script: str) -> dict:
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Node script failed (rc={proc.returncode}):\n{proc.stderr}")
    lines = [line for line in proc.stdout.strip().splitlines() if line.strip()]
    return json.loads(lines[-1])


MULTI_DEVICE_HARNESS = r"""
import fs from 'node:fs';
import vm from 'node:vm';

const FILES = {
  ledger: './shared/domain/reward-ledger.js',
  allowance: './shared/domain/free-time-allowance.js',
  session: './shared/domain/free-time-session.js',
  launcher: './shared/domain/external-tab-launcher.js',
  tx: './domains/reward/free-time-session-start-transaction.js',
  sync: './domains/sync/sync-engine.js',
  reward: './domains/reward/reward.js',
  dailyGoal: './domains/math/daily-goal.js',
};

function createCloudDb(initialRows = {}) {
  // Map of `${user_id}::${data_key}` -> { user_id, data_key, payload, updated_at }
  const table = new Map();
  let clock = 10_000;
  for (const [userId, entries] of Object.entries(initialRows)) {
    for (const [key, val] of Object.entries(entries)) {
      clock += 10;
      table.set(`${userId}::${key}`, {
        user_id: userId,
        data_key: key,
        payload: JSON.parse(JSON.stringify(val.payload ?? val)),
        updated_at: val.updated_at || new Date(clock).toISOString(),
      });
    }
  }

  return {
    table,
    clientFor() {
      return {
        from(tableName) {
          if (tableName !== 'user_data') throw new Error(`unexpected table: ${tableName}`);
          const state = { userId: null, keys: null };
          const builder = {
            select() { return builder; },
            eq(col, val) {
              if (col === 'user_id') state.userId = val;
              return builder;
            },
            in(col, vals) {
              if (col === 'data_key') state.keys = Array.from(vals);
              const rows = [];
              for (const key of state.keys || []) {
                const row = table.get(`${state.userId}::${key}`);
                if (row) rows.push(JSON.parse(JSON.stringify(row)));
              }
              return Promise.resolve({ data: rows, error: null });
            },
            upsert(payloadObj) {
              clock += 10;
              const row = {
                user_id: payloadObj.user_id,
                data_key: payloadObj.data_key,
                payload: JSON.parse(JSON.stringify(payloadObj.payload)),
                updated_at: payloadObj.updated_at || new Date(clock).toISOString(),
              };
              table.set(`${row.user_id}::${row.data_key}`, row);
              return Promise.resolve({ data: [row], error: null });
            },
          };
          return builder;
        },
      };
    },
    read(userId, key) {
      const row = table.get(`${userId}::${key}`);
      return row ? JSON.parse(JSON.stringify(row.payload)) : null;
    },
  };
}

function createBrowser(cloud, {
  userId = 'user-1',
  initialLocal = {},
  authAlreadyReady = false,
  loadRewardSystem = true,
  loadDailyGoal = false,
} = {}) {
  const store = new Map(
    Object.entries(initialLocal).map(([k, v]) => [
      k,
      typeof v === 'string' ? v : JSON.stringify(v),
    ])
  );
  const listeners = new Map();
  let currentUser = userId ? { id: userId, email: `${userId}@example.com` } : null;
  let readyResolved = authAlreadyReady;
  let resolveReady;
  const readyPromise = authAlreadyReady
    ? Promise.resolve(currentUser)
    : new Promise((res) => { resolveReady = res; });

  const localStorage = {
    getItem(k) { return store.has(k) ? store.get(k) : null; },
    setItem(k, v) { store.set(k, String(v)); },
    removeItem(k) { store.delete(k); },
    clear() { store.clear(); },
  };

  const document = {
    readyState: 'complete',
    visibilityState: 'visible',
    body: { dataset: {}, classList: { toggle() {}, add() {}, remove() {} } },
    addEventListener(type, fn) {
      if (!listeners.has(`doc:${type}`)) listeners.set(`doc:${type}`, []);
      listeners.get(`doc:${type}`).push(fn);
    },
    getElementById() { return null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    createElement() {
      return {
        style: {},
        classList: { add() {}, remove() {}, toggle() {} },
        appendChild() {},
        setAttribute() {},
        addEventListener() {},
      };
    },
  };

  const window = {
    localStorage,
    document,
    navigator: { onLine: true },
    supabaseClient: cloud.clientFor(),
    Event: class Event {
      constructor(type) {
        this.type = type;
      }
    },
    CustomEvent: class CustomEvent {
      constructor(type, init = {}) {
        this.type = type;
        this.detail = init.detail;
      }
    },
    Auth: {
      getUser() { return currentUser; },
      isReady() { return readyResolved; },
      whenReady() { return readyPromise; },
    },
    RewardSystemUI: {
      injectCriticalStyles() {},
      injectInventoryBar() {},
      injectStyles(_state, cb) { if (cb) cb(); },
      syncInventoryBarWithState(state) { window._lastRenderedRewardState = JSON.parse(JSON.stringify(state)); },
      updateUI(state) { window._lastRenderedRewardState = JSON.parse(JSON.stringify(state)); },
      applyBodyTopOffset() {},
      renderFreeTimeTimerUI(snap) { window._lastBannerSnap = snap ? JSON.parse(JSON.stringify(snap)) : null; },
      renderExpiredFreeTimeSessionUI(snap) { window._lastBannerSnap = snap ? JSON.parse(JSON.stringify(snap)) : null; },
      showToast() {},
    },
    addEventListener(type, fn) {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(fn);
    },
    removeEventListener(type, fn) {
      const arr = listeners.get(type) || [];
      const idx = arr.indexOf(fn);
      if (idx >= 0) arr.splice(idx, 1);
    },
    dispatchEvent(evt) {
      for (const fn of [...(listeners.get(evt.type) || [])]) fn(evt);
    },
    open() {
      return { closed: false, opener: null, location: { href: '' }, close() {} };
    },
    setTimeout,
    clearTimeout,
    // 주기 타이머가 테스트 프로세스를 붙잡지 않도록 더미 id 반환
    setInterval() { return 1; },
    clearInterval() {},
  };
  window.window = window;
  window.globalThis = window;

  Object.assign(window, {
    self: window,
    console,
    Date,
    Math,
    JSON,
    Number,
    String,
    Boolean,
    Object,
    Array,
    Set,
    Map,
    Promise,
    Error,
    TypeError,
    RegExp,
    parseInt,
    parseFloat,
    isNaN,
    isFinite,
  });

  const ctx = vm.createContext(window);

  for (const key of ['ledger', 'allowance', 'session', 'launcher', 'tx', 'sync']) {
    vm.runInContext(fs.readFileSync(FILES[key], 'utf8'), ctx, { filename: FILES[key] });
  }
  if (loadDailyGoal) {
    vm.runInContext(fs.readFileSync(FILES.dailyGoal, 'utf8'), ctx, { filename: FILES.dailyGoal });
  }
  if (loadRewardSystem) {
    vm.runInContext(fs.readFileSync(FILES.reward, 'utf8'), ctx, { filename: FILES.reward });
    vm.runInContext('globalThis.RewardSystem = RewardSystem;', ctx);
  }

  async function flushMicrotasks(rounds = 8) {
    for (let i = 0; i < rounds; i += 1) {
      await new Promise((r) => setTimeout(r, 0));
    }
  }

  return {
    window,
    store,
    localStorage,
    flushMicrotasks,
    async signIn(nextUserId = userId) {
      currentUser = nextUserId ? { id: nextUserId, email: `${nextUserId}@example.com` } : null;
      readyResolved = true;
      if (resolveReady) resolveReady(currentUser);
      window.dispatchEvent(new window.CustomEvent('auth-changed', { detail: { user: currentUser } }));
      await flushMicrotasks();
    },
    readLocalJson(key) {
      const raw = store.get(key);
      return raw ? JSON.parse(raw) : null;
    },
  };
}
"""


def test_single_browser_first_earn_survives_reload():
    """빈 브라우저에서 첫 보석을 획득한 뒤 새로고침해도 0으로 증발하지 않는다."""
    result = _run_node(
        MULTI_DEVICE_HARNESS
        + """
        const cloud = createCloudDb();
        const b1 = createBrowser(cloud, { userId: null });
        b1.window.RewardSystem.add('gems', 2, { reason: 'quiz_clear' });
        const beforeReload = b1.window.RewardSystem.getState().gems;

        // 동일 localStorage를 가진 채 페이지 새로고침 시뮬레이션
        const snapshotLocal = Object.fromEntries(b1.store.entries());
        const b1Reloaded = createBrowser(cloud, { userId: null, initialLocal: snapshotLocal });
        const afterReload = b1Reloaded.window.RewardSystem.getState().gems;

        console.log(JSON.stringify({ beforeReload, afterReload }));
        """
    )
    assert result["beforeReload"] == 2
    assert result["afterReload"] == 2, (
        f"첫 보석 적립 후 새로고침 시 잔액이 유지되어야 하나 {result['afterReload']}이 되었다."
    )


def test_fresh_browser_converges_with_existing_cloud_device_without_zero_wipe():
    """기기 A의 클라우드 보상이 새 브라우저 B(빈 localStorage) 로그인 시 0으로 깎이지 않고 양쪽 모두 수렴한다."""
    result = _run_node(
        MULTI_DEVICE_HARNESS
        + """
        const cloud = createCloudDb();
        const deviceA = createBrowser(cloud, {
          userId: 'user-1',
          initialLocal: {
            study_rewards: {
              gems: 7,
              youtube_minutes: 30,
              snacks: 3,
              marble_plays: 1,
              bubble_plays: 2,
              theme: 'analog',
              shop_items: [
                { id: 'youtube', name: '유튜브 10분', icon: '📺', cost: 2 },
                { id: 'snack', name: '맛있는 간식', icon: '🍪', cost: 2 },
                { id: 'marble', name: '마블 플레이 1회', icon: '🎮', cost: 3 },
                { id: 'bubble', name: '버블 게임 1회', icon: '🫧', cost: 2 },
                { id: 'custom_lego', name: '레고 조립 20분', icon: '🧱', cost: 4 },
              ],
              custom_inventory: { custom_lego: 1 },
              _updated_at: 1000,
            },
          },
        });
        await deviceA.signIn('user-1');

        // 완전히 비어 있는 새 브라우저 B가 동일 계정으로 로그인
        const browserB = createBrowser(cloud, { userId: 'user-1', initialLocal: {} });
        await browserB.signIn('user-1');

        // 기기 A가 다시 동기화해도 그대로 동일한 잔액이어야 한다
        await deviceA.window.SyncEngine.syncNow('recheck');
        await deviceA.flushMicrotasks();

        console.log(JSON.stringify({
          a: {
            gems: deviceA.window.RewardSystem.getState().gems,
            yt: deviceA.window.RewardSystem.getState().youtube_minutes,
            snacks: deviceA.window.RewardSystem.getState().snacks,
            lego: deviceA.window.RewardSystem.getState().custom_inventory.custom_lego || 0,
            theme: deviceA.window.RewardSystem.getState().theme,
            shopCount: deviceA.window.RewardSystem.getState().shop_items.length,
          },
          b: {
            gems: browserB.window.RewardSystem.getState().gems,
            yt: browserB.window.RewardSystem.getState().youtube_minutes,
            snacks: browserB.window.RewardSystem.getState().snacks,
            lego: browserB.window.RewardSystem.getState().custom_inventory.custom_lego || 0,
            theme: browserB.window.RewardSystem.getState().theme,
            shopCount: browserB.window.RewardSystem.getState().shop_items.length,
          },
        }));
        """
    )
    expected = {
        "gems": 7,
        "yt": 30,
        "snacks": 3,
        "lego": 1,
        "theme": "analog",
        "shopCount": 5,
    }
    assert result["a"] == expected
    assert result["b"] == expected


def test_poisoned_legacy_snapshot_downward_cloud_row_self_heals_across_devices():
    """이미 legacy_snapshot_downward로 0이 된 클라우드 데이터도 동기화 시 원래 잔액으로 복구된다."""
    result = _run_node(
        MULTI_DEVICE_HARNESS
        + """
        const poisoned = {
          gems: 0,
          youtube_minutes: 0,
          snacks: 0,
          marble_plays: 0,
          bubble_plays: 0,
          custom_inventory: {},
          reward_ledger: {
            v: 1,
            base: { gems: 9, youtube_minutes: 20, snacks: 2, marble_plays: 1, bubble_plays: 1, custom_inventory: {} },
            base_at: 2000,
            events: [
              { id: 'ev-poison-1', at: 0, key: 'gems', delta: -9, type: 'adjust', reason: 'legacy_snapshot_downward' },
              { id: 'ev-poison-2', at: 0, key: 'youtube_minutes', delta: -20, type: 'adjust', reason: 'legacy_snapshot_downward' },
              { id: 'ev-poison-3', at: 0, key: 'snacks', delta: -2, type: 'adjust', reason: 'legacy_snapshot_downward' },
              { id: 'ev-real-earn', at: 2500, key: 'gems', delta: 2, type: 'grant', reason: 'quiz' },
            ],
          },
          _updated_at: 3000,
        };
        const cloud = createCloudDb({ 'user-1': { study_rewards: poisoned } });
        const browser = createBrowser(cloud, { userId: 'user-1', initialLocal: {} });
        await browser.signIn('user-1');

        const cloudRow = cloud.read('user-1', 'study_rewards');
        console.log(JSON.stringify({
          localGems: browser.window.RewardSystem.getState().gems,
          localYt: browser.window.RewardSystem.getState().youtube_minutes,
          localSnacks: browser.window.RewardSystem.getState().snacks,
          cloudGems: cloudRow.gems,
          cloudBadEvents: (cloudRow.reward_ledger?.events || []).filter((e) => e.reason === 'legacy_snapshot_downward').length,
        }));
        """
    )
    assert result["localGems"] == 11
    assert result["localYt"] == 20
    assert result["localSnacks"] == 2
    assert result["cloudGems"] == 11
    assert result["cloudBadEvents"] == 0


def test_concurrent_rewards_youtube_session_and_math_daily_goal_converge():
    """브라우저 A(목표 달성·보석 획득)와 브라우저 B(유튜브 자유시간 세션 시작)가 모든 상단 상태를 일치시킨다."""
    result = _run_node(
        MULTI_DEVICE_HARNESS
        + """
        const initialRewards = {
          gems: 5,
          youtube_minutes: 30,
          snacks: 2,
          marble_plays: 0,
          bubble_plays: 0,
          custom_inventory: {},
          _updated_at: 1000,
        };
        const cloud = createCloudDb();
        const browserA = createBrowser(cloud, {
          userId: 'user-1',
          initialLocal: { study_rewards: initialRewards },
          loadDailyGoal: true,
        });
        await browserA.signIn('user-1');

        const browserB = createBrowser(cloud, {
          userId: 'user-1',
          initialLocal: {},
          loadDailyGoal: true,
        });
        await browserB.signIn('user-1');

        // 브라우저 A: 오늘의 수학 목표 생성 및 완료 + 보상(보석 2개 + 유튜브 10분) 수령
        const now = Date.now();
        let goal = browserA.window.MathDailyGoalEngine.initOrGetDailyGoal({
          now,
          masteryMap: {},
          skillOrder: ['math.add.within_10'],
          preference: { presetId: 'light' },
        });
        for (let i = 0; i < goal.targetCount; i += 1) {
          const step = browserA.window.MathDailyGoalEngine.recordGoalProgress({
            goal,
            skillId: 'math.add.within_10',
            correct: true,
            now,
          });
          goal = step.goal;
        }
        browserA.window.MathDailyGoalEngine.claimGoalReward({
          goal,
          rewardSystem: browserA.window.RewardSystem,
          now,
        });
        await browserA.flushMicrotasks();

        // 브라우저 B: 아직 A의 최신 상태를 안 당긴 상태에서 유튜브 10분 자유시간 시작!
        const ytNow = now + 50;
        const ytRes = browserB.window.RewardSystem.startYouTubeSession(10, { nowMs: ytNow });
        await browserB.flushMicrotasks();

        // 양쪽 브라우저가 포커스/주기 동기화를 수행하면 모든 상단 수치가 완전히 일치해야 한다
        await browserA.window.SyncEngine.syncNow('focus');
        await browserA.flushMicrotasks();
        await browserB.window.SyncEngine.syncNow('focus');
        await browserB.flushMicrotasks();

        const goalOnB = browserB.window.MathDailyGoalEngine.loadDailyGoal();
        const streakOnB = browserB.window.MathDailyGoalEngine.loadStreak();
        const sessionOnA = browserA.readLocalJson('study_youtube_free_time_session_v1');
        const usageOnA = browserA.readLocalJson('study_youtube_free_time_daily_usage_v1');

        console.log(JSON.stringify({
          ytOk: Boolean(ytRes && ytRes.code === 'started'),
          gemsA: browserA.window.RewardSystem.getState().gems,
          gemsB: browserB.window.RewardSystem.getState().gems,
          ytA: browserA.window.RewardSystem.getState().youtube_minutes,
          ytB: browserB.window.RewardSystem.getState().youtube_minutes,
          goalCompletedOnB: Boolean(goalOnB && goalOnB.completed && goalOnB.rewardGranted),
          streakOnB: streakOnB ? streakOnB.currentStreak : 0,
          sessionRunningOnA: Boolean(sessionOnA && sessionOnA.status === 'running'),
          bannerRenderedOnA: Boolean(browserA.window._lastBannerSnap && browserA.window._lastBannerSnap.status === 'running'),
          dailyUsedOnA: usageOnA ? (usageOnA.morningMinutes || 0) + (usageOnA.afternoonMinutes || 0) : 0,
        }));
        """
    )
    assert result["ytOk"] is True
    assert result["gemsA"] == 7
    assert result["gemsB"] == 7
    assert result["ytA"] == 30
    assert result["ytB"] == 30
    assert result["goalCompletedOnB"] is True
    assert result["streakOnB"] == 1
    assert result["sessionRunningOnA"] is True
    assert result["bannerRenderedOnA"] is True
    assert result["dailyUsedOnA"] == 10


def test_sync_engine_bootstraps_even_when_auth_resolved_before_script_load():
    """auth-gate/auth.js가 sync-engine.js보다 먼저 세션을 확정한 경우에도 초기 pull이 실행된다."""
    result = _run_node(
        MULTI_DEVICE_HARNESS
        + """
        const cloud = createCloudDb({
          'user-1': {
            study_rewards: {
              gems: 12,
              youtube_minutes: 40,
              snacks: 4,
              marble_plays: 0,
              bubble_plays: 0,
              custom_inventory: {},
              _updated_at: 2000,
            },
          },
        });
        // auth-changed 이벤트를 다시 쏘지 않고 Auth.whenReady()만 이미 resolve된 상태
        const browser = createBrowser(cloud, {
          userId: 'user-1',
          authAlreadyReady: true,
          initialLocal: {},
        });
        await browser.flushMicrotasks();

        console.log(JSON.stringify({
          gems: browser.window.RewardSystem.getState().gems,
          yt: browser.window.RewardSystem.getState().youtube_minutes,
          snacks: browser.window.RewardSystem.getState().snacks,
        }));
        """
    )
    assert result == {"gems": 12, "yt": 40, "snacks": 4}


def test_switching_accounts_on_same_browser_isolates_local_cache():
    """같은 브라우저에서 user-1 로그아웃 후 user-2로 로그인하면 user-1의 로컬 보상이 섞이지 않는다."""
    result = _run_node(
        MULTI_DEVICE_HARNESS
        + """
        const cloud = createCloudDb({
          'user-1': { study_rewards: { gems: 15, youtube_minutes: 30, snacks: 5, _updated_at: 1000 } },
          'user-2': {
            study_rewards: {
              gems: 2,
              youtube_minutes: 0,
              snacks: 1,
              reward_ledger: {
                v: 1,
                base: { gems: 2, youtube_minutes: 0, snacks: 1, marble_plays: 0, bubble_plays: 0, custom_inventory: {} },
                base_at: 1000,
                events: [],
              },
              _updated_at: 1000,
            },
          },
        });
        const browser = createBrowser(cloud, { userId: 'user-1', initialLocal: {} });
        await browser.signIn('user-1');
        browser.window.RewardSystem.add('gems', 3, { reason: 'user1_quiz' });
        await browser.flushMicrotasks();
        const user1Gems = browser.window.RewardSystem.getState().gems;

        // 동일 브라우저에서 user-2로 전환
        await browser.signIn('user-2');
        const user2Gems = browser.window.RewardSystem.getState().gems;
        const user2CloudGems = cloud.read('user-2', 'study_rewards').gems;

        console.log(JSON.stringify({ user1Gems, user2Gems, user2CloudGems }));
        """
    )
    assert result["user1Gems"] == 18
    assert result["user2Gems"] == 2
    assert result["user2CloudGems"] == 2


def test_all_learning_and_hub_surfaces_statically_load_sync_engine_after_reward_ledger():
    """모든 주요 진입 페이지가 reward-ledger.js 뒤에 sync-engine.js를 정적으로 포함한다."""
    pages = [
        ROOT / "index.html",
        ROOT / "domains" / "english" / "index.html",
        ROOT / "domains" / "math" / "index.html",
        ROOT / "domains" / "korean" / "index.html",
        ROOT / "domains" / "science" / "index.html",
        ROOT / "domains" / "english" / "weekly-test" / "index.html",
        ROOT / "domains" / "reward" / "guardian" / "index.html",
    ]
    for page in pages:
        html = page.read_text(encoding="utf-8")
        ledger_idx = html.find("shared/domain/reward-ledger.js")
        sync_idx = html.find("domains/sync/sync-engine.js")
        assert ledger_idx != -1, f"{page}: reward-ledger.js 스크립트가 없다."
        assert sync_idx != -1, (
            f"{page}: domains/sync/sync-engine.js 정적 스크립트가 없다."
        )
        assert ledger_idx < sync_idx, (
            f"{page}: reward-ledger.js가 sync-engine.js보다 먼저 로드되어야 한다."
        )
