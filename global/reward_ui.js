/* ═══════════════════════════════════
   전역 보상 시스템 UI/UX 모듈 (Reward System UI)
   - 모달, 토스트, 애니메이션 및 시각 효과 전용
   - core 모듈(reward.js)과 연동하여 동작
   - 2026-03-28: reward.js로부터 분리 (500라인 제한 준수)
   ═══════════════════════════════════ */

const RewardSystemUI = (() => {
  let resizeBound = false;

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
    const currentPath = window.location.pathname;
    const depth = (currentPath.match(/\//g) || []).length - 1;
    const prefix = depth > 0 ? '../'.repeat(depth) : './';

    const link = document.createElement('link');
    link.id = 'reward-system-css';
    link.rel = 'stylesheet';
    link.href = prefix + 'global/reward.css';
    link.onload = () => {
      if (onLoad) onLoad();
    };
    document.head.appendChild(link);

    if (state.theme === 'analog') {
      const analogLink = document.createElement('link');
      analogLink.id = 'reward-system-analog-css';
      analogLink.rel = 'stylesheet';
      analogLink.href = prefix + 'global/reward_analog.css';
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
    bar.innerHTML = `
      <div class="inventory-content">
        <div class="inventory-item gem-item" data-type="gems" onclick="RewardSystem.openShopModal()">
          <span class="icon">💎</span> <span class="val" id="inv-gems">0</span>
        </div>
        <div class="inventory-item" data-type="youtube" onclick="RewardSystem.consume('youtube')">
          <span class="icon">📺</span> <span class="val" id="inv-yt">0</span><span class="unit">분</span>
        </div>
        <div class="inventory-item" data-type="snack" onclick="RewardSystem.consume('snack')">
          <span class="icon">🍪</span> <span class="val" id="inv-snack">0</span><span class="unit">개</span>
        </div>
        <div class="inventory-item" data-type="marble" onclick="RewardSystem.consume('marble')">
          <span class="icon">🎮</span> <span class="val" id="inv-marble">0</span><span class="unit">회</span>
        </div>
      </div>
    `;
    document.body.prepend(bar);
    applyBodyTopOffset();

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
    const yt = document.getElementById('inv-yt');
    const snack = document.getElementById('inv-snack');
    const marble = document.getElementById('inv-marble');

    if (gems) gems.textContent = state.gems;
    if (yt) yt.textContent = state.youtube_minutes;
    if (snack) snack.textContent = state.snacks;
    if (marble) marble.textContent = state.marble_plays;
    
    document.querySelectorAll('.inventory-item').forEach(el => {
      const type = el.dataset.type;
      const count = (type === 'gems') ? state.gems :
                    (type === 'youtube') ? state.youtube_minutes : 
                    (type === 'snack') ? state.snacks : state.marble_plays;
      if (count > 0) el.classList.add('has-reward');
      else el.classList.remove('has-reward');
    });
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
    
    const shopItems = [
      { id: 'youtube', icon: '📺', label: '유튜브 15분', desc: '좋아하는 영상 시청' },
      { id: 'snack', icon: '🍪', label: '간식 1개', desc: '맛있는 간식 시간' },
      { id: 'marble', icon: '🎮', label: '마블 게임', desc: '마블 한 판 더!' },
    ];

    overlay.innerHTML = `
      <div class="reward-modal-content shop-modal">
        <div class="reward-head">
          <h3 style="margin:0; font-size:1.5rem;">💎 보석 상점</h3>
          <p style="margin:5px 0 0; font-size:0.9rem; color:#666;">보석 1개로 선물을 골라보세요!</p>
        </div>
        <div class="shop-inventory-info" style="margin: 15px 0; padding: 10px; background: #f1f5f9; border-radius: 12px; font-weight: bold;">
          보유 보석: <span style="color:#8b5cf6;">💎 ${state.gems}개</span>
        </div>
        <div class="shop-grid" style="display: grid; gap: 12px; margin: 20px 0;">
          ${shopItems.map(item => `
            <div class="shop-card" onclick="RewardSystem.exchangeGem('${item.id}')" style="cursor:pointer; padding:15px; border:2px solid #e2e8f0; border-radius:18px; display:flex; align-items:center; gap:15px; text-align:left; transition:all 0.2s;">
              <div style="font-size:2rem;">${item.icon}</div>
              <div style="flex:1;">
                <div style="font-weight:bold; font-size:1.05rem;">${item.label}</div>
                <div style="font-size:0.8rem; color:#666;">${item.desc}</div>
              </div>
              <div style="background:#8b5cf6; color:white; padding:4px 10px; border-radius:10px; font-size:0.85rem; font-weight:bold;">💎 1</div>
            </div>
          `).join('')}
        </div>
        <button class="btn-close" style="width:100%; padding:12px;" onclick="this.closest('.reward-modal-overlay').remove()">나중에 하기</button>
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

  function openSnackModal() {
    const overlay = createModalOverlay('reward-snack-modal');
    overlay.innerHTML = `
      <div class="reward-modal-content">
        <h3>🍪 간식 한 개 고르기</h3>
        <p>과일, 요거트, 또는 좋아하는 과자 하나를 골라 드세요!</p>
        <div class="snack-icons">🍎 🍌 🥛 🥨 🍫</div>
        <button class="btn-primary" onclick="this.closest('.reward-modal-overlay').remove()">맛있게 먹을게요!</button>
      </div>
    `;
    document.body.appendChild(overlay);
  }

  function openMarbleModal() {
    const currentPath = window.location.pathname;
    const depth = (currentPath.match(/\//g) || []).length - 1;
    const prefix = depth > 0 ? '../'.repeat(depth) : './';
    const marbleUrl = prefix + 'marble/';

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

  return {
    injectCriticalStyles, injectStyles, injectInventoryBar, applyBodyTopOffset, updateUI,
    playEntranceAndAddGem, openShopModal, spawnExplosion, showToast, 
    openYoutubeModal, openSnackModal, openMarbleModal
  };
})();
