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

test('MathDailyGoalEngine integrates with RewardSystem.grantWithReceipt and handles partial-failure recovery', () => {
  class MockReceiptRewardSystem {
    constructor() {
      this.inventory = { gems: 0, youtube_minutes: 0 };
      this.receipts = new Map();
    }
    hasReceipt(id) {
      return this.receipts.has(id);
    }
    grantWithReceipt(receiptId, grants) {
      if (this.hasReceipt(receiptId)) {
        return { success: false, reason: 'already_claimed', alreadyClaimed: true };
      }
      for (const g of grants) {
        if (g.type === 'gems') this.inventory.gems += g.amount;
        if (g.type === 'youtube') this.inventory.youtube_minutes += g.amount * 10;
      }
      this.receipts.set(receiptId, grants);
      return { success: true, alreadyClaimed: false };
    }
  }

  const storage = new MockStorage();
  const rewardSystem = new MockReceiptRewardSystem();
  const now = Date.parse('2026-08-16T09:00:00.000Z');

  const goal = MathDailyGoalEngine.initOrGetDailyGoal({
    storage,
    now,
    skillCatalog: MathSkills.MATH_SKILLS,
  });
  goal.completed = true;
  goal.currentCount = 5;
  goal.completedAt = now;

  // 1. Initial claim with grantWithReceipt
  const claim1 = MathDailyGoalEngine.claimGoalReward({ goal, rewardSystem, storage, now });
  assert.equal(claim1.success, true);
  assert.equal(rewardSystem.inventory.gems, 2);
  assert.equal(rewardSystem.inventory.youtube_minutes, 10);
  assert.equal(rewardSystem.hasReceipt(goal.rewardReceiptId), true);
  assert.equal(goal.rewardGranted, true);

  // 2. Partial failure simulation: goal in memory says rewardGranted=false, but RewardSystem has receipt
  goal.rewardGranted = false;
  const claim2 = MathDailyGoalEngine.claimGoalReward({ goal, rewardSystem, storage, now });
  assert.equal(claim2.success, false);
  assert.equal(claim2.reason, 'already_claimed');
  assert.equal(rewardSystem.inventory.gems, 2); // Unchanged!
  assert.equal(rewardSystem.inventory.youtube_minutes, 10); // Unchanged!
  assert.equal(goal.rewardGranted, true); // Recovered!

  // 3. Partial failure simulation: rewardSystem has no receipt in memory, but storage has receiptKey
  const freshRewardSystem = new MockReceiptRewardSystem();
  goal.rewardGranted = false;
  const claim3 = MathDailyGoalEngine.claimGoalReward({ goal, rewardSystem: freshRewardSystem, storage, now });
  assert.equal(claim3.success, false);
  assert.equal(claim3.reason, 'already_claimed');
  assert.equal(freshRewardSystem.inventory.gems, 0); // No accidental grant!
  assert.equal(goal.rewardGranted, true);
});

test('MathDailyGoalEngine Presets: missing preference defaults to standard 5', () => {
  const storage = new MockStorage();
  const now = Date.parse('2026-08-16T09:00:00.000Z');

  const pref = MathDailyGoalEngine.loadGoalPreference({ storage });
  assert.equal(pref.presetId, 'standard');

  const goal = MathDailyGoalEngine.initOrGetDailyGoal({
    storage,
    now,
    skillCatalog: MathSkills.MATH_SKILLS,
    skillOrder: MathSkills.MATH_SKILL_ORDER,
  });
  assert.equal(goal.targetCount, 5);
});

test('MathDailyGoalEngine Presets: light preset creates new goal with targetCount 3', () => {
  const storage = new MockStorage();
  const now = Date.parse('2026-08-16T09:00:00.000Z');

  MathDailyGoalEngine.saveGoalPreference('light', { storage, now });
  const pref = MathDailyGoalEngine.loadGoalPreference({ storage });
  assert.equal(pref.presetId, 'light');

  const goal = MathDailyGoalEngine.initOrGetDailyGoal({
    storage,
    now,
    skillCatalog: MathSkills.MATH_SKILLS,
    skillOrder: MathSkills.MATH_SKILL_ORDER,
  });
  assert.equal(goal.targetCount, 3);
});

