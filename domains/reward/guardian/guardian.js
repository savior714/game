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
  math: 'aiden_math_stats',
  english: 'aiden_english_stats',
  korean: 'aiden_korean_stats',
  science: 'aiden_science_stats'
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
  
  // 수학 학습 진도 스냅샷 및 일일 목표 프리셋 섹션 노출 제어 (수학만)
  const mathSection = document.getElementById('math-progress-snapshot-section');
  if (mathSection) {
    mathSection.style.display = (sub === 'math') ? 'block' : 'none';
  }
  const presetsSection = document.getElementById('math-daily-goal-presets-section');
  if (presetsSection) {
    presetsSection.style.display = (sub === 'math') ? 'block' : 'none';
  }
  if (sub === 'math') {
    renderMathGoalPresets();
    renderMathProgressSnapshot();
  }

  // 레거시 난이도 조절 패널 및 미리보기 (수학에서는 숨김, 타 과목에서만 노출)
  const diffPanel = document.getElementById('difficulty-control-panel');
  if (diffPanel) diffPanel.style.display = (sub === 'math') ? 'none' : 'block';
  const previewSection = document.getElementById('preview-section');
  if (previewSection) previewSection.style.display = (sub === 'math') ? 'none' : 'block';

  // 주간 단어 섹션 노출 제어 (영어만)
  const wwSection = document.getElementById('weekly-words-section');
  if (wwSection) wwSection.style.display = (sub === 'english') ? 'block' : 'none';
  if (sub === 'english') loadWeeklyWords();

  // 다른 공용 패널 복구
  const rewardSection = document.getElementById('reward-custom-section');
  if (rewardSection) rewardSection.style.display = 'block';
  const backupSection = document.getElementById('local-backup-section');
  if (backupSection) backupSection.style.display = 'block';
  const growthPanel = document.getElementById('growth-panel');
  if (growthPanel) growthPanel.classList.add('hidden');

  // 탭 라벨 스타일 변환
  document.querySelectorAll('.tab-btn').forEach(b => {
    b.classList.remove('active-tab');
    b.classList.add('inactive-tab');
  });
  const t = document.getElementById(`tab-${sub}`);
  if (t) {
    t.classList.remove('inactive-tab');
    t.classList.add('active-tab');
  }

  // 로컬 스토리지에서 현재 레벨 산출 (수학이 아닐 때만 슬라이더 갱신)
  if (sub !== 'math') {
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
    if (sl) {
      sl.value = baseLevel;
      onSliderChange(baseLevel);
    }
  }
}

// Slider input handler
document.addEventListener('input', (e) => {
  if (e.target.id === 'level-slider' && window.onSliderChange) {
    window.onSliderChange(e.target.value);
  }
});

// ── Event Delegation: data-action → handler mapping ──
document.addEventListener('click', (e) => {
  const target = e.target.closest('[data-action]');
  if (!target) return;
  const action = target.dataset.action;

  switch (action) {
    case 'go-home':
      window.location.href = '../../../index.html';
      e.stopPropagation();
      break;
    case 'set-subject':
      if (window.setSubject) {
        window.setSubject(target.dataset.subject);
      }
      e.stopPropagation();
      break;
    case 'set-math-preset':
      if (window.onSelectMathPreset) {
        window.onSelectMathPreset(target.dataset.preset);
      }
      e.stopPropagation();
      break;
    case 'save-settings':
      if (window.saveSettings) {
        window.saveSettings();
      }
      e.stopPropagation();
      break;
    case 'add-weekly-word':
      if (window.addWeeklyWord) {
        window.addWeeklyWord();
      }
      e.stopPropagation();
      break;
    case 'add-custom-reward':
      if (window.addCustomReward) {
        window.addCustomReward();
      }
      e.stopPropagation();
      break;
    case 'show-growth':
      if (window.showGrowthTab) {
        window.showGrowthTab();
      }
      e.stopPropagation();
      break;
    case 'delete-weekly-word':
      if (window.deleteWeeklyWord) {
        window.deleteWeeklyWord(parseInt(target.dataset.idx, 10));
      }
      e.stopPropagation();
      break;
    case 'export-backup':
      if (window.exportBackup) {
        window.exportBackup();
      }
      e.stopPropagation();
      break;
    case 'import-backup-trigger':
      if (window.importBackupTrigger) {
        window.importBackupTrigger();
      }
      e.stopPropagation();
      break;
    case 'confirm-restore':
      if (window.confirmRestore) {
        window.confirmRestore();
      }
      e.stopPropagation();
      break;
    case 'cancel-restore':
      if (window.cancelRestore) {
        window.cancelRestore();
      }
      e.stopPropagation();
      break;
  }
});

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
      gems: 0, youtube_minutes: 0, snacks: 0, marble_plays: 0, bubble_plays: 0,
      shop_items: [
        { id: 'youtube', icon: '📺', label: '유튜브 10분', desc: '좋아하는 영상 시청', price: 1 },
        { id: 'snack', icon: '🍪', label: '간식 1개', desc: '맛있는 간식 시간', price: 1 },
        { id: 'marble', icon: '🎮', label: '마블 게임', desc: '마블 한 판 더!', price: 1 },
        { id: 'bubble', icon: '🫧', label: '비눗방울 게임', desc: '버블팡 한 판 더!', price: 1 }
      ],
      custom_inventory: {}
    };
  }
  const defaultItems = [
    { id: 'youtube', icon: '📺', label: '유튜브 10분', desc: '좋아하는 영상 시청', price: 1 },
    { id: 'snack', icon: '🍪', label: '간식 1개', desc: '맛있는 간식 시간', price: 1 },
    { id: 'marble', icon: '🎮', label: '마블 게임', desc: '마블 한 판 더!', price: 1 },
    { id: 'bubble', icon: '🫧', label: '비눗방울 게임', desc: '버블팡 한 판 더!', price: 1 }
  ];
  if (!rewardState.shop_items) {
    rewardState.shop_items = [...defaultItems];
  } else {
    defaultItems.forEach(item => {
      if (!rewardState.shop_items.some(i => i.id === item.id)) {
        rewardState.shop_items.push({ ...item });
      }
    });
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
    else if (item.id === 'bubble') invCount = (rewardState.bubble_plays || 0) + '회';
    else invCount = (rewardState.custom_inventory[item.id] || 0) + '개';

    const div = document.createElement('div');
    div.className = 'flex items-center justify-between bg-white p-3 rounded-xl border border-gray-100 shadow-sm gap-2';

    const left = document.createElement('div');
    left.className = 'flex items-center gap-3 min-w-0 flex-1';
    const iconEl = document.createElement('button');
    iconEl.type = 'button';
    iconEl.className = 'text-2xl flex-shrink-0 cursor-pointer hover:opacity-80 rounded leading-none p-0 border-0 bg-transparent';
    iconEl.title = '아이콘·이름 등 편집';
    iconEl.setAttribute('aria-label', '보상 편집');
    iconEl.textContent = item.icon || '🎁';
    iconEl.addEventListener('click', () => openEditReward(item.id));
    const textWrap = document.createElement('div');
    textWrap.className = 'min-w-0';
    const titleEl = document.createElement('div');
    titleEl.className = 'font-bold text-sm text-gray-800 truncate';
    titleEl.textContent = item.label || '';
    const metaEl = document.createElement('div');
    metaEl.className = 'text-xs text-gray-500';
    metaEl.innerHTML = `가격: 💎 ${item.price || 1} | 아이 보유량: <span class="text-blue-600 font-bold">${invCount}</span>`;
    textWrap.append(titleEl, metaEl);
    left.append(iconEl, textWrap);

    const actions = document.createElement('div');
    actions.className = 'flex items-center gap-1 flex-shrink-0';
    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.className = 'text-blue-600 hover:text-blue-800 transition px-2 py-1 text-sm font-bold';
    editBtn.title = '편집';
    editBtn.textContent = '편집';
    editBtn.addEventListener('click', () => openEditReward(item.id));
    const delBtn = document.createElement('button');
    delBtn.type = 'button';
    delBtn.className = 'text-gray-400 hover:text-red-500 transition px-2 py-1';
    delBtn.title = '삭제';
    delBtn.addEventListener('click', () => deleteCustomReward(item.id));
    delBtn.innerHTML = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>';
    actions.append(editBtn, delBtn);

    div.append(left, actions);
    container.appendChild(div);
  });
}

