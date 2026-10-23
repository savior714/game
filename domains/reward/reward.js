/* ═══════════════════════════════════
   전역 보상 인벤토리 시스템 (Reward System Core)
   - localStorage 기반 상태 관리
   - 핵심 비즈니스 로직 (보석 획득, 아이템 교환 등)
   - UI 처리는 reward_ui.js에 위임
   - 2026-03-28: 퇴장 가드 제거 및 UI 분산 리팩토링
   - 2026-10-22: 보상 원장(RewardLedger) 도입
     · 획득/사용을 델타 이벤트로 기록하고, 저장 직전 항상 디스크 원장과 병합한다.
     · 다른 탭·기기·클라우드의 오래된 스냅샷이 이미 사용한 보상을 되살리지 못한다.
   ═══════════════════════════════════ */

const RewardSystem = (() => {
  const STORAGE_KEY = 'study_rewards';
  // 원장 복구 저널: study_rewards가 구버전/외부 스냅샷으로 통째로 덮여도
  // 획득·사용 이벤트를 되살려 "사용한 보상이 다시 채워지는" 일을 막는다.
  const LEDGER_JOURNAL_KEY = 'study_rewards_ledger_v1';
  const initialState = {
    gems: 0,
    youtube_minutes: 0,
    snacks: 0,
    marble_plays: 0,
    bubble_plays: 0,
    shop_items: [
      { id: 'youtube', icon: '📺', label: '유튜브 10분', desc: '좋아하는 영상 시청', price: 1 },
      { id: 'snack', icon: '🍪', label: '간식 1개', desc: '맛있는 간식 시간', price: 1 },
      { id: 'marble', icon: '🎮', label: '마블 게임', desc: '마블 한 판 더!', price: 1 },
      { id: 'bubble', icon: '🫧', label: '비눗방울 게임', desc: '버블팡 한 판 더!', price: 1 }
    ],
    custom_inventory: {},
    claimed_receipts: {},
    theme: 'modern',
    last_updated: new Date().toISOString()
  };

  let state = { ...initialState };
  let storageListenerBound = false;

  // ──────────────────────────────────────────
  // 1. 상태 관리 (State Management)
  // ──────────────────────────────────────────
  function ledger() {
    if (typeof RewardLedger !== 'undefined' && RewardLedger &&
      typeof RewardLedger.normalizeState === 'function') return RewardLedger;
    if (typeof window !== 'undefined' && window && window.RewardLedger &&
      typeof window.RewardLedger.normalizeState === 'function') return window.RewardLedger;
    return null;
  }

  function ensureDefaultShopItems(targetState) {
    if (!targetState.shop_items || !Array.isArray(targetState.shop_items)) {
      targetState.shop_items = [...initialState.shop_items];
      return;
    }
    initialState.shop_items.forEach(defaultItem => {
      if (!targetState.shop_items.some(item => item.id === defaultItem.id)) {
        targetState.shop_items.push({ ...defaultItem });
      }
    });
  }

  function applyStateDefaults(targetState) {
    ensureDefaultShopItems(targetState);
    if (!targetState.custom_inventory || typeof targetState.custom_inventory !== 'object') {
      targetState.custom_inventory = {};
    }
    if (!targetState.claimed_receipts || typeof targetState.claimed_receipts !== 'object') {
      targetState.claimed_receipts = {};
    }
    return targetState;
  }

  /** 원장이 없는 상태(구버전/외부 쓰기)를 현재 계약으로 정규화한다. */
  function legacyNormalizeState(raw) {
    const next = { ...initialState, ...(raw && typeof raw === 'object' ? raw : {}) };
    applyStateDefaults(next);
    next.gems = Number.isFinite(Number(next.gems)) ? Number(next.gems) : 0;
    next.youtube_minutes = Number.isFinite(Number(next.youtube_minutes)) ? Number(next.youtube_minutes) : 0;
    // 10분권 단위가 아닌 찌꺼기(예: 5분)는 타이머/소진 로직에서 사용할 수 없어 고착된다. 로드 시 자동 정규화.
    if (next.youtube_minutes % 10 !== 0) {
      const normalized = Math.max(0, Math.floor(next.youtube_minutes / 10) * 10);
      console.warn('[RewardSystem] normalizing stray youtube_minutes', next.youtube_minutes, '→', normalized);
      next.youtube_minutes = normalized;
    }
    next.snacks = Number.isFinite(Number(next.snacks)) ? Number(next.snacks) : 0;
    next.marble_plays = Number.isFinite(Number(next.marble_plays)) ? Number(next.marble_plays) : 0;
    next.bubble_plays = Number.isFinite(Number(next.bubble_plays)) ? Number(next.bubble_plays) : 0;
    return next;
  }

  function normalizeRewardState(raw, options) {
    const L = ledger();
    if (!L) return legacyNormalizeState(raw);
    const normalized = L.normalizeState(raw || {}, options);
    return applyStateDefaults(normalized);
  }

  function parseStorage() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) return null;
    try {
      const parsed = JSON.parse(saved);
      return parsed && typeof parsed === 'object' ? parsed : null;
    } catch (e) {
      console.error('RewardSystem load failed:', e);
      return null;
    }
  }

  function balanceSnapshot(target) {
    const L = ledger();
    if (L) return L.balanceSnapshot(target);
    return {
      gems: Number(target.gems) || 0,
      youtube_minutes: Number(target.youtube_minutes) || 0,
      snacks: Number(target.snacks) || 0,
      marble_plays: Number(target.marble_plays) || 0,
      bubble_plays: Number(target.bubble_plays) || 0,
      custom_inventory: { ...(target.custom_inventory || {}) }
    };
  }

  function readLedgerJournal() {
    const L = ledger();
    if (!L) return null;
    const raw = localStorage.getItem(LEDGER_JOURNAL_KEY);
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== 'object' || Number(parsed.v) !== 1) return null;
      return parsed;
    } catch (e) {
      console.warn('[RewardSystem] reward ledger journal is unreadable:', e);
      return null;
    }
  }

  function localDateKey(ms) {
    const d = new Date(Number.isFinite(ms) ? ms : Date.now());
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  }

  /**
   * 보상 초기화 기준점(`targetEpoch`) 이전의 부속 보상 상태(진행 중/만료 자유시간 세션, 일일 사용량,
   * 일일 목표 수령 플래그, 출석/다양성/마일스톤 보석 지급 플래그, 로컬 영수증 키)를 일괄 초기화한다.
   */
  function syncCompanionEpoch(targetEpoch, options) {
    const epoch = Math.max(1, Math.trunc(Number(targetEpoch) || 1));
    const opts = options && typeof options === 'object' ? options : {};
    const nowTs = Number.isFinite(Number(opts.now)) ? Number(opts.now) : Date.now();
    const force = Boolean(opts.force);
    const shouldPush = opts.pushCompanion !== false;

    const companionUpdates = [];
    const writeCompanion = (key, nextObj) => {
      try {
        localStorage.setItem(key, JSON.stringify(nextObj));
        companionUpdates.push([key, nextObj]);
      } catch (e) {
        console.warn('[RewardSystem] companion epoch write failed:', key, e);
      }
    };

    try {
      const rawSession = localStorage.getItem('study_youtube_free_time_session_v1');
      if (rawSession || force) {
        let parsedSession = null;
        try { parsedSession = rawSession ? JSON.parse(rawSession) : null; } catch (_e) { parsedSession = null; }
        if (force || !parsedSession || (Number(parsedSession.resetEpoch) || 0) < epoch) {
          writeCompanion('study_youtube_free_time_session_v1', {
            schemaVersion: 1,
            status: 'inactive',
            sessionId: null,
            resetEpoch: epoch,
            resetAt: nowTs,
          });
        }
      }

      const rawUsage = localStorage.getItem('study_youtube_free_time_daily_usage_v1');
      if (rawUsage || force) {
        let parsedUsage = null;
        try { parsedUsage = rawUsage ? JSON.parse(rawUsage) : null; } catch (_e) { parsedUsage = null; }
        if (force || !parsedUsage || (Number(parsedUsage.resetEpoch) || 0) < epoch) {
          writeCompanion('study_youtube_free_time_daily_usage_v1', {
            schemaVersion: 1,
            dateKey: localDateKey(nowTs),
            morningMinutes: 0,
            afternoonMinutes: 0,
            resetEpoch: epoch,
          });
        }
      }

      if (typeof localStorage.removeItem === 'function') {
        try { localStorage.removeItem('study_youtube_free_time_start_tx_v1'); } catch (_e) {}
      }

      if (typeof localStorage.length === 'number' && typeof localStorage.key === 'function' && typeof localStorage.removeItem === 'function') {
        const receiptKeys = [];
        for (let i = 0; i < localStorage.length; i += 1) {
          const k = localStorage.key(i);
          if (k && k.startsWith('aiden_receipt_')) receiptKeys.push(k);
        }
        for (const rk of receiptKeys) {
          try { localStorage.removeItem(rk); } catch (_e) {}
        }
      }

      const rawGoal = localStorage.getItem('aiden_math_daily_goal_v1');
      if (rawGoal) {
        try {
          const goal = JSON.parse(rawGoal);
          if (goal && typeof goal === 'object' && (force || (Number(goal.resetEpoch) || 0) < epoch)) {
            writeCompanion('aiden_math_daily_goal_v1', {
              ...goal,
              currentCount: 0,
              completed: false,
              completedAt: null,
              rewardGranted: false,
              resetEpoch: epoch,
              lastUpdated: new Date(nowTs).toISOString(),
            });
          }
        } catch (_e) {}
      }

      const rawStreak = localStorage.getItem('aiden_daily_streak');
      if (rawStreak) {
        try {
          const streak = JSON.parse(rawStreak);
          if (streak && typeof streak === 'object' && (force || (Number(streak.resetEpoch) || 0) < epoch)) {
            writeCompanion('aiden_daily_streak', {
              ...streak,
              todayRecorded: false,
              gemAwarded: {},
              resetEpoch: epoch,
            });
          }
        } catch (_e) {}
      }

      const rawDiv = localStorage.getItem('aiden_diversity');
      if (rawDiv) {
        try {
          const div = JSON.parse(rawDiv);
          if (div && typeof div === 'object' && (force || (Number(div.resetEpoch) || 0) < epoch)) {
            writeCompanion('aiden_diversity', {
              ...div,
              subjectsWithCorrect: [],
              gemAwarded: false,
              resetEpoch: epoch,
            });
          }
        } catch (_e) {}
      }

      const rawMile = localStorage.getItem('aiden_milestones');
      if (rawMile) {
        try {
          const mile = JSON.parse(rawMile);
          if (mile && typeof mile === 'object' && (force || (Number(mile.resetEpoch) || 0) < epoch)) {
            writeCompanion('aiden_milestones', {
              ...mile,
              achieved: {},
              session: { rocketStreak: 0, milestoneStreak: 0, sessionCorrect: 0 },
              resetEpoch: epoch,
            });
          }
        } catch (_e) {}
      }
    } catch (e) {
      console.warn('[RewardSystem] syncCompanionEpoch partial failure:', e);
    }

    if (typeof DailyStreak !== 'undefined' && typeof DailyStreak.reload === 'function') {
      try { DailyStreak.reload(); } catch (_e) {}
    }
    if (typeof DiversityReward !== 'undefined' && typeof DiversityReward.reload === 'function') {
      try { DiversityReward.reload(); } catch (_e) {}
    }
    if (typeof MilestoneTracker !== 'undefined' && typeof MilestoneTracker.reload === 'function') {
      try { MilestoneTracker.reload(); } catch (_e) {}
    }

    if (shouldPush) {
      for (const [k, payload] of companionUpdates) {
        pushKeyToCloud(k, payload);
      }
    }
    reconcileFreeTimeSessionUI();
  }

  function load() {
    const parsed = parseStorage();
    const L = ledger();
    const prevMemoryEpoch = L && state ? L.getEpoch(state) : 0;
    const prevDiskEpoch = L && parsed ? L.getEpoch(parsed) : 0;
    let base = parsed || {};

    if (L && parsed) {
      const journal = readLedgerJournal();
      if (journal) {
        // 저장된 상태에 원장이 없거나(구버전 덮어쓰기) 일부 이벤트가 사라졌다면 저널과 합친다.
        base = { ...base, reward_ledger: L.mergeLedgers(journal, base.reward_ledger) };
      }
    } else if (L && !parsed) {
      // 저장 키 자체가 사라진 경우는 사용자가 의도적으로 비운 상태로 본다.
      // (저널로 되살리면 "초기화했는데 다시 돌아오는" 현상이 재발한다.)
      try {
        localStorage.removeItem(LEDGER_JOURNAL_KEY);
      } catch (e) {
        // ignore
      }
    }

    const nowTs = Date.now();
    const normalized = normalizeRewardState(base, { adoptFields: true, at: nowTs });
    state = normalized;

    const currentEpoch = L ? L.getEpoch(normalized) : 1;
    const epochCutoverOccurred = Boolean(
      L && (
        (parsed && prevDiskEpoch < currentEpoch)
        || (prevMemoryEpoch > 0 && prevMemoryEpoch < currentEpoch)
      )
    );
    if (epochCutoverOccurred) {
      syncCompanionEpoch(currentEpoch, { now: nowTs, pushCompanion: true });
    }

    // 다른 경로(자유시간 트랜잭션 등)가 저장한 원장도 저널에 반영해 복구 기준을 최신으로 유지한다.
    if (L && normalized.reward_ledger) {
      const journalRaw = localStorage.getItem(LEDGER_JOURNAL_KEY);
      const ledgerRaw = JSON.stringify(normalized.reward_ledger);
      if (journalRaw !== ledgerRaw) {
        try {
          localStorage.setItem(LEDGER_JOURNAL_KEY, ledgerRaw);
        } catch (e) {
          console.warn('[RewardSystem] reward ledger journal sync failed:', e);
        }
      }
    }

    // 이전 epoch 데이터 초기화 또는 스냅샷 정규화가 발생한 경우 즉시 영속화 + 클라우드 푸시한다.
    const hadCurrentEpochLedger = Boolean(
      parsed
      && parsed.reward_ledger
      && parsed.reward_ledger.v === 1
      && (!L || L.getEpoch(parsed) >= L.BASELINE_RESET_EPOCH)
    );
    const balancesChanged = parsed
      ? JSON.stringify(balanceSnapshot(parsed)) !== JSON.stringify(balanceSnapshot(normalized))
      : false;
    if (parsed && (!hadCurrentEpochLedger || balancesChanged)) {
      persist(normalized, { reason: 'epoch_cutover_migration' });
    }
  }

  const SYNC_QUEUE_KEY = 'sync_queue';

  /**
   * 보상 상태를 계정 단위 클라우드 동기화 큐에 기록한다.
   * SyncEngine이 아직 로드되지 않은 시점에서도 호출 가능하며,
   * SyncEngine 로드 후 인증·온라인 상태가 되면 flushQueue가 해당 큐를
   * Supabase public.user_data(user_id 기준)에 upsert 한다.
   * 이렇게 하면 태블릿·노트북 기기 간에 동일한 계정으로 로그인했을 때
   * 보상(보석·자유시간·간식·인벤토리)이 누락 없이 연동된다.
   */
  function _enqueueSyncQueue(key, payload) {
    if (!payload) return;
    if (!payload._updated_at) payload._updated_at = Date.now();
    try {
      let q = {};
      const raw = localStorage.getItem(SYNC_QUEUE_KEY);
      if (raw) {
        try {
          q = JSON.parse(raw);
          if (!q || typeof q !== 'object') q = {};
        } catch (e) {
          q = {};
        }
      }
      q[key] = payload;
      localStorage.setItem(SYNC_QUEUE_KEY, JSON.stringify(q));
    } catch (e) {
      console.warn('[RewardSystem] sync queue enqueue failed:', e);
    }
  }

  function pushKeyToCloud(key, payload) {
    if (!payload || typeof payload !== 'object') return;
    if (window.SyncEngine && typeof window.SyncEngine.pushStats === 'function') {
      window.SyncEngine.pushStats(key, payload);
    } else {
      _enqueueSyncQueue(key, payload);
    }
  }

  function pushToCloud() {
    // 보상 변경을 계정 단위 클라우드 DB(Supabase user_data)에 연동한다.
    // SyncEngine이 준비되어 있으면 즉시 푸시(온라인 + 로그인 시 Supabase upsert),
    // 아직 준비되지 않았어도 동기화 큐에 기록해 두고 SyncEngine 로드 후
    // 인증/온라인 복구 시 flush가 처리하게 한다.
    if (window.SyncEngine && typeof window.SyncEngine.pushStats === 'function') {
      window.SyncEngine.pushStats(STORAGE_KEY, state);
    } else {
      _enqueueSyncQueue(STORAGE_KEY, state);
    }
  }

  function notifyUI() {
    if (typeof RewardSystemUI !== 'undefined') {
      RewardSystemUI.syncInventoryBarWithState(state);
      RewardSystemUI.updateUI(state);
    }
  }

  /** 원장/잔액을 저장한다. (외부 쓰기와 경합하지 않도록 저장 직전 상태를 그대로 기록) */
  function persist(next, options) {
    const opts = options || {};
    next.last_updated = new Date().toISOString();
    next._updated_at = Math.max(Date.now(), (Number(next._updated_at) || 0) + 1);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    try {
      if (next.reward_ledger) {
        localStorage.setItem(LEDGER_JOURNAL_KEY, JSON.stringify(next.reward_ledger));
      }
    } catch (e) {
      console.warn('[RewardSystem] reward ledger journal write failed:', e);
    }
    state = next;
    if (opts.push !== false) pushToCloud();
    notifyUI();
  }

  function hasEventById(candidate, eventId) {
    const ledgerRaw = candidate && candidate.reward_ledger;
    if (!ledgerRaw || !Array.isArray(ledgerRaw.events)) return false;
    return ledgerRaw.events.some(event => event && event.id === eventId);
  }

  function readBackState() {
    const parsed = parseStorage();
    if (!parsed) return null;
    return normalizeRewardState(parsed, { adoptFields: false });
  }

  /**
   * 잔액 변경을 원장 델타로 확정한다.
   * 1) 메모리에서 만든 델타를 2) 디스크의 최신 원장과 병합한 뒤 3) 적용·저장하고
   * 4) 다시 읽어 이벤트가 실제로 남았는지 확인한다. 경합이 감지되면 재병합한다.
   * @param {object} beforeSnapshot 변경 전 잔액 스냅샷
   * @param {{type?: string, reason?: string, receipt?: string, at?: number}} options
   */
  function commit(beforeSnapshot, options) {
    const L = ledger();
    if (!L) {
      // 원장 모듈이 없는 환경(구버전 로더)에서도 보상 자체는 잃지 않는다.
      persist(state, {});
      return { committed: true, verified: false };
    }

    const opts = options || {};
    const at = Number.isFinite(Number(opts.at)) ? Number(opts.at) : Date.now();
    const deltas = L.diffSnapshots(beforeSnapshot, L.snapshot(state));
    let attempt = 0;
    let verified = false;

    while (attempt < 3) {
      attempt += 1;
      const disk = normalizeRewardState(parseStorage() || {}, { adoptFields: true, at });

      // 같은 영수증이 이미 디스크에 있으면 다른 탭/기기가 먼저 지급한 것이다.
      if (opts.receipt && disk.claimed_receipts && disk.claimed_receipts[opts.receipt]) {
        state = disk;
        notifyUI();
        return { committed: false, duplicateReceipt: true, verified: true };
      }

      const memory = normalizeRewardState(state, { adoptFields: false, at });
      let next = L.mergeStates(disk, memory, { adoptFields: false, at });
      next.claimed_receipts = L.mergeReceipts(next.claimed_receipts, memory.claimed_receipts);

      let eventIds = [];
      if (deltas.length > 0) {
        const applied = L.applyDeltas(next, deltas, {
          at,
          type: opts.type,
          reason: opts.reason,
          receipt: opts.receipt,
          group: opts.group,
          source: opts.source,
          actor: opts.actor,
          surface: opts.surface,
          client: opts.client,
          detail: opts.detail,
        });
        next = applied.state;
        eventIds = applied.eventIds;
      }
      next.claimed_receipts = L.mergeReceipts(next.claimed_receipts, memory.claimed_receipts);

      persist(next, {});

      const readBack = readBackState();
      const eventsKept = eventIds.every(eventId => hasEventById(readBack, eventId));
      const receiptsKept = !opts.receipt || Boolean(readBack && readBack.claimed_receipts[opts.receipt]);
      if (readBack && eventsKept && receiptsKept) {
        state = readBack;
        notifyUI();
        verified = true;
        break;
      }
      // 다른 탭이 덮어썼다면 디스크 상태를 기준으로 델타를 다시 적용한다.
      if (readBack) state = readBack;
    }

    if (!verified) {
      console.warn('[RewardSystem] reward commit race detected; kept best-effort state');
      notifyUI();
    }
    return { committed: true, verified };
  }

  function save() {
    const L = ledger();
    commit(balanceSnapshot(state), { type: 'meta', reason: L ? 'meta_save' : 'legacy_save' });
  }

  function setTheme(themeName) {
    state.theme = themeName;
    state._meta_at = { ...(state._meta_at || {}), theme: Date.now() };
    save();
    window.location.reload();
  }

  function add(type, amount = 1, options) {
    const safeAmount = Number.isFinite(Number(amount)) ? Number(amount) : 0;
    if (safeAmount <= 0) return;

    const opts = options && typeof options === 'object' ? options : {};
    const before = balanceSnapshot(state);

    let typeName = type;
    if (type === 'gems') typeName = '💎 보석';
    else if (type === 'youtube') typeName = '📺 유튜브 시간';
    else if (type === 'snack') typeName = '🍪 간식';
    else if (type === 'marble') typeName = '🎮 마블 게임';
    else if (type === 'bubble') typeName = '🫧 비눗방울 게임';
    else {
      const item = state.shop_items.find(i => i.id === type);
      if (item) typeName = `${item.icon} ${item.label}`;
    }

    if (type === 'gems') {
      state.gems = (Number(state.gems) || 0) + safeAmount;
    } else if (type === 'youtube') {
      state.youtube_minutes = (Number(state.youtube_minutes) || 0) + (safeAmount * 10);
    } else if (type === 'snack') {
      state.snacks = (Number(state.snacks) || 0) + safeAmount;
    } else if (type === 'marble') {
      state.marble_plays = (Number(state.marble_plays) || 0) + safeAmount;
    } else if (type === 'bubble') {
      state.bubble_plays = (Number(state.bubble_plays) || 0) + safeAmount;
    } else {
      if (!state.custom_inventory[type]) state.custom_inventory[type] = 0;
      state.custom_inventory[type] = (Number(state.custom_inventory[type]) || 0) + safeAmount;
    }

    commit(before, {
      type: 'grant',
      reason: opts.reason || ('add:' + type),
      receipt: opts.receipt,
      source: opts.source || 'quiz',
      actor: opts.actor || 'system',
      surface: opts.surface,
      client: opts.client,
      detail: opts.detail || `${typeName} 획득`,
      at: opts.now || opts.at,
    });

    if (typeof RewardSystemUI !== 'undefined') {
      RewardSystemUI.showToast(`${typeName} 획득!`);
    }
  }

  function has(type, amount = 1) {
    if (type === 'gems') return state.gems >= amount;
    if (type === 'youtube') return state.youtube_minutes >= 10;
    if (type === 'snack') return state.snacks >= amount;
    if (type === 'marble') return state.marble_plays >= amount;
    if (type === 'bubble') return state.bubble_plays >= amount;
    return (state.custom_inventory[type] || 0) >= amount;
  }

  function hasReceipt(receiptId) {
    if (!receiptId || typeof receiptId !== 'string') return false;
    return Boolean(state.claimed_receipts && state.claimed_receipts[receiptId]);
  }

  /**
   * 영수증이 있는 지급. 같은 receiptId는 몇 번을 호출해도 한 번만 지급된다.
   * 델타와 영수증을 한 번의 저장으로 확정해 "지급됐는데 영수증이 없는" 상태를 만들지 않는다.
   */
  function grantWithReceipt(receiptId, grants, options) {
    if (!receiptId || typeof receiptId !== 'string') {
      return { success: false, reason: 'invalid_receipt_id' };
    }
    if (hasReceipt(receiptId)) {
      return { success: false, reason: 'already_claimed', alreadyClaimed: true };
    }

    const opts = options && typeof options === 'object' ? options : {};
    const now = typeof opts.now === 'number' ? opts.now : Date.now();
    const list = Array.isArray(grants) ? grants : [];
    const before = balanceSnapshot(state);
    let totalGems = 0;
    let totalYoutubeMinutes = 0;

    for (const g of list) {
      const type = g && g.type;
      const amount = Number.isFinite(Number(g && g.amount)) ? Number(g.amount) : 0;
      if (amount <= 0) continue;

      if (type === 'gems') {
        state.gems = (Number(state.gems) || 0) + amount;
        totalGems += amount;
      } else if (type === 'youtube') {
        state.youtube_minutes = (Number(state.youtube_minutes) || 0) + (amount * 10);
        totalYoutubeMinutes += (amount * 10);
      } else if (type === 'snack') {
        state.snacks = (Number(state.snacks) || 0) + amount;
      } else if (type === 'marble') {
        state.marble_plays = (Number(state.marble_plays) || 0) + amount;
      } else if (type === 'bubble') {
        state.bubble_plays = (Number(state.bubble_plays) || 0) + amount;
      } else {
        if (!state.custom_inventory[type]) state.custom_inventory[type] = 0;
        state.custom_inventory[type] = (Number(state.custom_inventory[type]) || 0) + amount;
      }
    }

    if (!state.claimed_receipts) state.claimed_receipts = {};
    state.claimed_receipts[receiptId] = {
      receiptId: receiptId,
      grantedAt: now,
      grants: list,
      ...(opts.source ? { source: opts.source } : {}),
      ...(opts.detail ? { detail: opts.detail } : {}),
    };

    const result = commit(before, {
      type: 'grant',
      reason: opts.reason || 'receipt',
      receipt: receiptId,
      source: opts.source,
      actor: opts.actor || 'system',
      surface: opts.surface,
      client: opts.client,
      detail: opts.detail,
      at: now,
    });

    if (result.duplicateReceipt) {
      return { success: false, reason: 'already_claimed', alreadyClaimed: true };
    }

    if (typeof RewardSystemUI !== 'undefined') {
      const toastParts = [];
      if (totalGems > 0) toastParts.push(`💎 보석 ${totalGems}개`);
      if (totalYoutubeMinutes > 0) toastParts.push(`📺 자유시간 ${totalYoutubeMinutes}분`);
      const toastMsg = toastParts.length > 0 ? `${toastParts.join(' + ')} 획득!` : '보상 획득!';
      RewardSystemUI.showToast(toastMsg);
    }

    return {
      success: true,
      alreadyClaimed: false,
      gems: state.gems,
      youtube_minutes: state.youtube_minutes,
    };
  }

  /** 단일 항목을 영수증 기반으로 지급한다 (하루 1회·업적 1회 보상용). */
  function grantOnce(receiptId, type, amount, options) {
    return grantWithReceipt(receiptId, [{ type, amount }], options);
  }

  function consume(type) {
    if (typeof RewardSystemUI === 'undefined') return;

    if (type === 'youtube') {
      RewardSystemUI.openYoutubeModal(state);
      return;
    } else if (type === 'snack') {
      // 유튜브와 동일: 모달에서 부모 잠금 후 '사용 기록' 시 consumeInternal로 차감
      RewardSystemUI.openSnackModal(state);
      return;
    } else if (type !== 'marble' && type !== 'bubble') {
      const item = state.shop_items.find(i => i.id === type) || { id: type, icon: '🎁', label: '알 수 없는 보상' };
      RewardSystemUI.openCustomModal(item, state);
      return;
    }

    // Short-play games require fresh study, not purchased play tickets.
    if (type === 'marble') RewardSystemUI.openMarbleModal();
    else if (type === 'bubble') RewardSystemUI.openBubbleModal();
  }

  // reward_ui.js에서 호출하는 내부 데이터 수정 함수
  function consumeInternal(type, onSuccess, amount = 1) {
    const safeAmount = Number(amount);
    if (!Number.isSafeInteger(safeAmount) || safeAmount < 1) return false;

    const before = balanceSnapshot(state);

    if (type === 'youtube') {
      const minutesToDeduct = safeAmount * 10;
      if (state.youtube_minutes < minutesToDeduct) {
        if (typeof RewardSystemUI !== 'undefined') alert('보유 중인 유튜브 시간이 부족합니다.');
        return false;
      }
      state.youtube_minutes -= minutesToDeduct;
      commit(before, {
        type: 'consume',
        reason: 'youtube_ticket',
        source: 'youtube_modal',
        actor: 'guardian',
        detail: `유튜브 자유시간 모달 차감 (${safeAmount}개 · ${minutesToDeduct}분 사용)`,
      });
      if (typeof RewardSystemUI !== 'undefined') {
        RewardSystemUI.showToast(
          safeAmount === 1
            ? '10분 차감 완료'
            : `📺 유튜브 ${safeAmount}개 (${minutesToDeduct}분) 사용 완료`
        );
      }
    } else if (type === 'snack') {
      if (state.snacks < safeAmount) {
        if (typeof RewardSystemUI !== 'undefined') alert('보유 중인 간식이 부족합니다.');
        return false;
      }
      state.snacks -= safeAmount;
      commit(before, {
        type: 'consume',
        reason: 'snack',
        source: 'snack_modal',
        actor: 'guardian',
        detail: `간식 사용 승인 차감 (${safeAmount}개 사용)`,
      });
      if (typeof RewardSystemUI !== 'undefined') RewardSystemUI.showToast(`🍪 간식 ${safeAmount}개 사용 완료`);
    } else if (type === 'marble') {
      if (state.marble_plays < safeAmount) {
        if (typeof RewardSystemUI !== 'undefined') alert('보유 중인 마블 게임 횟수가 부족합니다.');
        return false;
      }
      state.marble_plays -= safeAmount;
      commit(before, {
        type: 'consume',
        reason: 'marble_play',
        source: 'hub',
        actor: 'child',
        detail: `마블 게임 플레이권 사용 (${safeAmount}회)`,
      });
      if (typeof RewardSystemUI !== 'undefined') RewardSystemUI.showToast(`🎮 마블 게임 ${safeAmount}회 사용 완료`);
    } else if (type === 'bubble') {
      if (state.bubble_plays < safeAmount) {
        if (typeof RewardSystemUI !== 'undefined') alert('보유 중인 비눗방울 게임 횟수가 부족합니다.');
        return false;
      }
      state.bubble_plays -= safeAmount;
      commit(before, {
        type: 'consume',
        reason: 'bubble_play',
        source: 'hub',
        actor: 'child',
        detail: `버블 게임 플레이권 사용 (${safeAmount}회)`,
      });
      if (typeof RewardSystemUI !== 'undefined') RewardSystemUI.showToast(`🫧 비눗방울 게임 ${safeAmount}회 사용 완료`);
    } else {
      const available = Number(state.custom_inventory[type]) || 0;
      if (available < safeAmount) {
        if (typeof RewardSystemUI !== 'undefined') alert('보유 중인 보상이 부족합니다.');
        return false;
      }
      const item = state.shop_items.find(i => i.id === type);
      const label = item ? item.label : '보상';
      state.custom_inventory[type] = available - safeAmount;
      commit(before, {
        type: 'consume',
        reason: 'custom_reward:' + type,
        source: 'custom_modal',
        actor: 'guardian',
        detail: `${item && item.icon ? item.icon + ' ' : ''}${label} 사용 승인 (${safeAmount}개 차감)`,
      });
      if (typeof RewardSystemUI !== 'undefined') RewardSystemUI.showToast(`${label} ${safeAmount}개 사용 완료`);
    }

    if (onSuccess) onSuccess(state);
    return true;
  }

  function exchangeGem(targetType) {
    if (targetType === 'marble' || targetType === 'bubble') {
      consume(targetType);
      return;
    }
    const item = state.shop_items.find(i => i.id === targetType);
    const price = item && item.price ? item.price : 1;

    if (state.gems < price) {
      alert(`보석이 부족합니다! (필요: ${price}개)`);
      return false;
    }

    const before = balanceSnapshot(state);
    state.gems -= price;
    let targetLabel = targetType;
    if (targetType === 'youtube') {
      state.youtube_minutes += 10;
      targetLabel = '📺 유튜브 자유시간 10분';
    } else if (targetType === 'snack') {
      state.snacks += 1;
      targetLabel = '🍪 간식 1개';
    } else if (targetType === 'marble') {
      state.marble_plays += 1;
      targetLabel = '🎮 마블 게임 1회';
    } else if (targetType === 'bubble') {
      state.bubble_plays += 1;
      targetLabel = '🫧 버블 게임 1회';
    } else {
      if (!state.custom_inventory[targetType]) state.custom_inventory[targetType] = 0;
      state.custom_inventory[targetType] += 1;
      targetLabel = item ? `${item.icon || '🎁'} ${item.label} 1개` : `${targetType} 1개`;
    }

    commit(before, {
      type: 'exchange',
      reason: 'gem_exchange:' + targetType,
      source: 'shop',
      actor: 'child',
      detail: `보석 상점 교환 (💎 ${price}개 → ${targetLabel})`,
    });
    if (typeof RewardSystemUI !== 'undefined') {
      RewardSystemUI.showToast('교환 성공! 보관함을 확인하세요.');
      const info = document.querySelector('.shop-inventory-info span');
      if (info) info.textContent = `💎 ${state.gems}개`;
      RewardSystemUI.updateUI(state);
    }
    return true;
  }

  /** 10분권 단위가 아닌 자투리 시간을 원장에 기록하며 정리한다. */
  function normalizeYoutubeMinutes() {
    const L = ledger();
    const current = Number(state.youtube_minutes) || 0;
    const normalized = Math.max(0, Math.floor(current / 10) * 10);
    if (current === normalized) return normalized;
    if (!L) {
      state.youtube_minutes = normalized;
      persist(state, {});
      return normalized;
    }
    const disk = normalizeRewardState(parseStorage() || state, { adoptFields: true });
    const memory = normalizeRewardState(state, { adoptFields: false });
    const merged = L.mergeStates(disk, memory, { adoptFields: false });
    const applied = L.setQuantity(merged, 'youtube_minutes', normalized, {
      type: 'adjust',
      reason: 'youtube_stray',
      at: Date.now(),
    });
    persist(applied.state, {});
    return normalized;
  }

  // ──────────────────────────────────────────
  // 2. 초기화 (Initialization)
  // ──────────────────────────────────────────
  function reconcileFreeTimeSessionUI() {
    try {
      const rawSession = localStorage.getItem('study_youtube_free_time_session_v1');
      if (!rawSession || typeof FreeTimeSession === 'undefined') {
        if (typeof RewardSystemUI !== 'undefined' && typeof RewardSystemUI.clearFreeTimeSessionUI === 'function') {
          RewardSystemUI.clearFreeTimeSessionUI();
        }
        return;
      }
      const saved = JSON.parse(rawSession);
      const nowMs = Date.now();
      const restored = FreeTimeSession.restore({ savedSession: saved, now: nowMs });
      const sel = FreeTimeSession.select(restored, nowMs);
      if (sel.active && typeof RewardSystemUI !== 'undefined' && typeof RewardSystemUI.renderFreeTimeTimerUI === 'function') {
        RewardSystemUI.renderFreeTimeTimerUI(restored, { isDirectUserStart: false });
      } else if (sel.expired && typeof RewardSystemUI !== 'undefined' && typeof RewardSystemUI.renderExpiredFreeTimeSessionUI === 'function') {
        try {
          localStorage.setItem('study_youtube_free_time_session_v1', JSON.stringify(restored));
        } catch (e) {}
        RewardSystemUI.renderExpiredFreeTimeSessionUI(restored);
      } else if (typeof RewardSystemUI !== 'undefined' && typeof RewardSystemUI.clearFreeTimeSessionUI === 'function') {
        RewardSystemUI.clearFreeTimeSessionUI();
      }
    } catch (e) {
      // ignore session UI reconciliation failure
    }
  }

  function refreshFromStorage() {
    load();
    if (typeof RewardSystemUI !== 'undefined') {
      RewardSystemUI.syncInventoryBarWithState(state);
      RewardSystemUI.updateUI(state);
      RewardSystemUI.applyBodyTopOffset();
    }
    reconcileFreeTimeSessionUI();
  }

  function startYouTubeSession(durationMinutes, options) {
    if (typeof FreeTimeSessionStartTransaction === 'undefined') {
      console.error('[RewardSystem] FreeTimeSessionStartTransaction not loaded');
      return { code: 'commit_failed' };
    }
    if (typeof ExternalTabLauncher === 'undefined') {
      console.error('[RewardSystem] ExternalTabLauncher not loaded');
      return { code: 'commit_failed' };
    }
    if (typeof FreeTimeSession === 'undefined') {
      console.error('[RewardSystem] FreeTimeSession not loaded');
      return { code: 'commit_failed' };
    }
    if (typeof FreeTimeAllowance === 'undefined') {
      console.error('[RewardSystem] FreeTimeAllowance not loaded');
      return { code: 'commit_failed' };
    }

    const openExternal = ExternalTabLauncher.createOpenExternal(window, 'https://www.youtube.com/');
    const nowMs = options && Number.isFinite(options.nowMs) ? options.nowMs : Date.now();
    const sessionId = 'yt-' + nowMs + '-' + Math.random().toString(36).slice(2, 8);

    const result = FreeTimeSessionStartTransaction.attemptStart({
      storage: localStorage,
      openExternal: openExternal,
      now: nowMs,
      sessionId: sessionId,
      FreeTimeSession: FreeTimeSession,
      FreeTimeAllowance: FreeTimeAllowance,
      RewardLedger: ledger(),
      durationMinutes: durationMinutes !== undefined ? durationMinutes : 10,
    });

    if (result.code === 'started') {
      load();
      pushToCloud();
      if (result.session) {
        pushKeyToCloud('study_youtube_free_time_session_v1', result.session);
      }
      try {
        const rawUsage = localStorage.getItem('study_youtube_free_time_daily_usage_v1');
        if (rawUsage) {
          pushKeyToCloud('study_youtube_free_time_daily_usage_v1', JSON.parse(rawUsage));
        }
      } catch (e) {}
      if (typeof RewardSystemUI !== 'undefined') {
        RewardSystemUI.syncInventoryBarWithState(state);
        RewardSystemUI.updateUI(state);
        RewardSystemUI.applyBodyTopOffset();
        if (typeof RewardSystemUI.renderFreeTimeTimerUI === 'function') {
          RewardSystemUI.renderFreeTimeTimerUI(result.session, options);
        }
      }
    }

    return result;
  }

  function bindSyncListeners() {
    if (storageListenerBound) return;
    storageListenerBound = true;
    // 다른 탭이 보상을 쓰거나 사용하면 메모리 스냅샷을 즉시 최신화한다.
    // (오래된 메모리 상태가 다시 저장되어 소비를 되돌리는 경로를 차단)
    window.addEventListener('storage', (event) => {
      if (
        event
        && event.key
        && event.key !== STORAGE_KEY
        && event.key !== 'study_youtube_free_time_session_v1'
        && event.key !== 'study_youtube_free_time_daily_usage_v1'
      ) {
        return;
      }
      refreshFromStorage();
    });
    window.addEventListener('cloud-sync-complete', refreshFromStorage);
  }

  function init() {
    load();
    if (typeof RewardSystemUI !== 'undefined') {
      RewardSystemUI.injectCriticalStyles();
      RewardSystemUI.injectInventoryBar(state);
      RewardSystemUI.injectStyles(state, () => {
        RewardSystemUI.updateUI(state);
        const bar = document.getElementById('reward-inventory');
        if (bar) bar.style.opacity = '1';
        RewardSystemUI.applyBodyTopOffset();
      });
    }
    bindSyncListeners();
    reconcileFreeTimeSessionUI();
  }

  /** 최근 획득/사용 기록 — "무엇이 언제 들어오고 나갔는지"를 사용자에게 보여준다. */
  function getRecentActivity(limit) {
    const L = ledger();
    if (!L) return [];
    return L.activity(state, { limit: limit === undefined ? 12 : limit });
  }

  /** 전체 감사 리포트(무결성 검증, 항목별 합계, 타임라인, 영수증, 초기화 이력)를 반환한다. */
  function getAuditReport(filter) {
    const L = ledger();
    if (!L || typeof L.auditReport !== 'function') return null;
    return L.auditReport(state, filter);
  }

  /** 감사 내역을 CSV 문자열로 내보낸다. */
  function getAuditCsv(filter) {
    const L = ledger();
    if (!L || typeof L.auditCsv !== 'function') return '';
    return L.auditCsv(state, filter);
  }

  /**
   * 모든 획득된 보상을 0으로 초기화하고 새 감사 epoch를 시작한다(로컬·부속 키·클라우드 동기화 반영).
   */
  function resetAllRewards(options) {
    const opts = options && typeof options === 'object' ? options : {};
    const nowTs = Number.isFinite(Number(opts.now)) ? Number(opts.now) : Date.now();
    const L = ledger();
    let resetNext;
    if (L && typeof L.resetState === 'function') {
      const disk = normalizeRewardState(parseStorage() || state, { adoptFields: true, at: nowTs });
      const memory = normalizeRewardState(state, { adoptFields: false, at: nowTs });
      const combined = L.mergeStates(disk, memory, { adoptFields: false, at: nowTs });
      resetNext = L.resetState(combined, {
        at: nowTs,
        reason: opts.reason || 'guardian_manual_reset',
        actor: opts.actor || 'guardian',
        note: opts.note || '보호자 전체 보상 초기화',
        surface: opts.surface,
        client: opts.client,
      });
    } else {
      resetNext = {
        ...state,
        gems: 0,
        youtube_minutes: 0,
        snacks: 0,
        marble_plays: 0,
        bubble_plays: 0,
        custom_inventory: {},
        claimed_receipts: {},
      };
    }
    const nextEpoch = L ? L.getEpoch(resetNext) : 1;
    syncCompanionEpoch(nextEpoch, { now: nowTs, force: true, pushCompanion: true });
    persist(resetNext, { reason: 'manual_reset' });
    return resetNext;
  }

  /** 저장된 잔액과 원장 합계가 일치하는지 확인한다. */
  function verifyIntegrity() {
    const L = ledger();
    if (!L) return { ok: false, reason: 'ledger_module_missing', mismatches: [] };
    return L.verify(state);
  }

  return {
    init, add, has, hasReceipt, grantWithReceipt, grantOnce, consume, consumeInternal, exchangeGem,
    startYouTubeSession, normalizeYoutubeMinutes, getRecentActivity, getAuditReport, getAuditCsv,
    resetAllRewards, syncCompanionEpoch, verifyIntegrity,
    getState: () => state,
    setTheme,
    openShopModal: () => {
      if (typeof RewardSystemUI !== 'undefined' && typeof RewardSystemUI.openShopModal === 'function') {
        RewardSystemUI.openShopModal(state);
      }
    },
    playEntranceAndAddGem: (id, meta) => {
      // UI 연출 실패 여부와 무관하게 보석 지급은 코어에서 보장한다.
      try {
        if (typeof RewardSystemUI !== 'undefined' && typeof RewardSystemUI.playEntranceAndAddGem === 'function') {
          RewardSystemUI.playEntranceAndAddGem(id, meta);
          return;
        }
      } catch (e) {
        console.error('RewardSystem animation failed, fallback to direct gem grant:', e);
      }
      add('gems', 1, meta);
    }
  };
})();

if (typeof window !== 'undefined') {
  window.RewardSystem = RewardSystem;
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => RewardSystem.init());
} else {
  RewardSystem.init();
}
