/* ═══════════════════════════════════
   상수
═══════════════════════════════════ */
const TOTAL              = 10;
const TIME_LIMIT         = 120;
const MIN_DATA           = 3;    // 난이도 조정 최소 시도 횟수(레벨별 판정용)
/** ProgressEngine 승급 임계값 — 수학만 다소 완화(빠른 승급) */
const MATH_DIFF_OPTS     = { upThreshold: 0.85, downThreshold: 0.75 };
const LAUNCH_STREAK      = 20;   // 연속 정답 → 로켓 발사
const STATS_KEY          = 'mathGameStats';
const MAX_WRONG_PATTERNS = 5;    // 기억할 최대 틀린 패턴 수
const REINFORCE_PROB     = 0.45; // 틀린 패턴 재출제 확률
const RECENT_LIMIT       = 10;    // 최근 출제 문제 기억 수

const DIFF_LABELS = ['입문', '기초', '중급', '숙련', '마스터', '초월', '전설'];
const DIFF_COLORS = ['#aed581', '#66bb6a', '#4fc3f7', '#29b6f6', '#ffca28', '#ab47bc', '#ef5350'];

// 로켓이 이동할 수 있는 최대 bottom 픽셀
const ROCKET_MAX_BOTTOM = 330;
const DOMAIN_KEYS = ['+', '-', '×'];

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
let globalBoost   = 0;
let launching     = false;
let crashing      = false;

// 그물망 시스템
let netStreak     = 0;
let hasNet        = false;
const NET_STREAK  = 5;

// 강화학습: 틀린 패턴 기억
let wrongPatterns = [];
let currentQData  = null; // { op, level, a, b, tag, isWeakness }
let recentHistory = []; // 최근 5문제 정답 여부
let recentQuestions = []; // 최근 10문제 (중복 방지용 키)

/* ═══════════════════════════════════
   통계 (localStorage)
═══════════════════════════════════ */
function emptyStats() {
  return ProgressEngine.emptyStats(DOMAIN_KEYS);
}

let stats = loadStats();

function loadStats() {
  return ProgressEngine.loadStats(STATS_KEY, DOMAIN_KEYS);
}

function saveStats() {
  ProgressEngine.saveStats(STATS_KEY, stats);
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
  return ProgressEngine.getBaseDiffLevel(stats, op, MIN_DATA, MATH_DIFF_OPTS);
}

function getDifficultyLevel(op) {
  return ProgressEngine.getDifficultyLevel(stats, op, MIN_DATA, globalBoost, recentHistory, MATH_DIFF_OPTS);
}

