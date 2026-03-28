/* ═══════════════════════════════════
   순차 빈칸 상태
═══════════════════════════════════ */
let seqBlanks = null;  // { word, blankIndices, blanks, ico, hint }
let seqStep   = 0;     // 현재 빈칸 인덱스 (0 or 1)
let seqFilled = [];    // 채워진 글자 배열
const timerCore = QuizUICore.createTimerCore({
  getTimeLimit: () => TIME_LIMIT,
  getTimeLeft: () => timeLeft,
  setTimeLeft: (v) => { timeLeft = v; },
  getTimerInterval: () => timerInterval,
  setTimerInterval: (id) => { timerInterval = id; },
  onTimeout: () => timeOut(),
  useGameCardDanger: true
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
    fb.textContent = ['잘했어요! 🎉', '맞았어요! ⭐', '완벽해요! 🌟', '훌륭해요! 👏'][Math.floor(Math.random()*4)];
    fb.className = 'feedback-correct';
    spawnConfetti();
  },
  onWrong: ({ button, answer: currentAnswer }) => {
    button.classList.add('wrong');
    const fb = document.getElementById('feedback');
    fb.textContent = `정답은 "${currentAnswer}"이에요! 😊`;
    fb.className = 'feedback-wrong';
  },
  showNextButton: () => {
    document.getElementById('next-btn').style.display = 'inline-block';
  }
});
const sequentialAnswerCore = QuizUICore.createSequentialAnswerCore({
  setAnswered: (v) => { answered = v; },
  getTimeLimit: () => TIME_LIMIT,
  getTimeLeft: () => timeLeft,
  stopTimer: () => stopTimer(),
  recordResult: (ok, elapsed) => recordResult(ok, elapsed),
  onSuccess: () => {
    score++;
    document.getElementById('q-score').textContent = score;
    const fb = document.getElementById('feedback');
    fb.textContent = ['잘했어요! 🎉', '맞았어요! ⭐', '완벽해요! 🌟', '훌륭해요! 👏'][Math.floor(Math.random()*4)];
    fb.className = 'feedback-correct';
    spawnConfetti();
    seqBlanks = null;
  },
  onFailure: ({ button }) => {
    button.classList.add('wrong');
    const fb = document.getElementById('feedback');
    fb.textContent = `정답은 "${answer}"이에요! 😊`;
    fb.className = 'feedback-wrong';
    seqBlanks = null;
  },
  showNextButton: () => {
    document.getElementById('next-btn').style.display = 'inline-block';
  }
});

/* ═══════════════════════════════════
   공통 보기 버튼 렌더
═══════════════════════════════════ */
function renderChoiceBtns(choices) {
  const container = document.getElementById('answer-buttons');
  container.innerHTML = '';
  choices.forEach(val => {
    const btn = document.createElement('button');
    btn.className   = 'answer-btn btn-hidden'; // 시작은 숨김 상태
    btn.textContent = val;
    btn.onclick     = () => checkAnswer(val, btn);
    container.appendChild(btn);
    // 렌더링 루프 확보 후 페이드 인
    setTimeout(() => btn.classList.remove('btn-hidden'), 10);
  });
}

/* ═══════════════════════════════════
   순차 빈칸 단어 표시 렌더
═══════════════════════════════════ */
function renderSeqWord() {
  const { word, blankIndices } = seqBlanks;
  let html = '';
  for (let k = 0; k < word.length; k++) {
    const bPos = blankIndices.indexOf(k);
    if (bPos === -1) {
      html += `<span class="sl">${word[k]}</span>`;
    } else if (seqFilled[bPos] != null) {
      html += `<span class="sl sl-filled">${seqFilled[bPos]}</span>`;
    } else if (bPos === seqStep) {
      html += `<span class="sl sl-active">&nbsp;</span>`;
    } else {
      html += `<span class="sl sl-dim">&nbsp;</span>`;
    }
  }
  document.getElementById('seq-word').innerHTML = html;
}

function renderSeqWordComplete() {
  const html = [...seqBlanks.word].map(ch =>
    `<span class="sl sl-filled">${ch}</span>`
  ).join('');
  document.getElementById('seq-word').innerHTML = html;
}

