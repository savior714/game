/* ═══════════════════════════════════
   단어 데이터베이스  [en, ko, emoji, level]
   level: 0=쉬움(3~5자), 1=보통(5~7자), 2=어려움(7자+)
═══════════════════════════════════ */
// WORDS 데이터는 words.js에서 로드됩니다.


// 단어 필드 접근자
const wEn  = w => w[0];
const wKo  = w => w[1];
const wIco = w => w[2];
const wLv  = w => w[3];

/* ═══════════════════════════════════
   상수
═══════════════════════════════════ */
const TOTAL              = 10;
const TIME_LIMIT         = 120;
const MIN_DATA           = 3;
const SUBJECT_DIFF_OPTS  = { upThreshold: 0.85, downThreshold: 0.75 };
const LAUNCH_STREAK      = 20;
const STATS_KEY          = 'englishGameStats';
const MAX_WRONG_PATTERNS = 5;
const REINFORCE_PROB     = 0.45;
const RECENT_LIMIT       = 10;
const ROCKET_MAX_BOTTOM  = 330;
const DIFF_LABELS        = ['입문', '기초', '중급', '숙련', '마스터', '초월', '전설'];
const DIFF_COLORS        = ['#aed581', '#66bb6a', '#4fc3f7', '#29b6f6', '#ffca28', '#ab47bc', '#ef5350'];
const DOMAIN_KEYS        = Object.keys(WORDS);

/* ═══════════════════════════════════
   게임 상태
═══════════════════════════════════ */
let currentQ       = 0;
let score          = 0;
let answer         = '';
let answered       = false;
let timerInterval  = null;
let timeLeft       = TIME_LIMIT;
let currentCat     = 'animals';
let currentWordData = null; // { cat, level, en, isWeakness }
var streak         = 0;
var globalBoost    = 0;
var launching      = false;
var crashing       = false;
var netStreak      = 0;
var hasNet         = false;
const NET_STREAK   = 5;
let wrongPatterns  = [];
let recentHistory  = []; // 최근 5문제 정답 여부
let recentQuestions = []; // 최근 10단어 (중복 방지용 키)
let weeklyWords = []; // 보호자가 등록한 주간 시험 단어
let weeklyTypeHistory = {}; // 단어별 출제 유형 기록 {'apple': 'spelling'}

function loadWeeklyWords() {
  const saved = localStorage.getItem('englishWeeklyWords');
  weeklyWords = saved ? JSON.parse(saved) : [];
}
loadWeeklyWords();

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

function saveStats()  { ProgressEngine.saveStats(STATS_KEY, stats); }
function resetStats() { stats = emptyStats(); saveStats(); renderStatsTable(); }

/* ═══════════════════════════════════
   난이도 계산
═══════════════════════════════════ */
function getBaseDiffLevel(cat) {
  return ProgressEngine.getBaseDiffLevel(stats, cat, MIN_DATA, SUBJECT_DIFF_OPTS);
}

function getDifficultyLevel(cat) {
  return ProgressEngine.getDifficultyLevel(stats, cat, MIN_DATA, globalBoost, recentHistory, SUBJECT_DIFF_OPTS);
}

/* ═══════════════════════════════════
   카테고리 선택
═══════════════════════════════════ */
function pickCategory() {
  const cats = Object.keys(WORDS);
  const w    = {};
  for (const cat of cats) {
    w[cat] = 1.0;
    let totalAttempts = 0, totalCorrect = 0;
    Object.values(stats[cat].levels).forEach(lv => {
      totalAttempts += lv.attempts;
      totalCorrect  += lv.correct;
    });
    if (totalAttempts >= MIN_DATA && totalCorrect / totalAttempts < 0.6) w[cat] += 0.5;
  }
  const total = Object.values(w).reduce((a, b) => a + b, 0);
  let r = Math.random() * total;
  for (const [cat, wt] of Object.entries(w)) { r -= wt; if (r <= 0) return cat; }
  return cats[0];
}

/* ═══════════════════════════════════
   문제 생성 및 유형
═══════════════════════════════════ */
const Q_TYPE_ORDER = ['kor2word', 'spelling', 'minimal_pair', 'sentence', 'typing'];

function pickQuestionType(level) {
  const rows = {
    0: [0.55, 0.45, 0, 0, 0],
    1: [0.40, 0.33, 0.12, 0.08, 0.07],
    2: [0.30, 0.26, 0.15, 0.15, 0.14],
    3: [0.22, 0.20, 0.18, 0.20, 0.20],
    4: [0.14, 0.16, 0.22, 0.24, 0.24],
    5: [0.08, 0.12, 0.24, 0.28, 0.28],
    6: [0, 0.10, 0.28, 0.31, 0.31],
  };
  const weights = rows[level] || rows[3];
  let r = Math.random();
  for (let i = 0; i < Q_TYPE_ORDER.length; i++) {
    r -= weights[i];
    if (r <= 0) return Q_TYPE_ORDER[i];
  }
  return 'kor2word';
}

