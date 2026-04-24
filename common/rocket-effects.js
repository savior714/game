(function (global) {
  /* ═══════════════════════════════════
     로켓 시각 효과 모듈 (Rocket Effects)
  ═══════════════════════════════════ */
  const RocketEffects = {
    flashScreen() {
      const flash = document.createElement("div");
      flash.style.cssText = `position: fixed; inset: 0; background: white; pointer-events: none; z-index: 300; animation: screen-flash 0.5s ease forwards;`;
      document.body.appendChild(flash);
      setTimeout(() => flash.remove(), 600);
    },

    flashScreenRed() {
      const flash = document.createElement("div");
      flash.style.cssText = `position: fixed; inset: 0; background: rgba(220, 30, 0, 0.45); pointer-events: none; z-index: 300; animation: screen-flash 0.55s ease forwards;`;
      document.body.appendChild(flash);
      setTimeout(() => flash.remove(), 650);
    },

    flashScreenBlue() {
      const flash = document.createElement("div");
      flash.style.cssText = `position: fixed; inset: 0; background: rgba(30, 120, 255, 0.32); pointer-events: none; z-index: 300; animation: screen-flash 0.5s ease forwards;`;
      document.body.appendChild(flash);
      setTimeout(() => flash.remove(), 600);
    },

    flashScreenNet() {
      const flash = document.createElement("div");
      flash.style.cssText = `position: fixed; inset: 0; background: rgba(0, 210, 120, 0.28); pointer-events: none; z-index: 300; animation: screen-flash 0.6s ease forwards;`;
      document.body.appendChild(flash);
      setTimeout(() => flash.remove(), 700);
    },

    spawnExhaust() {
      const rocket = document.getElementById("rp-rocket");
      if (!rocket) return;
      const rect = rocket.getBoundingClientRect();
      const items = ["💨", "🔥", "✨", "⚡", "🌟"];
      const el = document.createElement("div");
      const offsetX = (Math.random() - 0.5) * 24;
      el.style.cssText = `position: fixed; left: ${rect.left + rect.width / 2 + offsetX}px; top: ${rect.bottom + 4}px; font-size: ${0.7 + Math.random() * 0.9}rem; pointer-events: none; z-index: 250; animation: exhaust-drift ${0.55 + Math.random() * 0.35}s ease-out forwards;`;
      el.textContent = items[Math.floor(Math.random() * items.length)];
      document.body.appendChild(el);
      setTimeout(() => el.remove(), 1000);
    },

    spawnExplosion() {
      const rocket = document.getElementById("rp-rocket");
      if (!rocket) return;
      const rect = rocket.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const items = ["💥", "🔥", "💢", "⚡", "✨", "🌟"];

      for (let i = 0; i < 10; i++) {
        setTimeout(() => {
          const angle = (i / 10) * Math.PI * 2 + Math.random() * 0.5;
          const dist = 35 + Math.random() * 40;
          const el = document.createElement("div");
          el.style.cssText = `position: fixed; left: ${cx}px; top: ${cy}px; font-size: ${0.9 + Math.random() * 0.9}rem; pointer-events: none; z-index: 350; animation: explosion-particle ${0.5 + Math.random() * 0.3}s ease-out forwards;`;
          el.style.setProperty("--pdx", Math.cos(angle) * dist + "px");
          el.style.setProperty("--pdy", Math.sin(angle) * dist + "px");
          el.textContent = items[Math.floor(Math.random() * items.length)];
          document.body.appendChild(el);
          setTimeout(() => el.remove(), 900);
        }, i * 25);
      }
    },

    spawnSmoke() {
      const rocket = document.getElementById("rp-rocket");
      if (!rocket) return;
      const rect = rocket.getBoundingClientRect();
      const el = document.createElement("div");
      el.style.cssText = `position: fixed; left: ${rect.left + rect.width / 2 + (Math.random() - 0.5) * 14}px; top: ${rect.top + rect.height / 2}px; font-size: ${0.9 + Math.random() * 0.8}rem; pointer-events: none; z-index: 250; animation: smoke-drift ${0.8 + Math.random() * 0.5}s ease-out forwards;`;
      el.textContent = ["💨", "🌫️", "☁️"][Math.floor(Math.random() * 3)];
      document.body.appendChild(el);
      setTimeout(() => el.remove(), 1400);
    },

    spawnImpactDust() {
      const rocket = document.getElementById("rp-rocket");
      if (!rocket) return;
      const rect = rocket.getBoundingClientRect();
      const items = ["💥", "⭐", "💫", "✨", "🪨"];
      for (let i = 0; i < 8; i++) {
        const el = document.createElement("div");
        const dx = (Math.random() - 0.5) * 80;
        el.style.cssText = `position: fixed; left: ${rect.left + rect.width / 2}px; top: ${rect.bottom - 10}px; font-size: ${0.7 + Math.random() * 0.7}rem; pointer-events: none; z-index: 350; animation: impact-scatter 0.5s ease-out forwards;`;
        el.style.setProperty("--sdx", dx + "px");
        el.textContent = items[Math.floor(Math.random() * items.length)];
        document.body.appendChild(el);
        setTimeout(() => el.remove(), 600);
      }
    },

    initStars() {
      const container = document.getElementById("rp-stars");
      if (!container) return;

      container.innerHTML = "";
      const starLayers = [
        { count: 9, minSize: 1.8, maxSize: 3.1, minOpacity: 0.6, maxOpacity: 0.95 },
        { count: 11, minSize: 1.2, maxSize: 2.2, minOpacity: 0.45, maxOpacity: 0.8 },
        { count: 12, minSize: 0.8, maxSize: 1.6, minOpacity: 0.3, maxOpacity: 0.6 },
      ];

      for (const layer of starLayers) {
        for (let i = 0; i < layer.count; i++) {
          const star = document.createElement("div");
          star.className = "rp-star";
          star.style.left = Math.random() * 88 + 6 + "%";
          star.style.top = Math.random() * 66 + "%";
          const size = layer.minSize + Math.random() * (layer.maxSize - layer.minSize);
          star.style.width = size + "px";
          star.style.height = size + "px";
          star.style.opacity = (layer.minOpacity + Math.random() * (layer.maxOpacity - layer.minOpacity)).toFixed(2);
          star.style.animationDelay = Math.random() * 3 + "s";
          star.style.animationDuration = 1.6 + Math.random() * 2.6 + "s";
          container.appendChild(star);
        }
      }
    }
  };

  global.RocketEffects = RocketEffects;
})(window);
