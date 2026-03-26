const fs = require('fs');
const path = require('path');

const subjects = ['math', 'english', 'science', 'korean'];
const requiredEnginePatterns = [
  /let\s+netStreak\s*=\s*0\s*;/,
  /let\s+hasNet\s*=\s*false\s*;/,
  /const\s+NET_STREAK\s*=\s*5\s*;/,
  /netStreak\+\+/,
  /if\s*\(\s*netStreak\s*>=\s*NET_STREAK\s*&&\s*!hasNet\s*\)/,
  /showNetBanner\(\)/,
];

const requiredRocketPatterns = [
  /function\s+showNetBanner\s*\(/,
  /function\s+showNetActivatedBanner\s*\(/,
  /function\s+showNetIndicator\s*\(/,
  /function\s+netBounceRocket\s*\(/,
  /if\s*\(\s*hasNet\s*\)\s*\{/,
];

const requiredCssPatterns = [
  /\.net-element/,
  /\.net-indicator/,
  /\.net-banner/,
  /@keyframes\s+net-appear/,
  /@keyframes\s+net-banner-pop/,
];

function read(relativePath) {
  return fs.readFileSync(path.join(__dirname, relativePath), 'utf8');
}

function verifyPatterns(text, patterns, label, errors) {
  for (const p of patterns) {
    if (!p.test(text)) {
      errors.push(`[${label}] Missing pattern: ${p}`);
    }
  }
}

console.log('🚀 Starting Net Logic Verification...\n');

const errors = [];

for (const subject of subjects) {
  const engine = read(`${subject}/engine.js`);
  const rocket = read(`${subject}/rocket.js`);
  const css = read(`${subject}/rocket.css`);

  verifyPatterns(engine, requiredEnginePatterns, `${subject}/engine.js`, errors);
  verifyPatterns(rocket, requiredRocketPatterns, `${subject}/rocket.js`, errors);
  verifyPatterns(css, requiredCssPatterns, `${subject}/rocket.css`, errors);
}

if (errors.length > 0) {
  console.error(`❌ FAILED: Net verification found ${errors.length} issue(s)\n`);
  for (const err of errors) console.error(`  - ${err}`);
  process.exit(1);
}

console.log('✅ PASS: Net logic is wired for all subjects');
