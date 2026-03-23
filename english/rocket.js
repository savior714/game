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
  setTimeout(() => {
    if (!document.getElementById('marble-overlay')) openMarbleReward();
  }, 800);
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
