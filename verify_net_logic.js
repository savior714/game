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
  /RocketCore\.install\(\s*window\s*\)/,
];

const requiredRocketCorePatterns = [
  /function\s+showNetBanner\s*\(/,
  /function\s+showNetActivatedBanner\s*\(/,
  /function\s+netBounceRocket\s*\(/,
  /if\s*\(\s*hasNet\s*\)\s*\{/,
  /hasNet\s*=\s*false\s*;/,
  /spawnNetEffect\s*\(/,
];

const requiredCssPatterns = [
  /\.net-element/,
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

function countMatches(text, pattern) {
  const matches = text.match(pattern);
  return matches ? matches.length : 0;
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

const rocketCore = read('common/rocket-core.js');
verifyPatterns(rocketCore, requiredRocketCorePatterns, 'common/rocket-core.js', errors);

// spawnNetEffect 호출 경로 단일성 확인(현 구현 기준)
const spawnNetEffectCalls = countMatches(rocketCore, /spawnNetEffect\s*\(/g);
if (spawnNetEffectCalls !== 2) {
  // 1회는 함수 정의, 1회는 netBounceRocket 내 호출
  errors.push(`[common/rocket-core.js] Expected 2 spawnNetEffect() tokens (definition + call), got ${spawnNetEffectCalls}`);
}

// hasNet false 전환 이후 발동 배너 경로의 존재 확인
if (!/hasNet\s*=\s*false[\s\S]*?showNetActivatedBanner\s*\(/.test(rocketCore)) {
  errors.push('[common/rocket-core.js] Missing flow from hasNet=false to showNetActivatedBanner()');
}

if (errors.length > 0) {
  console.error(`❌ FAILED: Net verification found ${errors.length} issue(s)\n`);
  for (const err of errors) console.error(`  - ${err}`);
  process.exit(1);
}

console.log('✅ PASS: Net logic is wired for all subjects');
