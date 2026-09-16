/**
 * English definitions copied verbatim from the 9/18 Friday spelling-test sheet (Vocabulary B Unit 2).
 * The printed wording and punctuation are intentionally preserved.
 */
(function (root) {
  'use strict';

  const definitions = Object.freeze({
    across: 'from one side to the other side',
    surround: 'to be on all sides',
    relaxing: 'helping you to rest',
    peaceful: 'calm and not violent',
    mystery: 'a puzzle or secret',
    clear: 'see-through',
    bottom: 'the lowest part of something',
    explore: 'to look around and discover',
    calm: 'not moving much',
    imagine: 'to picture in your mind',
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
    batchId: '2026-09-18',
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
