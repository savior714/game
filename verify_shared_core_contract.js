const fs = require('fs');
const path = require('path');

const subjects = ['math', 'english', 'science', 'korean'];
const errors = [];

function read(relativePath) {
  return fs.readFileSync(path.join(__dirname, relativePath), 'utf8');
}

function verifyPatterns(text, patterns, label) {
  for (const p of patterns) {
    if (!p.test(text)) {
      errors.push(`[${label}] Missing pattern: ${p}`);
    }
  }
}

function extractFunctionBody(text, functionName) {
  const start = text.indexOf(`function ${functionName}(`);
  if (start === -1) return null;
  const open = text.indexOf('{', start);
  if (open === -1) return null;

  let depth = 0;
  for (let i = open; i < text.length; i++) {
    const ch = text[i];
    if (ch === '{') depth++;
    if (ch === '}') depth--;
    if (depth === 0) return text.slice(open + 1, i);
  }
  return null;
}

function verifyForbiddenPatterns(text, patterns, label) {
  for (const p of patterns) {
    if (p.test(text)) {
      errors.push(`[${label}] Forbidden pattern found: ${p}`);
    }
  }
}

const uiRequiredPatterns = [
  /QuizUICore\.createTimerCore\(/,
  /QuizUICore\.createStatsModalCore\(/,
  /QuizUICore\.createAnswerFlowCore\(/,
  /answerFlowCore\.evaluateStandard\(/,
];

const coreRequiredPatterns = [
  /function\s+createAnswerFlowCore\s*\(/,
  /function\s+evaluateStandard\s*\(/,
  /recordResult\(true,\s*elapsed\)/,
  /recordResult\(false,\s*elapsed\)/,
  /function\s+createSequentialAnswerCore\s*\(/,
  /function\s+finalizeSuccess\s*\(/,
  /function\s+finalizeFailure\s*\(/,
];

const checkAnswerForbiddenPatterns = [
  /recordResult\s*\(/,
  /stopTimer\s*\(/,
  /answered\s*=\s*true/,
];

const englishSequentialRequiredPatterns = [
  /QuizUICore\.createSequentialAnswerCore\(/,
  /sequentialAnswerCore\.finalizeSuccess\(/,
  /sequentialAnswerCore\.finalizeFailure\(/,
];

const checkSeqForbiddenPatterns = [
  /recordResult\s*\(/,
  /stopTimer\s*\(/,
  /answered\s*=\s*true/,
];

console.log('🧭 Starting Shared Core Contract Verification...\n');

const coreFile = read('common/quiz-ui-core.js');
verifyPatterns(coreFile, coreRequiredPatterns, 'common/quiz-ui-core.js');

for (const subject of subjects) {
  const uiFile = read(`${subject}/ui.js`);
  verifyPatterns(uiFile, uiRequiredPatterns, `${subject}/ui.js`);

  const checkAnswerBody = extractFunctionBody(uiFile, 'checkAnswer');
  if (!checkAnswerBody) {
    errors.push(`[${subject}/ui.js] Missing function body: checkAnswer`);
    continue;
  }
  verifyForbiddenPatterns(checkAnswerBody, checkAnswerForbiddenPatterns, `${subject}/ui.js checkAnswer`);
}

const englishUI = read('english/ui.js');
verifyPatterns(englishUI, englishSequentialRequiredPatterns, 'english/ui.js');
const checkSeqBody = extractFunctionBody(englishUI, 'checkSeqAnswer');
if (!checkSeqBody) {
  errors.push('[english/ui.js] Missing function body: checkSeqAnswer');
} else {
  verifyForbiddenPatterns(checkSeqBody, checkSeqForbiddenPatterns, 'english/ui.js checkSeqAnswer');
}

if (errors.length > 0) {
  console.error(`❌ FAILED: Shared core contract verification found ${errors.length} issue(s)\n`);
  for (const err of errors) console.error(`  - ${err}`);
  process.exit(1);
}

console.log('✅ PASS: Shared core delegation contract is consistent');
