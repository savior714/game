/* ═══════════════════════════════════
   연속 정답 & 로켓 스트릭
═══════════════════════════════════ */
function updateStreak(correct) {
  if (correct) {
    streak++;
    if (streak >= LAUNCH_STREAK) {
      launchRocket();
      return;
    }
    updateRocketUI();
  } else {
    const prevStreak = streak;
    streak = 0;
    if (prevStreak > 0) {
      crashRocket();
      return;
    }
    updateRocketUI();
  }
}

function updateRocketUI() {
  const progress  = Math.min(streak / LAUNCH_STREAK, 1);
  const bottomPx  = Math.round(progress * ROCKET_MAX_BOTTOM);
  const rocket    = document.getElementById('rp-rocket');
  const flame     = document.getElementById('rp-flame');
  const badge     = document.getElementById('streak-badge');

  rocket.style.bottom = bottomPx + 'px';
  flame.style.bottom  = (bottomPx - 28) + 'px';

  if (streak > 0) {
    flame.style.opacity = '1';
    flame.classList.add('flickering');
  } else {
    flame.style.opacity = '0';
    flame.classList.remove('flickering');
  }

  if (streak >= 15 && !launching) {
    rocket.classList.add('pre-launch');
  } else {
    rocket.classList.remove('pre-launch');
  }

  if (streak >= 18) {
    badge.textContent = `\uD83D\uDE80 \uBC1C\uc0ac ${LAUNCH_STREAK - streak}\uCD08\uc804!`;
    badge.classList.add('pre-launch');
  } else {
    badge.textContent = `\uD83D\uDD25 ${streak} / ${LAUNCH_STREAK}`;
    badge.classList.remove('pre-launch');
  }
}

/* ═══════════════════════════════════
   로켓 발사 시퀀스
═══════════════════════════════════ */
function launchRocket() {
  if (launching) return;
  launching = true;

  const rocket = document.getElementById('rp-rocket');
  const flame  = document.getElementById('rp-flame');
  const track  = document.getElementById('rp-track');
  const panel  = document.getElementById('rocket-panel');

  rocket.classList.remove('pre-launch', 'flickering');
  badgeReset();
  rocket.classList.add('igniting');
  flame.classList.remove('flickering');
  flame.classList.add('igniting');
  flame.style.opacity = '1';
  panel.classList.add('shaking');

  setTimeout(() => {
    rocket.classList.remove('igniting');
    rocket.classList.add('blasting');
    flame.classList.remove('igniting');
    flame.classList.add('blasting');
    track.classList.add('warping');
    panel.classList.remove('shaking');

    flashScreen();

    for (let i = 0; i < 7; i++) {
      setTimeout(() => spawnExhaust(), i * 90);
    }

    rocket.style.transition = 'bottom 1.0s cubic-bezier(0.4, 0, 1, 1)';
    flame.style.transition  = 'bottom 1.0s cubic-bezier(0.4, 0, 1, 1)';
    rocket.style.bottom = '440px';
    flame.style.bottom  = '412px';

    setTimeout(() => {
      globalBoost = Math.min(globalBoost + 1, 2);
      streak = 0;

      rocket.classList.remove('blasting');
      flame.classList.remove('blasting');
      track.classList.remove('warping');

      rocket.style.transition = 'none';
      flame.style.transition  = 'none';
      rocket.style.bottom = '4px';
      flame.style.bottom  = '-24px';
      flame.style.opacity = '0';

      requestAnimationFrame(() => requestAnimationFrame(() => {
        rocket.style.transition = 'bottom 0.55s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
        flame.style.transition  = 'bottom 0.55s cubic-bezier(0.25, 0.46, 0.45, 0.94), opacity 0.3s';
        updateRocketUI();
        launching = false;
      }));

      showBoostBanner();
    }, 1100);
  }, 600);
}

function badgeReset() {
  document.getElementById('streak-badge').classList.remove('pre-launch');
}

function showBoostBanner() {
  const boostNames = ['', '레벨 1', '레벨 2', '최고 레벨'];
  const banner = document.createElement('div');
  banner.className = 'boost-banner';
  banner.innerHTML = `
    🚀 우주 돌파!
    <div class="sub">전체 난이도 ${boostNames[globalBoost]} 상승!</div>
  `;
  document.body.appendChild(banner);
  setTimeout(() => banner.remove(), 3000);
  spawnConfetti();
  spawnConfetti();

  // 전역 보상 시스템의 룰렛 연출 호출
  setTimeout(() => {
    if (typeof RewardSystem !== 'undefined') {
      RewardSystem.playEntranceAndOpenRoulette('rp-rocket');
    }
  }, 250);
}

