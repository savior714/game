import test from 'node:test';
import assert from 'node:assert/strict';
import MathEvidenceStore from '../domains/math/evidence.js';

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

test('MathEvidenceStore creates default empty state on empty storage', () => {
  const storage = new MockStorage();
  const state = MathEvidenceStore.loadEvidence({ storage });

  assert.equal(state.schemaVersion, 1);
  assert.deepEqual(state.items, []);
});

test('MathEvidenceStore appends valid learning evidence and preserves fields', () => {
  const storage = new MockStorage();
  const now = 1771132000000;

  const item = MathEvidenceStore.appendEvidence({
    skillId: 'math.add.within_20.carry',
    problemKey: '8+7',
    op: '+',
    a: 8,
    b: 7,
    result: 15,
    correct: true,
    firstAttempt: true,
    attempts: 1,
    elapsedSeconds: 2.5,
    isWeakness: false,
    isReinforcement: false,
  }, { storage, now });

  assert.ok(item);
  assert.equal(item.timestamp, now);
  assert.equal(item.skillId, 'math.add.within_20.carry');
  assert.equal(item.problemKey, '8+7');
  assert.equal(item.correct, true);
  assert.equal(item.elapsedSeconds, 2.5);

  const list = MathEvidenceStore.getEvidenceList({ storage });
  assert.equal(list.length, 1);
  assert.equal(list[0].id, item.id);
});

test('MathEvidenceStore enforces bounded retention capacity', () => {
  const storage = new MockStorage();
  const maxItems = 10;

  for (let i = 1; i <= 15; i++) {
    MathEvidenceStore.appendEvidence({
      skillId: 'math.add.within_10',
      problemKey: `${i}+1`,
      a: i,
      b: 1,
      result: i + 1,
      correct: true,
    }, { storage, maxItems });
  }

  const list = MathEvidenceStore.getEvidenceList({ storage });
  assert.equal(list.length, 10);
  assert.equal(list[0].a, 6); // First 5 discarded
  assert.equal(list[9].a, 15);
});

test('MathEvidenceStore recovers gracefully from corrupted or malformed localStorage', () => {
  const storage = new MockStorage();
  storage.setItem(MathEvidenceStore.STORAGE_KEY, '{ invalid json');

  const state = MathEvidenceStore.loadEvidence({ storage });
  assert.equal(state.schemaVersion, 1);
  assert.deepEqual(state.items, []);

  // Recovers and allows new writes
  MathEvidenceStore.appendEvidence({
    skillId: 'math.add.within_10',
    a: 1,
    b: 2,
    result: 3,
    correct: true,
  }, { storage });

  const list = MathEvidenceStore.getEvidenceList({ storage });
  assert.equal(list.length, 1);
  assert.equal(list[0].a, 1);
});
