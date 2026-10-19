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

  function resolveDefinition(meta, englishWord) {
    var metaDefinition = meta
      ? (meta.academyDescription !== undefined ? meta.academyDescription : meta.prompt)
      : undefined;
    if (typeof metaDefinition === 'string' && metaDefinition.trim()) return metaDefinition.trim();

    var storedDefinition = getDefinition(englishWord);
    if (typeof storedDefinition === 'string' && storedDefinition.trim()) return storedDefinition.trim();
    return null;
  }

  /**
   * 질문 본문이 비어 있으면 definition으로 채운다.
   * 학원 시험지 원문만 등록된 주간 단어는 ko(한국어 뜻)가 비어 있어서
   * main/hint/koHint가 ''인 채로 렌더링되어 문제 내용이 보이지 않는 경우가 있었다.
   */
  function fillQuestionPrompt(question, koreanMeaning, definition) {
    ['main', 'hint', 'koHint'].forEach(function (field) {
      if (!Object.prototype.hasOwnProperty.call(question, field)) return;
      var value = question[field];
      var isBlank = typeof value === 'string' && value.trim() === '';
      var isKoreanMeaning =
        typeof koreanMeaning === 'string' &&
        koreanMeaning.trim() !== '' &&
        value === koreanMeaning;
      if (isBlank || isKoreanMeaning) question[field] = definition;
    });
  }

  function applyToQuestion(question, word, meta) {
    var englishWord = Array.isArray(word) ? word[0] : word;
    var koreanMeaning = Array.isArray(word) ? word[1] : null;
    var definition = resolveDefinition(meta, englishWord);
    if (!question || !definition) return question;

    var enriched = Object.assign({}, question, { englishDefinition: definition });
    if (meta && meta.weeklyItemId) enriched.weeklyItemId = meta.weeklyItemId;
    if (meta && meta.word) enriched.word = meta.word;
    if (meta && meta.isWeekly !== undefined) enriched.isWeekly = meta.isWeekly;

    fillQuestionPrompt(enriched, koreanMeaning, definition);
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