/* ═══════════════════════════════════
   문제 표시
═══════════════════════════════════ */
function askQuestion() {
  answered  = false;
  seqBlanks = null;
  seqStep   = 0;
  seqFilled = [];
  const q   = generateQuestion();
  
  // 상태 동기화 (engine.js에서 전달받은 메타데이터 사용)
  currentCat = q._cat;
  currentWordData = { cat: q._cat, level: q._level, en: q._wordEn, isWeakness: q.isWeakness };
  answer = q.answer;

  document.getElementById('q-count').textContent     = currentQ + 1;
  document.getElementById('feedback').textContent    = q.isWeakness ? '🔥 약점 단어 도전!' : '';
  document.getElementById('feedback').className      = q.isWeakness ? 'weakness-highlight' : '';
  document.getElementById('next-btn').style.display = 'none';

  const qEl = document.getElementById('question');
  const iconHtml = (q.ico.startsWith('./') || q.ico.endsWith('.png'))
    ? `<img src="${q.ico}" class="q-img" alt="question-icon">`
    : `<span class="q-emoji">${q.ico}</span>`;

  if (q.blanks) {
    // 순차 빈칸 모드
    seqBlanks = q;
    qEl.innerHTML =
      iconHtml +
      `<div class="q-hint">${q.hint}</div>` +
      `<div class="q-blanked" id="seq-word"></div>`;
    renderSeqWord();
    renderChoiceBtns(q.blanks[0].choices);
  } else if (q.hint) {
    qEl.innerHTML =
      iconHtml +
      `<div class="q-hint">${q.hint}</div>` +
      `<div class="q-blanked">${q.main}</div>`;
    renderChoiceBtns(q.choices);
  } else {
    qEl.innerHTML =
      iconHtml +
      `<div class="q-main">${q.main}</div>`;
    renderChoiceBtns(q.choices);
  }

  startTimer();
}

/* ═══════════════════════════════════
   결과 기록
═══════════════════════════════════ */

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
  if (seqBlanks) {
    const blank = seqBlanks.blanks[seqStep];
    document.querySelectorAll('.answer-btn').forEach(b => {
      if (b.textContent === blank.char) b.classList.add('correct');
    });
    seqBlanks = null;
  } else {
    document.querySelectorAll('.answer-btn').forEach(b => {
      if (b.textContent === answer) b.classList.add('correct');
    });
  }
  const fb = document.getElementById('feedback');
  fb.textContent = `⏰ 시간 초과! 정답은 "${answer}"이에요!`;
  fb.className   = 'feedback-wrong';
  document.getElementById('next-btn').style.display = 'inline-block';
}

/* ═══════════════════════════════════
   순차 빈칸 정답 확인
═══════════════════════════════════ */
function checkSeqAnswer(val, btn) {
  const blank = seqBlanks.blanks[seqStep];
  if (val === blank.char) {
    btn.classList.add('correct');
    seqFilled[seqStep] = val;
    seqStep++;
    renderSeqWord();
    if (seqStep >= seqBlanks.blanks.length) {
      // 모든 빈칸 완료 — 단어 전체를 초록으로 표시
      renderSeqWordComplete();
      sequentialAnswerCore.finalizeSuccess({ button: btn });
    } else {
      // 다음 빈칸 보기 표시 — 짧은 지연 후 부드럽게 전환
      setTimeout(() => {
        document.querySelectorAll('.answer-btn').forEach(b => b.classList.add('btn-hidden'));
        setTimeout(() => {
          if (seqBlanks) renderChoiceBtns(seqBlanks.blanks[seqStep].choices);
        }, 150);
      }, 100);
    }
  } else {
    // 오답 — 문제 종료
    document.querySelectorAll('.answer-btn').forEach(b => {
      if (b.textContent === blank.char) b.classList.add('correct');
    });
    sequentialAnswerCore.finalizeFailure({ button: btn });
  }
}

/* ═══════════════════════════════════
   정답 확인
═══════════════════════════════════ */
function checkAnswer(val, btn) {
  if (answered) return;
  if (seqBlanks) { checkSeqAnswer(val, btn); return; }
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
function openStats()  { statsModalCore.openStats(); }
function closeStats() { statsModalCore.closeStats(); }
function onModalBackdrop(e) { statsModalCore.onModalBackdrop(e); }

function renderStatsTable() {
  const tbody = document.getElementById('stats-tbody');
  tbody.innerHTML = '';
  for (const [cat, data] of Object.entries(WORDS)) {
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
    tr.innerHTML = `<td>${data.icon} ${data.label}</td><td>${totalAttempts}</td><td>${acc}</td><td>${avgT}</td><td>${badge}</td>`;
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
