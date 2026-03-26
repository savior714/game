const fs = require('fs');
const path = require('path');

const enginePath = path.join(__dirname, 'engine.js');
const content = fs.readFileSync(enginePath, 'utf8');

const dbMatch = content.match(/const DB = (\{[\s\S]*?\});/);
if (!dbMatch) {
  console.error('❌ Error: DB object not found in engine.js');
  process.exit(1);
}

let DB;
try {
  DB = eval(`(${dbMatch[1]})`);
} catch (e) {
  console.error('❌ Error: Failed to parse DB object:', e.message);
  process.exit(1);
}

console.log('🚀 Starting Science Engine Data Integrity Check...\n');

let totalChecks = 0;
let errors = [];

['biology', 'earth', 'physics'].forEach(cat => {
  const data = DB[cat];
  console.log(`Checking Category: [${cat}] (${data.length} questions)`);

  data.forEach((q, idx) => {
    totalChecks++;
    const [qText, qAns, qChoices, qLv, qTag] = q;

    // 1. 형식 무결성 (Length)
    if (q.length < 5) {
      errors.push(`[${cat}][Index ${idx}] 데이터 형식이 불완전함`);
    }

    // 2. 유일 정답성
    if (!qChoices.includes(qAns)) {
      errors.push(`[${cat}][Q: ${qText}] 정답(${qAns})이 선택지에 없음`);
    }

    // 3. 선택지 개수 (3지선다 표준 체크)
    if (qChoices.length < 3) {
      errors.push(`[${cat}][Q: ${qText}] 선택지 개수가 너무 적음 (Count: ${qChoices.length})`);
    }

    // 4. 선택지 중복
    const uniqueChoices = new Set(qChoices);
    if (uniqueChoices.size !== qChoices.length) {
      errors.push(`[${cat}][Q: ${qText}] 중복된 선택지가 존재함: ${qChoices}`);
    }

    // 5. 비어있는 텍스트
    if (!qText || !qAns || qChoices.some(c => !c)) {
      errors.push(`[${cat}][Index ${idx}] 빈 문자열 또는 null 값이 감지됨`);
    }
  });
});

console.log('\n----------------------------------------');
console.log(`Total Checks: ${totalChecks}`);
if (errors.length === 0) {
  console.log('✅ ALL CHECKS PASSED: Science Data is Healthy');
} else {
  console.error(`❌ FAILED: Found ${errors.length} error(s)`);
  errors.forEach(err => console.error(`  - ${err}`));
  process.exit(1);
}
console.log('----------------------------------------\n');
