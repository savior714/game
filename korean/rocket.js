/* ═══════════════════════════════════
   연속 정답 & 로켓
═══════════════════════════════════ */
function updateStreak(correct) {
  if (correct) {
    streak++;
    if (streak >= LAUNCH_STREAK) { launchRocket(); return; }
    updateRocketUI();
  } else {
    const prev = streak;
    streak = 0;
    if (prev > 0) { crashRocket(); return; }
    updateRocketUI();
  }
}

function updateRocketUI() {
  const progress = Math.min(streak / LAUNCH_STREAK, 1);
  const bottomPx = Math.round(progress * ROCKET_MAX_BOTTOM);
  const rocket   = document.getElementById('rp-rocket');
  const flame    = document.getElementById('rp-flame');
  const badge    = document.getElementById('streak-badge');

  rocket.style.bottom = bottomPx + 'px';
  flame.style.bottom  = (bottomPx - 28) + 'px';

  if (streak > 0) { flame.style.opacity='1'; flame.classList.add('flickering'); }
  else            { flame.style.opacity='0'; flame.classList.remove('flickering'); }

  if (streak >= 15 && !launching) rocket.classList.add('pre-launch');
  else rocket.classList.remove('pre-launch');

  if (streak >= 18) {
    badge.textContent = `🚀 발사 ${LAUNCH_STREAK - streak}초전!`;
    badge.classList.add('pre-launch');
  } else {
    badge.textContent = `🔥 ${streak} / ${LAUNCH_STREAK}`;
    badge.classList.remove('pre-launch');
  }
}

function launchRocket() {
  if (launching) return;
  launching = true;
  const rocket = document.getElementById('rp-rocket');
  const flame  = document.getElementById('rp-flame');
  const track  = document.getElementById('rp-track');
  const panel  = document.getElementById('rocket-panel');
  const badge  = document.getElementById('streak-badge');

  rocket.classList.remove('pre-launch'); badge.classList.remove('pre-launch');
  rocket.classList.add('igniting'); flame.classList.remove('flickering');
  flame.classList.add('igniting'); flame.style.opacity='1'; panel.classList.add('shaking');

  setTimeout(() => {
    rocket.classList.remove('igniting'); rocket.classList.add('blasting');
    flame.classList.remove('igniting'); flame.classList.add('blasting');
    track.classList.add('warping'); panel.classList.remove('shaking');
    flashScreen();
    for (let i=0;i<7;i++) setTimeout(()=>spawnExhaust(), i*90);
    rocket.style.transition='bottom 1.0s cubic-bezier(0.4,0,1,1)';
    flame.style.transition ='bottom 1.0s cubic-bezier(0.4,0,1,1)';
    rocket.style.bottom='440px'; flame.style.bottom='412px';

    setTimeout(() => {
      globalBoost = Math.min(globalBoost+1, 2);
      streak = 0;
      rocket.classList.remove('blasting'); flame.classList.remove('blasting');
      track.classList.remove('warping');
      rocket.style.transition='none'; flame.style.transition='none';
      rocket.style.bottom='4px'; flame.style.bottom='-24px'; flame.style.opacity='0';
      requestAnimationFrame(() => requestAnimationFrame(() => {
        rocket.style.transition='bottom 0.55s cubic-bezier(0.25,0.46,0.45,0.94)';
        flame.style.transition ='bottom 0.55s cubic-bezier(0.25,0.46,0.45,0.94), opacity 0.3s';
        updateRocketUI(); launching=false;
      }));
      showBoostBanner();
    }, 1100);
  }, 600);
}

function showBoostBanner() {
  const names  = ['','레벨 1','레벨 2','최고 레벨'];
  const banner = document.createElement('div');
  banner.className = 'boost-banner';
  banner.innerHTML = `🚀 우주 돌파!<div class="sub">전체 난이도 ${names[globalBoost]} 상승!</div>`;
  document.body.appendChild(banner);
  setTimeout(() => banner.remove(), 3000);
  spawnConfetti(); spawnConfetti();
  document.getElementById('marble-btn').style.display = 'inline-block';

  // 중앙 연출: 로켓이 화면 중앙으로 날아가 "펑!" → 그 자리에서 룰렛 등장(정지 상태)
  setTimeout(() => {
    if (!document.getElementById('reward-overlay')) playCenterRocketRouletteEntrance();
  }, 250);
}

