(function (root) {
  'use strict';

  var SCHEMA_VERSION = 1;
  var PROMPT_MODE = 'definition-to-spelling';
  var SESSION_KEY = 'englishWeeklyTestSessionV1';
  var RESULTS_KEY = 'englishWeeklyTestResultsV1';

  function normalizeAnswer(raw) {
    if (typeof raw !== 'string') return '';
    return raw.normalize('NFKC').trim().replace(/\s+/g, ' ').toLowerCase();
  }

  function shuffleArray(arr) {
    var array = arr.slice();
    for (var i = array.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var temp = array[i];
      array[i] = array[j];
      array[j] = temp;
    }
    return array;
  }

  function computeSpellingDiff(rawGiven, rawExpected) {
    var given = normalizeAnswer(rawGiven);
    var expected = normalizeAnswer(rawExpected);
    var n = given.length;
    var m = expected.length;

    var dp = [];
    for (var i = 0; i <= n; i++) {
      dp[i] = [];
      for (var j = 0; j <= m; j++) {
        dp[i][j] = 0;
      }
    }
    for (var i = 0; i <= n; i++) dp[i][0] = i;
    for (var j = 0; j <= m; j++) dp[0][j] = j;

    for (var i = 1; i <= n; i++) {
      for (var j = 1; j <= m; j++) {
        if (given[i - 1] === expected[j - 1]) {
          dp[i][j] = dp[i - 1][j - 1];
        } else {
          var costSub = dp[i - 1][j - 1] + 1;
          var costDel = dp[i - 1][j] + 1; // deletion from given (extra character in given)
          var costIns = dp[i][j - 1] + 1; // insertion into given (missing character in given)
          dp[i][j] = Math.min(costSub, costDel, costIns);
        }
      }
    }

    var ops = [];
    var ci = n;
    var cj = m;
    while (ci > 0 || cj > 0) {
      if (ci > 0 && cj > 0 && given[ci - 1] === expected[cj - 1] && dp[ci][cj] === dp[ci - 1][cj - 1]) {
        ops.push({ type: 'match', char: given[ci - 1] });
        ci--;
        cj--;
      } else if (ci > 0 && cj > 0 && dp[ci][cj] === dp[ci - 1][cj - 1] + 1) {
        ops.push({
          type: 'substitution',
          givenChar: given[ci - 1],
          expectedChar: expected[cj - 1]
        });
        ci--;
        cj--;
      } else if (ci > 0 && dp[ci][cj] === dp[ci - 1][cj] + 1) {
        ops.push({
          type: 'extra',
          char: given[ci - 1]
        });
        ci--;
      } else {
        ops.push({
          type: 'missing',
          char: expected[cj - 1]
        });
        cj--;
      }
    }
    ops.reverse();
    return ops;
  }

  function buildTestSet() {
    var canonicalSet = null;
    if (root && root.WeeklyVocabularyStore && typeof root.WeeklyVocabularyStore.getCurrentSet === 'function') {
      try {
        canonicalSet = root.WeeklyVocabularyStore.getCurrentSet();
      } catch (e) {
        canonicalSet = null;
      }
    } else if (typeof globalThis !== 'undefined' && globalThis.WeeklyVocabularyStore && typeof globalThis.WeeklyVocabularyStore.getCurrentSet === 'function') {
      try {
        canonicalSet = globalThis.WeeklyVocabularyStore.getCurrentSet();
      } catch (e) {
        canonicalSet = null;
      }
    } else if (typeof require === 'function') {
      try {
        var store = require('../weekly-vocabulary-store.js');
        if (store && typeof store.getCurrentSet === 'function') {
          canonicalSet = store.getCurrentSet();
        }
      } catch (e) {}
    }

    if (canonicalSet && Array.isArray(canonicalSet.items) && canonicalSet.items.length > 0) {
      var items = canonicalSet.items.map(function (it) {
        return {
          id: it.itemId || it.id,
          answer: it.word || it.answer,
          prompt: it.academyDescription !== undefined ? it.academyDescription : it.prompt,
          acceptedAnswers: it.acceptedAnswers || []
        };
      });
      return {
        schemaVersion: SCHEMA_VERSION,
        setId: canonicalSet.setId,
        title: canonicalSet.title || (canonicalSet.setId + ' 주간 영단어'),
        promptMode: PROMPT_MODE,
        items: items
      };
    }

    return {
      schemaVersion: SCHEMA_VERSION,
      setId: 'none',
      title: '주간 영단어',
      promptMode: PROMPT_MODE,
      items: []
    };
  }

  function createSession(testSet, options) {
    var now = new Date().toISOString();
    var shouldShuffle = (options && options.shuffle !== undefined) ? options.shuffle : true;
    var items = shouldShuffle ? shuffleArray(testSet.items) : testSet.items.slice();
    var answers = {};
    items.forEach(function (item) {
      answers[item.id] = '';
    });
    return {
      schemaVersion: SCHEMA_VERSION,
      setId: testSet.setId,
      status: 'in_progress',
      currentIndex: 0,
      answers: answers,
      results: [],
      items: items.map(function (item) {
        return {
          id: item.id,
          answer: item.answer,
          prompt: item.prompt,
          acceptedAnswers: item.acceptedAnswers || []
        };
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

  function loadSession(expectedSetId) {
    try {
      var raw = localStorage.getItem(SESSION_KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      if (!parsed || parsed.schemaVersion !== SCHEMA_VERSION) return null;
      if (expectedSetId && parsed.setId !== expectedSetId) {
        clearSession();
        return null;
      }
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
    var items = session.items && session.items.length > 0 ? session.items : testSet.items;
    items.forEach(function (item) {
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
      setId: session.setId || testSet.setId,
      total: items.length,
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

  root.WeeklyTestEngine = Object.freeze({
    normalizeAnswer: normalizeAnswer,
    shuffleArray: shuffleArray,
    computeSpellingDiff: computeSpellingDiff,
    buildTestSet: buildTestSet,
    createSession: createSession,
    saveSession: saveSession,
    loadSession: loadSession,
    clearSession: clearSession,
    gradeAnswer: gradeAnswer,
    gradeSession: gradeSession,
    saveResult: saveResult,
    getResults: getResults,
    SESSION_KEY: SESSION_KEY,
    RESULTS_KEY: RESULTS_KEY
  });
})(window);
