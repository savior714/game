/* ═══════════════════════════════════
   전역 보상 인벤토리 시스템 (Reward System Core)
   - localStorage 기반 상태 관리
   - 핵심 비즈니스 로직 (보석 획득, 아이템 교환 등)
   - UI 처리는 reward_ui.js에 위임
   - 2026-03-28: 퇴장 가드 제거 및 UI 분산 리팩토링
   ═══════════════════════════════════ */

const RewardSystem = (() => {
  const STORAGE_KEY = 'study_rewards';
  const initialState = {
    gems: 0,
    youtube_minutes: 0,
    snacks: 0,
    marble_plays: 0,
    theme: 'modern',
    last_updated: new Date().toISOString()
  };

  let state = { ...initialState };

  // ──────────────────────────────────────────
  // 1. 상태 관리 (State Management)
  // ──────────────────────────────────────────
  function load() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        state = { ...initialState, ...JSON.parse(saved) };
      } catch (e) {
        console.error('RewardSystem load failed:', e);
      }
    }
  }

  function save() {
    state.last_updated = new Date().toISOString();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    if (typeof RewardSystemUI !== 'undefined') {
      RewardSystemUI.updateUI(state);
    }
  }

  function setTheme(themeName) {
    state.theme = themeName;
    save();
    window.location.reload(); 
  }

  function add(type, amount = 1) {
    if (type === 'gems') {
      state.gems += amount;
    } else if (type === 'youtube') {
      state.youtube_minutes += (amount * 15);
    } else if (type === 'snack') {
      state.snacks += amount;
    } else if (type === 'marble') {
      state.marble_plays += amount;
    }
    
    save();
    const typeNames = { gems: '💎 보석', youtube: '📺 유튜브 시간', snack: '🍪 간식', marble: '🎮 마블 게임' };
    if (typeof RewardSystemUI !== 'undefined') {
      RewardSystemUI.showToast(`${typeNames[type] || type} 획득!`);
    }
  }

  function has(type, amount = 1) {
    if (type === 'gems') return state.gems >= amount;
    if (type === 'youtube') return state.youtube_minutes >= 15;
    if (type === 'snack') return state.snacks > 0;
    if (type === 'marble') return state.marble_plays > 0;
    return false;
  }

  function consume(type) {
    if (!has(type)) {
      alert('보유 중인 보상이 없습니다.');
      return;
    }
    if (typeof RewardSystemUI === 'undefined') return;

    if (type === 'youtube') {
      RewardSystemUI.openYoutubeModal(state);
    } else if (type === 'snack') {
      state.snacks -= 1;
      save();
      RewardSystemUI.openSnackModal();
    } else if (type === 'marble') {
      state.marble_plays -= 1;
      save();
      RewardSystemUI.openMarbleModal();
    }
  }

  // reward_ui.js에서 호출하는 내부 데이터 수정 함수
  function consumeInternal(type, onSuccess) {
    if (type === 'youtube' && state.youtube_minutes >= 15) {
      state.youtube_minutes -= 15;
      save();
      if (typeof RewardSystemUI !== 'undefined') RewardSystemUI.showToast('15분 차감 완료');
      if (onSuccess) onSuccess(state);
    }
  }

  function exchangeGem(targetType) {
    if (state.gems < 1) {
      alert('보석이 부족합니다!');
      return;
    }
    
    state.gems -= 1;
    if (targetType === 'youtube') state.youtube_minutes += 15;
    else if (targetType === 'snack') state.snacks += 1;
    else if (targetType === 'marble') state.marble_plays += 1;
    
    save();
    if (typeof RewardSystemUI !== 'undefined') {
      RewardSystemUI.showToast('교환 성공! 보관함을 확인하세요.');
      const info = document.querySelector('.shop-inventory-info span');
      if (info) info.textContent = `💎 ${state.gems}개`;
      RewardSystemUI.updateUI(state);
    }
  }

  // ──────────────────────────────────────────
  // 2. 초기화 (Initialization)
  // ──────────────────────────────────────────
  function init() {
    load();
    if (typeof RewardSystemUI !== 'undefined') {
      RewardSystemUI.injectCriticalStyles();
      RewardSystemUI.injectInventoryBar(state);
      RewardSystemUI.injectStyles(state, () => {
        RewardSystemUI.updateUI(state);
        const bar = document.getElementById('reward-inventory');
        if (bar) bar.style.opacity = '1';
        RewardSystemUI.applyBodyTopOffset();
      });
    }
  }

  return { 
    init, add, consume, consumeInternal, exchangeGem,
    getState: () => state, 
    setTheme, 
    openShopModal: () => RewardSystemUI.openShopModal(state),
    playEntranceAndAddGem: (id) => RewardSystemUI.playEntranceAndAddGem(id)
  };
})();

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => RewardSystem.init());
} else {
  RewardSystem.init();
}
