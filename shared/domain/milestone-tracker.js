/**
 * @fileoverview 마일스톤 추적 모듈 — 연속/누적/첫 도전 마일스톤 추적 및 피드백
 * @module milestone-tracker
 */

const MilestoneTracker = (() => {
  const STORAGE_KEY = 'aiden_milestones';

  const STREAK_MILESTONES = [
    { key: 'streak_3', threshold: 3, message: '3연속! 대단해! 🔥', gems: 0 },
    { key: 'streak_5', threshold: 5, message: '5연속! 넉줄 확인 무기! 🛡️', gems: 0 },
    { key: 'streak_10', threshold: 10, message: '10연속! 무서워! 😱', gems: 0 },
    { key: 'streak_15', threshold: 15, message: '15연속! 로켓 발사 임무! 🚀', gems: 0 },
  ];

  const SESSION_MILESTONES = [
    { key: 'session_3', threshold: 3, message: '오늘 3문제 맞혔어! 미션', gems: 0 },
    { key: 'session_5', threshold: 5, message: '세션 부분 이상! 5문제! 🌟', gems: 1 },
    { key: 'session_10', threshold: 10, message: '완벽 세션! 10문제 전부 정답! 💯', gems: 1 },
    { key: 'session_20', threshold: 20, message: '20문제?! 진지한 게임처! 🏆', gems: 1 },
  ];

  const FIRST_MILESTONES = [
    { key: 'first_answer', message: '처음 정답! 흥나하! 🎉', gems: 0 },
    { key: 'first_subject_complete', message: '처음 과제 완료! 🎊', gems: 0 },
    { key: 'first_rocket', message: '처음 로켓 발사! 🚀✨', gems: 0 },
  ];

  let state;

  function getDefaultState() {
    return {
      session: {
        rocketStreak: 0,
        milestoneStreak: 0,
        sessionCorrect: 0,
        firstAnswer: false,
        firstSubjectComplete: false,
        firstRocket: false,
      },
      lifetime: {
        totalCorrect: 0,
        subjectsCompleted: [],
        totalRockets: 0,
      },
      achieved: {
        'streak_3': false,
        'streak_5': false,
        'streak_10': false,
        'streak_15': false,
        'session_3': false,
        'session_5': false,
        'session_10': false,
        'session_20': false,
        'first_answer': false,
        'first_subject_complete': false,
        'first_rocket': false,
      },
    };
  }

  function load() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        state = getDefaultState();
        if (parsed.session) {
          state.session.rocketStreak = parsed.session.rocketStreak || 0;
          state.session.milestoneStreak = parsed.session.milestoneStreak || 0;
          state.session.sessionCorrect = parsed.session.sessionCorrect || 0;
          state.session.firstAnswer = parsed.session.firstAnswer || false;
          state.session.firstSubjectComplete = parsed.session.firstSubjectComplete || false;
          state.session.firstRocket = parsed.session.firstRocket || false;
        }
        if (parsed.lifetime) {
          state.lifetime.totalCorrect = parsed.lifetime.totalCorrect || 0;
          state.lifetime.subjectsCompleted = parsed.lifetime.subjectsCompleted || [];
          state.lifetime.totalRockets = parsed.lifetime.totalRockets || 0;
        }
        if (parsed.achieved) {
          state.achieved = { ...getDefaultState().achieved, ...parsed.achieved };
        }
        return;
      } catch (e) {
        console.error('[MilestoneTracker] Failed to load state:', e);
      }
    }
    state = getDefaultState();
  }

  function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function ensureAchievedKeys() {
    const defaults = getDefaultState().achieved;
    for (const key of Object.keys(defaults)) {
      if (!(key in state.achieved)) {
        state.achieved[key] = false;
      }
    }
  }

  function awardGems(count) {
    if (count > 0 && typeof RewardSystem !== 'undefined') {
      RewardSystem.add('gems', count);
    }
  }

  function showToast(message) {
    if (typeof RewardSystemUI !== 'undefined' && typeof RewardSystemUI.showToast === 'function') {
      RewardSystemUI.showToast(message);
    }
  }

  function checkAndAchieve(milestones, streakValue) {
    for (const m of milestones) {
      if (streakValue >= m.threshold && !state.achieved[m.key]) {
        state.achieved[m.key] = true;
        showToast(m.message);
        awardGems(m.gems);
      }
    }
  }

  function initSession(subject) {
    ensureAchievedKeys();
    state.session.sessionCorrect = 0;
    save();
  }

  function record(correct) {
    ensureAchievedKeys();

    if (correct) {
      state.session.rocketStreak++;
      state.session.milestoneStreak++;
      state.session.sessionCorrect++;
      state.lifetime.totalCorrect++;

      checkAndAchieve(STREAK_MILESTONES, state.session.milestoneStreak);
      checkAndAchieve(SESSION_MILESTONES, state.session.sessionCorrect);

      if (!state.achieved.first_answer) {
        state.achieved.first_answer = true;
        const m = FIRST_MILESTONES[0];
        showToast(m.message);
      }
    } else {
      state.session.milestoneStreak = 0;
    }

    save();
  }

  function endSession() {
    const sessionCorrect = state.session.sessionCorrect;
    return sessionCorrect;
  }

  function onRocketLaunch() {
    state.lifetime.totalRockets++;
    state.session.rocketStreak = 0;

    if (!state.achieved.first_rocket) {
      state.achieved.first_rocket = true;
      const m = FIRST_MILESTONES[2];
      showToast(m.message);
    }

    save();
  }

  function onSubjectComplete(subject) {
    if (!state.lifetime.subjectsCompleted.includes(subject)) {
      state.lifetime.subjectsCompleted.push(subject);
    }

    if (!state.achieved.first_subject_complete) {
      state.achieved.first_subject_complete = true;
      const m = FIRST_MILESTONES[1];
      showToast(m.message);
    }

    save();
  }

  function getAchieved(key) {
    ensureAchievedKeys();
    return !!state.achieved[key];
  }

  function getSessionData() {
    ensureAchievedKeys();
    return {
      rocketStreak: state.session.rocketStreak,
      milestoneStreak: state.session.milestoneStreak,
      sessionCorrect: state.session.sessionCorrect,
    };
  }

  function getLifetimeData() {
    return {
      totalCorrect: state.lifetime.totalCorrect,
      subjectsCompleted: [...state.lifetime.subjectsCompleted],
      totalRockets: state.lifetime.totalRockets,
    };
  }

  function resetSessionData() {
    state.session.sessionCorrect = 0;
    save();
  }

  load();

  return {
    initSession,
    record,
    endSession,
    onRocketLaunch,
    onSubjectComplete,
    getAchieved,
    resetSessionData,
    getSessionData,
    getLifetimeData,
  };
})();
