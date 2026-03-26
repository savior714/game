/* ═══════════════════════════════════
   데이터베이스: [질문, 정답, 보기들, 레벨]
   카테고리: spelling, antonym, honorific
═══════════════════════════════════ */
const DB = {
  spelling: [
    // Level 0: 기초 받침
    ['내 가( )은 파란색이야.', '방', ['방', '바', '반', '밤'], 0],
    ['선생님이 ( )판에 글씨를 써요.', '칠', ['칠', '치', '친', '침'], 0],
    ['( )늘은 날씨가 참 좋아요.', '오', ['오', '옥', '온', '옴'], 0],
    ['우리 집 ( )아지는 귀여워요.', '강', ['강', '가', '간', '감'], 0],
    ['밤하늘에 ( )이 떠 있어요.', '별', ['별', '벼', '볌', '볓'], 0],
    ['바다에 ( )고기가 살아요.', '물', ['물', '무', '뭄', '문'], 0],
    ['엄마가 ( )을 해주셨어요.', '밥', ['밥', '바', '박', '밤'], 0],
    // Level 1: 복잡한 받침
    ['연필을 ( )아서 써요.', '깎', ['깎', '깍', '꺽', '꺾'], 1],
    ['어제 본 영화는 정말 ( )었어요.', '있', ['있', '잇', '잊', '잍'], 1],
    ['바닥에 ( )지 마세요.', '앉', ['앉', '안', '않', '안'], 1],
    ['꽃이 활( ) 피었습니다.', '짝', ['짝', '작', '짠', '짬'], 1],
    ['가방을 ( )에 메요.', '어깨', ['어깨', '어개', '어케', '어께'], 1],
    ['도서관에서 책을 ( )어요.', '읽', ['읽', '익', '잇', '일'], 1],
    ['국물이 참 ( )해요.', '얼큰', ['얼큰', '얼컨', '얼근', '얼군'], 1],
    // Level 2: 헷갈리는 맞춤법
    ['내일 학교에 가도 ( )요?', '돼', ['돼', '되', '두', '데'], 2],
    ['이게 ( )일이야?', '웬', ['웬', '왠', '웨', '왜'], 2],
    ['어제보다 ( )이 나아요.', '훨씬', ['훨씬', '훨신', '헐씬', '홀씬'], 2],
    ['깨끗이 ( )아요.', '닦', ['닦', '닥', '딱', '딲'], 2],
    ['숙제를 ( ) 했어요.', '깨끗이', ['깨끗이', '깨끗히', '깨끗이', '깨끗히'], 2],
    ['노란 ( )이 피었습니다.', '꽃', ['꽃', '꼿', '꽂', '꽅'], 2],
    ['책상 위에 ( )이 있어요.', '연필', ['연필', '연필', '여필', '열필'], 2],
    // Level 3: 실생활 오용 잦은 맞춤법
    ['수업은 ( )에 시작합니다.', '며칠', ['며칠', '몇일', '몇 일', '며칟'], 3],
    ['김치( )를 끓이다.', '찌개', ['찌개', '찌게', '찌기', '지개'], 3],
    ['그렇지 ( )다.', '않', ['않', '안', '안하', '안으'], 3],
    ['( ) 대고 반말이야?', '얻다', ['얻다', '어따', '어디다', '어다가'], 3],
    ['( )면 안 돼.', '안 하', ['안 하', '않하', '않아', '안아'], 3],
    // Level 4: 고난이도 / 전문가 수준
    ['일이 복잡하게 ( ).', '얽히고설켜', ['얽히고설켜', '얼키고설켜', '얽히고섥혀', '얼키고섥혀'], 4],
    ['그는 ( )으로 살아왔다.', '혈혈단신', ['혈혈단신', '홀홀단신', '홀홀단심', '혈혈단심'], 4],
    ['화를 ( ) 못했다.', '주체하지', ['주체하지', '추스르지', '추스리지', '주최하지'], 4],
    ['산봉우리가 ( ) 솟아있다.', '우뚝', ['우뚝', '울뚝', '불뚝', '오뚝'], 4],
    ['( ) 들어오세요.', '알맞게', ['알맞게', '알맞은', '걸맞게', '알맞히'], 4],
  ],
  antonym: [
    // Level 0: 기초 반대말
    ['"크다"의 반대말은?', '작다', ['작다', '멀다', '낮다', '좁다'], 0],
    ['"길다"의 반대말은?', '짧다', ['짧다', '굵다', '작다', '낮다'], 0],
    ['"많다"의 반대말은?', '적다', ['적다', '작다', '낮다', '좁다'], 0],
    ['"높다"의 반대말은?', '낮다', ['낮다', '깊다', '멀다', '좁다'], 0],
    ['"차갑다"의 반대말은?', '뜨겁다', ['뜨겁다', '맵다', '짜다', '시다'], 0],
    ['"앞"의 반대말은?', '뒤', ['뒤', '옆', '밑', '위'], 0],
    // Level 1: 일상 반대말
    ['"무겁다"의 반대말은?', '가볍다', ['가볍다', '부드럽다', '빠르다', '밝다'], 1],
    ['"빠르다"의 반대말은?', '느리다', ['느리다', '게으르다', '둔하다', '무겁다'], 1],
    ['"덥다"의 반대말은?', '춥다', ['춥다', '시원하다', '맑다', '밝다'], 1],
    ['"기쁘다"의 반대말은?', '슬프다', ['슬프다', '괴롭다', '아프다', '화나다'], 1],
    ['"밝다"의 반대말은?', '어둡다', ['어둡다', '흐리다', '탁하다', '진하다'], 1],
    ['"강하다"의 반대말은?', '약하다', ['약하다', '작다', '느리다', '낮다'], 1],
    // Level 2: 추상/한자어 반대말
    ['"성공"의 반대말은?', '실패', ['실패', '포기', '절망', '거절'], 2],
    ['"안전"의 반대말은?', '위험', ['위험', '불안', '공포', '긴장'], 2],
    ['"희망"의 반대말은?', '절망', ['절망', '어둠', '공포', '실패'], 2],
    ['"승리"의 반대말은?', '패배', ['패배', '실패', '양보', '거절'], 2],
    ['"입구"의 반대말은?', '출구', ['출구', '통로', '창구', '계단'], 2],
    ['"과거"의 반대말은?', '미래', ['미래', '현재', '어제', '내일'], 2],
    // Level 3: 심화 한자어 반대말
    ['"긍정"의 반대말은?', '부정', ['부정', '비관', '거부', '절망'], 3],
    ['"객관"의 반대말은?', '주관', ['주관', '편견', '차별', '오만'], 3],
    ['"원인"의 반대말은?', '결과', ['결과', '과정', '시작', '목적'], 3],
    ['"절대"의 반대말은?', '상대', ['상대', '평범', '조건', '가치'], 3],
    // Level 4: 최고난도 한자어 반대말
    ['"구체"의 반대말은?', '추상', ['추상', '이상', '개념', '상상'], 4],
    ['"희소"의 반대말은?', '풍부', ['풍부', '가득', '만연', '과장'], 4],
    ['"거시"의 반대말은?', '미시', ['미시', '미세', '확대', '부분'], 4],
    ['"구축"의 반대말은?', '파괴', ['파괴', '소멸', '절망', '분해'], 4],
  ],
  honorific: [
    // Level 0: 기초 조사
    ['할아버지( ) 오신다.', '께서', ['께서', '이', '가', '는'], 0], // 주격 조사 높임: 이/가 → 께서
    ['선생님( ) 책을 드렸다.', '께', ['께', '에게', '한테', '를'], 0],
    ['아버님( ) 오신다.', '께서', ['께서', '이', '가', '는'], 0],
    // Level 1: 서술어 높임 (시)
    ['할머니가 잠을 ( ).', '주무신다', ['주무신다', '자신다', '자요', '잔다'], 1],
    ['아버지가 밥을 ( ).', '드신다', ['드신다', '먹는다', '먹어요', '드셔요'], 1],
    ['선생님이 학교에 ( ).', '오셨다', ['오셨다', '왔다', '오세요', '와요'], 1],
    ['할머니께서 ( )을 하신다.', '말씀', ['말씀', '얘기', '소리', '노래'], 1],
    // Level 2: 특수 어휘/문장
    ['선생님, ( )이/가 어떻게 되세요?', '성함', ['성함', '이름', '말씀', '얼굴'], 2],
    ['어머니께 ( )을 드렸어요.', '진지', ['진지', '밥', '말씀', '선물'], 2],
    ['할아버지께 ( )을 여쭈어 보았다.', '말씀', ['말씀', '얘기', '소리', '부탁'], 2],
    ['어른께 물건을 드릴 때는 ( )으로 드려야 해요.', '두 손', ['두 손', '한 손', '왼손', '오른손'], 2],
    ['진지 ( )?', '잡수셨어요', ['잡수셨어요', '먹었어요', '드셨어요', '하셨어요'], 2],
    // Level 3: 간접 높임 및 압존법 예비
    ['할아버지께서는 귀가 ( ).', '밝으시다', ['밝으시다', '밝다', '밝으다', '밝아지신다'], 3],
    ['사장님의 ( )이/가 있으시겠습니다.', '말씀', ['말씀', '얘기', '지시', '연설'], 3],
    ['어머니, 아버지가 이제 ( ).', '오셨어요', ['오셨어요', '왔어요', '오셨습니다', '오시어요'], 3],
    // Level 4: 고도화된 올바른 경어법 사용
    ['제가 직접 ( ) 보았습니다.', '여쭈어', ['여쭈어', '물어', '말씀해', '여쭤'], 4],
    ['할머니, 저희가 정성을 다해 ( )습니다.', '모시겠', ['모시겠', '대하겠', '섬기겠', '도와드리겠'], 4],
    ['고객님, 주문하신 커피 ( ).', '나오셨습니다', ['나왔습니다', '나오셨습니다', '되셨습니다', '계십니다'], 4], // 정답은 나왔습니다 이지만, 자주틀리는 상황 문제화 (위는 오답 선택지. 정답부터 써야함)
  ]
};
// 수정: 마지막 문제 수정
DB.honorific[DB.honorific.length - 1] = ['고객님, 주문하신 커피 ( ).', '나왔습니다', ['나왔습니다', '나오셨습니다', '되셨습니다', '계십니다'], 4];

