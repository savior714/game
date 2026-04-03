/* ═══════════════════════════════════
   데이터베이스: [질문, 정답, 보기들, 레벨, 태그]
   카테고리: spelling, antonym, honorific
   태그 예시: spelling_basic, spelling_complex, antonym_basic, antonym_abstract, hon_particle, hon_term
═══════════════════════════════════ */
const DB = {
  spelling: [
    // Level 0: 입문
    ['내 가( )은 파란색이야.', '방', ['방', '그', '나', '하'], 0, 'spelling_basic'],
    ['선생님이 ( )판에 글씨를 써요.', '칠', ['칠', '책', '문', '물'], 0, 'spelling_basic'],
    ['( )늘은 날씨가 참 좋아요.', '오', ['오', '우', '아', '이'], 0, 'spelling_basic'],
    ['우리 집 ( )아지는 귀여워요.', '강', ['강', '멍', '야', '새'], 0, 'spelling_basic'],
    ['밤하늘에 ( )이 떠 있어요.', '별', ['별', '물', '강', '숲'], 0, 'spelling_basic'],
    ['바다에 ( )고기가 살아요.', '물', ['물', '산', '숲', '흙'], 0, 'spelling_basic'],
    ['엄마가 ( )을 해주셨어요.', '밥', ['밥', '잠', '책', '차'], 0, 'spelling_basic'],
    // Level 1: 기초 받침
    ['나무 아래 ( )늘이 있어요.', '그', ['그', '가', '바', '나'], 1, 'spelling_basic'],
    ['연필을 ( )아서 써요.', '깎', ['깎', '깍', '꺽', '꺾'], 1, 'spelling_basic'],
    ['어제 본 영화는 정말 ( )었어요.', '있', ['있', '잇', '잊', '잍'], 1, 'spelling_basic'],
    ['바닥에 ( )지 마세요.', '앉', ['앉', '안', '않', '암'], 1, 'spelling_basic'],
    ['꽃이 활( ) 피었습니다.', '짝', ['짝', '작', '짠', '짬'], 1, 'spelling_basic'],
    // Level 2: 중급 받침/철자
    ['가방을 ( )에 메요.', '어깨', ['어깨', '어개', '어케', '어께'], 2, 'spelling_complex'],
    ['도서관에서 책을 ( )어요.', '읽', ['읽', '익', '잇', '일'], 2, 'spelling_complex'],
    ['국물이 참 ( )해요.', '얼큰', ['얼큰', '얼컨', '얼근', '얼군'], 2, 'spelling_complex'],
    // Level 3: 숙련된 맞춤법
    ['발을 ( )어 보세요.', '씻', ['씻', '싯', '싰', '싣'], 3, 'spelling_complex'],
    ['내일 학교에 가도 ( )요?', '돼', ['돼', '되', '두', '데'], 3, 'spelling_complex'],
    ['이게 ( )일이야?', '웬', ['웬', '왠', '웨', '왜'], 3, 'spelling_complex'],
    ['어제보다 ( )이 나아요.', '훨씬', ['훨씬', '훨신', '헐씬', '홀씬'], 3, 'spelling_complex'],
    ['깨끗이 ( )아요.', '닦', ['닦', '닥', '딱', '딲'], 3, 'spelling_complex'],
    // Level 4: 마스터 맞춤법
    ['숙제를 ( ) 했어요.', '깨끗이', ['깨끗이', '깨끗히', '깨끋이', '깨끋히'], 4, 'spelling_complex'],
    ['노란 ( )이 피었습니다.', '꽃', ['꽃', '꼿', '꽂', '꽅'], 4, 'spelling_complex'],
    ['책상 위에 ( )이 있어요.', '연필', ['연필', '연핖', '여필', '열필'], 4, 'spelling_complex'],
    // Level 5: 초월 맞춤법
    ['수업은 ( )에 시작합니다.', '며칠', ['며칠', '몇일', '몇 일', '며칟'], 5, 'spelling_complex'],
    ['김치( )를 끓이다.', '찌개', ['찌개', '찌게', '찌기', '지개'], 5, 'spelling_complex'],
    ['그렇지 ( )다.', '않', ['않', '안', '안하', '안으'], 5, 'spelling_complex'],
    ['( ) 대고 반말이야?', '얻다', ['얻다', '어따', '어디다', '어다가'], 5, 'spelling_complex'],
    ['( )면 안 돼.', '안 하', ['안 하', '않하', '않아', '안아'], 5, 'spelling_complex'],
    // Level 6: 전설 맞춤법
    ['일이 복잡하게 ( ).', '얽히고설켜', ['얽히고설켜', '얼키고설켜', '얽히고섥혀', '얼키고섥혀'], 6, 'spelling_complex'],
    ['그는 ( )으로 살아왔다.', '혈혈단신', ['혈혈단신', '홀홀단신', '홀홀단심', '혈혈단심'], 6, 'spelling_complex'],
    ['화를 ( ) 못했다.', '주체하지', ['주체하지', '추스르지', '추스리지', '주최하지'], 6, 'spelling_complex'],
    ['산봉우리가 ( ) 솟아있다.', '우뚝', ['우뚝', '울뚝', '불뚝', '오뚝'], 6, 'spelling_complex'],
    ['( ) 들어오세요.', '알맞게', ['알맞게', '알맞은', '걸맞게', '알맞히'], 6, 'spelling_complex'],
  ],
  antonym: [
    // Level 0: 기초 반대말
    ['"크다"의 반대말은?', '작다', ['작다', '달리다', '웃다', '높다'], 0, 'antonym_basic'],
    ['"길다"의 반대말은?', '짧다', ['짧다', '크다', '높다', '멀다'], 0, 'antonym_basic'],
    ['"많다"의 반대말은?', '적다', ['적다', '크다', '넓다', '무겁다'], 0, 'antonym_basic'],
    ['"높다"의 반대말은?', '낮다', ['낮다', '멀다', '좁다', '얇다'], 0, 'antonym_basic'],
    ['"차갑다"의 반대말은?', '뜨겁다', ['뜨겁다', '맵다', '짜다', '달다'], 0, 'antonym_basic'],
    ['"앞"의 반대말은?', '뒤', ['뒤', '옆', '밑', '속'], 0, 'antonym_basic'],
    // Level 1: 기초 반대말
    ['"무겁다"의 반대말은?', '가볍다', ['가볍다', '부드럽다', '빠르다', '밝다'], 1, 'antonym_basic'],
    ['"빠르다"의 반대말은?', '느리다', ['느리다', '게으르다', '밝다', '무겁다'], 1, 'antonym_basic'],
    ['"덥다"의 반대말은?', '춥다', ['춥다', '느리다', '맑다', '밝다'], 1, 'antonym_basic'],
    ['"가볍다"의 반대말은?', '무겁다', ['무겁다', '딱딱하다', '부드럽다', '느리다'], 1, 'antonym_basic'],
    // Level 2: 중급 반대말
    ['"기쁘다"의 반대말은?', '슬프다', ['슬프다', '빠르다', '길다', '화나다'], 2, 'antonym_basic'],
    ['"밝다"의 반대말은?', '어둡다', ['어둡다', '흐리다', '탁하다', '진하다'], 2, 'antonym_basic'],
    ['"강하다"의 반대말은?', '약하다', ['약하다', '작다', '느리다', '낮다'], 2, 'antonym_basic'],
    // Level 3: 숙련된 반대말
    ['"성공"의 반대말은?', '실패', ['실패', '포기', '절망', '거절'], 3, 'antonym_abstract'],
    ['"안전"의 반대말은?', '위험', ['위험', '불안', '공포', '긴장'], 3, 'antonym_abstract'],
    ['"희망"의 반대말은?', '절망', ['절망', '어둠', '공포', '실패'], 3, 'antonym_abstract'],
    ['"성실"의 반대말은?', '나태', ['나태', '거짓', '부지런', '정직'], 3, 'antonym_abstract'],
    // Level 4: 마스터 반대말
    ['"승리"의 반대말은?', '패배', ['패배', '협력', '양보', '거절'], 4, 'antonym_abstract'],
    ['"입구"의 반대말은?', '출구', ['출구', '통로', '창구', '계단'], 4, 'antonym_abstract'],
    ['"과거"의 반대말은?', '미래', ['미래', '현재', '어제', '내일'], 4, 'antonym_abstract'],
    // Level 5: 초월 반대말
    ['"긍정"의 반대말은?', '부정', ['부정', '양보', '실패', '절망'], 5, 'antonym_abstract'],
    ['"객관"의 반대말은?', '주관', ['주관', '편견', '차별', '오만'], 5, 'antonym_abstract'],
    ['"원인"의 반대말은?', '결과', ['결과', '과정', '시작', '목적'], 5, 'antonym_abstract'],
    ['"절대"의 반대말은?', '상대', ['상대', '평범', '조건', '가치'], 5, 'antonym_abstract'],
    // Level 6: 전설 반대말
    ['"구체"의 반대말은?', '추상', ['추상', '이상', '개념', '상상'], 6, 'antonym_abstract'],
    ['"희소"의 반대말은?', '풍부', ['풍부', '확장', '만연', '과장'], 6, 'antonym_abstract'],
    ['"거시"의 반대말은?', '미시', ['미시', '축소', '확대', '부분'], 6, 'antonym_abstract'],
    ['"구축"의 반대말은?', '파괴', ['파괴', '소멸', '절망', '분해'], 6, 'antonym_abstract'],
  ],
  honorific: [
    // Level 0: 기초 조사
    ['할아버지( ) 오신다.', '께서', ['께서', '를', '에', '에서'], 0, 'hon_particle'],
    ['선생님( ) 책을 드렸다.', '께', ['께', '를', '에', '에서'], 0, 'hon_particle'],
    ['아버님( ) 오신다.', '께서', ['께서', '를', '에', '에서'], 0, 'hon_particle'],
    // Level 1: 기초 서술어
    ['할머니가 잠을 ( ).', '주무신다', ['주무신다', '자신다', '자요', '잔다'], 1, 'hon_term'],
    ['아버지가 밥을 ( ).', '드신다', ['드신다', '먹는다', '먹어요', '드셔요'], 1, 'hon_term'],
    // Level 2: 중급 조사/어휘
    ['선생님이 학교에 ( ).', '오셨다', ['오셨다', '왔다', '오세요', '와요'], 2, 'hon_term'],
    ['할머니께서 ( )을 하신다.', '말씀', ['말씀', '얘기', '소리', '노래'], 2, 'hon_term'],
    // Level 3: 숙련된 특수 어휘
    ['선생님, ( )이/가 어떻게 되세요?', '성함', ['성함', '이름', '말씀', '얼굴'], 3, 'hon_term'],
    ['어머니께 ( )을 드렸어요.', '진지', ['진지', '밥', '말씀', '선물'], 3, 'hon_term'],
    ['할아버지께 ( )을 여쭈어 보았다.', '말씀', ['말씀', '얘기', '소리', '부탁'], 3, 'hon_term'],
    // Level 4: 마스터 특수 예절
    ['어른께 물건을 드릴 때는 ( )으로 드려야 해요.', '두 손', ['두 손', '한 손', '왼손', '오른손'], 4, 'hon_term'],
    ['진지 ( )?', '잡수셨어요', ['잡수셨어요', '먹었어요', '드셨어요', '하셨어요'], 4, 'hon_term'],
    // Level 5: 초월 간접 높임
    ['할아버지께서는 귀가 ( ).', '밝으시다', ['밝으시다', '밝다', '밝으다', '밝아지신다'], 5, 'hon_term'],
    ['사장님의 ( )이/가 있으시겠습니다.', '말씀', ['말씀', '얘기', '지시', '연설'], 5, 'hon_term'],
    ['어머니, 아버지가 이제 ( ).', '오셨어요', ['오셨어요', '왔어요', '오셨습니다', '오시어요'], 5, 'hon_term'],
    // Level 6: 전설 수준 정중 표현
    ['제가 직접 ( ) 보았습니다.', '여쭈어', ['여쭈어', '물어', '말씀해', '여쭤'], 6, 'hon_term'],
    ['할머니, 저희가 정성을 다해 ( )습니다.', '모시겠', ['모시겠', '대하겠', '섬기겠', '도와드리겠'], 6, 'hon_term'],
    ['고객님, 주문하신 커피 ( ).', '나왔습니다', ['나왔습니다', '나오셨습니다', '되셨습니다', '계십니다'], 6, 'hon_term'],
  ]
};
// 미동기화 방지: 마지막 데이터 태그 추가
DB.honorific[DB.honorific.length - 1] = ['고객님, 주문하신 커피 ( ).', '나왔습니다', ['나왔습니다', '나오셨습니다', '되셨습니다', '계십니다'], 6, 'hon_term'];

