/* ═══════════════════════════════════
   상수
═══════════════════════════════════ */
const TOTAL              = 10;
const TIME_LIMIT         = 20;
const MIN_DATA           = 4;    // 난이도 조정 최소 시도 횟수
const LAUNCH_STREAK      = 20;   // 연속 정답 → 로켓 발사
const STATS_KEY          = 'mathGameStats';
const MAX_WRONG_PATTERNS = 5;    // 기억할 최대 틀린 패턴 수
const REINFORCE_PROB     = 0.45; // 틀린 패턴 재출제 확률

const DIFF_LABELS = ['쉬움', '보통', '어려움'];
const DIFF_COLORS = ['#66bb6a', '#ffa726', '#ef5350'];

// 로켓이 이동할 수 있는 최대 bottom 픽셀 (트랙 높이 380 - 로켓 크기 ~40 - 여백)
const ROCKET_MAX_BOTTOM = 330;

/* ═══════════════════════════════════
   게임 상태
═══════════════════════════════════ */
let currentQ      = 0;
let score         = 0;
let answer        = 0;
let answered      = false;
let timerInterval = null;
let timeLeft      = TIME_LIMIT;
let currentOp     = '+';

// 적응형 난이도
let streak        = 0;
let globalBoost   = 0;   // 로켓 발사 횟수 (전체 난이도 가산, 최대 2)
let launching     = false;
let crashing      = false;

// 강화학습: 틀린 패턴 기억
let wrongPatterns = [];  // [{ op, level, a, b }, ...]
let currentQData  = null;

/* ═══════════════════════════════════
   통계 (localStorage)
═══════════════════════════════════ */
function emptyStats() {
  return {
    '+': { attempts: 0, correct: 0, totalTime: 0 },
    '-': { attempts: 0, correct: 0, totalTime: 0 },
    '×': { attempts: 0, correct: 0, totalTime: 0 },
  };
}

let stats = loadStats();

function loadStats() {
  try {
    const raw = localStorage.getItem(STATS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      const base = emptyStats();
      for (const op of ['+', '-', '×']) {
        if (parsed[op]) Object.assign(base[op], parsed[op]);
      }
      return base;
    }
  } catch(e) {}
  return emptyStats();
}

function saveStats() {
  localStorage.setItem(STATS_KEY, JSON.stringify(stats));
}

function resetStats() {
  stats = emptyStats();
  saveStats();
  renderStatsTable();
}

/* ═══════════════════════════════════
   난이도 계산
═══════════════════════════════════ */
function getBaseDiffLevel(op) {
  const s = stats[op];
  if (s.attempts < MIN_DATA) return 0;
  const accuracy = s.correct / s.attempts;
  const avgTime  = s.totalTime / s.attempts;
  if (accuracy >= 0.75 && avgTime <= 7)  return 2;
  if (accuracy >= 0.55 && avgTime <= 11) return 1;
  return 0;
}

function getDifficultyLevel(op) {
  return Math.min(2, getBaseDiffLevel(op) + globalBoost);
}

/* ═══════════════════════════════════
   연산 선택 (약한 연산 가중치 ↑)
═══════════════════════════════════ */
function pickOperation() {
  const combined = stats['+'].attempts + stats['-'].attempts;
  const w = { '+': 0.45, '-': 0.35, '×': combined >= 8 ? 0.20 : 0 };

  for (const op of ['+', '-', '×']) {
    if (stats[op].attempts >= MIN_DATA) {
      const acc = stats[op].correct / stats[op].attempts;
      if (acc < 0.5) w[op] += 0.15;
    }
  }

  const total = Object.values(w).reduce((a, b) => a + b, 0);
  let r = Math.random() * total;
  for (const [op, wt] of Object.entries(w)) {
    r -= wt;
    if (r <= 0) return op;
  }
  return '+';
}

/* ═══════════════════════════════════
   문제 생성
═══════════════════════════════════ */
function generateByOpLevel(op, level) {
  if (op === '+') {
    const maxSums = [20, 35, 60];
    const maxAs   = [10, 20, 40];
    const maxBs   = [10, 15, 20];
    const a = Math.floor(Math.random() * maxAs[level]) + 1;
    const b = Math.floor(Math.random() * Math.min(maxSums[level] - a, maxBs[level])) + 1;
    return { a, b, op: '+', result: a + b };

  } else if (op === '-') {
    const minAs = [5, 10, 20];
    const maxAs = [15, 30, 50];
    const a = Math.floor(Math.random() * (maxAs[level] - minAs[level] + 1)) + minAs[level];
    const b = Math.floor(Math.random() * (a - 1)) + 1;
    return { a, b, op: '-', result: a - b };

  } else {
    const baseSets = [
      [2, 5],
      [2, 3, 5],
      [2, 3, 4, 5, 6, 7, 8, 9],
    ];
    const bases = baseSets[level];
    const base  = bases[Math.floor(Math.random() * bases.length)];
    const mult  = Math.floor(Math.random() * 9) + 2;
    return { a: base, b: mult, op: '×', result: base * mult };
  }
}

