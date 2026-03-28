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

    // 6. 아동 창의성 보호 및 중의성 체크 (CRITICAL_LOGIC 제14조)
    if (qLv <= 1) {
      // 저난이도: 시각적/개념적 중의성이 우려되는 보기는 배제
      const visualAmbiguityKeywords = ['동그란', '동글', '모양', '색이에요'];
      const problematicDistractors = ['구름', '해', '공', '파란', '보라'];
      
      if (visualAmbiguityKeywords.some(kw => qText.includes(kw))) {
        const distractors = qChoices.filter(c => c !== qAns);
        distractors.forEach(d => {
          if (problematicDistractors.some(pd => d.includes(pd))) {
            errors.push(`[${cat}][Lv ${qLv}][Q: ${qText}] 오답 보기 [${d}]가 아이에게 창의적 오해를 줄 수 있음 (무관한 보류로 교체 권고)`);
          }
        });
      }
    } else if (qLv >= 2) {
      // 고난이도: 과학적 추론을 위한 변별력 단서 포함 여부 권고 (경고 피드백)
      const logicKeywords = ['매일', '밝게', '우주', '스스로', '모양을 바꾸는', '변하며'];
      if (!logicKeywords.some(kw => qText.includes(kw)) && qText.includes('모양')) {
        // 모양 관련 문항인데 단서가 부족한 경우 (경고 수준으로 기록하거나 필요시 에러)
        // console.warn(`[WARN][${cat}][Lv ${qLv}] 문항에 추론 단서 보강 권장: ${qText}`);
      }
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
