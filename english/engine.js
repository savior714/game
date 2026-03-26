/* ═══════════════════════════════════
   단어 데이터베이스  [en, ko, emoji, level]
   level: 0=쉬움(3~5자), 1=보통(5~7자), 2=어려움(7자+)
═══════════════════════════════════ */
const WORDS = {
  animals:  { label:'동물',   icon:'🐾', words:[
    ['tiger','호랑이','🐯',0], ['horse','말','🐴',0], ['sheep','양','🐑',0], ['snake','뱀','🐍',0],
    ['eagle','독수리','🦅',1], ['mouse','쥐','🐭',1], ['shark','상어','🦈',1],
    ['whale','고래','🐳',1], ['panda','판다','🐼',1], ['koala','코알라','🐨',1],
    ['giraffe','기린','🦒',2], ['dolphin','돌고래','🐬',2], ['penguin','펭귄','🐧',2],
    ['elephant','코끼리','🐘',3], ['kangaroo','캥거루','🦘',3],
    ['butterfly','나비','🦋',3], ['crocodile','악어','🐊',3],
    ['rhinoceros', '코뿔소', '🦏', 4], ['hippopotamus', '하마', '🦛', 4], ['chameleon', '카멜레온', '🦎', 4],
    ['orangutan', '오랑우탄', '🦧', 5], ['platypus', '오리너구리', '🦦', 5],
    ['brachiosaurus', '브라키오사우루스', '🦕', 6], ['stegosaurus', '스테고사우루스', '🦕', 6]
  ]},
  fruits:   { label:'과일',   icon:'🍎', words:[
    ['apple','사과','🍎',0], ['grape','포도','🍇',0], ['lemon','레몬','🍋',0],
    ['mango','망고','🥭',1], ['melon','멜론','🍈',1], ['peach','복숭아','🍑',1],
    ['cherry','체리','🍒',2], ['orange','오렌지','🍊',2], ['banana','바나나','🍌',2],
    ['papaya','파파야','🥭',3], ['pineapple','파인애플','🍍',3],
    ['strawberry','딸기','🍓',3], ['watermelon','수박','🍉',3],
    ['pomegranate', '석류', '🔴', 4], ['cranberry', '크랜베리', '🍒', 4],
    ['persimmon', '감', '🟠', 5], ['mangosteen', '망고스틴', '🥭', 5],
    ['dragonfruit', '용과', '🌵', 6], ['passionfruit', '백향과', '🟣', 6]
  ]},
  colors:   { label:'색깔',   icon:'🎨', words:[
    ['green','초록색','🟢',0], ['white','흰색','⬜',0], ['black','검정색','⬛',0],
    ['brown','갈색','🟫',1],
    ['purple','보라색','🟣',2], ['yellow','노란색','🟡',2], ['silver','은색','🪙',2],
    ['indigo','남색','💙',3],
    ['turquoise', '청록색', '🩵', 4], ['magenta', '자홍색', '🩷', 4],
    ['chartreuse', '연두색', '🟩', 5], ['vermilion', '주홍색', '🟥', 5],
    ['fluorescent', '형광색', '✨', 6], ['monochrome', '단색', '🏁', 6]
  ]},
  numbers:  { label:'숫자',   icon:'🔢', words:[
    ['zero','영','0️⃣',0], ['four','사','4️⃣',0], ['five','오','5️⃣',0],
    ['nine','구','9️⃣',1], ['three','삼','3️⃣',1], ['seven','칠','7️⃣',1], ['eight','팔','8️⃣',1],
    ['eleven','십일','🔢',2], ['twelve','십이','🔢',2], ['twenty','이십','🔢',2],
    ['thirty','삼십','🔢',3], ['hundred','백','💯',3],
    ['thousand', '천', '🔢', 4], ['million', '백만', '🔢', 4],
    ['billion', '십억', '🔢', 5], ['trillion', '조', '🔢', 5],
    ['quadrillion', '경', '🔢', 6], ['quintillion', '해', '🔢', 6]
  ]},
  body:     { label:'신체',   icon:'👤', words:[
    ['mouth','입','👄',0], ['cheek','뺨','😊',0], ['chest','가슴','🫀',1],
    ['elbow','팔꿈치','💪',1], ['tooth','이','🦷',1], ['knee','무릎','🦵',1],
    ['finger','손가락','🫵',2], ['stomach','위','🫀',2], ['shoulder','어깨','💆',3],
    ['forehead','이마','🧠',3], ['eyebrow','눈썹','🤨',3],
    ['skeleton', '골격', '🦴', 4], ['intestine', '장', '🫀', 4],
    ['esophagus', '식도', '🫀', 5], ['diaphragm', '횡격막', '🫀', 5],
    ['capillary', '모세혈관', '🩸', 6], ['cerebellum', '소뇌', '🧠', 6]
  ]},
  space:    { label:'우주',   icon:'🌌', words:[
    ['Mars','화성','🔴',0], ['Earth','지구','🌍',0], ['Venus','금성','💫',1],
    ['comet','혜성','☄️',1], ['Pluto','명왕성','🔵',1],
    ['Saturn','토성','🪐',2], ['Jupiter','목성','🌕',2], ['Neptune','해왕성','🔵',3],
    ['Mercury','수성','⭐',3], ['asteroid','소행성','🪨',3],
    ['galaxy', '은하', '🌌', 4], ['universe', '우주', '🌌', 4],
    ['constellation', '별자리', '✨', 5], ['atmosphere', '대기', '☁️', 5],
    ['nebula', '성운', '🌫️', 6], ['supernova', '초신성', '💥', 6]
  ]},
  jobs:     { label:'직업',   icon:'👷', words:[
    ['actor','배우','🎭',0], ['baker','제빵사','🥖',0], ['pilot','조종사','✈️',1],
    ['nurse','간호사','👩‍⚕️',1], ['judge','판사','⚖️',1],
    ['doctor','의사','👨‍⚕️',2], ['farmer','농부','👨‍🌾',2], ['dancer','무용수','💃',3],
    ['singer','가수','🎤',3], ['artist','예술가','🎨',3],
    ['teacher','선생님','👨‍🏫',3], ['soldier','군인','🪖',3],
    ['astronaut', '우주비행사', '👨‍🚀', 4], ['scientist', '과학자', '👨‍🔬', 4],
    ['veterinarian', '수의사', '👨‍⚕️', 5], ['psychiatrist', '정신과 의사', '👨‍⚕️', 5],
    ['archaeologist', '고고학자', '🏺', 6], ['meteorologist', '기상학자', '🌦️', 6]
  ]},
  transport:{ label:'교통',   icon:'🚗', words:[
    ['train','기차','🚂',0], ['plane','비행기','✈️',0], ['truck','트럭','🚛',1],
    ['yacht','요트','⛵',1], ['ferry','여객선','⛴️',1],
    ['rocket','로켓','🚀',2], ['subway','지하철','🚇',2], ['bicycle','자전거','🚲',3],
    ['helicopter','헬리콥터','🚁',3], ['motorcycle','오토바이','🏍️',3],
    ['submarine', '잠수함', '⛴️', 4], ['ambulance', '구급차', '🚑', 4],
    ['hovercraft', '호버크라프트', '🛥️', 5], ['bulldozer', '불도저', '🚜', 5],
    ['snowmobile', '스노모빌', '❄️', 6], ['spaceship', '우주선', '🛸', 6]
  ]},
  places:   { label:'장소',   icon:'🏠', words:[
    ['store','가게','🏪',0], ['hotel','호텔','🏨',0], ['beach','해변','🏖️',1],
    ['tower','탑','🗼',1], ['school','학교','🏫',1], ['church','교회','⛪',1],
    ['airport','공항','✈️',2], ['stadium','경기장','🏟️',2], ['museum','박물관','🏛️',3],
    ['hospital','병원','🏥',3], ['library','도서관','📚',3],
    ['restaurant', '식당', '🍽️', 4], ['university', '대학교', '🎓', 4],
    ['observatory', '천문대', '🔭', 5], ['laboratory', '연구실', '🔬', 5],
    ['auditorium', '강당', '🏛️', 6], ['penitentiary', '교도소', '⛓️', 6]
  ]},
  nature:   { label:'자연',   icon:'🌿', words:[
    ['cloud','구름','☁️',0], ['storm','폭풍','⛈️',0], ['river','강','🏞️',1],
    ['grass','풀','🌱',1], ['flame','불꽃','🔥',1], ['stone','돌','🪨',1],
    ['thunder','천둥','⛈️',2], ['rainbow','무지개','🌈',2], ['volcano','화산','🌋',3],
    ['mountain','산','🏔️',3], ['hurricane','허리케인','🌀',3],
    ['avalanche', '눈사태', '🌨️', 4], ['waterfall', '폭포', '🌊', 4],
    ['earthquake', '지진', '🌋', 5], ['stalactite', '종유석', '🪨', 5],
    ['photosynthesis', '광합성', '☀️', 6], ['precipitation', '강수량', '🌧️', 6]
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
const TIME_LIMIT         = 60;
const MIN_DATA           = 3;
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
let streak         = 0;
let globalBoost    = 0;
let launching      = false;
let crashing       = false;
let netStreak      = 0;
let hasNet         = false;
const NET_STREAK   = 5;
let wrongPatterns  = [];
let recentHistory  = []; // 최근 5문제 정답 여부
let recentQuestions = []; // 최근 10단어 (중복 방지용 키)

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
  return ProgressEngine.getBaseDiffLevel(stats, cat, MIN_DATA);
}

function getDifficultyLevel(cat) {
  return ProgressEngine.getDifficultyLevel(stats, cat, MIN_DATA, globalBoost, recentHistory);
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
function pickQuestionType(level) {
  const weights = {0:[1,0], 1:[0.8,0.2], 2:[0.6,0.4], 3:[0.4,0.6], 4:[0.2,0.8], 5:[0.1,0.9], 6:[0,1]}[level] || [0.55, 0.45];
  const types   = ['kor2word', 'spelling'];
  let r = Math.random();
  for (let i = 0; i < types.length; i++) { r -= weights[i]; if (r <= 0) return types[i]; }
  return 'kor2word';
}

function buildQuestion(type, word) {
  const en  = wEn(word);
  const ko  = wKo(word);
  const ico = wIco(word);
  if (type === 'spelling') {
    const numBlanks = en.length >= 5 && Math.random() < 0.5 ? 2 : 1;
    if (numBlanks === 2) {
      const idx1 = Math.floor(Math.random() * en.length);
      let idx2; do { idx2 = Math.floor(Math.random() * en.length); } while (idx2 === idx1);
      const [i, j] = [idx1, idx2].sort((a, b) => a - b);
      const correct = (en[i] + en[j]).toLowerCase();
      return { type, ico, hint: ko, answer: correct, word: en, blankIndices: [i, j], 
               blanks: [{char:en[i].toLowerCase(), choices:makeSpellingChoices(en[i].toLowerCase())}, {char:en[j].toLowerCase(), choices:makeSpellingChoices(en[j].toLowerCase())}] };
    }
    const blankIdx = Math.floor(Math.random() * en.length);
    const correct  = en[blankIdx].toLowerCase();
    const display  = en.slice(0, blankIdx) + ' _ ' + en.slice(blankIdx + 1);
    return { type, ico, main: display, hint: ko, answer: correct, choices: makeSpellingChoices(correct) };
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
    
    const slice = recentQuestions.slice(-limit);
    if (!slice.includes(wordKey) || catWords.length <= 1) {
      q = candidate;
      break;
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
      const res = buildQuestion(pickQuestionType(level), word);
      return { ...res, _cat: worstCat, _level: level, _wordEn: wEn(word), isWeakness: true };
    }
  }

  // 2. 틀린 패턴 재출제
  if (wrongPatterns.length > 0 && Math.random() < REINFORCE_PROB) {
    const p = wrongPatterns[Math.floor(Math.random() * wrongPatterns.length)];
    const word = WORDS[p.cat].words.find(w => wEn(w) === p.en) || pickWord(p.cat, p.level);
    const res = buildQuestion(pickQuestionType(p.level), word);
    return { ...res, _cat: p.cat, _level: p.level, _wordEn: wEn(word) };
  }

  const cat  = pickCategory();
  const level = getDifficultyLevel(cat);
  const word = pickWord(cat, level);
  const res = buildQuestion(pickQuestionType(level), word);
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
    wrongPatterns.unshift({ cat: currentCat, level: currentWordData.level, en: currentWordData.en });
    if (wrongPatterns.length > MAX_WRONG_PATTERNS) wrongPatterns.pop();
  } else {
    const idx = wrongPatterns.findIndex(p => p.cat === currentCat && p.en === currentWordData.en);
    if (idx !== -1) wrongPatterns.splice(idx, 1);
  }
  recentHistory.push(correct); if (recentHistory.length > 5) recentHistory.shift();
}

function showWeaknessClear() {
  const fb = document.getElementById('feedback');
  fb.textContent = '✨ 약점 단어 정복! 영어 천재예요! ✨';
  fb.className = 'weakness-clear-message';
}
