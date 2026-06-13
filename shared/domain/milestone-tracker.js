/**
 * @fileoverview 마일스톤 추적 모듈 — 연속/누적/첫 도전 마일스톤 추적 및 피드백
 * @module milestone-tracker
 */

const MilestoneTracker = (() => {
  const STORAGE_KEY = 'aiden_milestones';

  const STREAK_MILESTONES = [
    { key: 'streak_3', threshold: 3, message: '3연속! 대단해! \uD83D\uDD25', gems: 0 },
    { key: 'streak_5', threshold: 5, message: '5연속! \uBBC0\uC9D1 \uD655\uC81C \uC6CC\uAE30! \uD83D\uDEE1\uD83C\uDFFB', gems: 0 },
    { key: 'streak_10', threshold: 10, message: '10연속! \ubb34\uC11C\uC6B0! \uD83D\uDE31\uD83C\uDFFB', gems: 0 },
    { key: 'streak_15', threshold: 15, message: '15연속! \ub85C\uCF2B \ubc30\uC0AC \uC784\uAE35! \uD83D\uDE80', gems: 0 },
  ];

  const SESSION_MILESTONES = [
    { key: 'session_3', threshold: 3, message: '\uc624\ub298 3\ubb38\ubb38 \ub9de\uD588\uc5B4! \uD4BC\uD130', gems: 0 },
    { key: 'session_5', threshold: 5, message: '\uC138\uC158 \UBC30\uBD80 \uC774\uC0C1! 5\ubb38\ubb38! \uD83C\uDF1F', gems: 1 },
    { key: 'session_10', threshold: 10, message: '\uc644\ubcbd \uC138\uC158! 10\ubb38\ubb38 \uC804\uBD80\uC815\uB2F9! \uD83D\uDCAF', gems: 1 },
    { key: 'session_20', threshold: 20, message: '20\ubb38\ubb38?!\uc9c4\uc9c0 \uce74\uC784\uCC98! \uD83C\uDFC6', gems: 1 },
  ];

  const FIRST_MILESTONES = [
    { key: 'first_answer', message: '\ucc98\ubb38 \uC815\uB2F9! \uD64D\uCE20\uD558! \uD83C\uDF89', gems: 0 },
    { key: 'first_subject_complete', message: '\ucc98\ubb38 \uACFC\ubb38 \uc644\ub8CC! \uD83C\uDF8A', gems: 0 },
    { key: 'first_rocket', message: '\ucc98\ubb38 \ub85C\uCF2B \ubc30\uC0AC! \uD83D\uDE80\u2728', gems: 0 },
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