test('MathDailyGoalEngine Presets: challenge preset creates new goal with targetCount 7', () => {
  const storage = new MockStorage();
  const now = Date.parse('2026-08-16T09:00:00.000Z');

  MathDailyGoalEngine.saveGoalPreference('challenge', { storage, now });
  const pref = MathDailyGoalEngine.loadGoalPreference({ storage });
  assert.equal(pref.presetId, 'challenge');

  const goal = MathDailyGoalEngine.initOrGetDailyGoal({
    storage,
    now,
    skillCatalog: MathSkills.MATH_SKILLS,
    skillOrder: MathSkills.MATH_SKILL_ORDER,
  });
  assert.equal(goal.targetCount, 7);
});

test('MathDailyGoalEngine Presets: skill selection logic remains identical regardless of preset', () => {
  const now = Date.parse('2026-08-16T09:00:00.000Z');
  const masteryMap = {
    'math.add.within_10': { status: 'MASTERED' },
    'math.add.within_20.carry': { status: 'STRUGGLING', isWeak: true },
  };

  const storageLight = new MockStorage();
  MathDailyGoalEngine.saveGoalPreference('light', { storage: storageLight });
  const goalLight = MathDailyGoalEngine.initOrGetDailyGoal({
    storage: storageLight,
    now,
    masteryMap,
    skillCatalog: MathSkills.MATH_SKILLS,
    skillOrder: MathSkills.MATH_SKILL_ORDER,
  });

  const storageChallenge = new MockStorage();
  MathDailyGoalEngine.saveGoalPreference('challenge', { storage: storageChallenge });
  const goalChallenge = MathDailyGoalEngine.initOrGetDailyGoal({
    storage: storageChallenge,
    now,
    masteryMap,
    skillCatalog: MathSkills.MATH_SKILLS,
    skillOrder: MathSkills.MATH_SKILL_ORDER,
  });

  assert.equal(goalLight.skillId, 'math.add.within_20.carry');
  assert.equal(goalChallenge.skillId, 'math.add.within_20.carry');
  assert.equal(goalLight.targetCount, 3);
  assert.equal(goalChallenge.targetCount, 7);
});

test('MathDailyGoalEngine Presets: malformed or unknown preference fails soft to standard 5', () => {
  const storage = new MockStorage();
  const now = Date.parse('2026-08-16T09:00:00.000Z');

  // Unknown presetId
  storage.setItem(MathDailyGoalEngine.PREFERENCE_STORAGE_KEY, JSON.stringify({ schemaVersion: 1, presetId: 'invalid_super_hard' }));
  const prefUnknown = MathDailyGoalEngine.loadGoalPreference({ storage });
  assert.equal(prefUnknown.presetId, 'standard');

  const goalUnknown = MathDailyGoalEngine.initOrGetDailyGoal({
    storage,
    now,
    skillCatalog: MathSkills.MATH_SKILLS,
  });
  assert.equal(goalUnknown.targetCount, 5);

  // Corrupted JSON
  storage.setItem(MathDailyGoalEngine.PREFERENCE_STORAGE_KEY, '{ invalid json');
  const prefCorrupted = MathDailyGoalEngine.loadGoalPreference({ storage });
  assert.equal(prefCorrupted.presetId, 'standard');

  const storageCorrupted = new MockStorage();
  storageCorrupted.setItem(MathDailyGoalEngine.PREFERENCE_STORAGE_KEY, '{ invalid json');
  const goalCorrupted = MathDailyGoalEngine.initOrGetDailyGoal({
    storage: storageCorrupted,
    now,
    skillCatalog: MathSkills.MATH_SKILLS,
  });
  assert.equal(goalCorrupted.targetCount, 5);
});

