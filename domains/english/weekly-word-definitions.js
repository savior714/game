/**
 * English definitions copied verbatim from the 8/14 Thursday spelling-test sheet.
 * Only words 3–12; words 1 (Antarctica) and 2 (survive) are excluded per the sheet.
 * The printed wording and punctuation are intentionally preserved.
 */
(function (root) {
  'use strict';

  const definitions = Object.freeze({
    belly: 'the part of the body below the chest and above the legs',
    glide: 'to move easily without stopping and without effort or noise',
    sleek: 'smooth or shiny',
    waterproof: 'not allowing water to go through',
    huddle: 'to move close together',
    feather: 'one of the soft and light parts of a bird that grows from the skin and covers the body',
    throat: 'the space inside the neck down which food and air can go through',
    waddle: 'to walk using short steps while rocking from side to side',
    fuzzy: 'furry, hairy',
    hunt: 'to chase and try to catch and kill an animal or bird for food',
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
    batchId: '2026-08-14',
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
