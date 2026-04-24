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