test('MathDailyGoalEngine Presets HARD RULE: existing today goal is never rewritten on preference change', () => {
  const storage = new MockStorage();
  const now = Date.parse('2026-08-16T09:00:00.000Z');

  // 1. Create standard (5) goal today and progress 2/5
  const goal = MathDailyGoalEngine.initOrGetDailyGoal({
    storage,
    now,
    skillCatalog: MathSkills.MATH_SKILLS,
  });
  assert.equal(goal.targetCount, 5);
  MathDailyGoalEngine.recordGoalProgress({ goal, skillId: goal.skillId, correct: true, storage, now });
  MathDailyGoalEngine.recordGoalProgress({ goal, skillId: goal.skillId, correct: true, storage, now });
  assert.equal(goal.currentCount, 2);
  assert.equal(goal.completed, false);
  const initialReceiptId = goal.rewardReceiptId;

  // 2. Guardian changes preference to light (3) or challenge (7)
  MathDailyGoalEngine.saveGoalPreference('light', { storage });

  // 3. Calling initOrGetDailyGoal on the same day returns the existing goal untouched
  const todayGoal = MathDailyGoalEngine.initOrGetDailyGoal({
    storage,
    now: now + 60000,
    skillCatalog: MathSkills.MATH_SKILLS,
  });
  assert.equal(todayGoal.targetCount, 5); // NOT changed to 3!
  assert.equal(todayGoal.currentCount, 2);
  assert.equal(todayGoal.completed, false);
  assert.equal(todayGoal.rewardReceiptId, initialReceiptId);

  // 4. Next day's goal applies the new light preset (3)
  const nextDay = now + 86400000;
  const nextDayGoal = MathDailyGoalEngine.initOrGetDailyGoal({
    storage,
    now: nextDay,
    skillCatalog: MathSkills.MATH_SKILLS,
  });
  assert.equal(nextDayGoal.targetCount, 3);
  assert.equal(nextDayGoal.currentCount, 0);
});

test('MathDailyGoalEngine Presets: saving preference causes 0 mutation to evidence/mastery/stats/rewards', () => {
  const storage = new MockStorage();
  storage.setItem('aiden_math_stats', JSON.stringify({ '+': { levels: {} } }));
  storage.setItem('aiden_math_learning_evidence_v1', JSON.stringify({ schemaVersion: 1, items: [] }));
  storage.setItem('study_rewards', JSON.stringify({ gems: 10 }));

  const statsBefore = storage.getItem('aiden_math_stats');
  const evidenceBefore = storage.getItem('aiden_math_learning_evidence_v1');
  const rewardsBefore = storage.getItem('study_rewards');

  MathDailyGoalEngine.saveGoalPreference('challenge', { storage });

  assert.equal(storage.getItem('aiden_math_stats'), statsBefore);
  assert.equal(storage.getItem('aiden_math_learning_evidence_v1'), evidenceBefore);
  assert.equal(storage.getItem('study_rewards'), rewardsBefore);
});

// ── Math Daily Streak Unit Tests ──────────────────────────────────────────

test('MathDailyGoalEngine Streak 1: first-run initializes streak at 0 without retroactive decay', () => {
  const storage = new MockStorage();
  const now = Date.parse('2026-08-16T09:00:00.000Z');

  const streak = MathDailyGoalEngine.initOrGetStreak({ storage, now });
  assert.equal(streak.schemaVersion, 1);
  assert.equal(streak.currentStreak, 0);
  assert.equal(streak.lastObservedDate, '2026-08-16');
  assert.equal(streak.lastCompletedDate, null);
});

