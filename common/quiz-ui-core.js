(function (global) {
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
      const gameCard = document.getElementById("game-card");
      const bar = document.getElementById("timer-bar");
      const label = document.getElementById("timer-label");
      if (useGameCardDanger && gameCard) gameCard.classList.remove("time-danger");
      if (bar) bar.classList.remove("warn", "danger");
      if (label) label.classList.remove("danger");
    }

    function updateTimerUI() {
      const pct = (getTimeLeft() / getTimeLimit()) * 100;
      const bar = document.getElementById("timer-bar");
      const label = document.getElementById("timer-label");
      const text = document.getElementById("timer-text");
      const gameCard = document.getElementById("game-card");

      if (text) text.textContent = Math.ceil(getTimeLeft());
      if (bar) {
        bar.style.width = pct + "%";
        bar.classList.remove("warn", "danger");
      }
      if (label) label.classList.remove("danger");
      if (useGameCardDanger && gameCard) gameCard.classList.remove("time-danger");

      if (pct <= 25) {
        if (bar) bar.classList.add("danger");
        if (label) label.classList.add("danger");
        if (useGameCardDanger && gameCard) gameCard.classList.add("time-danger");
      } else if (pct <= 50) {
        if (bar) bar.classList.add("warn");
      }
    }

    return { startTimer, stopTimer, updateTimerUI };
  }

  function createStatsModalCore(options) {
    const { renderStatsTable } = options;

    function openStats() {
      renderStatsTable();
      document.getElementById("stats-modal").style.display = "flex";
    }

    function closeStats() {
      document.getElementById("stats-modal").style.display = "none";
    }

    function onModalBackdrop(e) {
      if (e.target === document.getElementById("stats-modal")) closeStats();
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

  global.QuizUICore = {
    createTimerCore,
    createStatsModalCore,
    createAnswerFlowCore,
    createSequentialAnswerCore,
  };
})(window);
