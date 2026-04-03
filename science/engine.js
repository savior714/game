/* ═══════════════════════════════════
   과학 데이터베이스 [질문, 정답, [보기], 레벨, 태그]
   카테고리: biology(생물), earth(지구과학), physics(물리/기초과학)
   태그: animal_life, plant_life, human_body, cell, solar_system, weather, earth_material, magnetism, light, electricity, force
═══════════════════════════════════ */
const DB = {
  biology: [
    ['사과는 주로 ( )색이에요.', '빨간', ['빨간', '하늘색', '회색'], 0, 'plant_life'],
    ['강아지는 다리가 ( )개예요.', '4', ['2', '4', '6'], 0, 'animal_life'],
    ['사자는 ( )하고 울어요.', '크앙', ['크앙', '야옹', '음매'], 0, 'animal_life'],
    ['코끼리는 코가 ( )요.', '길어', ['길어', '짧아', '딱딱해'], 0, 'animal_life'],
    ['나무는 뿌리, 줄기, ( )으로 되어 있어요.', '잎', ['잎', '다리', '꼬리'], 0, 'plant_life'],
    ['우리 몸에서 숨을 쉬는 곳은 ( )예요.', '허파(폐)', ['허파(폐)', '심장', '위'], 1, 'human_body'],
    ['개구리는 알 -> 올챙이 -> ( ) 순서로 자라요.', '개구리', ['개구리', '붕어', '거북'], 1, 'animal_life'],
    ['나비는 알 -> 애벌레 -> ( ) -> 나비가 돼요.', '번데기', ['번데기', '지렁이', '달팽이'], 1, 'animal_life'],
    ['토끼는 귀가 ( )요.', '길어', ['길어', '짧아', '뾰족해'], 1, 'animal_life'],
    ['식물이 자라는 데 꼭 필요한 것은 물과 ( )이에요.', '햇빛', ['햇빛', '그림자', '바람'], 2, 'plant_life'],
    ['곤충의 다리는 모두 ( )개예요.', '6', ['4', '6', '8'], 2, 'animal_life'],
    ['식물이 영양분을 만드는 과정을 ( )이라고 해요.', '광합성', ['광합성', '호흡', '증발'], 3, 'plant_life'],
    ['곤충의 몸은 머리, 가슴, ( )로 나뉘어요.', '배', ['배', '등', '다리'], 3, 'animal_life'],
    ['척추가 없는 동물을 ( ) 동물이라고 해요.', '무척추', ['무척추', '척추', '포유'], 4, 'animal_life'],
    ['우리 몸에서 음식물을 소화시키는 주된 곳은 ( )예요.', '위', ['위', '심장', '뇌'], 4, 'human_body'],
    ['사람의 뼈는 몸을 지탱하고 ( )을 보호해요.', '심장', ['심장', '발톱', '머리카락'], 5, 'human_body'],
    ['세포의 핵 속에 유전 정보를 담고 있는 것은 ( )예요.', 'DNA', ['DNA', 'RNA', '세포질'], 6, 'cell'],
    ['균류에 속하며 포자로 번식하는 생물은 ( )예요.', '버섯(곰팡이)', ['버섯(곰팡이)', '이끼', '고사리'], 6, 'microorganisms'],
    ['우리 몸에서 사물을 보는 곳은 ( )이에요.', '눈', ['눈', '코', '입'], 0, 'human_body']
  ],
  earth: [
    ['밤하늘에 떠 있는 동그란 모양은 ( )이에요.', '달', ['달', '자동차', '포크'], 0, 'solar_system'],
    ['해가 뜨는 곳은 ( )쪽이에요.', '동', ['동', '서', '남'], 0, 'solar_system'],
    ['비가 그친 뒤 하늘에 나타나는 일곱 빛깔 다리는 ( )이에요.', '무지개', ['무지개', '안개', '구름'], 0, 'weather'],
    ['하늘에서 내리는 눈은 ( )색이에요.', '하얀', ['하얀', '검은', '노란'], 0, 'weather'],
    ['여름에는 날씨가 매우 ( ).', '더워요', ['더워요', '추워요', '시원해요'], 1, 'weather'],
    ['지구의 유일한 자연 위성은 ( )이에요.', '달', ['달', '해', '화성'], 1, 'solar_system'],
    ['강물은 높은 곳에서 ( ) 곳으로 흘러요.', '낮은', ['낮은', '높은', '옆'], 1, 'earth_material'],
    ['우리가 딛고 서 있는 지구의 겉부분을 ( )라고 해요.', '지표', ['지표', '공기', '우주'], 2, 'earth_material'],
    ['태양계의 중심에 있으며 스스로 빛을 내는 천체는 ( )이에요.', '태양', ['태양', '달', '지구'], 2, 'solar_system'],
    ['밤하늘에서 매일 모양이 변하며 밝게 빛나는 천체는 ( )이에요.', '달', ['달', '인공위성', '금성'], 2, 'solar_system'],
    ['계절이 변하는 이유는 지구가 ( )하기 때문이에요.', '공전', ['공전', '자전', '폭발'], 3, 'solar_system'],
    ['태양계에서 가장 큰 행성은 ( )이에요.', '목성', ['목성', '토성', '지구'], 3, 'solar_system'],
    ['화석은 주로 ( )암에서 발견돼요.', '퇴적', ['퇴적', '화성', '변성'], 4, 'earth_material'],
    ['태양계에서 고리가 가장 크고 아름다운 행성은 ( )이에요.', '토성', ['토성', '목성', '화성'], 4, 'solar_system'],
    ['지진의 크기를 나타내는 척도를 ( )라고 해요.', '규모(리히터)', ['규모(리히터)', '온도', '기압'], 5, 'weather'],
    ['지구가 스스로 하루에 한 바퀴씩 도는 것을 ( )이라고 해요.', '자전', ['자전', '공전', '회전'], 5, 'solar_system'],
    ['조개나 나뭇잎이 돌처럼 굳어진 것을 ( )이라고 해요.', '화석', ['화석', '보석', '조약돌'], 6, 'earth_material']
  ],
  physics: [
    ['공을 던지면 ( )로 떨어져요.', '아래', ['아래', '위', '옆'], 0, 'force'],
    ['자석의 같은 극끼리는 서로 ( ).', '밀어내요', ['밀어내요', '끌어당겨요', '붙어요'], 0, 'magnetism'],
    ['얼음은 만지면 ( )워요.', '차가', ['차가', '뜨거', '따뜻해'], 0, 'energy_matter'],
    ['물은 ( ) 흐르는 성질이 있어요.', '찰랑찰랑', ['찰랑찰랑', '딱딱하게', '가볍게'], 0, 'energy_matter'],
    ['얼음은 ( ) 상태예요.', '고체', ['고체', '액체', '기체'], 1, 'energy_matter'],
    ['물은 ( )도에서 얼어요.', '0', ['0', '50', '100'], 1, 'energy_matter'],
    ['얼음이 녹아 물이 되는 것은 ( ) 변화예요.', '상태', ['상태', '성질', '색깔'], 2, 'energy_matter'],
    ['빛이 거울에 부딪혀 튕겨 나가는 현상은 ( )이에요.', '반사', ['반사', '굴절', '흡수'], 2, 'light'],
    ['물체가 원래 모습으로 돌아가려는 힘은 ( )력이에요.', '탄성', ['탄성', '중력', '마찰'], 3, 'force'],
    ['전기가 흐르는 길을 ( )라고 해요.', '회로', ['회로', '통로', '발전'], 3, 'electricity'],
    ['힘의 크기를 나타내는 단위는 ( )이에요.', 'N(뉴턴)', ['N(뉴턴)', 'kg', 'm'], 4, 'force'],
    ['열이 물질을 따라 전달되는 현상을 ( )라고 해요.', '전도', ['전도', '대류', '복사'], 4, 'energy_matter'],
    ['두 물체가 문질러질 때 열이 발생하는 이유는 ( ) 때문이에요.', '마찰력', ['마찰력', '중력', '탄성력'], 5, 'force'],
    ['건전지 2개를 나란히 연결하는 방법을 ( ) 연결이라고 해요.', '병렬', ['병렬', '직렬', '교차'], 5, 'electricity'],
    ['액체에서 기체로 변하는 현상을 ( )이라고 해요.', '기화', ['기화', '액화', '융해'], 6, 'energy_matter']
  ]
};

