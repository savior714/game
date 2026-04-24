/**
 * @fileoverview 과학 과목 엔진 - 문제 출제, 정답 평가, 진행률 관리
 * @module science/engine
 */

/**
 * 과학 문제 데이터
 * @typedef {Array} ScienceQuestion
 * @property {string} 0 - 질문
 * @property {string} 1 - 정답
 * @property {string[]} 2 - 보기 배열
 * @property {number} 3 - 난이도 레벨 (0-6)
 * @property {string} 4 - 태그
 */

/* ═══════════════════════════════════
   과학 데이터베이스 [질문, 정답, [보기], 레벨, 태그]
   카테고리: biology(생물), earth(지구과학), physics(물리/기초과학)
   태그: animal_life, plant_life, human_body, cell, solar_system, weather, earth_material, magnetism, light, electricity, force
   ※ 실제 데이터는 science/data/questions.json에서 동적 로드됨
══════════════════════════════════ */

// DB getter: window.WORDS를 참조 (words-loaded 이벤트 후 사용)
function getDB() {
  return window.WORDS || {};
}

/* ═══════════════════════════════════
   상수 및 상태
══════════════════════════════════ */
const TOTAL              = 10;
const TIME_LIMIT         = 120;
const MIN_DATA           = 3;
const SUBJECT_DIFF_OPTS  = { upThreshold: 0.85, downThreshold: 0.75 };
const LAUNCH_STREAK      = 20;
const STATS_KEY          = ProgressEngine.createStatsKey('science');
const MAX_WRONG_PATTERNS = 5;
const REINFORCE_PROB     = 0.45;
const RECENT_LIMIT       = 10;
const ROCKET_MAX_BOTTOM  = 330;

const DIFF_LABELS = ['입문', '기초', '중급', '숙련', '마스터', '초월', '전설'];
const DIFF_COLORS = ['#aed581', '#66bb6a', '#4fc3f7', '#29b6f6', '#ffca28', '#ab47bc', '#ef5350'];
const DOMAIN_KEYS = ['biology', 'earth', 'physics'];

let currentQ      = 0;
let score         = 0;
let answer        = '';
let answered      = false;
let timerInterval = null;
let timeLeft      = TIME_LIMIT;
let currentCat    = 'biology';

var streak        = 0;
var globalBoost   = 0;
var launching     = false;
var crashing      = false;
var netStreak     = 0;
var hasNet        = false;
const NET_STREAK  = 5;
let wrongPatterns = [];
let currentQData  = null; // { cat, level, tag, isWeakness }
let recentHistory = []; 
let recentQuestions = []; // 최근 10문제 (중복 방지용 키)

/* ═══════════════════════════════════
   통계 (localStorage)
══════════════════════════════════ */
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
══════════════════════════════════ */
function getBaseDiffLevel(cat) {
  return ProgressEngine.getBaseDiffLevel(stats, cat, MIN_DATA, SUBJECT_DIFF_OPTS);
}

function getDifficultyLevel(cat) {
  return ProgressEngine.getDifficultyLevel(stats, cat, MIN_DATA, globalBoost, recentHistory, SUBJECT_DIFF_OPTS);
}

/* ═══════════════════════════════════
   카테고리 선택
══════════════════════════════════ */
function pickCategory() {
  const db = getDB();
  const cats = Object.keys(db);
  const w = {};
  for (const cat of cats) {
    w[cat] = 1.0;
    let totalAttempts = 0, totalCorrect = 0;
    Object.values(stats[cat].levels).forEach(lv => { totalAttempts += lv.attempts; totalCorrect += lv.correct; });
    if (totalAttempts >= MIN_DATA && totalCorrect / totalAttempts < 0.6) w[cat] += 0.5;
  }
  const total = Object.values(w).reduce((a, b) => a + b, 0);
  let r = Math.random() * total;
  for (const [cat, wt] of Object.entries(w)) { r -= wt; if (r <= 0) return cat; }
  return cats[0];
}

/* ═══════════════════════════════════
   문제 생성
══════════════════════════════════ */
function generateQuestion() {
  let q = null;
  let tries = 0;

  while (tries < 20) {
    const candidate = _generateCandidate();
    const key = candidate.data[0]; // 질문 텍스트
    
    // 가용 문제 수에 따른 버퍼 크기 조절
    const db = getDB();
    const pool = db[candidate.cat].filter(item => item[3] === candidate.level);
    const limit = Math.min(RECENT_LIMIT, Math.floor(pool.length / 2));
    
    const slice = recentQuestions.slice(-limit);
    if (!slice.includes(key) || pool.length <= 1) {
      q = candidate;
      break;
    }
    tries++;
  }
  
  if (!q) q = _generateCandidate();
  return q;
}

