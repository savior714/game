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
        return;
      } catch (e) {
        console.error('[DailyStreak] Failed to load state:', e);
      }
    }
    state = getDefaultState();
  }

  function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function calculateStreakGems(streak) {
    if (streak === 0) return 0;
    let gems = 1;
    if (streak >= 3 && streak < 7) gems += 1;
    if (streak >= 7) gems += 1;
    return gems;
  }

  function awardGems(streak) {
    const gems = calculateStreakGems(streak);
    if (gems > 0 && typeof RewardSystem !== 'undefined') {
      RewardSystem.add('gems', gems);
    }
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
      awardGems(state.currentStreak);
      state.gemAwarded[today] = calculateStreakGems(state.currentStreak);
    }

    state.todayRecorded = true;
    save();
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

  return {
    recordAnswer,
    checkMidnightReset,
    getCurrentStreak,
    isTodayActive,
    getHistory,
  };
})();
