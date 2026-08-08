(function (root) {
  'use strict';

  var Engine = root.WeeklyTestEngine;
  var SCHEMA_VERSION = 1;
  var dom = {};
  var testSet = null;
  var session = null;
  var mode = 'start';
  var lastResult = null;
  var startTime = null;

  function $(id) { return document.getElementById(id); }

  function showScreen(name) {
    ['start-screen', 'test-screen', 'review-screen', 'result-screen'].forEach(function (s) {
      var el = $(s);
      if (el) el.style.display = (s === name) ? 'block' : 'none';
    });
    mode = name;
  }

  function renderStart() {
    var savedSession = Engine.loadSession();
    var contBtn = $('continue-btn');
    var resumeBanner = $('resume-banner');
    if (savedSession && savedSession.status === 'in_progress') {
      if (resumeBanner) resumeBanner.style.display = 'block';
      if (contBtn) contBtn.style.display = 'inline-block';
    } else {
      if (resumeBanner) resumeBanner.style.display = 'none';
      if (contBtn) contBtn.style.display = 'none';
    }

    $('test-title').textContent = testSet.title;
    $('test-total').textContent = testSet.items.length + '개 단어';
    showScreen('start-screen');
  }

  function startNewTest() {
    session = Engine.createSession(testSet);
    startTime = Date.now();
    Engine.saveSession(session);
    renderQuestion();
  }

  function resumeTest() {
    session = Engine.loadSession();
    if (!session) {
      startNewTest();
      return;
    }
    if (session.items && session.items.length > 0) {
      testSet = {
        schemaVersion: SCHEMA_VERSION,
        setId: session.setId,
        title: session.setId,
        promptMode: 'definition-to-spelling',
        items: session.items
      };
    }
    startTime = Date.now();
    renderQuestion();
  }

  function renderQuestion() {
    showScreen('test-screen');
    var item = testSet.items[session.currentIndex];
    var total = testSet.items.length;
    var current = session.currentIndex + 1;

    $('q-number').textContent = current + ' / ' + total;
    $('q-prompt').textContent = item.prompt;

    var input = $('answer-input');
    input.value = session.answers[item.id] || '';
    input.disabled = false;
    input.className = 'wt-input';

    $('q-progress-bar').style.width = (current / total * 100) + '%';

    $('prev-btn').style.visibility = session.currentIndex === 0 ? 'hidden' : 'visible';

    updateEmptyState();
    setTimeout(function () { input.focus(); }, 50);
  }

  function updateEmptyState() {
    var input = $('answer-input');
    var emptyMsg = $('empty-msg');
    if (!input || !emptyMsg) return;
    emptyMsg.style.display = input.value.trim() === '' ? 'block' : 'none';
  }

  function moveToNext() {
    var item = testSet.items[session.currentIndex];
    var input = $('answer-input');
    session.answers[item.id] = input.value;
    Engine.saveSession(session);

    if (session.currentIndex >= testSet.items.length - 1) {
      renderReview();
    } else {
      session.currentIndex++;
      Engine.saveSession(session);
      renderQuestion();
    }
  }

  function moveToPrev() {
    if (session.currentIndex <= 0) return;
    var input = $('answer-input');
    var item = testSet.items[session.currentIndex];
    session.answers[item.id] = input.value;
    session.currentIndex--;
    Engine.saveSession(session);
    renderQuestion();
  }

  function renderReview() {
    showScreen('review-screen');
    var list = $('review-list');
    list.innerHTML = '';

    var unanswered = [];

    testSet.items.forEach(function (item, idx) {
      var given = session.answers[item.id] || '';
      if (given.trim() === '') unanswered.push(idx + 1);

      var row = document.createElement('div');
      row.className = 'review-row';
      row.innerHTML =
        '<span class="review-num">' + (idx + 1) + '.</span>' +
        '<span class="review-answer' + (given.trim() === '' ? ' review-empty' : '') + '">' +
          (given.trim() === '' ? '미입력' : escapeHtml(given)) +
        '</span>';
      row.addEventListener('click', (function (targetIdx) {
        return function () {
          session.currentIndex = targetIdx;
          Engine.saveSession(session);
          renderQuestion();
        };
      })(idx));
      list.appendChild(row);
    });

    var warn = $('unanswered-warning');
    if (warn) {
      if (unanswered.length > 0) {
        warn.style.display = 'block';
        warn.textContent = '입력하지 않은 문제: ' + unanswered.join(', ');
      } else {
        warn.style.display = 'none';
      }
    }
  }

  function submitTest() {
    if (!confirm('정말로 최종 제출하시겠습니까? 제출 후에는 수정할 수 없습니다.')) return;

    var result = Engine.gradeSession(testSet, session);
    lastResult = result;
    Engine.saveResult(result);
    Engine.clearSession();
    renderResult(result);
  }

  function renderResult(result) {
    showScreen('result-screen');
    var pct = result.total > 0 ? Math.round(result.correct / result.total * 100) : 0;
    var elapsedSec = Math.floor(result.elapsedMs / 1000);
    var min = Math.floor(elapsedSec / 60);
    var sec = elapsedSec % 60;
    var timeStr = min > 0 ? min + '분 ' + sec + '초' : sec + '초';

    $('result-score').textContent = result.correct + ' / ' + result.total;
    $('result-pct').textContent = pct + '%';
    $('result-time').textContent = timeStr;

    var detailList = $('result-detail');
    detailList.innerHTML = '';

    result.results.forEach(function (r) {
      var row = document.createElement('div');
      row.className = 'result-item ' + (r.correct ? 'result-correct' : 'result-wrong');
      row.innerHTML =
        '<div class="result-icon">' + (r.correct ? '✅' : '❌') + '</div>' +
        '<div class="result-word">' + escapeHtml(r.answer) + '</div>' +
        '<div class="result-prompt">' + escapeHtml(r.prompt) + '</div>' +
        '<div class="result-comparison">' +
          '<div class="result-myanswer">내 답: ' + (r.given.trim() === '' ? '(미입력)' : escapeHtml(r.given)) + '</div>' +
          (r.correct ? '' : '<div class="result-answer">정답: ' + escapeHtml(r.answer) + '</div>') +
        '</div>';
      detailList.appendChild(row);
    });

    var retryBtn = $('retry-wrong-btn');
    var wrongCount = result.results.filter(function (r) { return !r.correct; }).length;
    if (wrongCount === 0) {
      retryBtn.style.display = 'none';
    } else {
      retryBtn.style.display = 'inline-block';
      retryBtn.textContent = '틀린 단어 다시 쓰기 (' + wrongCount + '개)';
    }
  }

  function retryWrongWords() {
    if (!lastResult) return;
    var wrongSet = Engine.buildWrongWordSet(lastResult);
    if (wrongSet.items.length === 0) return;
    testSet = wrongSet;
    startNewTest();
  }

  function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function init() {
    var savedSession = Engine.loadSession();
    if (savedSession && savedSession.items && savedSession.items.length > 0) {
      testSet = {
        schemaVersion: SCHEMA_VERSION,
        setId: savedSession.setId,
        title: savedSession.setId,
        promptMode: 'definition-to-spelling',
        items: savedSession.items
      };
    } else {
      testSet = Engine.buildTestSet();
    }

    dom.startScreen = $('start-screen');
    dom.testScreen = $('test-screen');
    dom.reviewScreen = $('review-screen');
    dom.resultScreen = $('result-screen');

    $('start-btn').addEventListener('click', startNewTest);
    $('continue-btn').addEventListener('click', resumeTest);
    $('prev-btn').addEventListener('click', moveToPrev);
    $('submit-btn').addEventListener('click', submitTest);
    $('retry-wrong-btn').addEventListener('click', retryWrongWords);
    $('result-restart-btn').addEventListener('click', function () {
      testSet = Engine.buildTestSet();
      startNewTest();
    });

    var input = $('answer-input');
    input.addEventListener('keydown', function (event) {
      if (event.key !== 'Enter') return;
      if (event.isComposing) return;
      event.preventDefault();
      var val = input.value.trim();
      if (val === '') {
        updateEmptyState();
        return;
      }
      moveToNext();
    });
    input.addEventListener('input', updateEmptyState);

    renderStart();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window);
