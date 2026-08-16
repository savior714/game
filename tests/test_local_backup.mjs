import test from 'node:test';
import assert from 'node:assert/strict';
import LocalBackupCore from '../domains/reward/guardian/local-backup.js';
import MathEvidenceStore from '../domains/math/evidence.js';
import MathDailyGoalEngine from '../domains/math/daily-goal.js';

function createMockStorage(initialData = {}) {
  const store = new Map(Object.entries(initialData));
  let failKey = null;

  return {
    _store: store,
    setFailKey(key) {
      failKey = key;
    },
    getItem(key) {
      return store.has(key) ? store.get(key) : null;
    },
    setItem(key, value) {
      if (failKey === key) {
        throw new Error(`Disk quota exceeded or mock error on ${key}`);
      }
      store.set(key, String(value));
    },
    removeItem(key) {
      store.delete(key);
    },
    clear() {
      store.clear();
    },
    get length() {
      return store.size;
    },
    key(index) {
      const keys = Array.from(store.keys());
      return keys[index] || null;
    },
  };
}

test('A. LocalBackupCore generates valid schemaVersion 1 snapshot from canonical state', () => {
  const storage = createMockStorage();
  const now = Date.UTC(2026, 7, 16, 12, 0, 0);

  // 1. Math evidence
  const evidenceData = {
    schemaVersion: 1,
    lastUpdated: '2026-08-16T12:00:00.000Z',
    items: [
      { id: 'ev-1', timestamp: now, skillId: 'math.add.within_10', op: '+', a: 1, b: 2, result: 3, correct: true, attempts: 1 },
    ],
  };
  storage.setItem(LocalBackupCore.STORAGE_KEYS.MATH_EVIDENCE, JSON.stringify(evidenceData));

  // 2. Math daily goal
  const goalData = {
    schemaVersion: 1,
    date: '2026-08-16',
    goalId: 'goal-2026-08-16-math.add.within_10-v1',
    skillId: 'math.add.within_10',
    skillName: '10 이하의 덧셈',
    shortName: '10 이하 덧셈',
    targetCount: 5,
    currentCount: 5,
    completed: true,
    completedAt: now,
    rewardGranted: true,
    rewardReceiptId: 'receipt-math-goal-2026-08-16-math.add.within_10-v1',
    lastUpdated: '2026-08-16T12:00:00.000Z',
  };
  storage.setItem(LocalBackupCore.STORAGE_KEYS.MATH_DAILY_GOAL, JSON.stringify(goalData));

  // 3. Rewards & Receipt
  const rewardsData = {
    gems: 10,
    youtube_minutes: 30,
    snacks: 2,
    marble_plays: 1,
    bubble_plays: 0,
    shop_items: [{ id: 'youtube', label: '유튜브 10분', price: 1 }],
    custom_inventory: { special_ticket: 2 },
    claimed_receipts: {
      'receipt-math-goal-2026-08-16-math.add.within_10-v1': {
        receiptId: 'receipt-math-goal-2026-08-16-math.add.within_10-v1',
        grantedAt: now,
      },
    },
  };
  storage.setItem(LocalBackupCore.STORAGE_KEYS.STUDY_REWARDS, JSON.stringify(rewardsData));

  const receiptKey = 'aiden_receipt_receipt-math-goal-2026-08-16-math.add.within_10-v1';
  storage.setItem(receiptKey, JSON.stringify({ receiptId: 'receipt-math-goal-2026-08-16-math.add.within_10-v1', gems: 2 }));

  const snapshot = LocalBackupCore.createBackupSnapshot({ storage, now });

  assert.equal(snapshot.format, 'aidengame-local-backup');
  assert.equal(snapshot.schemaVersion, 1);
  assert.equal(snapshot.app, 'AidenGame');
  assert.equal(snapshot.exportedAt, '2026-08-16T12:00:00.000Z');

  assert.equal(snapshot.datasets.mathEvidence.present, true);
  assert.equal(snapshot.datasets.mathEvidence.data.items.length, 1);

  assert.equal(snapshot.datasets.mathDailyGoal.present, true);
  assert.equal(snapshot.datasets.mathDailyGoal.data.goalId, 'goal-2026-08-16-math.add.within_10-v1');

  assert.equal(snapshot.datasets.studyRewards.present, true);
  assert.equal(snapshot.datasets.studyRewards.data.gems, 10);

  assert.equal(snapshot.datasets.mathReceipts.present, true);
  assert.ok(snapshot.datasets.mathReceipts.data[receiptKey]);
});

