/* ═══════════════════════════════════
   문제 표시
═══════════════════════════════════ */
function askQuestion() {
  answered = false;
  const q  = generateQuestion();
  answer   = q.answer;

  document.getElementById('q-count').textContent       = currentQ + 1;
  document.getElementById('feedback').textContent      = '';
  document.getElementById('feedback').className        = '';
  document.getElementById('next-btn').style.display   = 'none';

  const qEl = document.getElementById('question');
  if (q.hint) {
    qEl.innerHTML =
      `<span class="q-emoji">${q.ico}</span>` +
      `<div class="q-hint">${q.hint}</div>` +
      `<div class="q-blanked">${q.main}</div>`;
  } else {
    qEl.innerHTML =
      `<span class="q-emoji">${q.ico}</span>` +
      `<div class="q-main">${q.main}</div>`;
  }

  const container = document.getElementById('answer-buttons');
  container.innerHTML = '';
  q.choices.forEach(val => {
    const btn = document.createElement('button');
    btn.className   = 'answer-btn';
    btn.textContent = val;
    btn.onclick     = () => checkAnswer(val, btn);
    container.appendChild(btn);
  });

  startTimer();
}

/* ═══════════════════════════════════
   결과 기록
═══════════════════════════════════ */
function recordResult(correct, elapsed) {
  stats[currentCat].attempts++;
  if (correct) stats[currentCat].correct++;
  stats[currentCat].totalTime += elapsed;
  saveStats();
  updateStreak(correct);
  if (!correct && currentWordData) addWrongPattern(currentWordData);
  else if (correct && currentWordData) removeWrongPattern(currentWordData);
}

/* ═══════════════════════════════════
   타이머
═══════════════════════════════════ */
function startTimer() {
  stopTimer();
  timeLeft = TIME_LIMIT;
  updateTimerUI();
  timerInterval = setInterval(() => {
    timeLeft -= 0.25;
    if (timeLeft <= 0) { timeLeft = 0; updateTimerUI(); stopTimer(); timeOut(); }
    else updateTimerUI();
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
  document.querySelectorAll('.answer-btn').forEach(b => {
    if (b.textContent === answer) b.classList.add('correct');
  });
  const fb = document.getElementById('feedback');
  fb.textContent = `⏰ 시간 초과! 정답은 "${answer}"이에요!`;
  fb.className   = 'feedback-wrong';
  document.getElementById('next-btn').style.display = 'inline-block';
}

/* ═══════════════════════════════════
   정답 확인
═══════════════════════════════════ */
function checkAnswer(val, btn) {
  if (answered) return;
  answered       = true;
  const elapsed  = TIME_LIMIT - timeLeft;
  stopTimer();

  document.querySelectorAll('.answer-btn').forEach(b => {
    if (b.textContent === answer) b.classList.add('correct');
  });

  const fb = document.getElementById('feedback');
  if (val === answer) {
    recordResult(true, elapsed);
    score++;
    document.getElementById('q-score').textContent = score;
    fb.textContent = ['잘했어요! 🎉', '맞았어요! ⭐', '완벽해요! 🌟', '훌륭해요! 👏'][Math.floor(Math.random()*4)];
    fb.className   = 'feedback-correct';
    spawnConfetti();
  } else {
    recordResult(false, elapsed);
    btn.classList.add('wrong');
    fb.textContent = `정답은 "${answer}"이에요! 😊`;
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
  if (pct === 1)       { stars='⭐⭐⭐'; title='완벽해요!';        msg=`10문제 모두 맞췄어요! 영어 천재! 🎊`; }
  else if (pct >= 0.7) { stars='⭐⭐';  title='잘했어요!';        msg=`10문제 중 ${score}개 맞췄어요! 최고예요! 😄`; }
  else                 { stars='⭐';    title='조금 더 연습해요!'; msg=`10문제 중 ${score}개 맞췄어요. 같이 다시 해봐요! 💪`; }
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
function openStats()  { renderStatsTable(); document.getElementById('stats-modal').style.display='flex'; }
function closeStats() { document.getElementById('stats-modal').style.display='none'; }
function onModalBackdrop(e) { if (e.target===document.getElementById('stats-modal')) closeStats(); }

function renderStatsTable() {
  const tbody = document.getElementById('stats-tbody');
  tbody.innerHTML = '';
  for (const [cat, data] of Object.entries(WORDS)) {
    const s      = stats[cat];
    const acc    = s.attempts > 0 ? Math.round(s.correct/s.attempts*100)+'%' : '-';
    const avgT   = s.attempts > 0 ? (s.totalTime/s.attempts).toFixed(1)+'초' : '-';
    const hasData = s.attempts >= MIN_DATA;
    const level   = hasData ? getBaseDiffLevel(cat) : -1;
    const badge   = hasData
      ? `<span class="diff-badge" style="background:${DIFF_COLORS[level]}">${DIFF_LABELS[level]}</span>`
      : `<span class="diff-badge" style="background:#ccc">데이터 부족</span>`;
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${data.icon} ${data.label}</td><td>${s.attempts}</td><td>${acc}</td><td>${avgT}</td><td>${badge}</td>`;
    tbody.appendChild(tr);
  }
}

function confirmResetStats() { if (confirm('누적 기록을 모두 지울까요?')) resetStats(); }

/* ═══════════════════════════════════
   색종이
═══════════════════════════════════ */
function spawnConfetti() {
  const items=['🎉','🌟','✨','🎊','⭐','🍬','🎈'];
  for (let i=0;i<8;i++) setTimeout(()=>{
    const el=document.createElement('div');
    el.className='confetti-emoji';
    el.textContent=items[Math.floor(Math.random()*items.length)];
    el.style.left=Math.random()*100+'vw'; el.style.top='-40px';
    el.style.animationDuration=(1+Math.random())+'s';
    document.body.appendChild(el); setTimeout(()=>el.remove(),2500);
  }, i*100);
}

/* ═══════════════════════════════════
   시작
═══════════════════════════════════ */
initRocketPanel();
startGame();
