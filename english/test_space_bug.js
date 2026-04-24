const fs = require('fs');
const path = require('path');

global.ProgressEngine = {
  emptyStats: (keys) => ({}),
  loadStats: (key, keys) => ({}),
  saveStats: (key, stats) => {},
  getBaseDiffLevel: (stats, cat, min) => 0,
  getDifficultyLevel: (stats, cat, min, boost, history) => 0
};

const enginePath = path.join(__dirname, 'engine.js');
let content = fs.readFileSync(enginePath, 'utf8');

const buildQuestionMatch = content.match(/function buildQuestion[\s\S]*?\n\}/);
const makeSpellingChoicesMatch = content.match(/function makeSpellingChoices[\s\S]*?\n\}/);
const wEnMatch = content.match(/const wEn[\s\S]*?;/);
const wKoMatch = content.match(/const wKo[\s\S]*?;/);
const wIcoMatch = content.match(/const wIco[\s\S]*?;/);
const wLvMatch = content.match(/const wLv[\s\S]*?;/);

const testCode = `
${wEnMatch[0]}
${wKoMatch[0]}
${wIcoMatch[0]}
${wLvMatch[0]}
${makeSpellingChoicesMatch[0]}
${buildQuestionMatch[0]}

const word = ['navy blue', '남색', '💙', 4];
console.log('Testing word "navy blue" containing space...');
for (let i = 0; i < 50; i++) {
  const q = buildQuestion('spelling', word);
  // 공백이 빈칸으로 잡혔는지 확인 (en[idx] === ' ')
  q.blankIndices.forEach(idx => {
    if (word[0][idx] === ' ') {
      console.error('❌ BUG: Space detected in blankIndices at index ' + idx);
      process.exit(1);
    }
  });
}
console.log('✅ Success: No space detected in any spelling blanks for "navy blue"!');
`;

eval(testCode);
