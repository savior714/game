const fs = require('fs');
const path = require('path');

// 국어 엔진 파일 읽기
const enginePath = path.join(__dirname, 'engine.js');
const jsonPath = path.join(__dirname, 'data', 'words.json');

let DB;
if (fs.existsSync(jsonPath)) {
  try {
    DB = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
  } catch (e) {
    console.error('❌ Error: Failed to parse data/words.json:', e.message);
    process.exit(1);
  }
} else {
  const content = fs.readFileSync(enginePath, 'utf8');
  const dbMatch = content.match(/const DB = (\{[\s\S]*?\});/);
  if (!dbMatch) {
    console.error('❌ Error: DB object not found in engine.js and data/words.json is missing');
    process.exit(1);
  }
  try {
    DB = eval(`(${dbMatch[1]})`);
  } catch (e) {
    console.error('❌ Error: Failed to parse DB object:', e.message);
    process.exit(1);
  }
}

console.log('🚀 Starting Korean Engine Data Integrity Check...\n');

let totalChecks = 0;
let errors = [];
let warnings = [];

// 모호성 검토용 블랙리스트 (정답: 오답금지리스트)
const AMBIGUITY_BLACKLIST = {
  '느리다': ['둔하다'],
  '나태': ['태만'],
  '부정': ['거부', '비관'],
  '슬프다': ['괴롭다', '아프다'],
  '춥다': ['시원하다'],
  '패배': ['실패'],
  '풍부': ['가득'],
  '미시': ['미세'],
};

['spelling', 'antonym', 'honorific'].forEach(cat => {
  const data = DB[cat];
  console.log(`Checking Category: [${cat}] (${data.length} questions)`);

  data.forEach((q, idx) => {
    totalChecks++;
    const [qText, qAns, qChoices, qLv, qTag] = q;

    // 1. 형식 무결성 (Length)
    if (q.length < 5) {
      errors.push(`[${cat}][Index ${idx}] 데이터 형식이 불완전함 (필드 부족)`);
    }

    // 2. 유일 정답성 (Answer presence in choices)
    if (!qChoices.includes(qAns)) {
      errors.push(`[${cat}][Q: ${qText}] 정답(${qAns})이 선택지에 포함되어 있지 않음`);
    }

    // 3. 선택지 개수 (Exactly 4)
    if (qChoices.length !== 4) {
      errors.push(`[${cat}][Q: ${qText}] 선택지 개수가 4개가 아님 (Count: ${qChoices.length})`);
    }

    // 4. 선택지 중복 (Duplicity)
    const uniqueChoices = new Set(qChoices);
    if (uniqueChoices.size !== qChoices.length) {
      errors.push(`[${cat}][Q: ${qText}] 중복된 선택지가 존재함: ${qChoices}`);
    }

    // 5. 모호성 블랙리스트 검사
    if (AMBIGUITY_BLACKLIST[qAns]) {
      const forbidden = AMBIGUITY_BLACKLIST[qAns];
      forbidden.forEach(word => {
        if (qChoices.includes(word) && word !== qAns) {
          errors.push(`[${cat}][Q: ${qText}] 모호한 선택지 감지: "${word}" (정답 "${qAns}"와 혼동 가능성)`);
        }
      });
    }

    // 6. 비어있는 텍스트 검사
    if (!qText || !qAns || qChoices.some(c => !c)) {
      errors.push(`[${cat}][Index ${idx}] 빈 문자열 또는 null 값이 감지됨`);
    }
  });
});

console.log('\n----------------------------------------');
console.log(`Total Checks: ${totalChecks}`);
if (errors.length === 0) {
  console.log('✅ ALL CHECKS PASSED: Data Integrity is 100%');
} else {
  console.error(`❌ FAILED: Found ${errors.length} error(s)`);
  errors.forEach(err => console.error(`  - ${err}`));
  process.exit(1);
}
console.log('----------------------------------------\n');