test('B. Export and restore round-trip preserves exact durable datasets', () => {
  const sourceStorage = createMockStorage();
  const targetStorage = createMockStorage();
  const now = Date.now();

  const evidenceData = {
    schemaVersion: 1,
    lastUpdated: new Date(now).toISOString(),
    items: [
      { id: 'ev-1', timestamp: now, skillId: 'math.add.within_10', op: '+', a: 3, b: 4, result: 7, correct: true, attempts: 1 },
      { id: 'ev-2', timestamp: now, skillId: 'math.subtract.within_10', op: '-', a: 8, b: 2, result: 6, correct: true, attempts: 1 },
    ],
  };
  const goalData = {
    schemaVersion: 1,
    date: '2026-08-16',
    goalId: 'goal-1',
    skillId: 'math.add.within_10',
    targetCount: 5,
    currentCount: 3,
    completed: false,
  };
  const rewardsData = {
    gems: 42,
    youtube_minutes: 60,
    snacks: 5,
    marble_plays: 3,
    bubble_plays: 2,
    claimed_receipts: { 'rec-1': { receiptId: 'rec-1', grantedAt: now } },
    custom_inventory: { bonus_toy: 1 },
  };
  const weeklyWords = [{ en: 'apple', ko: '사과', icon: '🍎' }];
  const statsMath = { '+': { levels: { 0: { attempts: 10, correct: 10 } } } };
  const sessionLog = { '2026-08-16': [{ subject: 'math', correct: 5, total: 5 }] };

  sourceStorage.setItem(LocalBackupCore.STORAGE_KEYS.MATH_EVIDENCE, JSON.stringify(evidenceData));
  sourceStorage.setItem(LocalBackupCore.STORAGE_KEYS.MATH_DAILY_GOAL, JSON.stringify(goalData));
  sourceStorage.setItem(LocalBackupCore.STORAGE_KEYS.STUDY_REWARDS, JSON.stringify(rewardsData));
  sourceStorage.setItem('aiden_receipt_rec-1', JSON.stringify({ receiptId: 'rec-1' }));
  sourceStorage.setItem(LocalBackupCore.STORAGE_KEYS.WEEKLY_WORDS, JSON.stringify(weeklyWords));
  sourceStorage.setItem(LocalBackupCore.STORAGE_KEYS.SUBJECT_STATS_MATH, JSON.stringify(statsMath));
  sourceStorage.setItem(LocalBackupCore.STORAGE_KEYS.SESSION_LOG, JSON.stringify(sessionLog));

  // Export
  const backup = LocalBackupCore.createBackupSnapshot({ storage: sourceStorage, now });

  // Restore into target
  const restoreRes = LocalBackupCore.restoreBackup(backup, { storage: targetStorage });
  assert.equal(restoreRes.success, true);

  assert.deepEqual(JSON.parse(targetStorage.getItem(LocalBackupCore.STORAGE_KEYS.MATH_EVIDENCE)), evidenceData);
  assert.deepEqual(JSON.parse(targetStorage.getItem(LocalBackupCore.STORAGE_KEYS.MATH_DAILY_GOAL)), goalData);
  assert.deepEqual(JSON.parse(targetStorage.getItem(LocalBackupCore.STORAGE_KEYS.STUDY_REWARDS)), rewardsData);
  assert.deepEqual(JSON.parse(targetStorage.getItem('aiden_receipt_rec-1')), { receiptId: 'rec-1' });
  assert.deepEqual(JSON.parse(targetStorage.getItem(LocalBackupCore.STORAGE_KEYS.WEEKLY_WORDS)), weeklyWords);
  assert.deepEqual(JSON.parse(targetStorage.getItem(LocalBackupCore.STORAGE_KEYS.SUBJECT_STATS_MATH)), statsMath);
  assert.deepEqual(JSON.parse(targetStorage.getItem(LocalBackupCore.STORAGE_KEYS.SESSION_LOG)), sessionLog);
});

test('C. Unrelated localStorage keys are preserved after restore', () => {
  const targetStorage = createMockStorage({
    bubble_best: '150',
    bubble_sound: '1',
    ocean_rescue_profile: '{"selected":true}',
    unrelated_app_setting: 'dark',
  });

  const validBackup = LocalBackupCore.createBackupSnapshot({
    storage: createMockStorage(),
    now: Date.now(),
  });

  const res = LocalBackupCore.restoreBackup(validBackup, { storage: targetStorage });
  assert.equal(res.success, true);

  assert.equal(targetStorage.getItem('bubble_best'), '150');
  assert.equal(targetStorage.getItem('bubble_sound'), '1');
  assert.equal(targetStorage.getItem('ocean_rescue_profile'), '{"selected":true}');
  assert.equal(targetStorage.getItem('unrelated_app_setting'), 'dark');
});

