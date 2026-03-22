/* ═══════════════════════════════════
   단어 데이터베이스  [en, ko, emoji, level]
   level: 0=쉬움(3~5자), 1=보통(5~7자), 2=어려움(7자+)
═══════════════════════════════════ */
const WORDS = {
  animals:  { label:'동물',   icon:'🐾', words:[
    ['tiger','호랑이','🐯',1], ['horse','말','🐴',1], ['sheep','양','🐑',1], ['snake','뱀','🐍',1],
    ['eagle','독수리','🦅',1], ['mouse','쥐','🐭',1], ['shark','상어','🦈',1],
    ['whale','고래','🐳',1], ['panda','판다','🐼',1], ['koala','코알라','🐨',1],
    ['giraffe','기린','🦒',2], ['dolphin','돌고래','🐬',2], ['penguin','펭귄','🐧',2],
    ['elephant','코끼리','🐘',2], ['kangaroo','캥거루','🦘',2],
    ['butterfly','나비','🦋',2], ['crocodile','악어','🐊',2],
  ]},
  fruits:   { label:'과일',   icon:'🍎', words:[
    ['apple','사과','🍎',1], ['grape','포도','🍇',1], ['lemon','레몬','🍋',1],
    ['mango','망고','🥭',1], ['melon','멜론','🍈',1], ['peach','복숭아','🍑',1],
    ['cherry','체리','🍒',2], ['orange','오렌지','🍊',2], ['banana','바나나','🍌',2],
    ['papaya','파파야','🍑',2], ['pineapple','파인애플','🍍',2],
    ['strawberry','딸기','🍓',2], ['watermelon','수박','🍉',2],
  ]},
  colors:   { label:'색깔',   icon:'🎨', words:[
    ['green','초록색','🟢',1], ['white','흰색','⬜',1], ['black','검정색','⬛',1],
    ['brown','갈색','🟫',1], ['orange','주황색','🟠',1],
    ['purple','보라색','🟣',2], ['yellow','노란색','🟡',2], ['silver','은색','🪙',2],
    ['indigo','남색','💙',2], ['rainbow','무지개색','🌈',2],
  ]},
  numbers:  { label:'숫자',   icon:'🔢', words:[
    ['zero','영','0️⃣',1], ['four','사','4️⃣',1], ['five','오','5️⃣',1],
    ['nine','구','9️⃣',1], ['three','삼','3️⃣',1], ['seven','칠','7️⃣',1], ['eight','팔','8️⃣',1],
    ['eleven','십일','🔢',2], ['twelve','십이','🔢',2], ['twenty','이십','🔢',2],
    ['thirty','삼십','🔢',2], ['hundred','백','💯',2],
  ]},
  body:     { label:'신체',   icon:'👤', words:[
    ['mouth','입','👄',1], ['cheek','뺨','😊',1], ['chest','가슴','🫀',1],
    ['elbow','팔꿈치','💪',1], ['tooth','이','🦷',1], ['knee','무릎','🦵',1],
    ['finger','손가락','🫵',2], ['stomach','위','🫀',2], ['shoulder','어깨','💆',2],
    ['forehead','이마','🧠',2], ['eyebrow','눈썹','🤨',2],
  ]},
  space:    { label:'우주',   icon:'🌌', words:[
    ['Mars','화성','🔴',1], ['Earth','지구','🌍',1], ['Venus','금성','💫',1],
    ['comet','혜성','☄️',1], ['Pluto','명왕성','🔵',1],
    ['Saturn','토성','🪐',2], ['Jupiter','목성','🌕',2], ['Neptune','해왕성','🔵',2],
    ['Mercury','수성','⭐',2], ['asteroid','소행성','🪨',2],
  ]},
  jobs:     { label:'직업',   icon:'👷', words:[
    ['actor','배우','🎭',1], ['baker','제빵사','🥖',1], ['pilot','조종사','✈️',1],
    ['nurse','간호사','👩‍⚕️',1], ['judge','판사','⚖️',1],
    ['doctor','의사','👨‍⚕️',2], ['farmer','농부','👨‍🌾',2], ['dancer','무용수','💃',2],
    ['singer','가수','🎤',2], ['artist','예술가','🎨',2],
    ['teacher','선생님','👨‍🏫',2], ['soldier','군인','🪖',2],
  ]},
  transport:{ label:'교통',   icon:'🚗', words:[
    ['train','기차','🚂',1], ['plane','비행기','✈️',1], ['truck','트럭','🚛',1],
    ['yacht','요트','⛵',1], ['ferry','여객선','⛴️',1],
    ['rocket','로켓','🚀',2], ['subway','지하철','🚇',2], ['bicycle','자전거','🚲',2],
    ['helicopter','헬리콥터','🚁',2], ['motorcycle','오토바이','🏍️',2],
  ]},
  places:   { label:'장소',   icon:'🏠', words:[
    ['store','가게','🏪',1], ['hotel','호텔','🏨',1], ['beach','해변','🏖️',1],
    ['tower','탑','🗼',1], ['school','학교','🏫',1], ['church','교회','⛪',1],
    ['airport','공항','✈️',2], ['stadium','경기장','🏟️',2], ['museum','박물관','🏛️',2],
    ['hospital','병원','🏥',2], ['library','도서관','📚',2],
  ]},
  nature:   { label:'자연',   icon:'🌿', words:[
    ['cloud','구름','☁️',1], ['storm','폭풍','⛈️',1], ['river','강','🏞️',1],
    ['grass','풀','🌱',1], ['flame','불꽃','🔥',1], ['stone','돌','🪨',1],
    ['thunder','천둥','⛈️',2], ['rainbow','무지개','🌈',2], ['volcano','화산','🌋',2],
    ['mountain','산','🏔️',2], ['hurricane','허리케인','🌀',2],
  ]},
};

