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
        if (Number(parsed.resetEpoch) > 0) state.resetEpoch = Number(parsed.resetEpoch);
        return;
      } catch (e) {
        console.error('[DiversityReward] Failed to load state:', e);
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

  function getDiversityGems(subjectCount) {
    if (subjectCount >= 4) return 2;
    if (subjectCount >= 3) return 2;
    if (subjectCount >= 2) return 1;
    return 0;
  }

  const SUBJECT_LABELS = {
    math: '수학',
    english: '영어',
    'weekly-test': '주간 영단어',
    korean: '국어',
    science: '과학',
  };

  /**
   * 과목 다양성 보석은 날짜 기반 영수증으로 지급한다(하루 1회, 기기 간 중복 방지).
   */
  function awardGems(count, dateKey, subjects, triggerSubject) {
    if (count <= 0 || typeof RewardSystem === 'undefined') return;
    const receiptId = 'reward.diversity.' + (dateKey || getTodayKey());
    const joined = Array.isArray(subjects) && subjects.length > 0
      ? subjects.map((s) => SUBJECT_LABELS[s] || s).join('·')
      : '';
    const detail = `다과목 학습 보상 (${joined ? joined + ' ' : ''}${Array.isArray(subjects) ? subjects.length : 2}과목 달성)`;
    const meta = {
      reason: 'diversity',
      source: triggerSubject || 'quiz',
      actor: 'system',
      detail,
    };
    if (typeof RewardSystem.grantOnce === 'function') {
      RewardSystem.grantOnce(receiptId, 'gems', count, meta);
      return;
    }
    RewardSystem.add('gems', count, meta);
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
        awardGems(gems, state.today, state.subjectsWithCorrect, subject);
      }
    }

    save(true);
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
  if (typeof window !== 'undefined' && typeof window.addEventListener === 'function') {
    window.addEventListener('cloud-sync-complete', load);
    window.addEventListener('storage', (e) => {
      if (!e || !e.key || e.key === STORAGE_KEY) load();
    });
  }

  return {
    recordCorrect,
    checkMidnightReset,
    getTodaySubjectCount,
    getTodaySubjects,
    reload: load,
  };
})();
