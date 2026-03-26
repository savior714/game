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
    fb.textContent = ['참 잘했어요! 🔬', '정답이에요! ✨', '대단해요! 🌟', '과학 박사님! 👏'][Math.floor(Math.random()*4)];
    fb.className = 'feedback-correct';
    spawnConfetti();
  },
  onWrong: ({ button, answer: currentAnswer }) => {
    button.classList.add('wrong');
    const fb = document.getElementById('feedback');
    fb.textContent = `정답은 "${currentAnswer}"이에요! 다시 해봐요 😊`;
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
  document.querySelectorAll('.answer-btn').forEach(b => {
    if (b.textContent === answer) b.classList.add('correct');
  });
  const fb = document.getElementById('feedback');
  fb.textContent = `⏳ 시간 초과! 정답은 "${answer}" 정답이에요!`;
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
  if (pct === 1)       { stars='⭐⭐⭐'; title='완벽해요!';        msg=`10문제 모두 맞췄어요! 미래의 과학자네요! 🎊`; }
  else if (pct >= 0.7) { stars='⭐⭐';  title='잘했어요!';        msg=`10문제 중 ${score}개 맞췄어요! 정말 훌륭해요! 😄`; }
  else                 { stars='⭐';    title='조금 더 연습해요!'; msg=`10문제 중 ${score}개 맞췄어요. 다음에 더 잘할 수 있어요! 💪`; }
  document.getElementById('stars').textContent        = stars;
  document.getElementById('result-title').textContent = title;
  document.getElementById('result-msg').textContent   = msg;
}

function startGame() {
  stopTimer();
  currentQ = 0; score = 0;
  stats    = loadStats();
  document.getElementById('q-score').textContent         = 0;
  document.getElementById('result-screen').style.display = 'none';
  document.getElementById('game-area').style.display     = 'block';
  askQuestion();
}

/* ═══════════════════════════════════
   통계 모달
═══════════════════════════════════ */
function openStats()  { statsModalCore.openStats(); }
function closeStats() { statsModalCore.closeStats(); }
function onModalBackdrop(e) { statsModalCore.onModalBackdrop(e); }

function renderStatsTable() {
  const CAT_LABELS = { biology: '생물', earth: '지구과학', physics: '물리/기초' };
  const tbody = document.getElementById('stats-tbody');
  tbody.innerHTML = '';
  for (const cat of ['biology', 'earth', 'physics']) {
    const s = stats[cat];
    let totalAttempts = 0, totalCorrect = 0, totalTime = 0;
    Object.values(s.levels).forEach(lv => {
      totalAttempts += lv.attempts;
      totalCorrect  += lv.correct;
      totalTime     += lv.totalTime;
    });

    const acc     = totalAttempts > 0 ? Math.round(totalCorrect / totalAttempts * 100) + '%' : '-';
    const avgT    = totalAttempts > 0 ? (totalTime / totalAttempts).toFixed(1) + '초' : '-';
    const hasData = totalAttempts >= MIN_DATA;
    const level   = getBaseDiffLevel(cat);
    const badge   = hasData
      ? `<span class="diff-badge" style="background:${DIFF_COLORS[level]}">${DIFF_LABELS[level]}</span>`
      : `<span class="diff-badge" style="background:#ccc">데이터 부족</span>`;
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${CAT_LABELS[cat]}</td><td>${totalAttempts}</td><td>${acc}</td><td>${avgT}</td><td>${badge}</td>`;
    tbody.appendChild(tr);
  }
}

function confirmResetStats() { if (confirm('누적 기록을 모두 지울까요?')) resetStats(); }

/* ═══════════════════════════════════
   색종이
═══════════════════════════════════ */
function spawnConfetti() {
  const items=['🧪','🧬','🔬','🌍','🌟','✨'];
  for (let i=0;i<8;i++) setTimeout(()=>{
    const el=document.createElement('div');
    el.className='confetti-emoji';
    el.textContent=items[Math.floor(Math.random()*items.length)];
    el.style.left=Math.random()*100+'vw'; el.style.top='-40px';
    el.style.animationDuration=(1+Math.random())+'s';
    document.body.appendChild(el); setTimeout(()=>el.remove(),2500);
  }, i*100);
}

window.onload = () => {
  initRocketPanel();
  startGame();
};
