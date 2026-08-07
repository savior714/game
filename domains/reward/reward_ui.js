/* ═══════════════════════════════════
   전역 보상 시스템 UI/UX 모듈 (Reward System UI)
   - 모달, 토스트, 애니메이션 및 시각 효과 전용
   - core 모듈(reward.js)과 연동하여 동작
   - 2026-03-28: reward.js로부터 분리 (500라인 제한 준수)
   ═══════════════════════════════════ */

const RewardSystemUI = (() => {
  let resizeBound = false;
  let authListenerBound = false;
  let cachedGlobalBaseUrl = null;
  let freeTimeAlertAudioContext = null;

  function primeFreeTimeAlertAudio() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      if (!freeTimeAlertAudioContext || freeTimeAlertAudioContext.state === 'closed') {
        freeTimeAlertAudioContext = new AudioCtx();
      }
      if (freeTimeAlertAudioContext && freeTimeAlertAudioContext.state === 'suspended') {
        const res = freeTimeAlertAudioContext.resume();
        if (res && typeof res.catch === 'function') {
          res.catch(() => {});
        }
      }
    } catch (e) {
      // Audio priming is best-effort side effect
    }
  }


  function getGlobalBaseUrl() {
    if (cachedGlobalBaseUrl) return cachedGlobalBaseUrl;

    const script =
      document.currentScript ||
      document.querySelector('script[src*="/domains/reward/reward_ui.js"]') ||
      document.querySelector('script[src$="reward_ui.js"]');

    if (script && script.src) {
      cachedGlobalBaseUrl = new URL('.', script.src);
      return cachedGlobalBaseUrl;
    }

    // Fallback: when script lookup fails, keep previous templates-based default.
    cachedGlobalBaseUrl = new URL('./', window.location.href);
    return cachedGlobalBaseUrl;
  }

  function resolveGlobalAsset(relativePath) {
    return new URL(relativePath, getGlobalBaseUrl()).href;
  }

  function injectCriticalStyles() {
    if (document.getElementById('reward-critical-css')) return;
    const style = document.createElement('style');
    style.id = 'reward-critical-css';
    style.innerHTML = `
      #reward-inventory {
        position: fixed; top: 0; left: 0; width: 100%; z-index: 1000;
        opacity: 0; visibility: visible; display: flex; justify-content: center;
        min-height: 48px; pointer-events: none; transition: opacity 0.4s ease;
      }
      #reward-inventory.ready { opacity: 1; pointer-events: auto; }
      body.reward-loading { overflow: hidden; }

      /* 숙련도 바 스타일 */
      .proficiency-bar-container {
        width: 100%;
        height: 8px;
        background: #e2e8f0;
        border-radius: 4px;
        margin-top: 8px;
        overflow: hidden;
        display: none;
      }
      .proficiency-bar-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.5s ease;
      }

      /* 성장 토스트 스타일 (Blueprint §7.2) */
      .growth-toast {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%) translateY(100px);
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 12px 24px;
        border-radius: 16px;
        font-size: 1.1rem;
        font-weight: bold;
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
        z-index: 5000;
        opacity: 0;
        transition: all 0.4s cubic-bezier(0.2, 0.9, 0.2, 1);
        pointer-events: none;
      }
      .growth-toast.show {
        opacity: 1;
        transform: translateX(-50%) translateY(0);
      }
    `;
    document.head.appendChild(style);
  }

  function injectStyles(state, onLoad) {
    if (document.getElementById('reward-system-css')) {
      if (onLoad) onLoad();
      return;
    }
    const link = document.createElement('link');
    link.id = 'reward-system-css';
    link.rel = 'stylesheet';
    link.href = resolveGlobalAsset('reward.css');
    link.onload = () => {
      if (onLoad) onLoad();
    };
    link.onerror = () => {
      console.warn('[RewardSystemUI] reward.css load failed:', link.href);
      // Keep UI operable even when stylesheet fetch fails.
      if (onLoad) onLoad();
    };
    document.head.appendChild(link);

    // Inject Supabase & Auth scripts
    if (!document.getElementById('supabase-js')) {
      const s1 = document.createElement('script');
      s1.id = 'supabase-js';
      s1.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2';
      s1.onload = () => {
        const s2 = document.createElement('script'); s2.src = resolveGlobalAsset('auth.js');
        const s3 = document.createElement('script'); s3.src = resolveGlobalAsset('sync-engine.js');
        document.head.append(s2, s3);
      };
      document.head.appendChild(s1);
    }

    if (state.theme === 'analog') {
      const analogLink = document.createElement('link');
      analogLink.id = 'reward-system-analog-css';
      analogLink.rel = 'stylesheet';
      analogLink.href = resolveGlobalAsset('reward_analog.css');
      document.head.appendChild(analogLink);
      document.body.classList.add('theme-analog');
    }
  }

  function injectInventoryBar(state) {
    if (document.getElementById('reward-inventory')) return;
    const bar = document.createElement('div');
    bar.id = 'reward-inventory';
    if (state.theme === 'analog') bar.classList.add('theme-analog');
    bar.style.opacity = '0';
    let html = `
      <div class="inventory-content">
        <div class="inventory-rail inventory-rail-left" aria-hidden="true"></div>
        <div class="inventory-center">
        <div class="inventory-left">
        <div class="inventory-item gem-item" data-type="gems" data-action="open-shop-modal" style="display:flex;">
          <span class="icon">💎</span> <span class="val" id="inv-gems">${state.gems}</span><span class="unit">개</span>
        </div>
    `;

    state.shop_items.forEach(item => {
      let unit = '개';
      if (item.id === 'youtube') unit = '분';
      else if (item.id === 'marble') unit = '회';
      
      html += `
        <div class="inventory-item empty-slot" data-type="${item.id}" data-action="consume" data-item-id="${item.id}" style="display:flex;">
          <span class="icon">${item.icon}</span> <span class="val" id="inv-${item.id}">0</span><span class="unit">${unit}</span>
        </div>
      `;
    });

    html += `
        </div>
        </div>
        <div class="inventory-rail inventory-rail-right">
        <div class="inventory-actions">
        <div class="inventory-item inventory-auth" style="cursor:pointer; display:flex;" data-action="auth-toggle">
          <span class="icon">👤</span> <span class="val" id="inv-auth" style="font-size:0.8rem;">로그인</span>
        </div>
        <button type="button" class="inventory-bar-icon-btn" data-action="check-guardian" title="보호자 관리" aria-label="보호자 관리">
          <svg width="22" height="22" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
        </button>
        </div>
        </div>
      </div>
    `;
    bar.innerHTML = html;
    bar.dataset.shopItemsSig = JSON.stringify(state.shop_items || []);
    document.body.prepend(bar);
    applyBodyTopOffset();

    if (!authListenerBound) {
      authListenerBound = true;
      window.addEventListener('auth-changed', (e) => {
        const authLabel = document.getElementById('inv-auth');
        if (authLabel) {
          authLabel.textContent = e.detail.user ? '로그아웃' : '로그인';
        }
      });
    }

    if (!resizeBound) {
      window.addEventListener('resize', applyBodyTopOffset);
      resizeBound = true;
    }
  }

  function applyBodyTopOffset() {
    const bar = document.getElementById('reward-inventory');
    if (!bar || !document.body) return;

    const currentPaddingTop = parseFloat(window.getComputedStyle(document.body).paddingTop) || 0;
    const basePaddingTop = Number(document.body.dataset.basePaddingTop || currentPaddingTop);
    document.body.dataset.basePaddingTop = String(basePaddingTop);

    const barHeight = Math.ceil(bar.getBoundingClientRect().height);
    if (barHeight === 0) return;

    document.body.style.paddingTop = `${basePaddingTop + barHeight}px`;
    document.documentElement.style.setProperty('--reward-bar-height', `${barHeight}px`);
    document.documentElement.style.setProperty('--base-padding-top', `${basePaddingTop}px`);
    bar.classList.add('ready');
  }

  function updateUI(state) {
    const gems = document.getElementById('inv-gems');
    if (gems) gems.textContent = state.gems;

    document.querySelectorAll('#reward-inventory .inventory-item[data-type]').forEach(el => {
      const type = el.dataset.type;
      if (!type) return;

      let count = 0;
      if (type === 'gems') { count = state.gems; }
      else if (type === 'youtube') { count = state.youtube_minutes; }
      else if (type === 'snack') { count = state.snacks; }
      else if (type === 'marble') { count = state.marble_plays; }
      else { count = state.custom_inventory[type] || 0; }

      const valEl = document.getElementById('inv-' + type);
      if (valEl) valEl.textContent = count;

      if (type === 'gems') {
        el.classList.add('has-reward');
        el.classList.remove('empty-slot');
        el.style.display = 'flex';
        return;
      }

      el.style.display = 'flex';
      if (count > 0) {
        el.classList.add('has-reward');
        el.classList.remove('empty-slot');
      } else {
        el.classList.remove('has-reward');
        el.classList.add('empty-slot');
      }
    });
  }

  /** shop_items 변경(항목 추가·삭제·아이콘 등) 시 바 DOM을 상태와 맞춤 */
  function syncInventoryBarWithState(state) {
    const sig = JSON.stringify(state.shop_items || []);
    const bar = document.getElementById('reward-inventory');
    if (bar && bar.dataset.shopItemsSig === sig) return;

    if (bar) bar.remove();
    injectInventoryBar(state);
    const next = document.getElementById('reward-inventory');
    if (next) {
      next.dataset.shopItemsSig = sig;
      next.style.opacity = '1';
      next.classList.add('ready');
      applyBodyTopOffset();
    }
  }

  function playEntranceAndAddGem(sourceElId = 'rp-rocket') {
    const src = document.getElementById(sourceElId);
    const startX = src ? src.getBoundingClientRect().left + src.offsetWidth / 2 : window.innerWidth / 2;
    const startY = src ? src.getBoundingClientRect().top + src.offsetHeight / 2 : window.innerHeight / 2;
    const endX = window.innerWidth / 2;
    const endY = window.innerHeight / 2;

    const el = document.createElement('div');
    el.className = 'reward-center-rocket';
    el.textContent = '🚀';
    el.style.cssText = `
      position:fixed; left:0; top:0; z-index:2000; font-size:2.5rem; pointer-events:none;
      filter: drop-shadow(0 0 15px rgba(255,100,0,0.8));
      transition: transform 1s cubic-bezier(0.2, 0.9, 0.2, 1.05);
      transform: translate(${startX}px, ${startY}px) scale(1);
    `;
    document.body.appendChild(el);

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        el.style.transform = `translate(${endX}px, ${endY}px) scale(1.6) rotate(25deg)`;
      });
    });

    setTimeout(() => {
      spawnExplosion(endX, endY);
      el.remove();
      showGemAwarded(endX, endY);
    }, 1050);
  }

  function showGemAwarded(cx, cy) {
    const overlay = document.createElement('div');
    overlay.className = 'reward-choice-overlay';
    overlay.innerHTML = `
      <div class="reward-choice-modal">
        <div class="icon-bounce" style="font-size:5rem;">💎</div>
        <h3 style="font-size:1.8rem;">보석 획득!</h3>
        <p>축하합니다! 보석 1개를 얻었습니다.</p>
        <p class="sub">보석을 모아 원하는 선물로 바꾸세요!</p>
        <div class="choice-actions">
          <button class="btn-now" data-action="close-overlay">확인</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
    RewardSystem.add('gems', 1);
  }

  function openShopModal(state) {
    if (document.getElementById('reward-shop-overlay')) return;

    const overlay = document.createElement('div');
    overlay.id = 'reward-shop-overlay';
    overlay.className = 'reward-modal-overlay';
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
    
    const shopItems = state.shop_items || [];

    overlay.innerHTML = `
      <div class="reward-modal-content shop-modal">
        <div class="reward-head">
          <h3 style="margin:0; font-size:1.5rem;">💎 보석 상점</h3>
          <p style="margin:5px 0 0; font-size:0.9rem; color:#666;">보석으로 선물을 골라보세요!</p>
        </div>
        <div class="shop-inventory-info" style="margin: 15px 0; padding: 10px; background: #f1f5f9; border-radius: 12px; font-weight: bold;">
          보유 보석: <span style="color:#8b5cf6;">💎 ${state.gems}개</span>
        </div>
        <div class="shop-grid" style="display: grid; gap: 12px; margin: 20px 0; max-height:50vh; overflow-y:auto; padding-right:5px;">
          ${shopItems.map(item => `
            <div class="shop-card" data-action="exchange-gem" data-item-id="${item.id}" style="cursor:pointer; padding:15px; border:2px solid #e2e8f0; border-radius:18px; display:flex; align-items:center; gap:15px; text-align:left; transition:all 0.2s;">
              <div style="font-size:2rem;">${item.icon}</div>
              <div style="flex:1;">
                <div style="font-weight:bold; font-size:1.05rem;">${item.label}</div>
                <div style="font-size:0.8rem; color:#666; word-break:keep-all;">${item.desc}</div>
              </div>
              <div style="background:#8b5cf6; color:white; padding:4px 10px; border-radius:10px; font-size:0.85rem; font-weight:bold; flex-shrink:0;">💎 ${item.price || 1}</div>
            </div>
          `).join('')}
        </div>
        <button class="btn-close" style="width:100%; padding:12px;" data-action="close-overlay">나가기</button>
      </div>
    `;
    document.body.appendChild(overlay);
  }

  function spawnExplosion(cx, cy) {
    const items = ['✨','⚡','🌟','💥','🔥'];
    for (let i = 0; i < 15; i++) {
      setTimeout(() => {
        const angle = i / 15 * Math.PI * 2 + Math.random() * 0.4;
        const dist  = 45 + Math.random() * 70;
        const p = document.createElement('div');
        p.style.cssText = `
          position:fixed; left:${cx}px; top:${cy}px; z-index:3000; pointer-events:none;
          font-size: 1.5rem; transition: all 0.7s cubic-bezier(0.1, 0.5, 0.1, 1);
        `;
        p.textContent = items[Math.floor(Math.random() * items.length)];
        document.body.appendChild(p);
        
        requestAnimationFrame(() => {
          const dx = Math.cos(angle) * dist;
          const dy = Math.sin(angle) * dist;
          p.style.transform = `translate(${dx}px, ${dy}px) scale(0) rotate(${Math.random()*180}deg)`;
          p.style.opacity = '0';
        });
        setTimeout(() => p.remove(), 800);
      }, i * 20);
    }
  }

  function openYoutubeModal(state) {
    const overlay = createModalOverlay('reward-yt-modal');
    overlay.innerHTML = `
      <div class="reward-modal-content">
        <div class="icon-bounce" style="font-size:3rem; margin-bottom:15px;">📺</div>
        <h3>확보된 유튜브 시간</h3>
        <div class="secured-time-display" style="font-size:2.5rem; font-weight:bold; color:#f43f5e; margin:15px 0;">
          ${state.youtube_minutes}분
        </div>
        
        <div id="yt-lock-area" style="margin: 20px 0;">
          <button id="yt-unlock-trigger" style="background:none; border:none; font-size:4rem; cursor:pointer;" title="부모님용 잠금 해제">🔒</button>
          <p class="sub" style="color:#666; font-size:0.8rem;">부모님께서 자물쇠를 눌러 승인해 주세요.</p>
        </div>

        <div id="yt-start-area" style="display:none; margin-top:10px;">
          <button class="btn-primary" id="start-yt-btn" style="background:#f43f5e; border-color:#e11d48; width:100%;">유튜브 자유시간 15분 시작</button>
          <p class="sub" style="color:#666; font-size:0.8rem; margin-top:10px;">
            새 YouTube 탭이 열려요.<br>
            게임 탭을 닫지 않아야 이후 타이머와 종료 알림이 유지돼요.<br>
            일찍 닫아도 사용 시간은 환불되지 않아요.
          </p>
          <div id="yt-result-msg" style="margin-top:10px; font-size:0.9rem; display:none;"></div>
        </div>

        <button class="btn-close" style="margin-top:15px;" data-action="close-overlay">닫기</button>
      </div>
    `;
    document.body.appendChild(overlay);

    const lockTrigger = overlay.querySelector('#yt-unlock-trigger');
    const startArea = overlay.querySelector('#yt-start-area');
    const lockArea   = overlay.querySelector('#yt-lock-area');
    const startBtn  = overlay.querySelector('#start-yt-btn');
    const resultMsg = overlay.querySelector('#yt-result-msg');
    const display   = overlay.querySelector('.secured-time-display');

    lockTrigger.addEventListener('click', () => {
      const n1 = Math.floor(Math.random() * 40) + 11; 
      const n2 = Math.floor(Math.random() * 40) + 11;
      const answer = prompt(`🔒 [부모님 잠금 해제]\n\n계산해 주세요: ${n1} + ${n2} = ?`);
      
      if (String(answer) === String(n1 + n2)) {
        lockArea.style.display = 'none';
        startArea.style.display = 'block';
      } else if (answer !== null) {
        alert('정답이 아닙니다.');
      }
    });

    function showResult(code) {
      resultMsg.style.display = 'block';
      switch (code) {
        case 'started':
          resultMsg.style.color = '#16a34a';
          resultMsg.textContent = '유튜브 자유시간이 시작되었어요! 새 탭을 확인하세요.';
          break;
        case 'already_active':
          resultMsg.style.color = '#d97706';
          resultMsg.textContent = '이미 유튜브 자유시간이 진행 중이에요.';
          break;
        case 'popup_blocked':
          resultMsg.style.color = '#dc2626';
          resultMsg.textContent = '팝업이 차단되었어요. 팝업을 허용한 뒤 다시 눌러 주세요.';
          startBtn.disabled = false;
          break;
        case 'insufficient_time':
          resultMsg.style.color = '#dc2626';
          resultMsg.textContent = '사용할 시간이 부족해요. 현재 남은 시간을 확인하세요.';
          break;
        case 'commit_failed':
        case 'recovery_required':
        case 'corrupt_reward_state':
        case 'corrupt_transaction_journal':
          resultMsg.style.color = '#dc2626';
          resultMsg.textContent = '시작에 실패했어요. 다시 시도하거나 페이지를 새로고침해 주세요.';
          break;
        default:
          resultMsg.style.color = '#dc2626';
          resultMsg.textContent = '알 수 없는 오류가 발생했어요.';
      }
    }

    startBtn.addEventListener('click', () => {
      startBtn.disabled = true;
      resultMsg.style.display = 'none';

      try {
        primeFreeTimeAlertAudio();
      } catch (e) {
        // audio preparation failure must not block session start
      }

      const result = RewardSystem.startYouTubeSession();
      showResult(result.code);

      if (result.code === 'started') {
        display.textContent = `${RewardSystem.getState().youtube_minutes}분`;
        if (RewardSystem.getState().youtube_minutes < 15) {
          setTimeout(() => overlay.remove(), 2000);
        }
      } else if (result.code === 'already_active') {
        startBtn.disabled = false;
      } else if (result.code === 'popup_blocked') {
        startBtn.disabled = false;
      } else if (result.code === 'insufficient_time') {
        display.textContent = `${RewardSystem.getState().youtube_minutes}분`;
        startBtn.disabled = false;
      } else {
        startBtn.disabled = false;
      }
    });
  }

  function openSnackModal(state) {
    const overlay = createModalOverlay('reward-snack-modal');
    const initialCount = state && typeof state.snacks === 'number' ? state.snacks : 0;
    overlay.innerHTML = `
      <div class="reward-modal-content">
        <div class="icon-bounce" style="font-size:3rem; margin-bottom:15px;">🍪</div>
        <h3>확보된 간식</h3>
        <div class="secured-snack-display" style="font-size:2.5rem; font-weight:bold; color:#8b5cf6; margin:15px 0;">
          ${initialCount}개
        </div>
        <p class="sub" style="color:#666; font-size:0.9rem;">과일, 요거트, 또는 좋아하는 과자를 골라 드신 뒤 부모님께서 사용을 기록해 주세요.</p>

        <div id="snack-lock-area" style="margin: 20px 0;">
          <button id="snack-unlock-trigger" style="background:none; border:none; font-size:4rem; cursor:pointer;" title="부모님용 잠금 해제">🔒</button>
          <p class="sub" style="color:#666; font-size:0.8rem;">부모님께서 자물쇠를 눌러 승인해 주세요.</p>
        </div>

        <div id="snack-deduct-area" style="display:none; margin-top:10px;">
          <button class="btn-primary" id="deduct-snack-btn" style="background:#8b5cf6; border-color:#7c3aed; width:100%;">간식 1개 사용 기록하기</button>
        </div>

        <button class="btn-close" style="margin-top:15px;" data-action="close-overlay">닫기</button>
      </div>
    `;
    document.body.appendChild(overlay);

    const lockTrigger = overlay.querySelector('#snack-unlock-trigger');
    const deductArea = overlay.querySelector('#snack-deduct-area');
    const lockArea = overlay.querySelector('#snack-lock-area');
    const deductBtn = overlay.querySelector('#deduct-snack-btn');
    const display = overlay.querySelector('.secured-snack-display');

    lockTrigger.addEventListener('click', () => {
      const n1 = Math.floor(Math.random() * 40) + 11;
      const n2 = Math.floor(Math.random() * 40) + 11;
      const answer = prompt(`🔒 [부모님 잠금 해제]\n\n계산해 주세요: ${n1} + ${n2} = ?`);

      if (String(answer) === String(n1 + n2)) {
        lockArea.style.display = 'none';
        deductArea.style.display = 'block';
      } else if (answer !== null) {
        alert('정답이 아닙니다.');
      }
    });

    deductBtn.addEventListener('click', () => {
      RewardSystem.consumeInternal('snack', (newState) => {
        display.textContent = `${newState.snacks}개`;
        if (newState.snacks < 1) {
          setTimeout(() => overlay.remove(), 400);
        } else {
          lockArea.style.display = 'block';
          deductArea.style.display = 'none';
        }
      });
    });
  }

  function openMarbleModal() {
    const marbleUrl = new URL('../marble/', getGlobalBaseUrl()).href;

    const overlay = createModalOverlay('reward-marble-modal');
    overlay.style.backgroundColor = 'rgba(0,0,0,0.92)';
    overlay.innerHTML = `
      <div class="reward-marble-content">
         <iframe src="${marbleUrl}" style="width:360px; height:560px; border:none; border-radius:20px; box-shadow: 0 10px 40px rgba(0,0,0,0.5);"></iframe>
          <button class="btn-close-marble" data-action="close-overlay">학습으로 돌아가기</button>
      </div>
    `;
    document.body.appendChild(overlay);
    
    window.addEventListener('message', (e) => {
      if (e.data === 'closeMarble') {
        overlay.remove();
      }
    }, { once: true });
  }

  function createModalOverlay(id) {
    const el = document.createElement('div');
    el.className = 'reward-modal-overlay ' + id;
    el.addEventListener('click', (e) => { if (e.target === el) el.remove(); });
    return el;
  }

  function showToast(msg) {
    document.querySelectorAll('.reward-toast').forEach(t => t.remove());

    const toast = document.createElement('div');
    toast.className = 'reward-toast';
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('show');
      setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 500);
      }, 2000);
    }, 50);
  }

  /** 성장 토스트 표시 (Blueprint §7.1) — GrowthVisualizer에서 호출 */
  function showGrowthToast(message) {
    document.querySelectorAll('.growth-toast').forEach(t => t.remove());

    const toast = document.createElement('div');
    toast.className = 'growth-toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    requestAnimationFrame(() => {
      toast.classList.add('show');
    });

    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 500);
    }, 3000);
  }

  function openCustomModal(item, state) {
    const overlay = createModalOverlay('reward-custom-modal');
    overlay.innerHTML = `
      <div class="reward-modal-content">
        <div class="icon-bounce" style="font-size:3.5rem; margin-bottom:15px;">${item.icon}</div>
        <h3 style="font-size:1.6rem;">${item.label}</h3>
        <p style="color:#666; margin-top:5px;">확보 인벤토리: ${state.custom_inventory[item.id] || 0}개</p>
        
        <div style="margin: 25px 0;">
          <button class="btn-primary" id="deduct-custom-btn" style="background:#f43f5e; border-color:#e11d48; width:100%;">
            1개 사용 승인하기 (권장: 부모님)
          </button>
        </div>
        <button class="btn-close" data-action="close-overlay">닫기</button>
      </div>
    `;
    document.body.appendChild(overlay);

    const deductBtn = overlay.querySelector('#deduct-custom-btn');
    deductBtn.addEventListener('click', () => {
      RewardSystem.consumeInternal(item.id, () => {
        overlay.remove();
      });
    });
  }

  // ── Event Delegation: data-action → handler mapping ──
  document.addEventListener('click', (e) => {
    const target = e.target.closest('[data-action]');
    if (!target) return;
    const action = target.dataset.action;
    const itemId = target.dataset.itemId;

    switch (action) {
      case 'open-shop-modal':
        if (typeof RewardSystem !== 'undefined' && RewardSystem.openShopModal) {
          RewardSystem.openShopModal();
        }
        e.stopPropagation();
        break;
      case 'consume':
        if (typeof RewardSystem !== 'undefined' && RewardSystem.consume) {
          RewardSystem.consume(itemId);
        }
        e.stopPropagation();
        break;
      case 'auth-toggle':
        if (window.Auth) {
          if (window.Auth.getUser()) {
            window.Auth.signOut();
          } else {
            window.Auth.signInGoogle();
          }
        }
        e.stopPropagation();
        break;
      case 'check-guardian':
        if (window.checkGuardian) {
          window.checkGuardian();
        }
        e.stopPropagation();
        break;
      case 'exchange-gem':
        if (typeof RewardSystem !== 'undefined' && RewardSystem.exchangeGem) {
          RewardSystem.exchangeGem(itemId);
        }
        e.stopPropagation();
        break;
      case 'close-overlay': {
        const overlay = target.closest('.reward-modal-overlay, .reward-choice-overlay');
        if (overlay) overlay.remove();
        e.stopPropagation();
        break;
      }
    }
  });

  let timerIntervalId = null;

  function formatTimeMMSS(ms) {
    const totalSec = Math.max(0, Math.floor(ms / 1000));
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }

  function triggerAudioAlert() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      let ctx = freeTimeAlertAudioContext;
      if (!ctx || ctx.state === 'closed') {
        ctx = new AudioCtx();
        freeTimeAlertAudioContext = ctx;
      }
      if (ctx.state === 'suspended') {
        const res = ctx.resume();
        if (res && typeof res.catch === 'function') {
          res.catch(() => {});
        }
      }
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
      osc.frequency.setValueAtTime(880, ctx.currentTime + 0.2); // A5
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.5);
    } catch (e) {
      // Audio context blocked or unsupported
    }
  }

  function renderExpiryOverlay(session) {
    if (document.getElementById('yt-expired-overlay')) return;

    const overlay = document.createElement('div');
    overlay.id = 'yt-expired-overlay';
    overlay.style.cssText = `
      position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 10000;
      background: rgba(15, 23, 42, 0.95); display: flex; align-items: center; justify-content: center;
      color: white; font-family: sans-serif; text-align: center; padding: 24px; box-sizing: border-box;
    `;
    overlay.innerHTML = `
      <div style="max-width: 440px; width: 100%; background: #1e293b; border: 3px solid #f43f5e; border-radius: 24px; padding: 32px 24px; box-shadow: 0 20px 50px rgba(244,63,94,0.3);">
        <div style="font-size: 4rem; margin-bottom: 16px; animation: pulse 1s infinite alternate;">⏰</div>
        <h2 style="font-size: 1.8rem; margin: 0 0 12px; color: #f43f5e;">시간이 끝났어요!</h2>
        <p style="font-size: 1.05rem; line-height: 1.6; color: #cbd5e1; margin-bottom: 24px;">
          YouTube 탭을 닫고 게임으로 돌아오세요.
        </p>
        <button id="yt-ack-btn" style="
          width: 100%; padding: 14px; background: #f43f5e; color: white; border: none;
          border-radius: 14px; font-size: 1.1rem; font-weight: bold; cursor: pointer;
          box-shadow: 0 4px 14px rgba(244,63,94,0.4); transition: transform 0.1s;
        ">확인했어요</button>
      </div>
    `;
    document.body.appendChild(overlay);

    triggerAudioAlert();

    const ackBtn = overlay.querySelector('#yt-ack-btn');
    ackBtn.addEventListener('click', () => {
      // Mark acknowledged in storage
      session.status = 'acknowledged';
      session.acknowledgedAt = Date.now();
      try {
        localStorage.setItem('study_youtube_free_time_session_v1', JSON.stringify(session));
      } catch (e) {}

      overlay.remove();
      const timerBar = document.getElementById('youtube-free-time-timer');
      if (timerBar) timerBar.remove();
    });
  }

  function startTimerLoop(session) {
    if (timerIntervalId) clearInterval(timerIntervalId);

    function update() {
      try {
        const raw = localStorage.getItem('study_youtube_free_time_session_v1');
        if (raw) {
          const saved = JSON.parse(raw);
          if (saved && saved.sessionId === session.sessionId) {
            session.endsAt = saved.endsAt || session.endsAt;
            session.deadline = saved.deadline || session.deadline;
          }
        }
      } catch (e) {}

      const deadline = session.endsAt || session.deadline || Date.now();
      const remainingMs = Math.max(0, deadline - Date.now());
      const formatted = formatTimeMMSS(remainingMs);
      const textEl = document.getElementById('yt-timer-text');
      if (textEl) textEl.textContent = formatted;

      const progressEl = document.getElementById('yt-timer-progress');
      if (progressEl && session.durationMs > 0) {
        const pct = Math.min(100, Math.max(0, (remainingMs / session.durationMs) * 100));
        progressEl.style.width = `${pct}%`;
      }

      if (remainingMs <= 0) {
        clearInterval(timerIntervalId);
        timerIntervalId = null;
        if (textEl) textEl.textContent = '00:00';
        session.status = 'expired';
        session.expiredAt = session.expiredAt || Date.now();
        try {
          localStorage.setItem('study_youtube_free_time_session_v1', JSON.stringify(session));
        } catch (e) {}
        renderExpiryOverlay(session);
      }
    }

    update();
    timerIntervalId = setInterval(update, 1000);
  }

  function renderFreeTimeTimerUI(session) {
    if (!session || session.status !== 'running') return;
    const deadline = session.endsAt || session.deadline || Date.now();

    // 1. Try Document Picture-in-Picture if available and requested
    if ('documentPictureInPicture' in window && typeof window.documentPictureInPicture.requestWindow === 'function') {
      try {
        window.documentPictureInPicture.requestWindow({ width: 320, height: 140 }).then((pipWin) => {
          pipWin.document.body.innerHTML = `
            <div style="font-family: sans-serif; padding: 12px; background: #0f172a; color: white; border-radius: 8px; text-align: center;">
              <div style="font-size: 0.9rem; font-weight: bold; color: #f43f5e;">📺 유튜브 자유시간</div>
              <div id="pip-timer-text" style="font-size: 2rem; font-weight: bold; margin: 6px 0;">${formatTimeMMSS(deadline - Date.now())}</div>
              <div style="font-size: 0.75rem; color: #94a3b8;">게임 탭을 닫지 마세요</div>
            </div>
          `;
          const pipInterval = setInterval(() => {
            const rem = Math.max(0, deadline - Date.now());
            const text = pipWin.document.getElementById('pip-timer-text');
            if (text) text.textContent = formatTimeMMSS(rem);
            if (rem <= 0) clearInterval(pipInterval);
          }, 1000);
          pipWin.addEventListener('unload', () => clearInterval(pipInterval));
          return;
        }).catch(() => {
          renderFixedTabTimerBar(session);
        });
        // Still render fixed tab timer bar in case PiP window is backgrounded or fails
        renderFixedTabTimerBar(session);
        return;
      } catch (e) {
        renderFixedTabTimerBar(session);
        return;
      }
    }

    renderFixedTabTimerBar(session);
  }

  function renderFixedTabTimerBar(session) {
    let timerBar = document.getElementById('youtube-free-time-timer');
    if (!timerBar) {
      timerBar = document.createElement('div');
      timerBar.id = 'youtube-free-time-timer';
      timerBar.className = 'youtube-timer-bar';
      timerBar.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; z-index: 9999;
        background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);
        color: white; padding: 8px 16px; display: flex; align-items: center; justify-content: space-between;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3); font-family: sans-serif; font-size: 0.95rem; font-weight: bold;
      `;
      timerBar.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px;">
          <span>📺 유튜브 자유시간</span>
          <div style="width: 120px; height: 6px; background: #334155; border-radius: 3px; overflow: hidden;">
            <div id="yt-timer-progress" style="height: 100%; width: 100%; background: #f43f5e; transition: width 1s linear;"></div>
          </div>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
          <span id="yt-timer-text" style="font-size: 1.2rem; color: #f43f5e; font-variant-numeric: tabular-nums;">--:--</span>
          <span style="font-size: 0.75rem; color: #94a3b8; font-weight: normal;">(게임 탭 유치)</span>
        </div>
      `;
      document.body.prepend(timerBar);
    }
    startTimerLoop(session);
  }

  function renderExpiredFreeTimeSessionUI(session) {
    if (!session || session.status !== 'expired') return;
    renderExpiryOverlay(session);
  }

  return {
    injectCriticalStyles, injectStyles, injectInventoryBar, syncInventoryBarWithState, applyBodyTopOffset, updateUI,
    playEntranceAndAddGem, openShopModal, spawnExplosion, showToast, showGrowthToast,
    openYoutubeModal, openSnackModal, openMarbleModal, openCustomModal, renderFreeTimeTimerUI, renderExpiredFreeTimeSessionUI
  };
})();

(function registerGuardianNav() {
  function guardianPageUrl() {
    const script =
      document.querySelector('script[src*="/domains/reward/reward_ui.js"]') ||
      document.querySelector('script[src$="reward_ui.js"]');
    if (script && script.src) {
      return new URL('../guardian/index.html', new URL('.', script.src)).href;
    }
    return './guardian/index.html';
  }
  window.checkGuardian = function checkGuardian() {
    const url = guardianPageUrl();
    if (window.Auth?.getUser()) {
      window.location.href = url;
      return;
    }
    const a = Math.floor(Math.random() * 8) + 12;
    const b = Math.floor(Math.random() * 8) + 12;
    const ans = prompt(`보호자 확인을 위해 다음 문제를 풀어주세요.\n\n${a} × ${b} = ?`);
    if (ans !== null && parseInt(ans.trim(), 10) === a * b) {
      window.location.href = url;
    } else if (ans !== null) {
      alert('오답입니다. 보호자만 접근할 수 있습니다.');
    }
  };
})();