/* ═══════════════════════════════════
   보상 룰렛 (20연속 보상 선택)
═══════════════════════════════════ */
function playCenterRocketRouletteEntrance() {
  if (document.getElementById('reward-overlay')) return;
  if (document.getElementById('center-rocket')) return;

  const src = document.getElementById('rp-rocket');
  if (!src) { openRewardRoulette(); return; }

  const r = src.getBoundingClientRect();
  const startX = r.left + r.width / 2;
  const startY = r.top + r.height / 2;
  const endX = window.innerWidth / 2;
  const endY = window.innerHeight / 2;

  const el = document.createElement('div');
  el.id = 'center-rocket';
  el.textContent = '🚀';
  el.style.cssText =
    'position:fixed;left:0;top:0;transform:translate(-50%,-50%);' +
    'font-size:2.2rem;z-index:1100;pointer-events:none;' +
    'filter:drop-shadow(0 0 18px rgba(255,120,0,1)) drop-shadow(0 0 10px rgba(255,220,0,0.9));' +
    'transition: transform 0.95s cubic-bezier(0.2,0.9,0.2,1.05);';
  el.style.transform = `translate(${startX}px, ${startY}px) scale(1) rotate(0deg)`;
  document.body.appendChild(el);

  // 다음 프레임에 이동 시작
  requestAnimationFrame(() => requestAnimationFrame(() => {
    el.style.transform = `translate(${endX}px, ${endY}px) scale(1.55) rotate(25deg)`;
  }));

  // 중앙 도착 → 폭발 + 룰렛 오픈
  setTimeout(() => {
    try {
      flashScreen();
      spawnExplosionAt(endX, endY);
      spawnConfetti();
    } catch (_) {}
    el.remove();
    openRewardRoulette(); // 룰렛은 "멈춰있는 상태"로 뜨고, 회전은 버튼 클릭으로만 시작
  }, 1050);
}

function spawnExplosionAt(cx, cy) {
  const items = ['💥','🔥','💢','⚡','✨','🌟'];
  for (let i = 0; i < 12; i++) {
    setTimeout(() => {
      const angle = i / 12 * Math.PI * 2 + Math.random() * 0.5;
      const dist  = 38 + Math.random() * 55;
      const p = document.createElement('div');
      p.style.cssText =
        'position:fixed;left:' + cx + 'px;top:' + cy + 'px;' +
        'font-size:' + (1.0 + Math.random() * 1.0) + 'rem;' +
        'pointer-events:none;z-index:1150;' +
        'animation:explosion-particle ' + (0.55 + Math.random() * 0.35) + 's ease-out forwards;';
      p.style.setProperty('--pdx', (Math.cos(angle) * dist) + 'px');
      p.style.setProperty('--pdy', (Math.sin(angle) * dist) + 'px');
      p.textContent = items[Math.floor(Math.random() * items.length)];
      document.body.appendChild(p);
      setTimeout(() => p.remove(), 1000);
    }, i * 18);
  }
}

