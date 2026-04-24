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

  function getGlobalBaseUrl() {
    if (cachedGlobalBaseUrl) return cachedGlobalBaseUrl;

    const script =
      document.currentScript ||
      document.querySelector('script[src*="/global/reward_ui.js"]') ||
      document.querySelector('script[src$="global/reward_ui.js"]');

    if (script && script.src) {
      cachedGlobalBaseUrl = new URL('.', script.src);
      return cachedGlobalBaseUrl;
    }

    // Fallback: when script lookup fails, keep previous templates-based default.
    cachedGlobalBaseUrl = new URL('./global/', window.location.href);
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
        <div class="inventory-item gem-item" data-type="gems" onclick="RewardSystem.openShopModal()" style="display:flex;">
          <span class="icon">💎</span> <span class="val" id="inv-gems">${state.gems}</span><span class="unit">개</span>
        </div>
    `;

    state.shop_items.forEach(item => {
      let unit = '개';
      if (item.id === 'youtube') unit = '분';
      else if (item.id === 'marble') unit = '회';
      
      html += `
        <div class="inventory-item empty-slot" data-type="${item.id}" onclick="RewardSystem.consume('${item.id}')" style="display:flex;">
          <span class="icon">${item.icon}</span> <span class="val" id="inv-${item.id}">0</span><span class="unit">${unit}</span>
        </div>
      `;
    });

    html += `
        </div>
        </div>
        <div class="inventory-rail inventory-rail-right">
        <div class="inventory-actions">
        <div class="inventory-item inventory-auth" style="cursor:pointer; display:flex;" onclick="if(window.Auth?.getUser()) window.Auth.signOut(); else window.Auth?.signInGoogle();">
          <span class="icon">👤</span> <span class="val" id="inv-auth" style="font-size:0.8rem;">로그인</span>
        </div>
        <button type="button" class="inventory-bar-icon-btn" onclick="window.checkGuardian()" title="보호자 관리" aria-label="보호자 관리">
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
          <button class="btn-now" onclick="this.closest('.reward-choice-overlay').remove()">확인</button>
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
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
    
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
            <div class="shop-card" onclick="RewardSystem.exchangeGem('${item.id}')" style="cursor:pointer; padding:15px; border:2px solid #e2e8f0; border-radius:18px; display:flex; align-items:center; gap:15px; text-align:left; transition:all 0.2s;">
              <div style="font-size:2rem;">${item.icon}</div>
              <div style="flex:1;">
                <div style="font-weight:bold; font-size:1.05rem;">${item.label}</div>
                <div style="font-size:0.8rem; color:#666; word-break:keep-all;">${item.desc}</div>
              </div>
              <div style="background:#8b5cf6; color:white; padding:4px 10px; border-radius:10px; font-size:0.85rem; font-weight:bold; flex-shrink:0;">💎 ${item.price || 1}</div>
            </div>
          `).join('')}
        </div>
        <button class="btn-close" style="width:100%; padding:12px;" onclick="this.closest('.reward-modal-overlay').remove()">나가기</button>
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

        <div id="yt-deduct-area" style="display:none; margin-top:10px;">
          <button class="btn-primary" id="deduct-yt-btn" style="background:#f43f5e; border-color:#e11d48; width:100%;">15분 사용 기록하기</button>
        </div>

        <button class="btn-close" style="margin-top:15px;" onclick="this.closest('.reward-modal-overlay').remove()">닫기</button>
      </div>
    `;
    document.body.appendChild(overlay);

    const lockTrigger = overlay.querySelector('#yt-unlock-trigger');
    const deductArea = overlay.querySelector('#yt-deduct-area');
    const lockArea   = overlay.querySelector('#yt-lock-area');
    const deductBtn  = overlay.querySelector('#deduct-yt-btn');
    const display    = overlay.querySelector('.secured-time-display');

    lockTrigger.onclick = () => {
      const n1 = Math.floor(Math.random() * 40) + 11; 
      const n2 = Math.floor(Math.random() * 40) + 11;
      const answer = prompt(`🔒 [부모님 잠금 해제]\n\n계산해 주세요: ${n1} + ${n2} = ?`);
      
      if (String(answer) === String(n1 + n2)) {
        lockArea.style.display = 'none';
        deductArea.style.display = 'block';
      } else if (answer !== null) {
        alert('정답이 아닙니다.');
      }
    };

    deductBtn.onclick = () => {
      RewardSystem.consumeInternal('youtube', (newState) => {
        display.textContent = `${newState.youtube_minutes}분`;
        if (newState.youtube_minutes < 15) {
          setTimeout(() => overlay.remove(), 400);
        } else {
          lockArea.style.display = 'block';
          deductArea.style.display = 'none';
        }
      });
    };
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

        <button class="btn-close" style="margin-top:15px;" onclick="this.closest('.reward-modal-overlay').remove()">닫기</button>
      </div>
    `;
    document.body.appendChild(overlay);

    const lockTrigger = overlay.querySelector('#snack-unlock-trigger');
    const deductArea = overlay.querySelector('#snack-deduct-area');
    const lockArea = overlay.querySelector('#snack-lock-area');
    const deductBtn = overlay.querySelector('#deduct-snack-btn');
    const display = overlay.querySelector('.secured-snack-display');

    lockTrigger.onclick = () => {
      const n1 = Math.floor(Math.random() * 40) + 11;
      const n2 = Math.floor(Math.random() * 40) + 11;
      const answer = prompt(`🔒 [부모님 잠금 해제]\n\n계산해 주세요: ${n1} + ${n2} = ?`);

      if (String(answer) === String(n1 + n2)) {
        lockArea.style.display = 'none';
        deductArea.style.display = 'block';
      } else if (answer !== null) {
        alert('정답이 아닙니다.');
      }
    };

    deductBtn.onclick = () => {
      RewardSystem.consumeInternal('snack', (newState) => {
        display.textContent = `${newState.snacks}개`;
        if (newState.snacks < 1) {
          setTimeout(() => overlay.remove(), 400);
        } else {
          lockArea.style.display = 'block';
          deductArea.style.display = 'none';
        }
      });
    };
  }

  function openMarbleModal() {
    const marbleUrl = new URL('../marble/', getGlobalBaseUrl()).href;

    const overlay = createModalOverlay('reward-marble-modal');
    overlay.style.backgroundColor = 'rgba(0,0,0,0.92)';
    overlay.innerHTML = `
      <div class="reward-marble-content">
         <iframe src="${marbleUrl}" style="width:360px; height:560px; border:none; border-radius:20px; box-shadow: 0 10px 40px rgba(0,0,0,0.5);"></iframe>
         <button class="btn-close-marble" onclick="this.closest('.reward-modal-overlay').remove()">학습으로 돌아가기</button>
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
    el.onclick = (e) => { if (e.target === el) el.remove(); };
    return el;
  }

  function showToast(msg) {
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
        <button class="btn-close" onclick="this.closest('.reward-modal-overlay').remove()">닫기</button>
      </div>
    `;
    document.body.appendChild(overlay);

    const deductBtn = overlay.querySelector('#deduct-custom-btn');
    deductBtn.onclick = () => {
      RewardSystem.consumeInternal(item.id, () => {
        overlay.remove();
      });
    };
  }

  return {
    injectCriticalStyles, injectStyles, injectInventoryBar, syncInventoryBarWithState, applyBodyTopOffset, updateUI,
    playEntranceAndAddGem, openShopModal, spawnExplosion, showToast, 
    openYoutubeModal, openSnackModal, openMarbleModal, openCustomModal
  };
})();

(function registerGuardianNav() {
  function guardianPageUrl() {
    const script =
      document.querySelector('script[src*="/global/reward_ui.js"]') ||
      document.querySelector('script[src$="global/reward_ui.js"]');
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
