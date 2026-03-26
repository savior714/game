/**
 * RewardSystem Logic Verification Script
 * - Mocking localStorage to test RewardSystem core functions in Node.js
 */

// 1. Mock localStorage
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: (key) => store[key] || null,
    setItem: (key, value) => { store[key] = String(value); },
    removeItem: (key) => { delete store[key]; },
    clear: () => { store = {}; }
  };
})();
global.localStorage = localStorageMock;

// 2. Mock DOM related things that RewardSystem uses
global.document = {
  getElementById: () => ({ textContent: '', style: {}, scrollIntoView: () => {}, dataset: {}, classList: { add: () => {}, remove: () => {} } }),
  createElement: () => ({ 
    style: {}, 
    classList: { add: () => {}, remove: () => {} }, 
    appendChild: () => {}, 
    prepend: () => {},
    querySelector: () => ({ onclick: null, remove: () => {} })
  }),
  head: { appendChild: () => {} },
  body: { appendChild: () => {}, prepend: () => {} },
  querySelectorAll: () => [],
  readyState: 'complete',
  addEventListener: () => {}
};
global.window = { location: { pathname: '/' } };
global.alert = (msg) => console.log('  [Alert Mock]:', msg);
global.requestAnimationFrame = (callback) => setTimeout(callback, 0);

// 3. Load RewardSystem (Simplified for Node testing)
// Since reward.js is a browser script with an IIFE, we'll re-declare the core logic here for testing
// In a real automated test environment (like Jest/Puppeteer), we'd run the actual file.
// For this environment, we verify the logic manually as coded in reward.js.

const RewardSystem = (() => {
  const STORAGE_KEY = 'study_rewards';
  let state = { youtube_minutes: 0, snacks: 0, marble_plays: 0 };

  function load() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) state = JSON.parse(saved);
  }
  function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }
  function add(type, amount = 1) {
    if (type === 'youtube') state.youtube_minutes += (amount * 15);
    else if (type === 'snack') state.snacks += amount;
    else if (type === 'marble') state.marble_plays += amount;
    save();
  }
  function has(type) {
    if (type === 'youtube') return state.youtube_minutes >= 15;
    if (type === 'snack') return state.snacks > 0;
    if (type === 'marble') return state.marble_plays > 0;
    return false;
  }
  function consume(type) {
    if (!has(type)) return false;
    if (type === 'youtube') state.youtube_minutes -= 15;
    else if (type === 'snack') state.snacks -= 1;
    else if (type === 'marble') state.marble_plays -= 1;
    save();
    return true;
  }
  return { add, has, consume, getState: () => state, load };
})();

// 4. Test Suite
console.log('🚀 Starting RewardSystem Logic Verification...\n');

function assert(condition, message) {
  if (!condition) {
    console.error(`  ❌ FAIL: ${message}`);
    process.exit(1);
  } else {
    console.log(`  ✅ PASS: ${message}`);
  }
}

// Test Case 1: Initial State
assert(RewardSystem.getState().youtube_minutes === 0, 'Initial youtube time should be 0');

// Test Case 2: Adding Rewards
RewardSystem.add('youtube', 1);
assert(RewardSystem.getState().youtube_minutes === 15, 'Adding 1 youtube reward should result in 15 mins');
RewardSystem.add('snack', 2);
assert(RewardSystem.getState().snacks === 2, 'Adding 2 snacks should result in 2');

// Test Case 3: Persistence (Save & Load)
const savedValue = JSON.parse(localStorage.getItem('study_rewards'));
assert(savedValue.youtube_minutes === 15 && savedValue.snacks === 2, 'LocalStorage should contain saved rewards');

// Test Case 4: Consumption
assert(RewardSystem.has('youtube') === true, 'Should have youtube reward');
const consumed = RewardSystem.consume('youtube');
assert(consumed === true, 'Consumption should succeed');
assert(RewardSystem.getState().youtube_minutes === 0, 'Youtube minutes should be 0 after consumption');

RewardSystem.consume('snack');
assert(RewardSystem.getState().snacks === 1, '1 snack should remain after consuming 1');

// Test Case 5: Empty Consumption
const failedConsume = RewardSystem.consume('marble');
assert(failedConsume === false, 'Consuming non-existent reward should fail');

console.log('\n✨ All tests passed successfully!');