// 단어 필드 접근자
const wEn  = w => w[0];
const wKo  = w => w[1];
const wIco = w => w[2];
const wLv  = w => w[3];

/* ═══════════════════════════════════
   상수
═══════════════════════════════════ */
const TOTAL              = 10;
const TIME_LIMIT         = 20;
const MIN_DATA           = 3;
const LAUNCH_STREAK      = 20;
const STATS_KEY          = 'englishGameStats';
const MAX_WRONG_PATTERNS = 5;
const REINFORCE_PROB     = 0.45;
const ROCKET_MAX_BOTTOM  = 330;
const DIFF_LABELS        = ['쉬움', '보통', '어려움'];
const DIFF_COLORS        = ['#66bb6a', '#ffa726', '#ef5350'];

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
let currentWordData = null;
let streak         = 0;
let globalBoost    = 0;
let launching      = false;
let crashing       = false;
let wrongPatterns  = [];

/* ═══════════════════════════════════
   통계 (localStorage)
═══════════════════════════════════ */
function emptyStats() {
  const s = {};
  for (const cat of Object.keys(WORDS)) s[cat] = { attempts:0, correct:0, totalTime:0 };
  return s;
}

let stats = loadStats();

function loadStats() {
  try {
    const raw = localStorage.getItem(STATS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      const base = emptyStats();
      for (const cat of Object.keys(WORDS)) {
        if (parsed[cat]) Object.assign(base[cat], parsed[cat]);
      }
      return base;
    }
  } catch(e) {}
  return emptyStats();
}

function saveStats()  { localStorage.setItem(STATS_KEY, JSON.stringify(stats)); }
function resetStats() { stats = emptyStats(); saveStats(); renderStatsTable(); }

/* ═══════════════════════════════════
   난이도 계산
═══════════════════════════════════ */
function getBaseDiffLevel(cat) {
  const s = stats[cat];
  if (s.attempts < MIN_DATA) return 0;
  const accuracy = s.correct / s.attempts;
  const avgTime  = s.totalTime / s.attempts;
  if (accuracy >= 0.65 && avgTime <= 9)  return 2;
  if (accuracy >= 0.45 && avgTime <= 13) return 1;
  return 1;
}

function getDifficultyLevel(cat) {
  return Math.min(2, getBaseDiffLevel(cat) + globalBoost);
}

/* ═══════════════════════════════════
   카테고리 선택 (약한 카테고리 가중치 ↑)
═══════════════════════════════════ */
function pickCategory() {
  const cats = Object.keys(WORDS);
  const w = {};
  for (const cat of cats) w[cat] = 1.0;
  for (const cat of cats) {
    const s = stats[cat];
    if (s.attempts >= MIN_DATA && s.correct / s.attempts < 0.5) w[cat] += 0.5;
  }
  const total = Object.values(w).reduce((a, b) => a + b, 0);
  let r = Math.random() * total;
  for (const [cat, wt] of Object.entries(w)) { r -= wt; if (r <= 0) return cat; }
  return cats[0];
}

/* ═══════════════════════════════════
   단어 선택
═══════════════════════════════════ */
function pickWord(cat, level) {
  const words = WORDS[cat].words.filter(w => wLv(w) === level);
  const pool  = words.length > 0 ? words : WORDS[cat].words;
  return pool[Math.floor(Math.random() * pool.length)];
}

/* ═══════════════════════════════════
   문제 유형 선택
═══════════════════════════════════ */
function pickQuestionType(level) {
  const weights = {1: [0.60, 0.40], 2: [0.45, 0.55]}[level] || [0.55, 0.45];
  const types   = ['kor2word', 'spelling'];
  let r = Math.random();
  for (let i = 0; i < types.length; i++) { r -= weights[i]; if (r <= 0) return types[i]; }
  return 'kor2word';
}

/* ═══════════════════════════════════
   보기 생성
═══════════════════════════════════ */
function makeWordChoices(word, field) {
  const correctVal = word[field === 'en' ? 0 : 1];
  const pool = [];
  for (const data of Object.values(WORDS)) {
    for (const w of data.words) {
      const val = w[field === 'en' ? 0 : 1];
      if (val !== correctVal) pool.push(val);
    }
  }
  const unique   = [...new Set(pool)].sort(() => Math.random() - 0.5);
  const wrong    = unique.slice(0, 3);
  return [correctVal, ...wrong].sort(() => Math.random() - 0.5);
}

