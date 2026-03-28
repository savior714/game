const fs = require('fs');
const path = require('path');

// Mock DOM
global.document = {
  createElement: () => ({ setAttribute: () => {}, innerHTML: '', style: {}, appendChild: () => {} }),
  body: { appendChild: () => {}, prepend: () => {}, removeChild: () => {} },
  getElementById: () => ({ style: {}, classList: { add: () => {}, remove: () => {} }, textContent: '' }),
  documentElement: { style: { setProperty: () => {} } }
};
global.window = {
  addEventListener: () => {},
  getComputedStyle: () => ({ paddingTop: '0px' }),
  innerWidth: 1024,
  innerHeight: 768,
  document: global.document,
  location: { pathname: '/' }
};
const window = global.window;
global.requestAnimationFrame = (cb) => setTimeout(cb, 0);

// Mock RewardSystem
let rouletteCalled = false;
global.RewardSystem = {
  playEntranceAndOpenRoulette: (id) => {
    console.log(`[Test] RewardSystem.playEntranceAndOpenRoulette called with ID: ${id}`);
    rouletteCalled = true;
  }
};

// Load RocketCore
const rocketCoreContent = fs.readFileSync(path.join(__dirname, '../common/rocket-core.js'), 'utf8');
eval(rocketCoreContent);

// Test installation
const target = {};
if (global.window.RocketCore) {
  global.window.RocketCore.install(target);
} else {
  console.error('❌ FAIL: global.window.RocketCore is undefined');
  process.exit(1);
}

console.log('--- Starting verification of RewardSystem integration ---');

// Trigger showBoostBanner
target.showBoostBanner();

if (rouletteCalled) {
  console.log('✅ PASS: RewardSystem.playEntranceAndOpenRoulette was successfully called.');
} else {
  console.error('❌ FAIL: RewardSystem.playEntranceAndOpenRoulette was NOT called.');
  process.exit(1);
}

console.log('--- Verification complete ---');
