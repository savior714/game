/**
 * @fileoverview 수학 보호자 진도 스냅샷 순수 코어 모듈 (Guardian Math Progress Snapshot V1)
 * @module math/guardian-summary
 *
 * 정규 원시 학습 증거(Evidence), 숙달도(Mastery), 일일 목표(Daily Goal), 스킬 카탈로그(Skills)를 읽어
 * 보호자 화면을 위한 읽기 전용 스냅샷을 결정론적으로 계산(Pure Projection).
 *
 * 불변식:
 * 1. 로컬 저장소 및 입력 데이터 무변형 (Pure Read-Only Projection)
 * 2. 인위적인 AI 점수나 가짜 숙달률(%)을 배제하고 실제 원시 증거(Raw Evidence) 기반 집계
 * 3. 동일한 입력과 시간에 대해 항상 동일한 스냅샷 반환 (Deterministic)
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.MathGuardianSummary = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const STATUS_LABELS = Object.freeze({
    NOT_STARTED: '시작 전',
    PRACTICING: '연습 중',
    MASTERED: '잘하고 있어요',
    NEEDS_REVIEW: '복습할 때예요',
    STRUGGLING: '도움이 필요해요',
  });

  const WINDOW_SIZE = 5;

  /**
   * 보호자용 수학 학습 진도 스냅샷 생성 (Pure Function)
   * @param {Object} options
   * @param {Object} [options.skillCatalog] - MathSkills.MATH_SKILLS
   * @param {Array<string>} [options.skillOrder] - MathSkills.MATH_SKILL_ORDER
   * @param {Array<Object>} [options.evidenceList] - MathEvidenceStore에서 로드한 증거 목록
   * @param {Object} [options.masteryMap] - MathMasteryEngine에서 계산한 스킬별 숙달도 맵
   * @param {Object} [options.dailyGoal] - MathDailyGoalEngine에서 로드한 오늘의 목표
   * @param {number} [options.now] - 기준 타임스탬프 (ms)
   * @returns {Object} guardianSnapshot
   */
  function buildGuardianMathSnapshot(options) {
    const opts = options || {};
    const skillCatalog = opts.skillCatalog || {};
    const skillOrder = Array.isArray(opts.skillOrder)
      ? opts.skillOrder
      : Object.keys(skillCatalog);
    const rawEvidences = Array.isArray(opts.evidenceList) ? opts.evidenceList : [];
    const masteryMap = opts.masteryMap || {};
    const dailyGoal = opts.dailyGoal || null;
    const now = typeof opts.now === 'number' && Number.isFinite(opts.now) ? opts.now : Date.now();

    // 유효한 증거만 필터링 (불변식: 원본 배열 변경 없음)
    const validEvidences = rawEvidences.filter(
      e => e && typeof e === 'object' && typeof e.skillId === 'string'
    );

    const isEmpty = validEvidences.length === 0;

    // 스킬별 증거 분류 및 정렬
    const evidenceBySkill = {};
    for (const sId of skillOrder) {
      evidenceBySkill[sId] = [];
    }
    for (const ev of validEvidences) {
      if (!evidenceBySkill[ev.skillId]) {
        evidenceBySkill[ev.skillId] = [];
      }
      evidenceBySkill[ev.skillId].push(ev);
    }

    // 각 스킬별 스냅샷 생성
    const skillSnapshots = [];
    const masteredSkills = [];
    const attentionCandidates = [];

    for (let index = 0; index < skillOrder.length; index++) {
      const sId = skillOrder[index];
      const skillMeta = skillCatalog[sId] || {
        id: sId,
        name: sId,
        shortName: sId,
        curriculumRef: '',
        gradeBand: '',
        description: '',
      };

      const evidences = (evidenceBySkill[sId] || [])
        .slice()
        .sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0));

      const totalAttempts = evidences.length;
      const totalCorrect = evidences.filter(e => e.correct).length;
      const totalAccuracy = totalAttempts > 0
        ? Math.round((totalCorrect / totalAttempts) * 100) / 100
        : 0;

      const mastery = masteryMap[sId] || {
        skillId: sId,
        status: totalAttempts === 0 ? 'NOT_STARTED' : 'PRACTICING',
        score: 0.0,
        isWeak: false,
        isDueForReview: false,
        isMastered: false,
        lastPracticedAt: totalAttempts > 0 ? evidences[totalAttempts - 1].timestamp : null,
      };

      const status = mastery.status || (totalAttempts === 0 ? 'NOT_STARTED' : 'PRACTICING');
      const statusLabel = STATUS_LABELS[status] || STATUS_LABELS.PRACTICING;
      const isWeak = Boolean(mastery.isWeak);
      const isDueForReview = Boolean(mastery.isDueForReview);
      const lastPracticedAt = evidences.length > 0
        ? (evidences[evidences.length - 1].timestamp || null)
        : null;

      // 최근 최대 5회 vs 그 직전 최대 5회 윈도우 분리
      const recentEvidences = evidences.slice(-WINDOW_SIZE);
      const previousEvidences = evidences.length > WINDOW_SIZE
        ? evidences.slice(-WINDOW_SIZE * 2, -WINDOW_SIZE)
        : [];

      const recentAttempts = recentEvidences.length;
      const recentCorrect = recentEvidences.filter(e => e.correct).length;
      const recentAccuracy = recentAttempts > 0
        ? Math.round((recentCorrect / recentAttempts) * 100) / 100
        : 0;

      const previousAttempts = previousEvidences.length;
      const previousCorrect = previousEvidences.filter(e => e.correct).length;
      const previousAccuracy = previousAttempts > 0
        ? Math.round((previousCorrect / previousAttempts) * 100) / 100
        : 0;

      const hasPreviousComparison = previousAttempts > 0;
      let trend = 'none';
      let trendText = '비교 대기';
      let growthSummary = '연습 기록이 더 쌓이면 변화를 비교할 수 있어요.';

      if (recentAttempts === 0) {
        growthSummary = '아직 연습 기록이 없습니다.';
      } else if (hasPreviousComparison) {
        if (recentAccuracy > previousAccuracy) {
          trend = 'improved';
          trendText = '상승';
        } else if (recentAccuracy < previousAccuracy) {
          trend = 'declined';
          trendText = '하락';
        } else {
          trend = 'maintained';
          trendText = '유지';
        }
        growthSummary = `최근 ${recentAttempts}문제 중 ${recentCorrect}정답 (직전 ${previousAttempts}문제 ${previousCorrect}정답 대비 ${trendText})`;
      } else {
        growthSummary = `최근 ${recentAttempts}문제 중 ${recentCorrect}정답 (이전 기록 쌓이는 중)`;
      }

      const snapshot = {
        skillId: sId,
        orderIndex: index,
        name: skillMeta.name || sId,
        shortName: skillMeta.shortName || skillMeta.name || sId,
        curriculumRef: skillMeta.curriculumRef || '',
        gradeBand: skillMeta.gradeBand || '',
        description: skillMeta.description || '',
        status: status,
        statusLabel: statusLabel,
        isWeak: isWeak,
        isDueForReview: isDueForReview,
        isMastered: status === 'MASTERED',
        totalAttempts: totalAttempts,
        totalCorrect: totalCorrect,
        totalAccuracy: totalAccuracy,
        recentAttempts: recentAttempts,
        recentCorrect: recentCorrect,
        recentAccuracy: recentAccuracy,
        previousAttempts: previousAttempts,
        previousCorrect: previousCorrect,
        previousAccuracy: previousAccuracy,
        hasPreviousComparison: hasPreviousComparison,
        trend: trend,
        trendText: trendText,
        growthSummary: growthSummary,
        lastPracticedAt: lastPracticedAt,
      };

      skillSnapshots.push(snapshot);

      if (status === 'MASTERED') {
        masteredSkills.push(snapshot);
      }

      // Attention Priority 후보 분류 (연습한 적이 있는 스킬 대상)
      if (totalAttempts > 0 || status !== 'NOT_STARTED') {
        let priorityRank = 99;
        if (status === 'STRUGGLING') {
          priorityRank = 1;
        } else if (status === 'NEEDS_REVIEW' || isDueForReview) {
          priorityRank = 2;
        } else if (status === 'PRACTICING' && isWeak) {
          priorityRank = 3;
        } else if (status === 'PRACTICING') {
          priorityRank = 4;
        }

        if (priorityRank <= 4) {
          attentionCandidates.push({
            snapshot: snapshot,
            priorityRank: priorityRank,
            orderIndex: index,
          });
        }
      }
    }

    // Attention Priority 결정론적 정렬: priorityRank 오름차순 -> orderIndex 오름차순 (canonical order tie-break)
    attentionCandidates.sort((a, b) => {
      if (a.priorityRank !== b.priorityRank) {
        return a.priorityRank - b.priorityRank;
      }
      return a.orderIndex - b.orderIndex;
    });

    const attentionSkills = attentionCandidates.slice(0, 3).map(c => c.snapshot);

    // 오늘의 목표 프로젝션 (Read-Only)
    let todayGoalSummary = null;
    if (dailyGoal && typeof dailyGoal === 'object') {
      const targetCount = typeof dailyGoal.targetCount === 'number' ? dailyGoal.targetCount : 5;
      const currentCount = typeof dailyGoal.currentCount === 'number' ? dailyGoal.currentCount : 0;
      const completed = Boolean(dailyGoal.completed);
      const skillName = dailyGoal.skillName || dailyGoal.shortName || (skillCatalog[dailyGoal.skillId]?.name || '수학 연습');
      const shortName = dailyGoal.shortName || dailyGoal.skillName || (skillCatalog[dailyGoal.skillId]?.shortName || '수학 연습');

      todayGoalSummary = {
        hasGoal: true,
        date: dailyGoal.date || '',
        goalId: dailyGoal.goalId || '',
        skillId: dailyGoal.skillId || '',
        skillName: skillName,
        shortName: shortName,
        targetCount: targetCount,
        currentCount: currentCount,
        completed: completed,
        completedAt: dailyGoal.completedAt || null,
        rewardGranted: Boolean(dailyGoal.rewardGranted),
        progressPercent: targetCount > 0
          ? Math.min(100, Math.round((currentCount / targetCount) * 100))
          : 0,
      };
    } else {
      todayGoalSummary = {
        hasGoal: false,
        date: '',
        goalId: '',
        skillId: '',
        skillName: '설정된 목표 없음',
        shortName: '목표 없음',
        targetCount: 5,
        currentCount: 0,
        completed: false,
        completedAt: null,
        rewardGranted: false,
        progressPercent: 0,
      };
    }

    // 전체 요약 집계
    const totalEvidenceCount = validEvidences.length;
    const practicedSkillCount = skillSnapshots.filter(s => s.totalAttempts > 0).length;
    const masteredSkillCount = masteredSkills.length;
    const strugglingSkillCount = skillSnapshots.filter(s => s.status === 'STRUGGLING').length;
    const needsReviewSkillCount = skillSnapshots.filter(s => s.status === 'NEEDS_REVIEW').length;

    return Object.freeze({
      isEmpty: isEmpty,
      generatedAt: now,
      summary: Object.freeze({
        totalEvidenceCount: totalEvidenceCount,
        practicedSkillCount: practicedSkillCount,
        masteredSkillCount: masteredSkillCount,
        strugglingSkillCount: strugglingSkillCount,
        needsReviewSkillCount: needsReviewSkillCount,
        totalSkillCount: skillOrder.length,
      }),
      todayGoal: Object.freeze(todayGoalSummary),
      attentionSkills: Object.freeze(attentionSkills),
      masteredSkills: Object.freeze(masteredSkills),
      skillSnapshots: Object.freeze(skillSnapshots),
      statusLabels: STATUS_LABELS,
    });
  }

  return Object.freeze({
    STATUS_LABELS: STATUS_LABELS,
    WINDOW_SIZE: WINDOW_SIZE,
    buildGuardianMathSnapshot: buildGuardianMathSnapshot,
  });
});
