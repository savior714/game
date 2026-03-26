/* ═══════════════════════════════════
   전역 보상 인벤토리 시스템 (Reward System)
   - localStorage 기반 상태 관리
   - 모든 페이지 상단 인벤토리 UI 자동 주입
   - "지금 하기 vs 나중에 하기" 선택 로직
═══════════════════════════════════ */

const RewardSystem = (() => {
  const STORAGE_KEY = 'study_rewards';
  const initialState = {
    youtube_minutes: 0,
    snacks: 0,
    marble_plays: 0,
    theme: 'modern',
    last_updated: new Date().toISOString()
  };

  let state = { ...initialState };
  let resizeBound = false;

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
    updateUI();
  }

  function setTheme(themeName) {
    state.theme = themeName;
    save();
    window.location.reload(); 
  }

  function add(type, amount = 1) {
    if (type === 'youtube') state.youtube_minutes += (amount * 15);
    else if (type === 'snack') state.snacks += amount;
    else if (type === 'marble') state.marble_plays += amount;
    
    save();
    showToast(`${type === 'youtube' ? '📺 유튜브 시간' : type === 'snack' ? '🍪 간식' : '🎮 마블 게임'} 획득!`);
  }

  function has(type) {
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

    if (type === 'youtube') {
      openYoutubeModal();
    } else if (type === 'snack') {
      state.snacks -= 1;
      save();
      openSnackModal();
    } else if (type === 'marble') {
      state.marble_plays -= 1;
      save();
      openMarbleModal();
    }
  }

  // ──────────────────────────────────────────
  // 2. UI 주입 및 갱신 (UI Injection)
  // ──────────────────────────────────────────
  function init() {
    load();
    injectStyles();
    injectInventoryBar();
    updateUI();
  }

  function injectStyles() {
    if (document.getElementById('reward-system-css')) return;
    const currentPath = window.location.pathname;
    const depth = (currentPath.match(/\//g) || []).length - 1;
    const prefix = depth > 0 ? '../'.repeat(depth) : './';

    const link = document.createElement('link');
    link.id = 'reward-system-css';
    link.rel = 'stylesheet';
    link.href = prefix + 'global/reward.css';
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

  function injectInventoryBar() {
    if (document.getElementById('reward-inventory')) return;
    const bar = document.createElement('div');
    bar.id = 'reward-inventory';
    if (state.theme === 'analog') bar.classList.add('theme-analog');
    bar.innerHTML = `
      <div class="inventory-content">
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
    document.body.style.paddingTop = `${basePaddingTop + barHeight}px`;
  }

  function updateUI() {
    const yt = document.getElementById('inv-yt');
    const snack = document.getElementById('inv-snack');
    const marble = document.getElementById('inv-marble');

    if (yt) yt.textContent = state.youtube_minutes;
    if (snack) snack.textContent = state.snacks;
    if (marble) marble.textContent = state.marble_plays;
    
    document.querySelectorAll('.inventory-item').forEach(el => {
      const type = el.dataset.type;
      const count = (type === 'youtube') ? state.youtube_minutes : 
                    (type === 'snack') ? state.snacks : state.marble_plays;
      if (count > 0) el.classList.add('has-reward');
      else el.classList.remove('has-reward');
    });
  }

  // ──────────────────────────────────────────
  // 3. 룰렛 및 선택 팝업 (Roulette & Choice Workflow)
  // ──────────────────────────────────────────
  function playEntranceAndOpenRoulette(sourceElId = 'rp-rocket') {
    if (document.getElementById('reward-overlay')) return;
    const src = document.getElementById(sourceElId);
    if (!src) { openRoulette(); return; }

    const r = src.getBoundingClientRect();
    const startX = r.left + r.width / 2;
    const startY = r.top + r.height / 2;
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
      openRoulette();
    }, 1050);
  }

  function openRoulette() {
    if (document.getElementById('reward-overlay')) return;

    const rewards = [
      { id: 'marble',  label: '🎮 마블 게임 1판' },
      { id: 'youtube', label: '📺 유튜브 15분 보기' },
      { id: 'snack',   label: '🍪 간식 하나 고르기' },
    ];

    const overlay = document.createElement('div');
    overlay.id = 'reward-overlay';
    overlay.className = 'reward-modal-overlay';
    
    overlay.innerHTML = `
      <div class="reward-modal-content roulette-modal">
        <div class="reward-head">
          <h3 style="margin:0; font-size:1.5rem;">🎁 보상 룰렛</h3>
        </div>
        <div class="reward-body" style="margin-top:16px;">
          <p class="reward-sub" style="color:#666; font-size:0.9rem;">축하합니다! 룰렛을 돌려 보상을 받으세요.</p>
          <div class="roulette-list" style="margin: 20px 0; display: flex; flex-direction: column; gap: 8px;">
            ${rewards.map(r => `<div class="roulette-item" data-reward="${r.id}" style="padding:12px; border-radius:12px; background:#f8fafc; border:1px solid #e2e8f0; transition:all 0.2s; position:relative;">${r.label}<span style="position:absolute; right:12px; opacity:0;">🎯</span></div>`).join('')}
          </div>
          <div class="reward-actions" style="display:flex; flex-direction:column; gap:10px;">
            <button class="btn-primary" id="reward-spin-btn" style="margin:0;">룰렛 돌리기</button>
            <button class="btn-close" id="reward-cancel-btn">나중에</button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);

    const items = Array.from(overlay.querySelectorAll('.roulette-item'));
    const spinBtn = overlay.querySelector('#reward-spin-btn');
    const cancelBtn = overlay.querySelector('#reward-cancel-btn');

    cancelBtn.onclick = () => overlay.remove();

    spinBtn.onclick = () => {
      spinBtn.disabled = true;
      cancelBtn.style.display = 'none';
      
      const winner = rewards[Math.floor(Math.random() * rewards.length)];
      const winnerEl = overlay.querySelector(`.roulette-item[data-reward="${winner.id}"]`);

      let i = 0;
      const start = performance.now();
      const duration = 1800;
      const tickMs = 85;

      const itv = setInterval(() => {
        items.forEach(it => {
          it.style.background = '#f8fafc';
          it.style.borderColor = '#e2e8f0';
          it.querySelector('span').style.opacity = '0';
        });
        const current = items[i % items.length];
        current.style.background = '#fff7ed';
        current.style.borderColor = '#fdba74';
        i++;
        if (performance.now() - start >= duration) {
          clearInterval(itv);
          items.forEach(it => { it.style.background = '#f8fafc'; it.style.borderColor = '#e2e8f0'; });
          winnerEl.style.background = '#ffedd5';
          winnerEl.style.borderColor = '#f97316';
          winnerEl.querySelector('span').style.opacity = '1';
          setTimeout(() => {
            overlay.remove();
            offerChoice(winner.id);
          }, 600);
        }
      }, tickMs);
    };
  }

  function offerChoice(type) {
    const overlay = document.createElement('div');
    overlay.className = 'reward-choice-overlay';
    
    const labels = {
      youtube: { name: '유튜브 15분', icon: '📺' },
      snack: { name: '맛있는 간식', icon: '🍪' },
      marble: { name: '마블 게임 1판', icon: '🎮' }
    };
    const info = labels[type] || { name: '보상', icon: '🎁' };

    overlay.innerHTML = `
      <div class="reward-choice-modal">
        <div class="icon-bounce">${info.icon}</div>
        <h3>🎉 보상 획득!</h3>
        <p><strong>${info.name}</strong> 보상을 받았습니다.</p>
        <p class="sub">지금 바로 사용할까요, 아니면 나중에 쓸까요?</p>
        <div class="choice-actions">
          <button class="btn-now" onclick="RewardSystem._handleChoice('${type}', 'now')">지금 하기</button>
          <button class="btn-later" onclick="RewardSystem._handleChoice('${type}', 'later')">나중에 하기</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
  }

  function _handleChoice(type, choice) {
    document.querySelector('.reward-choice-overlay')?.remove();
    if (choice === 'now') {
      add(type, 1);
      consume(type);
    } else {
      add(type, 1);
    }
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

  // ──────────────────────────────────────────
  // 4. 모달 구현 (Modals)
  // ──────────────────────────────────────────
  function openYoutubeModal() {
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
      // 복잡한 계산 (두 자리 덧셈)
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
      if (state.youtube_minutes < 15) {
        alert('시간이 부족합니다.');
        overlay.remove();
        return;
      }
      state.youtube_minutes -= 15;
      save();
      display.textContent = `${state.youtube_minutes}분`;
      showToast('15분 차감 완료');
      if (state.youtube_minutes < 15) {
        setTimeout(() => overlay.remove(), 400);
      } else {
        // 계속 사용할 수 있도록 버튼 유지
        lockArea.style.display = 'block';
        deductArea.style.display = 'none';
      }
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

  return { init, add, consume, getState: () => state, setTheme, offerChoice, playEntranceAndOpenRoulette, _handleChoice };
})();

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => RewardSystem.init());
} else {
  RewardSystem.init();
}
