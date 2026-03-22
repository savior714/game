/* ═══════════════════════════════════
   타이머
═══════════════════════════════════ */
function startTimer() {
  stopTimer();
  timeLeft = TIME_LIMIT;
  updateTimerUI();
  timerInterval = setInterval(() => {
    timeLeft -= 0.25;
    if (timeLeft <= 0) {
      timeLeft = 0;
      updateTimerUI();
      stopTimer();
      timeOut();
    } else {
      updateTimerUI();
    }
  }, 250);
}

function stopTimer() {
  clearInterval(timerInterval);
  timerInterval = null;
  document.getElementById('game-card').classList.remove('time-danger');
  document.getElementById('timer-bar').classList.remove('warn', 'danger');
  document.getElementById('timer-label').classList.remove('danger');
}

function updateTimerUI() {
  const pct   = timeLeft / TIME_LIMIT * 100;
  const bar   = document.getElementById('timer-bar');
  const label = document.getElementById('timer-label');
  document.getElementById('timer-text').textContent = Math.ceil(timeLeft);
  bar.style.width = pct + '%';
  bar.classList.remove('warn', 'danger');
  label.classList.remove('danger');
  document.getElementById('game-card').classList.remove('time-danger');
  if (pct <= 25) {
    bar.classList.add('danger');
    label.classList.add('danger');
    document.getElementById('game-card').classList.add('time-danger');
  } else if (pct <= 50) {
    bar.classList.add('warn');
  }
}

function timeOut() {
  if (answered) return;
  answered = true;
  recordResult(false, TIME_LIMIT);
  playTimeout();
  document.querySelectorAll('.answer-btn').forEach(b => {
    if (parseInt(b.textContent) === answer) b.classList.add('correct');
  });
  const fb = document.getElementById('feedback');
  fb.textContent = `\u23F0 \uc2dc\uac04 \ucd08\uacfc! \uc815\ub2f5\uc740 ${answer}\uc774\uc5d0\uc694!`;
  fb.className   = 'feedback-wrong';
  document.getElementById('next-btn').style.display = 'inline-block';
}

/* ═══════════════════════════════════
   정답 확인
═══════════════════════════════════ */
function checkAnswer(val, btn) {
  if (answered) return;
  answered      = true;
  const elapsed = TIME_LIMIT - timeLeft;
  stopTimer();

  document.querySelectorAll('.answer-btn').forEach(b => {
    if (parseInt(b.textContent) === answer) b.classList.add('correct');
  });

  const fb = document.getElementById('feedback');
  if (val === answer) {
    recordResult(true, elapsed);
    score++;
    document.getElementById('q-score').textContent = score;
    fb.textContent = ['\uc798\ud588\uc5b4\uc694! \uD83C\uDF89', '\ub9de\uc558\uc5b4\uc694! \u2B50', '\uc644\ubcbd\ud574\uc694! \uD83C\uDF1F', '\ud5c8\ub96d\ud574\uc694! \uD83D\uDC4F'][Math.floor(Math.random()*4)];
    fb.className   = 'feedback-correct';
    playCorrect();
    spawnConfetti();
  } else {
    recordResult(false, elapsed);
    btn.classList.add('wrong');
    fb.textContent = `\uc815\ub2f5\uc740 ${answer}\uc774\uc5d0\uc694! \ub2e4\uc2dc \ud574\ubd10\uc694 \uD83D\uDE0A`;
    fb.className   = 'feedback-wrong';
    playWrong();
  }
  document.getElementById('next-btn').style.display = 'inline-block';
}

/* ═══════════════════════════════════
   게임 흐름
═══════════════════════════════════ */
function nextQuestion() {
  currentQ++;
  if (currentQ >= TOTAL) showResult();
  else askQuestion();
}

