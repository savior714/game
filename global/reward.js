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
    shop_items: [
      { id: 'youtube', icon: '📺', label: '유튜브 15분', desc: '좋아하는 영상 시청', price: 1 },
      { id: 'snack', icon: '🍪', label: '간식 1개', desc: '맛있는 간식 시간', price: 1 },
      { id: 'marble', icon: '🎮', label: '마블 게임', desc: '마블 한 판 더!', price: 1 }
    ],
    custom_inventory: {},
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
        if (!state.shop_items || state.shop_items.length === 0) {
          state.shop_items = [...initialState.shop_items];
        }
        if (!state.custom_inventory) state.custom_inventory = {};
      } catch (e) {
        console.error('RewardSystem load failed:', e);
      }
    }
  }

  function save() {
    state.last_updated = new Date().toISOString();
    state._updated_at = Date.now();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    if (window.SyncEngine) {
      window.SyncEngine.pushStats(STORAGE_KEY, state);
    }
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
    } else {
      if (!state.custom_inventory[type]) state.custom_inventory[type] = 0;
      state.custom_inventory[type] += amount;
    }
    
    save();
    let typeName = type;
    if (type === 'gems') typeName = '💎 보석';
    else if (type === 'youtube') typeName = '📺 유튜브 시간';
    else if (type === 'snack') typeName = '🍪 간식';
    else if (type === 'marble') typeName = '🎮 마블 게임';
    else {
       const item = state.shop_items.find(i => i.id === type);
       if (item) typeName = `${item.icon} ${item.label}`;
    }

    if (typeof RewardSystemUI !== 'undefined') {
      RewardSystemUI.showToast(`${typeName} 획득!`);
    }
  }

  function has(type, amount = 1) {
    if (type === 'gems') return state.gems >= amount;
    if (type === 'youtube') return state.youtube_minutes >= 15;
    if (type === 'snack') return state.snacks >= amount;
    if (type === 'marble') return state.marble_plays >= amount;
    return (state.custom_inventory[type] || 0) >= amount;
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
    } else {
      const item = state.shop_items.find(i => i.id === type) || { id: type, icon: '🎁', label: '알 수 없는 보상' };
      RewardSystemUI.openCustomModal(item, state);
    }
  }

  // reward_ui.js에서 호출하는 내부 데이터 수정 함수
  function consumeInternal(type, onSuccess) {
    if (type === 'youtube' && state.youtube_minutes >= 15) {
      state.youtube_minutes -= 15;
      save();
      if (typeof RewardSystemUI !== 'undefined') RewardSystemUI.showToast('15분 차감 완료');
      if (onSuccess) onSuccess(state);
    } else if (type !== 'youtube' && state.custom_inventory[type] > 0) {
      state.custom_inventory[type] -= 1;
      save();
      const item = state.shop_items.find(i => i.id === type);
      const label = item ? item.label : '보상';
      if (typeof RewardSystemUI !== 'undefined') RewardSystemUI.showToast(`${label} 1개 사용 완료`);
      if (onSuccess) onSuccess(state);
    }
  }

  function exchangeGem(targetType) {
    const item = state.shop_items.find(i => i.id === targetType);
    const price = item && item.price ? item.price : 1;

    if (state.gems < price) {
      alert(`보석이 부족합니다! (필요: ${price}개)`);
      return;
    }
    
    state.gems -= price;
    if (targetType === 'youtube') state.youtube_minutes += 15;
    else if (targetType === 'snack') state.snacks += 1;
    else if (targetType === 'marble') state.marble_plays += 1;
    else {
      if (!state.custom_inventory[targetType]) state.custom_inventory[targetType] = 0;
      state.custom_inventory[targetType] += 1;
    }
    
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
  let cloudSyncListenerBound = false;

  function refreshFromStorage() {
    load();
    if (typeof RewardSystemUI !== 'undefined') {
      RewardSystemUI.updateUI(state);
      RewardSystemUI.applyBodyTopOffset();
    }
  }

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
    if (!cloudSyncListenerBound) {
      cloudSyncListenerBound = true;
      window.addEventListener('cloud-sync-complete', refreshFromStorage);
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