/* ═══════════════════════════════════
   강화학습: 틀린 패턴 기반 재출제
═══════════════════════════════════ */
function addWrongPattern(data) {
  wrongPatterns.unshift(data);
  if (wrongPatterns.length > MAX_WRONG_PATTERNS) wrongPatterns.pop();
}

function removeWrongPattern(op, a, b) {
  const idx = wrongPatterns.findIndex(p => p.op === op && p.a === a && p.b === b);
  if (idx !== -1) wrongPatterns.splice(idx, 1);
}

function generateSimilar({ op, level, a, b }) {
  const rnd = (n, lo, hi) => Math.max(lo, Math.min(hi, n + Math.floor(Math.random() * 7) - 3));

  if (op === '+') {
    const maxSums = [20, 35, 60];
    const maxAs   = [10, 20, 40];
    const maxBs   = [10, 15, 20];
    const newA = rnd(a, 1, maxAs[level]);
    const newB = rnd(b, 1, Math.min(maxSums[level] - newA, maxBs[level]));
    return { a: newA, b: newB, op: '+', result: newA + newB };

  } else if (op === '-') {
    const minAs = [5, 10, 20];
    const maxAs = [15, 30, 50];
    const newA  = rnd(a, minAs[level], maxAs[level]);
    const newB  = rnd(b, 1, newA - 1);
    return { a: newA, b: newB, op: '-', result: newA - newB };

  } else {
    const mult = Math.floor(Math.random() * 9) + 2;
    return { a, b: mult, op: '×', result: a * mult };
  }
}

function generateQuestion() {
  if (wrongPatterns.length > 0 && Math.random() < REINFORCE_PROB) {
    const pattern = wrongPatterns[Math.floor(Math.random() * wrongPatterns.length)];
    return generateSimilar(pattern);
  }
  const op    = pickOperation();
  const level = getDifficultyLevel(op);
  return generateByOpLevel(op, level);
}

/* ═══════════════════════════════════
   보기 생성 (정답 근처 plausible 오답)
═══════════════════════════════════ */
function makeChoices(correct, op, level) {
  const spread = op === '×' ? 18 : [8, 13, 20][level];
  const set = new Set([correct]);
  let tries = 0;
  while (set.size < 8 && tries < 300) {
    tries++;
    const v = correct + Math.floor(Math.random() * (spread * 2 + 1)) - spread;
    if (v !== correct && v >= 0) set.add(v);
  }
  let fb = 1;
  while (set.size < 8) { if (fb !== correct) set.add(fb); fb++; }
  return [...set].sort(() => Math.random() - 0.5);
}

/* ═══════════════════════════════════
   문제 표시
═══════════════════════════════════ */
function askQuestion() {
  answered  = false;
  const q   = generateQuestion();
  answer    = q.result;
  currentOp = q.op;
  const level = getDifficultyLevel(q.op);
  currentQData = { op: q.op, level, a: q.a, b: q.b };

  document.getElementById('question').textContent = `${q.a}  ${q.op}  ${q.b}  =  ?`;
  document.getElementById('feedback').textContent = '';
  document.getElementById('feedback').className   = '';
  document.getElementById('next-btn').style.display = 'none';

  const choices   = makeChoices(q.result, q.op, level);
  const container = document.getElementById('answer-buttons');
  container.innerHTML = '';
  choices.forEach(val => {
    const btn = document.createElement('button');
    btn.className   = 'answer-btn';
    btn.textContent = val;
    btn.onclick = () => checkAnswer(val, btn);
    container.appendChild(btn);
  });

  document.getElementById('q-count').textContent = currentQ + 1;
  startTimer();
}

/* ═══════════════════════════════════
   결과 기록
═══════════════════════════════════ */
function recordResult(correct, elapsed) {
  stats[currentOp].attempts++;
  if (correct) stats[currentOp].correct++;
  stats[currentOp].totalTime += elapsed;
  saveStats();
  updateStreak(correct);

  if (!correct && currentQData) {
    addWrongPattern(currentQData);
  } else if (correct && currentQData) {
    removeWrongPattern(currentQData.op, currentQData.a, currentQData.b);
  }
}
