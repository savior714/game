import test from 'node:test';
import assert from 'node:assert/strict';
import MathSkills from '../domains/math/skills.js';
import MathMasteryEngine from '../domains/math/mastery.js';
import MathGuardianSummary from '../domains/math/guardian-summary.js';

test('A. buildGuardianMathSnapshot returns identical snapshot for identical input and now (Deterministic)', () => {
  const now = 1700000000000;
  const evidenceList = [
    { skillId: 'math.add.within_10', correct: true, timestamp: now - 5000 },
    { skillId: 'math.add.within_10', correct: false, timestamp: now - 4000 },
    { skillId: 'math.add.within_10', correct: true, timestamp: now - 3000 },
  ];
  const masteryMap = MathMasteryEngine.computeAllSkillsMastery(
    MathSkills.MATH_SKILL_ORDER,
    evidenceList,
    now
  );
  const dailyGoal = {
    date: '2026-08-16',
    goalId: 'goal-2026-08-16-math.add.within_10-v1',
    skillId: 'math.add.within_10',
    skillName: '10 이하의 덧셈',
    shortName: '10 이하 덧셈',
    targetCount: 5,
    currentCount: 3,
    completed: false,
  };

  const snapshot1 = MathGuardianSummary.buildGuardianMathSnapshot({
    skillCatalog: MathSkills.MATH_SKILLS,
    skillOrder: MathSkills.MATH_SKILL_ORDER,
    evidenceList: evidenceList,
    masteryMap: masteryMap,
    dailyGoal: dailyGoal,
    now: now,
  });

  const snapshot2 = MathGuardianSummary.buildGuardianMathSnapshot({
    skillCatalog: MathSkills.MATH_SKILLS,
    skillOrder: MathSkills.MATH_SKILL_ORDER,
    evidenceList: evidenceList,
    masteryMap: masteryMap,
    dailyGoal: dailyGoal,
    now: now,
  });

  assert.deepEqual(snapshot1, snapshot2);
  assert.equal(snapshot1.isEmpty, false);
  assert.equal(snapshot1.summary.totalEvidenceCount, 3);
  assert.equal(snapshot1.summary.practicedSkillCount, 1);
});

test('B. Status mapping: NOT_STARTED, PRACTICING, MASTERED, NEEDS_REVIEW, STRUGGLING connect to proper guardian labels', () => {
  const now = 2000000000000;

  // 1. NOT_STARTED: no evidence
  // 2. MASTERED: 4 consecutive correct
  // 3. STRUGGLING: 3 consecutive failures
  // 4. NEEDS_REVIEW: mastered 50 hours ago
  const practiceTime = now - (50 * 60 * 60 * 1000);

  const evidenceList = [
    // math.add.within_10: MASTERED
    { skillId: 'math.add.within_10', correct: true, timestamp: now - 4000 },
    { skillId: 'math.add.within_10', correct: true, timestamp: now - 3000 },
    { skillId: 'math.add.within_10', correct: true, timestamp: now - 2000 },
    { skillId: 'math.add.within_10', correct: true, timestamp: now - 1000 },

    // math.add.within_20.carry: STRUGGLING
    { skillId: 'math.add.within_20.carry', correct: false, timestamp: now - 3000 },
    { skillId: 'math.add.within_20.carry', correct: false, timestamp: now - 2000 },
    { skillId: 'math.add.within_20.carry', correct: false, timestamp: now - 1000 },

    // math.subtract.within_10: NEEDS_REVIEW
    { skillId: 'math.subtract.within_10', correct: true, timestamp: practiceTime - 4000 },
    { skillId: 'math.subtract.within_10', correct: true, timestamp: practiceTime - 3000 },
    { skillId: 'math.subtract.within_10', correct: true, timestamp: practiceTime - 2000 },
    { skillId: 'math.subtract.within_10', correct: true, timestamp: practiceTime - 1000 },

    // math.multiply.basic_facts: PRACTICING (1 attempt)
    { skillId: 'math.multiply.basic_facts', correct: true, timestamp: now - 500 },
  ];

  const masteryMap = MathMasteryEngine.computeAllSkillsMastery(
    MathSkills.MATH_SKILL_ORDER,
    evidenceList,
    now
  );

  const snapshot = MathGuardianSummary.buildGuardianMathSnapshot({
    skillCatalog: MathSkills.MATH_SKILLS,
    skillOrder: MathSkills.MATH_SKILL_ORDER,
    evidenceList: evidenceList,
    masteryMap: masteryMap,
    now: now,
  });

  const sMap = {};
  for (const s of snapshot.skillSnapshots) {
    sMap[s.skillId] = s;
  }

  // math.add.within_10 -> MASTERED -> '잘하고 있어요'
  assert.equal(sMap['math.add.within_10'].status, 'MASTERED');
  assert.equal(sMap['math.add.within_10'].statusLabel, '잘하고 있어요');
  assert.equal(sMap['math.add.within_10'].isMastered, true);

  // math.add.within_20.carry -> STRUGGLING -> '도움이 필요해요'
  assert.equal(sMap['math.add.within_20.carry'].status, 'STRUGGLING');
  assert.equal(sMap['math.add.within_20.carry'].statusLabel, '도움이 필요해요');
  assert.equal(sMap['math.add.within_20.carry'].isWeak, true);

  // math.subtract.within_10 -> NEEDS_REVIEW -> '복습할 때예요'
  assert.equal(sMap['math.subtract.within_10'].status, 'NEEDS_REVIEW');
  assert.equal(sMap['math.subtract.within_10'].statusLabel, '복습할 때예요');
  assert.equal(sMap['math.subtract.within_10'].isDueForReview, true);

  // math.multiply.basic_facts -> PRACTICING -> '연습 중'
  assert.equal(sMap['math.multiply.basic_facts'].status, 'PRACTICING');
  assert.equal(sMap['math.multiply.basic_facts'].statusLabel, '연습 중');

  // math.add.multi_digit -> NOT_STARTED -> '시작 전'
  assert.equal(sMap['math.add.multi_digit'].status, 'NOT_STARTED');
  assert.equal(sMap['math.add.multi_digit'].statusLabel, '시작 전');
  assert.equal(sMap['math.add.multi_digit'].totalAttempts, 0);
});

