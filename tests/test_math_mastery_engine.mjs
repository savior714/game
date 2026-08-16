import test from 'node:test';
import assert from 'node:assert/strict';
import MathMasteryEngine from '../domains/math/mastery.js';

test('MathMasteryEngine returns NOT_STARTED for skills with zero attempts', () => {
  const result = MathMasteryEngine.computeSkillMastery('math.add.within_10', [], 1000);
  assert.equal(result.status, 'NOT_STARTED');
  assert.equal(result.score, 0.0);
  assert.equal(result.totalAttempts, 0);
  assert.equal(result.isMastered, false);
});

test('MathMasteryEngine marks skill MASTERED on repeated success sequence', () => {
  const now = 1000000;
  const evidences = [
    { skillId: 'math.add.within_10', correct: true, timestamp: now - 3000 },
    { skillId: 'math.add.within_10', correct: true, timestamp: now - 2000 },
    { skillId: 'math.add.within_10', correct: true, timestamp: now - 1000 },
    { skillId: 'math.add.within_10', correct: true, timestamp: now },
  ];

  const result = MathMasteryEngine.computeSkillMastery('math.add.within_10', evidences, now);
  assert.equal(result.status, 'MASTERED');
  assert.equal(result.isMastered, true);
  assert.equal(result.recentAccuracy, 1.0);
  assert.equal(result.consecutiveCorrect, 4);
  assert.equal(result.isWeak, false);
  assert.ok(result.score >= 0.9);
});

test('MathMasteryEngine marks skill STRUGGLING on repeated failures', () => {
  const now = 1000000;
  const evidences = [
    { skillId: 'math.add.within_20.carry', correct: false, timestamp: now - 3000 },
    { skillId: 'math.add.within_20.carry', correct: false, timestamp: now - 2000 },
    { skillId: 'math.add.within_20.carry', correct: false, timestamp: now - 1000 },
  ];

  const result = MathMasteryEngine.computeSkillMastery('math.add.within_20.carry', evidences, now);
  assert.equal(result.status, 'STRUGGLING');
  assert.equal(result.isMastered, false);
  assert.equal(result.isWeak, true);
  assert.equal(result.recentAccuracy, 0.0);
});

test('MathMasteryEngine transitions mastered skill to NEEDS_REVIEW after spaced review interval', () => {
  const practiceTime = 1000000;
  const reviewTime = practiceTime + (50 * 60 * 60 * 1000); // 50 hours later (> 48h)
  const evidences = [
    { skillId: 'math.add.within_10', correct: true, timestamp: practiceTime - 3000 },
    { skillId: 'math.add.within_10', correct: true, timestamp: practiceTime - 2000 },
    { skillId: 'math.add.within_10', correct: true, timestamp: practiceTime - 1000 },
    { skillId: 'math.add.within_10', correct: true, timestamp: practiceTime },
  ];

  // Immediately after practice: MASTERED
  const immediateResult = MathMasteryEngine.computeSkillMastery('math.add.within_10', evidences, practiceTime);
  assert.equal(immediateResult.status, 'MASTERED');
  assert.equal(immediateResult.isDueForReview, false);

  // 50 hours later: NEEDS_REVIEW
  const laterResult = MathMasteryEngine.computeSkillMastery('math.add.within_10', evidences, reviewTime);
  assert.equal(laterResult.status, 'NEEDS_REVIEW');
  assert.equal(laterResult.isDueForReview, true);
});

test('computeAllSkillsMastery computes results deterministically for all requested skills', () => {
  const now = 2000000;
  const evidences = [
    { skillId: 'math.add.within_10', correct: true, timestamp: now },
  ];
  const allSkills = ['math.add.within_10', 'math.multiply.basic_facts'];

  const results = MathMasteryEngine.computeAllSkillsMastery(allSkills, evidences, now);
  assert.equal(results['math.add.within_10'].totalAttempts, 1);
  assert.equal(results['math.multiply.basic_facts'].status, 'NOT_STARTED');
});
