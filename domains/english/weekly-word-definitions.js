/**
 * English definitions copied verbatim from the 8/7 Friday spelling-test sheet.
 * The printed wording and punctuation are intentionally preserved.
 */
(function (root) {
  'use strict';

  const definitions = Object.freeze({
    amount: 'how much of something there is',
    material: 'a solid substance such as wood, plastic, or metal',
    space: 'an empty area that is available to be used',
    example: 'something that shows what a group of things is like',
    easily: 'without problems or difficulties',
    forms: 'the shape or appearance of something',
    planet: 'a large object in space that moves around a star',
    tasty: 'dilicious ; having a pleasing flavor',
    antarctica: 'the continent that surrounds the South Pole',
    survive: 'to continue to live and grow',
  });

  function getDefinition(rawWord) {
    if (typeof rawWord !== 'string') return null;
    const normalized = rawWord.trim().normalize('NFKC').toLowerCase();
    return definitions[normalized] || null;
  }

  function applyToQuestion(question, word) {
    const englishWord = Array.isArray(word) ? word[0] : word;
    const koreanMeaning = Array.isArray(word) ? word[1] : null;
    const definition = getDefinition(englishWord);
    if (!question || !definition) return question;

    const enriched = { ...question, englishDefinition: definition };
    if (koreanMeaning && enriched.main === koreanMeaning) enriched.main = definition;
    if (koreanMeaning && enriched.hint === koreanMeaning) enriched.hint = definition;
    if (koreanMeaning && enriched.koHint === koreanMeaning) enriched.koHint = definition;
    return enriched;
  }

  root.EnglishWeeklyWordDefinitions = Object.freeze({
    batchId: '2026-08-07',
    all: definitions,
    get: getDefinition,
    applyToQuestion,
  });

  if (typeof buildQuestion === 'function') {
    const buildQuestionWithoutEnglishDefinition = buildQuestion;
    buildQuestion = function (type, word, meta) {
      const question = buildQuestionWithoutEnglishDefinition(type, word, meta);
      return applyToQuestion(question, word);
    };
  }
})(window);