/* ═══════════════════════════════════
   상수 및 상태
═══════════════════════════════════ */
const TOTAL              = 10;
const TIME_LIMIT         = 120;
const MIN_DATA           = 3;
const SUBJECT_DIFF_OPTS  = { upThreshold: 0.85, downThreshold: 0.75 };
const LAUNCH_STREAK      = 20;
const STATS_KEY          = 'koreanGameStats';
const MAX_WRONG_PATTERNS = 5;
const REINFORCE_PROB     = 0.45;
const RECENT_LIMIT       = 10;
const ROCKET_MAX_BOTTOM  = 330;

const DIFF_LABELS = ['입문', '기초', '중급', '숙련', '마스터', '초월', '전설'];
const DIFF_COLORS = ['#aed581', '#66bb6a', '#4fc3f7', '#29b6f6', '#ffca28', '#ab47bc', '#ef5350'];
const DOMAIN_KEYS = ['spelling', 'antonym', 'honorific'];

let currentQ      = 0;
let score         = 0;
let answer        = '';
let answered      = false;
let timerInterval = null;
let timeLeft      = TIME_LIMIT;
let currentCat    = 'spelling';

var streak        = 0;
var globalBoost   = 0;
var launching     = false;
var crashing      = false;
var netStreak     = 0;
var hasNet        = false;
const NET_STREAK  = 5;
let wrongPatterns = [];
let currentQData  = null; // { cat, level, tag, isWeakness }
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
   난이도 및 문제 생성 로직
