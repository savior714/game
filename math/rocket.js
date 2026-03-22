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
  const boostNames = ['', '\ub808\ubca8 1', '\ub808\ubca8 2', '\ucd5c\uace0 \ub808\ubca8'];
  const banner = document.createElement('div');
  banner.className = 'boost-banner';
  banner.innerHTML = `
    \uD83D\uDE80 \uc6b0\uc8fc \ub3cc\ud30c!
    <div class="sub">\uc804\uccb4 \ub09c\uc774\ub3c4 ${boostNames[globalBoost]} \uc0c1\uc2b9!</div>
  `;
  document.body.appendChild(banner);
  setTimeout(() => banner.remove(), 3000);
  spawnConfetti();
  spawnConfetti();
  document.getElementById('marble-btn').style.display = 'inline-block';
}

/* ═══════════════════════════════════
   추락 시퀀스
═══════════════════════════════════ */
function crashRocket() {
  if (crashing || launching) return;
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
