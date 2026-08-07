/**
 * @fileoverview 수학 강화문항 fallback의 최종 반환 경계 회귀 테스트
 *
 * 실행: node tests/test_math_reinforcement_fallback_guarantee.mjs
 */

import { strict as assert } from 'node:assert';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const enginePath = resolve(__dirname, '..', 'domains', 'math', 'engine.js');
const engineSource = readFileSync(enginePath, 'utf8');

function createDomainStats() {
  return { levels: {}, weaknesses: {} };
}

function createEngineContext() {
  const initialStats = {
    '+': createDomainStats(),
    '-': createDomainStats(),
    '×': createDomainStats(),
  };
  const context = vm.createContext({
    console,
    Math,
    ProgressEngine: {
      createStatsKey: () => 'math',
      emptyStats: () => initialStats,
      loadStats: () => initialStats,
      saveStats: () => {},
      getBaseDiffLevel: () => 0,
      getDifficultyLevel: () => 0,
      recordResultCore: () => {},
    },
  });
  vm.runInContext(engineSource, context, { filename: enginePath });
  return context;
}

function questionKey(question) {
  return [question.a, question.b].sort((a, b) => a - b).join(',') + question.op;
}

const repeatedA = {
  a: 2,
  b: 3,
  op: '+',
  result: 5,
  tag: 'add_unit_2_3',
  level: 0,
  isWeakness: true,
  isReinforcement: true,
};
const differentB = {
  a: 4,
  b: 5,
  op: '+',
  result: 9,
  tag: 'add_unit_4_5',
  level: 0,
  isWeakness: true,
  isReinforcement: true,
};

{
  const context = createEngineContext();
  context.repeatedA = repeatedA;
  context.differentB = differentB;
  vm.runInContext(
    `
      _lastQuestionKey = '2,3+';
      recentQuestions = ['2,3+'];
      (() => {
        let candidateCalls = 0;
        _generateCandidate = () => {
          candidateCalls += 1;
          return candidateCalls <= 22 ? repeatedA : differentB;
        };
        globalThis.__result = generateQuestion();
        globalThis.__candidateCalls = candidateCalls;
      })();
    `,
    context,
  );

  assert.equal(
    context.__candidateCalls,
    23,
    'fallback must keep checking candidates after a repeated second fallback candidate',
  );
  assert.equal(
    questionKey(context.__result),
    '4,5+',
    'the first fallback candidate different from _lastQuestionKey must be returned',
  );
}

{
  const context = createEngineContext();
  context.repeatedA = repeatedA;
  vm.runInContext(
    `
      _lastQuestionKey = '2,3+';
      recentQuestions = ['2,3+'];
      (() => {
        let candidateCalls = 0;
        _generateCandidate = () => {
          candidateCalls += 1;
          return repeatedA;
        };
        globalThis.__result = generateQuestion();
        globalThis.__candidateCalls = candidateCalls;
      })();
    `,
    context,
  );

  assert.equal(
    context.__candidateCalls,
    40,
    'generation must remain bounded when every generated candidate repeats the last question',
  );
  assert.notEqual(
    questionKey(context.__result),
    '2,3+',
    'the final emergency question must never repeat _lastQuestionKey',
  );
  assert.notEqual(
    context.__result.isReinforcement,
    true,
    'the emergency question must be a normal question rather than an unchecked reinforcement replay',
  );
}

console.log('PASS: reinforcement fallback never returns the immediate previous question');