/* ═══════════════════════════════════
   상수 및 상태
═══════════════════════════════════ */
const TOTAL              = 10;
const TIME_LIMIT         = 60;
const MIN_DATA           = 4;
const LAUNCH_STREAK      = 20;
const STATS_KEY          = 'koreanGameStats';
const MAX_WRONG_PATTERNS = 5;
const REINFORCE_PROB     = 0.45;
const ROCKET_MAX_BOTTOM  = 330;

const DIFF_LABELS = ['기초', '중급', '마스터', '초월', '신'];
const DIFF_COLORS = ['#66bb6a', '#42a5f5', '#ffca28', '#ab47bc', '#ef5350'];

let currentQ      = 0;
let score         = 0;
let answer        = '';
let answered      = false;
let timerInterval = null;
let timeLeft      = TIME_LIMIT;
let currentCat    = 'spelling';

let streak        = 0;
let globalBoost   = 0;
let launching     = false;
let crashing      = false;
let wrongPatterns = [];
let currentQData  = null;

/* ═══════════════════════════════════
   통계 (localStorage)
═══════════════════════════════════ */
function emptyStats() {
  return {
    'spelling':  { attempts: 0, correct: 0, totalTime: 0 },
    'antonym':   { attempts: 0, correct: 0, totalTime: 0 },
    'honorific': { attempts: 0, correct: 0, totalTime: 0 },
  };
}