function saveRewards() {
  rewardState._updated_at = Date.now();
  localStorage.setItem('study_rewards', JSON.stringify(rewardState));
  if (window.SyncEngine) window.SyncEngine.pushStats('study_rewards', rewardState);
}

function openEditReward(id) {
  const item = rewardState.shop_items.find(i => i.id === id);
  if (!item) return;

  const existing = document.getElementById('cr-edit-overlay');
  if (existing) existing.remove();

  const overlay = document.createElement('div');
  overlay.id = 'cr-edit-overlay';
  overlay.className = 'fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40';
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) overlay.remove();
  });

  const panel = document.createElement('div');
  panel.className = 'bg-white rounded-2xl shadow-xl max-w-md w-full p-6 space-y-3';
  panel.addEventListener('click', (e) => e.stopPropagation());

  const h = document.createElement('h4');
  h.className = 'font-bold text-gray-900 text-base mb-1';
  h.textContent = '보상 편집 (ID: ' + item.id + ')';

  const hint = document.createElement('p');
  hint.className = 'text-xs text-gray-500 mb-2';
  hint.textContent = '아이콘·이름·설명·가격을 바꿀 수 있습니다. 비워 둔 아이콘은 저장 시 🎁으로 됩니다. 내부 ID는 바꾸지 않습니다.';

  function labeledInput(labelText, inputEl) {
    const wrap = document.createElement('div');
    const lb = document.createElement('label');
    lb.className = 'block text-xs font-semibold text-gray-600 mb-1';
    lb.textContent = labelText;
    wrap.append(lb, inputEl);
    return wrap;
  }

  const iconIn = document.createElement('input');
  iconIn.type = 'text';
  iconIn.className = 'w-full px-3 py-2 border border-gray-200 rounded-lg text-lg text-center';
  iconIn.placeholder = '이모지 입력 (비우면 🎁)';
  iconIn.value = item.icon || '';
  iconIn.setAttribute('aria-describedby', 'cr-edit-icon-hint');

  const iconHint = document.createElement('p');
  iconHint.id = 'cr-edit-icon-hint';
  iconHint.className = 'text-xs text-gray-400 mt-1';
  const kbdWin = document.createElement('kbd');
  kbdWin.className = 'px-1 py-0.5 rounded bg-gray-200 text-gray-800 font-sans text-[0.7rem]';
  kbdWin.textContent = 'Win';
  const kbdDot = document.createElement('kbd');
  kbdDot.className = 'px-1 py-0.5 rounded bg-gray-200 text-gray-800 font-sans text-[0.7rem]';
  kbdDot.textContent = '.';
  iconHint.append('Windows: ', kbdWin, ' + ', kbdDot, ' 를 누르면 이모지 패널이 열립니다.');

  const labelIn = document.createElement('input');
  labelIn.type = 'text';
  labelIn.className = 'w-full px-3 py-2 border border-gray-200 rounded-lg text-sm';
  labelIn.placeholder = '보상 이름';
  labelIn.value = item.label || '';

  const descIn = document.createElement('input');
  descIn.type = 'text';
  descIn.className = 'w-full px-3 py-2 border border-gray-200 rounded-lg text-sm';
  descIn.placeholder = '상세 설명 (선택)';
  descIn.value = item.desc || '';

  const priceIn = document.createElement('input');
  priceIn.type = 'number';
  priceIn.min = '1';
  priceIn.className = 'w-24 px-2 py-2 border border-gray-200 rounded-lg text-sm text-center';
  priceIn.value = String(item.price || 1);

  const btnRow = document.createElement('div');
  btnRow.className = 'flex gap-2 justify-end pt-3';

  const cancelBtn = document.createElement('button');
  cancelBtn.type = 'button';
  cancelBtn.className = 'px-4 py-2 rounded-lg border border-gray-200 text-gray-700 text-sm font-medium hover:bg-gray-50';
  cancelBtn.textContent = '취소';
  cancelBtn.addEventListener('click', () => overlay.remove());

  const saveBtn = document.createElement('button');
  saveBtn.type = 'button';
  saveBtn.className = 'px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-bold hover:bg-blue-700';
  saveBtn.textContent = '저장';
  saveBtn.addEventListener('click', () => {
    let icon = iconIn.value.trim();
    if (!icon) icon = '🎁';
    const label = labelIn.value.trim();
    const desc = descIn.value.trim();
    const price = parseInt(priceIn.value, 10);
    if (!label || isNaN(price) || price < 1) {
      alert('이름과 유효한 가격을 입력해주세요.');
      return;
    }
    item.icon = icon;
    item.label = label;
    item.desc = desc;
    item.price = price;
    saveRewards();
    renderRewardList();
    overlay.remove();
  });

  btnRow.append(cancelBtn, saveBtn);
  const iconField = labeledInput('아이콘', iconIn);
  iconField.appendChild(iconHint);
  panel.append(
    h, hint,
    iconField,
    labeledInput('이름', labelIn),
    labeledInput('설명', descIn),
    labeledInput('가격 (보석)', priceIn),
    btnRow
  );
  overlay.appendChild(panel);
  document.body.appendChild(overlay);
  iconIn.focus();
}

