/**
 * English definitions copied verbatim from the 9/18 Friday spelling-test sheet (Vocabulary B Unit 2).
 * The printed wording and punctuation are intentionally preserved.
 */
(function (root) {
  'use strict';

  function getCanonicalSet() {
    if (root && root.WeeklyVocabularyStore && typeof root.WeeklyVocabularyStore.getCurrentSet === 'function') {
      try {
        return root.WeeklyVocabularyStore.getCurrentSet();
      } catch (e) {
        return null;
      }
    }
    if (typeof globalThis !== 'undefined' && globalThis.WeeklyVocabularyStore && typeof globalThis.WeeklyVocabularyStore.getCurrentSet === 'function') {
      try {
        return globalThis.WeeklyVocabularyStore.getCurrentSet();
      } catch (e) {
        return null;
      }
    }
    if (typeof require === 'function') {
      try {
        var store = require('./weekly-vocabulary-store.js');
        if (store && typeof store.getCurrentSet === 'function') {
          return store.getCurrentSet();
        }
      } catch (e) {}
    }
    return null;
  }

  function getBatchId() {
    var current = getCanonicalSet();
    return (current && current.setId) || 'none';
  }

  function getAllDefinitions() {
    var current = getCanonicalSet();
    if (current && Array.isArray(current.items)) {
      var map = {};
      current.items.forEach(function (item) {
        var w = item.word || item.answer;
        var d = item.academyDescription !== undefined ? item.academyDescription : item.prompt;
        if (w && !map[w]) {
          map[w] = d || '';
        }
      });
      return Object.freeze(map);
    }
    return Object.freeze({});
  }

  function getDefinition(rawWord) {
    if (typeof rawWord !== 'string') return null;
    var normalized = rawWord.trim().normalize('NFKC').toLowerCase();
    var current = getCanonicalSet();
    if (current && Array.isArray(current.items)) {
      for (var i = 0; i < current.items.length; i++) {
        var itemWord = String(current.items[i].word || current.items[i].answer || '').trim().normalize('NFKC').toLowerCase();
        if (itemWord === normalized) {
          return current.items[i].academyDescription !== undefined ? current.items[i].academyDescription : current.items[i].prompt;
        }
      }
    }
    return null;
  }

  function applyToQuestion(question, word, meta) {
    var englishWord = Array.isArray(word) ? word[0] : word;
    var koreanMeaning = Array.isArray(word) ? word[1] : null;
    var definition = (meta && (meta.academyDescription !== undefined ? meta.academyDescription : meta.prompt))
      ? (meta.academyDescription !== undefined ? meta.academyDescription : meta.prompt)
      : getDefinition(englishWord);
    if (!question || !definition) return question;

    var enriched = Object.assign({}, question, { englishDefinition: definition });
    if (meta && meta.weeklyItemId) enriched.weeklyItemId = meta.weeklyItemId;
    if (meta && meta.word) enriched.word = meta.word;
    if (meta && meta.isWeekly !== undefined) enriched.isWeekly = meta.isWeekly;

    if (koreanMeaning && enriched.main === koreanMeaning) enriched.main = definition;
    if (koreanMeaning && enriched.hint === koreanMeaning) enriched.hint = definition;
    if (koreanMeaning && enriched.koHint === koreanMeaning) enriched.koHint = definition;
    return enriched;
  }

  var targetRoot = root || (typeof globalThis !== 'undefined' ? globalThis : window);
  targetRoot.EnglishWeeklyWordDefinitions = Object.freeze({
    get batchId() {
      return getBatchId();
    },
    get all() {
      return getAllDefinitions();
    },
    get: getDefinition,
    applyToQuestion: applyToQuestion,
  });

  if (typeof buildQuestion === 'function') {
    var buildQuestionWithoutEnglishDefinition = buildQuestion;
    buildQuestion = function (type, word, meta) {
      var question = buildQuestionWithoutEnglishDefinition(type, word, meta);
      return applyToQuestion(question, word, meta);
    };
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