test('D. Absent dataset in backup clears stale local target key on restore', () => {
  const targetStorage = createMockStorage({
    [LocalBackupCore.STORAGE_KEYS.MATH_EVIDENCE]: '{"items":[{"id":"stale"}]}',
    [LocalBackupCore.STORAGE_KEYS.WEEKLY_WORDS]: '[{"en":"stale"}]',
    'aiden_receipt_old': '{"receiptId":"old"}',
  });

  const emptyBackup = {
    format: 'aidengame-local-backup',
    schemaVersion: 1,
    exportedAt: new Date().toISOString(),
    datasets: {
      mathEvidence: { storageKey: LocalBackupCore.STORAGE_KEYS.MATH_EVIDENCE, present: false, data: null },
      guardianWeeklyWords: { storageKey: LocalBackupCore.STORAGE_KEYS.WEEKLY_WORDS, present: false, data: null },
      mathReceipts: { present: false, data: {} },
    },
  };

  const res = LocalBackupCore.restoreBackup(emptyBackup, { storage: targetStorage });
  assert.equal(res.success, true);

  assert.equal(targetStorage.getItem(LocalBackupCore.STORAGE_KEYS.MATH_EVIDENCE), null);
  assert.equal(targetStorage.getItem(LocalBackupCore.STORAGE_KEYS.WEEKLY_WORDS), null);
  assert.equal(targetStorage.getItem('aiden_receipt_old'), null);
});

test('E. Invalid backup (wrong marker, higher version, malformed) causes 0 mutation', () => {
  const initialData = {
    [LocalBackupCore.STORAGE_KEYS.STUDY_REWARDS]: '{"gems":100}',
    bubble_best: '500',
  };
  const storage = createMockStorage(initialData);

  // 1. Wrong format
  const res1 = LocalBackupCore.restoreBackup({ format: 'random-dump', schemaVersion: 1, datasets: {} }, { storage });
  assert.equal(res1.success, false);
  assert.equal(storage.getItem(LocalBackupCore.STORAGE_KEYS.STUDY_REWARDS), '{"gems":100}');

  // 2. Future schemaVersion
  const res2 = LocalBackupCore.restoreBackup({ format: 'aidengame-local-backup', schemaVersion: 999, datasets: {} }, { storage });
  assert.equal(res2.success, false);
  assert.equal(storage.getItem(LocalBackupCore.STORAGE_KEYS.STUDY_REWARDS), '{"gems":100}');

  // 3. Null / Non-object payload
  const res3 = LocalBackupCore.restoreBackup(null, { storage });
  assert.equal(res3.success, false);
  assert.equal(storage.getItem(LocalBackupCore.STORAGE_KEYS.STUDY_REWARDS), '{"gems":100}');
});

test('F. Write failure during restore triggers complete rollback to previous state', () => {
  const initialRewards = '{"gems":50,"youtube_minutes":20}';
  const initialEvidence = '{"items":[{"id":"ev-initial"}]}';

  const storage = createMockStorage({
    [LocalBackupCore.STORAGE_KEYS.STUDY_REWARDS]: initialRewards,
    [LocalBackupCore.STORAGE_KEYS.MATH_EVIDENCE]: initialEvidence,
  });

  // Mock write failure on MATH_DAILY_GOAL
  storage.setFailKey(LocalBackupCore.STORAGE_KEYS.MATH_DAILY_GOAL);

  const newBackup = {
    format: 'aidengame-local-backup',
    schemaVersion: 1,
    exportedAt: new Date().toISOString(),
    datasets: {
      mathEvidence: { storageKey: LocalBackupCore.STORAGE_KEYS.MATH_EVIDENCE, present: true, data: { items: [{ id: 'new-ev' }] } },
      mathDailyGoal: { storageKey: LocalBackupCore.STORAGE_KEYS.MATH_DAILY_GOAL, present: true, data: { date: '2026-08-16' } },
      studyRewards: { storageKey: LocalBackupCore.STORAGE_KEYS.STUDY_REWARDS, present: true, data: { gems: 999 } },
    },
  };

  const res = LocalBackupCore.restoreBackup(newBackup, { storage });
  assert.equal(res.success, false);
  assert.equal(res.reason, 'write_failed');

  // Verify rollback succeeded
  assert.equal(storage.getItem(LocalBackupCore.STORAGE_KEYS.STUDY_REWARDS), initialRewards);
  assert.equal(storage.getItem(LocalBackupCore.STORAGE_KEYS.MATH_EVIDENCE), initialEvidence);
});

