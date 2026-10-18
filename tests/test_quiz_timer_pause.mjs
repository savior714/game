import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../shared/ui/quiz-ui-core.js', import.meta.url), 'utf8');

function timerHarness() {
  const intervals = new Map();
  let nextId = 0;
  let interval = null;
  let remaining = 120;
  let timeouts = 0;
  const context = vm.createContext({
    window: {},
    document: { getElementById: () => null },
    setInterval: (callback, milliseconds) => {
      assert.equal(milliseconds, 250);
      const id = nextId++;
      intervals.set(id, callback);
      return id;
    },
    clearInterval: id => intervals.delete(id),
  });
  vm.runInContext(source, context);
  const timer = context.window.QuizUICore.createTimerCore({
    getTimeLimit: () => 120,
    getTimeLeft: () => remaining,
    setTimeLeft: value => { remaining = value; },
    getTimerInterval: () => interval,
    setTimerInterval: id => { interval = id; },
    onTimeout: () => { timeouts++; },
  });
  return {
    timer,
    intervals,
    remaining: () => remaining,
    timeouts: () => timeouts,
    tick: (count = 1) => {
      for (let i = 0; i < count; i++) {
        for (const callback of [...intervals.values()]) callback();
      }
    },
  };
}

test('pause/resume preserves the budget and owns exactly one interval', () => {
  const h = timerHarness();
  h.timer.startTimer();
  h.tick(2);
  h.timer.pauseTimer();
  h.timer.pauseTimer();
  h.tick(20);
  assert.equal(h.remaining(), 119.5);
  assert.equal(h.intervals.size, 0);
  h.timer.resumeTimer();
  h.timer.resumeTimer();
  assert.equal(h.intervals.size, 1);
  h.tick(2);
  assert.equal(h.remaining(), 119);
});

test('stop while paused cancels the pending resume', () => {
  const h = timerHarness();
  h.timer.startTimer();
  h.tick();
  h.timer.pauseTimer();
  h.timer.stopTimer();
  h.timer.resumeTimer();
  h.tick(20);
  assert.equal(h.intervals.size, 0);
  assert.equal(h.remaining(), 119.75);
});

test('a fresh question supersedes an old pause without duplicate ticking', () => {
  const h = timerHarness();
  h.timer.startTimer();
  h.tick(4);
  h.timer.pauseTimer();
  h.timer.startTimer();
  h.timer.resumeTimer();
  assert.equal(h.intervals.size, 1);
  assert.equal(h.remaining(), 120);
  h.tick(4);
  assert.equal(h.remaining(), 119);
});

test('stopped or untimed questions cannot be started by pause/resume', () => {
  const h = timerHarness();
  h.timer.pauseTimer();
  h.timer.resumeTimer();
  assert.equal(h.intervals.size, 0);
  assert.equal(h.remaining(), 120);
});

test('timeout fires once and cannot resume an expired budget', () => {
  const h = timerHarness();
  h.timer.startTimer();
  h.tick(480);
  h.timer.pauseTimer();
  h.timer.resumeTimer();
  h.tick(20);
  assert.equal(h.remaining(), 0);
  assert.equal(h.timeouts(), 1);
  assert.equal(h.intervals.size, 0);
});
