/**
 * @fileoverview 수학 스킬 모델 및 스킬별 문제 생성 모듈
 * @module math/skills
 *
 * 대한민국 2022 개정 초등 수학 교육과정(수와 연산 영역) 성취기준에 맞춘
 * 최소 단위 시맨틱 스킬 정의 및 스킬 맞춤형 문제 생성기.
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.MathSkills = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /**
   * 2022 개정 교육과정 기반 수학 스킬 카탈로그
   */
  const MATH_SKILLS = Object.freeze({
    'math.add.within_10': Object.freeze({
      id: 'math.add.within_10',
      operation: '+',
      name: '10 이하의 덧셈',
      shortName: '10 이하 덧셈',
      curriculumRef: '2022-2수01-05',
      gradeBand: '1-2',
      description: '합이 10 이하인 한 자리 수의 덧셈',
    }),
    'math.add.within_20.no_carry': Object.freeze({
      id: 'math.add.within_20.no_carry',
      operation: '+',
      name: '받아올림이 없는 20 이하의 덧셈',
      shortName: '받아올림 없는 덧셈',
      curriculumRef: '2022-2수01-06',
      gradeBand: '1-2',
      description: '합이 20 이하이며 일의 자리 받아올림이 없는 덧셈',
    }),
    'math.add.within_20.carry': Object.freeze({
      id: 'math.add.within_20.carry',
      operation: '+',
      name: '받아올림이 있는 20 이하의 덧셈',
      shortName: '받아올림 덧셈',
      curriculumRef: '2022-2수01-06',
      gradeBand: '1-2',
      description: '합이 20 이하이며 일의 자리에서 받아올림이 발생하는 덧셈',
    }),
    'math.add.within_100': Object.freeze({
      id: 'math.add.within_100',
      operation: '+',
      name: '100 이하의 두 자리 수 덧셈',
      shortName: '100 이하 덧셈',
      curriculumRef: '2022-2수01-06',
      gradeBand: '1-2',
      description: '합이 100 이하인 두 자리 수의 덧셈',
    }),
    'math.add.multi_digit': Object.freeze({
      id: 'math.add.multi_digit',
      operation: '+',
      name: '세 자리 수 이상의 덧셈',
      shortName: '큰 수 덧셈',
      curriculumRef: '2022-4수01-01',
      gradeBand: '3-4',
      description: '합이 100을 초과하는 덧셈',
    }),
    'math.subtract.within_10': Object.freeze({
      id: 'math.subtract.within_10',
      operation: '-',
      name: '10 이하의 뺄셈',
      shortName: '10 이하 뺄셈',
      curriculumRef: '2022-2수01-05',
      gradeBand: '1-2',
      description: '10 이하의 수에서 빼는 한 자리 수 뺄셈',
    }),
    'math.subtract.within_20.no_borrow': Object.freeze({
      id: 'math.subtract.within_20.no_borrow',
      operation: '-',
      name: '받아내림이 없는 20 이하의 뺄셈',
      shortName: '받아내림 없는 뺄셈',
      curriculumRef: '2022-2수01-06',
      gradeBand: '1-2',
      description: '20 이하의 수에서 일의 자리 받아내림이 없는 뺄셈',
    }),
    'math.subtract.within_20.borrow': Object.freeze({
      id: 'math.subtract.within_20.borrow',
      operation: '-',
      name: '받아내림이 있는 20 이하의 뺄셈',
      shortName: '받아내림 뺄셈',
      curriculumRef: '2022-2수01-06',
      gradeBand: '1-2',
      description: '20 이하의 수에서 십의 자리에서 받아내림이 있는 뺄셈',
    }),
    'math.subtract.within_100': Object.freeze({
      id: 'math.subtract.within_100',
      operation: '-',
      name: '100 이하의 두 자리 수 뺄셈',
      shortName: '100 이하 뺄셈',
      curriculumRef: '2022-2수01-06',
      gradeBand: '1-2',
      description: '100 이하의 두 자리 수 뺄셈',
    }),
    'math.subtract.multi_digit': Object.freeze({
      id: 'math.subtract.multi_digit',
      operation: '-',
      name: '세 자리 수 이상의 뺄셈',
      shortName: '큰 수 뺄셈',
      curriculumRef: '2022-4수01-01',
      gradeBand: '3-4',
      description: '100을 초과하는 수의 뺄셈',
    }),
    'math.multiply.basic_facts': Object.freeze({
      id: 'math.multiply.basic_facts',
      operation: '×',
      name: '한 자리 수 곱셈구구 (구구단)',
      shortName: '구구단 곱셈',
      curriculumRef: '2022-2수01-11',
      gradeBand: '1-2',
      description: '2단부터 9단까지의 한 자리 수 곱셈구구',
    }),
    'math.multiply.multi_digit': Object.freeze({
      id: 'math.multiply.multi_digit',
      operation: '×',
      name: '두 자리 수 이상의 곱셈',
      shortName: '두 자리 수 곱셈',
      curriculumRef: '2022-4수01-03',
      gradeBand: '3-4',
      description: '두 자리 수 이상의 곱셈',
    }),
  });

  /**
   * 교육과정 권장 학습 순서
   */
  const MATH_SKILL_ORDER = Object.freeze([
    'math.add.within_10',
    'math.subtract.within_10',
    'math.add.within_20.no_carry',
    'math.subtract.within_20.no_borrow',
    'math.add.within_20.carry',
    'math.subtract.within_20.borrow',
    'math.multiply.basic_facts',
    'math.add.within_100',
    'math.subtract.within_100',
    'math.multiply.multi_digit',
    'math.add.multi_digit',
    'math.subtract.multi_digit',
  ]);

  /**
   * 주어진 문제의 피연산자와 연산자로부터 정확한 스킬 ID를 결정
   * @param {number} a
   * @param {number} b
   * @param {string} op ('+' | '-' | '×')
   * @returns {string} skillId
   */
  function classifyMathSkill(a, b, op) {
    if (op === '+') {
      const sum = a + b;
      if (sum <= 10) {
        return 'math.add.within_10';
      }
      if (sum <= 20) {
        const unitA = a % 10;
        const unitB = b % 10;
        if (unitA + unitB >= 10) {
          return 'math.add.within_20.carry';
        }
        return 'math.add.within_20.no_carry';
      }
      if (sum <= 100) {
        return 'math.add.within_100';
      }
      return 'math.add.multi_digit';
    }

    if (op === '-') {
      if (a <= 10) {
        return 'math.subtract.within_10';
      }
      if (a <= 20) {
        const unitA = a % 10;
        const unitB = b % 10;
        if (unitA < unitB) {
          return 'math.subtract.within_20.borrow';
        }
        return 'math.subtract.within_20.no_borrow';
      }
      if (a <= 100) {
        return 'math.subtract.within_100';
      }
      return 'math.subtract.multi_digit';
    }

    if (op === '×') {
      if (a >= 2 && a <= 9 && b >= 1 && b <= 9) {
        return 'math.multiply.basic_facts';
      }
      return 'math.multiply.multi_digit';
    }

    return 'math.add.within_10';
  }

  /**
   * 기존 레거시 태그 추출 (하위 호환성 유지용)
   */
  function extractLegacyTag(a, b, op) {
    if (op === '+') {
      const d1 = a % 10;
      const d2 = b % 10;
      const min = Math.min(d1, d2);
      const max = Math.max(d1, d2);
      return `add_unit_${min}_${max}`;
    }
    if (op === '-') {
      return `sub_unit_${a % 10}_${b % 10}`;
    }
    if (op === '×') {
      return a >= 10 || b >= 10 ? 'mult_complex' : 'mult_table';
    }
    return 'basic';
  }

  /**
   * 특정 스킬에 정확히 부합하는 문제를 생성
   * @param {string} skillId
   * @param {Object} [options]
   * @param {() => number} [options.rng] - 난수 생성기 (기본 Math.random)
   * @returns {{ a: number, b: number, op: string, result: number, skillId: string, tag: string, curriculumRef: string }}
   */
  function generateQuestionForSkill(skillId, options) {
    const opts = options || {};
    const rng = typeof opts.rng === 'function' ? opts.rng : Math.random;

    let a = 1;
    let b = 1;
    let op = '+';
    let result = 2;

    switch (skillId) {
      case 'math.add.within_10': {
        op = '+';
        a = Math.floor(rng() * 8) + 1; // 1 ~ 8
        const maxB = 10 - a;
        b = Math.floor(rng() * maxB) + 1; // 1 ~ maxB
        result = a + b;
        break;
      }

      case 'math.add.within_20.no_carry': {
        op = '+';
        const choice = rng();
        if (choice < 0.35) {
          a = 10;
          b = Math.floor(rng() * 9) + 1; // 1 ~ 9 -> 11 ~ 19
        } else if (choice < 0.7) {
          const unitA = Math.floor(rng() * 8) + 1; // 1 ~ 8
          a = 10 + unitA; // 11 ~ 18
          const maxUnitB = 9 - unitA;
          b = Math.floor(rng() * maxUnitB) + 1; // 1 ~ (9 - unitA)
        } else {
          const unitB = Math.floor(rng() * 8) + 1; // 1 ~ 8
          b = 10 + unitB; // 11 ~ 18
          const maxUnitA = 9 - unitB;
          a = Math.floor(rng() * maxUnitA) + 1;
        }
        result = a + b;
        break;
      }

      case 'math.add.within_20.carry': {
        op = '+';
        a = Math.floor(rng() * 8) + 2; // 2 ~ 9
        const minB = 11 - a; // sum >= 11 so it is strictly within 11~18
        const maxB = 9;
        b = Math.floor(rng() * (maxB - minB + 1)) + minB;
        result = a + b;
        break;
      }

      case 'math.add.within_100': {
        op = '+';
        // sum 21 ~ 100
        a = Math.floor(rng() * 60) + 12; // 12 ~ 71
        const minB = Math.max(1, 21 - a);
        const maxB = Math.min(100 - a, 40);
        b = Math.floor(rng() * (maxB - minB + 1)) + minB;
        result = a + b;
        break;
      }

      case 'math.add.multi_digit': {
        op = '+';
        a = Math.floor(rng() * 100) + 60; // 60 ~ 159
        b = Math.floor(rng() * 80) + 50;  // 50 ~ 129
        result = a + b;
        break;
      }

      case 'math.subtract.within_10': {
        op = '-';
        a = Math.floor(rng() * 8) + 2; // 2 ~ 10
        b = Math.floor(rng() * (a - 1)) + 1; // 1 ~ a-1
        result = a - b;
        break;
      }

      case 'math.subtract.within_20.no_borrow': {
        op = '-';
        const unitA = Math.floor(rng() * 8) + 1; // 1 ~ 8
        a = 10 + unitA; // 11 ~ 18
        b = Math.floor(rng() * unitA) + 1; // 1 ~ unitA
        result = a - b;
        break;
      }

      case 'math.subtract.within_20.borrow': {
        op = '-';
        // a: 11 ~ 18, unitA < b, b <= 9
        const unitA = Math.floor(rng() * 8) + 1; // 1 ~ 8 -> a = 11 ~ 18
        a = 10 + unitA; // 11 ~ 18
        const minB = unitA + 1;
        const maxB = 9;
        b = Math.floor(rng() * (maxB - minB + 1)) + minB;
        result = a - b;
        break;
      }

      case 'math.subtract.within_100': {
        op = '-';
        a = Math.floor(rng() * 70) + 25; // 25 ~ 94
        b = Math.floor(rng() * (a - 10)) + 5; // 5 ~ a-6
        result = a - b;
        break;
      }

      case 'math.subtract.multi_digit': {
        op = '-';
        a = Math.floor(rng() * 90) + 105; // 105 ~ 194
        b = Math.floor(rng() * 80) + 20;   // 20 ~ 99
        result = a - b;
        break;
      }

      case 'math.multiply.basic_facts': {
        op = '×';
        const baseSets = [2, 3, 4, 5, 6, 7, 8, 9];
        a = baseSets[Math.floor(rng() * baseSets.length)];
        b = Math.floor(rng() * 8) + 2; // 2 ~ 9
        result = a * b;
        break;
      }

      case 'math.multiply.multi_digit': {
        op = '×';
        const bases = [11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 25];
        a = bases[Math.floor(rng() * bases.length)];
        b = Math.floor(rng() * 8) + 2; // 2 ~ 9
        result = a * b;
        break;
      }

      default: {
        op = '+';
        a = Math.floor(rng() * 5) + 1;
        b = Math.floor(rng() * 5) + 1;
        result = a + b;
        break;
      }
    }

    const verifiedSkillId = classifyMathSkill(a, b, op);
    const skillMeta = MATH_SKILLS[verifiedSkillId] || MATH_SKILLS['math.add.within_10'];
    const tag = extractLegacyTag(a, b, op);

    return {
      a: a,
      b: b,
      op: op,
      result: result,
      skillId: verifiedSkillId,
      tag: tag,
      curriculumRef: skillMeta.curriculumRef,
    };
  }

  return Object.freeze({
    MATH_SKILLS: MATH_SKILLS,
    MATH_SKILL_ORDER: MATH_SKILL_ORDER,
    classifyMathSkill: classifyMathSkill,
    extractLegacyTag: extractLegacyTag,
    generateQuestionForSkill: generateQuestionForSkill,
  });
});
