// Sync Engine Module (Offline-First Queue + Cross-Device Deterministic Merge)
// 의존성: window.Auth, window.supabaseClient, window.RewardLedger

(function () {
  const QUEUE_KEY = 'sync_queue';
  const REWARD_LEDGER_JOURNAL_KEY = 'study_rewards_ledger_v1';
  const ACTIVE_USER_STORAGE_KEY = 'aiden_active_auth_user_id_v1';
  const PERIODIC_INTERVAL_MS = 30 * 1000; // 30초(가시 탭 전용 주기 동기화)
  const FOCUS_COOLDOWN_MS = 3 * 1000; // 탭/창 전환 시 3초 쿨다운
  const SYNC_EVENT_KEY = 'aiden_sync_trigger'; // 탭 간 동기화 트리거용

  let _syncIntervalId = null;
  let _lastSyncAt = 0;
  let _syncInProgress = false;
  let _pendingSyncReason = null;
  let _activeSyncPromise = null;

  const LEGACY_STATS_KEY_MAP = {
    mathGameStats: 'aiden_math_stats',
    englishGameStats: 'aiden_english_stats',
    koreanGameStats: 'aiden_korean_stats',
    scienceGameStats: 'aiden_science_stats',
  };
  const CANONICAL_STATS_KEYS = Object.values(LEGACY_STATS_KEY_MAP);

  const COMPANION_REWARD_KEYS = [
    'study_youtube_free_time_session_v1',
    'study_youtube_free_time_daily_usage_v1',
    'aiden_math_daily_goal_v1',
    'aiden_math_streak_v1',
    'aiden_math_goal_preference_v1',
    'aiden_math_learning_evidence_v1',
    'aiden_daily_streak',
    'aiden_diversity',
    'aiden_milestones',
  ];

  // 페이지 진입·초기 로그인·포커스 복귀·주기 동기화에서 함께 당길 표준 키 목록.
  const DEFAULT_PULL_KEYS = [
    'study_rewards',
    ...COMPANION_REWARD_KEYS,
    ...CANONICAL_STATS_KEYS,
    ...Object.keys(LEGACY_STATS_KEY_MAP),
    'aiden_canonical_weekly_vocabulary_v1',
  ];

  const SERVER_AUTHORITATIVE_KEYS = new Set([
    'aiden_canonical_weekly_vocabulary_v1',
    'englishWeeklyWords',
  ]);

  const DEFAULT_STUDY_SHOP_ITEMS = [
    { id: 'youtube', icon: '📺', label: '유튜브 10분', desc: '좋아하는 영상 시청', price: 1 },
    { id: 'snack', icon: '🍪', label: '간식 1개', desc: '맛있는 간식 시간', price: 1 },
    { id: 'marble', icon: '🎮', label: '마블 게임', desc: '마블 한 판 더!', price: 1 },
    { id: 'bubble', icon: '🫧', label: '비눗방울 게임', desc: '버블팡 한 판 더!', price: 1 },
  ];

  const USER_SCOPED_LOCAL_KEYS = [
    QUEUE_KEY,
    'study_rewards',
    REWARD_LEDGER_JOURNAL_KEY,
    ...COMPANION_REWARD_KEYS,
    ...CANONICAL_STATS_KEYS,
    ...Object.keys(LEGACY_STATS_KEY_MAP),
  ];

  function isOnline() {
    if (typeof navigator === 'undefined' || typeof navigator.onLine !== 'boolean') {
      return true;
    }
    return navigator.onLine;
  }

  function createDomEvent(type, detail) {
    if (detail !== undefined && typeof CustomEvent === 'function') {
      return new CustomEvent(type, { detail });
    }
    if (typeof Event === 'function') {
      return new Event(type);
    }
    if (typeof CustomEvent === 'function') {
      return new CustomEvent(type);
    }
    return { type, detail };
  }

  function isPlainObject(value) {
    return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
  }

  function safeParseJson(raw, fallback = null) {
    if (!raw || typeof raw !== 'string') return fallback;
    try {
      return JSON.parse(raw);
    } catch (e) {
      return fallback;
    }
  }

  function ensureAccountStorageScope(userId) {
    if (!userId || typeof userId !== 'string') return false;
    let switchedAccount = false;
    try {
      const prevUserId = localStorage.getItem(ACTIVE_USER_STORAGE_KEY);
      if (prevUserId && prevUserId !== userId) {
        switchedAccount = true;
        for (const key of USER_SCOPED_LOCAL_KEYS) {
          localStorage.removeItem(key);
        }
      }
      localStorage.setItem(ACTIVE_USER_STORAGE_KEY, userId);
    } catch (e) {
      console.warn('[SyncEngine] Failed to enforce account storage scope:', e);
    }
    return switchedAccount;
  }

  function persistRewardsLocally(mergedRewards) {
    localStorage.setItem('study_rewards', JSON.stringify(mergedRewards));
    if (mergedRewards && isPlainObject(mergedRewards.reward_ledger)) {
      try {
        localStorage.setItem(
          REWARD_LEDGER_JOURNAL_KEY,
          JSON.stringify(mergedRewards.reward_ledger)
        );
      } catch (e) {
        console.warn('[SyncEngine] Failed to update reward ledger journal:', e);
      }
    }
  }

  function getQueue() {
    try {
      const q = JSON.parse(localStorage.getItem(QUEUE_KEY) || '{}');
      if (q && typeof q === 'object') {
        for (const k of Object.keys(q)) {
          if (SERVER_AUTHORITATIVE_KEYS.has(k)) {
            delete q[k];
          }
        }
        return q;
      }
      return {};
    } catch (e) {
      return {};
    }
  }

  function setQueue(q) {
    try {
      localStorage.setItem(QUEUE_KEY, JSON.stringify(q));
    } catch (e) {
      console.warn('Sync queue full', e);
    }
  }

  // ── 1. 도메인별 결정적 병합 함수 ─────────────────────────────

  function mergeStudyRewardsPayload(local, remote) {
    const L = local && typeof local === 'object' ? local : {};
    const R = remote && typeof remote === 'object' ? remote : {};
    const rewardLedger = typeof window !== 'undefined' && window.RewardLedger;
    if (rewardLedger && typeof rewardLedger.mergeStates === 'function') {
      const merged = rewardLedger.mergeStates(L, R, { adoptFields: true });
      if (!Array.isArray(merged.shop_items) || merged.shop_items.length === 0) {
        merged.shop_items = DEFAULT_STUDY_SHOP_ITEMS.slice();
      }
      if (typeof merged.theme !== 'string') {
        merged.theme = 'modern';
      }
      return merged;
    }
    // 원장 모듈이 아직 로드되지 않은 비정상 경로에서는 보수적으로 폴백하되,
    // 로컬이 완전히 비어 있는 새 브라우저({})라면 원격 스냅샷을 그대로 수용한다.
    const localHasBalanceKey = ['gems', 'youtube_minutes', 'snacks', 'marble_plays', 'bubble_plays']
      .some((k) => Object.prototype.hasOwnProperty.call(L, k));
    const minOf = (a, b) => {
      if (!localHasBalanceKey) return Math.max(0, Math.floor(Number(b) || 0));
      const na = Math.max(0, Math.floor(Number(a) || 0));
      const nb = Math.max(0, Math.floor(Number(b) || 0));
      return Math.min(na, nb);
    };
    const localTime = Number(L._updated_at) || 0;
    const remoteTime = Number(R._updated_at) || 0;
    const newer = localTime >= remoteTime ? L : R;
    const older = localTime >= remoteTime ? R : L;
    const defaultShopItems = [
      { id: 'youtube', name: '유튜브 10분', icon: '📺', cost: 2 },
      { id: 'snack', name: '맛있는 간식', icon: '🍪', cost: 2 },
      { id: 'marble', name: '마블 플레이 1회', icon: '🎮', cost: 3 },
      { id: 'bubble', name: '버블 게임 1회', icon: '🫧', cost: 2 },
    ];
    return {
      ...older,
      ...newer,
      gems: minOf(L.gems, R.gems),
      youtube_minutes: minOf(L.youtube_minutes, R.youtube_minutes),
      snacks: minOf(L.snacks, R.snacks),
      marble_plays: minOf(L.marble_plays, R.marble_plays),
      bubble_plays: minOf(L.bubble_plays, R.bubble_plays),
      shop_items: Array.isArray(newer.shop_items)
        ? newer.shop_items
        : (Array.isArray(older.shop_items) ? older.shop_items : defaultShopItems),
      theme: typeof newer.theme === 'string'
        ? newer.theme
        : (typeof older.theme === 'string' ? older.theme : 'modern'),
      _updated_at: Math.max(localTime, remoteTime),
    };
  }

  function normalizePulledRows(data) {
    return Array.isArray(data) ? data : [];
  }

  function activeRewardEpochContext() {
    const rewardLedger = typeof window !== 'undefined' && window.RewardLedger;
    const minEpoch = rewardLedger && Number(rewardLedger.BASELINE_RESET_EPOCH) > 0
      ? Number(rewardLedger.BASELINE_RESET_EPOCH)
      : 1;
    let epoch = minEpoch;
    let resetAt = 0;
    try {
      const raw = localStorage.getItem('study_rewards');
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && isPlainObject(parsed.reward_ledger)) {
          epoch = Math.max(epoch, Number(parsed.reward_ledger.reset_epoch) || 0);
          resetAt = Math.max(0, Number(parsed.reward_ledger.reset_at) || 0);
        }
      }
    } catch (_e) {}
    return { epoch, resetAt };
  }

  function mergeFreeTimeSessionPayload(local, remote) {
    const ctx = activeRewardEpochContext();
    const isCurrentEpochSession = (s) => {
      if (!isPlainObject(s)) return false;
      if ((Number(s.resetEpoch) || 0) >= ctx.epoch) return true;
      if (ctx.resetAt > 0 && Number.isFinite(Number(s.startedAt)) && Number(s.startedAt) > ctx.resetAt) {
        return true;
      }
      return false;
    };
    const sanitize = (s) => {
      if (!isPlainObject(s)) return {};
      if (!isCurrentEpochSession(s)) {
        return { schemaVersion: 1, status: 'inactive', sessionId: null, resetEpoch: ctx.epoch, resetAt: ctx.resetAt };
      }
      return s;
    };
    const L = sanitize(local);
    const R = sanitize(remote);
    const valid = (s) => isPlainObject(s)
      && s.schemaVersion === 1
      && typeof s.sessionId === 'string'
      && s.sessionId.length > 0
      && Number.isFinite(Number(s.startedAt));
    const vL = valid(L);
    const vR = valid(R);
    if (!vL && !vR) {
      return isPlainObject(R) && Object.keys(R).length > 0
        ? R
        : (isPlainObject(L) && Object.keys(L).length > 0 ? L : { schemaVersion: 1, status: 'inactive', sessionId: null, resetEpoch: ctx.epoch });
    }
    if (!vL) return { ...R, resetEpoch: ctx.epoch };
    if (!vR) return { ...L, resetEpoch: ctx.epoch };

    const statusRank = { inactive: 0, running: 1, expired: 2, acknowledged: 3 };
    if (L.sessionId === R.sessionId) {
      const rankL = statusRank[L.status] ?? 0;
      const rankR = statusRank[R.status] ?? 0;
      const primary = rankL >= rankR ? L : R;
      const secondary = rankL >= rankR ? R : L;
      return {
        ...secondary,
        ...primary,
        resetEpoch: ctx.epoch,
        warningEmittedAt: primary.warningEmittedAt || secondary.warningEmittedAt || null,
        expiredAt: primary.expiredAt || secondary.expiredAt || null,
        acknowledgedAt: primary.acknowledgedAt || secondary.acknowledgedAt || null,
      };
    }
    return {
      ...(Number(L.startedAt) >= Number(R.startedAt) ? L : R),
      resetEpoch: ctx.epoch,
    };
  }

  function mergeFreeTimeUsagePayload(local, remote) {
    const ctx = activeRewardEpochContext();
    const cleanUsage = (u) => {
      if (!isPlainObject(u)) return null;
      if ((Number(u.resetEpoch) || 0) < ctx.epoch) {
        return {
          schemaVersion: 1,
          dateKey: typeof u.dateKey === 'string' && u.dateKey ? u.dateKey : new Date().toISOString().slice(0, 10),
          morningMinutes: 0,
          afternoonMinutes: 0,
          resetEpoch: ctx.epoch,
        };
      }
      return u;
    };
    const L = cleanUsage(local);
    const R = cleanUsage(remote);
    const valid = (u) => isPlainObject(u)
      && u.schemaVersion === 1
      && typeof u.dateKey === 'string'
      && u.dateKey.length > 0;
    const vL = valid(L);
    const vR = valid(R);
    if (!vL && !vR) return { schemaVersion: 1, dateKey: new Date().toISOString().slice(0, 10), morningMinutes: 0, afternoonMinutes: 0, resetEpoch: ctx.epoch };
    if (!vL) return { ...R, resetEpoch: ctx.epoch };
    if (!vR) return { ...L, resetEpoch: ctx.epoch };
    if (L.dateKey !== R.dateKey) {
      return { ...(L.dateKey > R.dateKey ? L : R), resetEpoch: ctx.epoch };
    }
    return {
      schemaVersion: 1,
      dateKey: R.dateKey,
      morningMinutes: Math.max(Number(L.morningMinutes) || 0, Number(R.morningMinutes) || 0),
      afternoonMinutes: Math.max(Number(L.afternoonMinutes) || 0, Number(R.afternoonMinutes) || 0),
      resetEpoch: ctx.epoch,
    };
  }

  function mergeMathDailyGoalPayload(local, remote) {
    const ctx = activeRewardEpochContext();
    const cleanGoal = (g) => {
      if (!isPlainObject(g)) return {};
      const gEpoch = Number(g.resetEpoch) || 0;
      const completedAfterReset = ctx.resetAt > 0
        && Number.isFinite(Number(g.completedAt))
        && Number(g.completedAt) > ctx.resetAt;
      if (gEpoch < ctx.epoch && !completedAfterReset && typeof g.date === 'string' && g.date) {
        return {
          ...g,
          currentCount: 0,
          completed: false,
          completedAt: null,
          rewardGranted: false,
          resetEpoch: ctx.epoch,
        };
      }
      return g;
    };
    local = cleanGoal(local);
    remote = cleanGoal(remote);
    const valid = (g) => isPlainObject(g)
      && g.schemaVersion === 1
      && typeof g.date === 'string'
      && g.date.length > 0;
    const vL = valid(local);
    const vR = valid(remote);
    if (!vL && !vR) return isPlainObject(remote) ? remote : (isPlainObject(local) ? local : {});
    if (!vL) return { ...remote, resetEpoch: ctx.epoch };
    if (!vR) return { ...local, resetEpoch: ctx.epoch };

    if (local.date !== remote.date) {
      return { ...(local.date > remote.date ? local : remote), resetEpoch: ctx.epoch };
    }

    const score = (g) => (g.rewardGranted ? 2000 : 0)
      + (g.completed ? 1000 : 0)
      + Math.max(0, Number(g.currentCount) || 0);
    const scoreL = score(local);
    const scoreR = score(remote);

    if (local.skillId === remote.skillId) {
      const primary = scoreL > scoreR ? local : remote;
      const secondary = scoreL > scoreR ? remote : local;
      const targetCount = Math.max(1, Number(primary.targetCount) || Number(secondary.targetCount) || 5);
      const currentCount = Math.min(
        targetCount,
        Math.max(Number(local.currentCount) || 0, Number(remote.currentCount) || 0)
      );
      const completed = Boolean(local.completed || remote.completed || currentCount >= targetCount);
      return {
        ...secondary,
        ...primary,
        targetCount,
        currentCount,
        completed,
        completedAt: primary.completedAt || secondary.completedAt || null,
        rewardGranted: Boolean(local.rewardGranted || remote.rewardGranted),
        resetEpoch: ctx.epoch,
      };
    }

    if (scoreL !== scoreR) {
      return { ...(scoreL > scoreR ? local : remote), resetEpoch: ctx.epoch };
    }
    // 둘 다 아직 진행도 0인 초기 상태라면 클라우드 목표를 기준으로 수렴한다.
    return { ...remote, resetEpoch: ctx.epoch };
  }

  function mergeMathStreakPayload(local, remote) {
    const valid = (s) => isPlainObject(s)
      && s.schemaVersion === 1
      && typeof s.lastObservedDate === 'string';
    const vL = valid(local);
    const vR = valid(remote);
    if (!vL && !vR) return isPlainObject(remote) ? remote : (isPlainObject(local) ? local : {});
    if (!vL) return remote;
    if (!vR) return local;

    const emptyL = (Number(local.currentStreak) || 0) === 0 && !local.lastCompletedDate;
    const emptyR = (Number(remote.currentStreak) || 0) === 0 && !remote.lastCompletedDate;
    if (emptyL !== emptyR) {
      return emptyL ? remote : local;
    }
    const compL = local.lastCompletedDate || '';
    const compR = remote.lastCompletedDate || '';
    if (compL !== compR) {
      return compL > compR ? local : remote;
    }
    if (local.lastObservedDate !== remote.lastObservedDate) {
      return local.lastObservedDate > remote.lastObservedDate ? local : remote;
    }
    return (Number(local.currentStreak) || 0) >= (Number(remote.currentStreak) || 0) ? local : remote;
  }

  function mergeMathGoalPreferencePayload(local, remote) {
    const valid = (p) => isPlainObject(p) && typeof p.presetId === 'string';
    if (!valid(local)) return isPlainObject(remote) ? remote : {};
    if (!valid(remote)) return local;
    const timeL = local.updatedAt ? Date.parse(local.updatedAt) || 0 : 0;
    const timeR = remote.updatedAt ? Date.parse(remote.updatedAt) || 0 : 0;
    return timeL > timeR ? local : remote;
  }

  function mergeMathEvidencePayload(local, remote) {
    const itemsL = isPlainObject(local) && Array.isArray(local.items) ? local.items : [];
    const itemsR = isPlainObject(remote) && Array.isArray(remote.items) ? remote.items : [];
    const byId = new Map();
    for (const item of [...itemsR, ...itemsL]) {
      if (!isPlainObject(item) || typeof item.id !== 'string' || !item.id) continue;
      if (!byId.has(item.id)) byId.set(item.id, item);
    }
    const mergedItems = Array.from(byId.values())
      .sort((a, b) => (Number(a.timestamp) || 0) - (Number(b.timestamp) || 0))
      .slice(-500);
    return {
      schemaVersion: 1,
      items: mergedItems,
    };
  }

  function mergeDailyStreakPayload(local, remote) {
    const ctx = activeRewardEpochContext();
    const sanitizeStreak = (s) => {
      if (!isPlainObject(s)) return {};
      if ((Number(s.resetEpoch) || 0) < ctx.epoch) {
        return {
          ...s,
          todayRecorded: false,
          gemAwarded: {},
          resetEpoch: ctx.epoch,
        };
      }
      return s;
    };
    const L = sanitizeStreak(local);
    const R = sanitizeStreak(remote);
    const history = { ...(isPlainObject(R.history) ? R.history : {}) };
    if (isPlainObject(L.history)) {
      for (const [d, cnt] of Object.entries(L.history)) {
        history[d] = Math.max(Number(history[d]) || 0, Number(cnt) || 0);
      }
    }
    const gemAwarded = { ...(isPlainObject(R.gemAwarded) ? R.gemAwarded : {}) };
    if (isPlainObject(L.gemAwarded)) {
      for (const [d, granted] of Object.entries(L.gemAwarded)) {
        if (granted) gemAwarded[d] = true;
      }
    }
    const dateL = typeof L.lastActiveDate === 'string' ? L.lastActiveDate : '';
    const dateR = typeof R.lastActiveDate === 'string' ? R.lastActiveDate : '';
    const lastActiveDate = (dateL >= dateR ? dateL : dateR) || null;
    let currentStreak = 0;
    if (dateL && dateL === dateR) {
      currentStreak = Math.max(Number(L.currentStreak) || 0, Number(R.currentStreak) || 0);
    } else if (dateL > dateR) {
      currentStreak = Number(L.currentStreak) || 0;
    } else {
      currentStreak = Number(R.currentStreak) || 0;
    }
    const todayRecorded = dateL === dateR
      ? Boolean(L.todayRecorded || R.todayRecorded)
      : Boolean((dateL > dateR ? L : R).todayRecorded);
    return {
      currentStreak,
      lastActiveDate,
      todayRecorded,
      gemAwarded,
      history,
      resetEpoch: ctx.epoch,
    };
  }

  function mergeDiversityPayload(local, remote) {
    const ctx = activeRewardEpochContext();
    const sanitizeDiv = (d) => {
      if (!isPlainObject(d)) return {};
      if ((Number(d.resetEpoch) || 0) < ctx.epoch) {
        return {
          today: d.today || null,
          subjectsWithCorrect: [],
          gemAwarded: false,
          resetEpoch: ctx.epoch,
        };
      }
      return d;
    };
    const L = sanitizeDiv(local);
    const R = sanitizeDiv(remote);
    const dayL = typeof L.today === 'string' ? L.today : '';
    const dayR = typeof R.today === 'string' ? R.today : '';
    if (dayL !== dayR) {
      return { ...(dayL > dayR ? L : R), resetEpoch: ctx.epoch };
    }
    const subjects = Array.from(new Set([
      ...(Array.isArray(R.subjectsWithCorrect) ? R.subjectsWithCorrect : []),
      ...(Array.isArray(L.subjectsWithCorrect) ? L.subjectsWithCorrect : []),
    ]));
    return {
      today: dayR || dayL || null,
      subjectsWithCorrect: subjects,
      gemAwarded: Boolean(L.gemAwarded || R.gemAwarded),
      resetEpoch: ctx.epoch,
    };
  }

  function mergeMilestonesPayload(local, remote) {
    const ctx = activeRewardEpochContext();
    const sanitizeMile = (m) => {
      if (!isPlainObject(m)) return {};
      if ((Number(m.resetEpoch) || 0) < ctx.epoch) {
        return {
          ...m,
          achieved: {},
          session: { rocketStreak: 0, milestoneStreak: 0, sessionCorrect: 0 },
          resetEpoch: ctx.epoch,
        };
      }
      return m;
    };
    const L = sanitizeMile(local);
    const R = sanitizeMile(remote);
    const achieved = { ...(isPlainObject(R.achieved) ? R.achieved : {}) };
    if (isPlainObject(L.achieved)) {
      for (const [k, v] of Object.entries(L.achieved)) {
        if (v) achieved[k] = true;
      }
    }
    const lifeL = isPlainObject(L.lifetime) ? L.lifetime : {};
    const lifeR = isPlainObject(R.lifetime) ? R.lifetime : {};
    const subjectsCompleted = Array.from(new Set([
      ...(Array.isArray(lifeR.subjectsCompleted) ? lifeR.subjectsCompleted : []),
      ...(Array.isArray(lifeL.subjectsCompleted) ? lifeL.subjectsCompleted : []),
    ]));
    return {
      achieved,
      session: isPlainObject(L.session)
        ? L.session
        : (isPlainObject(R.session) ? R.session : { correctCount: 0, consecutiveCorrect: 0 }),
      lifetime: {
        totalCorrect: Math.max(Number(lifeL.totalCorrect) || 0, Number(lifeR.totalCorrect) || 0),
        totalRockets: Math.max(Number(lifeL.totalRockets) || 0, Number(lifeR.totalRockets) || 0),
        subjectsCompleted,
      },
      resetEpoch: ctx.epoch,
    };
  }

  const DOMAIN_MERGERS = {
    study_rewards: mergeStudyRewardsPayload,
    study_youtube_free_time_session_v1: mergeFreeTimeSessionPayload,
    study_youtube_free_time_daily_usage_v1: mergeFreeTimeUsagePayload,
    aiden_math_daily_goal_v1: mergeMathDailyGoalPayload,
    aiden_math_streak_v1: mergeMathStreakPayload,
    aiden_math_goal_preference_v1: mergeMathGoalPreferencePayload,
    aiden_math_learning_evidence_v1: mergeMathEvidencePayload,
    aiden_daily_streak: mergeDailyStreakPayload,
    aiden_diversity: mergeDiversityPayload,
    aiden_milestones: mergeMilestonesPayload,
  };

  /** 병합된 보상 상태가 클라우드 행과 다른 사실(새 epoch·이벤트·영수증·치유된 잔액·메타)을 담고 있는지 확인한다. */
  function hasMoreRewardFacts(merged, remote, localTime = 0, dbTime = 0) {
    if (!merged || !remote) return true;
    const remoteLedger = isPlainObject(remote.reward_ledger) ? remote.reward_ledger : null;
    if (!remoteLedger || Number(remoteLedger.v) !== 1 || !Array.isArray(remoteLedger.events)) {
      return true;
    }
    const mergedEpoch = Number(merged.reward_ledger?.reset_epoch) || 1;
    const remoteEpoch = Number(remoteLedger.reset_epoch) || 0;
    if (mergedEpoch !== remoteEpoch) {
      return true;
    }
    const mergedResetCount = Array.isArray(merged.reward_ledger?.reset_history)
      ? merged.reward_ledger.reset_history.length
      : 0;
    const remoteResetCount = Array.isArray(remoteLedger.reset_history)
      ? remoteLedger.reset_history.length
      : 0;
    if (mergedResetCount > remoteResetCount) {
      return true;
    }
    if (remoteLedger.events.some((ev) => ev && ev.reason === 'legacy_snapshot_downward')) {
      return true;
    }
    const mergedEvents = Array.isArray(merged.reward_ledger?.events)
      ? merged.reward_ledger.events
      : [];
    const remoteEventIds = new Set(remoteLedger.events.map((ev) => ev && ev.id).filter(Boolean));
    for (const ev of mergedEvents) {
      if (ev && ev.id && !remoteEventIds.has(ev.id)) return true;
    }
    const mergedReceipts = Object.keys(merged.claimed_receipts || {});
    const remoteReceipts = new Set(Object.keys(remote.claimed_receipts || {}));
    for (const rId of mergedReceipts) {
      if (!remoteReceipts.has(rId)) return true;
    }
    for (const k of ['gems', 'youtube_minutes', 'snacks', 'marble_plays', 'bubble_plays']) {
      if ((Number(merged[k]) || 0) !== (Number(remote[k]) || 0)) return true;
    }
    if (
      JSON.stringify(merged.custom_inventory || {})
      !== JSON.stringify(remote.custom_inventory || {})
    ) {
      return true;
    }
    if (localTime > dbTime) {
      if (JSON.stringify(merged.shop_items || []) !== JSON.stringify(remote.shop_items || [])) {
        return true;
      }
      if ((merged.theme || 'modern') !== (remote.theme || 'modern')) {
        return true;
      }
    }
    return false;
  }

  function hasMeaningfulLocalData(key, parsed) {
    if (!isPlainObject(parsed)) return false;
    if (key === 'study_rewards') {
      for (const k of ['gems', 'youtube_minutes', 'snacks', 'marble_plays', 'bubble_plays']) {
        if ((Number(parsed[k]) || 0) > 0) return true;
      }
      if (
        isPlainObject(parsed.custom_inventory)
        && Object.values(parsed.custom_inventory).some((v) => (Number(v) || 0) > 0)
      ) {
        return true;
      }
      if (Array.isArray(parsed.reward_ledger?.events) && parsed.reward_ledger.events.length > 0) {
        return true;
      }
      if ((Number(parsed.reward_ledger?.reset_epoch) || 0) > 1) {
        return true;
      }
      if (Array.isArray(parsed.reward_ledger?.reset_history) && parsed.reward_ledger.reset_history.length > 0) {
        return true;
      }
      if (Object.keys(parsed.claimed_receipts || {}).length > 0) return true;
      if (Array.isArray(parsed.shop_items) && parsed.shop_items.length > 4) return true;
      if (parsed.theme && parsed.theme !== 'modern') return true;
      return false;
    }
    if (key === 'study_youtube_free_time_session_v1') {
      return Boolean(parsed.sessionId && (parsed.status === 'running' || parsed.status === 'expired'));
    }
    if (key === 'study_youtube_free_time_daily_usage_v1') {
      return (Number(parsed.morningMinutes) || 0) > 0 || (Number(parsed.afternoonMinutes) || 0) > 0;
    }
    if (key === 'aiden_math_daily_goal_v1') {
      return Boolean((Number(parsed.currentCount) || 0) > 0 || parsed.completed || parsed.rewardGranted);
    }
    if (key === 'aiden_math_streak_v1') {
      return Boolean((Number(parsed.currentStreak) || 0) > 0 || parsed.lastCompletedDate);
    }
    if (key === 'aiden_math_goal_preference_v1') {
      return Boolean(parsed.updatedAt);
    }
    if (key === 'aiden_math_learning_evidence_v1') {
      return Array.isArray(parsed.items) && parsed.items.length > 0;
    }
    if (key === 'aiden_daily_streak') {
      return Boolean((Number(parsed.currentStreak) || 0) > 0 || Object.keys(parsed.history || {}).length > 0);
    }
    if (key === 'aiden_diversity') {
      return Array.isArray(parsed.subjectsWithCorrect) && parsed.subjectsWithCorrect.length > 0;
    }
    if (key === 'aiden_milestones') {
      return Boolean(
        (Number(parsed.lifetime?.totalCorrect) || 0) > 0
        || Object.values(parsed.achieved || {}).some(Boolean)
      );
    }
    if (CANONICAL_STATS_KEYS.includes(key)) {
      for (const dom of Object.values(parsed)) {
        if (!isPlainObject(dom) || !isPlainObject(dom.levels)) continue;
        for (const lv of Object.values(dom.levels)) {
          if ((Number(lv && lv.attempts) || 0) > 0) return true;
        }
      }
      return false;
    }
    return false;
  }

  // ── 2. Supabase Push / Queue / Pull ─────────────────────────

  async function pushToSupabase(key, payload, options) {
    const opts = isPlainObject(options) ? options : {};
    const user = window.Auth?.getUser();
    if (!user || !window.supabaseClient) return false;
    // Never push server-authoritative keys
    if (SERVER_AUTHORITATIVE_KEYS.has(key)) return false;

    try {
      let payloadToSend = payload;
      const merger = DOMAIN_MERGERS[key];

      // 단독 푸시 시 클라우드의 다른 기기 변경을 덮어쓰지 않도록 사전 조회 후 병합한다.
      if (merger && !opts.skipRemoteMerge) {
        try {
          const { data: existingRows, error: readErr } = await window.supabaseClient
            .from('user_data')
            .select('data_key, payload, updated_at')
            .eq('user_id', user.id)
            .in('data_key', [key]);
          if (
            !readErr
            && Array.isArray(existingRows)
            && existingRows.length > 0
            && existingRows[0]
            && existingRows[0].payload
          ) {
            payloadToSend = merger(payload || {}, existingRows[0].payload);
            const mergedJson = JSON.stringify(payloadToSend);
            if (mergedJson !== localStorage.getItem(key)) {
              if (key === 'study_rewards') {
                persistRewardsLocally(payloadToSend);
              } else {
                localStorage.setItem(key, mergedJson);
              }
              window.dispatchEvent(createDomEvent('cloud-sync-complete'));
            }
          }
        } catch (preMergeErr) {
          console.warn('[SyncEngine] Pre-push merge skipped:', preMergeErr);
        }
      }

      const { error } = await window.supabaseClient
        .from('user_data')
        .upsert(
          {
            user_id: user.id,
            data_key: key,
            payload: payloadToSend,
            updated_at: new Date().toISOString(),
          },
          { onConflict: 'user_id, data_key' }
        );
      if (error) {
        console.error('Supabase Upsert Error:', error);
        return false;
      }
      return true;
    } catch (e) {
      console.error('Network Error during sync:', e);
      return false;
    }
  }

  async function flushQueue(options) {
    const opts = isPlainObject(options) ? options : {};
    if (!isOnline() || !window.Auth?.getUser()) return;
    const q = getQueue();
    const keys = Object.keys(q);
    if (keys.length === 0) return;

    for (const key of keys) {
      // Never push server-authoritative keys
      if (SERVER_AUTHORITATIVE_KEYS.has(key)) {
        delete q[key];
        setQueue(q);
        continue;
      }
      const skipRemoteMerge = Boolean(opts.alreadyMergedKeys && opts.alreadyMergedKeys.has(key));
      const success = await pushToSupabase(key, q[key], { skipRemoteMerge });
      if (success) {
        delete q[key];
        setQueue(q);
      }
    }
  }

  async function pullAndMerge(keysToPull = DEFAULT_PULL_KEYS) {
    const user = window.Auth?.getUser();
    if (!user || !window.supabaseClient || !isOnline()) return;
    if (!keysToPull || keysToPull.length === 0) return;

    const switchedAccount = ensureAccountStorageScope(user.id);

    try {
      const { data, error } = await window.supabaseClient
        .from('user_data')
        .select('data_key, payload, updated_at')
        .eq('user_id', user.id)
        .in('data_key', keysToPull);

      if (error) {
        console.error('Pull Error:', error);
        return;
      }

      const rows = normalizePulledRows(data).slice().sort((a, b) => {
        const aKey = a && a.data_key;
        const bKey = b && b.data_key;
        if (aKey === bKey) return 0;
        if (aKey === 'study_rewards') return -1;
        if (bKey === 'study_rewards') return 1;
        return 0;
      });
      const rowMap = new Map(rows.map((r) => [r.data_key, r]));
      const handledTargetKeys = new Set(rowMap.keys());
      const q = getQueue();
      let queueMutated = false;
      let updatedAny = switchedAccount;

      for (const row of rows) {
        if (!row || !row.data_key) continue;

        // Server-authoritative keys: always overwrite local without timestamp contest
        if (SERVER_AUTHORITATIVE_KEYS.has(row.data_key)) {
          handledTargetKeys.add(row.data_key);
          if (row.data_key === 'aiden_canonical_weekly_vocabulary_v1') {
            const prevStr = localStorage.getItem(row.data_key);
            const nextStr = JSON.stringify(row.payload);
            if (prevStr !== nextStr) {
              localStorage.setItem(row.data_key, nextStr);
              updatedAny = true;
            }
            if (window.WeeklyVocabularyStore && typeof window.WeeklyVocabularyStore.toLegacyProjection === 'function') {
              try {
                const legacyProj = window.WeeklyVocabularyStore.toLegacyProjection(row.payload);
                localStorage.setItem('englishWeeklyWords', JSON.stringify(legacyProj));
              } catch (e) {}
            } else if (row.payload && Array.isArray(row.payload.items)) {
              try {
                const legacyProj = row.payload.items.map((it) => ({
                  en: it.word || it.answer,
                  ko: it.ko || '',
                  icon: it.icon || '',
                }));
                localStorage.setItem('englishWeeklyWords', JSON.stringify(legacyProj));
              } catch (e) {}
            }
            window.dispatchEvent(createDomEvent('weekly-vocabulary-synced', { source: 'cloud-pull', payload: row.payload }));
          }
          if (Object.prototype.hasOwnProperty.call(q, row.data_key)) {
            delete q[row.data_key];
            queueMutated = true;
          }
          // Never push server-authoritative keys back to cloud via LWW
          continue;
        }

        const targetKey = LEGACY_STATS_KEY_MAP[row.data_key] || row.data_key;
        const isLegacyMigration = targetKey !== row.data_key;

        // 레거시 통계 키는 정식 키 행이 서버에 없을 때만 마이그레이션한다.
        if (isLegacyMigration && rowMap.has(targetKey)) {
          continue;
        }
        handledTargetKeys.add(targetKey);

        const localRaw = localStorage.getItem(targetKey);
        const dbTime = (row.payload && row.payload._updated_at)
          || (row.payload && row.payload.updatedAt ? new Date(row.payload.updatedAt).getTime() : 0)
          || (row.updated_at ? new Date(row.updated_at).getTime() : 0);

        // study_rewards는 이벤트 원장(RewardLedger) 기반 합집합 병합으로 처리한다.
        if (targetKey === 'study_rewards') {
          let localParsed = safeParseJson(localRaw, null);
          if (q.study_rewards && isPlainObject(q.study_rewards)) {
            localParsed = localParsed
              ? mergeStudyRewardsPayload(localParsed, q.study_rewards)
              : q.study_rewards;
          }
          const localTime = Number(localParsed && localParsed._updated_at) || 0;
          const localEpochBefore = Number(localParsed && localParsed.reward_ledger && localParsed.reward_ledger.reset_epoch) || 0;
          const mergedRewards = mergeStudyRewardsPayload(localParsed || {}, row.payload);
          const mergedEpoch = Number(mergedRewards && mergedRewards.reward_ledger && mergedRewards.reward_ledger.reset_epoch) || 1;
          const nextStr = JSON.stringify(mergedRewards);
          if (localRaw !== nextStr) {
            persistRewardsLocally(mergedRewards);
            updatedAny = true;
          }
          if (mergedEpoch > localEpochBefore && window.RewardSystem && typeof window.RewardSystem.syncCompanionEpoch === 'function') {
            window.RewardSystem.syncCompanionEpoch(mergedEpoch, { pushCompanion: false });
          }
          const shouldPushMerged = hasMoreRewardFacts(
            mergedRewards,
            row.payload,
            localTime,
            dbTime
          );
          if (Object.prototype.hasOwnProperty.call(q, 'study_rewards')) {
            delete q.study_rewards;
            queueMutated = true;
          }
          if (shouldPushMerged) {
            const ok = await pushToSupabase('study_rewards', mergedRewards, { skipRemoteMerge: true });
            if (!ok) {
              q.study_rewards = mergedRewards;
              queueMutated = true;
            }
          }
          continue;
        }

        // 상단 자유시간 세션/쿼터·수학 오늘의 목표/스트릭·공통 보상 트래커는 의미 기반 병합으로 처리한다.
        const merger = DOMAIN_MERGERS[targetKey];
        if (merger) {
          let localParsed = safeParseJson(localRaw, null);
          if (q[targetKey] && isPlainObject(q[targetKey])) {
            localParsed = localParsed ? merger(localParsed, q[targetKey]) : q[targetKey];
          }
          const mergedVal = merger(localParsed || {}, row.payload);
          const nextStr = JSON.stringify(mergedVal);
          const remoteStr = JSON.stringify(row.payload);
          if (localRaw !== nextStr) {
            localStorage.setItem(targetKey, nextStr);
            updatedAny = true;
          }
          if (Object.prototype.hasOwnProperty.call(q, targetKey)) {
            delete q[targetKey];
            queueMutated = true;
          }
          if (nextStr !== remoteStr) {
            const ok = await pushToSupabase(targetKey, mergedVal, { skipRemoteMerge: true });
            if (!ok) {
              q[targetKey] = mergedVal;
              queueMutated = true;
            }
          }
          continue;
        }

        // 나머지 키(과목별 누적 학습 통계 등)는 LWW + 레거시 정식 키 승격으로 처리한다.
        let localTime = 0;
        if (localRaw) {
          const parsed = safeParseJson(localRaw, null);
          if (parsed && parsed._updated_at) localTime = parsed._updated_at;
        }

        if (!localRaw || dbTime > localTime) {
          localStorage.setItem(targetKey, JSON.stringify(row.payload));
          updatedAny = true;
          if (Object.prototype.hasOwnProperty.call(q, targetKey)) {
            delete q[targetKey];
            queueMutated = true;
          }
          if (isLegacyMigration) {
            await pushToSupabase(targetKey, row.payload, { skipRemoteMerge: true });
          }
        } else if (localTime > dbTime) {
          const localParsed = safeParseJson(localRaw, null);
          if (localParsed) {
            await pushToSupabase(targetKey, localParsed, { skipRemoteMerge: true });
          }
        } else if (isLegacyMigration && localRaw) {
          const localParsed = safeParseJson(localRaw, null);
          if (localParsed) {
            await pushToSupabase(targetKey, localParsed, { skipRemoteMerge: true });
          }
        }
      }

      // 클라우드에 아직 행이 없지만 이 기기 로컬에는 실제 보상·목표·학습 기록이 있는 경우 초기 시드 업로드!
      for (const reqKey of keysToPull) {
        if (SERVER_AUTHORITATIVE_KEYS.has(reqKey)) continue;
        if (LEGACY_STATS_KEY_MAP[reqKey]) continue;
        if (handledTargetKeys.has(reqKey)) continue;
        if (Object.prototype.hasOwnProperty.call(q, reqKey)) continue;

        const localRaw = localStorage.getItem(reqKey);
        if (!localRaw) continue;
        const localParsed = safeParseJson(localRaw, null);
        if (!hasMeaningfulLocalData(reqKey, localParsed)) continue;

        let payloadToSeed = localParsed;
        if (reqKey === 'study_rewards' && window.RewardLedger) {
          payloadToSeed = window.RewardLedger.normalizeState(localParsed, { adoptFields: true });
          persistRewardsLocally(payloadToSeed);
        }
        const ok = await pushToSupabase(reqKey, payloadToSeed, { skipRemoteMerge: true });
        if (!ok) {
          q[reqKey] = payloadToSeed;
          queueMutated = true;
        }
      }

      if (queueMutated) {
        setQueue(q);
      }

      if (updatedAny) {
        window.dispatchEvent(createDomEvent('cloud-sync-complete'));
      }
    } catch (e) {
      console.error('Pull Error', e);
    }
  }

  /**
   * 즉시 전체 동기화 수행 (pull-merge 먼저 수행 후 남은 큐 flush)
   * 동시 호출 시 누락 없이 후속 1회 동기화로 합쳐 수렴을 보장한다.
   */
  async function syncNow(reason = 'manual') {
    if (_syncInProgress) {
      _pendingSyncReason = reason;
      return _activeSyncPromise || Promise.resolve(false);
    }
    if (!isOnline() || !window.Auth?.getUser()) return false;

    _syncInProgress = true;
    _activeSyncPromise = (async () => {
      let currentReason = reason;
      try {
        while (currentReason) {
          _pendingSyncReason = null;
          await pullAndMerge(DEFAULT_PULL_KEYS);
          await flushQueue({ alreadyMergedKeys: new Set(DEFAULT_PULL_KEYS) });
          _lastSyncAt = Date.now();
          _notifyOtherTabs(currentReason);
          currentReason = _pendingSyncReason;
          if (!isOnline() || !window.Auth?.getUser()) break;
        }
        return true;
      } catch (e) {
        console.error(`[SyncEngine] Sync failed (${currentReason}):`, e);
        return false;
      } finally {
        _syncInProgress = false;
        _pendingSyncReason = null;
        _activeSyncPromise = null;
      }
    })();

    return _activeSyncPromise;
  }

  function _notifyOtherTabs(reason) {
    try {
      const payload = JSON.stringify({
        ts: Date.now(),
        reason,
        tabId: Math.random().toString(36).slice(2, 8),
      });
      localStorage.setItem(SYNC_EVENT_KEY, payload);
    } catch (e) {
      // localStorage 에러 무시 (용량 초과 등)
    }
  }

  function _startPeriodicSync() {
    if (_syncIntervalId || typeof setInterval !== 'function') return;
    _syncIntervalId = setInterval(() => {
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
        return;
      }
      if (isOnline() && window.Auth?.getUser()) {
        syncNow('periodic');
      }
    }, PERIODIC_INTERVAL_MS);
  }

  function _stopPeriodicSync() {
    if (_syncIntervalId) {
      if (typeof clearInterval === 'function') {
        clearInterval(_syncIntervalId);
      }
      _syncIntervalId = null;
    }
  }

  function _onFocusOrVisible(source = 'visibility') {
    if (typeof document !== 'undefined' && source === 'visibility' && document.visibilityState !== 'visible') {
      return;
    }
    const elapsed = Date.now() - _lastSyncAt;
    if (elapsed > FOCUS_COOLDOWN_MS && isOnline() && window.Auth?.getUser()) {
      syncNow(source);
    }
  }

  function _onStorageChange(e) {
    if (!e || e.key !== SYNC_EVENT_KEY || !e.newValue) return;
    window.dispatchEvent(createDomEvent('cloud-sync-complete'));
  }

  function _bootstrapIfAlreadyReady() {
    if (!window.Auth || typeof window.Auth.whenReady !== 'function') return;
    Promise.resolve(window.Auth.whenReady())
      .then(() => {
        if (window.Auth?.getUser() && _lastSyncAt === 0 && !_syncInProgress) {
          _startPeriodicSync();
          syncNow('auth-ready-bootstrap');
        }
      })
      .catch(() => {});
  }

  function _init() {
    if (typeof document !== 'undefined' && typeof document.addEventListener === 'function') {
      document.addEventListener('visibilitychange', () => _onFocusOrVisible('visibility'));
    }
    window.addEventListener('focus', () => _onFocusOrVisible('focus'));
    window.addEventListener('pageshow', () => _onFocusOrVisible('pageshow'));
    window.addEventListener('storage', _onStorageChange);
    window.addEventListener('online', () => {
      if (window.Auth?.getUser()) {
        syncNow('online');
      } else {
        flushQueue();
      }
    });

    window.addEventListener('auth-changed', (e) => {
      const user = e && e.detail ? e.detail.user : window.Auth?.getUser();
      if (user) {
        _startPeriodicSync();
        syncNow('auth-changed');
      } else {
        _stopPeriodicSync();
      }
    });

    _bootstrapIfAlreadyReady();
  }

  const SyncEngine = {
    pushStats(key, statsObj) {
      // Never push server-authoritative keys via client queue
      if (SERVER_AUTHORITATIVE_KEYS.has(key)) return;
      const q = getQueue();
      const payload = { ...statsObj, _updated_at: Date.now() };
      q[key] = payload;
      setQueue(q);

      if (isOnline()) {
        flushQueue();
      }
    },

    pullAndMerge,
    flushQueue,
    getQueue,
    syncNow,
    mergeStudyRewardsPayload,
    getLastSyncAt: () => _lastSyncAt,
    isSyncInProgress: () => _syncInProgress,
  };

  window.SyncEngine = SyncEngine;

  if (typeof document !== 'undefined' && document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _init);
  } else {
    _init();
  }
})();
