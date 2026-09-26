/**
 * English definitions copied verbatim from the 9/18 Friday spelling-test sheet (Vocabulary B Unit 2).
 * The printed wording and punctuation are intentionally preserved.
 */
(function (root) {
  'use strict';

  const fallbackDefinitions = Object.freeze({
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

  function getCanonicalSet() {
    if (root.WeeklyVocabularyStore && typeof root.WeeklyVocabularyStore.getCurrentSet === 'function') {
      try {
        return root.WeeklyVocabularyStore.getCurrentSet();
      } catch (e) {
        return null;
      }
    }
    return null;
  }

  function getBatchId() {
    const current = getCanonicalSet();
    return (current && current.setId) || '2026-09-18';
  }

  function getAllDefinitions() {
    const current = getCanonicalSet();
    if (current && Array.isArray(current.items)) {
      const map = {};
      current.items.forEach(function (item) {
        if (!map[item.word]) {
          map[item.word] = item.academyDescription;
        }
      });
      return Object.freeze(map);
    }
    return fallbackDefinitions;
  }

  function getDefinition(rawWord) {
    if (typeof rawWord !== 'string') return null;
    const normalized = rawWord.trim().normalize('NFKC').toLowerCase();
    const current = getCanonicalSet();
    if (current && Array.isArray(current.items)) {
      for (let i = 0; i < current.items.length; i++) {
        if (current.items[i].word.trim().normalize('NFKC').toLowerCase() === normalized) {
          return current.items[i].academyDescription;
        }
      }
      return null;
    }
    return fallbackDefinitions[normalized] || null;
  }

  function applyToQuestion(question, word, meta) {
    const englishWord = Array.isArray(word) ? word[0] : word;
    const koreanMeaning = Array.isArray(word) ? word[1] : null;
    // selected weekly item의 academyDescription이 전달된 경우 global map lookup을 우회하여 정확한 sense 보존
    const definition = (meta && meta.academyDescription)
      ? meta.academyDescription
      : getDefinition(englishWord);
    if (!question || !definition) return question;

    const enriched = { ...question, englishDefinition: definition };
    if (meta && meta.weeklyItemId) enriched.weeklyItemId = meta.weeklyItemId;
    if (meta && meta.word) enriched.word = meta.word;
    if (meta && meta.isWeekly !== undefined) enriched.isWeekly = meta.isWeekly;

    if (koreanMeaning && enriched.main === koreanMeaning) enriched.main = definition;
    if (koreanMeaning && enriched.hint === koreanMeaning) enriched.hint = definition;
    if (koreanMeaning && enriched.koHint === koreanMeaning) enriched.koHint = definition;
    return enriched;
  }

  root.EnglishWeeklyWordDefinitions = Object.freeze({
    get batchId() {
      return getBatchId();
    },
    get all() {
      return getAllDefinitions();
    },
    get: getDefinition,
    applyToQuestion,
  });

  if (typeof buildQuestion === 'function') {
    const buildQuestionWithoutEnglishDefinition = buildQuestion;
    buildQuestion = function (type, word, meta) {
      const question = buildQuestionWithoutEnglishDefinition(type, word, meta);
      return applyToQuestion(question, word, meta);
    };
  }
})(window);