function makeSpellingChoices(correct) {
  const vowels  = 'aeiou';
  const cons    = 'bcdfghjklmnpqrstvwxyz';
  const poolFor = c => vowels.includes(c.toLowerCase()) ? vowels : cons;
  const key     = correct.toLowerCase();

  if (key.length === 1) {
    const pool  = poolFor(key);
    const wrong = new Set();
    let tries   = 0;
    while (wrong.size < 3 && tries < 200) {
      tries++;
      const c = pool[Math.floor(Math.random() * pool.length)];
      if (c !== key) wrong.add(c);
    }
    const fallback = 'abcdefghijklmnopqrstuvwxyz';
    while (wrong.size < 3) {
      const c = fallback[Math.floor(Math.random() * fallback.length)];
      if (c !== key) wrong.add(c);
    }
    return [key, ...[...wrong]].sort(() => Math.random() - 0.5);
  }

  // 2-char: 각 위치를 독립적으로 같은 모음/자음 풀에서 선택
  const p0    = poolFor(key[0]);
  const p1    = poolFor(key[1]);
  const wrong = new Set();
  let tries   = 0;
  while (wrong.size < 3 && tries < 300) {
    tries++;
    const combo = p0[Math.floor(Math.random() * p0.length)] +
                  p1[Math.floor(Math.random() * p1.length)];
    if (combo !== key) wrong.add(combo);
  }
  const alpha = 'abcdefghijklmnopqrstuvwxyz';
  while (wrong.size < 3) {
    const combo = alpha[Math.floor(Math.random() * 26)] + alpha[Math.floor(Math.random() * 26)];
    if (combo !== key) wrong.add(combo);
  }
  return [key, ...[...wrong]].sort(() => Math.random() - 0.5);
}

/* ═══════════════════════════════════
   문제 생성
═══════════════════════════════════ */
function buildQuestion(type, word) {
  const en  = wEn(word);
  const ko  = wKo(word);
  const ico = wIco(word);

  if (type === 'spelling') {
    const numBlanks = en.length >= 5 && Math.random() < 0.5 ? 2 : 1;
    if (numBlanks === 2) {
      const idx1 = Math.floor(Math.random() * en.length);
      let idx2;
      do { idx2 = Math.floor(Math.random() * en.length); } while (idx2 === idx1);
      const [i, j] = [idx1, idx2].sort((a, b) => a - b);
      const correct = (en[i] + en[j]).toLowerCase();
      return {
        type, ico, hint: ko, answer: correct, word: en, blankIndices: [i, j],
        blanks: [
          { char: en[i].toLowerCase(), choices: makeSpellingChoices(en[i].toLowerCase()) },
          { char: en[j].toLowerCase(), choices: makeSpellingChoices(en[j].toLowerCase()) },
        ],
      };
    }
    const blankIdx = Math.floor(Math.random() * en.length);
    const correct  = en[blankIdx].toLowerCase();
    const display  = en.slice(0, blankIdx) + ' _ ' + en.slice(blankIdx + 1);
    return { type, ico, main: display, hint: ko, answer: correct, choices: makeSpellingChoices(correct) };
  }
  // kor2word
  return { type, ico, main: ko, hint: null, answer: en, choices: makeWordChoices(word, 'en') };
}

/* ═══════════════════════════════════
   강화학습: 틀린 패턴 재출제
═══════════════════════════════════ */
function addWrongPattern(data) {
  wrongPatterns.unshift(data);
  if (wrongPatterns.length > MAX_WRONG_PATTERNS) wrongPatterns.pop();
}

function removeWrongPattern({ cat, en }) {
  const idx = wrongPatterns.findIndex(p => p.cat === cat && p.en === en);
  if (idx !== -1) wrongPatterns.splice(idx, 1);
}

function generateSimilar({ cat, level, en }) {
  const same = WORDS[cat].words.filter(w => wLv(w) === level && wEn(w) !== en);
  const pool = same.length > 0 ? same : WORDS[cat].words.filter(w => wEn(w) !== en);
  return { cat, word: pool.length > 0 ? pool[Math.floor(Math.random() * pool.length)] : WORDS[cat].words[0] };
}

function generateQuestion() {
  let cat, word;
  if (wrongPatterns.length > 0 && Math.random() < REINFORCE_PROB) {
    const pattern  = wrongPatterns[Math.floor(Math.random() * wrongPatterns.length)];
    const result   = generateSimilar(pattern);
    cat  = result.cat;
    word = result.word;
  } else {
    cat  = pickCategory();
    word = pickWord(cat, getDifficultyLevel(cat));
  }
  currentCat      = cat;
  currentWordData = { cat, level: wLv(word), en: wEn(word) };
  const type      = pickQuestionType(getDifficultyLevel(cat));
  return buildQuestion(type, word);
}