function openRewardRoulette() {
  if (document.getElementById('reward-overlay')) return;

  const rewards = [
    { id: 'marble',  label: '🎮 마블 게임 1판',     run: () => openMarbleReward() },
    { id: 'youtube', label: '📺 유튜브 15분 보기',  run: () => openYoutubeReward() },
    { id: 'snack',   label: '🍪 간식 하나 고르기',  run: () => openSnackReward() },
  ];

  const overlay = document.createElement('div');
  overlay.id = 'reward-overlay';

  const modal = document.createElement('div');
  modal.className = 'reward-modal';
  modal.innerHTML = `
    <div class="reward-head">
      <div class="reward-title">🎁 보상 룰렛</div>
      <button class="reward-close" type="button">닫기</button>
    </div>
    <div class="reward-body">
      <div class="reward-sub">20문제 연속 정답! 룰렛을 돌려서 보상을 받아요.</div>
      <div class="roulette-list">
        ${rewards.map(r => `<div class="roulette-item" data-reward="${r.id}">${r.label}<span>🎯</span></div>`).join('')}
      </div>
      <div class="reward-actions">
        <button class="reward-primary" id="reward-spin-btn" type="button">룰렛 돌리기</button>
        <button class="reward-secondary" id="reward-cancel-btn" type="button">나중에</button>
      </div>
    </div>
  `;

  overlay.appendChild(modal);

  function cleanup() {
    overlay.remove();
  }

  function consumeRewardButton() {
    const btn = document.getElementById('marble-btn');
    if (btn) btn.style.display = 'none';
  }

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) cleanup();
  });

  modal.querySelector('.reward-close').onclick = () => cleanup();
  modal.querySelector('#reward-cancel-btn').onclick = () => { cleanup(); consumeRewardButton(); };

  const items = Array.from(modal.querySelectorAll('.roulette-item'));
  const spinBtn = modal.querySelector('#reward-spin-btn');

  spinBtn.onclick = () => {
    spinBtn.disabled = true;
    items.forEach(it => it.classList.remove('active', 'winner'));

    const winner = rewards[Math.floor(Math.random() * rewards.length)];
    const winnerEl = modal.querySelector(`.roulette-item[data-reward="${winner.id}"]`);

    let i = 0;
    const start = performance.now();
    const duration = 1600;
    const tickMs = 85;

    const timer = setInterval(() => {
      items.forEach(it => it.classList.remove('active'));
      items[i % items.length].classList.add('active');
      i++;
      if (performance.now() - start >= duration) {
        clearInterval(timer);
        items.forEach(it => it.classList.remove('active'));
        if (winnerEl) winnerEl.classList.add('winner');
        setTimeout(() => {
          cleanup();
          consumeRewardButton();
          winner.run();
        }, 450);
      }
    }, tickMs);
  };

  document.body.appendChild(overlay);
}

function openYoutubeReward() {
  if (document.getElementById('reward-overlay')) return;

  const overlay = document.createElement('div');
  overlay.id = 'reward-overlay';

  const modal = document.createElement('div');
  modal.className = 'reward-modal';
  modal.innerHTML = `
    <div class="reward-head">
      <div class="reward-title">📺 유튜브 15분 보기</div>
      <button class="reward-close" type="button">닫기</button>
    </div>
    <div class="reward-body">
      <div class="reward-sub">15분 동안 쉬고 다시 공부하자!</div>
      <div class="reward-timer" id="reward-yt-timer">15:00</div>
      <div class="reward-note">원하면 유튜브를 켜고(별도), 타이머가 끝나면 돌아오면 돼.</div>
      <div class="reward-actions">
        <button class="reward-primary" id="reward-yt-start" type="button">타이머 시작</button>
        <button class="reward-secondary" id="reward-yt-close" type="button">닫기</button>
      </div>
    </div>
  `;

  overlay.appendChild(modal);

  let interval = null;
  function cleanup() {
    if (interval) clearInterval(interval);
    overlay.remove();
  }

  function render(sec) {
    const mm = String(Math.floor(sec / 60)).padStart(2, '0');
    const ss = String(sec % 60).padStart(2, '0');
    modal.querySelector('#reward-yt-timer').textContent = `${mm}:${ss}`;
  }

  modal.querySelector('.reward-close').onclick = () => cleanup();
  modal.querySelector('#reward-yt-close').onclick = () => cleanup();
  overlay.addEventListener('click', (e) => { if (e.target === overlay) cleanup(); });

  const startBtn = modal.querySelector('#reward-yt-start');
  startBtn.onclick = () => {
    startBtn.disabled = true;
    let remaining = 15 * 60;
    render(remaining);
    interval = setInterval(() => {
      remaining--;
      if (remaining <= 0) {
        render(0);
        clearInterval(interval);
        interval = null;
        spawnConfetti();
        startBtn.disabled = false;
        startBtn.textContent = '다시 15분';
      } else {
        render(remaining);
      }
    }, 1000);
  };

  document.body.appendChild(overlay);
}

