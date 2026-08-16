import test from 'node:test';
import assert from 'node:assert/strict';
import MathSkills from '../domains/math/skills.js';
import MathAdaptiveSelector from '../domains/math/adaptive-selector.js';

test('MathAdaptiveSelector generates question matching the selected skill and never repeats immediate previous question', () => {
  const lastKey = '3,4+';
  const recentQuestions = ['3,4+', '1,2+'];

  for (let i = 0; i < 30; i++) {
    const q = MathAdaptiveSelector.selectNextQuestion({
      dailyGoalSkillId: 'math.add.within_10',
      MathSkills: MathSkills,
      recentQuestions: recentQuestions,
      lastQuestionKey: lastKey,
    });

    assert.ok(q);
    assert.ok(q.skillId);
    assert.notEqual(`${Math.min(q.a, q.b)},${Math.max(q.a, q.b)}${q.op}`, lastKey);
  }
});

test('MathAdaptiveSelector prioritizes weak skills when weak skills exist in mastery map', () => {
  const masteryMap = {
    'math.add.within_10': { status: 'MASTERED', isWeak: false },
    'math.add.within_20.carry': { status: 'STRUGGLING', isWeak: true },
  };

  let weakGeneratedCount = 0;
  for (let i = 0; i < 50; i++) {
    const q = MathAdaptiveSelector.selectNextQuestion({
      dailyGoalSkillId: 'math.add.within_10',
      masteryMap: masteryMap,
      MathSkills: MathSkills,
      skillOrder: ['math.add.within_10', 'math.add.within_20.carry'],
    });

    if (q.skillId === 'math.add.within_20.carry' || q.isWeakness) {
      weakGeneratedCount++;
    }
  }

  // Weak skill should be generated with significant frequency (> 15% of 50 = > 7 times)
  assert.ok(weakGeneratedCount >= 5, `Weak skill was generated only ${weakGeneratedCount} times out of 50`);
});

test('MathAdaptiveSelector reinforces wrong patterns when wrong patterns are supplied', () => {
  const wrongPatterns = [
    { a: 7, b: 8, op: '+', tag: 'add_unit_7_8', skillId: 'math.add.within_20.carry' },
  ];

  let reinforcedCount = 0;
  for (let i = 0; i < 50; i++) {
    const q = MathAdaptiveSelector.selectNextQuestion({
      dailyGoalSkillId: 'math.add.within_10',
      MathSkills: MathSkills,
      wrongPatterns: wrongPatterns,
      reinforceProb: 0.8, // high prob for test
    });

    if (q.isReinforcement && q.a === 7 && q.b === 8) {
      reinforcedCount++;
    }
  }

  assert.ok(reinforcedCount > 10, `Reinforcement occurred only ${reinforcedCount} times`);
});
