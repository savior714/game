const fs = require('fs');

// Mock localStorage
const mockStorage = {
  englishWeeklyWords: JSON.stringify([
    { en: 'weekly1', ko: '주간1', icon: '📝' },
    { en: 'weekly2', ko: '주간2', icon: '📝' }
  ]),
  getItem(key) { return this[key] || null; }
};

// Simple mock for WORDS and necessary functions
const WORDS = {
  animals: { words: [['cat', '고양이', '🐱', 0], ['dog', '개', '🐶', 0]] }
};
const currentCat = 'animals';
const getDifficultyLevel = () => 0;
const pickQuestionType = () => 'kor2word';
const buildQuestion = (type, word) => ({ type, answer: word[0], ico: word[2] });

// The logic from engine.js
function _generateCandidate(weeklyWords) {
  if (weeklyWords.length > 0 && Math.random() < 0.6) {
    const w = weeklyWords[Math.floor(Math.random() * weeklyWords.length)];
    const wordData = [w.en, w.ko, w.icon || '🎁', getDifficultyLevel()];
    const type = pickQuestionType();
    const res = buildQuestion(type, wordData);
    return { ...res, isWeekly: true };
  }
  return { isWeekly: false };
}

const weeklyWords = JSON.parse(mockStorage.getItem('englishWeeklyWords'));
let weeklyCount = 0;
const iterations = 1000;

for (let i = 0; i < iterations; i++) {
  const result = _generateCandidate(weeklyWords);
  if (result.isWeekly) weeklyCount++;
}

const percentage = (weeklyCount / iterations) * 100;
console.log(`Iterations: ${iterations}`);
console.log(`Weekly Word Count: ${weeklyCount}`);
console.log(`Percentage: ${percentage.toFixed(2)}%`);

if (percentage >= 55 && percentage <= 65) {
  console.log('✅ PASS: Weekly word probability is around 60%');
} else {
  console.log('❌ FAIL: Weekly word probability is out of range');
}