test('MathDailyGoalEngine Streak 2: real daily goal completion increments streak by 1 exactly once', () => {
  const storage = new MockStorage();
  const now = Date.parse('2026-08-16T09:00:00.000Z');

  const goal = MathDailyGoalEngine.initOrGetDailyGoal({ storage, now, skillCatalog: MathSkills.MATH_SKILLS });
  assert.equal(goal.completed, false);

  // Complete goal with targetCount (5)
  for (let i = 0; i < 5; i++) {
    const res = MathDailyGoalEngine.recordGoalProgress({
      goal,
      skillId: goal.skillId,
      correct: true,
      storage,
      now: now + i * 1000,
    });
    if (i < 4) {
      assert.equal(res.completedJustNow, false);
      assert.equal(res.streakResult, null);
    } else {
      assert.equal(res.completedJustNow, true);
      assert.ok(res.streakResult);
      assert.equal(res.streakResult.currentStreak, 1);
      assert.equal(res.streakResult.incremented, true);
    }
  }

  const streakState = MathDailyGoalEngine.loadStreak({ storage });
  assert.equal(streakState.currentStreak, 1);
  assert.equal(streakState.lastCompletedDate, '2026-08-16');
  assert.equal(streakState.lastObservedDate, '2026-08-16');
});

test('MathDailyGoalEngine Streak 3: same-day repeated completion or claim does not duplicate increment (Idempotency)', () => {
  const storage = new MockStorage();
  const now = Date.parse('2026-08-16T09:00:00.000Z');

  const goal = MathDailyGoalEngine.initOrGetDailyGoal({ storage, now, skillCatalog: MathSkills.MATH_SKILLS });
  for (let i = 0; i < 5; i++) {
    MathDailyGoalEngine.recordGoalProgress({ goal, skillId: goal.skillId, correct: true, storage, now });
  }

  // Streak is 1
  assert.equal(MathDailyGoalEngine.loadStreak({ storage }).currentStreak, 1);

  // Calling recordStreakGoalCompletion again on same day -> duplicate increment blocked!
  const dupRes = MathDailyGoalEngine.recordStreakGoalCompletion({ storage, now: now + 5000 });
  assert.equal(dupRes.currentStreak, 1);
  assert.equal(dupRes.incremented, false);

  // Calling claimGoalReward again -> does not alter streak
  const claimRes = MathDailyGoalEngine.claimGoalReward({ goal, storage, now });
  assert.equal(claimRes.success, true);
  const secondClaim = MathDailyGoalEngine.claimGoalReward({ goal, storage, now });
  assert.equal(secondClaim.success, false);
  assert.equal(MathDailyGoalEngine.loadStreak({ storage }).currentStreak, 1);
});

test('MathDailyGoalEngine Streak 4: same-day reload / evaluation causes 0 decay', () => {
  const storage = new MockStorage();
  const now = Date.parse('2026-08-16T09:00:00.000Z');

  // Existing streak = 3 from earlier
  storage.setItem(MathDailyGoalEngine.STREAK_STORAGE_KEY, JSON.stringify({
    schemaVersion: 1,
    currentStreak: 3,
    lastObservedDate: '2026-08-16',
    lastCompletedDate: '2026-08-15',
    updatedAt: new Date(now).toISOString(),
  }));

  // Re-evaluating on the same day (e.g. page reload 10 times)
  for (let t = 0; t < 10; t++) {
    const s = MathDailyGoalEngine.initOrGetStreak({ storage, now: now + t * 60000 });
    assert.equal(s.currentStreak, 3);
  }
});

test('MathDailyGoalEngine Streak 5: partial goal progress on the day does not increment streak', () => {
  const storage = new MockStorage();
  const now = Date.parse('2026-08-16T09:00:00.000Z');

  const goal = MathDailyGoalEngine.initOrGetDailyGoal({ storage, now, skillCatalog: MathSkills.MATH_SKILLS });
  // 3 out of 5 solved
  for (let i = 0; i < 3; i++) {
    MathDailyGoalEngine.recordGoalProgress({ goal, skillId: goal.skillId, correct: true, storage, now });
  }
  assert.equal(goal.currentCount, 3);
  assert.equal(goal.completed, false);

  // Streak initialized at 0, must NOT increment to 1
  const streak = MathDailyGoalEngine.initOrGetStreak({ storage, now });
  assert.equal(streak.currentStreak, 0);
  assert.equal(streak.lastCompletedDate, null);
});

