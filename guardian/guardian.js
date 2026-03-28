const MOCK_DB = {
  math: [
    ['1 + 2 = ?', '5 - 1 = ?', '3 + 3 = ?', '4 - 2 = ?', '3 + 4 = ?'],
    ['7 + 8 = ?', '15 - 9 = ?', '9 + 6 = ?', '12 - 4 = ?', '11 + 7 = ?'],
    ['25 + 14 = ?', '30 - 15 = ?', '2 × 3 = ?', '4 × 5 = ?', '22 + 18 = ?'],
    ['14 × 6 = ?', '58 + 49 = ?', '12 × 4 = ?', '75 - 38 = ?', '11 × 5 = ?'],
    ['64 × 12 = ?', '150 - 45 = ?', '21 × 11 = ?', '120 + 85 = ?', '18 × 15 = ?'],
    ['125 × 25 = ?', '350 - 188 = ?', '45 × 16 = ?', '200 + 155 = ?', '28 × 22 = ?'],
    ['256 × 130 = ?', '500 - 347 = ?', '64 × 35 = ?', '1000 - 489 = ?', '72 × 48 = ?']
  ],
  english: [
    ['"사과"  a _ _ _ e', '"개"  d _ g', '"고양이"  c _ t', '"태양"  s _ n', '"바다"  s _ a'],
    ['"학교"  s c _ _ o l', '"책상"  d e _ k', '"의자"  c h _ i r', '"연필"  p _ n c i l', '"가방"  b _ g'],
    ['"도서관"  library', '"우주"  space', '"친구"  friend', '"병원"  hospital', '"과학자"  scientist'],
    ['"아름다운"  beautiful', '"위험한"  dangerous', '"중요한"  important', '"환상적인"  fantastic', '"놀라운"  amazing'],
    ['"경험하다"  experience', '"지식"  knowledge', '"발달시키다"  develop', '"조사하다"  investigate', '"성공적인"  successful'],
    ['"책임감"  responsibility', '"독립적인"  independent', '"상상력"  imagination', '"이해하다"  comprehend', '"동기부여"  motivation'],
    ['"철학적인"  philosophical', '"현상"  phenomenon', '"치료법"  therapeutic', '"논쟁의 여지가 있는"  controversial', '"결과"  consequence']
  ],
  korean: [
    ['방, 강, 나, 이, 오', '글자를 올바르게 고르기', '강아지 - 강', '별 - 별', '물 - 물'],
    ['그늘 - 그', '연필을 깎다', '재미있었다', '바닥에 앉지 마', '활짝 피다'],
    ['가방을 어깨에 메다', '도서관에서 책을 읽다', '얼큰하다', '"밝다"의 반대말은? 어둡다', '"기쁘다"의 반대말은? 슬프다'],
    ['발을 씻어 보세요', '가도 돼요?', '웬일이야?', '"희망"의 반대말은? 절망', '진지 잡수셨어요?'],
    ['숙제를 깨끗이 했다', '노란 꽃이 피었다', '연필이 있다', '승리의 반대말은 패배', '두 손으로 드려야 해요'],
    ['며칠에 시작합니까?', '김치찌개', '그렇지 않다', '사장님의 말씀이 있으시겠습니다', '"긍정"의 반대말은? 부정'],
    ['얽히고설켜', '혈혈단신', '주체하지 못했다', '제가 직접 여쭈어 보았습니다', '"구체"의 반대말은? 추상']
  ],
  science: [
    ['사과는 빨간색', '강아지 다리는 4개', '태양은 동쪽에서 떠요', '비 온 뒤 무지개', '밤하늘의 달'],
    ['우리 몸의 허파(폐)', '올챙이 다음 개구리', '여름엔 더워요', '물은 0도에서 얼어요', '얼음은 고체예요'],
    ['식물에 빛과 물이 필요해요', '우리가 딛는 지표', '태양계의 중심 태양', '얼음이 물이 되는 상태 변화', '거울의 빛 반사'],
    ['광합성 작용', '곤충은 머리,가슴,배', '지구의 공전과 계절', '가장 큰 행성 목성', '고무줄의 탄성력'],
    ['무척추 동물', '소화를 담당하는 위', '퇴적암 속의 화석', '힘의 단위 뉴턴(N)', '열의 전달(전도)'],
    ['뼈는 심장을 보호해요', '지진의 크기 규모(리히터)', '지구의 자전', '마찰력과 열', '건전지의 병렬 연결'],
    ['DNA와 유전', '균류 번식 방법', '화석이 만들어지는 과정', '액체가 기체로 기화', '자력선과 물리 법칙']
  ]
};