let stats = loadStats();

function loadStats() {
  try {
    const raw = localStorage.getItem(STATS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      const base = emptyStats();
      for (const cat of Object.keys(base)) {
        if (parsed[cat]) Object.assign(base[cat], parsed[cat]);
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
   난이도 및 문제 생성 로직
═══════════════════════════════════ */
function getBaseDiffLevel(cat) {
  const s = stats[cat];
  if (s.attempts < MIN_DATA) return 0;
  const accuracy = s.correct / s.attempts;
  const avgTime  = s.totalTime / s.attempts;
  if (accuracy >= 0.90 && avgTime <= 3)  return 4;
  if (accuracy >= 0.85 && avgTime <= 5)  return 3;
  if (accuracy >= 0.75 && avgTime <= 7)  return 2;
  if (accuracy >= 0.55 && avgTime <= 11) return 1;
  return 0;
}

function getDifficultyLevel(cat) {
  return Math.min(4, getBaseDiffLevel(cat) + globalBoost);
}

function pickCategory() {
  const cats = Object.keys(DB);
  const w = {};
  for (const cat of cats) {
    w[cat] = 1.0;
    const s = stats[cat];
    if (s.attempts >= MIN_DATA && s.correct / s.attempts < 0.5) w[cat] += 0.5;
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
  // 강화학습: 틀린 패턴 재출제
  if (wrongPatterns.length > 0 && Math.random() < REINFORCE_PROB) {
    const pattern = wrongPatterns[Math.floor(Math.random() * wrongPatterns.length)];
    // 동일 카테고리/레벨에서 랜덤 출제 (단순화)
    const pool = DB[pattern.cat].filter(q => q[3] === pattern.level);
    const item = pool[Math.floor(Math.random() * pool.length)];
    return { cat: pattern.cat, level: pattern.level, data: item };
  }

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
  currentQData = { cat: q.cat, level: q.level };

  const [qText, qAns, qChoices, qLv] = q.data;
  answer = qAns;

  document.getElementById('question').textContent = qText;
  document.getElementById('feedback').textContent = '';
  document.getElementById('feedback').className   = '';
  document.getElementById('next-btn').style.display = 'none';

  const container = document.getElementById('answer-buttons');
  container.innerHTML = '';
  
  // 보기 셔플
  const choices = [...qChoices].sort(() => Math.random() - 0.5);
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

function recordResult(correct, elapsed) {
  stats[currentCat].attempts++;
  if (correct) stats[currentCat].correct++;
  stats[currentCat].totalTime += elapsed;
  saveStats();
  updateStreak(correct);

  if (!correct && currentQData) {
    wrongPatterns.unshift(currentQData);
    if (wrongPatterns.length > MAX_WRONG_PATTERNS) wrongPatterns.pop();
  } else if (correct && currentQData) {
    const idx = wrongPatterns.findIndex(p => p.cat === currentQData.cat && p.level === currentQData.level);
    if (idx !== -1) wrongPatterns.splice(idx, 1);
  }
}
