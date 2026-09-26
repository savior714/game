(function (root) {
  'use strict';

  var Engine = root.WeeklyTestEngine;
  var SCHEMA_VERSION = 1;
  var testSet = null;
  var session = null;
  var isFeedbackState = false;
  var isSubmitting = false;
  var autoNextTimer = null;

  function $(id) {
    return document.getElementById(id);
  }

  function clearAutoNextTimer() {
    if (autoNextTimer) {
      clearTimeout(autoNextTimer);
      autoNextTimer = null;
    }
  }

  function renderDiffView(container, expectedWord, givenWord) {
    container.textContent = '';

    var diffOps = Engine.computeSpellingDiff(givenWord, expectedWord);

    var diffTable = document.createElement('div');
    diffTable.className = 'wt-diff-table';

    // 1. 내 답 행
    var givenRow = document.createElement('div');
    givenRow.className = 'wt-diff-row wt-diff-row-given';

    var givenLabel = document.createElement('span');
    givenLabel.className = 'wt-diff-row-label';
    givenLabel.textContent = '내 입력:';
    givenRow.appendChild(givenLabel);

    var givenChips = document.createElement('div');
    givenChips.className = 'wt-diff-chips';

    // 2. 정답 행
    var expectedRow = document.createElement('div');
    expectedRow.className = 'wt-diff-row wt-diff-row-expected';

    var expectedLabel = document.createElement('span');
    expectedLabel.className = 'wt-diff-row-label';
    expectedLabel.textContent = '정답:';
    expectedRow.appendChild(expectedLabel);

    var expectedChips = document.createElement('div');
    expectedChips.className = 'wt-diff-chips';

    diffOps.forEach(function (op) {
      if (op.type === 'match') {
        var cGiven = document.createElement('span');
        cGiven.className = 'wt-chip wt-chip-match';
        cGiven.textContent = op.char;
        givenChips.appendChild(cGiven);

        var cExpected = document.createElement('span');
        cExpected.className = 'wt-chip wt-chip-match';
        cExpected.textContent = op.char;
        expectedChips.appendChild(cExpected);
      } else if (op.type === 'substitution') {
        var cSubGiven = document.createElement('span');
        cSubGiven.className = 'wt-chip wt-chip-sub-given';
        cSubGiven.textContent = op.givenChar;
        cSubGiven.title = '틀린 글자';
        givenChips.appendChild(cSubGiven);

        var cSubExpected = document.createElement('span');
        cSubExpected.className = 'wt-chip wt-chip-sub-expected';
        cSubExpected.textContent = op.expectedChar;
        cSubExpected.title = '올바른 글자';
        expectedChips.appendChild(cSubExpected);
      } else if (op.type === 'extra') {
        var cExtra = document.createElement('span');
        cExtra.className = 'wt-chip wt-chip-extra';
        cExtra.textContent = op.char;
        cExtra.title = '불필요한 글자';
        givenChips.appendChild(cExtra);

        var cPlaceholder = document.createElement('span');
        cPlaceholder.className = 'wt-chip wt-chip-placeholder';
        cPlaceholder.textContent = '·';
        expectedChips.appendChild(cPlaceholder);
      } else if (op.type === 'missing') {
        var cPlaceholderGiven = document.createElement('span');
        cPlaceholderGiven.className = 'wt-chip wt-chip-placeholder';
        cPlaceholderGiven.textContent = '·';
        givenChips.appendChild(cPlaceholderGiven);

        var cMissing = document.createElement('span');
        cMissing.className = 'wt-chip wt-chip-missing';
        cMissing.textContent = op.char;
        cMissing.title = '빠진 글자';
        expectedChips.appendChild(cMissing);
      }
    });

    givenRow.appendChild(givenChips);
    expectedRow.appendChild(expectedChips);

    diffTable.appendChild(givenRow);
    diffTable.appendChild(expectedRow);
    container.appendChild(diffTable);

    // 정답 텍스트 명시
    var targetWordNote = document.createElement('div');
    targetWordNote.className = 'wt-diff-summary';
    var targetWordStrong = document.createElement('strong');
    targetWordStrong.textContent = expectedWord;
    targetWordNote.appendChild(document.createTextNode('올바른 철자: '));
    targetWordNote.appendChild(targetWordStrong);
    container.appendChild(targetWordNote);
  }

  function renderQuestion() {
    clearAutoNextTimer();
    isFeedbackState = false;
    isSubmitting = false;

    $('test-screen').style.display = 'block';
    $('result-screen').style.display = 'none';

    var currentIndex = session.currentIndex;
    var total = testSet.items.length;
    var currentItem = testSet.items[currentIndex];

    $('q-number').textContent = (currentIndex + 1) + ' / ' + total;
    $('q-progress-bar').style.width = ((currentIndex + 1) / total * 100) + '%';
    $('q-prompt').textContent = currentItem.prompt;

    var input = $('answer-input');
    input.value = '';
    input.disabled = false;
    $('empty-msg').style.display = 'none';

    $('feedback-box').style.display = 'none';
    $('feedback-correct').style.display = 'none';
    $('feedback-wrong').style.display = 'none';

    $('check-btn').style.display = 'inline-flex';
    $('next-btn').style.display = 'none';

    setTimeout(function () {
      input.focus();
    }, 30);
  }

  function submitCurrentAnswer() {
    if (isSubmitting || isFeedbackState) return;

    var input = $('answer-input');
    var rawAnswer = input.value;
    if (rawAnswer.trim() === '') {
      $('empty-msg').style.display = 'block';
      input.focus();
      return;
    }
    $('empty-msg').style.display = 'none';

    isSubmitting = true;
    input.disabled = true;

    var item = testSet.items[session.currentIndex];
    var isCorrect = Engine.gradeAnswer(item, rawAnswer);

    session.answers[item.id] = rawAnswer;
    session.results = session.results || [];
    session.results[session.currentIndex] = {
      id: item.id,
      answer: item.answer,
      prompt: item.prompt,
      given: rawAnswer,
      correct: isCorrect
    };
    Engine.saveSession(session);

    // 학습 evidence 기록
    if (typeof MilestoneTracker !== 'undefined') {
      MilestoneTracker.record(isCorrect);
    }
    if (isCorrect && typeof DailyStreak !== 'undefined') {
      DailyStreak.recordAnswer('english');
    }
    if (isCorrect && typeof DiversityReward !== 'undefined') {
      DiversityReward.recordCorrect('english');
    }

    if (isCorrect) {
      // 정답 피드백: 0.7초 후 자동 다음 문제
      $('feedback-box').style.display = 'block';
      $('feedback-correct').style.display = 'flex';
      $('feedback-wrong').style.display = 'none';

      $('check-btn').style.display = 'none';
      $('next-btn').style.display = 'none';

      autoNextTimer = setTimeout(function () {
        isSubmitting = false;
        advanceToNextQuestion();
      }, 700);
    } else {
      // 오답 피드백: 자동 이동하지 않고 diff 표시
      isFeedbackState = true;
      isSubmitting = false;

      $('feedback-box').style.display = 'block';
      $('feedback-correct').style.display = 'none';
      $('feedback-wrong').style.display = 'block';

      var diffContainer = $('spelling-diff-container');
      renderDiffView(diffContainer, item.answer, rawAnswer);

      $('check-btn').style.display = 'none';
      var nextBtn = $('next-btn');
      nextBtn.style.display = 'inline-flex';
      setTimeout(function () {
        nextBtn.focus();
      }, 30);
    }
  }

  function advanceToNextQuestion() {
    clearAutoNextTimer();
    session.currentIndex++;

    if (session.currentIndex >= testSet.items.length) {
      finishTest();
    } else {
      Engine.saveSession(session);
      renderQuestion();
    }
  }

  function finishTest() {
    clearAutoNextTimer();
    session.status = 'completed';
    Engine.saveSession(session);

    var finalResult = Engine.gradeSession(testSet, session);
    Engine.saveResult(finalResult);

    // 학습 evidence 세션 종료 및 과목 완료 hook
    if (typeof MilestoneTracker !== 'undefined') {
      MilestoneTracker.endSession();
      MilestoneTracker.onSubjectComplete('english');
    }

    renderResult(finalResult);
  }

  function renderResult(result) {
    clearAutoNextTimer();
    $('test-screen').style.display = 'none';
    $('result-screen').style.display = 'block';

    var pct = result.total > 0 ? Math.round(result.correct / result.total * 100) : 0;
    $('result-score').textContent = result.correct + ' / ' + result.total;
    $('result-pct').textContent = pct + '%';

    var wrongItems = result.results.filter(function (r) {
      return !r.correct;
    });

    var wrongSection = $('wrong-section');
    var perfectMsg = $('perfect-msg');
    var wrongList = $('wrong-list');

    if (wrongItems.length > 0) {
      wrongSection.style.display = 'block';
      perfectMsg.style.display = 'none';
      wrongList.textContent = '';

      wrongItems.forEach(function (w, idx) {
        var itemCard = document.createElement('div');
        itemCard.className = 'wt-wrong-card';

        var header = document.createElement('div');
        header.className = 'wt-wrong-card-header';

        var numBadge = document.createElement('span');
        numBadge.className = 'wt-wrong-badge';
        numBadge.textContent = '단어 ' + (idx + 1);
        header.appendChild(numBadge);

        var promptText = document.createElement('span');
        promptText.className = 'wt-wrong-prompt';
        promptText.textContent = w.prompt;
        header.appendChild(promptText);

        itemCard.appendChild(header);

        var diffArea = document.createElement('div');
        diffArea.className = 'wt-wrong-diff-mount';
        renderDiffView(diffArea, w.answer, w.given);
        itemCard.appendChild(diffArea);

        wrongList.appendChild(itemCard);
      });
    } else {
      wrongSection.style.display = 'none';
      perfectMsg.style.display = 'block';
    }

    setTimeout(function () {
      var restartBtn = $('result-restart-btn');
      if (restartBtn) restartBtn.focus();
    }, 30);
  }

  function startNewTest() {
    clearAutoNextTimer();
    session = Engine.createSession(testSet, { shuffle: true });
    testSet.items = session.items;
    Engine.saveSession(session);

    // 학습 evidence 세션 초기화
    if (typeof MilestoneTracker !== 'undefined') {
      MilestoneTracker.initSession('english');
      MilestoneTracker.resetSessionData();
    }

    renderQuestion();
  }

  function init() {
    testSet = Engine.buildTestSet();
    var savedSession = Engine.loadSession(testSet.setId);

    if (
      savedSession &&
      savedSession.schemaVersion === SCHEMA_VERSION &&
      savedSession.status === 'in_progress' &&
      savedSession.setId === testSet.setId &&
      Array.isArray(savedSession.items) &&
      savedSession.items.length === testSet.items.length &&
      typeof savedSession.currentIndex === 'number' &&
      savedSession.currentIndex < savedSession.items.length
    ) {
      session = savedSession;
      testSet.items = session.items;
      renderQuestion();
    } else {
      Engine.clearSession();
      startNewTest();
    }

    // 버튼 이벤트 연결
    $('check-btn').addEventListener('click', function () {
      submitCurrentAnswer();
    });

    $('next-btn').addEventListener('click', function () {
      if (isFeedbackState) {
        advanceToNextQuestion();
      }
    });

    $('result-restart-btn').addEventListener('click', function () {
      Engine.clearSession();
      testSet = Engine.buildTestSet();
      startNewTest();
    });

    var input = $('answer-input');
    input.addEventListener('input', function () {
      $('empty-msg').style.display = 'none';
    });

    // 키보드 엔터 처리 (IME composition 방어 및 더블 엔터 방어)
    document.addEventListener('keydown', function (event) {
      if (event.key !== 'Enter') return;
      if (event.isComposing || event.keyCode === 229) return;

      // 시험 진행 화면이 활성화되어 있을 때만
      if ($('test-screen').style.display === 'block') {
        event.preventDefault();
        if (isSubmitting) return; // 더블 엔터 방어!

        if (isFeedbackState) {
          advanceToNextQuestion();
        } else {
          submitCurrentAnswer();
        }
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window);