const AGES = ['5~6세 (유아)', '7세 (예비 초)', '8세 (초1)', '9세 (초2)', '10세 (초3)', '11세 (초4)', '12세 이상 (고학년)'];
const LABELS = ['입문', '기초', '중급', '숙련', '마스터', '초월', '전설'];
const COLORS = ['text-green-500 bg-green-100', 'text-emerald-500 bg-emerald-100', 'text-blue-500 bg-blue-100', 'text-indigo-500 bg-indigo-100', 'text-orange-500 bg-orange-100', 'text-purple-500 bg-purple-100', 'text-red-500 bg-red-100'];

const STORAGE_KEYS = {
  math: 'mathGameStats',
  english: 'englishGameStats',
  korean: 'koreanGameStats',
  science: 'scienceGameStats'
};

let currentSubject = 'math';
let currentLevel = 1;

// 초기화
window.addEventListener('DOMContentLoaded', () => {
  setSubject('math');
  loadRewards();
});

function setSubject(sub) {
  currentSubject = sub;
  
  // 탭 라벨 스타일 변환
  document.querySelectorAll('.tab-btn').forEach(b => {
    b.classList.remove('active-tab');
    b.classList.add('inactive-tab');
  });
  const t = document.getElementById(`tab-${sub}`);
  t.classList.remove('inactive-tab');
  t.classList.add('active-tab');

  // 로컬 스토리지에서 현재 레벨 산출
  const key = STORAGE_KEYS[sub];
  const statsStr = localStorage.getItem(key);
  let baseLevel = 0;
  if (statsStr) {
    try {
      const stats = JSON.parse(statsStr);
      // 첫 번째 도메인 키를 기반으로 베이스 레벨 계산
      const firstDomain = Object.keys(stats).find(k => k !== '_updated_at' && stats[k].levels);
      if (firstDomain) {
        if (window.ProgressEngine) {
           baseLevel = window.ProgressEngine.getBaseDiffLevel(stats, firstDomain, 4); // minData usually 3~4
        } else {
           // Fallback logic
           for(let i=0; i<6; i++) {
              if(stats[firstDomain].levels[i].attempts > 3 && (stats[firstDomain].levels[i].correct / stats[firstDomain].levels[i].attempts) >= 0.9) {
                baseLevel = i+1;
              } else break;
           }
        }
      }
    } catch(e) {}
  }
  
  const sl = document.getElementById('level-slider');
  sl.value = baseLevel;
  onSliderChange(baseLevel);
}

function onSliderChange(val) {
  currentLevel = parseInt(val, 10);
  
  // Update texts
  const clbl = document.getElementById('current-label');
  clbl.className = `px-2.5 py-0.5 rounded-md text-sm ${COLORS[currentLevel]}`;
  clbl.textContent = LABELS[currentLevel];
  
  document.getElementById('current-age').textContent = AGES[currentLevel];
  document.getElementById('level-display').textContent = `Lv. ${currentLevel}`;

  // Update preview cards
  const container = document.getElementById('preview-container');
  container.innerHTML = '';

  const mockSet = MOCK_DB[currentSubject][currentLevel];
  mockSet.forEach((q, idx) => {
    const d = document.createElement('div');
    d.className = "flex items-center gap-3 bg-white p-3.5 rounded-xl border border-gray-100 shadow-sm transition-transform hover:-translate-y-0.5";
    
    // Icon badge
    const badge = document.createElement('div');
    badge.className = "w-8 h-8 rounded-full bg-gray-50 text-gray-400 flex items-center justify-center font-bold text-xs shrink-0 select-none";
    badge.textContent = `Q${idx+1}`;
    
    // Label
    const span = document.createElement('span');
    span.className = "text-gray-700 font-medium text-sm tracking-wide";
    span.textContent = q;

    d.appendChild(badge);
    d.appendChild(span);
    container.appendChild(d);
  });
}

