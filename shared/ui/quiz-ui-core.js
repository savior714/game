/**
 * QuizUICore - 퀴즈 UI 공통 모듈
 * @module QuizUICore
 */

/**
 * 타이머 코어 옵션
 * @typedef {Object} TimerCoreOptions
 * @property {function(): number} getTimeLimit
 * @property {function(): number} getTimeLeft
 * @property {function(number): void} setTimeLeft
 * @property {function(): ?number} getTimerInterval
 * @property {function(?number): void} setTimerInterval
 * @property {function(): void} onTimeout
 * @property {boolean} [useGameCardDanger]
 */

/**
 * 답변 컨텍스트
 * @typedef {Object} AnswerContext
 * @property {string} [value]
 * @property {string|string[]} [answer]
 * @property {number} elapsed
 * @property {HTMLElement} [button]
 */

(function (global) {
  /**
   * 타이머 코어 생성
   * @param {TimerCoreOptions} options
   * @returns {{startTimer: function(): void, stopTimer: function(): void, updateTimerUI: function(): void}}
   */
  function createTimerCore(options) {
    const {
      getTimeLimit,
      getTimeLeft,
      setTimeLeft,
      getTimerInterval,
      setTimerInterval,
      onTimeout,
      useGameCardDanger,
    } = options;

    const els = {
      gameCard: document.getElementById("game-card"),
      timerBar: document.getElementById("timer-bar"),
      timerLabel: document.getElementById("timer-label"),
      timerText: document.getElementById("timer-text"),
    };

    function startTimer() {
      stopTimer();
      setTimeLeft(getTimeLimit());
      updateTimerUI();
      const id = setInterval(() => {
        setTimeLeft(getTimeLeft() - 0.25);
        if (getTimeLeft() <= 0) {
          setTimeLeft(0);
          updateTimerUI();
          stopTimer();
          onTimeout();
        } else {
          updateTimerUI();
        }
      }, 250);
      setTimerInterval(id);
    }

    function stopTimer() {
      clearInterval(getTimerInterval());
      setTimerInterval(null);
      if (useGameCardDanger && els.gameCard) els.gameCard.classList.remove("time-danger");
      if (els.timerBar) els.timerBar.classList.remove("warn", "danger");
      if (els.timerLabel) els.timerLabel.classList.remove("danger");
    }

    function updateTimerUI() {
      const pct = (getTimeLeft() / getTimeLimit()) * 100;

      if (els.timerText) els.timerText.textContent = Math.ceil(getTimeLeft());
      if (els.timerBar) {
        els.timerBar.style.width = pct + "%";
        els.timerBar.classList.remove("warn", "danger");
      }
      if (els.timerLabel) els.timerLabel.classList.remove("danger");
      if (useGameCardDanger && els.gameCard) els.gameCard.classList.remove("time-danger");

      if (pct <= 25) {
        if (els.timerBar) els.timerBar.classList.add("danger");
        if (els.timerLabel) els.timerLabel.classList.add("danger");
        if (useGameCardDanger && els.gameCard) els.gameCard.classList.add("time-danger");
      } else if (pct <= 50) {
        if (els.timerBar) els.timerBar.classList.add("warn");
      }
    }

    return { startTimer, stopTimer, updateTimerUI };
  }

  function createStatsModalCore(options) {
    const { renderStatsTable } = options;

    const els = {
      statsModal: document.getElementById("stats-modal"),
    };

    function openStats() {
      if (els.statsModal) {
        els.statsModal._prevFocusTarget = document.activeElement || null;
      }
      renderStatsTable();
      if (els.statsModal) els.statsModal.style.display = "flex";
      const closeBtn = document.getElementById("close-stats-btn");
      if (closeBtn && typeof closeBtn.focus === "function") {
        try { closeBtn.focus(); } catch (_) {}
      }
    }

    function closeStats() {
      if (els.statsModal) els.statsModal.style.display = "none";
      const target = els.statsModal ? els.statsModal._prevFocusTarget : null;
      if (els.statsModal) {
        els.statsModal._prevFocusTarget = null;
      }
      if (target && typeof target.focus === "function") {
        try {
          if (target.isConnected) {
            target.focus();
          }
        } catch (_) {}
      }
    }

    function onModalBackdrop(e) {
      if (e.target === els.statsModal) closeStats();
    }

    return { openStats, closeStats, onModalBackdrop };
  }

  function createAnswerFlowCore(options) {
    const {
      getAnswered,
      setAnswered,
      getTimeLimit,
      getTimeLeft,
      stopTimer,
      recordResult,
      getAnswer,
      markCorrectChoices,
      onCorrect,
      onWrong,
      showNextButton,
    } = options;

    function evaluateStandard(value, button) {
      if (getAnswered()) return false;

      setAnswered(true);
      const elapsed = getTimeLimit() - getTimeLeft();
      stopTimer();
      markCorrectChoices();

      const answer = getAnswer();
      if (value === answer) {
        recordResult(true, elapsed);
        onCorrect({ value, answer, elapsed, button });
      } else {
        recordResult(false, elapsed);
        onWrong({ value, answer, elapsed, button });
      }

      showNextButton();
      return true;
    }

    return { evaluateStandard };
  }

  function createSequentialAnswerCore(options) {
    const {
      setAnswered,
      getTimeLimit,
      getTimeLeft,
      stopTimer,
      recordResult,
      onSuccess,
      onFailure,
      showNextButton,
    } = options;

    function finalizeSuccess(context) {
      setAnswered(true);
      const elapsed = getTimeLimit() - getTimeLeft();
      stopTimer();
      recordResult(true, elapsed);
      onSuccess({ ...context, elapsed });
      showNextButton();
      return true;
    }

    function finalizeFailure(context) {
      setAnswered(true);
      const elapsed = getTimeLimit() - getTimeLeft();
      stopTimer();
      recordResult(false, elapsed);
      onFailure({ ...context, elapsed });
      showNextButton();
      return true;
    }

    return { finalizeSuccess, finalizeFailure };
  }

  /**
   * 문제 생성 에러 처리 함수
   * - 에러 발생 시 안내 모달 표시
   * - 과목별 ui.js에서 try/catch 블록 내에서 호출
   * @param {Error} [err] - 발생한 에러 객체 (선택)
   * @returns {void}
   */
  function handleQuestionError(err) {
    console.error('[QuizUICore] 문제 생성 에러:', err);
    const els = {
      question: document.getElementById('question'),
      answerButtons: document.getElementById('answer-buttons'),
    };
    if (els.question) {
      els.question.innerHTML = '<div class="error-message">⚠️ 문제를 불러오지 못했어요.<br>다시 시도해주세요!</div>';
    }
    if (els.answerButtons) {
      els.answerButtons.innerHTML = '<button class="answer-btn" onclick="location.reload()">다시 시작 🔄</button>';
    }
  }

  /**
   * QuizUICore 전역 객체
   * @typedef {Object} QuizUICore
   * @property {typeof createTimerCore} createTimerCore
   * @property {typeof createStatsModalCore} createStatsModalCore
   * @property {typeof createAnswerFlowCore} createAnswerFlowCore
   * @property {typeof createSequentialAnswerCore} createSequentialAnswerCore
   * @property {typeof handleQuestionError} handleQuestionError
   */

  /** @type {QuizUICore} */
  global.QuizUICore = {
    createTimerCore,
    createStatsModalCore,
    createAnswerFlowCore,
    createSequentialAnswerCore,
    handleQuestionError,
  };
})(window);
