import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const source = readFileSync(new URL('../shared/domain/progress-engine.js', import.meta.url), 'utf8');

function loadProgressEngine() {
  const sandboxWindow = {};
  new Function('window', source)(sandboxWindow);
  return sandboxWindow.ProgressEngine;
}

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
}

test('A. Guardian base level preference round-trips, keeps level 0 valid, clamps and clears', () => {
  const ProgressEngine = loadProgressEngine();
  const storage = new MockStorage();

  assert.equal(ProgressEngine.loadGuardianBaseLevel('english', { storage }), null);

  ProgressEngine.saveGuardianBaseLevel('english', 4, { storage, now: 1000 });
  assert.equal(ProgressEngine.loadGuardianBaseLevel('english', { storage }), 4);

  ProgressEngine.saveGuardianBaseLevel('english', 0, { storage });
  assert.equal(ProgressEngine.loadGuardianBaseLevel('english', { storage }), 0);

  ProgressEngine.saveGuardianBaseLevel('english', 9, { storage });
  assert.equal(ProgressEngine.loadGuardianBaseLevel('english', { storage }), 6);

  ProgressEngine.clearGuardianBaseLevel('english', { storage });
  assert.equal(ProgressEngine.loadGuardianBaseLevel('english', { storage }), null);
});

test('B. Corrupted or foreign guardian base level storage fails soft to null', () => {
  const ProgressEngine = loadProgressEngine();
  const storage = new MockStorage();

  storage.setItem('aiden_korean_guardian_base_level_v1', '{broken');
  assert.equal(ProgressEngine.loadGuardianBaseLevel('korean', { storage }), null);

  storage.setItem('aiden_korean_guardian_base_level_v1', JSON.stringify({ schemaVersion: 999, level: 3 }));
  assert.equal(ProgressEngine.loadGuardianBaseLevel('korean', { storage }), null);

  storage.setItem('aiden_korean_guardian_base_level_v1', JSON.stringify({ schemaVersion: 1, level: 'high' }));
  assert.equal(ProgressEngine.loadGuardianBaseLevel('korean', { storage }), null);
});

test('C. Guardian base level replaces the stats-derived base while boosts and penalties still apply', () => {
  const ProgressEngine = loadProgressEngine();
  const stats = ProgressEngine.emptyStats(['animals']);
  stats.animals.levels[0] = { attempts: 10, correct: 10, totalTime: 100 };
  stats.animals.levels[1] = { attempts: 10, correct: 10, totalTime: 100 };

  assert.equal(ProgressEngine.getBaseDiffLevel(stats, 'animals', 2), 2);

  const opts = { guardianBaseLevel: 4 };
  assert.equal(ProgressEngine.getBaseDiffLevel(stats, 'animals', 2, opts), 4);
  assert.equal(ProgressEngine.getDifficultyLevel(stats, 'animals', 2, 0, [true, true, true], opts), 6);
  assert.equal(ProgressEngine.getDifficultyLevel(stats, 'animals', 2, 0, [true, false, false], opts), 3);
  assert.equal(ProgressEngine.getDifficultyLevel(stats, 'animals', 2, 0, [true, true, true, true, true], opts), 6);
});

test('D. Saving a guardian base level never touches the subject stats storage', () => {
  const ProgressEngine = loadProgressEngine();
  const storage = new MockStorage();
  storage.setItem(
    'aiden_science_stats',
    JSON.stringify({ biology: { levels: { 0: { attempts: 3, correct: 1, totalTime: 5 } }, weaknesses: {} } })
  );
  const statsBefore = storage.getItem('aiden_science_stats');

  ProgressEngine.saveGuardianBaseLevel('science', 5, { storage });

  assert.equal(storage.getItem('aiden_science_stats'), statsBefore);
  const payload = JSON.parse(storage.getItem('aiden_science_guardian_base_level_v1'));
  assert.equal(payload.schemaVersion, 1);
  assert.equal(payload.level, 5);
});