function addCustomReward() {
  const iconRaw = document.getElementById('cr-icon').value.trim();
  const icon = iconRaw || '🎁';
  const label = document.getElementById('cr-label').value.trim();
  const desc = document.getElementById('cr-desc').value.trim();
  const price = parseInt(document.getElementById('cr-price').value, 10);
  
  if (!label || isNaN(price) || price < 1) {
    alert('이름과 유효한 가격을 입력해주세요.');
    return;
  }
  
  const id = 'custom_' + Date.now();
  rewardState.shop_items.push({ id, icon, label, desc, price });
  saveRewards();
  renderRewardList();
  
  document.getElementById('cr-icon').value = '🎁';
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
// ──────────────────────────────────────────
// 영어 주간 시험 단어 관리 (Weekly Words)
// ──────────────────────────────────────────
let weeklyWords = [];
function loadWeeklyWords() {
  const saved = localStorage.getItem('englishWeeklyWords');
  weeklyWords = saved ? JSON.parse(saved) : [];
  renderWeeklyWords();
}
function saveWeeklyWords() {
  localStorage.setItem('englishWeeklyWords', JSON.stringify(weeklyWords));
  if (window.SyncEngine) window.SyncEngine.pushStats('englishWeeklyWords', weeklyWords);
}
function renderWeeklyWords() {
  const container = document.getElementById('ww-list');
  if (!container) return;
  if (weeklyWords.length === 0) {
    container.innerHTML = '<div class="text-center py-4 text-xs text-gray-400 italic">추가된 단어가 없습니다.</div>';
    return;
  }
  container.innerHTML = weeklyWords.map((w, idx) => `
    <div class="flex items-center justify-between bg-blue-50/50 p-2.5 rounded-xl border border-blue-100/50">
      <div class="flex items-center gap-3 min-w-0">
        ${w.icon ? `<span class="text-lg shrink-0">${w.icon}</span>` : ''}
        <div class="min-w-0">
          <div class="font-bold text-sm text-blue-900 truncate">${w.en}</div>
          <div class="text-[10px] text-blue-600 truncate">${w.ko}</div>
        </div>
      </div>
      <button data-action="delete-weekly-word" data-idx="${idx}" class="text-gray-400 hover:text-red-500 transition p-1">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
      </button>
    </div>
  `).join('');
}
function resolveWeeklyWord(rawInput, wordsCatalog) {
  if (typeof rawInput !== 'string') return null;
  var normalized = rawInput.trim().normalize('NFKC').toLowerCase();
  if (!normalized) return null;
  if (!/^[a-z]+(?:[-'][a-z]+)*$/.test(normalized)) return null;
  var categories = Object.keys(wordsCatalog);
  for (var c = 0; c < categories.length; c++) {
    var words = wordsCatalog[categories[c]].words;
    for (var i = 0; i < words.length; i++) {
      if (words[i][0] === normalized) {
        return { en: words[i][0], ko: words[i][1], icon: words[i][2] };
      }
    }
  }
  return null;
}
function addWeeklyWord() {
  var rawEn = document.getElementById('ww-en').value;
  var resolved = resolveWeeklyWord(rawEn, window.WORDS || {});
  if (!resolved) {
    alert('게임 단어 사전에 없는 단어입니다.');
    return;
  }
  var normalized = resolved.en;
  var isDuplicate = weeklyWords.some(function(w) { return w.en === normalized; });
  if (isDuplicate) {
    alert('이미 등록된 단어입니다.');
    return;
  }
  weeklyWords.push({ en: resolved.en, ko: resolved.ko, icon: resolved.icon });
  saveWeeklyWords(); renderWeeklyWords();
  document.getElementById('ww-en').value = '';
}
function deleteWeeklyWord(idx) {
  if (confirm('이 단어를 주간 시험 목록에서 삭제할까요?')) {
    weeklyWords.splice(idx, 1); saveWeeklyWords(); renderWeeklyWords();
  }
}

// ──────────────────────────────────────────
// 주간 성장 요약 (Weekly Growth Summary)
// ──────────────────────────────────────────
function showGrowthTab() {
  // Hide subject panels, show growth panel
  const mathSection = document.getElementById('math-progress-snapshot-section');
  if (mathSection) mathSection.style.display = 'none';
  const presetsSection = document.getElementById('math-daily-goal-presets-section');
  if (presetsSection) presetsSection.style.display = 'none';
  const diffPanel = document.getElementById('difficulty-control-panel');
  if (diffPanel) diffPanel.style.display = 'none';
  const previewSection = document.getElementById('preview-section');
  if (previewSection) previewSection.style.display = 'none';
  document.getElementById('weekly-words-section').style.display = 'none';
  document.getElementById('reward-custom-section').style.display = 'none';
  const backupSection = document.getElementById('local-backup-section');
  if (backupSection) backupSection.style.display = 'block';
  document.getElementById('growth-panel').classList.remove('hidden');

  // Update tab styles
  document.querySelectorAll('.tab-btn').forEach(b => {
    b.classList.remove('active-tab');
    b.classList.add('inactive-tab');
  });
  document.getElementById('tab-growth').classList.remove('inactive-tab');
  document.getElementById('tab-growth').classList.add('active-tab');

  renderGrowthSummary();
}

function renderGrowthSummary() {
  const loading = document.getElementById('growth-loading');
  const content = document.getElementById('growth-content');
  loading.style.display = 'block';
  content.classList.add('hidden');

  setTimeout(() => {
    try {
      let summary;
      if (typeof GrowthVisualizer !== 'undefined' && GrowthVisualizer.getWeeklySummary) {
        summary = GrowthVisualizer.getWeeklySummary();
      } else {
        summary = loadAndComputeWeeklySummary();
      }

      if (!summary) {
        loading.textContent = '아직 학습 기록이 없습니다.';
        return;
      }

      loading.style.display = 'none';
      content.classList.remove('hidden');

      renderGrowthCards(summary);
      renderWeeklyTotal(summary);
      renderInsights(summary);
    } catch (e) {
      console.error('[Guardian] Growth summary error:', e);
      loading.textContent = '데이터를 불러오는 중 오류가 발생했습니다.';
    }
  }, 100);
}

function loadAndComputeWeeklySummary() {
  const logRaw = localStorage.getItem('aiden_session_log');
  if (!logRaw) return null;

  try {
    const log = JSON.parse(logRaw);
    const subjects = ['math', 'english', 'korean', 'science'];

    const now = new Date();
    now.setHours(23, 59, 59, 999);
    const thisWeekStart = new Date(now);
    thisWeekStart.setDate(now.getDate() - now.getDay());
    thisWeekStart.setHours(0, 0, 0, 0);

    const lastWeekStart = new Date(thisWeekStart);
    lastWeekStart.setDate(thisWeekStart.getDate() - 7);

    const summary = {};
    for (const subject of subjects) {
      const allSessions = [];
      for (const date of Object.keys(log)) {
        for (const entry of log[date]) {
          if (entry.subject === subject) allSessions.push(entry);
        }
      }

      const thisWeekSessions = allSessions.filter(e => new Date(e.time) >= thisWeekStart);
      const lastWeekSessions = allSessions.filter(e => {
        const d = new Date(e.time);
        return d >= lastWeekStart && d < thisWeekStart;
      });

      const thisWeekCorrect = thisWeekSessions.reduce((s, e) => s + e.correct, 0);
      const thisWeekTotal = thisWeekSessions.reduce((s, e) => s + e.total, 0);
      const lastWeekCorrect = lastWeekSessions.reduce((s, e) => s + e.correct, 0);

      summary[subject] = {
        thisWeekSessions: thisWeekSessions.length,
        lastWeekSessions: lastWeekSessions.length,
        sessionChange: thisWeekSessions.length - lastWeekSessions.length,
        thisWeekCorrect,
        thisWeekTotal,
        lastWeekCorrect,
        correctChange: thisWeekCorrect - lastWeekCorrect,
        avgAccuracy: thisWeekTotal > 0 ? Math.round((thisWeekCorrect / thisWeekTotal) * 100) : 0,
      };
    }

    return summary;
  } catch (e) {
    console.error('[Guardian] Failed to parse session log:', e);
    return null;
  }
}

const SUBJECT_ICONS = { math: '🔢', english: '📚', korean: '📖', science: '🔬' };
const SUBJECT_NAMES = { math: '수학', english: '영어', korean: '국어', science: '과학' };

function renderGrowthCards(summary) {
  const container = document.getElementById('growth-summary-cards');
  container.innerHTML = '';

  for (const subject of ['math', 'english', 'korean', 'science']) {
    const data = summary[subject];
    if (!data) continue;

    const changeIcon = data.sessionChange > 0 ? '📈' : data.sessionChange < 0 ? '→' : '—';
    const changeText = data.sessionChange > 0 ? `+${data.sessionChange}세션` : data.sessionChange < 0 ? `${data.sessionChange}세션` : '→세션';

    const card = document.createElement('div');
    card.className = 'flex items-center justify-between bg-gray-50 rounded-xl p-4';
    card.innerHTML = `
      <div class="flex items-center gap-3">
        <span class="text-xl">${SUBJECT_ICONS[subject]}</span>
        <span class="font-bold text-gray-800">${SUBJECT_NAMES[subject]}</span>
      </div>
      <div class="flex items-center gap-4 text-sm">
        <span class="font-bold text-gray-700">${changeText}</span>
        <span class="text-gray-600">${data.avgAccuracy}% 정확도</span>
      </div>
    `;
    container.appendChild(card);
  }
}

function renderWeeklyTotal(summary) {
  const container = document.getElementById('growth-weekly-total');
  let totalSessions = 0;
  let totalCorrect = 0;
  let totalQuestions = 0;
  let lastWeekCorrect = 0;

  for (const subject of ['math', 'english', 'korean', 'science']) {
    const data = summary[subject];
    if (!data) continue;
    totalSessions += data.thisWeekSessions;
    totalCorrect += data.thisWeekCorrect;
    totalQuestions += data.thisWeekTotal;
    lastWeekCorrect += data.lastWeekCorrect;
  }

  const correctChange = totalCorrect - lastWeekCorrect;
  const changeText = correctChange > 0 ? `+${correctChange}문제` : `${correctChange}문제`;

  container.innerHTML = `
    <div class="flex items-center justify-between">
      <span class="font-bold text-gray-800">이번 주 총 학습</span>
      <span class="text-lg font-black text-blue-600">${totalSessions}세션, ${totalQuestions}문제</span>
    </div>
    <div class="flex items-center justify-between mt-2">
      <span class="text-sm text-gray-600">전주 대비 정답</span>
      <span class="text-sm font-bold ${correctChange >= 0 ? 'text-green-600' : 'text-red-500'}">${changeText}</span>
    </div>
  `;
}

function renderInsights(summary) {
  const container = document.getElementById('growth-insights');
  container.innerHTML = '';

  let strongest = null, strongestAcc = 0;
  let weakest = null, weakestAcc = 101;

  for (const subject of ['math', 'english', 'korean', 'science']) {
    const data = summary[subject];
    if (!data || data.thisWeekTotal === 0) continue;

    if (data.avgAccuracy > strongestAcc) {
      strongestAcc = data.avgAccuracy;
      strongest = subject;
    }
    if (data.avgAccuracy < weakestAcc) {
      weakestAcc = data.avgAccuracy;
      weakest = subject;
    }
  }

  if (strongest) {
    const div = document.createElement('div');
    div.className = 'flex items-center gap-2 text-sm bg-green-50 rounded-lg px-3 py-2';
    div.innerHTML = `<span>💪</span><span class="text-green-700">가장 강한 과목: ${SUBJECT_NAMES[strongest]} (${strongestAcc}% 정확도)</span>`;
    container.appendChild(div);
  }

  if (weakest && weakest !== strongest) {
    const div = document.createElement('div');
    div.className = 'flex items-center gap-2 text-sm bg-orange-50 rounded-lg px-3 py-2';
    div.innerHTML = `<span>📚</span><span class="text-orange-700">성장 필요 과목: ${SUBJECT_NAMES[weakest]} (${weakestAcc}% 정확도)</span>`;
    container.appendChild(div);
  }

  if (!strongest) {
    const div = document.createElement('div');
    div.className = 'text-sm text-gray-400 text-center py-2';
    div.textContent = '아직 학습 기록이 부족합니다. 열심히 공부해보세요!';
    container.appendChild(div);
  }
}

// ──────────────────────────────────────────
// 수학 보호자 학습 진도 스냅샷 (Math Guardian Progress Snapshot)
// ──────────────────────────────────────────

function escapeHtml(str) {
  if (typeof str !== 'string') return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

const STATUS_BADGE_CLASSES = {
  MASTERED: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  NEEDS_REVIEW: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
  STRUGGLING: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  PRACTICING: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  NOT_STARTED: 'bg-slate-700/30 text-slate-400 border-white/10',
};

function renderMathProgressSnapshot() {
  const container = document.getElementById('math-progress-snapshot-section');
  if (!container) return;

  let evidenceList = [];
  let skillCatalog = {};
  let skillOrder = [];
  let masteryMap = {};
  let dailyGoal = null;
  let streakState = null;
  const now = Date.now();

  try {
    if (window.MathEvidenceStore && typeof window.MathEvidenceStore.getEvidenceList === 'function') {
      evidenceList = window.MathEvidenceStore.getEvidenceList();
    }
    if (window.MathSkills) {
      skillCatalog = window.MathSkills.MATH_SKILLS || {};
      skillOrder = window.MathSkills.MATH_SKILL_ORDER || Object.keys(skillCatalog);
    }
    if (window.MathMasteryEngine && typeof window.MathMasteryEngine.computeAllSkillsMastery === 'function') {
      masteryMap = window.MathMasteryEngine.computeAllSkillsMastery(skillOrder, evidenceList, now);
    }
    if (window.MathDailyGoalEngine) {
      if (typeof window.MathDailyGoalEngine.loadDailyGoal === 'function') {
        dailyGoal = window.MathDailyGoalEngine.loadDailyGoal();
      }
      if (typeof window.MathDailyGoalEngine.initOrGetStreak === 'function') {
        streakState = window.MathDailyGoalEngine.initOrGetStreak({ now: now });
      } else if (typeof window.MathDailyGoalEngine.loadStreak === 'function') {
        streakState = window.MathDailyGoalEngine.loadStreak();
      }
    }
  } catch (err) {
    console.warn('[Guardian] Failed to read canonical math state:', err);
  }

  let snapshot = null;
  if (window.MathGuardianSummary && typeof window.MathGuardianSummary.buildGuardianMathSnapshot === 'function') {
    snapshot = window.MathGuardianSummary.buildGuardianMathSnapshot({
      skillCatalog: skillCatalog,
      skillOrder: skillOrder,
      evidenceList: evidenceList,
      masteryMap: masteryMap,
      dailyGoal: dailyGoal,
      streakState: streakState,
      now: now,
    });
  }

  if (!snapshot) {
    container.innerHTML = `
      <div class="bg-[#0e1422]/90 backdrop-blur-xl rounded-2xl p-6 shadow-2xl border border-white/10 text-center text-xs text-slate-400">
        진도 데이터를 불러올 수 없습니다.
      </div>
    `;
    return;
  }

  let html = '';

  // 1. 헤더
  html += `
    <div class="flex items-center justify-between">
      <h3 class="text-base font-extrabold text-white flex items-center gap-2">
        <span class="text-lg">📈</span>
        <span>수학 학습 진도 스냅샷</span>
      </h3>
      <span class="text-xs px-2.5 py-1 rounded-full bg-[#d7ff00]/10 text-[#d7ff00] font-bold border border-[#d7ff00]/20">
        보호자 전용 진도표
      </span>
    </div>
  `;

  // 2. 오늘의 목표 카드 (Today's Goal Card) + 연속 학습 스트릭 (Streak Card)
  const todayGoal = snapshot.todayGoal;
  const streakInfo = snapshot.streak || { currentStreak: 0, todayStatusText: '아직 시작 전' };
  html += `
    <div class="bg-[#0e1422]/90 backdrop-blur-xl rounded-2xl p-5 shadow-2xl border border-white/10">
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <span class="text-lg">🎯</span>
          <span class="text-xs font-bold text-slate-300 uppercase tracking-wider">오늘의 수학 목표</span>
        </div>
        ${todayGoal.hasGoal ? (
          todayGoal.completed
            ? '<span class="px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-black">오늘 목표 완료 ✓</span>'
            : '<span class="px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-bold">도전 중</span>'
        ) : (
          '<span class="px-2.5 py-0.5 rounded-full bg-white/10 text-slate-400 text-xs font-medium">목표 미설정</span>'
        )}
      </div>
      <div class="text-base font-extrabold text-white mb-2">
        ${escapeHtml(todayGoal.skillName)}
      </div>
      ${todayGoal.hasGoal ? `
        <div class="flex items-center justify-between text-xs text-slate-400 mb-2 font-medium">
          <span>목표 진행도</span>
          <span class="font-mono font-bold text-white">${todayGoal.currentCount} / ${todayGoal.targetCount} 완료</span>
        </div>
        <div class="w-full bg-black/40 rounded-full h-2 overflow-hidden border border-white/10">
          <div class="bg-[#d7ff00] h-full rounded-full transition-all duration-300" style="width: ${todayGoal.progressPercent}%;"></div>
        </div>
      ` : `
        <p class="text-xs text-slate-400 leading-relaxed">
          아이가 수학 놀이를 시작하면 오늘의 맞춤형 스킬 목표가 자동으로 추천됩니다.
        </p>
      `}
      <div class="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-xs">
        <div class="flex items-center gap-1.5 text-slate-300">
          <span class="text-sm">🔥</span>
          <span class="font-bold text-slate-400">연속 학습:</span>
          <span class="font-mono font-bold text-[#d7ff00] text-sm" id="guardian-math-streak-val">${streakInfo.currentStreak}일</span>
        </div>
        <div class="text-slate-400">
          오늘: <span class="font-medium text-slate-200" id="guardian-math-streak-status">${escapeHtml(streakInfo.todayStatusText)}</span>
        </div>
      </div>
    </div>
  `;

  // 3. 빈 상태인 경우 (Empty State)
  if (snapshot.isEmpty) {
    html += `
      <div class="bg-[#0e1422]/90 backdrop-blur-xl rounded-2xl p-6 shadow-2xl border border-white/10 text-center">
        <div class="text-4xl mb-3">🌱</div>
        <h4 class="text-sm font-bold text-white mb-1">아직 기록된 수학 학습 증거가 없습니다</h4>
        <p class="text-xs text-slate-400 leading-relaxed max-w-md mx-auto">
          아이가 수학 놀이에서 문제를 풀기 시작하면, 여기에 실제 학습 결과, 취약점 분석, 복습 시점 안내 및 풀이 변화가 나타납니다.
        </p>
      </div>
    `;
    container.innerHTML = html;
    return;
  }

  // 4. 지금 살펴볼 스킬 (Attention Priority Cards)
  if (snapshot.attentionSkills && snapshot.attentionSkills.length > 0) {
    let attentionCardsHtml = '';
    for (const skill of snapshot.attentionSkills) {
      const badgeClass = STATUS_BADGE_CLASSES[skill.status] || STATUS_BADGE_CLASSES.PRACTICING;
      const rankIcon = skill.status === 'STRUGGLING' ? '🚨' : (skill.status === 'NEEDS_REVIEW' ? '🔄' : '⚡');

      attentionCardsHtml += `
        <div class="bg-white/5 border border-white/10 rounded-xl p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div class="flex-1">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-sm">${rankIcon}</span>
              <span class="text-sm font-bold text-white">${escapeHtml(skill.name)}</span>
              <span class="text-[10px] px-2 py-0.5 rounded-full border font-bold ${badgeClass}">
                ${escapeHtml(skill.statusLabel)}
              </span>
            </div>
            <p class="text-xs text-slate-300 font-medium">
              ${escapeHtml(skill.growthSummary)}
            </p>
          </div>
          <div class="text-right shrink-0">
            <div class="text-xs text-slate-400">최근 결과</div>
            <div class="text-sm font-mono font-bold text-[#d7ff00]">
              ${skill.recentCorrect} / ${skill.recentAttempts} 정답
            </div>
          </div>
        </div>
      `;
    }

    html += `
      <div class="bg-[#0e1422]/90 backdrop-blur-xl rounded-2xl p-5 shadow-2xl border border-amber-500/20">
        <div class="flex items-center gap-2 mb-3">
          <span class="text-base">⚠️</span>
          <h4 class="text-xs font-bold text-amber-400 uppercase tracking-wider">지금 살펴볼 스킬 (집중 필요)</h4>
        </div>
        <div class="space-y-2.5">
          ${attentionCardsHtml}
        </div>
      </div>
    `;
  }

  // 5. 잘하고 있는 스킬 (Mastered Strengths)
  if (snapshot.masteredSkills && snapshot.masteredSkills.length > 0) {
    let masteredTagsHtml = '';
    for (const skill of snapshot.masteredSkills) {
      masteredTagsHtml += `
        <div class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 text-xs font-bold">
          <span>✨</span>
          <span>${escapeHtml(skill.shortName)}</span>
          <span class="text-[10px] opacity-75 font-mono">(${skill.totalAttempts}회 완료)</span>
        </div>
      `;
    }

    html += `
      <div class="bg-[#0e1422]/90 backdrop-blur-xl rounded-2xl p-5 shadow-2xl border border-emerald-500/20">
        <div class="flex items-center gap-2 mb-3">
          <span class="text-base">🌟</span>
          <h4 class="text-xs font-bold text-emerald-400 uppercase tracking-wider">잘하고 있어요 (숙달 완료)</h4>
        </div>
        <div class="flex flex-wrap gap-2">
          ${masteredTagsHtml}
        </div>
      </div>
    `;
  }

  // 6. 스킬별 상세 학습 현황 목록
  let allSkillsHtml = '';
  for (const skill of snapshot.skillSnapshots) {
    const badgeClass = STATUS_BADGE_CLASSES[skill.status] || STATUS_BADGE_CLASSES.NOT_STARTED;
    const trendIcon = skill.trend === 'improved' ? '📈' : (skill.trend === 'declined' ? '📉' : (skill.trend === 'maintained' ? '➡️' : ''));

    allSkillsHtml += `
      <div class="bg-white/5 border border-white/10 rounded-xl p-3.5 transition-all hover:bg-white/[0.07]">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
          <div class="flex items-center gap-2">
            <span class="text-sm font-bold text-white">${escapeHtml(skill.name)}</span>
            <span class="text-[10px] px-2 py-0.5 rounded-full border font-bold ${badgeClass}">
              ${escapeHtml(skill.statusLabel)}
            </span>
          </div>
          <div class="flex items-center gap-2 text-[11px] text-slate-400 font-mono">
            ${skill.curriculumRef ? `<span class="bg-black/30 px-1.5 py-0.5 rounded">${escapeHtml(skill.curriculumRef)}</span>` : ''}
            <span>총 ${skill.totalAttempts}회 시도</span>
          </div>
        </div>

        <div class="flex flex-col sm:flex-row sm:items-center justify-between text-xs text-slate-300 gap-1 bg-black/20 p-2.5 rounded-lg border border-white/5">
          <div>
            <span class="text-slate-400">최근 풀이:</span>
            <span class="font-bold text-white ml-1 font-mono">${skill.recentAttempts > 0 ? `${skill.recentCorrect} / ${skill.recentAttempts} 정답` : '기록 없음'}</span>
          </div>
          <div class="text-xs text-slate-300">
            ${skill.hasPreviousComparison ? `
              <span class="text-slate-400">이전 대비:</span>
              <span class="font-bold text-[#d7ff00] ml-1">${escapeHtml(skill.trendText)} ${trendIcon}</span>
              <span class="text-slate-400 font-mono text-[11px] ml-1">(직전 ${skill.previousCorrect}/${skill.previousAttempts})</span>
            ` : `
              <span class="text-slate-400 text-[11px]">${escapeHtml(skill.growthSummary)}</span>
            `}
          </div>
        </div>
      </div>
    `;
  }

  html += `
    <div class="bg-[#0e1422]/90 backdrop-blur-xl rounded-2xl p-5 shadow-2xl border border-white/10">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-2">
          <span class="text-base">📋</span>
          <h4 class="text-xs font-bold text-slate-300 uppercase tracking-wider">교육과정 스킬별 학습 현황</h4>
        </div>
        <span class="text-[11px] text-slate-400 font-medium font-mono">
          ${snapshot.summary.practicedSkillCount} / ${snapshot.summary.totalSkillCount} 스킬 연습
        </span>
      </div>
      <div class="space-y-3">
        ${allSkillsHtml}
      </div>
    </div>
  `;

  container.innerHTML = html;
}

// ──────────────────────────────────────────
// 데이터 백업 및 복원 UI 핸들러 (Local Backup & Restore UI)
// ──────────────────────────────────────────
let pendingRestorePayload = null;

function exportBackup() {
  if (!window.LocalBackupCore || typeof window.LocalBackupCore.createBackupSnapshot !== 'function') {
    alert('백업 모듈을 로드할 수 없습니다.');
    return;
  }

  try {
    const snapshot = window.LocalBackupCore.createBackupSnapshot();
    const now = new Date();
    const dateStr = now.toISOString().split('T')[0];
    const filename = `aidengame-backup-${dateStr}.json`;
    const jsonStr = JSON.stringify(snapshot, null, 2);

    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    const statusMsg = document.getElementById('backup-status-msg');
    if (statusMsg) {
      statusMsg.className = 'mt-4 text-xs font-bold text-[#d7ff00] flex items-center gap-1.5';
      statusMsg.innerHTML = `<span>✓</span><span>백업 파일(${filename})이 저장되었습니다.</span>`;
      statusMsg.classList.remove('hidden');
      setTimeout(() => {
        statusMsg.classList.add('hidden');
      }, 4000);
    }
  } catch (err) {
    console.error('[Guardian] Export backup failed:', err);
    alert('백업 파일 생성 중 오류가 발생했습니다: ' + err.message);
  }
}

function importBackupTrigger() {
  const input = document.getElementById('backup-file-input');
  if (input) {
    input.value = '';
    input.click();
  }
}

function onBackupFileSelected(event) {
  const input = event.target;
  if (!input || !input.files || input.files.length === 0) return;

  const file = input.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function (e) {
    try {
      const content = e.target?.result;
      const parsed = JSON.parse(content);

      if (!window.LocalBackupCore || typeof window.LocalBackupCore.validateBackup !== 'function') {
        alert('백업 검증 모듈이 로드되지 않았습니다.');
        input.value = '';
        return;
      }

      const validation = window.LocalBackupCore.validateBackup(parsed);
      if (!validation.valid) {
        alert('⚠️ 유효하지 않은 백업 파일입니다:\n• ' + validation.errors.join('\n• '));
        input.value = '';
        return;
      }

      pendingRestorePayload = parsed;
      openRestoreModal(validation.summary);
    } catch (parseErr) {
      console.error('[Guardian] JSON parse error on import:', parseErr);
      alert('백업 파일 형식이 올바르지 않습니다 (JSON 파싱 오류).');
      input.value = '';
    }
  };

  reader.onerror = function () {
    alert('파일을 읽는 중 오류가 발생했습니다.');
    input.value = '';
  };

  reader.readAsText(file);
}

function openRestoreModal(summary) {
  const modal = document.getElementById('backup-restore-modal');
  const summaryEl = document.getElementById('restore-modal-summary');
  if (!modal || !summaryEl) return;

  let exportedTimeStr = '알 수 없음';
  if (summary.exportedAt) {
    try {
      exportedTimeStr = new Date(summary.exportedAt).toLocaleString('ko-KR');
    } catch (e) {
      exportedTimeStr = summary.exportedAt;
    }
  }

  summaryEl.innerHTML = `
    <div class="flex justify-between border-b border-white/10 pb-1.5 mb-1.5">
      <span class="text-slate-400">백업 생성 시각:</span>
      <span class="font-bold text-white">${escapeHtml(exportedTimeStr)}</span>
    </div>
    <div class="flex justify-between">
      <span class="text-slate-400">수학 학습 기록:</span>
      <span class="font-bold text-[#d7ff00]">${summary.mathEvidenceCount}건</span>
    </div>
    <div class="flex justify-between">
      <span class="text-slate-400">오늘의 수학 목표:</span>
      <span class="font-bold text-white">${summary.hasDailyGoal ? `${escapeHtml(summary.dailyGoalDate)} 목표` : '없음'}</span>
    </div>
    <div class="flex justify-between">
      <span class="text-slate-400">보석 / 자유시간:</span>
      <span class="font-bold text-white">💎 ${summary.gems}개 / 📺 ${summary.youtubeMinutes}분</span>
    </div>
    <div class="flex justify-between">
      <span class="text-slate-400">수학 연속 학습:</span>
      <span class="font-bold text-white">${summary.hasMathStreak ? `🔥 ${summary.mathCurrentStreak}일` : '기존 유지'}</span>
    </div>
    <div class="flex justify-between">
      <span class="text-slate-400">등록된 보상 개수:</span>
      <span class="font-bold text-white">${summary.rewardItemsCount}개</span>
    </div>
    <div class="flex justify-between">
      <span class="text-slate-400">영어 주간 단어:</span>
      <span class="font-bold text-white">${summary.weeklyWordsCount}개</span>
    </div>
  `;

  modal.classList.remove('hidden');
}

function cancelRestore() {
  pendingRestorePayload = null;
  const modal = document.getElementById('backup-restore-modal');
  if (modal) modal.classList.add('hidden');
  const input = document.getElementById('backup-file-input');
  if (input) input.value = '';
}

function confirmRestore() {
  if (!pendingRestorePayload) {
    cancelRestore();
    return;
  }

  if (!window.LocalBackupCore || typeof window.LocalBackupCore.restoreBackup !== 'function') {
    alert('복원 코어 모듈이 로드되지 않았습니다.');
    cancelRestore();
    return;
  }

  try {
    const result = window.LocalBackupCore.restoreBackup(pendingRestorePayload);
    if (result.success) {
      alert('✓ 백업 데이터 복원이 완료되었습니다. 화면을 새로고침합니다.');
      cancelRestore();
      window.location.reload();
    } else {
      alert('복원 실패:\n' + (result.errors ? result.errors.join('\n') : result.reason));
      cancelRestore();
    }
  } catch (err) {
    console.error('[Guardian] Restore execution failed:', err);
    alert('복원 처리 중 예기치 않은 오류가 발생했습니다: ' + err.message);
    cancelRestore();
  }
}

// ──────────────────────────────────────────
// 수학 하루 목표 프리셋 렌더링 및 선택 핸들러 (Math Goal Presets)
// ──────────────────────────────────────────
const PRESET_ACTIVE_CLASSES = ['bg-[#d7ff00]/15', 'text-[#d7ff00]', 'border-[#d7ff00]/50', 'shadow-[0_0_15px_rgba(215,255,0,0.2)]'];
const PRESET_INACTIVE_CLASSES = ['bg-white/5', 'text-slate-300', 'border-white/10', 'hover:bg-white/10'];

function renderMathGoalPresets() {
  let preference = { presetId: 'standard' };
  if (window.MathDailyGoalEngine && typeof window.MathDailyGoalEngine.loadGoalPreference === 'function') {
    preference = window.MathDailyGoalEngine.loadGoalPreference();
  }
  const currentPresetId = (preference && preference.presetId) ? preference.presetId : 'standard';

  ['light', 'standard', 'challenge'].forEach(presetId => {
    const btn = document.getElementById(`preset-btn-${presetId}`);
    if (!btn) return;

    if (presetId === currentPresetId) {
      btn.classList.add(...PRESET_ACTIVE_CLASSES);
      btn.classList.remove(...PRESET_INACTIVE_CLASSES);
      btn.setAttribute('aria-pressed', 'true');
    } else {
      btn.classList.remove(...PRESET_ACTIVE_CLASSES);
      btn.classList.add(...PRESET_INACTIVE_CLASSES);
      btn.setAttribute('aria-pressed', 'false');
    }
  });
}

function onSelectMathPreset(presetId) {
  if (window.MathDailyGoalEngine && typeof window.MathDailyGoalEngine.saveGoalPreference === 'function') {
    window.MathDailyGoalEngine.saveGoalPreference(presetId);
  }
  renderMathGoalPresets();
}

// 전역 window 노출
window.exportBackup = exportBackup;
window.importBackupTrigger = importBackupTrigger;
window.onBackupFileSelected = onBackupFileSelected;
window.confirmRestore = confirmRestore;
window.cancelRestore = cancelRestore;
window.renderMathGoalPresets = renderMathGoalPresets;
window.onSelectMathPreset = onSelectMathPreset;
