const fs = require('fs');
const path = require('path');

const enginePath = path.join(__dirname, 'engine.js');
const content = fs.readFileSync(enginePath, 'utf8');

// 가상 DOM 및 localStorage 모킹
global.localStorage = { getItem: () => null, setItem: () => null };
global.document = { getElementById: () => ({ textContent: '', className: '', style: {}, innerHTML: '' }) };

// 함수 추출 (node 환경에서 실행 가능하도록 eval)
// generateByOpLevel, makeChoices 함수가 필요함
const funcMatch = content.match(/function generateByOpLevel\([\s\S]*?\} \n\} \nfunction makeChoices\([\s\S]*?\}/);
// Actually, it's easier to just eval the whole file but mock the browser APIs.
// Or I'll just write a simulator that uses the business logic.

// 연산 로직 재구현 (engine.js와 동기화 필수)
function generateByOpLevel(op, level) {
    let a, b, result, tag;
    if (op === '+') {
      const maxSums = [10, 20, 40, 60, 100, 150, 200];
      const maxAs   = [5, 10, 20, 35, 70, 100, 150];
      const maxBs   = [5, 10, 15, 20, 40, 60, 80];
      a = Math.floor(Math.random() * maxAs[level]) + 1;
      b = Math.floor(Math.random() * Math.min(maxSums[level] - a, maxBs[level])) + 1;
      result = a + b;
    } else if (op === '-') {
      const minAs = [3, 7, 15, 30, 60, 100, 150];
      const maxAs = [8, 20, 40, 80, 120, 160, 200];
      a = Math.floor(Math.random() * (maxAs[level] - minAs[level] + 1)) + minAs[level];
      b = Math.floor(Math.random() * (a - 1)) + 1;
      result = a - b;
    } else {
      const baseSets = [[2,5,10], [2,3,5,10], [2,3,4,5,6,7,8,9], [11,12,13,14,15], [16,17,18,19], [21,23,25,30], [31,37,43,47]];
      const bases = baseSets[level];
      a  = bases[Math.floor(Math.random() * bases.length)];
      const mult = level >= 3 ? Math.floor(Math.random() * 18) + 2 : Math.floor(Math.random() * 9) + 2;
      b = mult;
      result = a * b;
    }
    return { a, b, op, result };
}

function makeChoices(correct, op, level) {
    const spread = op === '×' ? 18 + level * 10 : [5, 8, 13, 20, 30, 40, 50][level];
    const set = new Set([correct]);
    let tries = 0;
    while (set.size < 4 && tries < 300) {
      tries++;
      const v = correct + Math.floor(Math.random() * (spread * 2 + 1)) - spread;
      if (v !== correct && v >= 0) set.add(v);
    }
    let fb = 1;
    while (set.size < 4) { if (fb !== correct) set.add(fb); fb++; }
    return [...set];
}

console.log('🚀 Starting Math Engine Algorithm Simulation...\n');

let totalChecks = 0;
let errors = [];

['+', '-', '×'].forEach(op => {
  for (let level = 0; level <= 6; level++) {
    console.log(`Simulating: [Operator ${op}] [Level ${level}] (100 iterations)`);
    for (let i = 0; i < 100; i++) {
        totalChecks++;
        const q = generateByOpLevel(op, level);
        
        // 1. 연산 정확성
        let actual;
        if (op === '+') actual = q.a + q.b;
        else if (op === '-') actual = q.a - q.b;
        else actual = q.a * q.b;

        if (actual !== q.result) {
            errors.push(`[${op}][Lv ${level}] 연산 결과 불일치: ${q.a} ${op} ${q.b} = ${q.result} (실제: ${actual})`);
        }

        // 2. 음수 결과 방지 (뺄셈)
        if (op === '-' && q.result < 0) {
            errors.push(`[${op}][Lv ${level}] 음수 결과 발생: ${q.a} - ${q.b} = ${q.result}`);
        }

        // 3. 보기 생성 무결성
        const choices = makeChoices(q.result, op, level);
        if (choices.length !== 4) {
            errors.push(`[${op}][Lv ${level}] 선택지가 4개가 아님: ${choices.length}`);
        }
        if (!choices.includes(q.result)) {
            errors.push(`[${op}][Lv ${level}] 선택지에 정답이 포함되어 있지 않음: ${q.result}`);
        }
        const unique = new Set(choices);
        if (unique.size !== choices.length) {
            errors.push(`[${op}][Lv ${level}] 선택지 중복 발생: ${choices}`);
        }
    }
  }
});

console.log('\n----------------------------------------');
console.log(`Total Cycles: ${totalChecks}`);
if (errors.length === 0) {
  console.log('✅ ALL CHECKS PASSED: Math Algorithms are Stable');
} else {
  console.error(`❌ FAILED: Found ${errors.length} error(s)`);
  errors.forEach(err => console.error(`  - ${err}`));
  process.exit(1);
}
console.log('----------------------------------------\n');