function buildQuestion(type, word, meta) {
  const cat = (meta && meta.cat) || 'animals';
  const en  = wEn(word);
  const ko  = wKo(word);
  const ico = wIco(word);
  if (type === 'minimal_pair') {
    const choices = EnglishAdvancedQuestions.makeMinimalPairChoices(word, WORDS, wEn, () => makeWordChoices(word, 'en'));
    return {
      type, ico, main: ko, hint: '비슷한 철자에 주목하세요!',
      answer: en, choices, word: en,
    };
  }
  if (type === 'sentence') {
    const sq = EnglishAdvancedQuestions.buildSentenceQuestion(word, cat, wEn, wKo, wIco);
    return {
      type,
      ...sq,
      answer: en,
      choices: makeWordChoices(word, 'en'),
      word: en,
    };
  }
  if (type === 'typing') {
    return { type, ico, main: ko, sub: '영어 철자를 직접 입력하세요.', answer: en, word: en };
  }
  if (type === 'spelling') {
    const numBlanks = en.length >= 5 && Math.random() < 0.5 ? 2 : 1;
    const validIndices = [];
    for (let k = 0; k < en.length; k++) {
      if (en[k] !== ' ') validIndices.push(k);
    }

    const blankIndices = [];
    const targetCount = Math.min(numBlanks, validIndices.length);
    while (blankIndices.length < targetCount) {
      const candidate = validIndices[Math.floor(Math.random() * validIndices.length)];
      if (!blankIndices.includes(candidate)) blankIndices.push(candidate);
    }
    blankIndices.sort((a, b) => a - b);
    
    const blanks = blankIndices.map(idx => {
      const char = en[idx].toLowerCase();
      return { char, choices: makeSpellingChoices(char) };
    });
    
    const correct = blanks.map(b => b.char).join('');
    
    return { 
      type, ico, hint: ko, answer: correct, word: en, 
      blankIndices, blanks 
    };
  }
  return { type, ico, main: ko, hint: null, answer: en, choices: makeWordChoices(word, 'en') };
}

function generateQuestion() {
  let q = null;
  let tries = 0;

  while (tries < 20) {
    const candidate = _generateCandidate();
    const wordKey = candidate._wordEn; // 단어 자체가 키
    
    // 가용 단어 수에 따른 버퍼 크기 조절
    const catWords = WORDS[candidate._cat].words.filter(w => wLv(w) === candidate._level);
    const limit = Math.min(RECENT_LIMIT, Math.floor(catWords.length / 2));
    
    // 주간 단어면 바로 통과 (최근 단어 체크를 단어 수에 맞춰 완화)
    if (candidate.isWeekly) {
      const weeklyLimit = Math.max(1, Math.min(RECENT_LIMIT, Math.floor(weeklyWords.length / 2)));
      if (!recentQuestions.slice(-weeklyLimit).includes(wordKey) || weeklyWords.length <= 1) {
        q = candidate; break;
      }
    } else {
      const slice = recentQuestions.slice(-limit);
      if (!slice.includes(wordKey) || catWords.length <= 1) {
        q = candidate;
        break;
      }
    }
    tries++;
  }

  if (!q) q = _generateCandidate();
  
  // 중복 방지 큐에 추가
  recentQuestions.push(q._wordEn);
  if (recentQuestions.length > RECENT_LIMIT) recentQuestions.shift();

  return q;
}

function _generateCandidate() {
  // 0. 주간 시험 단어 우선 출제 (60% 확률)
  if (weeklyWords.length > 0 && Math.random() < 0.6) {
    loadWeeklyWords(); // 실시간 데이터 반영 (나갔다 들어올 때 등)
    // 오답 기록이 있는 주간 단어 우선 순위 부여
    const wrongWeekly = wrongPatterns.find(p => p.isWeekly && weeklyWords.some(w => w.en === p.en));
    const w = wrongWeekly 
      ? weeklyWords.find(ww => ww.en === wrongWeekly.en)
      : weeklyWords[Math.floor(Math.random() * weeklyWords.length)];
    
    const diff = getDifficultyLevel(currentCat);
    const wordData = [w.en, w.ko, w.icon || "", diff];
    
    // 유형 순환 (주간 단어는 유형 다각도 노출)
    let type = pickQuestionType(diff);
    if (weeklyTypeHistory[w.en] !== undefined) {
      const idx = Q_TYPE_ORDER.indexOf(weeklyTypeHistory[w.en]);
      const next = Q_TYPE_ORDER[(idx + 1 + Q_TYPE_ORDER.length) % Q_TYPE_ORDER.length];
      type = next;
    }
    weeklyTypeHistory[w.en] = type;

    const res = buildQuestion(type, wordData, { cat: currentCat });
    return { ...res, _cat: currentCat, _level: diff, _wordEn: w.en, isWeekly: true };
  }

  // 1. 약점 단어 강화 (30% 확률)
  if (Math.random() < 0.3) {
    let worstCat = null, minAcc = 2;
    for (const cat of Object.keys(WORDS)) {
      const s = stats[cat].weaknesses['overall'] || { attempts: 0, correct: 0 };
      const acc = s.attempts > 0 ? s.correct / s.attempts : 1;
      if (s.attempts >= 3 && acc < 0.7 && acc < minAcc) {
        minAcc = acc; worstCat = cat;
      }
    }
    if (worstCat) {
      const level = getDifficultyLevel(worstCat);
      const word = pickWord(worstCat, level);
      const res = buildQuestion(pickQuestionType(level), word, { cat: worstCat });
      return { ...res, _cat: worstCat, _level: level, _wordEn: wEn(word), isWeakness: true };
    }
  }

  // 2. 틀린 패턴 재출제
  if (wrongPatterns.length > 0 && Math.random() < REINFORCE_PROB) {
    const p = wrongPatterns[Math.floor(Math.random() * wrongPatterns.length)];
    let word = null;
    if (p.isWeekly) {
      const ww = weeklyWords.find(w => w.en === p.en);
      if (ww) word = [ww.en, ww.ko, ww.icon || "", p.level];
    }
    if (!word) word = WORDS[p.cat].words.find(w => wEn(w) === p.en) || pickWord(p.cat, p.level);
    
    const res = buildQuestion(pickQuestionType(p.level), word, { cat: p.cat });
    return { ...res, _cat: p.cat, _level: p.level, _wordEn: wEn(word), isWeekly: p.isWeekly };
  }

  const cat  = pickCategory();
  const level = getDifficultyLevel(cat);
  const word = pickWord(cat, level);
  const res = buildQuestion(pickQuestionType(level), word, { cat });
  return { ...res, _cat: cat, _level: level, _wordEn: wEn(word) };
}

