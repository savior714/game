(function (root) {
  'use strict';

  var SCHEMA_VERSION = 1;
  var PROMPT_MODE = 'definition-to-spelling';
  var SESSION_KEY = 'englishWeeklyTestSessionV1';
  var RESULTS_KEY = 'englishWeeklyTestResultsV1';

  function normalizeAnswer(raw) {
    if (typeof raw !== 'string') return '';
    return raw.trim().normalize('NFKC').toLowerCase();
  }

  function buildTestSet() {
    var src = (root.EnglishWeeklyWordDefinitions && root.EnglishWeeklyWordDefinitions.all) || {};
    var batchId = (root.EnglishWeeklyWordDefinitions && root.EnglishWeeklyWordDefinitions.batchId) || 'unknown';
    var items = Object.keys(src).map(function (word) {
      return {
        id: word,
        answer: word,
        prompt: src[word],
        acceptedAnswers: []
      };
    });
    return {
      schemaVersion: SCHEMA_VERSION,
      setId: batchId,
      title: batchId + ' 주간 영단어',
      promptMode: PROMPT_MODE,
      items: items
    };
  }

  function createSession(testSet) {
    var now = new Date().toISOString();
    var answers = {};
    testSet.items.forEach(function (item) {
      answers[item.id] = '';
    });
    return {
      schemaVersion: SCHEMA_VERSION,
      setId: testSet.setId,
      status: 'in_progress',
      currentIndex: 0,
      answers: answers,
      items: testSet.items.map(function (item) {
        return { id: item.id, answer: item.answer, prompt: item.prompt, acceptedAnswers: item.acceptedAnswers };
      }),
      startedAt: now,
      updatedAt: now
    };
  }

  function saveSession(session) {
    session.updatedAt = new Date().toISOString();
    try {
      localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    } catch (e) {}
  }

  function loadSession() {
    try {
      var raw = localStorage.getItem(SESSION_KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      if (!parsed || parsed.schemaVersion !== SCHEMA_VERSION) return null;
      return parsed;
    } catch (e) {
      return null;
    }
  }

  function clearSession() {
    try {
      localStorage.removeItem(SESSION_KEY);
    } catch (e) {}
  }

  function gradeAnswer(item, raw) {
    var given = normalizeAnswer(raw);
    if (given === '') return false;
    if (given === normalizeAnswer(item.answer)) return true;
    if (Array.isArray(item.acceptedAnswers)) {
      for (var i = 0; i < item.acceptedAnswers.length; i++) {
        if (given === normalizeAnswer(item.acceptedAnswers[i])) return true;
      }
    }
    return false;
  }

  function gradeSession(testSet, session) {
    var results = [];
    var correctCount = 0;
    testSet.items.forEach(function (item) {
      var given = session.answers[item.id] || '';
      var isCorrect = gradeAnswer(item, given);
      if (isCorrect) correctCount++;
      results.push({
        id: item.id,
        answer: item.answer,
        prompt: item.prompt,
        given: given,
        correct: isCorrect
      });
    });
    return {
      schemaVersion: SCHEMA_VERSION,
      setId: testSet.setId,
      total: testSet.items.length,
      correct: correctCount,
      elapsedMs: session.startedAt ? (new Date().getTime() - new Date(session.startedAt).getTime()) : 0,
      results: results,
      submittedAt: new Date().toISOString()
    };
  }

  function saveResult(result) {
    try {
      var existing = [];
      var raw = localStorage.getItem(RESULTS_KEY);
      if (raw) existing = JSON.parse(raw);
      existing.push(result);
      localStorage.setItem(RESULTS_KEY, JSON.stringify(existing));
    } catch (e) {}
  }

  function getResults() {
    try {
      var raw = localStorage.getItem(RESULTS_KEY);
      if (!raw) return [];
      return JSON.parse(raw);
    } catch (e) {
      return [];
    }
  }

  function buildWrongWordSet(result) {
    var wrong = result.results.filter(function (r) { return !r.correct; });
    return {
      schemaVersion: SCHEMA_VERSION,
      setId: result.setId + '_retry_' + Date.now(),
      title: '틀린 단어 다시 쓰기',
      promptMode: PROMPT_MODE,
      items: wrong.map(function (r) {
        return { id: r.id, answer: r.answer, prompt: r.prompt, acceptedAnswers: [] };
      })
    };
  }

  root.WeeklyTestEngine = Object.freeze({
    normalizeAnswer: normalizeAnswer,
    buildTestSet: buildTestSet,
    createSession: createSession,
    saveSession: saveSession,
    loadSession: loadSession,
    clearSession: clearSession,
    gradeAnswer: gradeAnswer,
    gradeSession: gradeSession,
    saveResult: saveResult,
    getResults: getResults,
    buildWrongWordSet: buildWrongWordSet,
    SESSION_KEY: SESSION_KEY,
    RESULTS_KEY: RESULTS_KEY
  });
})(window);