function saveSettings() {
  const key = STORAGE_KEYS[currentSubject];
  const statsStr = localStorage.getItem(key);
  let stats = {};
  
  if (statsStr) {
    try { stats = JSON.parse(statsStr); } catch(e) {}
  }

  // If stats is completely empty, initialize it with correct domains
  if (Object.keys(stats).length === 0) {
    const defaultDomains = {
      'math': ['+', '-', '×'],
      'english': ['animals','fruits','nature','vehicles','colors','numbers','clothing','body','food','objects'],
      'korean': ['spelling', 'antonym', 'honorific'],
      'science': ['biology', 'earth', 'physics']
    };
    const domains = defaultDomains[currentSubject];
    if (window.ProgressEngine) {
      stats = window.ProgressEngine.emptyStats(domains);
    } else {
      for (const d of domains) {
        stats[d] = { levels: {}, weaknesses: {} };
        for (let i = 0; i < 7; i++) {
          stats[d].levels[i] = { attempts: 0, correct: 0, totalTime: 0 };
        }
      }
    }
  }

  // Inject false progress up to targeted level, and clear above
  const targetLv = currentLevel;

  for (const domain of Object.keys(stats)) {
    if (domain === '_updated_at') continue;
    if (!stats[domain].levels) continue;
    
    for (let i = 0; i < 7; i++) {
       if (!stats[domain].levels[i]) {
          stats[domain].levels[i] = { attempts:0, correct:0, totalTime:0 };
       }
       if (i < targetLv) {
          stats[domain].levels[i].attempts = 10;
          stats[domain].levels[i].correct = 10;
       } else {
          stats[domain].levels[i].attempts = 0;
          stats[domain].levels[i].correct = 0;
          stats[domain].levels[i].totalTime = 0;
       }
    }
  }

  stats._updated_at = Date.now();
  localStorage.setItem(key, JSON.stringify(stats));
  
  if(window.SyncEngine) {
     window.SyncEngine.pushStats(key, stats);
  }

  const btn = document.getElementById('save-btn');
  const oldText = btn.textContent;
  btn.textContent = "저장 완료!";
  btn.classList.add("bg-green-600");
  btn.classList.remove("bg-gray-900");
  setTimeout(() => {
    btn.textContent = oldText;
    btn.classList.add("bg-gray-900");
    btn.classList.remove("bg-green-600");
  }, 1500);
}

// ──────────────────────────────────────────
// 보상 상점 관리 (Reward Customization)
// ──────────────────────────────────────────
let rewardState = null;

function loadRewards() {
  const saved = localStorage.getItem('study_rewards');
  if (saved) {
    try {
      rewardState = JSON.parse(saved);
    } catch(e) {}
  }
  if (!rewardState) {
    rewardState = {
      gems: 0, youtube_minutes: 0, snacks: 0, marble_plays: 0,
      shop_items: [
        { id: 'youtube', icon: '📺', label: '유튜브 15분', desc: '좋아하는 영상 시청', price: 1 },
        { id: 'snack', icon: '🍪', label: '간식 1개', desc: '맛있는 간식 시간', price: 1 },
        { id: 'marble', icon: '🎮', label: '마블 게임', desc: '마블 한 판 더!', price: 1 }
      ],
      custom_inventory: {}
    };
  }
  if (!rewardState.shop_items) {
    rewardState.shop_items = [
      { id: 'youtube', icon: '📺', label: '유튜브 15분', desc: '좋아하는 영상 시청', price: 1 },
      { id: 'snack', icon: '🍪', label: '간식 1개', desc: '맛있는 간식 시간', price: 1 },
      { id: 'marble', icon: '🎮', label: '마블 게임', desc: '마블 한 판 더!', price: 1 }
    ];
  }
  if (!rewardState.custom_inventory) rewardState.custom_inventory = {};
  renderRewardList();
}