test('C. Attention priority: STRUGGLING > NEEDS_REVIEW > weak PRACTICING > PRACTICING with canonical tie-break', () => {
  const now = 2000000000000;
  const practiceTime = now - (50 * 60 * 60 * 1000);

  const evidenceList = [
    // 1. math.multiply.basic_facts: STRUGGLING (rank 1)
    { skillId: 'math.multiply.basic_facts', correct: false, timestamp: now - 3000 },
    { skillId: 'math.multiply.basic_facts', correct: false, timestamp: now - 2000 },
    { skillId: 'math.multiply.basic_facts', correct: false, timestamp: now - 1000 },

    // 2. math.add.within_10: NEEDS_REVIEW (rank 2)
    { skillId: 'math.add.within_10', correct: true, timestamp: practiceTime - 4000 },
    { skillId: 'math.add.within_10', correct: true, timestamp: practiceTime - 3000 },
    { skillId: 'math.add.within_10', correct: true, timestamp: practiceTime - 2000 },
    { skillId: 'math.add.within_10', correct: true, timestamp: practiceTime - 1000 },

    // 3. math.subtract.within_10: PRACTICING (rank 4, earlier in canonical order)
    { skillId: 'math.subtract.within_10', correct: true, timestamp: now - 2000 },

    // 4. math.add.within_20.no_carry: PRACTICING (rank 4, later in canonical order)
    { skillId: 'math.add.within_20.no_carry', correct: true, timestamp: now - 1000 },
  ];

  const masteryMap = MathMasteryEngine.computeAllSkillsMastery(
    MathSkills.MATH_SKILL_ORDER,
    evidenceList,
    now
  );

  const snapshot = MathGuardianSummary.buildGuardianMathSnapshot({
    skillCatalog: MathSkills.MATH_SKILLS,
    skillOrder: MathSkills.MATH_SKILL_ORDER,
    evidenceList: evidenceList,
    masteryMap: masteryMap,
    now: now,
  });

  assert.equal(snapshot.attentionSkills.length, 3);
  assert.equal(snapshot.attentionSkills[0].skillId, 'math.multiply.basic_facts'); // STRUGGLING
  assert.equal(snapshot.attentionSkills[1].skillId, 'math.add.within_10');         // NEEDS_REVIEW
  assert.equal(snapshot.attentionSkills[2].skillId, 'math.subtract.within_10');    // PRACTICING (tie-break by skill order)
});