function pickWord(cat, level) {
  const words = WORDS[cat].words.filter(w => wLv(w) === level);
  return (words.length > 0 ? words : WORDS[cat].words)[Math.floor(Math.random() * (words.length || WORDS[cat].words.length))];
}

/* ═══════════════════════════════════
   보기 생성 및 기록
═══════════════════════════════════ */
function makeWordChoices(word, field) {
  const correctVal = word[field === 'en' ? 0 : 1];
  const confusable = {
    '주황색': ['주홍색'], '주홍색': ['주황색'],
    'orange': ['vermilion'], 'vermilion': ['orange'],
    '무지개': ['무지개색'], '무지개색': ['무지개']
  };
  const exclude = confusable[correctVal] || [];

  const pool = [];
  for (const data of Object.values(WORDS)) {
    for (const w of data.words) {
      const val = w[field === 'en' ? 0 : 1];
      if (val !== correctVal && !exclude.includes(val)) {
        pool.push(val);
      }
    }
  }
  const unique = [...new Set(pool)].sort(() => Math.random() - 0.5);
  return [correctVal, ...unique.slice(0, 3)].sort(() => Math.random() - 0.5);
}

function makeSpellingChoices(correct) {
  const vowels = 'aeiou', cons = 'bcdfghjklmnpqrstvwxyz', poolFor = c => vowels.includes(c.toLowerCase()) ? vowels : cons;
  const key = correct.toLowerCase();
  const pool = poolFor(key);
  const wrong = new Set();
  while (wrong.size < 3) { const c = pool[Math.floor(Math.random() * pool.length)]; if (c !== key) wrong.add(c); }
  return [key, ...[...wrong]].sort(() => Math.random() - 0.5);
}

function recordResult(correct, elapsed) {
  const lvStats = stats[currentCat].levels[currentWordData.level];
  lvStats.attempts++;
  if (correct) lvStats.correct++;
  lvStats.totalTime += elapsed;

  // 태그(카테고리)별 약점 업데이트
  if (!stats[currentCat].weaknesses['overall']) stats[currentCat].weaknesses['overall'] = { attempts: 0, correct: 0 };
  const wStats = stats[currentCat].weaknesses['overall'];
  wStats.attempts++; if (correct) wStats.correct++;

  if (correct && currentWordData.isWeakness && wStats.attempts >= 5 && wStats.correct / wStats.attempts >= 0.8) {
    showWeaknessClear();
  }

  saveStats(); updateStreak(correct);
  if (correct) {
    netStreak++;
    if (netStreak >= NET_STREAK && !hasNet) {
      hasNet = true; netStreak = 0; showNetBanner();
    }
  } else {
    netStreak = 0;
  }
  if (!correct) {
    wrongPatterns.unshift({ cat: currentCat, level: currentWordData.level, en: currentWordData.en, isWeekly: currentWordData.isWeekly });
    if (wrongPatterns.length > MAX_WRONG_PATTERNS) wrongPatterns.pop();
  } else {
    const idx = wrongPatterns.findIndex(p => p.en === currentWordData.en);
    if (idx !== -1) wrongPatterns.splice(idx, 1);
  }
  recentHistory.push(correct); if (recentHistory.length > 5) recentHistory.shift();
}

function showWeaknessClear() {
  const fb = document.getElementById('feedback');
  fb.textContent = '✨ 약점 단어 정복! 영어 천재예요! ✨';
  fb.className = 'weakness-clear-message';
}
