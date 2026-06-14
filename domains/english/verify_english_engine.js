const fs = require('fs');
const path = require('path');

const wordsPath = path.join(__dirname, 'words.js');
const content = fs.readFileSync(wordsPath, 'utf8');

const dbMatch = content.match(/const WORDS = (\{[\s\S]*?\});/);
if (!dbMatch) {
  console.error('❌ Error: WORDS object not found in words.js');
  process.exit(1);
}

let WORDS;
try {
  WORDS = eval(`(${dbMatch[1]})`);
} catch (e) {
  console.error('❌ Error: Failed to parse WORDS object:', e.message);
  process.exit(1);
}

console.log('🚀 Starting English Engine Word Integrity Check...\n');

let totalChecks = 0;
let errors = [];
let allEnWords = new Set();

Object.keys(WORDS).forEach(catId => {
  const cat = WORDS[catId];
  console.log(`Checking Category: [${cat.label}] (${cat.words.length} words)`);

  cat.words.forEach((w, idx) => {
    totalChecks++;
    const [en, ko, emoji, lv] = w;

    // 1. 형식 무결성 (Length)
    if (w.length < 4) {
      errors.push(`[${catId}][Index ${idx}] 데이터 형식이 불완전함`);
    }

    // 2. 중복 단어 (Duplicate English Words)
    if (allEnWords.has(en)) {
      errors.push(`[${catId}][en: ${en}] 중복된 영단어가 존재함`);
    }
    allEnWords.add(en);

    // 3. 비어있는 필드
    if (!en || !ko || !emoji) {
      errors.push(`[${catId}][en: ${en}] 빈 문자열 또는 null 값이 감지됨`);
    }

    // 4. 레벨 범위 (0-6)
    if (lv < 0 || lv > 6) {
      errors.push(`[${catId}][en: ${en}] 레벨 범위(0~6)를 벗어남: ${lv}`);
    }

    // 5. 이모지 유효성 (Emoji length/existence)
    if (emoji && emoji.length === 0) {
      errors.push(`[${catId}][en: ${en}] 이모지가 비어있음`);
    }
  });
});

console.log('\n----------------------------------------');
console.log(`Total Checks: ${totalChecks}`);
if (errors.length === 0) {
  console.log('✅ ALL CHECKS PASSED: English Data is Healthy');
} else {
  console.error(`❌ FAILED: Found ${errors.length} error(s)`);
  errors.forEach(err => console.error(`  - ${err}`));
  process.exit(1);
}
console.log('----------------------------------------\n');

// SHOP_DIALOGUES 검증 섹션
const advancedPath = path.join(__dirname, 'advanced-questions.js');
const advContent = fs.readFileSync(advancedPath, 'utf8');

const shopMatch = advContent.match(/const SHOP_DIALOGUES = (\[[\s\S]*?\]);/);
if (!shopMatch) {
  console.error('❌ SHOP_DIALOGUES not found in advanced-questions.js');
  process.exit(1);
}

let SHOP_DIALOGUES;
try {
  SHOP_DIALOGUES = eval(`(${shopMatch[1]})`);
} catch (e) {
  console.error('❌ Failed to parse SHOP_DIALOGUES:', e.message);
  process.exit(1);
}

console.log('🛍️ Starting SHOP_DIALOGUES Structure Validation...\n');

let shopErrors = [];
const shopIds = new Set();

if (!Array.isArray(SHOP_DIALOGUES)) {
  console.error('❌ SHOP_DIALOGUES is not an array');
  process.exit(1);
}

if (SHOP_DIALOGUES.length !== 20) {
  shopErrors.push(`템플릿 수가 20개가 아님: ${SHOP_DIALOGUES.length}개`);
}

SHOP_DIALOGUES.forEach((d, idx) => {
  if (!d.id) shopErrors.push(`[${idx}] id 필드 누락`);
  else if (shopIds.has(d.id)) shopErrors.push(`[${idx}] 중복된 id: ${d.id}`);
  else shopIds.add(d.id);

  if (!d.speaker) shopErrors.push(`[${idx || d.id}] speaker 필드 누락`);
  if (!d.line) shopErrors.push(`[${idx || d.id}] line 필드 누락`);
  if (d.blank !== true) shopErrors.push(`[${idx || d.id}] blank이 true 아님`);
  if (!Array.isArray(d.answer) || d.answer.length === 0) shopErrors.push(`[${idx || d.id}] answer 배열이 비어있음`);
  if (!d.category) shopErrors.push(`[${idx || d.id}] category 필드 누락`);
});

if (shopErrors.length === 0) {
  console.log('✅ SHOP_DIALOGUES Validation PASSED: 20 templates, all fields valid');
} else {
  console.error(`❌ SHOP_DIALOGUES Validation FAILED: ${shopErrors.length} error(s)`);
  shopErrors.forEach(err => console.error(`  - ${err}`));
  process.exit(1);
}

console.log('----------------------------------------\n');