test('D. Raw evidence window separation: recent (max 5) vs previous (prior max 5) correctly partitioned', () => {
  const now = 1000000;
  // Create 12 attempts for math.add.within_10
  // attempts 1~2: correct (timestamp 100, 200) - older than 10
  // attempts 3~7: previous window (timestamp 300~700) -> 2 correct out of 5 (accuracy 0.4)
  // attempts 8~12: recent window (timestamp 800~1200) -> 4 correct out of 5 (accuracy 0.8)
  const evidenceList = [
    { skillId: 'math.add.within_10', correct: true, timestamp: 100 },
    { skillId: 'math.add.within_10', correct: true, timestamp: 200 },

    // Previous window (5 items)
    { skillId: 'math.add.within_10', correct: true, timestamp: 300 },
    { skillId: 'math.add.within_10', correct: false, timestamp: 400 },
    { skillId: 'math.add.within_10', correct: true, timestamp: 500 },
    { skillId: 'math.add.within_10', correct: false, timestamp: 600 },
    { skillId: 'math.add.within_10', correct: false, timestamp: 700 },

    // Recent window (5 items)
    { skillId: 'math.add.within_10', correct: true, timestamp: 800 },
    { skillId: 'math.add.within_10', correct: true, timestamp: 900 },
    { skillId: 'math.add.within_10', correct: true, timestamp: 1000 },
    { skillId: 'math.add.within_10', correct: false, timestamp: 1100 },
    { skillId: 'math.add.within_10', correct: true, timestamp: 1200 },
  ];

  const masteryMap = MathMasteryEngine.computeAllSkillsMastery(
    MathSkills.MATH_SKILL_ORDER,
    evidenceList,
    now
  );

  const snapshot = MathGuardianSummary.buildGuardianMathSnapshot({
    skillCatalog: MathSkills.MATH_SKILLS,
    skillOrder: MathSkills.MATH_SKILL_ORDER,
    evidenceList: evidenceList,
    masteryMap: masteryMap,
    now: now,
  });

  const skill = snapshot.skillSnapshots.find(s => s.skillId === 'math.add.within_10');
  assert.ok(skill);
  assert.equal(skill.totalAttempts, 12);
  assert.equal(skill.totalCorrect, 8);

  assert.equal(skill.recentAttempts, 5);
  assert.equal(skill.recentCorrect, 4);
  assert.equal(skill.recentAccuracy, 0.8);

  assert.equal(skill.previousAttempts, 5);
  assert.equal(skill.previousCorrect, 2);
  assert.equal(skill.previousAccuracy, 0.4);

  assert.equal(skill.hasPreviousComparison, true);
  assert.equal(skill.trend, 'improved');
  assert.equal(skill.trendText, '상승');
  assert.ok(skill.growthSummary.includes('최근 5문제 중 4정답'));
  assert.ok(skill.growthSummary.includes('상승'));
});

test('E. Evidence deficiency: does not synthesize growth or fake models when previous window is absent', () => {
  const now = 1000000;
  // Only 3 attempts (less than 6, so no previous window)
  const evidenceList = [
    { skillId: 'math.add.within_10', correct: true, timestamp: 800 },
    { skillId: 'math.add.within_10', correct: true, timestamp: 900 },
    { skillId: 'math.add.within_10', correct: false, timestamp: 1000 },
  ];

  const masteryMap = MathMasteryEngine.computeAllSkillsMastery(
    MathSkills.MATH_SKILL_ORDER,
    evidenceList,
    now
  );

  const snapshot = MathGuardianSummary.buildGuardianMathSnapshot({
    skillCatalog: MathSkills.MATH_SKILLS,
    skillOrder: MathSkills.MATH_SKILL_ORDER,
    evidenceList: evidenceList,
    masteryMap: masteryMap,
    now: now,
  });

  const skill = snapshot.skillSnapshots.find(s => s.skillId === 'math.add.within_10');
  assert.ok(skill);
  assert.equal(skill.recentAttempts, 3);
  assert.equal(skill.recentCorrect, 2);
  assert.equal(skill.previousAttempts, 0);
  assert.equal(skill.hasPreviousComparison, false);
  assert.equal(skill.trend, 'none');
  assert.ok(skill.growthSummary.includes('이전 기록 쌓이는 중') || skill.growthSummary.includes('더 쌓이면'));
});

test('F. Read-only guarantee: input arrays, objects, and evidence store are not mutated', () => {
  const now = 1000000;
  const originalEvidence = Object.freeze({
    id: 'ev-1',
    skillId: 'math.add.within_10',
    correct: true,
    timestamp: 500,
  });
  const evidenceList = Object.freeze([originalEvidence]);
  const skillOrder = Object.freeze([...MathSkills.MATH_SKILL_ORDER]);
  const dailyGoal = Object.freeze({
    date: '2026-08-16',
    goalId: 'g1',
    skillId: 'math.add.within_10',
    targetCount: 5,
    currentCount: 2,
    completed: false,
  });

  const snapshot = MathGuardianSummary.buildGuardianMathSnapshot({
    skillCatalog: MathSkills.MATH_SKILLS,
    skillOrder: skillOrder,
    evidenceList: evidenceList,
    dailyGoal: dailyGoal,
    now: now,
  });

  // Verify snapshot object exists and input is unchanged
  assert.ok(snapshot);
  assert.equal(evidenceList.length, 1);
  assert.equal(evidenceList[0], originalEvidence);
  assert.equal(dailyGoal.currentCount, 2);
  assert.equal(dailyGoal.completed, false);
});