test('MathDailyGoalEngine Streak 6: incomplete goal causes deterministic -1 decay on the next day', () => {
  const storage = new MockStorage();
  const day1 = Date.parse('2026-08-16T09:00:00.000Z');
  const day2 = Date.parse('2026-08-17T09:00:00.000Z');

  // User had 4 streak on Day 1, but did not complete Day 1 goal
  storage.setItem(MathDailyGoalEngine.STREAK_STORAGE_KEY, JSON.stringify({
    schemaVersion: 1,
    currentStreak: 4,
    lastObservedDate: '2026-08-16',
    lastCompletedDate: '2026-08-15',
    updatedAt: new Date(day1).toISOString(),
  }));

  // Day 2 arrives
  const streakDay2 = MathDailyGoalEngine.initOrGetStreak({ storage, now: day2 });
  assert.equal(streakDay2.currentStreak, 3); // 4 -> 3 (-1 decay)
  assert.equal(streakDay2.lastObservedDate, '2026-08-17');
});

test('MathDailyGoalEngine Streak 7: missed day on 0 streak remains 0 (min floor 0, never negative)', () => {
  const storage = new MockStorage();
  const day1 = Date.parse('2026-08-16T09:00:00.000Z');
  const day2 = Date.parse('2026-08-17T09:00:00.000Z');

  storage.setItem(MathDailyGoalEngine.STREAK_STORAGE_KEY, JSON.stringify({
    schemaVersion: 1,
    currentStreak: 0,
    lastObservedDate: '2026-08-16',
    lastCompletedDate: null,
  }));

  const streakDay2 = MathDailyGoalEngine.initOrGetStreak({ storage, now: day2 });
  assert.equal(streakDay2.currentStreak, 0); // max(0, 0 - 1) = 0
});

test('MathDailyGoalEngine Streak 8: multi-day gap decays only by missed uncompleted calendar days', () => {
  const storage = new MockStorage();

  // Scenario A: 5 streak on 2026-08-15 (completed). User opens app on 2026-08-19 (missed 16, 17, 18 = 3 days).
  storage.setItem(MathDailyGoalEngine.STREAK_STORAGE_KEY, JSON.stringify({
    schemaVersion: 1,
    currentStreak: 5,
    lastObservedDate: '2026-08-15',
    lastCompletedDate: '2026-08-15',
  }));

  const nowA = Date.parse('2026-08-19T09:00:00.000Z');
  const streakA = MathDailyGoalEngine.initOrGetStreak({ storage, now: nowA });
  assert.equal(streakA.currentStreak, 2); // 5 - 3 = 2
  assert.equal(streakA.lastObservedDate, '2026-08-19');

  // Scenario B: 5 streak on 2026-08-15 (not completed on 15). User opens on 2026-08-19 (missed 15, 16, 17, 18 = 4 days).
  const storageB = new MockStorage();
  storageB.setItem(MathDailyGoalEngine.STREAK_STORAGE_KEY, JSON.stringify({
    schemaVersion: 1,
    currentStreak: 5,
    lastObservedDate: '2026-08-15',
    lastCompletedDate: '2026-08-14',
  }));

  const streakB = MathDailyGoalEngine.initOrGetStreak({ storage: storageB, now: nowA });
  assert.equal(streakB.currentStreak, 1); // 5 - 4 = 1
});