/* ═══════════════════════════════════
   추락 시퀀스
═══════════════════════════════════ */
function crashRocket() {
  if (crashing || launching) return;

  // 그물망 발동 체크
  if (hasNet) {
    hasNet = false;
    netStreak = 0;
    netBounceRocket();
    return;
  }

  crashing = true;

  const rocket = document.getElementById('rp-rocket');
  const flame  = document.getElementById('rp-flame');
  const badge  = document.getElementById('streak-badge');

  flame.style.opacity = '0';
  flame.classList.remove('flickering', 'blasting', 'igniting');
  rocket.classList.remove('pre-launch', 'blasting', 'igniting');
  badge.classList.remove('pre-launch');

  // Phase 1: 폭발 (0-500ms)
  rocket.classList.add('exploding');
  flashScreenRed();
  spawnExplosion();

  setTimeout(() => {
    // Phase 2: 추락 스핀 (500-1550ms)
    rocket.classList.remove('exploding');
    rocket.classList.add('crashing');
    rocket.style.transition = 'bottom 1.05s cubic-bezier(0.55, 0, 1, 0.5)';
    rocket.style.bottom = '4px';

    for (let i = 0; i < 5; i++) {
      setTimeout(() => spawnSmoke(), i * 160);
    }

    setTimeout(() => {
      // Phase 3: 충돌 바운스 (1550-2000ms)
      rocket.classList.remove('crashing');
      rocket.classList.add('crash-impact');
      spawnImpactDust();

      setTimeout(() => {
        rocket.classList.remove('crash-impact');
        rocket.style.transition = 'bottom 0.55s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
        crashing = false;
        updateRocketUI();
      }, 450);
    }, 1080);
  }, 500);
}

/* ═══════════════════════════════════
   그물망 튕김 (추락 막기)
═══════════════════════════════════ */
function netBounceRocket() {
  const rocket = document.getElementById('rp-rocket');
  const flame  = document.getElementById('rp-flame');
  const badge  = document.getElementById('streak-badge');
  const track  = document.getElementById('rp-track');

  // 현재 로켓 위치 저장
  const savedBottom = rocket.style.bottom || '4px';

  flame.style.opacity = '0';
  flame.classList.remove('flickering', 'blasting', 'igniting');
  rocket.classList.remove('pre-launch', 'blasting', 'igniting');
  badge.classList.remove('pre-launch');

  // Phase 1: 파랑빛 플래시 (추락 시작)
  flashScreenBlue();

  // Phase 2: 로켓 추락 시작
  rocket.classList.add('net-falling');
  rocket.style.transition = 'bottom 0.9s cubic-bezier(0.55, 0, 1, 0.45)';
  rocket.style.bottom = '34px'; // 그물 높이로 추락

  // 추락 중 연기
  for (let i = 0; i < 4; i++) {
    setTimeout(() => spawnSmoke(), i * 120);
  }

  setTimeout(() => {
    // Phase 3: 그물 등장 + 튕김 효과
    rocket.classList.remove('net-falling');
    spawnNetEffect(track);
    flashScreenNet();

    // 튕김 애니메이션
    rocket.classList.add('net-bounce');
    rocket.style.transition = 'none';

    setTimeout(() => {
      rocket.classList.remove('net-bounce');
      // Phase 4: 다시 위로 올라가기 (스프링 바운스)
      const targetBottom = savedBottom;
      rocket.style.transition = 'bottom 0.85s cubic-bezier(0.34, 1.56, 0.64, 1)';
      flame.style.transition  = 'bottom 0.85s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.4s';
      rocket.style.bottom = targetBottom;
      const rocketPx = parseInt(targetBottom, 10) || 4;
      flame.style.bottom = (rocketPx - 28) + 'px';
      flame.style.opacity = streak > 0 ? '1' : '0';
      if (streak > 0) flame.classList.add('flickering');

      // 튕김 후 상태 복원 + 배너
      setTimeout(() => {
        updateRocketUI();
        showNetActivatedBanner();
      }, 900);
    }, 350);
  }, 950);
}

function flashScreenBlue() {
  const flash = document.createElement('div');
  flash.style.cssText = `position:fixed;inset:0;background:rgba(30,120,255,0.32);
    pointer-events:none;z-index:300;animation:screen-flash 0.5s ease forwards;`;
  document.body.appendChild(flash);
  setTimeout(() => flash.remove(), 600);
}