test('G. Auth, sync internals, and transient session keys are excluded from backup', () => {
  const storage = createMockStorage({
    'sb-abcdef-auth-token': '{"access_token":"secret123"}',
    'sync_queue': '{"study_rewards":{"gems":10}}',
    'study_youtube_free_time_session_v1': '{"active":true,"expiresAt":9999999}',
    'aiden_math_learning_evidence_v1': '{"schemaVersion":1,"items":[]}',
  });

  const snapshot = LocalBackupCore.createBackupSnapshot({ storage });
  const serialized = JSON.stringify(snapshot);

  assert.ok(!serialized.includes('secret123'));
  assert.ok(!serialized.includes('sb-abcdef-auth-token'));
  assert.ok(!serialized.includes('study_youtube_free_time_session_v1'));
  assert.ok(!serialized.includes('sync_queue'));
});

test('H. Reward idempotency survives backup and restore round-trip', () => {
  const storage = createMockStorage();
  const now = Date.now();
  const today = '2026-08-16';

  // 1. Math Daily Goal 완료 및 Reward 지급
  const goal = {
    schemaVersion: 1,
    date: today,
    goalId: `goal-${today}-math.add.within_10-v1`,
    skillId: 'math.add.within_10',
    skillName: '10 이하의 덧셈',
    shortName: '10 이하 덧셈',
    targetCount: 5,
    currentCount: 5,
    completed: true,
    completedAt: now,
    rewardGranted: false,
    rewardReceiptId: `receipt-math-goal-${today}-math.add.within_10-v1`,
    lastUpdated: new Date(now).toISOString(),
  };
  storage.setItem(MathDailyGoalEngine.STORAGE_KEY, JSON.stringify(goal));

  const rewardState = {
    gems: 0,
    youtube_minutes: 0,
    claimed_receipts: {},
  };
  const mockRewardSystem = {
    hasReceipt(receiptId) {
      return Boolean(rewardState.claimed_receipts[receiptId]);
    },
    grantWithReceipt(receiptId, grants) {
      if (this.hasReceipt(receiptId)) {
        return { success: false, alreadyClaimed: true };
      }
      for (const g of grants) {
        if (g.type === 'gems') rewardState.gems += g.amount;
        if (g.type === 'youtube') rewardState.youtube_minutes += g.amount * 10;
      }
      rewardState.claimed_receipts[receiptId] = { receiptId, grants };
      storage.setItem('study_rewards', JSON.stringify(rewardState));
      return { success: true, gems: rewardState.gems, youtube_minutes: rewardState.youtube_minutes };
    },
  };

  // Claim first time
  const claim1 = MathDailyGoalEngine.claimGoalReward({
    goal: goal,
    rewardSystem: mockRewardSystem,
    storage: storage,
    now: now,
  });
  assert.equal(claim1.success, true);
  assert.equal(rewardState.gems, 2);
  assert.equal(rewardState.youtube_minutes, 10);

  // 2. Export Backup
  const backup = LocalBackupCore.createBackupSnapshot({ storage, now });

  // 3. State corruption / reset on target machine
  const corruptedStorage = createMockStorage({
    [MathDailyGoalEngine.STORAGE_KEY]: JSON.stringify({
      ...goal,
      rewardGranted: false, // simulated ungranted goal state
    }),
    study_rewards: JSON.stringify({
      gems: 0,
      youtube_minutes: 0,
      claimed_receipts: {},
    }),
  });

  // 4. Restore from backup
  const restoreRes = LocalBackupCore.restoreBackup(backup, { storage: corruptedStorage });
  assert.equal(restoreRes.success, true);

  // 5. Attempt claim again on restored storage
  const restoredGoal = MathDailyGoalEngine.loadDailyGoal({ storage: corruptedStorage });
  const restoredRewards = JSON.parse(corruptedStorage.getItem('study_rewards'));

  const restoredRewardSystem = {
    hasReceipt(receiptId) {
      return Boolean(restoredRewards.claimed_receipts && restoredRewards.claimed_receipts[receiptId]);
    },
    grantWithReceipt(receiptId, grants) {
      if (this.hasReceipt(receiptId)) {
        return { success: false, alreadyClaimed: true };
      }
      for (const g of grants) {
        if (g.type === 'gems') restoredRewards.gems += g.amount;
        if (g.type === 'youtube') restoredRewards.youtube_minutes += g.amount * 10;
      }
      restoredRewards.claimed_receipts[receiptId] = { receiptId, grants };
      corruptedStorage.setItem('study_rewards', JSON.stringify(restoredRewards));
      return { success: true };
    },
  };

  const claim2 = MathDailyGoalEngine.claimGoalReward({
    goal: restoredGoal,
    rewardSystem: restoredRewardSystem,
    storage: corruptedStorage,
    now: now,
  });

  // Must NOT grant double rewards!
  assert.equal(claim2.success, false);
  assert.equal(claim2.reason, 'already_claimed');
  assert.equal(restoredRewards.gems, 2);
  assert.equal(restoredRewards.youtube_minutes, 10);
});

