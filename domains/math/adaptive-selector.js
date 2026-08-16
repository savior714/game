/**
 * @fileoverview 수학 적응형 스킬/문항 선택기 (Math Adaptive Selector)
 * @module math/adaptive-selector
 *
 * 단순 연산 정확도 중심이 아닌 스킬 숙달도(Mastery) 및 일일 목표 기반 문항 선택.
 * 1. 목표 학습 스킬(Target Skill)
 * 2. 취약/부진 스킬(Weak/Struggling Skill)
 * 3. 간격 복습 필요 스킬(Due Review Skill)
 * 4. 성공 경험 유지(Confidence Builder)
 * 사이의 균형을 유지하며, 직전 문항 반복 방지 및 비상 문항 보장 불변식을 준수.
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.MathAdaptiveSelector = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  function _questionKey(candidate) {
    const a = candidate.a;
    const b = candidate.b;
    const sorted = [a, b].sort((x, y) => x - y);
    return `${sorted[0]},${sorted[1]}${candidate.op}`;
  }

  function _buildEmergencyCandidate(lastQuestionKey, MathSkills) {
    const emergencyCandidates = [
      { a: 1, b: 1, op: '+', result: 2, tag: 'add_unit_1_1', skillId: 'math.add.within_10', level: 0 },
      { a: 1, b: 2, op: '+', result: 3, tag: 'add_unit_1_2', skillId: 'math.add.within_10', level: 0 },
      { a: 2, b: 2, op: '+', result: 4, tag: 'add_unit_2_2', skillId: 'math.add.within_10', level: 0 },
    ];
    for (const c of emergencyCandidates) {
      if (_questionKey(c) !== lastQuestionKey) {
        return c;
      }
    }
    return emergencyCandidates[0];
  }

  /**
   * 가중치 기반 카테고리/스킬 선택
   */
  function _pickSkillId({ dailyGoalSkillId, masteryMap, skillOrder, rng }) {
    const skills = skillOrder || [];
    const targetSkillId = dailyGoalSkillId || skills[0] || 'math.add.within_10';

    const weakSkills = [];
    const reviewSkills = [];
    const masteredSkills = [];
    const unmasteredSkills = [];

    for (const sId of skills) {
      const m = masteryMap && masteryMap[sId];
      if (!m || m.status === 'NOT_STARTED') {
        unmasteredSkills.push(sId);
      } else if (m.status === 'NEEDS_REVIEW' || m.isDueForReview) {
        reviewSkills.push(sId);
      } else if (m.status === 'STRUGGLING' || m.isWeak) {
        weakSkills.push(sId);
      } else if (m.status === 'MASTERED') {
        masteredSkills.push(sId);
      } else {
        unmasteredSkills.push(sId);
      }
    }

    // 풀 가중치 구성
    const weights = [];

    // 1. 목표 스킬 (45%)
    weights.push({
      category: 'target',
      weight: 0.45,
      skillId: targetSkillId,
    });

    // 2. 취약 스킬 (30%)
    if (weakSkills.length > 0) {
      const picked = weakSkills[Math.floor(rng() * weakSkills.length)];
      weights.push({ category: 'weak', weight: 0.30, skillId: picked });
    }

    // 3. 복습 스킬 (15%)
    if (reviewSkills.length > 0) {
      const picked = reviewSkills[Math.floor(rng() * reviewSkills.length)];
      weights.push({ category: 'review', weight: 0.15, skillId: picked });
    }

    // 4. 성공 경험 (10%)
    if (masteredSkills.length > 0) {
      const picked = masteredSkills[Math.floor(rng() * masteredSkills.length)];
      weights.push({ category: 'success', weight: 0.10, skillId: picked });
    } else {
      // 마스터한 스킬이 아직 없으면 가장 기초 스킬(10 이하 덧셈)을 성공 경험용으로 제공
      weights.push({ category: 'success', weight: 0.10, skillId: 'math.add.within_10' });
    }

    const totalWeight = weights.reduce((sum, w) => sum + w.weight, 0);
    let r = rng() * totalWeight;
    for (const w of weights) {
      r -= w.weight;
      if (r <= 0) {
        return { skillId: w.skillId, category: w.category };
      }
    }

    return { skillId: targetSkillId, category: 'target' };
  }

  /**
   * 적응형 다음 문항 선택 및 생성
   * @param {Object} params
   * @param {string} [params.dailyGoalSkillId]
   * @param {Object} [params.masteryMap]
   * @param {Array<string>} [params.skillOrder]
   * @param {Array<string>} [params.recentQuestions]
   * @param {string} [params.lastQuestionKey]
   * @param {Array<Object>} [params.wrongPatterns]
   * @param {number} [params.reinforceProb]
   * @param {() => number} [params.rng]
   * @param {Object} params.MathSkills - MathSkills 모듈 참조
   * @returns {Object} 생성된 문항 객체
   */
  function selectNextQuestion(params) {
    const p = params || {};
    const MathSkills = p.MathSkills;
    if (!MathSkills || typeof MathSkills.generateQuestionForSkill !== 'function') {
      throw new Error('MathAdaptiveSelector: MathSkills module is required');
    }

    const rng = typeof p.rng === 'function' ? p.rng : Math.random;
    const recentQuestions = Array.isArray(p.recentQuestions) ? p.recentQuestions : [];
    const lastQuestionKey = typeof p.lastQuestionKey === 'string' ? p.lastQuestionKey : '';
    const wrongPatterns = Array.isArray(p.wrongPatterns) ? p.wrongPatterns : [];
    const reinforceProb = typeof p.reinforceProb === 'number' ? p.reinforceProb : 0.45;

    // 1. 오답 정확 재출제 (강화 복습)
    if (wrongPatterns.length > 0 && rng() < reinforceProb) {
      const wrong = wrongPatterns[Math.floor(rng() * wrongPatterns.length)];
      const result = wrong.op === '+' ? wrong.a + wrong.b : (wrong.op === '-' ? wrong.a - wrong.b : wrong.a * wrong.b);
      const skillId = wrong.skillId || MathSkills.classifyMathSkill(wrong.a, wrong.b, wrong.op);
      const candidate = {
        a: wrong.a,
        b: wrong.b,
        op: wrong.op,
        result: result,
        skillId: skillId,
        tag: wrong.tag || MathSkills.extractLegacyTag(wrong.a, wrong.b, wrong.op),
        curriculumRef: (MathSkills.MATH_SKILLS[skillId] && MathSkills.MATH_SKILLS[skillId].curriculumRef) || '',
        isWeakness: true,
        isReinforcement: true,
      };

      if (_questionKey(candidate) !== lastQuestionKey) {
        return candidate;
      }
    }

    // 2. 스킬 숙달도 기반 적응형 생성 (20회 시도)
    const skillOrder = p.skillOrder || MathSkills.MATH_SKILL_ORDER;
    for (let tries = 0; tries < 20; tries++) {
      const selection = _pickSkillId({
        dailyGoalSkillId: p.dailyGoalSkillId,
        masteryMap: p.masteryMap,
        skillOrder: skillOrder,
        rng: rng,
      });

      const candidate = MathSkills.generateQuestionForSkill(selection.skillId, { rng: rng });
      candidate.isWeakness = (selection.category === 'weak');
      candidate.isReinforcement = false;

      const key = _questionKey(candidate);
      if (key !== lastQuestionKey && !recentQuestions.includes(key)) {
        return candidate;
      }
    }

    // 3. 최근 10개 중복 제한만 완화하여 직전 문항 반복만 금지 (20회 시도)
    for (let fallbackTries = 0; fallbackTries < 20; fallbackTries++) {
      const selection = _pickSkillId({
        dailyGoalSkillId: p.dailyGoalSkillId,
        masteryMap: p.masteryMap,
        skillOrder: skillOrder,
        rng: rng,
      });
      const candidate = MathSkills.generateQuestionForSkill(selection.skillId, { rng: rng });
      candidate.isWeakness = (selection.category === 'weak');
      candidate.isReinforcement = false;

      if (_questionKey(candidate) !== lastQuestionKey) {
        return candidate;
      }
    }

    // 4. 비상 문항 반환
    return _buildEmergencyCandidate(lastQuestionKey, MathSkills);
  }

  return Object.freeze({
    selectNextQuestion: selectNextQuestion,
  });
});
