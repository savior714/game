/**
 * Bind the shared quiz progression button to the subject's nextQuestion handler.
 * Loaded after each subject ui.js so the handler and button both exist.
 */
(function bindQuizProgressionControl(global) {
  const nextButton = document.getElementById('next-btn');
  if (!nextButton) throw new Error('Quiz next button is missing.');
  if (nextButton.dataset.progressionBound === 'true') return;

  const advanceQuestion = global.nextQuestion;
  if (typeof advanceQuestion !== 'function') {
    throw new Error('Quiz nextQuestion handler is missing.');
  }

  nextButton.addEventListener('click', advanceQuestion);
  nextButton.dataset.progressionBound = 'true';
})(window);
