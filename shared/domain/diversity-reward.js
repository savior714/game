/**
 * @fileoverview 과목 다양성 보상 모듈 — 여러 과목 정답 시 차등 보석 지급
 * @module diversity-reward
 */

const DiversityReward = (() => {
  const STORAGE_KEY = 'aiden_diversity';

  let state;

  function getDefaultState() {
    return {
      today: getTodayKey(),
      subjectsWithCorrect: [],
      gemAwarded: false,
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
        state.today = parsed.today || getTodayKey();
        state.subjectsWithCorrect = parsed.subjectsWithCorrect || [];
        state.gemAwarded = parsed.gemAwarded || false;
        return;
      } catch (e) {
        console.error('[DiversityReward] Failed to load state:', e);
      }
    }
    state = getDefaultState();
  }

  function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function getDiversityGems(subjectCount) {
    if (subjectCount >= 4) return 2;
    if (subjectCount >= 3) return 2;
    if (subjectCount >= 2) return 1;
    return 0;
  }

  function awardGems(count) {
    if (count > 0 && typeof RewardSystem !== 'undefined') {
      RewardSystem.add('gems', count);
    }
  }

  function checkMidnightReset() {
    const today = getTodayKey();
    if (state.today !== today) {
      state.today = today;
      state.subjectsWithCorrect = [];
      state.gemAwarded = false;
      save();
    }
  }

  function recordCorrect(subject) {
    checkMidnightReset();

    if (state.subjectsWithCorrect.includes(subject)) return;

    state.subjectsWithCorrect.push(subject);

    if (!state.gemAwarded) {
      const gems = getDiversityGems(state.subjectsWithCorrect.length);
      if (gems > 0) {
        state.gemAwarded = true;
        awardGems(gems);
      }
    }

    save();
  }

  function getTodaySubjectCount() {
    checkMidnightReset();
    return state.subjectsWithCorrect.length;
  }

  function getTodaySubjects() {
    checkMidnightReset();
    return [...state.subjectsWithCorrect];
  }

  load();

  return {
    recordCorrect,
    checkMidnightReset,
    getTodaySubjectCount,
    getTodaySubjects,
  };
})();