test('MathDailyGoalEngine Streak 9: guardian preset change does not alter existing today goal or streak', () => {
  const storage = new MockStorage();
  const now = Date.parse('2026-08-16T09:00:00.000Z');

  // Complete goal of 5 problems
  const goal = MathDailyGoalEngine.initOrGetDailyGoal({ storage, now, skillCatalog: MathSkills.MATH_SKILLS });
  for (let i = 0; i < 5; i++) {
    MathDailyGoalEngine.recordGoalProgress({ goal, skillId: goal.skillId, correct: true, storage, now });
  }
  assert.equal(MathDailyGoalEngine.loadStreak({ storage }).currentStreak, 1);

  // Guardian changes preset to challenge (7)
  MathDailyGoalEngine.saveGoalPreference('challenge', { storage });

  // Streak is still 1, today's goal is still 5 and completed
  assert.equal(MathDailyGoalEngine.loadStreak({ storage }).currentStreak, 1);
  const reloadedGoal = MathDailyGoalEngine.loadDailyGoal({ storage });
  assert.equal(reloadedGoal.targetCount, 5);
  assert.equal(reloadedGoal.completed, true);
});

test('MathDailyGoalEngine Streak 10: corrupted streak state fails soft safely', () => {
  const storage = new MockStorage();
  const now = Date.parse('2026-08-16T09:00:00.000Z');

  // Corrupt string
  storage.setItem(MathDailyGoalEngine.STREAK_STORAGE_KEY, '{invalid json');
  const s1 = MathDailyGoalEngine.initOrGetStreak({ storage, now });
  assert.equal(s1.currentStreak, 0);
  assert.equal(s1.lastObservedDate, '2026-08-16');

  // Negative streak or bad schema
  storage.setItem(MathDailyGoalEngine.STREAK_STORAGE_KEY, JSON.stringify({
    schemaVersion: 999,
    currentStreak: -5,
    lastObservedDate: 12345,
  }));
  const s2 = MathDailyGoalEngine.initOrGetStreak({ storage, now });
  assert.equal(s2.currentStreak, 0);
  assert.equal(s2.lastObservedDate, '2026-08-16');
});

test('MathDailyGoalEngine Streak 11: streak operations cause 0 artificial mutation to stats/evidence/mastery/session log', () => {
  const storage = new MockStorage();
  const now = Date.parse('2026-08-16T09:00:00.000Z');

  storage.setItem('aiden_math_stats', JSON.stringify({ '+': { levels: {} } }));
  storage.setItem('aiden_math_learning_evidence_v1', JSON.stringify({ schemaVersion: 1, items: [] }));
  storage.setItem('aiden_session_log', JSON.stringify([{ session: 1 }]));

  const statsBefore = storage.getItem('aiden_math_stats');
  const evidenceBefore = storage.getItem('aiden_math_learning_evidence_v1');
  const sessionBefore = storage.getItem('aiden_session_log');

  MathDailyGoalEngine.initOrGetStreak({ storage, now });
  MathDailyGoalEngine.recordStreakGoalCompletion({ storage, now });

  assert.equal(storage.getItem('aiden_math_stats'), statsBefore);
  assert.equal(storage.getItem('aiden_math_learning_evidence_v1'), evidenceBefore);
  assert.equal(storage.getItem('aiden_session_log'), sessionBefore);
});

test('MathDailyGoalEngine getTodayDateString resolves local calendar date YYYY-MM-DD', () => {
  const localDate = new Date(2026, 8, 1, 8, 30, 0); // Month index 8 is September (2026-09-01)
  const dateStr = MathDailyGoalEngine.getTodayDateString(localDate);
  assert.equal(dateStr, '2026-09-01');

  // Verify number timestamp works identically
  const dateStrFromTimestamp = MathDailyGoalEngine.getTodayDateString(localDate.getTime());
  assert.equal(dateStrFromTimestamp, '2026-09-01');

  // Single digit month and day padding check
  const paddedDate = new Date(2026, 0, 5, 12, 0, 0); // 2026-01-05
  assert.equal(MathDailyGoalEngine.getTodayDateString(paddedDate), '2026-01-05');
});
