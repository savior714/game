/**
 * @fileoverview 수학 일일 스킬 목표 및 멱등적 보상 엔진 (Math Daily Goal Engine)
 * @module math/daily-goal
 *
 * 매일 아이에게 의미 있는 스킬 목표(예: 5문제 해결)를 제공하고,
 * 목표 달성 시 보석 및 자유시간 보상을 멱등적(Idempotent, 중복 지급 방지)으로 지급.
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.MathDailyGoalEngine = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const STORAGE_KEY = 'aiden_math_daily_goal_v1';
  const PREFERENCE_STORAGE_KEY = 'aiden_math_goal_preference_v1';
  const SCHEMA_VERSION = 1;
  const PREFERENCE_SCHEMA_VERSION = 1;
  const DEFAULT_TARGET_COUNT = 5;
  const DEFAULT_PRESET_ID = 'standard';
  const GOAL_PRESET_TARGETS = Object.freeze({
    light: 3,
    standard: 5,
    challenge: 7,
  });
  const GOAL_REWARD_GEMS = 2;
  const GOAL_REWARD_FREE_TIME_MINUTES = 10;

  function _getStorage(customStorage) {
    if (customStorage) return customStorage;
    if (typeof localStorage !== 'undefined') return localStorage;
    return null;
  }

  function getTodayDateString(now) {
    const d = typeof now === 'number' ? new Date(now) : new Date();
    return d.toISOString().split('T')[0];
  }

  function resolveGoalTargetCount(presetId) {
    if (typeof presetId === 'string' && Object.prototype.hasOwnProperty.call(GOAL_PRESET_TARGETS, presetId)) {
      return GOAL_PRESET_TARGETS[presetId];
    }
    return GOAL_PRESET_TARGETS[DEFAULT_PRESET_ID];
  }

  function loadGoalPreference(options) {
    const opts = options || {};
    const storage = _getStorage(opts.storage);
    const key = opts.key || PREFERENCE_STORAGE_KEY;

    if (!storage || typeof storage.getItem !== 'function') {
      return { schemaVersion: PREFERENCE_SCHEMA_VERSION, presetId: DEFAULT_PRESET_ID, updatedAt: null };
    }

    try {
      const raw = storage.getItem(key);
      if (!raw) {
        return { schemaVersion: PREFERENCE_SCHEMA_VERSION, presetId: DEFAULT_PRESET_ID, updatedAt: null };
      }
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === 'object' && parsed.schemaVersion === PREFERENCE_SCHEMA_VERSION && typeof parsed.presetId === 'string') {
        const validPresetId = Object.prototype.hasOwnProperty.call(GOAL_PRESET_TARGETS, parsed.presetId) ? parsed.presetId : DEFAULT_PRESET_ID;
        return {
          schemaVersion: PREFERENCE_SCHEMA_VERSION,
          presetId: validPresetId,
          updatedAt: typeof parsed.updatedAt === 'string' ? parsed.updatedAt : null,
        };
      }
    } catch (e) {
      console.warn('[MathDailyGoal] Failed to parse goal preference storage:', e);
    }
    return { schemaVersion: PREFERENCE_SCHEMA_VERSION, presetId: DEFAULT_PRESET_ID, updatedAt: null };
  }

  function saveGoalPreference(presetId, options) {
    const opts = options || {};
    const storage = _getStorage(opts.storage);
    const key = opts.key || PREFERENCE_STORAGE_KEY;
    const now = typeof opts.now === 'number' ? opts.now : Date.now();

    const validPresetId = (typeof presetId === 'string' && Object.prototype.hasOwnProperty.call(GOAL_PRESET_TARGETS, presetId))
      ? presetId
      : DEFAULT_PRESET_ID;

    const payload = {
      schemaVersion: PREFERENCE_SCHEMA_VERSION,
      presetId: validPresetId,
      updatedAt: new Date(now).toISOString(),
    };

    if (!storage || typeof storage.setItem !== 'function') {
      return payload;
    }

    try {
      storage.setItem(key, JSON.stringify(payload));
    } catch (e) {
      console.error('[MathDailyGoal] Failed to save goal preference:', e);
    }
    return payload;
  }

  function loadDailyGoal(options) {
    const opts = options || {};
    const storage = _getStorage(opts.storage);
    const key = opts.key || STORAGE_KEY;

    if (!storage || typeof storage.getItem !== 'function') return null;

    try {
      const raw = storage.getItem(key);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (parsed && parsed.schemaVersion === SCHEMA_VERSION && typeof parsed.date === 'string') {
        return parsed;
      }
    } catch (e) {
      console.warn('[MathDailyGoal] Failed to parse daily goal storage:', e);
    }
    return null;
  }

  function saveDailyGoal(goal, options) {
    const opts = options || {};
    const storage = _getStorage(opts.storage);
    const key = opts.key || STORAGE_KEY;

    if (!storage || typeof storage.setItem !== 'function' || !goal) return false;

    try {
      goal.lastUpdated = new Date().toISOString();
      storage.setItem(key, JSON.stringify(goal));
      return true;
    } catch (e) {
      console.error('[MathDailyGoal] Failed to save daily goal:', e);
      return false;
    }
  }

  /**
   * 오늘 날짜의 일일 목표 조회 또는 새로 초기화
   */
  function initOrGetDailyGoal(options) {
    const opts = options || {};
    const now = typeof opts.now === 'number' ? opts.now : Date.now();
    const today = getTodayDateString(now);
    const storage = _getStorage(opts.storage);

    const existing = loadDailyGoal({ storage: storage, key: opts.key });
    if (existing && existing.date === today) {
      return existing;
    }

    // 신규 목표 생성: 숙달도 상태 분석
    const masteryMap = opts.masteryMap || {};
    const skillCatalog = opts.skillCatalog || {};
    const skillOrder = opts.skillOrder || Object.keys(skillCatalog);

    let targetSkillId = null;

    // 1. 복습 필요 스킬 우선
    for (const sId of skillOrder) {
      const m = masteryMap[sId];
      if (m && (m.status === 'NEEDS_REVIEW' || m.isDueForReview)) {
        targetSkillId = sId;
        break;
      }
    }

    // 2. 취약/부진 스킬 다음
    if (!targetSkillId) {
      for (const sId of skillOrder) {
        const m = masteryMap[sId];
        if (m && (m.status === 'STRUGGLING' || m.isWeak)) {
          targetSkillId = sId;
          break;
        }
      }
    }

    // 3. 미숙달 스킬
    if (!targetSkillId) {
      for (const sId of skillOrder) {
        const m = masteryMap[sId];
        if (!m || m.status === 'NOT_STARTED' || m.status === 'PRACTICING') {
          targetSkillId = sId;
          break;
        }
      }
    }

    // 4. 전부 마스터한 경우 첫 번째 스킬 유지 보수
    if (!targetSkillId) {
      targetSkillId = skillOrder[0] || 'math.add.within_10';
    }

    // 보호자 프리셋 설정에서 목표 문제 수 산출
    const preference = opts.preference || loadGoalPreference({ storage: storage, key: opts.preferenceKey });
    const targetCount = resolveGoalTargetCount(preference ? preference.presetId : DEFAULT_PRESET_ID);

    const skillMeta = skillCatalog[targetSkillId] || { name: '수학 놀이 목표', shortName: '수학 목표' };
    const goalId = `goal-${today}-${targetSkillId}-v1`;
    const receiptId = `receipt-math-goal-${today}-${targetSkillId}-v1`;

    const newGoal = {
      schemaVersion: SCHEMA_VERSION,
      date: today,
      goalId: goalId,
      skillId: targetSkillId,
      skillName: skillMeta.name || skillMeta.shortName || '수학 연습',
      shortName: skillMeta.shortName || skillMeta.name || '수학 연습',
      targetCount: targetCount,
      currentCount: 0,
      completed: false,
      completedAt: null,
      rewardGranted: false,
      rewardReceiptId: receiptId,
      lastUpdated: new Date(now).toISOString(),
    };

    saveDailyGoal(newGoal, { storage: storage, key: opts.key });
    return newGoal;
  }

  /**
   * 문제 풀이 결과에 따라 목표 진행도 업데이트
   */
  function recordGoalProgress(options) {
    const opts = options || {};
    const goal = opts.goal;
    const skillId = opts.skillId;
    const correct = Boolean(opts.correct);
    const now = typeof opts.now === 'number' ? opts.now : Date.now();
    const storage = _getStorage(opts.storage);

    if (!goal || !correct || goal.completed) {
      return { goal: goal, completedJustNow: false };
    }

    let completedJustNow = false;
    if (skillId === goal.skillId) {
      goal.currentCount = (goal.currentCount || 0) + 1;
      if (goal.currentCount >= goal.targetCount && !goal.completed) {
        goal.completed = true;
        goal.completedAt = now;
        completedJustNow = true;
      }
      saveDailyGoal(goal, { storage: storage, key: opts.key });
    }

    return { goal: goal, completedJustNow: completedJustNow };
  }

  /**
   * 목표 완료 보상 멱등 지급
   */
  function claimGoalReward(options) {
    const opts = options || {};
    const goal = opts.goal;
    const rewardSystem = opts.rewardSystem;
    const storage = _getStorage(opts.storage);
    const now = typeof opts.now === 'number' ? opts.now : Date.now();

    if (!goal) {
      return { success: false, reason: 'invalid_goal' };
    }

    if (!goal.completed) {
      return { success: false, reason: 'not_completed' };
    }

    if (goal.rewardGranted) {
      return { success: false, reason: 'already_claimed' };
    }

    const receiptKey = `aiden_receipt_${goal.rewardReceiptId}`;
    let alreadyClaimed = false;

    if (storage && typeof storage.getItem === 'function') {
      const existingReceipt = storage.getItem(receiptKey);
      if (existingReceipt) {
        alreadyClaimed = true;
      }
    }

    if (!alreadyClaimed && rewardSystem && typeof rewardSystem.hasReceipt === 'function') {
      if (rewardSystem.hasReceipt(goal.rewardReceiptId)) {
        alreadyClaimed = true;
      }
    }

    if (alreadyClaimed) {
      goal.rewardGranted = true;
      saveDailyGoal(goal, { storage: storage, key: opts.key });
      return { success: false, reason: 'already_claimed' };
    }

    // 보상 시스템 연동 (보석 2개 + 자유시간 10분)
    if (rewardSystem) {
      if (typeof rewardSystem.grantWithReceipt === 'function') {
        const grantRes = rewardSystem.grantWithReceipt(
          goal.rewardReceiptId,
          [
            { type: 'gems', amount: GOAL_REWARD_GEMS },
            { type: 'youtube', amount: 1 }, // 1단위 = 10분
          ],
          { now: now }
        );
        if (!grantRes.success && grantRes.alreadyClaimed) {
          goal.rewardGranted = true;
          saveDailyGoal(goal, { storage: storage, key: opts.key });
          return { success: false, reason: 'already_claimed' };
        }
      } else if (typeof rewardSystem.add === 'function') {
        rewardSystem.add('gems', GOAL_REWARD_GEMS);
        rewardSystem.add('youtube', 1); // 1단위 = 10분
      }
    }

    // 영수증 기록 및 목표 상태 저장
    if (storage && typeof storage.setItem === 'function') {
      try {
        const receiptData = {
          receiptId: goal.rewardReceiptId,
          date: goal.date,
          skillId: goal.skillId,
          gems: GOAL_REWARD_GEMS,
          freeTimeMinutes: GOAL_REWARD_FREE_TIME_MINUTES,
          grantedAt: now,
        };
        storage.setItem(receiptKey, JSON.stringify(receiptData));
      } catch (e) {
        console.error('[MathDailyGoal] Failed to save reward receipt:', e);
      }
    }

    goal.rewardGranted = true;
    saveDailyGoal(goal, { storage: storage, key: opts.key });

    return {
      success: true,
      gems: GOAL_REWARD_GEMS,
      freeTimeMinutes: GOAL_REWARD_FREE_TIME_MINUTES,
      receiptId: goal.rewardReceiptId,
    };
  }

  return Object.freeze({
    STORAGE_KEY: STORAGE_KEY,
    PREFERENCE_STORAGE_KEY: PREFERENCE_STORAGE_KEY,
    SCHEMA_VERSION: SCHEMA_VERSION,
    PREFERENCE_SCHEMA_VERSION: PREFERENCE_SCHEMA_VERSION,
    DEFAULT_TARGET_COUNT: DEFAULT_TARGET_COUNT,
    DEFAULT_PRESET_ID: DEFAULT_PRESET_ID,
    GOAL_PRESET_TARGETS: GOAL_PRESET_TARGETS,
    GOAL_REWARD_GEMS: GOAL_REWARD_GEMS,
    GOAL_REWARD_FREE_TIME_MINUTES: GOAL_REWARD_FREE_TIME_MINUTES,
    getTodayDateString: getTodayDateString,
    loadDailyGoal: loadDailyGoal,
    saveDailyGoal: saveDailyGoal,
    resolveGoalTargetCount: resolveGoalTargetCount,
    loadGoalPreference: loadGoalPreference,
    saveGoalPreference: saveGoalPreference,
    initOrGetDailyGoal: initOrGetDailyGoal,
    recordGoalProgress: recordGoalProgress,
    claimGoalReward: claimGoalReward,
  });
});