function openSnackReward() {
  if (document.getElementById('reward-overlay')) return;

  const overlay = document.createElement('div');
  overlay.id = 'reward-overlay';

  const modal = document.createElement('div');
  modal.className = 'reward-modal';
  modal.innerHTML = `
    <div class="reward-head">
      <div class="reward-title">🍪 간식 하나 고르기</div>
      <button class="reward-close" type="button">닫기</button>
    </div>
    <div class="reward-body">
      <div class="reward-sub">오늘의 보상!</div>
      <div class="reward-note">
        아래 중에서 하나 골라서 먹자.<br/>
        - 과일 한 조각<br/>
        - 요거트 / 우유<br/>
        - 작은 과자 한 봉지
      </div>
      <div class="reward-actions">
        <button class="reward-primary" id="reward-snack-ok" type="button">골랐어!</button>
        <button class="reward-secondary" id="reward-snack-close" type="button">닫기</button>
      </div>
    </div>
  `;

  overlay.appendChild(modal);

  function cleanup() { overlay.remove(); }
  modal.querySelector('.reward-close').onclick = () => cleanup();
  modal.querySelector('#reward-snack-close').onclick = () => cleanup();
  modal.querySelector('#reward-snack-ok').onclick = () => { spawnConfetti(); cleanup(); };
  overlay.addEventListener('click', (e) => { if (e.target === overlay) cleanup(); });

  document.body.appendChild(overlay);
}

/* ═══════════════════════════════════
   마블 머지 보상 게임 (iframe 오버레이)
═══════════════════════════════════ */
function openMarbleReward() {
  const overlay = document.createElement('div');
  overlay.id = 'marble-overlay';
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.88);' +
    'z-index:800;display:flex;align-items:center;justify-content:center;';
  const iframe = document.createElement('iframe');
  iframe.src = '../marble/';
  iframe.style.cssText = 'border:none;border-radius:20px;' +
    'width:360px;height:560px;max-width:96vw;max-height:95vh;';
  overlay.appendChild(iframe);
  function _closeMarble() {
    document.getElementById('marble-overlay')?.remove();
    document.getElementById('marble-btn').style.display = 'none';
  }
  overlay.addEventListener('click', (e) => { if (e.target === overlay) _closeMarble(); });
  document.body.appendChild(overlay);
  window.addEventListener('message', (e) => {
    if (e.data === 'closeMarble') _closeMarble();
  }, { once: true });
}

/* ═══════════════════════════════════
   추락 애니메이션
═══════════════════════════════════ */
function crashRocket() {
  if (crashing || launching) return;
  crashing = true;
  const rocket = document.getElementById('rp-rocket');
  const flame  = document.getElementById('rp-flame');
  const badge  = document.getElementById('streak-badge');
  flame.style.opacity='0'; flame.classList.remove('flickering','blasting','igniting');
  rocket.classList.remove('pre-launch','blasting','igniting'); badge.classList.remove('pre-launch');
  rocket.classList.add('exploding'); flashScreenRed(); spawnExplosion();
  setTimeout(() => {
    rocket.classList.remove('exploding'); rocket.classList.add('crashing');
    rocket.style.transition='bottom 1.05s cubic-bezier(0.55,0,1,0.5)';
    rocket.style.bottom='4px';
    for (let i=0;i<5;i++) setTimeout(()=>spawnSmoke(), i*160);
    setTimeout(() => {
      rocket.classList.remove('crashing'); rocket.classList.add('crash-impact');
      spawnImpactDust();
      setTimeout(() => {
        rocket.classList.remove('crash-impact');
        rocket.style.transition='bottom 0.55s cubic-bezier(0.25,0.46,0.45,0.94)';
        crashing=false; updateRocketUI();
      }, 450);
    }, 1080);
  }, 500);
}

function flashScreenRed() {
  const el = document.createElement('div');
  el.style.cssText='position:fixed;inset:0;background:rgba(220,30,0,0.45);pointer-events:none;z-index:300;animation:screen-flash 0.55s ease forwards;';
  document.body.appendChild(el); setTimeout(()=>el.remove(), 650);
}