function flashScreenNet() {
  const flash = document.createElement('div');
  flash.style.cssText = `position:fixed;inset:0;background:rgba(0,210,120,0.28);
    pointer-events:none;z-index:300;animation:screen-flash 0.6s ease forwards;`;
  document.body.appendChild(flash);
  setTimeout(() => flash.remove(), 700);
}

function spawnNetEffect(track) {
  const net = document.createElement('div');
  net.className = 'net-element';
  net.innerHTML = `<svg width="64" height="30" viewBox="0 0 64 30" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <pattern id="np${Date.now()}" x="0" y="0" width="8" height="8" patternUnits="userSpaceOnUse">
        <path d="M0 0 L8 0 L8 8 L0 8 Z" fill="none" stroke="rgba(0,220,130,0.9)" stroke-width="1.3"/>
        <line x1="0" y1="0" x2="8" y2="8" stroke="rgba(0,220,130,0.55)" stroke-width="0.8"/>
        <line x1="8" y1="0" x2="0" y2="8" stroke="rgba(0,220,130,0.55)" stroke-width="0.8"/>
      </pattern>
    </defs>
    <rect width="64" height="30" rx="3" fill="url(#np${Date.now()})"/>
    <rect width="64" height="30" rx="3" fill="none" stroke="rgba(0,255,150,0.95)" stroke-width="2.5"/>
  </svg>`;
  track.appendChild(net);
  setTimeout(() => net.remove(), 1800);
}

function showNetBanner() {
  const banner = document.createElement('div');
  banner.className = 'net-banner net-earned';
  banner.innerHTML = `\uD83D\uDEF8 \uADF8\uBB3C\uB9DD \uD68D\uB4DD!<div class="sub">5\uC5F0\uC18D \uC815\uB2F5! \uCD94\uB099 1\uD68C \uBCF4\uD638\uBC1B\uC73C\uC138\uC694 \uD83D\uDEE1\uFE0F</div>`;
  document.body.appendChild(banner);
  setTimeout(() => banner.remove(), 3000);
  showNetIndicator(true);
}

function showNetActivatedBanner() {
  const banner = document.createElement('div');
  banner.className = 'net-banner net-activated';
  banner.innerHTML = `\uD83D\uDECD\uFE0F \uADF8\uBB3C\uB9DD \uBC1C\uB3D9!<div class="sub">\uCD94\uB099\uC744 \uB9C9\uC558\uC5B4\uC694! \uB2E4\uC2DC 5\uC5F0\uC18D\uC73C\uB85C \uD68D\uB4DD\uD558\uC138\uC694</div>`;
  document.body.appendChild(banner);
  setTimeout(() => banner.remove(), 3000);
  showNetIndicator(false);
}

function showNetIndicator(active) {
  let indicator = document.getElementById('net-indicator');
  if (!indicator) {
    indicator = document.createElement('div');
    indicator.id = 'net-indicator';
    document.getElementById('rocket-panel').appendChild(indicator);
  }
  if (active) {
    indicator.className = 'net-indicator active';
    indicator.textContent = '\uD83D\uDEE1\uFE0F \uADF8\uBB3C\uB9DD';
  } else {
    indicator.className = 'net-indicator inactive';
    indicator.textContent = '\uD83D\uDECD\uFE0F \uC0AC\uC6A9\uB428';
    setTimeout(() => indicator?.remove(), 4000);
  }
}

/* ═══════════════════════════════════
   파티클 이펙트
═══════════════════════════════════ */
function flashScreen() {
  const flash = document.createElement('div');
  flash.style.cssText = `
    position: fixed; inset: 0; background: white;
    pointer-events: none; z-index: 300;
    animation: screen-flash 0.5s ease forwards;
  `;
  document.body.appendChild(flash);
  setTimeout(() => flash.remove(), 600);
}

function flashScreenRed() {
  const flash = document.createElement('div');
  flash.style.cssText = `
    position: fixed; inset: 0; background: rgba(220, 30, 0, 0.45);
    pointer-events: none; z-index: 300;
    animation: screen-flash 0.55s ease forwards;
  `;
  document.body.appendChild(flash);
  setTimeout(() => flash.remove(), 650);
}