/* ═══════════════════════════════════
   상수 및 상태
═══════════════════════════════════ */
const TOTAL              = 10;
const TIME_LIMIT         = 120;
const MIN_DATA           = 3;
const SUBJECT_DIFF_OPTS  = { upThreshold: 0.85, downThreshold: 0.75 };
const LAUNCH_STREAK      = 20;
const STATS_KEY          = 'scienceGameStats';
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
  const cats = Object.keys(DB);
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
═══════════════════════════════════ */
function generateQuestion() {
  let q = null;
  let tries = 0;

  while (tries < 20) {
    const candidate = _generateCandidate();
    const key = candidate.data[0]; // 질문 텍스트
    
    // 가용 문제 수에 따른 버퍼 크기 조절
    const pool = DB[candidate.cat].filter(item => item[3] === candidate.level);
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
      const pool = DB[tagCat].filter(q => q[4] === worstTag);
      if (pool.length > 0) {
        const item = pool[Math.floor(Math.random() * pool.length)];
        return { cat: tagCat, level: item[3], data: item, isWeakness: true };
      }
    }
  }

  // 2. 틀린 패턴
  if (wrongPatterns.length > 0 && Math.random() < REINFORCE_PROB) {
    const p = wrongPatterns[Math.floor(Math.random() * wrongPatterns.length)];
    const pool = DB[p.cat].filter(item => item[3] === p.level);
    const q = pool[Math.floor(Math.random() * pool.length)];
    return { cat: p.cat, level: p.level, data: q };
  }

  const cat = pickCategory();
  const level = getDifficultyLevel(cat);
  const pool = DB[cat].filter(item => item[3] === level);
  const q = (pool.length > 0) ? pool[Math.floor(Math.random() * pool.length)] : DB[cat][0];
  return { cat, level, data: q };
}

function askQuestion() {
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
}

function recordResult(correct, elapsed) {
  const lvStats = stats[currentCat].levels[currentQData.level];
  lvStats.attempts++;
  if (correct) lvStats.correct++;
  lvStats.totalTime += elapsed;

  // 태그별 약점 통계
  if (!stats[currentCat].weaknesses[currentQData.tag]) {
    stats[currentCat].weaknesses[currentQData.tag] = { attempts: 0, correct: 0 };
  }
  const wStats = stats[currentCat].weaknesses[currentQData.tag];
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