═══════════════════════════════════ */
function getBaseDiffLevel(cat) {
  return ProgressEngine.getBaseDiffLevel(stats, cat, MIN_DATA, SUBJECT_DIFF_OPTS);
}

function getDifficultyLevel(cat) {
  return ProgressEngine.getDifficultyLevel(stats, cat, MIN_DATA, globalBoost, recentHistory, SUBJECT_DIFF_OPTS);
}

function pickCategory() {
  const cats = Object.keys(DB);
  const w = {};
  for (const cat of cats) {
    w[cat] = 1.0;
    let totalAtt = 0, totalCorr = 0;
    Object.values(stats[cat].levels).forEach(l => { totalAtt += l.attempts; totalCorr += l.correct; });
    if (totalAtt >= MIN_DATA && totalCorr / totalAtt < 0.6) w[cat] += 0.5;
  }
  const total = Object.values(w).reduce((a, b) => a + b, 0);
  let r = Math.random() * total;
  for (const [cat, wt] of Object.entries(w)) {
    r -= wt;
    if (r <= 0) return cat;
  }
  return cats[0];
}

function generateQuestion() {
  let q = null;
  let tries = 0;

  while (tries < 20) {
    const candidate = _generateCandidate();
    const key = candidate.data[0]; // 질문 텍스트
    
    // 가용 문제 수가 적은 경우를 위한 동적 버퍼 크기 조절
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
  // 1. 태그 기반 약점 강화 (30% 확률로 가장 낮은 정답률 태그에서 추출)
  if (Math.random() < 0.3) {
    let worstTag = null, minAcc = 2;
    ['spelling', 'antonym', 'honorific'].forEach(c => {
      for (const [tag, s] of Object.entries(stats[c].weaknesses)) {
        const acc = s.attempts > 0 ? s.correct / s.attempts : 1;
        if (s.attempts >= 2 && acc < 0.7 && acc < minAcc) {
          minAcc = acc; worstTag = { cat: c, tag };
        }
      }
    });

    if (worstTag) {
      const pool = DB[worstTag.cat].filter(q => q[4] === worstTag.tag);
      if (pool.length > 0) {
        const item = pool[Math.floor(Math.random() * pool.length)];
        return { cat: worstTag.cat, level: item[3], data: item, isWeakness: true };
      }
    }
  }

  // 2. 기존 틀린 패턴 (LIFO)
  if (wrongPatterns.length > 0 && Math.random() < REINFORCE_PROB) {
    const p = wrongPatterns[Math.floor(Math.random() * wrongPatterns.length)];
    const pool = DB[p.cat].filter(q => q[3] === p.level);
    const item = pool[Math.floor(Math.random() * pool.length)];
    return { cat: p.cat, level: p.level, data: item };
  }

  // 3. 일반 적응형 출제
  const cat   = pickCategory();
  const level = getDifficultyLevel(cat);
  const pool  = DB[cat].filter(q => q[3] === level);
  const item  = pool.length > 0 ? pool[Math.floor(Math.random() * pool.length)] : DB[cat][0];
  return { cat, level, data: item };
}

function askQuestion() {
  answered = false;
  const q = generateQuestion();
  currentCat = q.cat;
  currentQData = { cat: q.cat, level: q.level, tag: q.data[4], isWeakness: q.isWeakness };

  const [qText, qAns, qChoices, qLv, qTag] = q.data;
  answer = qAns; // 정답 데이터 (String)

  // 중복 방지 큐에 추가
  recentQuestions.push(qText);
  if (recentQuestions.length > RECENT_LIMIT) recentQuestions.shift();

  document.getElementById('question').textContent = qText;
  document.getElementById('feedback').textContent = q.isWeakness ? '🔥 약점 집중 도전!' : '';
  document.getElementById('feedback').className   = q.isWeakness ? 'weakness-highlight' : '';
  document.getElementById('next-btn').style.display = 'none';

  const container = document.getElementById('answer-buttons');
  container.innerHTML = '';
  const choices = [...qChoices].sort(() => Math.random() - 0.5);
  choices.forEach(val => {
    const btn = document.createElement('button');
    btn.className = 'answer-btn';
    btn.textContent = val;
    btn.onclick = () => checkAnswer(val, btn);
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

  // 태그별 약점 통계 업데이트
  if (!stats[currentCat].weaknesses[currentQData.tag]) {
    stats[currentCat].weaknesses[currentQData.tag] = { attempts: 0, correct: 0 };
  }
  const wStats = stats[currentCat].weaknesses[currentQData.tag];
  wStats.attempts++;
  if (correct) wStats.correct++;

  if (correct && currentQData.isWeakness && wStats.attempts >= 3 && wStats.correct / wStats.attempts >= 0.8) {
    showWeaknessClear(); // 약점 극복 시각적 피드백
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
  fb.textContent = '✨ 약점 극복 완료! 대단해요! ✨';
  fb.className = 'weakness-clear-message';
}
