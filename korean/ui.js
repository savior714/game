const timerCore = QuizUICore.createTimerCore({
  getTimeLimit: () => TIME_LIMIT,
  getTimeLeft: () => timeLeft,
  setTimeLeft: (v) => { timeLeft = v; },
  getTimerInterval: () => timerInterval,
  setTimerInterval: (id) => { timerInterval = id; },
  onTimeout: () => timeOut(),
  useGameCardDanger: false
});
const statsModalCore = QuizUICore.createStatsModalCore({
  renderStatsTable: () => renderStatsTable()
});
const answerFlowCore = QuizUICore.createAnswerFlowCore({
  getAnswered: () => answered,
  setAnswered: (v) => { answered = v; },
  getTimeLimit: () => TIME_LIMIT,
  getTimeLeft: () => timeLeft,
  stopTimer: () => stopTimer(),
  recordResult: (ok, elapsed) => recordResult(ok, elapsed),
  getAnswer: () => answer,
  markCorrectChoices: () => {
    document.querySelectorAll('.answer-btn').forEach(b => {
      if (b.textContent === answer) b.classList.add('correct');
    });
  },
  onCorrect: () => {
    score++;
    document.getElementById('q-score').textContent = score;
    const fb = document.getElementById('feedback');
    const msgs = ['참 잘했어요! ✨', '정답이에요! 👏', '대단해요! 🌟', '최고예요! 👍'];
    fb.textContent = msgs[Math.floor(Math.random() * msgs.length)];
    fb.className = 'feedback-correct';
    spawnConfetti();
  },
  onWrong: ({ button, answer: currentAnswer }) => {
    button.classList.add('wrong');
    const fb = document.getElementById('feedback');
    fb.textContent = `정답은 "${currentAnswer}"예요! 다시 해봐요 😊`;
    fb.className = 'feedback-wrong';
  },
  showNextButton: () => {
    document.getElementById('next-btn').style.display = 'inline-block';
  }
});

/* ═══════════════════════════════════
   타이머
═══════════════════════════════════ */
function startTimer() {
  timerCore.startTimer();
}

function stopTimer() {
  timerCore.stopTimer();
}

function updateTimerUI() {
  timerCore.updateTimerUI();
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
  answerFlowCore.evaluateStandard(val, btn);
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
  statsModalCore.openStats();
}

function closeStats() {
  statsModalCore.closeStats();
}

function onModalBackdrop(e) {
  statsModalCore.onModalBackdrop(e);
}

function renderStatsTable() {
  const CAT_LABELS = { spelling: '받침/맞춤법', antonym: '반대말', honorific: '높임말' };
  const tbody = document.getElementById('stats-tbody');
  tbody.innerHTML = '';

  for (const cat of ['spelling', 'antonym', 'honorific']) {
    const s = stats[cat];
    let totalAttempts = 0, totalCorrect = 0, totalTime = 0;
    Object.values(s.levels).forEach(lv => {
      totalAttempts += lv.attempts;
      totalCorrect  += lv.correct;
      totalTime     += lv.totalTime;
    });

    const acc     = totalAttempts > 0 ? Math.round(totalCorrect / totalAttempts * 100) + '%' : '-';
    const avgT    = totalAttempts > 0 ? (totalTime / totalAttempts).toFixed(1) + '초' : '-';
    const level   = getBaseDiffLevel(cat);
    const hasData = totalAttempts >= MIN_DATA;
    const badge   = hasData
      ? `<span class="diff-badge" style="background:${DIFF_COLORS[level]}">${DIFF_LABELS[level]}</span>`
      : `<span class="diff-badge" style="background:#ccc">데이터 부족</span>`;

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${CAT_LABELS[cat]}</td>
      <td>${totalAttempts}</td>
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
async function loadWordsData() {
  const res = await fetch('data/words.json');
  if (!res.ok) throw new Error(`words.json HTTP ${res.status}`);
  window.WORDS = await res.json();
  window.dispatchEvent(new Event('words-loaded'));
}

window.onload = async () => {
  try {
    await loadWordsData();
  } catch (e) {
    console.error(e);
    window.WORDS = {};
  }
  initRocketPanel();
  startGame();
};
