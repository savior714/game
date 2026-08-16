import test from 'node:test';
import assert from 'node:assert/strict';
import MathSkills from '../domains/math/skills.js';

test('MathSkills taxonomy has 12 valid skills with 2022 curriculum references', () => {
  const skills = MathSkills.MATH_SKILLS;
  assert.equal(Object.keys(skills).length, 12);

  for (const [id, meta] of Object.entries(skills)) {
    assert.equal(meta.id, id);
    assert.ok(meta.name.length > 0);
    assert.ok(meta.curriculumRef.startsWith('2022-'));
    assert.ok(['+', '-', '×'].includes(meta.operation));
  }

  assert.equal(MathSkills.MATH_SKILL_ORDER.length, 12);
});

test('classifyMathSkill accurately classifies addition boundary cases', () => {
  // Within 10
  assert.equal(MathSkills.classifyMathSkill(1, 1, '+'), 'math.add.within_10');
  assert.equal(MathSkills.classifyMathSkill(5, 5, '+'), 'math.add.within_10');
  assert.equal(MathSkills.classifyMathSkill(3, 7, '+'), 'math.add.within_10');

  // Within 20, no carry (e.g. 10+5, 12+3, 4+13)
  assert.equal(MathSkills.classifyMathSkill(10, 5, '+'), 'math.add.within_20.no_carry');
  assert.equal(MathSkills.classifyMathSkill(12, 3, '+'), 'math.add.within_20.no_carry');
  assert.equal(MathSkills.classifyMathSkill(14, 5, '+'), 'math.add.within_20.no_carry');

  // Within 20, with carry (e.g. 8+7=15, 9+6=15, 7+8=15, 6+9=15)
  assert.equal(MathSkills.classifyMathSkill(8, 7, '+'), 'math.add.within_20.carry');
  assert.equal(MathSkills.classifyMathSkill(9, 6, '+'), 'math.add.within_20.carry');
  assert.equal(MathSkills.classifyMathSkill(7, 5, '+'), 'math.add.within_20.carry');

  // Within 100
  assert.equal(MathSkills.classifyMathSkill(15, 15, '+'), 'math.add.within_100');
  assert.equal(MathSkills.classifyMathSkill(45, 55, '+'), 'math.add.within_100');

  // Multi-digit (> 100)
  assert.equal(MathSkills.classifyMathSkill(60, 50, '+'), 'math.add.multi_digit');
  assert.equal(MathSkills.classifyMathSkill(120, 35, '+'), 'math.add.multi_digit');
});

test('classifyMathSkill accurately classifies subtraction boundary cases', () => {
  // Within 10
  assert.equal(MathSkills.classifyMathSkill(9, 4, '-'), 'math.subtract.within_10');
  assert.equal(MathSkills.classifyMathSkill(10, 3, '-'), 'math.subtract.within_10');

  // Within 20, no borrow (e.g. 18-5=13, 17-4=13, 15-2=13)
  assert.equal(MathSkills.classifyMathSkill(18, 5, '-'), 'math.subtract.within_20.no_borrow');
  assert.equal(MathSkills.classifyMathSkill(15, 2, '-'), 'math.subtract.within_20.no_borrow');

  // Within 20, with borrow (e.g. 14-8=6, 12-7=5, 15-9=6)
  assert.equal(MathSkills.classifyMathSkill(14, 8, '-'), 'math.subtract.within_20.borrow');
  assert.equal(MathSkills.classifyMathSkill(12, 7, '-'), 'math.subtract.within_20.borrow');

  // Within 100
  assert.equal(MathSkills.classifyMathSkill(45, 12, '-'), 'math.subtract.within_100');
  assert.equal(MathSkills.classifyMathSkill(99, 50, '-'), 'math.subtract.within_100');

  // Multi-digit
  assert.equal(MathSkills.classifyMathSkill(120, 30, '-'), 'math.subtract.multi_digit');
});

test('classifyMathSkill accurately classifies multiplication', () => {
  // Basic facts
  assert.equal(MathSkills.classifyMathSkill(2, 9, '×'), 'math.multiply.basic_facts');
  assert.equal(MathSkills.classifyMathSkill(7, 8, '×'), 'math.multiply.basic_facts');
  assert.equal(MathSkills.classifyMathSkill(9, 9, '×'), 'math.multiply.basic_facts');

  // Multi-digit
  assert.equal(MathSkills.classifyMathSkill(12, 4, '×'), 'math.multiply.multi_digit');
  assert.equal(MathSkills.classifyMathSkill(25, 3, '×'), 'math.multiply.multi_digit');
});

test('generateQuestionForSkill produces valid questions matching the skill for all skills', () => {
  for (const skillId of Object.keys(MathSkills.MATH_SKILLS)) {
    for (let trial = 0; trial < 20; trial++) {
      const q = MathSkills.generateQuestionForSkill(skillId);
      assert.equal(q.skillId, skillId, `Generated question ${q.a} ${q.op} ${q.b} does not match ${skillId}`);
      assert.ok(typeof q.result === 'number');
      assert.ok(q.tag.length > 0);
      assert.ok(q.curriculumRef.startsWith('2022-'));

      if (q.op === '+') assert.equal(q.a + q.b, q.result);
      else if (q.op === '-') assert.equal(q.a - q.b, q.result);
      else if (q.op === '×') assert.equal(q.a * q.b, q.result);
    }
  }
});
