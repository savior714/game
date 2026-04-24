/**
 * RocketCore - 로켓 애니메이션 및 스트릭 관리 모듈
 * @module RocketCore
 */

/**
 * 로켓 상태 객체
 * @typedef {Object} RocketState
 * @property {number} streak - 연속 정답 횟수
 * @property {number} globalBoost - 전역 부스트 레벨 (0-2)
 * @property {boolean} launching - 발사 중 여부
 * @property {boolean} crashing - 추락 중 여부
 * @property {number} netStreak - 그물망 연속 횟수
 * @property {boolean} hasNet - 그물망 보유 여부
 * @property {number} LAUNCH_STREAK - 발사 필요 연속 횟수
 * @property {number} ROCKET_MAX_BOTTOM - 로켓 최대 높이 (px)
 */

(function (global) {
  /**
   * 로켓 코어를 대상 객체에 설치
   * @param {RocketState} target - 로켓 상태 변수가 선언된 객체
   * @returns {void}
   */
  function install(target) {
    /* ═══════════════════════════════════
       상태 초기화 — target에 바인딩
       과목별 engine.js의 var 선언과 호환 유지
    ═══════════════════════════════════ */
    // target에 상태가 없으면 초기화 (검증 스크립트 호환: engine.js에서 var 선언 유지)
    if (target.streak === undefined) target.streak = 0;
    if (target.globalBoost === undefined) target.globalBoost = 0;
    if (target.launching === undefined) target.launching = false;
    if (target.crashing === undefined) target.crashing = false;
    if (target.netStreak === undefined) target.netStreak = 0;
    if (target.hasNet === undefined) target.hasNet = false;
    // engine.js의 const LAUNCH_STREAK / ROCKET_MAX_BOTTOM은 window 프로퍼티가 아니므로,
    // 미설치 시 비교·연산이 전부 실패(20 >= undefined → false)한다. 과목 엔진이
    // window에 명시 할당하지 않아도 동작하도록 기본값을 둔다.
    if (target.LAUNCH_STREAK === undefined) target.LAUNCH_STREAK = 20;
    if (target.ROCKET_MAX_BOTTOM === undefined) target.ROCKET_MAX_BOTTOM = 330;

    // 상태 접근 헬퍼 (target 객체 참조)
    const state = target;

    /** LAUNCH_STREAK / ROCKET_MAX_BOTTOM이 비정상(NaN 등)이어도 UI·발사 판정이 깨지지 않게 정규화 */
    function getStreakConfig() {
      let ls = Number(state.LAUNCH_STREAK);
      let mx = Number(state.ROCKET_MAX_BOTTOM);
      if (!Number.isFinite(ls) || ls <= 0) ls = 20;
      if (!Number.isFinite(mx) || mx <= 0) mx = 330;
      state.LAUNCH_STREAK = ls;
      state.ROCKET_MAX_BOTTOM = mx;
      return { launchStreak: ls, maxBottom: mx };
    }

    /* ═══════════════════════════════════
       연속 정답 & 로켓 스트릭
    ═══════════════════════════════════ */
    function updateStreak(correct) {
      if (correct) {
        state.streak++;
        const { launchStreak } = getStreakConfig();
        if (state.streak >= launchStreak) {
          launchRocket();
          return;
        }
        updateRocketUI();
      } else {
        const prevStreak = state.streak;
        // 그물망이 있으면 연속 정답 상태를 유지한 채 추락만 방지한다.
        if (prevStreak > 0 && state.hasNet) {
          crashRocket();
          return;
        }

        state.streak = 0;
        if (prevStreak > 0) {
          crashRocket();
          return;
        }
        updateRocketUI();
      }
    }

    function updateRocketUI() {
      const { launchStreak, maxBottom } = getStreakConfig();
      const progress = Math.min(state.streak / launchStreak, 1);
      const bottomPx = 18 + Math.round(progress * maxBottom);
      const rocket = document.getElementById("rp-rocket");
      const flame = document.getElementById("rp-flame");
      const badge = document.getElementById("streak-badge");
      if (!rocket || !flame || !badge) return;

      rocket.style.bottom = bottomPx + "px";
      flame.style.bottom = bottomPx - 28 + "px";

      if (state.streak > 0) {
        flame.style.opacity = "1";
        flame.classList.add("flickering");
      } else {
        flame.style.opacity = "0";
        flame.classList.remove("flickering");
      }

      if (state.streak >= 15 && !state.launching) {
        rocket.classList.add("pre-launch");
      } else {
        rocket.classList.remove("pre-launch");
      }

      if (state.streak >= 18) {
        badge.textContent = `🚀 발사 ${launchStreak - state.streak}초전!`;
        badge.classList.add("pre-launch");
      } else {
        badge.textContent = `🔥 ${state.streak} / ${launchStreak}`;
        badge.classList.remove("pre-launch");
      }
    }

    /* ═══════════════════════════════════
       로켓 발사 시퀀스
    ═══════════════════════════════════ */
    function launchRocket() {
      if (state.launching) return;
      state.launching = true;

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
          state.globalBoost = Math.min(state.globalBoost + 1, 2);
          state.streak = 0;

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
              state.launching = false;
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
    <div class="sub">전체 난이도 ${boostNames[state.globalBoost]} 상승!</div>
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
      if (state.crashing || state.launching) return;

      const hasNet = state.hasNet;
      if (hasNet) {
        state.hasNet = false;
        state.netStreak = 0;
        netBounceRocket();
        return;
      }

      state.crashing = true;

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
            state.crashing = false;
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
      const netBottomPx = Math.round((savedBottomPx + 18) / 2);

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
          flame.style.opacity = state.streak > 0 ? "1" : "0";
          if (state.streak > 0) flame.classList.add("flickering");

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

  /**
   * RocketCore 전역 객체
   * @typedef {Object} RocketCore
   * @property {typeof install} install - 로켓 코어 설치
   */

  /** @type {RocketCore} */
  global.RocketCore = { install };
})(window);
