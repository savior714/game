/**
 * @fileoverview 일일 출석 추적 모듈 — 학습 기록 기반 출석 + 보석 지급
 * @module daily-streak
 */

const DailyStreak = (() => {
  const STORAGE_KEY = 'aiden_daily_streak';

  let state;

  function getDefaultState() {
    return {
      currentStreak: 0,
      lastActiveDate: null,
      todayRecorded: false,
      history: {},
      gemAwarded: {},
    };
  }

  function getTodayKey() {
    return new Date().toISOString().split('T')[0];
  }

  function load() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        state = getDefaultState();
        state.currentStreak = parsed.currentStreak || 0;
        state.lastActiveDate = parsed.lastActiveDate || null;
        state.todayRecorded = parsed.todayRecorded || false;
        state.history = parsed.history || {};
        state.gemAwarded = parsed.gemAwarded || {};
        if (Number(parsed.resetEpoch) > 0) state.resetEpoch = Number(parsed.resetEpoch);
        return;
      } catch (e) {
        console.error('[DailyStreak] Failed to load state:', e);
      }
    }
    state = getDefaultState();
  }

  function currentRewardEpoch() {
    if (typeof RewardSystem !== 'undefined' && typeof RewardSystem.getState === 'function') {
      const st = RewardSystem.getState();
      const ep = Number(st && st.reward_ledger && st.reward_ledger.reset_epoch);
      if (ep > 0) return ep;
    }
    if (typeof RewardLedger !== 'undefined' && typeof RewardLedger.BASELINE_RESET_EPOCH === 'number') {
      return RewardLedger.BASELINE_RESET_EPOCH;
    }
    return 1;
  }

  function save(pushCloud = false) {
    state.resetEpoch = Math.max(Number(state.resetEpoch) || 0, currentRewardEpoch());
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    if (pushCloud) {
      if (typeof window !== 'undefined' && window.SyncEngine && typeof window.SyncEngine.pushStats === 'function') {
        window.SyncEngine.pushStats(STORAGE_KEY, state);
      } else {
        try {
          const rawQ = localStorage.getItem('sync_queue');
          const q = rawQ ? JSON.parse(rawQ) : {};
          if (q && typeof q === 'object') {
            q[STORAGE_KEY] = { ...state, _updated_at: Date.now() };
            localStorage.setItem('sync_queue', JSON.stringify(q));
          }
        } catch (e) {}
      }
    }
  }

  function calculateStreakGems(streak) {
    if (streak === 0) return 0;
    let gems = 1;
    if (streak >= 3 && streak < 7) gems += 1;
    if (streak >= 7) gems += 1;
    return gems;
  }

  const SUBJECT_LABELS = {
    math: '수학',
    english: '영어',
    'weekly-test': '주간 영단어',
    korean: '국어',
    science: '과학',
  };

  /**
   * 오늘의 출석 보석은 날짜 기반 영수증으로 지급한다.
   * 같은 날 여러 번 호출되거나 다른 기기에서 다시 기록되어도 두 번 지급되지 않는다.
   */
  function awardGems(streak, dateKey, subject) {
    const gems = calculateStreakGems(streak);
    if (gems <= 0 || typeof RewardSystem === 'undefined') return;
    const receiptId = 'reward.daily-streak.' + (dateKey || getTodayKey());
    const subjectLabel = subject ? (SUBJECT_LABELS[subject] || subject) : '';
    const detail = `일일 출석 학습 보상 (${Math.max(1, streak)}일차${subjectLabel ? ' · ' + subjectLabel : ''})`;
    const meta = {
      reason: 'daily_streak',
      source: subject || 'quiz',
      actor: 'system',
      detail,
    };
    if (typeof RewardSystem.grantOnce === 'function') {
      RewardSystem.grantOnce(receiptId, 'gems', gems, meta);
      return;
    }
    RewardSystem.add('gems', gems, meta);
  }

  function checkMidnightReset() {
    const today = getTodayKey();
    if (state.lastActiveDate === today) {
      state.todayRecorded = false;
      save();
    }
  }

  function recordAnswer(subject) {
    const today = getTodayKey();

    if (state.todayRecorded && state.lastActiveDate === today) return;

    if (!state.lastActiveDate) {
      state.currentStreak = 1;
    } else {
      const lastDate = new Date(state.lastActiveDate);
      const todayDate = new Date(today);
      const diffMs = todayDate.getTime() - lastDate.getTime();
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

      if (diffDays === 1) {
        state.currentStreak++;
      } else if (diffDays > 1) {
        state.currentStreak = 0;
      }
    }

    state.lastActiveDate = today;
    state.history[today] = true;

    if (!state.gemAwarded[today]) {
      awardGems(state.currentStreak, today, subject);
      state.gemAwarded[today] = calculateStreakGems(state.currentStreak);
    }

    state.todayRecorded = true;
    save(true);
  }

  function getCurrentStreak() {
    return state.currentStreak;
  }

  function isTodayActive() {
    const today = getTodayKey();
    return state.lastActiveDate === today && state.history[today] === true;
  }

  function getHistory() {
    return { ...state.history };
  }

  load();
  if (typeof window !== 'undefined' && typeof window.addEventListener === 'function') {
    window.addEventListener('cloud-sync-complete', load);
    window.addEventListener('storage', (e) => {
      if (!e || !e.key || e.key === STORAGE_KEY) load();
    });
  }

  return {
    recordAnswer,
    checkMidnightReset,
    getCurrentStreak,
    isTodayActive,
    getHistory,
    reload: load,
  };
})();
