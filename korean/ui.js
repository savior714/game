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
  if (pct <= 25) {
    bar.classList.add('danger');
    label.classList.add('danger');
  } else if (pct <= 50) {
    bar.classList.add('warn');
  }
}

function timeOut() {
  if (answered) return;
  answered = true;
  recordResult(false, TIME_LIMIT);
  
  // 정답 표시
  document.querySelectorAll('.answer-btn').forEach(b => {
    if (b.textContent === answer) b.classList.add('correct');
  });

  const fb = document.getElementById('feedback');
  fb.textContent = `⏳ 시간 초과! 정답은 "${answer}"예요!`;
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
    if (b.textContent === answer) b.classList.add('correct');
  });

  const fb = document.getElementById('feedback');
  if (val === answer) {
    recordResult(true, elapsed);
    score++;
    document.getElementById('q-score').textContent = score;
    const msgs = ['참 잘했어요! ✨', '정답이에요! 👏', '대단해요! 🌟', '최고예요! 👍'];
    fb.textContent = msgs[Math.floor(Math.random() * msgs.length)];
    fb.className   = 'feedback-correct';
    spawnConfetti();
  } else {
    recordResult(false, elapsed);
    btn.classList.add('wrong');
    fb.textContent = `정답은 "${answer}"예요! 다시 해봐요 😊`;
    fb.className   = 'feedback-wrong';
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
  if (pct === 1) {
    stars = '⭐⭐⭐'; title = '완벽해요!'; msg = `10문제 모두 맞혔어요! 국어 박사님이시네요! 🎉`;
  } else if (pct >= 0.7) {
    stars = '⭐⭐'; title = '잘했어요!'; msg = `10문제 중 ${score}개 맞혔어요! 정말 훌륭해요! 😃`;
  } else {
    stars = '⭐'; title = '조금 더 연습해요!'; msg = `10문제 중 ${score}개 맞혔어요. 다음엔 더 잘할 수 있어요! 💪`;
  }
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
  const CAT_LABELS = { spelling: '받침/맞춤법', antonym: '반대말', honorific: '높임말' };
  const tbody = document.getElementById('stats-tbody');
  tbody.innerHTML = '';

  for (const cat of ['spelling', 'antonym', 'honorific']) {
    const s       = stats[cat];
    const acc     = s.attempts > 0 ? Math.round(s.correct / s.attempts * 100) + '%' : '-';
    const avgT    = s.attempts > 0 ? (s.totalTime / s.attempts).toFixed(1) + '초' : '-';
    const hasData = s.attempts >= MIN_DATA;
    const level   = hasData ? getBaseDiffLevel(cat) : -1;
    const badge   = hasData
      ? `<span class="diff-badge" style="background:${DIFF_COLORS[level]}">${DIFF_LABELS[level]}</span>`
      : `<span class="diff-badge" style="background:#ccc">데이터 부족</span>`;

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${CAT_LABELS[cat]}</td>
      <td>${s.attempts}</td>
      <td>${acc}</td>
      <td>${avgT}</td>
      <td>${badge}</td>
    `;
    tbody.appendChild(tr);
  }
}

function confirmResetStats() {
  if (confirm('누적 기록을 모두 지울까요?')) resetStats();
}

/* ═══════════════════════════════════
   색종이 이펙트
═══════════════════════════════════ */
function spawnConfetti() {
  const items = ['🎉','✨','🌟','🎊','⭐','🍭','🎈'];
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
   초기화 및 시작
═══════════════════════════════════ */
window.onload = () => {
  initRocketPanel();
  startGame();
};
