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
        position: static;
        width: auto;
        opacity: 0; visibility: visible; display: flex; align-items: center; justify-content: center;
        min-height: auto; pointer-events: none; transition: opacity 0.3s ease;
      }
      #reward-inventory.is-integrated,
      .hud-reward-mount #reward-inventory,
      .compact-hud-reward-mount #reward-inventory {
        position: static !important;
        background: transparent !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        width: auto !important;
        min-height: auto !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        z-index: auto !important;
        display: flex !important;
        align-items: center !important;
      }
      #reward-inventory.reward-surface-gem-only {
        display: inline-flex !important;
        align-items: center !important;
        width: auto !important;
      }
      #reward-inventory.reward-surface-gem-only .gem-only-content {
        display: inline-flex !important;
        align-items: center !important;
        width: auto !important;
        gap: 0 !important;
      }
      #reward-inventory .inventory-content,
      #reward-inventory .inventory-left {
        flex-wrap: nowrap !important;
        white-space: nowrap;
      }
      .dark #reward-inventory .inventory-item .val,
      html.dark #reward-inventory .inventory-item .val,
      .hud-reward-mount #reward-inventory .inventory-item .val,
      .compact-hud-reward-mount #reward-inventory .inventory-item .val {
        color: #FFFFFF !important;
      }
      .dark #reward-inventory .inventory-item .unit,
      html.dark #reward-inventory .inventory-item .unit,
      .hud-reward-mount #reward-inventory .inventory-item .unit,
      .compact-hud-reward-mount #reward-inventory .inventory-item .unit {
        color: #E2E8F0 !important;
      }
      .dark #reward-inventory .inventory-item.empty-slot .val,
      html.dark #reward-inventory .inventory-item.empty-slot .val,
      .hud-reward-mount #reward-inventory .inventory-item.empty-slot .val,
      .compact-hud-reward-mount #reward-inventory .inventory-item.empty-slot .val {
        color: #CBD5E1 !important;
      }
      .dark #reward-inventory #inv-auth,
      html.dark #reward-inventory #inv-auth,
      .hud-reward-mount #reward-inventory #inv-auth,
      .compact-hud-reward-mount #reward-inventory #inv-auth {
        color: #FFFFFF !important;
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

      /* 미니게임 모달 (Marble / Bubble) */
      .reward-marble-modal,
      .reward-bubble-modal {
        padding: 16px;
        box-sizing: border-box;
        overflow-y: auto;
      }
      .reward-marble-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 16px;
        width: 100%;
        max-width: 960px;
        box-sizing: border-box;
        margin: auto;
      }
      .reward-mini-game-frame {
        width: min(94vw, 960px);
        height: min(80vh, 680px);
        height: min(80dvh, 680px);
        max-width: 100%;
        border: none;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
        background: #0f121c;
      }
      .btn-close-marble {
        padding: 12px 24px;
        background: rgba(255, 255, 255, 0.15);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 99px;
        cursor: pointer;
        backdrop-filter: blur(10px);
        font-family: inherit;
        font-size: 14px;
        font-weight: 700;
        transition: background 0.2s ease, transform 0.15s ease;
      }
      .btn-close-marble:hover {
        background: rgba(255, 255, 255, 0.25);
        transform: translateY(-1px);
      }
      .reward-modal-content,
      .reward-choice-modal {
        color: #0f172a !important;
      }
      .reward-modal-content h3,
      .reward-choice-modal h3 {
        color: #0f172a !important;
      }
      .reward-modal-content input[type="number"] {
        color: #0f172a !important;
        background: #ffffff !important;
        font-weight: 800;
        text-align: center;
      }
    `;
    document.head.appendChild(style);
  }

  function ensureAuthAndSyncScripts() {
    if (
      !window.Auth
      && !document.getElementById('aiden-canonical-auth')
      && !document.querySelector('script[src$="/domains/auth/auth.js"]')
      && !document.querySelector('script[src$="domains/auth/auth.js"]')
    ) {
      const s2 = document.createElement('script');
      s2.src = resolveGlobalAsset('auth.js');
      document.head.appendChild(s2);
    }
    if (!window.SyncEngine && !document.getElementById('aiden-canonical-sync')) {
      const s3 = document.createElement('script');
      s3.src = resolveGlobalAsset('sync-engine.js');
      document.head.appendChild(s3);
    }
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

    // Inject Supabase & Auth scripts.
    // auth-gate.js가 먼저 Supabase/auth를 읽고 있을 수 있으므로, 이미 준비된
    // 의존성은 다시 읽지 않고 아직 없는 sync 모듈만 보완한다.
    if (typeof supabase === 'undefined' && !document.getElementById('supabase-js')) {
      const s1 = document.createElement('script');
      s1.id = 'supabase-js';
      s1.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2';
      s1.onload = ensureAuthAndSyncScripts;
      document.head.appendChild(s1);
    } else if (typeof supabase !== 'undefined') {
      ensureAuthAndSyncScripts();
    } else {
      const existing = document.getElementById('supabase-js');
      if (existing && typeof existing.addEventListener === 'function') {
        existing.addEventListener('load', ensureAuthAndSyncScripts, { once: true });
      }
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

  function resolveMainHubUrl() {
    const mountTarget = document.getElementById('reward-inventory-mount');
    if (mountTarget && mountTarget.dataset.hubHref) {
      return mountTarget.dataset.hubHref;
    }
    try {
      return new URL('../../index.html#reward-inventory-mount', getGlobalBaseUrl()).href;
    } catch (e) {
      return '../../index.html#reward-inventory-mount';
    }
  }

  function injectInventoryBar(state) {
    if (document.getElementById('reward-inventory')) return;
    const mountTarget = document.getElementById('reward-inventory-mount');
    if (!mountTarget) {
      // Invariant: 보상 UI는 해당 화면이 명시적으로 제공하는 surface 안에서만 렌더링한다.
      // mount가 없는 화면(게임, 몰입형 화면 등)에서는 전역 고정 바를 자동 생성하지 않는다.
      return;
    }

    const surfaceMode = mountTarget.dataset.rewardSurface || 'full';
    const bar = document.createElement('div');
    bar.id = 'reward-inventory';
    bar.classList.add('is-integrated');
    if (state.theme === 'analog') bar.classList.add('theme-analog');
    bar.dataset.surfaceMode = surfaceMode;

    if (surfaceMode === 'gem-only') {
      bar.classList.add('reward-surface-gem-only');
      const hubUrl = resolveMainHubUrl();
      bar.innerHTML = `
        <div class="inventory-content gem-only-content">
          <a href="${hubUrl}" class="inventory-item gem-item compact-gem-link" data-type="gems" data-action="go-main-reward" aria-label="보석 ${state.gems}개, 보상 화면으로 이동">
            <span class="icon">💎</span> <span class="val" id="inv-gems">${state.gems}</span>
          </a>
        </div>
      `;
      mountTarget.appendChild(bar);
      bar.style.opacity = '1';
      bar.classList.add('ready');
      applyBodyTopOffset();
      return;
    }

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
      else if (item.id === 'marble' || item.id === 'bubble') unit = '회';
      
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
        </div>
        </div>
      </div>
    `;
    bar.innerHTML = html;
    bar.dataset.shopItemsSig = JSON.stringify(state.shop_items || []);
    mountTarget.appendChild(bar);
    applyBodyTopOffset();

    const authLabel = document.getElementById('inv-auth');
    if (authLabel && window.Auth && typeof window.Auth.getUser === 'function') {
      authLabel.textContent = window.Auth.getUser() ? '로그아웃' : '로그인';
    }

    if (!authListenerBound) {
      authListenerBound = true;
      window.addEventListener('auth-changed', (e) => {
        const label = document.getElementById('inv-auth');
        const user = e && e.detail && Object.prototype.hasOwnProperty.call(e.detail, 'user')
          ? e.detail.user
          : (window.Auth && typeof window.Auth.getUser === 'function' ? window.Auth.getUser() : null);
        if (label) {
          label.textContent = user ? '로그아웃' : '로그인';
        }
      });
    }
  }

  function applyBodyTopOffset() {
    const bar = document.getElementById('reward-inventory');
    if (!bar) return;
    bar.classList.add('ready');
    bar.style.opacity = '1';
    document.documentElement.style.setProperty('--reward-bar-height', '0px');
  }

  let currentActiveSession = null;
  let sessionMonitorIntervalId = null;
  let activePipWindow = null;

  function updateContextualCountdown(session, remainingMs) {
    const deadline = session.endsAt || Date.now();
    const rem = typeof remainingMs === 'number' ? remainingMs : Math.max(0, deadline - Date.now());
    const formatted = formatTimeMMSS(rem);
    const isWarning = rem <= 60000 && rem > 0;

    const ytItem = document.querySelector('#reward-inventory .inventory-item[data-type="youtube"]');
    if (ytItem) {
      ytItem.classList.add('has-reward');
      ytItem.classList.remove('empty-slot');
      ytItem.style.display = 'flex';
      const valEl = document.getElementById('inv-youtube') || ytItem.querySelector('.val');
      const unitEl = ytItem.querySelector('.unit');
      if (valEl) {
        valEl.textContent = isWarning ? `1분 남음 · ${formatted}` : `사용 중 · ${formatted}`;
      }
      if (unitEl) {
        unitEl.textContent = '';
      }
    }
  }

  function restoreContextualControl() {
    const ytItem = document.querySelector('#reward-inventory .inventory-item[data-type="youtube"]');
    if (ytItem) {
      const state = (typeof RewardSystem !== 'undefined' && typeof RewardSystem.getState === 'function')
        ? RewardSystem.getState()
        : null;
      const count = state ? state.youtube_minutes : 0;
      const valEl = document.getElementById('inv-youtube') || ytItem.querySelector('.val');
      const unitEl = ytItem.querySelector('.unit');
      if (valEl) valEl.textContent = count;
      if (unitEl) unitEl.textContent = '분';
      if (count > 0) {
        ytItem.classList.add('has-reward');
        ytItem.classList.remove('empty-slot');
      } else {
        ytItem.classList.remove('has-reward');
        ytItem.classList.add('empty-slot');
      }
    }
  }

  function updateUI(state) {
    const gems = document.getElementById('inv-gems');
    if (gems) gems.textContent = state.gems;

    document.querySelectorAll('#reward-inventory .inventory-item[data-type]').forEach(el => {
      const type = el.dataset.type;
      if (!type) return;

      if (type === 'youtube' && currentActiveSession && currentActiveSession.status === 'running' && currentActiveSession.endsAt > Date.now()) {
        updateContextualCountdown(currentActiveSession);
        return;
      }

      let count = 0;
      if (type === 'gems') { count = state.gems; }
      else if (type === 'youtube') { count = state.youtube_minutes; }
      else if (type === 'snack') { count = state.snacks; }
      else if (type === 'marble') { count = state.marble_plays; }
      else if (type === 'bubble') { count = state.bubble_plays; }
      else { count = state.custom_inventory[type] || 0; }

      const valEl = document.getElementById('inv-' + type);
      if (valEl) valEl.textContent = count;

      if (type === 'youtube') {
        const unitEl = el.querySelector('.unit');
        if (unitEl) unitEl.textContent = '분';
      }

      if (type === 'marble' || type === 'bubble') {
        if (valEl) valEl.textContent = '5';
        const unitEl = el.querySelector('.unit');
        if (unitEl) unitEl.textContent = '분 놀이';
        el.title = '정답 5개를 맞히고 5분 동안 놀아요';
        el.setAttribute('role', 'button');
        el.tabIndex = 0;
        el.classList.add('has-reward');
        el.classList.remove('empty-slot');
        return;
      }

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
    const mountTarget = document.getElementById('reward-inventory-mount');
    if (!mountTarget) return;
    const surfaceMode = mountTarget.dataset.rewardSurface || 'full';
    if (surfaceMode === 'gem-only') {
      updateUI(state);
      return;
    }
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

  function playEntranceAndAddGem(sourceElId = 'rp-rocket', meta = null) {
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
      showGemAwarded(endX, endY, meta);
    }, 1050);
  }

  function showGemAwarded(cx, cy, meta = null) {
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
    RewardSystem.add('gems', 1, meta || {
      reason: 'rocket_launch',
      source: 'quiz',
      actor: 'system',
      detail: '연속 정답 로켓 발사 보상',
    });
  }


  // ── 보상 기록(감사 로그) ──
  const ACTIVITY_LABELS = {
    gems: '💎 보석',
    youtube_minutes: '📺 자유시간',
    snacks: '🍪 간식',
    marble_plays: '🎮 마블',
    bubble_plays: '🫧 비눗방울',
  };

  const ACTIVITY_TYPE_LABELS = {
    grant: '획득',
    consume: '사용',
    exchange: '교환',
    adjust: '조정',
  };

  function describeActivityKey(key, state) {
    if (ACTIVITY_LABELS[key]) return ACTIVITY_LABELS[key];
    if (typeof key === 'string' && key.startsWith('custom:')) {
      const id = key.slice('custom:'.length);
      const item = (state && Array.isArray(state.shop_items))
        ? state.shop_items.find(entry => entry.id === id)
        : null;
      return item ? `${item.icon || '🎁'} ${item.label || id}` : `🎁 ${id}`;
    }
    return '🎁 보상';
  }

  function formatActivityTime(at) {
    const value = Number(at) || 0;
    if (value <= 0) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    const pad = (num) => String(num).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
  }

  function escapeActivityHtml(raw) {
    return String(raw == null ? '' : raw)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function resolveGuardianAuditUrl() {
    try {
      const base = getGlobalBaseUrl();
      if (base) return new URL('guardian/index.html#audit', base).href;
    } catch (_e) {}
    return './domains/reward/guardian/index.html#audit';
  }

  let currentActivityFilter = 'all';

  /**
   * 최근 획득/사용 기록을 렌더링한다.
   * 아이·보호자가 "무엇이 언제 들어오고 나갔는지"를 같은 화면에서 확인할 수 있게 한다.
   */
  function renderActivityLog(state) {
    if (typeof RewardSystem === 'undefined' || typeof RewardSystem.getRecentActivity !== 'function') {
      return '';
    }
    let entries = [];
    try {
      entries = RewardSystem.getRecentActivity(20) || [];
    } catch (e) {
      entries = [];
    }
    if (currentActivityFilter !== 'all') {
      entries = entries.filter((entry) => entry && entry.type === currentActivityFilter);
    }
    const integrityOk = (typeof RewardSystem.verifyIntegrity === 'function')
      ? Boolean(RewardSystem.verifyIntegrity().ok)
      : false;
    const epochNum = state && state.reward_ledger && Number(state.reward_ledger.reset_epoch)
      ? Number(state.reward_ledger.reset_epoch)
      : 1;

    const filterBtnStyle = (active) => (active
      ? 'padding:3px 8px; border-radius:999px; border:1px solid #0f172a; background:#0f172a; color:#ffffff; font-size:0.7rem; font-weight:800; cursor:pointer;'
      : 'padding:3px 8px; border-radius:999px; border:1px solid #cbd5e1; background:#ffffff; color:#475569; font-size:0.7rem; font-weight:700; cursor:pointer;');

    const rows = entries.length === 0
      ? '<li style="color:#64748b; font-size:0.78rem; padding:8px 0;">아직 획득·사용 기록이 없어요. (초기화 이후 모든 내역이 초 단위로 기록됩니다)</li>'
      : entries.map((entry) => {
        const isPositive = Number(entry.delta) > 0;
        const color = isPositive ? '#0f766e' : '#be123c';
        const sign = isPositive ? '+' : '−';
        const unit = entry.key === 'youtube_minutes' ? '분' : (entry.key === 'marble_plays' || entry.key === 'bubble_plays') ? '회' : '개';
        const typeLabel = ACTIVITY_TYPE_LABELS[entry.type] || '기록';
        const timeText = formatActivityTime(entry.at);
        const beforePart = typeof entry.balanceBefore === 'number' ? `${entry.balanceBefore}→` : '';
        const metaText = `${beforePart}남은 ${entry.balanceAfter}${unit}${timeText ? ' · ' + timeText : ''}`;
        const detailText = entry.detail ? escapeActivityHtml(entry.detail) : '';
        return `<li style="display:flex; flex-direction:column; gap:2px; padding:7px 0; border-bottom:1px dashed #e2e8f0; font-size:0.8rem; color:#334155;">
          <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
            <span style="min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-weight:700;">${describeActivityKey(entry.key, state)} <span style="color:#64748b; font-size:0.72rem; font-weight:700;">${typeLabel}</span></span>
            <span style="flex-shrink:0; font-weight:800; color:${color};">${sign}${Math.abs(Number(entry.delta) || 0)}${unit}</span>
            <span style="flex-shrink:0; color:#475569; font-size:0.71rem; font-family:monospace;">${metaText}</span>
          </div>
          ${detailText ? `<div style="font-size:0.72rem; color:#64748b; line-height:1.3;">${detailText}${entry.surfaceLabel ? ' · ' + escapeActivityHtml(entry.surfaceLabel) : ''}</div>` : ''}
        </li>`;
      }).join('');

    return `
      <div class="reward-activity-log" style="margin: 0 0 14px; padding: 12px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:14px; text-align:left; color:#0f172a;">
        <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; margin-bottom:4px; flex-wrap:wrap;">
          <strong style="font-size:0.9rem; color:#0f172a;">🧾 보상 획득·사용 감사 기록 <span style="font-size:0.7rem; color:#64748b; font-weight:700;">(Epoch #${epochNum})</span></strong>
          <span style="font-size:0.72rem; font-weight:800; color:${integrityOk ? '#0f766e' : '#b45309'};">
            ${integrityOk ? '✅ 기록 확인됨' : '⚠️ 확인 필요'}
          </span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; margin:6px 0 8px; flex-wrap:wrap;">
          <div style="display:flex; gap:4px; flex-wrap:wrap;">
            <button type="button" data-action="filter-activity-log" data-filter-type="all" style="${filterBtnStyle(currentActivityFilter === 'all')}">전체</button>
            <button type="button" data-action="filter-activity-log" data-filter-type="grant" style="${filterBtnStyle(currentActivityFilter === 'grant')}">획득(+)</button>
            <button type="button" data-action="filter-activity-log" data-filter-type="consume" style="${filterBtnStyle(currentActivityFilter === 'consume')}">사용(−)</button>
            <button type="button" data-action="filter-activity-log" data-filter-type="exchange" style="${filterBtnStyle(currentActivityFilter === 'exchange')}">교환</button>
          </div>
          <a href="${escapeActivityHtml(resolveGuardianAuditUrl())}" style="font-size:0.72rem; font-weight:800; color:#4f46e5; text-decoration:none;">🛡️ 전체 감사·초기화 →</a>
        </div>
        <ul style="margin:0; padding:0; list-style:none; max-height:175px; overflow-y:auto;">${rows}</ul>
      </div>
    `;
  }

  function openShopModal(state) {
    if (document.getElementById('reward-shop-overlay')) return;

    const overlay = document.createElement('div');
    overlay.id = 'reward-shop-overlay';
    overlay.className = 'reward-modal-overlay';
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
    
    const shopItems = state.shop_items || [];

    overlay.innerHTML = `
      <div class="reward-modal-content shop-modal" style="color:#0f172a;">
        <div class="reward-head">
          <h3 style="margin:0; font-size:1.5rem; color:#0f172a; font-weight:800;">💎 보석 상점</h3>
          <p style="margin:5px 0 0; font-size:0.9rem; color:#475569;">보석으로 선물을 골라보세요!</p>
        </div>
        <div class="shop-inventory-info" style="margin: 15px 0; padding: 10px; background: #f1f5f9; border-radius: 12px; font-weight: bold; color:#0f172a;">
          보유 보석: <span style="color:#8b5cf6;">💎 ${state.gems}개</span>
        </div>
        ${renderActivityLog(state)}
        <div class="shop-grid" style="display: grid; gap: 12px; margin: 20px 0; max-height:50vh; overflow-y:auto; padding-right:5px;">
          ${shopItems.map(item => `
            <div class="shop-card" data-action="${item.id === 'marble' || item.id === 'bubble' ? 'consume' : 'exchange-gem'}" data-item-id="${item.id}" style="cursor:pointer; padding:15px; border:2px solid #e2e8f0; border-radius:18px; display:flex; align-items:center; gap:15px; text-align:left; transition:all 0.2s; color:#0f172a;">
              <div style="font-size:2rem;">${item.icon}</div>
              <div style="flex:1;">
                <div style="font-weight:bold; font-size:1.05rem; color:#0f172a;">${item.label}</div>
                <div style="font-size:0.8rem; color:#64748b; word-break:keep-all;">${item.id === 'marble' || item.id === 'bubble' ? '원하는 과목 정답 5개를 맞히고 입장해요' : item.desc}</div>
              </div>
              <div style="background:#8b5cf6; color:white; padding:4px 10px; border-radius:10px; font-size:0.85rem; font-weight:bold; flex-shrink:0;">${item.id === 'marble' || item.id === 'bubble' ? '공부하고 5분' : `💎 ${item.price || 1}`}</div>
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
    const initialMinutes = state && typeof state.youtube_minutes === 'number' ? state.youtube_minutes : 0;
    const initialTickets = Math.max(0, Math.floor(initialMinutes / 10));

    overlay.innerHTML = `
      <div class="reward-modal-content" style="color:#0f172a;">
        <div class="icon-bounce" style="font-size:2.6rem; margin-bottom:8px;">📺</div>
        <h3 style="margin:0 0 10px; font-size:1.35rem; color:#0f172a; font-weight:800;">유튜브 자유시간</h3>
        ${initialMinutes % 10 !== 0 ? `<div id="yt-stray-notice" style="background:#fef3c7; border:1.5px solid #f59e0b; border-radius:12px; padding:10px 12px; margin:10px 0; font-size:0.82rem; text-align:left; color:#92400e; line-height:1.4;">⚠️ <b>${initialMinutes}분</b> 중 <b>${initialMinutes % 10}분</b>은 10분권 단위가 아니라 사용할 수 없는 찌꺼기예요.<br><button type="button" id="yt-normalize-btn" style="margin-top:8px; width:100%; padding:8px; background:#f59e0b; color:white; border:none; border-radius:10px; font-weight:800; cursor:pointer;">찌꺼기 ${initialMinutes % 10}분 정리하고 ${Math.floor(initialMinutes/10)*10}분으로 맞추기</button></div>` : ''}

        <div class="yt-status-card" style="background:#f8fafc; border-radius:14px; padding:10px 14px; margin:10px 0; font-size:0.9rem; text-align:left; border:1px solid #e2e8f0; color:#0f172a;">
          <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
            <span style="color:#64748b;">보유 자유시간</span>
            <span style="font-weight:bold; color:#f43f5e;" id="yt-modal-inventory">${initialMinutes}분</span>
          </div>
          <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
            <span style="color:#64748b;">오늘 사용</span>
            <span style="font-weight:bold; color:#0f172a;" id="yt-modal-daily">0 / 60분</span>
          </div>
          <div style="display:flex; justify-content:space-between;">
            <span style="color:#64748b;" id="yt-modal-period-label">오전 사용</span>
            <span style="font-weight:bold; color:#0f172a;" id="yt-modal-period">0 / 30분</span>
          </div>
        </div>

        <div id="yt-deduct-area" class="reward-bulk-box" style="margin:12px 0; padding:12px 14px; background:#fff1f2; border:1.5px solid #fecdd3; border-radius:16px; text-align:left; color:#0f172a;">
          <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; margin-bottom:6px; flex-wrap:wrap;">
            <label for="yt-consume-quantity" style="font-size:0.88rem; font-weight:800; color:#be123c;">⚡ 부모님용 · 여러 개 한 번에 소진 (10분권)</label>
            <span id="yt-ticket-count-badge" style="font-size:0.76rem; font-weight:800; color:#e11d48; background:#ffe4e6; padding:2px 8px; border-radius:999px;">보유 ${initialTickets}개 (${initialMinutes}분)</span>
          </div>
          <p style="margin:0 0 8px; color:#475569; font-size:0.76rem; line-height:1.35;">TV·태블릿 등에서 이미 시청했거나 여러 개(10분 단위)를 한 번에 차감할 때 개수를 선택해 소진하세요.</p>
          <div class="reward-preset-row" style="display:flex; flex-wrap:wrap; gap:5px; margin-bottom:8px;">
            <button type="button" class="reward-preset-btn" data-yt-preset="1" style="flex:1 1 auto; padding:6px 8px; border-radius:8px; border:1.5px solid #fecdd3; background:#ffffff; color:#9f1239; font-size:0.78rem; font-weight:700; cursor:pointer;">1개(10분)</button>
            <button type="button" class="reward-preset-btn" data-yt-preset="2" style="flex:1 1 auto; padding:6px 8px; border-radius:8px; border:1.5px solid #fecdd3; background:#ffffff; color:#9f1239; font-size:0.78rem; font-weight:700; cursor:pointer;">2개(20분)</button>
            <button type="button" class="reward-preset-btn" data-yt-preset="3" style="flex:1 1 auto; padding:6px 8px; border-radius:8px; border:1.5px solid #fecdd3; background:#ffffff; color:#9f1239; font-size:0.78rem; font-weight:700; cursor:pointer;">3개(30분)</button>
            <button type="button" class="reward-preset-btn" data-yt-preset="5" style="flex:1 1 auto; padding:6px 8px; border-radius:8px; border:1.5px solid #fecdd3; background:#ffffff; color:#9f1239; font-size:0.78rem; font-weight:700; cursor:pointer;">5개(50분)</button>
            <button type="button" id="yt-use-all-btn" class="reward-preset-btn reward-use-all-btn" style="flex:1 1 auto; padding:6px 8px; border-radius:8px; border:1.5px solid #f43f5e; background:#ffe4e6; color:#be123c; font-size:0.78rem; font-weight:800; cursor:pointer;">전부 선택 (${initialTickets}개)</button>
          </div>
          <div class="reward-qty-row" style="display:flex; align-items:center; gap:6px; margin-bottom:8px;">
            <button type="button" id="yt-qty-minus" class="reward-qty-stepper" aria-label="유튜브 소진 개수 감소" style="width:36px; height:36px; border-radius:10px; border:1.5px solid #cbd5e1; background:#ffffff; color:#0f172a; font-size:1.15rem; font-weight:800; cursor:pointer;">−</button>
            <input id="yt-consume-quantity" type="number" min="1" max="${Math.max(1, initialTickets)}" value="1" inputmode="numeric" aria-label="한 번에 사용할 유튜브 10분권 개수" style="flex:1; min-width:60px; padding:7px 8px; border:1.5px solid #cbd5e1; border-radius:10px; font-size:1rem; font-weight:800; color:#0f172a; background:#ffffff; text-align:center;">
            <button type="button" id="yt-qty-plus" class="reward-qty-stepper" aria-label="유튜브 소진 개수 증가" style="width:36px; height:36px; border-radius:10px; border:1.5px solid #cbd5e1; background:#ffffff; color:#0f172a; font-size:1.15rem; font-weight:800; cursor:pointer;">+</button>
            <span id="yt-consume-minutes-preview" style="font-size:0.86rem; font-weight:800; color:#be123c; min-width:58px; text-align:right;">= 10분</span>
          </div>
          <button type="button" class="btn-primary" id="deduct-yt-btn" style="background:#e11d48; border-color:#be123c; width:100%; margin-bottom:0; padding:11px; font-size:0.95rem;">유튜브 1개 (10분) 사용 기록하기</button>
        </div>
        
        <div id="yt-lock-area" style="margin: 12px 0;">
          <button id="yt-unlock-trigger" style="background:#f8fafc; border:1.5px solid #cbd5e1; border-radius:14px; padding:8px 16px; font-size:1.5rem; cursor:pointer; display:inline-flex; align-items:center; gap:8px; color:#0f172a; font-weight:700;" title="부모님용 잠금 해제">
            <span>🔒</span>
            <span style="font-size:0.85rem;">브라우저 타이머 시작 (부모님 잠금 해제)</span>
          </button>
          <p class="sub" style="color:#64748b; font-size:0.76rem; margin-top:6px;">부모님께서 자물쇠를 눌러 승인해 주세요.</p>
        </div>

        <div id="yt-start-area" style="display:none; margin-top:10px;">
          <div style="font-size:0.95rem; font-weight:bold; margin-bottom:8px; color:#334155;">한 번에 사용할 시간을 선택해 주세요</div>
          <p style="margin:0 0 8px; color:#64748b; font-size:0.78rem;">10분권을 여러 개 모아 20분 또는 30분으로 한 번에 사용할 수 있어요.</p>
          <div class="yt-duration-options" style="display:flex; gap:8px; justify-content:center; margin-bottom:10px;">
            <button type="button" class="btn-duration btn-duration-10" data-duration="10" style="flex:1; padding:11px 6px; font-weight:bold; font-size:0.95rem; border-radius:12px; border:none;">10분</button>
            <button type="button" class="btn-duration btn-duration-20" data-duration="20" style="flex:1; padding:11px 6px; font-weight:bold; font-size:0.95rem; border-radius:12px; border:none;">20분</button>
            <button type="button" class="btn-duration btn-duration-30" data-duration="30" style="flex:1; padding:11px 6px; font-weight:bold; font-size:0.95rem; border-radius:12px; border:none;">30분</button>
          </div>
          <p class="sub" style="color:#666; font-size:0.78rem; margin-top:6px; line-height:1.4;">
            새 YouTube 탭이 열려요.<br>
            게임 탭을 닫지 않아야 종료 알림이 유지돼요.<br>
            일찍 닫아도 사용 시간은 환불되지 않아요.
          </p>
          <div id="yt-result-msg" style="margin-top:8px; font-size:0.88rem; display:none;"></div>
        </div>

        <button class="btn-close" style="margin-top:12px; width:100%;" data-action="close-overlay">닫기</button>
      </div>
    `;
    document.body.appendChild(overlay);

    const lockTrigger = overlay.querySelector('#yt-unlock-trigger');
    const startArea = overlay.querySelector('#yt-start-area');
    const lockArea = overlay.querySelector('#yt-lock-area');
    const resultMsg = overlay.querySelector('#yt-result-msg');
    const displayInv = overlay.querySelector('#yt-modal-inventory');
    const displayDaily = overlay.querySelector('#yt-modal-daily');
    const displayPeriod = overlay.querySelector('#yt-modal-period');
    const displayPeriodLabel = overlay.querySelector('#yt-modal-period-label');
    const durationBtns = overlay.querySelectorAll('.btn-duration');

    const ytQuantityInput = overlay.querySelector('#yt-consume-quantity');
    const ytUseAllBtn = overlay.querySelector('#yt-use-all-btn');
    const ytMinusBtn = overlay.querySelector('#yt-qty-minus');
    const ytPlusBtn = overlay.querySelector('#yt-qty-plus');
    const ytPresetBtns = overlay.querySelectorAll('[data-yt-preset]');
    const deductYtBtn = overlay.querySelector('#deduct-yt-btn');
    const ytTicketBadge = overlay.querySelector('#yt-ticket-count-badge');
    const ytMinutesPreview = overlay.querySelector('#yt-consume-minutes-preview');

    let isYtUnlocked = false;

    function ensureYtUnlocked() {
      if (isYtUnlocked) return true;
      const n1 = Math.floor(Math.random() * 40) + 11;
      const n2 = Math.floor(Math.random() * 40) + 11;
      const answer = prompt(`🔒 [부모님 잠금 해제]\n\n계산해 주세요: ${n1} + ${n2} = ?`);
      if (answer !== null && String(answer).trim() === String(n1 + n2)) {
        isYtUnlocked = true;
        lockArea.style.display = 'none';
        startArea.style.display = 'block';
        updateDurationButtons();
        updateYtQuantity();
        return true;
      }
      if (answer !== null) {
        alert('정답이 아닙니다.');
      }
      return false;
    }

    function getQuotaProjection() {
      if (typeof FreeTimeAllowance !== 'undefined' && typeof FreeTimeAllowance.getRemainingQuota === 'function') {
        let savedUsage = null;
        try {
          savedUsage = JSON.parse(localStorage.getItem(FreeTimeAllowance.STORAGE_KEY) || 'null');
        } catch (e) {}
        return FreeTimeAllowance.getRemainingQuota({ usage: savedUsage, now: Date.now() });
      }
      return null;
    }

    function updateYtQuantity() {
      const currentMinutes = (typeof RewardSystem !== 'undefined' && typeof RewardSystem.getState === 'function')
        ? Number(RewardSystem.getState().youtube_minutes) || 0
        : Number(state.youtube_minutes) || 0;
      const availableTickets = Math.max(0, Math.floor(currentMinutes / 10));

      if (ytTicketBadge) {
        ytTicketBadge.textContent = `보유 ${availableTickets}개 (${currentMinutes}분)`;
      }
      ytQuantityInput.max = String(Math.max(1, availableTickets));
      ytUseAllBtn.textContent = `전부 선택 (${availableTickets}개)`;
      ytUseAllBtn.disabled = availableTickets < 1;

      let quantity = Number(ytQuantityInput.value);
      if (availableTickets > 0 && Number.isSafeInteger(quantity) && quantity > availableTickets) {
        quantity = availableTickets;
        ytQuantityInput.value = String(availableTickets);
      }
      const valid = Number.isSafeInteger(quantity) && quantity >= 1 && quantity <= availableTickets;
      const minutesToDeduct = valid ? quantity * 10 : 0;

      if (ytMinutesPreview) {
        ytMinutesPreview.textContent = valid ? `= ${minutesToDeduct}분` : '= 0분';
      }

      ytPresetBtns.forEach(btn => {
        const presetVal = Number(btn.dataset.ytPreset);
        btn.disabled = availableTickets < presetVal;
        btn.classList.toggle('is-active', valid && quantity === presetVal);
      });
      ytMinusBtn.disabled = !valid || quantity <= 1;
      ytPlusBtn.disabled = !valid || quantity >= availableTickets;

      if (availableTickets < 1) {
        deductYtBtn.textContent = '보유 중인 유튜브 시간이 없습니다 (0분)';
        deductYtBtn.disabled = true;
      } else if (valid) {
        deductYtBtn.textContent = `유튜브 ${quantity}개 (${minutesToDeduct}분) 사용 기록하기`;
        deductYtBtn.disabled = false;
      } else {
        deductYtBtn.textContent = '사용할 개수를 입력해 주세요';
        deductYtBtn.disabled = true;
      }
    }

    function updateStatusDisplay() {
      const quota = getQuotaProjection();
      const currentMinutes = (typeof RewardSystem !== 'undefined' && typeof RewardSystem.getState === 'function')
        ? RewardSystem.getState().youtube_minutes
        : state.youtube_minutes;

      if (displayInv) displayInv.textContent = `${currentMinutes}분`;

      const dailyUsed = quota ? (quota.morningMinutes + quota.afternoonMinutes) : 0;
      if (displayDaily) displayDaily.textContent = `${dailyUsed} / 60분`;

      const isAfternoon = quota
        ? quota.period === (FreeTimeAllowance.PERIOD?.AFTERNOON || 'afternoon')
        : new Date().getHours() >= 12;
      const periodUsed = quota ? (isAfternoon ? quota.afternoonMinutes : quota.morningMinutes) : 0;
      if (displayPeriodLabel) displayPeriodLabel.textContent = `${isAfternoon ? '오후' : '오전'} 사용`;
      if (displayPeriod) displayPeriod.textContent = `${periodUsed} / 30분`;
      updateYtQuantity();
    }

    function updateDurationButtons() {
      const currentMinutes = (typeof RewardSystem !== 'undefined' && typeof RewardSystem.getState === 'function')
        ? RewardSystem.getState().youtube_minutes
        : state.youtube_minutes;

      let savedUsage = null;
      if (typeof FreeTimeAllowance !== 'undefined') {
        try {
          savedUsage = JSON.parse(localStorage.getItem(FreeTimeAllowance.STORAGE_KEY) || 'null');
        } catch (e) {}
      }

      durationBtns.forEach(btn => {
        const d = Number(btn.dataset.duration);
        const inventoryOk = currentMinutes >= d;
        let allowanceOk = false;
        if (typeof FreeTimeAllowance !== 'undefined' && typeof FreeTimeAllowance.evaluateStart === 'function') {
          const auth = FreeTimeAllowance.evaluateStart({ usage: savedUsage, now: Date.now(), durationMinutes: d });
          allowanceOk = auth.allowed;
        }
        const canStart = inventoryOk && allowanceOk;
        btn.disabled = !canStart;
        btn.style.background = canStart ? '#f43f5e' : '#cbd5e1';
        btn.style.color = canStart ? 'white' : '#64748b';
        btn.style.cursor = canStart ? 'pointer' : 'not-allowed';
        btn.style.opacity = canStart ? '1' : '0.6';
      });
    }

    ytQuantityInput.addEventListener('input', updateYtQuantity);
    ytUseAllBtn.addEventListener('click', () => {
      const currentMinutes = Number(RewardSystem.getState().youtube_minutes) || 0;
      const availableTickets = Math.max(0, Math.floor(currentMinutes / 10));
      ytQuantityInput.value = availableTickets > 0 ? String(availableTickets) : '1';
      updateYtQuantity();
    });
    ytMinusBtn.addEventListener('click', () => {
      const current = Math.max(1, (Math.floor(Number(ytQuantityInput.value)) || 1) - 1);
      ytQuantityInput.value = String(current);
      updateYtQuantity();
    });
    ytPlusBtn.addEventListener('click', () => {
      const currentMinutes = Number(RewardSystem.getState().youtube_minutes) || 0;
      const availableTickets = Math.max(1, Math.floor(currentMinutes / 10));
      const next = Math.min(availableTickets, (Math.floor(Number(ytQuantityInput.value)) || 1) + 1);
      ytQuantityInput.value = String(next);
      updateYtQuantity();
    });
    ytPresetBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        ytQuantityInput.value = String(btn.dataset.ytPreset);
        updateYtQuantity();
      });
    });

    deductYtBtn.addEventListener('click', () => {
      // 두 번 눌러도 두 번 차감되지 않도록 커밋 직후 잠깐 잠근다.
      if (deductYtBtn.disabled) return;
      deductYtBtn.disabled = true;
      setTimeout(() => { deductYtBtn.disabled = false; }, 500);
      const quantity = Math.floor(Number(ytQuantityInput.value));
      if (!Number.isSafeInteger(quantity) || quantity < 1) return;
      if (!ensureYtUnlocked()) return;
      RewardSystem.consumeInternal('youtube', (newState) => {
        updateStatusDisplay();
        updateDurationButtons();
        if (newState.youtube_minutes < 10) {
          setTimeout(() => overlay.remove(), 400);
        }
      }, quantity);
    });

    updateStatusDisplay();

    const ytNormalizeBtn = overlay.querySelector('#yt-normalize-btn');
    if (ytNormalizeBtn) {
      ytNormalizeBtn.addEventListener('click', () => {
        const curr = Number(RewardSystem.getState().youtube_minutes) || 0;
        const normalized = (typeof RewardSystem.normalizeYoutubeMinutes === 'function')
          ? RewardSystem.normalizeYoutubeMinutes()
          : Math.max(0, Math.floor(curr / 10) * 10);
        RewardSystemUI.showToast(`찌꺼기 정리 완료: ${normalized}분`);
        overlay.remove();
        if (typeof RewardSystemUI !== 'undefined') RewardSystemUI.updateUI(RewardSystem.getState());
      });
    }

    lockTrigger.addEventListener('click', () => {
      ensureYtUnlocked();
    });

    function showResult(code, duration) {
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
          break;
        case 'insufficient_time':
          resultMsg.style.color = '#dc2626';
          resultMsg.textContent = '사용할 시간이 부족해요. 현재 남은 시간을 확인하세요.';
          break;
        case 'invalid_duration':
          resultMsg.style.color = '#dc2626';
          resultMsg.textContent = '올바르지 않은 시간 설정이에요 (10/20/30분).';
          break;
        case 'exceeds_period_allowance': {
          const isAfternoon = (typeof FreeTimeAllowance !== 'undefined' && typeof FreeTimeAllowance.getPeriod === 'function')
            ? FreeTimeAllowance.getPeriod(Date.now()) === (FreeTimeAllowance.PERIOD?.AFTERNOON || 'afternoon')
            : new Date().getHours() >= 12;
          resultMsg.style.color = '#dc2626';
          resultMsg.textContent = isAfternoon
            ? '오후 자유시간 30분을 모두 사용했어요. 내일 다시 사용할 수 있어요.'
            : '오전 자유시간 30분을 모두 사용했어요. 오후에 다시 사용할 수 있어요.';
          break;
        }
        case 'exceeds_daily_allowance':
          resultMsg.style.color = '#dc2626';
          resultMsg.textContent = '오늘 하루 사용 한도(60분)를 초과했어요. 내일 다시 사용할 수 있어요.';
          break;
        case 'crosses_boundary':
          resultMsg.style.color = '#dc2626';
          resultMsg.textContent = '지금은 선택한 시간을 다 사용할 수 없어요. 가능한 시간을 선택해 주세요.';
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

    durationBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const duration = Number(btn.dataset.duration);
        durationBtns.forEach(b => { b.disabled = true; });
        resultMsg.style.display = 'none';

        try {
          primeFreeTimeAlertAudio();
        } catch (e) {
          // audio preparation failure must not block session start
        }

        const result = RewardSystem.startYouTubeSession(duration, { isDirectUserStart: true });
        showResult(result.code, duration);

        if (result.code === 'started') {
          updateStatusDisplay();
          setTimeout(() => overlay.remove(), 1500);
        } else {
          updateDurationButtons();
        }
      });
    });
  }

  function openSnackModal(state) {
    const overlay = createModalOverlay('reward-snack-modal');
    const initialCount = state && typeof state.snacks === 'number' ? state.snacks : 0;
    overlay.innerHTML = `
      <div class="reward-modal-content" style="color:#0f172a;">
        <div class="icon-bounce" style="font-size:2.8rem; margin-bottom:8px;">🍪</div>
        <h3 style="margin:0; font-size:1.35rem; color:#0f172a; font-weight:800;">확보된 간식</h3>
        <div class="secured-snack-display" style="font-size:2.3rem; font-weight:800; color:#8b5cf6; margin:10px 0;">
          ${initialCount}개
        </div>
        <p class="sub" style="color:#475569; font-size:0.86rem; margin-bottom:12px;">과일, 요거트, 또는 좋아하는 과자를 골라 드신 뒤 부모님께서 한 번에 여러 개를 소진·기록해 주세요.</p>

        <div id="snack-deduct-area" class="reward-bulk-box" style="display:block; margin-top:10px; padding:12px 14px; background:#f5f3ff; border:1.5px solid #ddd6fe; border-radius:16px; text-align:left; color:#0f172a;">
          <label for="snack-consume-quantity" style="display:block; margin-bottom:8px; color:#5b21b6; font-size:0.88rem; font-weight:800;">⚡ 부모님용 · 한 번에 사용할 개수 선택</label>
          <div class="reward-preset-row" style="display:flex; flex-wrap:wrap; gap:5px; margin-bottom:8px;">
            <button type="button" class="reward-preset-btn" data-snack-preset="1" style="flex:1 1 auto; padding:6px 8px; border-radius:8px; border:1.5px solid #ddd6fe; background:#ffffff; color:#5b21b6; font-size:0.8rem; font-weight:700; cursor:pointer;">1개</button>
            <button type="button" class="reward-preset-btn" data-snack-preset="2" style="flex:1 1 auto; padding:6px 8px; border-radius:8px; border:1.5px solid #ddd6fe; background:#ffffff; color:#5b21b6; font-size:0.8rem; font-weight:700; cursor:pointer;">2개</button>
            <button type="button" class="reward-preset-btn" data-snack-preset="3" style="flex:1 1 auto; padding:6px 8px; border-radius:8px; border:1.5px solid #ddd6fe; background:#ffffff; color:#5b21b6; font-size:0.8rem; font-weight:700; cursor:pointer;">3개</button>
            <button type="button" class="reward-preset-btn" data-snack-preset="5" style="flex:1 1 auto; padding:6px 8px; border-radius:8px; border:1.5px solid #ddd6fe; background:#ffffff; color:#5b21b6; font-size:0.8rem; font-weight:700; cursor:pointer;">5개</button>
            <button type="button" id="snack-use-all-btn" class="reward-preset-btn reward-use-all-btn" style="flex:1 1 auto; padding:6px 8px; border-radius:8px; border:1.5px solid #8b5cf6; background:#ede9fe; color:#5b21b6; font-size:0.8rem; font-weight:800; cursor:pointer;">전부 선택 (${initialCount}개)</button>
          </div>
          <div class="reward-qty-row" style="display:flex; align-items:center; gap:8px; margin-bottom:10px;">
            <button type="button" id="snack-qty-minus" class="reward-qty-stepper" aria-label="간식 소진 개수 감소" style="width:38px; height:38px; border-radius:10px; border:1.5px solid #cbd5e1; background:#ffffff; color:#0f172a; font-size:1.15rem; font-weight:800; cursor:pointer;">−</button>
            <input id="snack-consume-quantity" type="number" min="1" max="${Math.max(1, initialCount)}" value="1" inputmode="numeric" aria-label="한 번에 사용할 간식 개수" style="flex:1; min-width:70px; padding:8px 10px; border:1.5px solid #cbd5e1; border-radius:10px; font-size:1.05rem; font-weight:800; color:#0f172a; background:#ffffff; text-align:center;">
            <button type="button" id="snack-qty-plus" class="reward-qty-stepper" aria-label="간식 소진 개수 증가" style="width:38px; height:38px; border-radius:10px; border:1.5px solid #cbd5e1; background:#ffffff; color:#0f172a; font-size:1.15rem; font-weight:800; cursor:pointer;">+</button>
          </div>
          <button class="btn-primary" id="deduct-snack-btn" style="background:#8b5cf6; border-color:#7c3aed; width:100%; margin-bottom:0; padding:12px;">간식 1개 사용 기록하기</button>
        </div>

        <div id="snack-lock-area" style="margin: 12px 0 4px;">
          <button id="snack-unlock-trigger" style="background:#f8fafc; border:1.5px solid #cbd5e1; border-radius:12px; padding:6px 14px; font-size:1.1rem; cursor:pointer; display:inline-flex; align-items:center; gap:6px; color:#334155; font-weight:700;" title="부모님용 잠금 해제">
            <span>🔒</span>
            <span style="font-size:0.8rem;">부모님 사전 잠금 해제</span>
          </button>
        </div>

        <button class="btn-close" style="margin-top:12px;" data-action="close-overlay">닫기</button>
      </div>
    `;
    document.body.appendChild(overlay);

    const lockTrigger = overlay.querySelector('#snack-unlock-trigger');
    const deductArea = overlay.querySelector('#snack-deduct-area');
    const lockArea = overlay.querySelector('#snack-lock-area');
    const deductBtn = overlay.querySelector('#deduct-snack-btn');
    const quantityInput = overlay.querySelector('#snack-consume-quantity');
    const useAllBtn = overlay.querySelector('#snack-use-all-btn');
    const snackMinusBtn = overlay.querySelector('#snack-qty-minus');
    const snackPlusBtn = overlay.querySelector('#snack-qty-plus');
    const snackPresetBtns = overlay.querySelectorAll('[data-snack-preset]');
    const display = overlay.querySelector('.secured-snack-display');

    let isSnackUnlocked = false;

    function ensureSnackUnlocked() {
      if (isSnackUnlocked) return true;
      const n1 = Math.floor(Math.random() * 40) + 11;
      const n2 = Math.floor(Math.random() * 40) + 11;
      const answer = prompt(`🔒 [부모님 잠금 해제]\n\n계산해 주세요: ${n1} + ${n2} = ?`);

      if (answer !== null && String(answer).trim() === String(n1 + n2)) {
        isSnackUnlocked = true;
        lockArea.style.display = 'none';
        deductArea.style.display = 'block';
        return true;
      } else if (answer !== null) {
        alert('정답이 아닙니다.');
      }
      return false;
    }

    function updateSnackQuantity() {
      const available = Number(RewardSystem.getState().snacks) || 0;
      quantityInput.max = String(Math.max(1, available));
      useAllBtn.textContent = `전부 선택 (${available}개)`;
      useAllBtn.disabled = available < 1;
      let quantity = Number(quantityInput.value);
      if (available > 0 && Number.isSafeInteger(quantity) && quantity > available) {
        quantity = available;
        quantityInput.value = String(available);
      }
      const valid = Number.isSafeInteger(quantity) && quantity >= 1 && quantity <= available;

      snackPresetBtns.forEach(btn => {
        const presetVal = Number(btn.dataset.snackPreset);
        btn.disabled = available < presetVal;
        btn.classList.toggle('is-active', valid && quantity === presetVal);
      });
      snackMinusBtn.disabled = !valid || quantity <= 1;
      snackPlusBtn.disabled = !valid || quantity >= available;

      if (available < 1) {
        deductBtn.textContent = '보유 중인 간식이 없습니다 (0개)';
        deductBtn.disabled = true;
      } else {
        deductBtn.textContent = valid ? `간식 ${quantity}개 사용 기록하기` : '사용할 개수를 입력해 주세요';
        deductBtn.disabled = !valid;
      }
    }

    quantityInput.addEventListener('input', updateSnackQuantity);
    useAllBtn.addEventListener('click', () => {
      const available = Number(RewardSystem.getState().snacks) || 0;
      quantityInput.value = available > 0 ? String(available) : '';
      updateSnackQuantity();
    });
    snackMinusBtn.addEventListener('click', () => {
      const current = Math.max(1, (Math.floor(Number(quantityInput.value)) || 1) - 1);
      quantityInput.value = String(current);
      updateSnackQuantity();
    });
    snackPlusBtn.addEventListener('click', () => {
      const available = Math.max(1, Number(RewardSystem.getState().snacks) || 0);
      const next = Math.min(available, (Math.floor(Number(quantityInput.value)) || 1) + 1);
      quantityInput.value = String(next);
      updateSnackQuantity();
    });
    snackPresetBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        quantityInput.value = String(btn.dataset.snackPreset);
        updateSnackQuantity();
      });
    });
    updateSnackQuantity();

    lockTrigger.addEventListener('click', () => {
      ensureSnackUnlocked();
    });

    deductBtn.addEventListener('click', () => {
      if (deductBtn.disabled) return;
      deductBtn.disabled = true;
      setTimeout(() => { deductBtn.disabled = false; }, 500);
      const quantity = Math.floor(Number(quantityInput.value));
      if (!Number.isSafeInteger(quantity) || quantity < 1) return;
      if (!ensureSnackUnlocked()) return;
      RewardSystem.consumeInternal('snack', (newState) => {
        display.textContent = `${newState.snacks}개`;
        if (newState.snacks < 1) {
          setTimeout(() => overlay.remove(), 400);
        } else {
          updateSnackQuantity();
        }
      }, quantity);
    });
  }

  function openMarbleModal() {
    // Route all entry points through the shared per-entry learning gate.
    if (window.StudyGameAdmission) window.StudyGameAdmission.request('marble');
  }

  function openBubbleModal() {
    // Route all entry points through the shared per-entry learning gate.
    if (window.StudyGameAdmission) window.StudyGameAdmission.request('bubble');
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
    const initialCount = Number(state.custom_inventory[item.id]) || 0;
    overlay.innerHTML = `
      <div class="reward-modal-content" style="color:#0f172a;">
        <div class="icon-bounce" style="font-size:3rem; margin-bottom:10px;">${item.icon}</div>
        <h3 style="font-size:1.45rem; color:#0f172a; font-weight:800; margin:0;">${item.label}</h3>
        <p style="color:#475569; margin-top:6px; font-weight:700;">확보 인벤토리: <span id="custom-modal-inventory" style="color:#e11d48; font-weight:800;">${initialCount}</span>개</p>
        
        <div class="reward-bulk-box" style="margin: 16px 0; padding:12px 14px; background:#fff1f2; border:1.5px solid #fecdd3; border-radius:16px; text-align:left; color:#0f172a;">
          <label for="custom-consume-quantity" style="display:block; margin-bottom:8px; color:#be123c; font-size:0.88rem; font-weight:800;">⚡ 부모님용 · 한 번에 사용할 개수 선택</label>
          <div class="reward-preset-row" style="display:flex; flex-wrap:wrap; gap:5px; margin-bottom:8px;">
            <button type="button" class="reward-preset-btn" data-custom-preset="1" style="flex:1 1 auto; padding:6px 8px; border-radius:8px; border:1.5px solid #fecdd3; background:#ffffff; color:#9f1239; font-size:0.8rem; font-weight:700; cursor:pointer;">1개</button>
            <button type="button" class="reward-preset-btn" data-custom-preset="2" style="flex:1 1 auto; padding:6px 8px; border-radius:8px; border:1.5px solid #fecdd3; background:#ffffff; color:#9f1239; font-size:0.8rem; font-weight:700; cursor:pointer;">2개</button>
            <button type="button" class="reward-preset-btn" data-custom-preset="3" style="flex:1 1 auto; padding:6px 8px; border-radius:8px; border:1.5px solid #fecdd3; background:#ffffff; color:#9f1239; font-size:0.8rem; font-weight:700; cursor:pointer;">3개</button>
            <button type="button" class="reward-preset-btn" data-custom-preset="5" style="flex:1 1 auto; padding:6px 8px; border-radius:8px; border:1.5px solid #fecdd3; background:#ffffff; color:#9f1239; font-size:0.8rem; font-weight:700; cursor:pointer;">5개</button>
            <button type="button" id="custom-use-all-btn" class="reward-preset-btn reward-use-all-btn" style="flex:1 1 auto; padding:6px 8px; border-radius:8px; border:1.5px solid #f43f5e; background:#ffe4e6; color:#be123c; font-size:0.8rem; font-weight:800; cursor:pointer;">전부 선택 (${initialCount}개)</button>
          </div>
          <div class="reward-qty-row" style="display:flex; align-items:center; gap:8px; margin-bottom:10px;">
            <button type="button" id="custom-qty-minus" class="reward-qty-stepper" aria-label="${item.label} 소진 개수 감소" style="width:38px; height:38px; border-radius:10px; border:1.5px solid #cbd5e1; background:#ffffff; color:#0f172a; font-size:1.15rem; font-weight:800; cursor:pointer;">−</button>
            <input id="custom-consume-quantity" type="number" min="1" max="${Math.max(1, initialCount)}" value="1" inputmode="numeric" aria-label="한 번에 사용할 ${item.label} 개수" style="flex:1; min-width:70px; padding:8px 10px; border:1.5px solid #cbd5e1; border-radius:10px; font-size:1.05rem; font-weight:800; color:#0f172a; background:#ffffff; text-align:center;">
            <button type="button" id="custom-qty-plus" class="reward-qty-stepper" aria-label="${item.label} 소진 개수 증가" style="width:38px; height:38px; border-radius:10px; border:1.5px solid #cbd5e1; background:#ffffff; color:#0f172a; font-size:1.15rem; font-weight:800; cursor:pointer;">+</button>
          </div>
          <button class="btn-primary" id="deduct-custom-btn" style="background:#f43f5e; border-color:#e11d48; width:100%; margin-bottom:0; padding:12px;">1개 사용 승인하기 (권장: 부모님)</button>
        </div>
        <button class="btn-close" data-action="close-overlay">닫기</button>
      </div>
    `;
    document.body.appendChild(overlay);

    const deductBtn = overlay.querySelector('#deduct-custom-btn');
    const quantityInput = overlay.querySelector('#custom-consume-quantity');
    const useAllBtn = overlay.querySelector('#custom-use-all-btn');
    const customMinusBtn = overlay.querySelector('#custom-qty-minus');
    const customPlusBtn = overlay.querySelector('#custom-qty-plus');
    const customPresetBtns = overlay.querySelectorAll('[data-custom-preset]');
    const inventoryDisplay = overlay.querySelector('#custom-modal-inventory');

    function updateCustomQuantity() {
      const available = Number(RewardSystem.getState().custom_inventory[item.id]) || 0;
      quantityInput.max = String(Math.max(1, available));
      useAllBtn.textContent = `전부 선택 (${available}개)`;
      useAllBtn.disabled = available < 1;
      let quantity = Number(quantityInput.value);
      if (available > 0 && Number.isSafeInteger(quantity) && quantity > available) {
        quantity = available;
        quantityInput.value = String(available);
      }
      const valid = Number.isSafeInteger(quantity) && quantity >= 1 && quantity <= available;

      customPresetBtns.forEach(btn => {
        const presetVal = Number(btn.dataset.customPreset);
        btn.disabled = available < presetVal;
        btn.classList.toggle('is-active', valid && quantity === presetVal);
      });
      customMinusBtn.disabled = !valid || quantity <= 1;
      customPlusBtn.disabled = !valid || quantity >= available;

      if (available < 1) {
        deductBtn.textContent = `보유 중인 ${item.label} 보상이 없습니다 (0개)`;
        deductBtn.disabled = true;
      } else {
        deductBtn.textContent = valid ? `${quantity}개 사용 승인하기 (권장: 부모님)` : '사용할 개수를 입력해 주세요';
        deductBtn.disabled = !valid;
      }
      inventoryDisplay.textContent = String(available);
    }

    quantityInput.addEventListener('input', updateCustomQuantity);
    useAllBtn.addEventListener('click', () => {
      const available = Number(RewardSystem.getState().custom_inventory[item.id]) || 0;
      quantityInput.value = available > 0 ? String(available) : '';
      updateCustomQuantity();
    });
    customMinusBtn.addEventListener('click', () => {
      const current = Math.max(1, (Math.floor(Number(quantityInput.value)) || 1) - 1);
      quantityInput.value = String(current);
      updateCustomQuantity();
    });
    customPlusBtn.addEventListener('click', () => {
      const available = Math.max(1, Number(RewardSystem.getState().custom_inventory[item.id]) || 0);
      const next = Math.min(available, (Math.floor(Number(quantityInput.value)) || 1) + 1);
      quantityInput.value = String(next);
      updateCustomQuantity();
    });
    customPresetBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        quantityInput.value = String(btn.dataset.customPreset);
        updateCustomQuantity();
      });
    });
    updateCustomQuantity();

    deductBtn.addEventListener('click', () => {
      if (deductBtn.disabled) return;
      deductBtn.disabled = true;
      setTimeout(() => { deductBtn.disabled = false; }, 500);
      const quantity = Math.floor(Number(quantityInput.value));
      RewardSystem.consumeInternal(item.id, (newState) => {
        const remaining = Number(newState.custom_inventory[item.id]) || 0;
        if (remaining < 1) {
          overlay.remove();
        } else {
          updateCustomQuantity();
        }
      }, quantity);
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
      case 'go-main-reward':
        {
          const dest = target.getAttribute('href') || resolveMainHubUrl();
          window.location.href = dest;
          e.stopPropagation();
        }
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
      case 'exchange-gem':
        if (typeof RewardSystem !== 'undefined' && RewardSystem.exchangeGem) {
          RewardSystem.exchangeGem(itemId);
          const logContainer = document.querySelector('#reward-shop-overlay .reward-activity-log');
          if (logContainer && typeof RewardSystem.getState === 'function') {
            logContainer.outerHTML = renderActivityLog(RewardSystem.getState());
          }
        }
        e.stopPropagation();
        break;
      case 'filter-activity-log': {
        currentActivityFilter = target.dataset.filterType || 'all';
        const logContainer = target.closest('.reward-activity-log');
        if (logContainer && typeof RewardSystem !== 'undefined' && typeof RewardSystem.getState === 'function') {
          logContainer.outerHTML = renderActivityLog(RewardSystem.getState());
        }
        e.stopPropagation();
        break;
      }
      case 'close-overlay': {
        const overlay = target.closest('.reward-modal-overlay, .reward-choice-overlay');
        if (overlay) overlay.remove();
        e.stopPropagation();
        break;
      }
    }
  });

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
      session.status = 'acknowledged';
      session.acknowledgedAt = Date.now();
      try {
        localStorage.setItem('study_youtube_free_time_session_v1', JSON.stringify(session));
      } catch (e) {}
      if (window.SyncEngine && typeof window.SyncEngine.pushStats === 'function') {
        window.SyncEngine.pushStats('study_youtube_free_time_session_v1', session);
      }

      overlay.remove();
      currentActiveSession = null;
      restoreContextualControl();
    });
  }

  function clearFreeTimeSessionUI() {
    if (sessionMonitorIntervalId) {
      clearInterval(sessionMonitorIntervalId);
      sessionMonitorIntervalId = null;
    }
    currentActiveSession = null;
    const existingOverlay = document.getElementById('yt-expired-overlay');
    if (existingOverlay) {
      existingOverlay.remove();
    }
    if (activePipWindow && !activePipWindow.closed) {
      try { activePipWindow.close(); } catch (e) {}
      activePipWindow = null;
    }
    restoreContextualControl();
  }

  function startSessionMonitor(session) {
    if (sessionMonitorIntervalId) {
      clearInterval(sessionMonitorIntervalId);
      sessionMonitorIntervalId = null;
    }
    currentActiveSession = session;

    function tick() {
      try {
        const raw = localStorage.getItem('study_youtube_free_time_session_v1');
        if (raw) {
          const saved = JSON.parse(raw);
          if (saved && saved.sessionId === session.sessionId) {
            if (saved.status === 'acknowledged') {
              clearFreeTimeSessionUI();
              return;
            }
            session.endsAt = saved.endsAt || session.endsAt;
            session.status = saved.status || session.status;
            session.warningEmittedAt = saved.warningEmittedAt || session.warningEmittedAt;
            session.expiredAt = saved.expiredAt || session.expiredAt;
          }
        }
      } catch (e) {}

      const deadline = session.endsAt || Date.now();
      const remainingMs = Math.max(0, deadline - Date.now());

      // 1-minute warning: remaining <= 60s, exactly once
      if (remainingMs <= 60000 && remainingMs > 0 && !session.warningEmittedAt) {
        session.warningEmittedAt = Date.now();
        try {
          localStorage.setItem('study_youtube_free_time_session_v1', JSON.stringify(session));
        } catch (e) {}
        triggerAudioAlert();
      }

      // Expiry transition
      if (remainingMs <= 0) {
        clearInterval(sessionMonitorIntervalId);
        sessionMonitorIntervalId = null;
        session.status = 'expired';
        session.expiredAt = session.expiredAt || Date.now();
        try {
          localStorage.setItem('study_youtube_free_time_session_v1', JSON.stringify(session));
        } catch (e) {}
        if (window.SyncEngine && typeof window.SyncEngine.pushStats === 'function') {
          window.SyncEngine.pushStats('study_youtube_free_time_session_v1', session);
        }
        currentActiveSession = null;
        restoreContextualControl();
        if (activePipWindow && !activePipWindow.closed) {
          try { activePipWindow.close(); } catch (e) {}
          activePipWindow = null;
        }
        renderExpiryOverlay(session);
        return;
      }

      updateContextualCountdown(session, remainingMs);

      if (activePipWindow && !activePipWindow.closed && activePipWindow.document) {
        const pipText = activePipWindow.document.getElementById('pip-timer-text');
        if (pipText) {
          pipText.textContent = formatTimeMMSS(remainingMs);
        }
      }
    }

    tick();
    sessionMonitorIntervalId = setInterval(tick, 1000);
  }

  function renderFreeTimeTimerUI(session, options) {
    if (!session || session.status !== 'running') return;
    startSessionMonitor(session);

    const isDirectUserStart = Boolean(options && options.isDirectUserStart);
    if (isDirectUserStart && 'documentPictureInPicture' in window && typeof window.documentPictureInPicture.requestWindow === 'function') {
      try {
        const deadline = session.endsAt || Date.now();
        const initialRem = Math.max(0, deadline - Date.now());
        window.documentPictureInPicture.requestWindow({ width: 320, height: 140 }).then((pipWin) => {
          activePipWindow = pipWin;
          pipWin.document.body.innerHTML = `
            <div style="font-family: sans-serif; padding: 12px; background: #0f172a; color: white; border-radius: 8px; text-align: center;">
              <div style="font-size: 0.9rem; font-weight: bold; color: #f43f5e;">📺 유튜브 자유시간</div>
              <div id="pip-timer-text" style="font-size: 2rem; font-weight: bold; margin: 6px 0;">${formatTimeMMSS(initialRem)}</div>
              <div style="font-size: 0.75rem; color: #94a3b8;">게임 탭을 닫지 마세요</div>
            </div>
          `;
          pipWin.addEventListener('unload', () => {
            activePipWindow = null;
          });
        }).catch(() => {
          // Document PiP rejected or failed: session continues seamlessly without global fixed bar
        });
      } catch (e) {
        // Document PiP exception: session continues seamlessly
      }
    }
  }

  function renderExpiredFreeTimeSessionUI(session) {
    if (!session || session.status !== 'expired') return;
    renderExpiryOverlay(session);
  }

  return {
    injectCriticalStyles, injectStyles, injectInventoryBar, syncInventoryBarWithState, applyBodyTopOffset, updateUI,
    playEntranceAndAddGem, openShopModal, spawnExplosion, showToast, showGrowthToast,
    openYoutubeModal, openSnackModal, openMarbleModal, openBubbleModal, openCustomModal,
    renderFreeTimeTimerUI, renderExpiredFreeTimeSessionUI, clearFreeTimeSessionUI
  };
})();

if (typeof window !== 'undefined') {
  window.RewardSystemUI = RewardSystemUI;
}