test('I. LocalBackupCore exports and restores mathGoalPreference dataset round-trip', () => {
  const sourceStorage = createMockStorage();
  const targetStorage = createMockStorage();
  const now = Date.now();

  const prefData = {
    schemaVersion: 1,
    presetId: 'challenge',
    updatedAt: new Date(now).toISOString(),
  };
  sourceStorage.setItem(LocalBackupCore.STORAGE_KEYS.MATH_GOAL_PREFERENCE, JSON.stringify(prefData));

  // Export
  const backup = LocalBackupCore.createBackupSnapshot({ storage: sourceStorage, now });
  assert.equal(backup.datasets.mathGoalPreference.present, true);
  assert.equal(backup.datasets.mathGoalPreference.data.presetId, 'challenge');

  // Validate
  const validation = LocalBackupCore.validateBackup(backup);
  assert.equal(validation.valid, true);
  assert.equal(validation.summary.mathGoalPresetId, 'challenge');

  // Restore
  const restoreRes = LocalBackupCore.restoreBackup(backup, { storage: targetStorage });
  assert.equal(restoreRes.success, true);
  assert.deepEqual(JSON.parse(targetStorage.getItem(LocalBackupCore.STORAGE_KEYS.MATH_GOAL_PREFERENCE)), prefData);
});

test('J. LocalBackupCore clears mathGoalPreference when present is false', () => {
  const targetStorage = createMockStorage({
    [LocalBackupCore.STORAGE_KEYS.MATH_GOAL_PREFERENCE]: JSON.stringify({ schemaVersion: 1, presetId: 'light' }),
  });

  const backupWithAbsentPref = {
    format: 'aidengame-local-backup',
    schemaVersion: 1,
    exportedAt: new Date().toISOString(),
    datasets: {
      mathGoalPreference: {
        storageKey: LocalBackupCore.STORAGE_KEYS.MATH_GOAL_PREFERENCE,
        present: false,
        data: null,
      },
    },
  };

  const res = LocalBackupCore.restoreBackup(backupWithAbsentPref, { storage: targetStorage });
  assert.equal(res.success, true);
  assert.equal(targetStorage.getItem(LocalBackupCore.STORAGE_KEYS.MATH_GOAL_PREFERENCE), null);
});

test('K. Legacy schema v1 backup without mathGoalPreference keeps existing local preference unchanged', () => {
  const targetStorage = createMockStorage({
    [LocalBackupCore.STORAGE_KEYS.MATH_GOAL_PREFERENCE]: JSON.stringify({ schemaVersion: 1, presetId: 'challenge' }),
    [LocalBackupCore.STORAGE_KEYS.STUDY_REWARDS]: '{"gems":5}',
  });

  // Older v1 backup that does not have mathGoalPreference dataset key
  const legacyBackupWithoutPrefDataset = {
    format: 'aidengame-local-backup',
    schemaVersion: 1,
    exportedAt: '2026-08-15T10:00:00.000Z',
    datasets: {
      studyRewards: {
        storageKey: LocalBackupCore.STORAGE_KEYS.STUDY_REWARDS,
        present: true,
        data: { gems: 20 },
      },
      // mathGoalPreference is UNDEFINED (missing from older backup)
    },
  };

  const res = LocalBackupCore.restoreBackup(legacyBackupWithoutPrefDataset, { storage: targetStorage });
  assert.equal(res.success, true);

  // Rewards should be updated
  assert.equal(JSON.parse(targetStorage.getItem(LocalBackupCore.STORAGE_KEYS.STUDY_REWARDS)).gems, 20);
  // Math goal preference MUST remain untouched
  const pref = JSON.parse(targetStorage.getItem(LocalBackupCore.STORAGE_KEYS.MATH_GOAL_PREFERENCE));
  assert.equal(pref.presetId, 'challenge');
});