function renderRewardList() {
  const container = document.getElementById('cr-list');
  if (!container) return;
  container.innerHTML = '';
  
  if (rewardState.shop_items.length === 0) {
    container.innerHTML = '<p class="text-sm text-gray-400 text-center py-4">등록된 보상이 없습니다.</p>';
    return;
  }
  
  rewardState.shop_items.forEach(item => {
    let invCount = 0;
    if (item.id === 'youtube') invCount = rewardState.youtube_minutes + '분';
    else if (item.id === 'snack') invCount = rewardState.snacks + '개';
    else if (item.id === 'marble') invCount = rewardState.marble_plays + '회';
    else invCount = (rewardState.custom_inventory[item.id] || 0) + '개';

    const div = document.createElement('div');
    div.className = 'flex items-center justify-between bg-white p-3 rounded-xl border border-gray-100 shadow-sm';
    div.innerHTML = `
      <div class="flex items-center gap-3">
        <div class="text-2xl">${item.icon}</div>
        <div>
          <div class="font-bold text-sm text-gray-800">${item.label}</div>
          <div class="text-xs text-gray-500">가격: 💎 ${item.price || 1} | 아이 보유량: <span class="text-blue-600 font-bold">${invCount}</span></div>
        </div>
      </div>
      <button onclick="deleteCustomReward('${item.id}')" class="text-gray-400 hover:text-red-500 transition px-2 py-1" title="삭제">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
      </button>
    `;
    container.appendChild(div);
  });
}

function saveRewards() {
  rewardState._updated_at = Date.now();
  localStorage.setItem('study_rewards', JSON.stringify(rewardState));
  if (window.SyncEngine) window.SyncEngine.pushStats('study_rewards', rewardState);
}

function addCustomReward() {
  const icon = document.getElementById('cr-icon').value.trim();
  const label = document.getElementById('cr-label').value.trim();
  const desc = document.getElementById('cr-desc').value.trim();
  const price = parseInt(document.getElementById('cr-price').value, 10);
  
  if (!icon || !label || isNaN(price) || price < 1) {
    alert('아이콘, 이름, 유효한 가격을 입력해주세요.');
    return;
  }
  
  const id = 'custom_' + Date.now();
  rewardState.shop_items.push({ id, icon, label, desc, price });
  saveRewards();
  renderRewardList();
  
  document.getElementById('cr-label').value = '';
  document.getElementById('cr-desc').value = '';
}

function deleteCustomReward(id) {
  const item = rewardState.shop_items.find(i => i.id === id);
  if (!item) return;
  
  let hasInventory = false;
  if (id === 'youtube' && rewardState.youtube_minutes > 0) hasInventory = true;
  else if (id === 'snack' && rewardState.snacks > 0) hasInventory = true;
  else if (id === 'marble' && rewardState.marble_plays > 0) hasInventory = true;
  else if (rewardState.custom_inventory[id] > 0) hasInventory = true;
  
  if (hasInventory) {
    const confirmDelete = confirm('⚠️ 아이가 이미 이 보상을 인벤토리에 보유하고 있습니다.\\n삭제 시 아이의 인벤토리에서도 영구적으로 삭제되며 복구할 수 없습니다.\\n\\n정말 삭제하시겠습니까?');
    if (!confirmDelete) return;
    
    if (id === 'youtube') rewardState.youtube_minutes = 0;
    else if (id === 'snack') rewardState.snacks = 0;
    else if (id === 'marble') rewardState.marble_plays = 0;
    else delete rewardState.custom_inventory[id];
  } else {
    const confirmDelete = confirm('[' + item.label + '] 보상을 목록에서 삭제하시겠습니까?');
    if (!confirmDelete) return;
  }
  
  rewardState.shop_items = rewardState.shop_items.filter(i => i.id !== id);
  saveRewards();
  renderRewardList();
}
