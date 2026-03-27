(function (global) {
  function install(target) {
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
        // 그물망이 있으면 연속 정답 상태를 유지한 채 추락만 방지한다.
        if (prevStreak > 0 && hasNet) {
          crashRocket();
          return;
        }

        streak = 0;
        if (prevStreak > 0) {
          crashRocket();
          return;
        }
        updateRocketUI();
      }
    }

    function updateRocketUI() {
      const progress = Math.min(streak / LAUNCH_STREAK, 1);
      const bottomPx = 18 + Math.round(progress * ROCKET_MAX_BOTTOM);
      const rocket = document.getElementById("rp-rocket");
      const flame = document.getElementById("rp-flame");
      const badge = document.getElementById("streak-badge");

      rocket.style.bottom = bottomPx + "px";
      flame.style.bottom = bottomPx - 28 + "px";

      if (streak > 0) {
        flame.style.opacity = "1";
        flame.classList.add("flickering");
      } else {
        flame.style.opacity = "0";
        flame.classList.remove("flickering");
      }

      if (streak >= 15 && !launching) {
        rocket.classList.add("pre-launch");
      } else {
        rocket.classList.remove("pre-launch");
      }

      if (streak >= 18) {
        badge.textContent = `🚀 발사 ${LAUNCH_STREAK - streak}초전!`;
        badge.classList.add("pre-launch");
      } else {
        badge.textContent = `🔥 ${streak} / ${LAUNCH_STREAK}`;
        badge.classList.remove("pre-launch");
      }
    }

    /* ═══════════════════════════════════
       로켓 발사 시퀀스
    ═══════════════════════════════════ */
    function launchRocket() {
      if (launching) return;
      launching = true;

      const rocket = document.getElementById("rp-rocket");
      const flame = document.getElementById("rp-flame");
      const track = document.getElementById("rp-track");
      const panel = document.getElementById("rocket-panel");

      rocket.classList.remove("pre-launch", "flickering");
      badgeReset();
      rocket.classList.add("igniting");
      flame.classList.remove("flickering");
      flame.classList.add("igniting");
      flame.style.opacity = "1";
      panel.classList.add("shaking");

      setTimeout(() => {
        rocket.classList.remove("igniting");
        rocket.classList.add("blasting");
        flame.classList.remove("igniting");
        flame.classList.add("blasting");
        track.classList.add("warping");
        panel.classList.remove("shaking");

        if (global.RocketEffects) global.RocketEffects.flashScreen();

        for (let i = 0; i < 7; i++) {
          setTimeout(() => global.RocketEffects?.spawnExhaust(), i * 90);
        }

        rocket.style.transition = "bottom 1.0s cubic-bezier(0.4, 0, 1, 1)";
        flame.style.transition = "bottom 1.0s cubic-bezier(0.4, 0, 1, 1)";
        rocket.style.bottom = "440px";
        flame.style.bottom = "412px";

        setTimeout(() => {
          globalBoost = Math.min(globalBoost + 1, 2);
          streak = 0;

          rocket.classList.remove("blasting");
          flame.classList.remove("blasting");
          track.classList.remove("warping");

          rocket.style.transition = "none";
          flame.style.transition = "none";
          rocket.style.bottom = "18px";
          flame.style.bottom = "-24px";
          flame.style.opacity = "0";

          requestAnimationFrame(() =>
            requestAnimationFrame(() => {
              rocket.style.transition = "bottom 0.55s cubic-bezier(0.25, 0.46, 0.45, 0.94)";
              flame.style.transition = "bottom 0.55s cubic-bezier(0.25, 0.46, 0.45, 0.94), opacity 0.3s";
              updateRocketUI();
              launching = false;
            }),
          );

          showBoostBanner();
        }, 1100);
      }, 600);
    }

    function badgeReset() {
      document.getElementById("streak-badge").classList.remove("pre-launch");
    }

    function showBoostBanner() {
      const boostNames = ["", "레벨 1", "레벨 2", "최고 레벨"];
      const banner = document.createElement("div");
      banner.className = "boost-banner";
      banner.innerHTML = `
    🚀 우주 돌파!
    <div class="sub">전체 난이도 ${boostNames[globalBoost]} 상승!</div>
  `;
      document.body.appendChild(banner);
      setTimeout(() => banner.remove(), 3000);

      // 보석 획득 연출 호출 (RewardSystem.js 필요)
      if (typeof RewardSystem !== "undefined" && typeof RewardSystem.playEntranceAndAddGem === "function") {
        RewardSystem.playEntranceAndAddGem("rp-rocket");
      }
    }

    /* ═══════════════════════════════════
       추락 시퀀스
    ═══════════════════════════════════ */
    function crashRocket() {
      if (crashing || launching) return;

      if (hasNet) {
        hasNet = false;
        netStreak = 0;
        netBounceRocket();
        return;
      }

      crashing = true;

      const rocket = document.getElementById("rp-rocket");
      const flame = document.getElementById("rp-flame");
      const badge = document.getElementById("streak-badge");

      flame.style.opacity = "0";
      flame.classList.remove("flickering", "blasting", "igniting");
      rocket.classList.remove("pre-launch", "blasting", "igniting");
      badge.classList.remove("pre-launch");

      rocket.classList.add("exploding");
      global.RocketEffects?.flashScreenRed();
      global.RocketEffects?.spawnExplosion();

      setTimeout(() => {
        rocket.classList.remove("exploding");
        rocket.classList.add("crashing");
        rocket.style.transition = "bottom 1.05s cubic-bezier(0.55, 0, 1, 0.5)";
        rocket.style.bottom = "18px";

        for (let i = 0; i < 5; i++) {
          setTimeout(() => global.RocketEffects?.spawnSmoke(), i * 160);
        }

        setTimeout(() => {
          rocket.classList.remove("crashing");
          rocket.classList.add("crash-impact");
          global.RocketEffects?.spawnImpactDust();

          setTimeout(() => {
            rocket.classList.remove("crash-impact");
            rocket.style.transition = "bottom 0.55s cubic-bezier(0.25, 0.46, 0.45, 0.94)";
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
      const rocket = document.getElementById("rp-rocket");
      const flame = document.getElementById("rp-flame");
      const badge = document.getElementById("streak-badge");
      const track = document.getElementById("rp-track");

      const savedBottom = rocket.style.bottom || "18px";
      const savedBottomPx = parseInt(savedBottom, 10) || 18;
      const trackHeightPx = track ? track.clientHeight : 380;
      const minCatchBottom = 30;
      const maxCatchBottom = Math.max(trackHeightPx - 72, minCatchBottom);
      const catchDropPx = Math.max(Math.round(savedBottomPx * 0.45), 70);
      const netBottomPx = Math.min(Math.max(savedBottomPx - catchDropPx, minCatchBottom), maxCatchBottom);

      flame.style.opacity = "0";
      flame.classList.remove("flickering", "blasting", "igniting");
      rocket.classList.remove("pre-launch", "blasting", "igniting");
      badge.classList.remove("pre-launch");

      global.RocketEffects?.flashScreenBlue();

      rocket.classList.add("net-falling");
      rocket.style.transition = "bottom 0.9s cubic-bezier(0.55, 0, 1, 0.45)";
      rocket.style.bottom = `${netBottomPx + 2}px`;

      for (let i = 0; i < 4; i++) {
        setTimeout(() => global.RocketEffects?.spawnSmoke(), i * 120);
      }

      setTimeout(() => {
        rocket.classList.remove("net-falling");
        spawnNetEffect(track, netBottomPx);
        global.RocketEffects?.flashScreenNet();

        rocket.classList.add("net-bounce");
        rocket.style.transition = "none";

        setTimeout(() => {
          rocket.classList.remove("net-bounce");
          const targetBottom = savedBottom;
          rocket.style.transition = "bottom 0.68s cubic-bezier(0.22, 0.72, 0.23, 1)";
          flame.style.transition = "bottom 0.68s cubic-bezier(0.22, 0.72, 0.23, 1), opacity 0.35s";
          rocket.style.bottom = targetBottom;
          const rocketPx = parseInt(targetBottom, 10) || 18;
          flame.style.bottom = rocketPx - 28 + "px";
          flame.style.opacity = streak > 0 ? "1" : "0";
          if (streak > 0) flame.classList.add("flickering");

          setTimeout(() => {
            updateRocketUI();
            showNetActivatedBanner();
          }, 900);
        }, 350);
      }, 950);
    }

    function spawnNetEffect(track, netBottomPx) {
      const now = Date.now();
      track?.querySelectorAll(".net-element").forEach((el) => el.remove());
      const net = document.createElement("div");
      net.className = "net-element";
      net.style.bottom = `${netBottomPx}px`;
      net.innerHTML = `<svg width="64" height="30" viewBox="0 0 64 30" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <pattern id="np${now}" x="0" y="0" width="8" height="8" patternUnits="userSpaceOnUse">
        <path d="M0 0 L8 0 L8 8 L0 8 Z" fill="none" stroke="rgba(0,220,130,0.9)" stroke-width="1.3"/>
        <line x1="0" y1="0" x2="8" y2="8" stroke="rgba(0,220,130,0.55)" stroke-width="0.8"/>
        <line x1="8" y1="0" x2="0" y2="8" stroke="rgba(0,220,130,0.55)" stroke-width="0.8"/>
      </pattern>
    </defs>
    <rect width="64" height="30" rx="3" fill="url(#np${now})"/>
    <rect width="64" height="30" rx="3" fill="none" stroke="rgba(0,255,150,0.95)" stroke-width="2.5"/>
  </svg>`;
      track.appendChild(net);
      setTimeout(() => net.remove(), 1800);
    }

    function showNetBanner() {
      const banner = document.createElement("div");
      banner.className = "net-banner net-earned";
      banner.innerHTML = "🛸 그물망 획득!<div class=\"sub\">5연속 정답! 추락 1회 보호받으세요 🛡️</div>";
      document.body.appendChild(banner);
      setTimeout(() => banner.remove(), 3000);
    }

    function showNetActivatedBanner() {
      const banner = document.createElement("div");
      banner.className = "net-banner net-activated";
      banner.innerHTML = "🛍️ 그물망 발동!<div class=\"sub\">추락을 막았어요! 다시 5연속으로 정답을 맞혀 획득하세요</div>";
      document.body.appendChild(banner);
      setTimeout(() => banner.remove(), 3000);
    }

    function initRocketPanel() {
      if (global.RocketEffects) global.RocketEffects.initStars();
      updateRocketUI();
    }

    Object.assign(target, {
      updateStreak,
      updateRocketUI,
      launchRocket,
      badgeReset,
      showBoostBanner,
      crashRocket,
      netBounceRocket,
      spawnNetEffect,
      showNetBanner,
      showNetActivatedBanner,
      initRocketPanel,
    });
  }

  global.RocketCore = { install };
})(window);