function _generateCandidate() {
  const db = getDB();
  // 1. 약점 태그 강화 (30% 확률)
  if (Math.random() < 0.3) {
    let worstTag = null, minAcc = 2, tagCat = 'biology';
    ['biology', 'earth', 'physics'].forEach(c => {
      for (const [tag, s] of Object.entries(stats[c].weaknesses)) {
        const acc = s.attempts > 0 ? s.correct / s.attempts : 1;
        if (s.attempts >= 2 && acc < 0.7 && acc < minAcc) {
          minAcc = acc; worstTag = tag; tagCat = c;
        }
      }
    });

    if (worstTag) {
      const pool = db[tagCat].filter(q => q[4] === worstTag);
      if (pool.length > 0) {
        const item = pool[Math.floor(Math.random() * pool.length)];
        return { cat: tagCat, level: item[3], data: item, isWeakness: true };
      }
    }
  }

  // 2. 틀린 패턴
  if (wrongPatterns.length > 0 && Math.random() < REINFORCE_PROB) {
    const p = wrongPatterns[Math.floor(Math.random() * wrongPatterns.length)];
    const pool = db[p.cat].filter(item => item[3] === p.level);
    const q = pool[Math.floor(Math.random() * pool.length)];
    return { cat: p.cat, level: p.level, data: q };
  }

  const cat = pickCategory();
  const level = getDifficultyLevel(cat);
  const pool = db[cat].filter(item => item[3] === level);
  const q = (pool.length > 0) ? pool[Math.floor(Math.random() * pool.length)] : db[cat][0];
  return { cat, level, data: q };
}

function askQuestion() {
  try {
    answered  = false;
    const qObj = generateQuestion();
    const q = qObj.data;
    answer = q[1];
    currentCat = qObj.cat;
    currentQData = { cat: qObj.cat, level: qObj.level, tag: q[4], isWeakness: qObj.isWeakness };

    // 중복 방지 큐에 추가
    recentQuestions.push(q[0]);
    if (recentQuestions.length > RECENT_LIMIT) recentQuestions.shift();

    document.getElementById('question').textContent = q[0];
    document.getElementById('feedback').textContent = qObj.isWeakness ? '🔥 약점 탐구 도전!' : '';
    document.getElementById('feedback').className   = qObj.isWeakness ? 'weakness-highlight' : '';
    document.getElementById('next-btn').style.display = 'none';

    const choices   = [...q[2]].sort(() => Math.random() - 0.5);
    const container = document.getElementById('answer-buttons');
    container.innerHTML = '';
    choices.forEach(val => {
      const btn = document.createElement('button');
      btn.className   = 'answer-btn';
      btn.textContent = val;
      btn.onclick     = () => checkAnswer(val, btn);
      container.appendChild(btn);
    });
    document.getElementById('q-count').textContent = currentQ + 1;
    startTimer();
  } catch (err) {
    if (typeof QuizUICore !== 'undefined' && QuizUICore.handleQuestionError) {
      QuizUICore.handleQuestionError(err);
    } else {
      console.error('[Science] Question error:', err);
    }
  }
}

function recordResult(correct, elapsed) {
  // 공통 결과 기록
  ProgressEngine.recordResultCore({
    stats, domainKey: currentCat, level: currentQData.level,
    tag: currentQData.tag, correct, elapsed,
    weaknessesKey: currentQData.tag,
  });

  // 과목별 고유 로직: 약점 극복 피드백
  const wStats = stats[currentCat].weaknesses[currentQData.tag];
  if (correct && currentQData.isWeakness && wStats.attempts >= 3 && wStats.correct / wStats.attempts >= 0.8) {
    showWeaknessClear();
  }

  saveStats();
  updateStreak(correct);

  // 그물망 시스템
  if (correct) {
    netStreak++;
    if (netStreak >= NET_STREAK && !hasNet) {
      hasNet = true; netStreak = 0; showNetBanner();
    }
  } else {
    netStreak = 0;
  }

  // 틀린 패턴 기록
  if (!correct) {
    wrongPatterns.unshift({ cat: currentCat, level: currentQData.level });
    if (wrongPatterns.length > MAX_WRONG_PATTERNS) wrongPatterns.pop();
  } else {
    const idx = wrongPatterns.findIndex(p => p.cat === currentCat && p.level === currentQData.level);
    if (idx !== -1) wrongPatterns.splice(idx, 1);
  }
  recentHistory.push(correct);
  if (recentHistory.length > 5) recentHistory.shift();
}

function showWeaknessClear() {
  const fb = document.getElementById('feedback');
  fb.textContent = '✨ 과학 약점 타파! 멋진 과학자군요! ✨';
  fb.className = 'weakness-clear-message';
}