/* ═══════════════════════════════════
   연산 선택
═══════════════════════════════════ */
function pickOperation() {
  let addAtt = 0, subAtt = 0;
  Object.values(stats['+'].levels).forEach(l => addAtt += l.attempts);
  Object.values(stats['-'].levels).forEach(l => subAtt += l.attempts);
  const combined = addAtt + subAtt;
  const w = { '+': 0.45, '-': 0.35, '×': combined >= 8 ? 0.20 : 0 };
  for (const op of ['+', '-', '×']) {
    let opAtt = 0, opCorr = 0;
    Object.values(stats[op].levels).forEach(l => { opAtt += l.attempts; opCorr += l.correct; });
    if (opAtt >= MIN_DATA && opCorr / opAtt < 0.5) w[op] += 0.15;
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
   문제 생성 및 패턴 분석
═══════════════════════════════════ */
function extractPatternTag(a, b, op) {
  if (op === '+') {
    const d1 = a % 10;
    const d2 = b % 10;
    const [min, max] = [Math.min(d1, d2), Math.max(d1, d2)];
    return `add_unit_${min}_${max}`;
  }
  if (op === '-') {
    return `sub_unit_${a % 10}_${b % 10}`;
  }
  return 'basic';
}

function generateByPattern(op, level, tag) {
  let a, b, tries = 0;
  while (tries < 100) {
    const q = generateByOpLevel(op, level);
    if (q.tag === tag) return q;
    tries++;
  }
  return generateByOpLevel(op, level); // 실패 시 일반 생성 위임
}

function generateByOpLevel(op, level) {
  let a, b, result, tag;
  if (op === '+') {
    const maxSums = [10, 20, 40, 60, 100, 150, 200];
    const maxAs   = [5, 10, 20, 35, 70, 100, 150];
    const maxBs   = [5, 10, 15, 20, 40, 60, 80];
    a = Math.floor(Math.random() * maxAs[level]) + 1;
    b = Math.floor(Math.random() * Math.min(maxSums[level] - a, maxBs[level])) + 1;
    result = a + b;
    tag = extractPatternTag(a, b, op);
  } else if (op === '-') {
    const minAs = [3, 7, 15, 30, 60, 100, 150];
    const maxAs = [8, 20, 40, 80, 120, 160, 200];
    a = Math.floor(Math.random() * (maxAs[level] - minAs[level] + 1)) + minAs[level];
    b = Math.floor(Math.random() * (a - 1)) + 1;
    result = a - b;
    tag = extractPatternTag(a, b, op);
  } else {
    const baseSets = [[2,5,10], [2,3,5,10], [2,3,4,5,6,7,8,9], [11,12,13,14,15], [16,17,18,19], [21,23,25,30], [31,37,43,47]];
    const bases = baseSets[level];
    a  = bases[Math.floor(Math.random() * bases.length)];
    const mult = level >= 3 ? Math.floor(Math.random() * 18) + 2 : Math.floor(Math.random() * 9) + 2;
    b = mult;
    result = a * b;
    tag = level >= 3 ? 'mult_complex' : 'mult_table';
  }
  return { a, b, op, result, tag };
}

function generateQuestion() {
  let q = null;
  let tries = 0;

  while (tries < 20) {
    const candidate = _generateCandidate();
    const key = [candidate.a, candidate.b].sort((a, b) => a - b).join(',') + candidate.op;
    
    // 만약 전체 가용 문제 수가 너무 적으면 (예: 10개 미만), RECENT_LIMIT을 유동적으로 조절
    // 하지만 수학은 보통 조합이 많으므로 10개를 유지해도 무방함. 단, 아주 낮은 레벨은 예외.
    if (!recentQuestions.includes(key)) {
      q = candidate;
      break;
    }
    tries++;
  }
  
  // 20회 시도 후에도 못 찾으면 그냥 마지막 후보 사용
  if (!q) q = _generateCandidate();
  
  return q;
}

function _generateCandidate() {
  // 1. 상세 패턴 약점 자가 치유 (30% 확률)
  if (Math.random() < 0.3) {
    let worstTag = null, minAcc = 2, tagOp = '+';
    ['+', '-'].forEach(op => {
      for (const [tag, s] of Object.entries(stats[op].weaknesses)) {
        // 상세 패턴(add_unit 등)에 대해서만 우선 처리
        if (!tag.includes('_unit_')) continue;
        const acc = s.attempts > 0 ? s.correct / s.attempts : 1;
        if (s.attempts >= 2 && acc < 0.75 && acc < minAcc) {
          minAcc = acc; worstTag = tag; tagOp = op;
        }
      }
    });

    if (worstTag) {
      const level = getDifficultyLevel(tagOp);
      const q = generateByPattern(tagOp, level, worstTag);
      return { ...q, isWeakness: true, level };
    }
  }

  // 2. 기존 틀린 패턴
  if (wrongPatterns.length > 0 && Math.random() < REINFORCE_PROB) {
    const p = wrongPatterns[Math.floor(Math.random() * wrongPatterns.length)];
    return { ...generateByOpLevel(p.op, p.level), level: p.level };
  }

  // 3. 일반 출제
  const op = pickOperation();
  const level = getDifficultyLevel(op);
  return { ...generateByOpLevel(op, level), level };
}

/* ═══════════════════════════════════
   보기 생성 및 표시
═══════════════════════════════════ */
function makeChoices(correct, op, level) {
  const spread = op === '×' ? 18 + level * 10 : [5, 8, 13, 20, 30, 40, 50][level];
  const set = new Set([correct]);
  let tries = 0;
  while (set.size < 4 && tries < 300) {
    tries++;
    const v = correct + Math.floor(Math.random() * (spread * 2 + 1)) - spread;
    if (v !== correct && v >= 0) set.add(v);
  }
  let fb = 1;
  while (set.size < 4) { if (fb !== correct) set.add(fb); fb++; }
  return [...set].sort(() => Math.random() - 0.5);
}

function askQuestion() {
  answered  = false;
  const q   = generateQuestion();
  answer    = q.result;
  currentOp = q.op;
  currentQData = { op: q.op, level: q.level, a: q.a, b: q.b, tag: q.tag, isWeakness: q.isWeakness };

  // 중복 방지 큐에 추가
  const qKey = [q.a, q.b].sort((a, b) => a - b).join(',') + q.op;
  recentQuestions.push(qKey);
  if (recentQuestions.length > RECENT_LIMIT) recentQuestions.shift();

  document.getElementById('question').textContent = `${q.a}  ${q.op}  ${q.b}  =  ?`;
  document.getElementById('feedback').textContent = q.isWeakness ? '🔥 약점 연산 도전!' : '';
  document.getElementById('feedback').className   = q.isWeakness ? 'weakness-highlight' : '';
  document.getElementById('next-btn').style.display = 'none';

  const choices   = makeChoices(q.result, q.op, q.level);
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
  const lvStats = stats[currentOp].levels[currentQData.level];
  lvStats.attempts++;
  if (correct) lvStats.correct++;
  lvStats.totalTime += elapsed;

  // 태그별 약점 통계
  if (!stats[currentOp].weaknesses[currentQData.tag]) {
    stats[currentOp].weaknesses[currentQData.tag] = { attempts: 0, correct: 0 };
  }
  const wStats = stats[currentOp].weaknesses[currentQData.tag];
  wStats.attempts++;
  if (correct) wStats.correct++;

  if (correct && currentQData.isWeakness && wStats.attempts >= 3 && wStats.correct / wStats.attempts >= 0.8) {
    showWeaknessClear();
  }

  saveStats();
  updateStreak(correct);

  if (correct) {
    netStreak++;
    if (netStreak >= NET_STREAK && !hasNet) {
      hasNet = true; netStreak = 0; showNetBanner();
    }
  } else {
    netStreak = 0;
  }

  if (!correct) {
    wrongPatterns.unshift({ op: currentOp, level: currentQData.level, a: currentQData.a, b: currentQData.b });
    if (wrongPatterns.length > MAX_WRONG_PATTERNS) wrongPatterns.pop();
  } else {
    const idx = wrongPatterns.findIndex(p => p.op === currentOp && p.a === currentQData.a && p.b === currentQData.b);
    if (idx !== -1) wrongPatterns.splice(idx, 1);
  }
  recentHistory.push(correct);
  if (recentHistory.length > 5) recentHistory.shift();
}

function showWeaknessClear() {
  const fb = document.getElementById('feedback');
  fb.textContent = '✨ 약점 연산 정복! 정말 똑똑해요! ✨';
  fb.className = 'weakness-clear-message';
}
