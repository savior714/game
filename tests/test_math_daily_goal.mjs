import test from 'node:test';
import assert from 'node:assert/strict';
import MathDailyGoalEngine from '../domains/math/daily-goal.js';
import MathSkills from '../domains/math/skills.js';

class MockStorage {
  constructor() {
    this.map = new Map();
  }
  getItem(key) {
    return this.map.has(key) ? this.map.get(key) : null;
  }
  setItem(key, value) {
    this.map.set(key, String(value));
  }
  removeItem(key) {
    this.map.delete(key);
  }
  clear() {
    this.map.clear();
  }
}

class MockRewardSystem {
  constructor() {
    this.inventory = { gems: 0, youtube: 0 };
    this.calls = [];
  }
  add(type, amount) {
    this.inventory[type] = (this.inventory[type] || 0) + amount;
    this.calls.push({ type, amount });
  }
}

test('MathDailyGoalEngine initializes daily goal for today and persists across reloads', () => {
  const storage = new MockStorage();
  const now = Date.parse('2026-08-16T09:00:00.000Z');

  const goal = MathDailyGoalEngine.initOrGetDailyGoal({
    storage,
    now,
    skillCatalog: MathSkills.MATH_SKILLS,
    skillOrder: MathSkills.MATH_SKILL_ORDER,
  });

  assert.equal(goal.date, '2026-08-16');
  assert.equal(goal.skillId, 'math.add.within_10');
  assert.equal(goal.targetCount, 5);
  assert.equal(goal.currentCount, 0);
  assert.equal(goal.completed, false);
  assert.equal(goal.rewardGranted, false);

  // Reload on the same day restores the exact same goal
  const restored = MathDailyGoalEngine.initOrGetDailyGoal({
    storage,
    now: now + 3600000,
    skillCatalog: MathSkills.MATH_SKILLS,
    skillOrder: MathSkills.MATH_SKILL_ORDER,
  });

  assert.equal(restored.goalId, goal.goalId);
  assert.equal(restored.skillId, goal.skillId);
});

test('MathDailyGoalEngine updates progress on correct answers and completes on target', () => {
  const storage = new MockStorage();
  const now = Date.parse('2026-08-16T09:00:00.000Z');

  const goal = MathDailyGoalEngine.initOrGetDailyGoal({
    storage,
    now,
    skillCatalog: MathSkills.MATH_SKILLS,
  });

  // 1 to 4 correct answers
  for (let i = 1; i <= 4; i++) {
    const res = MathDailyGoalEngine.recordGoalProgress({
      goal,
      skillId: goal.skillId,
      correct: true,
      storage,
      now,
    });
    assert.equal(res.goal.currentCount, i);
    assert.equal(res.completedJustNow, false);
    assert.equal(res.goal.completed, false);
  }

  // Wrong answer does not increase progress
  const wrongRes = MathDailyGoalEngine.recordGoalProgress({
    goal,
    skillId: goal.skillId,
    correct: false,
    storage,
    now,
  });
  assert.equal(wrongRes.goal.currentCount, 4);

  // 5th correct answer completes goal
  const completeRes = MathDailyGoalEngine.recordGoalProgress({
    goal,
    skillId: goal.skillId,
    correct: true,
    storage,
    now: now + 1000,
  });
  assert.equal(completeRes.goal.currentCount, 5);
  assert.equal(completeRes.completedJustNow, true);
  assert.equal(completeRes.goal.completed, true);
  assert.equal(completeRes.goal.completedAt, now + 1000);
});

test('MathDailyGoalEngine claims reward exactly once (IDEMPOTENT)', () => {
  const storage = new MockStorage();
  const rewardSystem = new MockRewardSystem();
  const now = Date.parse('2026-08-16T09:00:00.000Z');

  const goal = MathDailyGoalEngine.initOrGetDailyGoal({
    storage,
    now,
    skillCatalog: MathSkills.MATH_SKILLS,
  });

  // Attempt reward before complete -> rejected
  const premature = MathDailyGoalEngine.claimGoalReward({ goal, rewardSystem, storage, now });
  assert.equal(premature.success, false);
  assert.equal(premature.reason, 'not_completed');
  assert.equal(rewardSystem.calls.length, 0);

  // Complete goal
  goal.currentCount = 5;
  goal.completed = true;
  goal.completedAt = now;

  // First claim -> succeeds
  const firstClaim = MathDailyGoalEngine.claimGoalReward({ goal, rewardSystem, storage, now });
  assert.equal(firstClaim.success, true);
  assert.equal(firstClaim.gems, 2);
  assert.equal(firstClaim.freeTimeMinutes, 10);
  assert.equal(rewardSystem.inventory.gems, 2);
  assert.equal(rewardSystem.inventory.youtube, 1);
  assert.equal(goal.rewardGranted, true);

  // Second claim -> rejected (already claimed)
  const secondClaim = MathDailyGoalEngine.claimGoalReward({ goal, rewardSystem, storage, now });
  assert.equal(secondClaim.success, false);
  assert.equal(secondClaim.reason, 'already_claimed');
  assert.equal(rewardSystem.inventory.gems, 2); // No increase!
  assert.equal(rewardSystem.inventory.youtube, 1); // No increase!
  assert.equal(rewardSystem.calls.length, 2); // only 1 gems + 1 youtube from first claim
});

test('MathDailyGoalEngine generates a new goal on the next day', () => {
  const storage = new MockStorage();
  const day1 = Date.parse('2026-08-16T09:00:00.000Z');
  const day2 = Date.parse('2026-08-17T09:00:00.000Z');

  const goal1 = MathDailyGoalEngine.initOrGetDailyGoal({
    storage,
    now: day1,
    skillCatalog: MathSkills.MATH_SKILLS,
    skillOrder: MathSkills.MATH_SKILL_ORDER,
  });
  assert.equal(goal1.date, '2026-08-16');

  const goal2 = MathDailyGoalEngine.initOrGetDailyGoal({
    storage,
    now: day2,
    skillCatalog: MathSkills.MATH_SKILLS,
    skillOrder: MathSkills.MATH_SKILL_ORDER,
  });
  assert.equal(goal2.date, '2026-08-17');
  assert.notEqual(goal1.goalId, goal2.goalId);
});