function showResult() {
  document.getElementById('game-area').style.display     = 'none';
  document.getElementById('result-screen').style.display = 'block';
  const pct = score / TOTAL;
  let stars, title, msg;
  if (pct === 1)       { stars = '\u2B50\u2B50\u2B50'; title = '\uc644\ubcbd\ud574\uc694!';        msg = `10\ubb38\uc81c \ubaa8\ub450 \ub9de\ucccb\uc5b4\uc694! \uc815\ub9d0 \ub300\ub2e8\ud574\uc694! \uD83C\uDF8A`; }
  else if (pct >= 0.7) { stars = '\u2B50\u2B50';  title = '\uc798\ud588\uc5b4\uc694!';        msg = `10\ubb38\uc81c \uc911 ${score}\uac1c \ub9de\ucccb\uc5b4\uc694! \ucd5c\uace0\uc608\uc694! \uD83D\uDE04`; }
  else                 { stars = '\u2B50';    title = '\uc870\uae08 \ub354 \uc5f0\uc2b5\ud574\uc694!'; msg = `10\ubb38\uc81c \uc911 ${score}\uac1c \ub9de\ucccb\uc5b4\uc694. \ub2e4\uc2dc \ud574\ubd10\uc694! \uD83D\uDCAA`; }
  document.getElementById('stars').textContent        = stars;
  document.getElementById('result-title').textContent = title;
  document.getElementById('result-msg').textContent   = msg;
}

function startGame() {
  stopTimer();
  currentQ = 0;
  score    = 0;
  stats    = loadStats();
  document.getElementById('q-score').textContent         = 0;
  document.getElementById('result-screen').style.display = 'none';
  document.getElementById('game-area').style.display     = 'block';
  askQuestion();
}

/* ═══════════════════════════════════
   통계 모달
═══════════════════════════════════ */
function openStats() {
  renderStatsTable();
  document.getElementById('stats-modal').style.display = 'flex';
}

function closeStats() {
  document.getElementById('stats-modal').style.display = 'none';
}

function onModalBackdrop(e) {
  if (e.target === document.getElementById('stats-modal')) closeStats();
}

function renderStatsTable() {
  const OP_LABELS = { '+': '\ub367\uc148 (+)', '-': '\ube7c\uc148 (-)', '\xD7': '\uacf1\uc148 (\xD7)' };
  const tbody = document.getElementById('stats-tbody');
  tbody.innerHTML = '';

  for (const op of ['+', '-', '\xD7']) {
    const s       = stats[op];
    const acc     = s.attempts > 0 ? Math.round(s.correct / s.attempts * 100) + '%' : '-';
    const avgT    = s.attempts > 0 ? (s.totalTime / s.attempts).toFixed(1) + '\ucd08' : '-';
    const hasData = s.attempts >= MIN_DATA;
    const level   = hasData ? getBaseDiffLevel(op) : -1;
    const badge   = hasData
      ? `<span class="diff-badge" style="background:${DIFF_COLORS[level]}">${DIFF_LABELS[level]}</span>`
      : `<span class="diff-badge" style="background:#ccc">\ub370\uc774\ud130 \ubd80\uc871</span>`;

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${OP_LABELS[op]}</td>
      <td>${s.attempts}</td>
      <td>${acc}</td>
      <td>${avgT}</td>
      <td>${badge}</td>
    `;
    tbody.appendChild(tr);
  }
}

function confirmResetStats() {
  if (confirm('\ub204\uc801 \uae30\ub85d\uc744 \ubaa8\ub450 \uc9c0\uc6b8\uae4c\uc694?')) resetStats();
}

/* ═══════════════════════════════════
   색종이
═══════════════════════════════════ */
function spawnConfetti() {
  const items = ['\uD83C\uDF89','\uD83C\uDF1F','\u2728','\uD83C\uDF8A','\u2B50','\uD83C\uDF6C','\uD83C\uDF88'];
  for (let i = 0; i < 8; i++) {
    setTimeout(() => {
      const el = document.createElement('div');
      el.className = 'confetti-emoji';
      el.textContent = items[Math.floor(Math.random() * items.length)];
      el.style.left  = Math.random() * 100 + 'vw';
      el.style.top   = '-40px';
      el.style.animationDuration = (1 + Math.random()) + 's';
      document.body.appendChild(el);
      setTimeout(() => el.remove(), 2500);
    }, i * 100);
  }
}

/* ═══════════════════════════════════
   시작
═══════════════════════════════════ */
initRocketPanel();
startGame();
