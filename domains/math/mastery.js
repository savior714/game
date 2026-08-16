/**
 * @fileoverview 수학 숙달도 엔진 (Math Mastery Engine V1)
 * @module math/mastery
 *
 * 결정론적이고 설명 가능한(explainable & deterministic) 스킬 숙달도 평가 순수 코어.
 * BKT, 머신러닝, 무작위성에 의존하지 않으며 동일한 증거와 시각에 대해 항상 동일한 결과를 반환.
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.MathMasteryEngine = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const DEFAULT_CONFIG = Object.freeze({
    minAttemptsForMastery: 3,         // 숙달 판정에 필요한 최소 시도 횟수
    masteryAccuracyThreshold: 0.8,    // 숙달 기준 정답률 (80%)
    strugglingAccuracyThreshold: 0.5, // 취약(부진) 기준 정답률 (50% 미만)
    recentWindowSize: 5,              // 최근 평가 윈도우 크기
    spacedReviewIntervalMs: 48 * 60 * 60 * 1000, // 간격 복습 주기 (48시간)
    consecutiveSuccessMastery: 4,     // 연속 정답 시 즉시 숙달 기준 (4회)
  });

  const STATUS = Object.freeze({
    NOT_STARTED: 'NOT_STARTED',
    PRACTICING: 'PRACTICING',
    MASTERED: 'MASTERED',
    NEEDS_REVIEW: 'NEEDS_REVIEW',
    STRUGGLING: 'STRUGGLING',
  });

  /**
   * 단일 스킬의 숙달 상태를 결정론적으로 계산
   * @param {string} skillId
   * @param {Array<Object>} evidenceList - 전체 또는 해당 스킬의 학습 증거 목록
   * @param {number} [now] - 현재 시각 (ms, 주입 가능)
   * @param {Object} [customConfig] - 설정 오버라이드
   */
  function computeSkillMastery(skillId, evidenceList, now, customConfig) {
    const config = Object.assign({}, DEFAULT_CONFIG, customConfig);
    const currentTime = typeof now === 'number' && Number.isFinite(now) ? now : Date.now();

    // 해당 스킬의 증거만 필터링
    const skillEvidences = Array.isArray(evidenceList)
      ? evidenceList.filter(e => e && e.skillId === skillId)
      : [];

    const totalAttempts = skillEvidences.length;
    if (totalAttempts === 0) {
      return {
        skillId: skillId,
        status: STATUS.NOT_STARTED,
        score: 0.0,
        totalAttempts: 0,
        totalCorrect: 0,
        recentAccuracy: 0.0,
        consecutiveCorrect: 0,
        lastPracticedAt: null,
        isDueForReview: false,
        isWeak: false,
        isMastered: false,
      };
    }

    let totalCorrect = 0;
    let consecutiveCorrect = 0;
    let streakCounted = false;

    // 역순(최신순) 순회로 연속 정답 및 최근 윈도우 집계
    const reversed = [...skillEvidences].reverse();
    const lastPracticedAt = reversed[0].timestamp || currentTime;

    for (let i = 0; i < reversed.length; i++) {
      const e = reversed[i];
      if (e.correct) {
        totalCorrect++;
        if (!streakCounted) consecutiveCorrect++;
      } else {
        streakCounted = true;
      }
    }

    const recentItems = reversed.slice(0, config.recentWindowSize);
    const recentCorrect = recentItems.filter(e => e.correct).length;
    const recentAccuracy = recentItems.length > 0 ? recentCorrect / recentItems.length : 0.0;

    // 숙달 판정 조건
    const hasEnoughAttempts = totalAttempts >= config.minAttemptsForMastery;
    const meetsAccuracy = recentAccuracy >= config.masteryAccuracyThreshold;
    const meetsStreak = consecutiveCorrect >= config.consecutiveSuccessMastery;
    const isMasteryLevel = (hasEnoughAttempts && meetsAccuracy) || meetsStreak;

    // 간격 복습 주기 초과 여부
    const isTimeForReview = isMasteryLevel && (currentTime - lastPracticedAt > config.spacedReviewIntervalMs);

    let status = STATUS.PRACTICING;
    let isWeak = false;

    if (isMasteryLevel) {
      if (isTimeForReview) {
        status = STATUS.NEEDS_REVIEW;
      } else {
        status = STATUS.MASTERED;
      }
    } else if (hasEnoughAttempts && recentAccuracy < config.strugglingAccuracyThreshold) {
      status = STATUS.STRUGGLING;
      isWeak = true;
    } else {
      status = STATUS.PRACTICING;
      if (hasEnoughAttempts && recentAccuracy < 0.6) {
        isWeak = true;
      }
    }

    // 결정론적 연속 점수 계산 (0.0 ~ 1.0)
    // 기본 점수: recentAccuracy (최대 0.7) + attempts 기여 (최대 0.15) + streak 보너스 (최대 0.15)
    let score = (recentAccuracy * 0.7) +
      (Math.min(totalAttempts, config.minAttemptsForMastery) / config.minAttemptsForMastery * 0.15) +
      (Math.min(consecutiveCorrect, config.consecutiveSuccessMastery) / config.consecutiveSuccessMastery * 0.15);

    if (status === STATUS.NEEDS_REVIEW) {
      // 복습 대기 시 약간의 점수 감쇠
      score = Math.min(score, 0.85);
    }
    score = Math.max(0.0, Math.min(1.0, Math.round(score * 100) / 100));

    return {
      skillId: skillId,
      status: status,
      score: score,
      totalAttempts: totalAttempts,
      totalCorrect: totalCorrect,
      recentAccuracy: Math.round(recentAccuracy * 100) / 100,
      consecutiveCorrect: consecutiveCorrect,
      lastPracticedAt: lastPracticedAt,
      isDueForReview: isTimeForReview,
      isWeak: isWeak,
      isMastered: status === STATUS.MASTERED,
    };
  }

  /**
   * 목록의 모든 스킬에 대해 숙달 상태 일괄 계산
   * @param {Array<string>} skillIds
   * @param {Array<Object>} evidenceList
   * @param {number} [now]
   * @param {Object} [customConfig]
   * @returns {Object.<string, Object>} skillId -> masteryObject
   */
  function computeAllSkillsMastery(skillIds, evidenceList, now, customConfig) {
    const result = {};
    if (!Array.isArray(skillIds)) return result;

    for (const skillId of skillIds) {
      result[skillId] = computeSkillMastery(skillId, evidenceList, now, customConfig);
    }
    return result;
  }

  return Object.freeze({
    DEFAULT_CONFIG: DEFAULT_CONFIG,
    STATUS: STATUS,
    computeSkillMastery: computeSkillMastery,
    computeAllSkillsMastery: computeAllSkillsMastery,
  });
});