function spawnExplosion() {
  const rect  = document.getElementById('rp-rocket').getBoundingClientRect();
  const cx=rect.left+rect.width/2, cy=rect.top+rect.height/2;
  const items=['💥','🔥','💢','⚡','✨','🌟'];
  for (let i=0;i<10;i++) setTimeout(()=>{
    const angle=i/10*Math.PI*2+Math.random()*0.5, dist=35+Math.random()*40;
    const el=document.createElement('div');
    el.style.cssText=`position:fixed;left:${cx}px;top:${cy}px;font-size:${0.9+Math.random()*0.9}rem;pointer-events:none;z-index:350;animation:explosion-particle ${0.5+Math.random()*0.3}s ease-out forwards;`;
    el.style.setProperty('--pdx',(Math.cos(angle)*dist)+'px');
    el.style.setProperty('--pdy',(Math.sin(angle)*dist)+'px');
    el.textContent=items[Math.floor(Math.random()*items.length)];
    document.body.appendChild(el); setTimeout(()=>el.remove(),900);
  }, i*25);
}

function spawnSmoke() {
  const rect=document.getElementById('rp-rocket').getBoundingClientRect();
  const el=document.createElement('div');
  el.style.cssText=`position:fixed;left:${rect.left+rect.width/2+(Math.random()-0.5)*14}px;top:${rect.top+rect.height/2}px;font-size:${0.9+Math.random()*0.8}rem;pointer-events:none;z-index:250;animation:smoke-drift ${0.8+Math.random()*0.5}s ease-out forwards;`;
  el.textContent=['💨','🌫️','☁️'][Math.floor(Math.random()*3)];
  document.body.appendChild(el); setTimeout(()=>el.remove(),1400);
}

function spawnImpactDust() {
  const rect=document.getElementById('rp-rocket').getBoundingClientRect();
  const items=['💥','⭐','💫','✨','🪨'];
  for (let i=0;i<8;i++) {
    const el=document.createElement('div'), dx=(Math.random()-0.5)*80;
    el.style.cssText=`position:fixed;left:${rect.left+rect.width/2}px;top:${rect.bottom-10}px;font-size:${0.7+Math.random()*0.7}rem;pointer-events:none;z-index:350;animation:impact-scatter 0.5s ease-out forwards;`;
    el.style.setProperty('--sdx',dx+'px');
    el.textContent=items[Math.floor(Math.random()*items.length)];
    document.body.appendChild(el); setTimeout(()=>el.remove(),600);
  }
}

function flashScreen() {
  const el=document.createElement('div');
  el.style.cssText='position:fixed;inset:0;background:white;pointer-events:none;z-index:300;animation:screen-flash 0.5s ease forwards;';
  document.body.appendChild(el); setTimeout(()=>el.remove(),600);
}

function spawnExhaust() {
  const rect=document.getElementById('rp-rocket').getBoundingClientRect();
  const items=['💨','🔥','✨','⚡','🌟'];
  const el=document.createElement('div'), ox=(Math.random()-0.5)*24;
  el.style.cssText=`position:fixed;left:${rect.left+rect.width/2+ox}px;top:${rect.bottom+4}px;font-size:${0.7+Math.random()*0.9}rem;pointer-events:none;z-index:250;animation:exhaust-drift ${0.55+Math.random()*0.35}s ease-out forwards;`;
  el.textContent=items[Math.floor(Math.random()*items.length)];
  document.body.appendChild(el); setTimeout(()=>el.remove(),1000);
}

/* ═══════════════════════════════════
   로켓 패널 초기화
═══════════════════════════════════ */
function initRocketPanel() {
  const container = document.getElementById('rp-stars');
  for (let i=0;i<18;i++) {
    const star = document.createElement('div');
    star.className = 'rp-star';
    star.style.left   = Math.random()*90+5+'%';
    star.style.top    = Math.random()*62+'%';
    star.style.width  = star.style.height = (Math.random()*2+1)+'px';
    star.style.animationDelay    = (Math.random()*3)+'s';
    star.style.animationDuration = (1.5+Math.random()*2)+'s';
    container.appendChild(star);
  }
  updateRocketUI();
}