function spawnExhaust() {
  const rocket = document.getElementById('rp-rocket');
  const rect   = rocket.getBoundingClientRect();
  const items  = ['\uD83D\uDCA8', '\uD83D\uDD25', '\u2728', '\u26A1', '\uD83C\uDF1F'];
  const el = document.createElement('div');
  const offsetX = (Math.random() - 0.5) * 24;
  el.style.cssText = `
    position: fixed;
    left: ${rect.left + rect.width / 2 + offsetX}px;
    top: ${rect.bottom + 4}px;
    font-size: ${0.7 + Math.random() * 0.9}rem;
    pointer-events: none; z-index: 250;
    animation: exhaust-drift ${0.55 + Math.random() * 0.35}s ease-out forwards;
  `;
  el.textContent = items[Math.floor(Math.random() * items.length)];
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 1000);
}

function spawnExplosion() {
  const rocket = document.getElementById('rp-rocket');
  const rect   = rocket.getBoundingClientRect();
  const cx = rect.left + rect.width / 2;
  const cy = rect.top  + rect.height / 2;
  const items  = ['\uD83D\uDCA5', '\uD83D\uDD25', '\uD83D\uDCA2', '\u26A1', '\u2728', '\uD83C\uDF1F'];

  for (let i = 0; i < 10; i++) {
    setTimeout(() => {
      const angle = (i / 10) * Math.PI * 2 + Math.random() * 0.5;
      const dist  = 35 + Math.random() * 40;
      const el = document.createElement('div');
      el.style.cssText = `
        position: fixed;
        left: ${cx}px; top: ${cy}px;
        font-size: ${0.9 + Math.random() * 0.9}rem;
        pointer-events: none; z-index: 350;
        animation: explosion-particle ${0.5 + Math.random() * 0.3}s ease-out forwards;
      `;
      el.style.setProperty('--pdx', (Math.cos(angle) * dist) + 'px');
      el.style.setProperty('--pdy', (Math.sin(angle) * dist) + 'px');
      el.textContent = items[Math.floor(Math.random() * items.length)];
      document.body.appendChild(el);
      setTimeout(() => el.remove(), 900);
    }, i * 25);
  }
}

function spawnSmoke() {
  const rocket = document.getElementById('rp-rocket');
  const rect   = rocket.getBoundingClientRect();
  const el = document.createElement('div');
  el.style.cssText = `
    position: fixed;
    left: ${rect.left + rect.width / 2 + (Math.random() - 0.5) * 14}px;
    top: ${rect.top + rect.height / 2}px;
    font-size: ${0.9 + Math.random() * 0.8}rem;
    pointer-events: none; z-index: 250;
    animation: smoke-drift ${0.8 + Math.random() * 0.5}s ease-out forwards;
  `;
  el.textContent = ['\uD83D\uDCA8', '\uD83C\uDF2B\uFE0F', '\u2601\uFE0F'][Math.floor(Math.random() * 3)];
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 1400);
}

function spawnImpactDust() {
  const rocket = document.getElementById('rp-rocket');
  const rect   = rocket.getBoundingClientRect();
  const items  = ['\uD83D\uDCA5', '\u2B50', '\uD83D\uDCAB', '\u2728', '\uD83E\uDEA8'];
  for (let i = 0; i < 8; i++) {
    const el = document.createElement('div');
    const dx = (Math.random() - 0.5) * 80;
    el.style.cssText = `
      position: fixed;
      left: ${rect.left + rect.width / 2}px;
      top: ${rect.bottom - 10}px;
      font-size: ${0.7 + Math.random() * 0.7}rem;
      pointer-events: none; z-index: 350;
      animation: impact-scatter 0.5s ease-out forwards;
    `;
    el.style.setProperty('--sdx', dx + 'px');
    el.textContent = items[Math.floor(Math.random() * items.length)];
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 600);
  }
}

/* ═══════════════════════════════════
   로켓 패널 초기화 (별 생성)
═══════════════════════════════════ */
function initRocketPanel() {
  const container = document.getElementById('rp-stars');
  for (let i = 0; i < 18; i++) {
    const star = document.createElement('div');
    star.className = 'rp-star';
    star.style.left   = Math.random() * 90 + 5 + '%';
    star.style.top    = Math.random() * 62 + '%';
    star.style.width  = star.style.height = (Math.random() * 2 + 1) + 'px';
    star.style.animationDelay    = (Math.random() * 3) + 's';
    star.style.animationDuration = (1.5 + Math.random() * 2) + 's';
    container.appendChild(star);
  }
  updateRocketUI();
}
