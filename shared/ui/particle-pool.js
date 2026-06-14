(function (global) {
  /* ═══════════════════════════════════
     파티클 오브젝트 풀 (Particle Object Pool)
     DOM 노드 생성·제거 부하를 줄이기 위한 재사용 풀
  ═══════════════════════════════════ */
  const ParticlePool = {
    _pool: null,
    _size: 0,

    createPool(size) {
      this._size = size;
      this._pool = [];
      for (let i = 0; i < size; i++) {
        const el = document.createElement("div");
        el.style.display = "none";
        el.style.position = "fixed";
        el.style.pointerEvents = "none";
        el.style.visibility = "hidden";
        document.body.appendChild(el);
        this._pool.push(el);
      }
    },

    acquire(className) {
      if (!this._pool || this._pool.length === 0) return null;
      const el = this._pool.pop();
      el.className = className || "";
      el.style.display = "block";
      el.style.visibility = "visible";
      // 이전 애니메이션 스타일 초기화 — 새 애니메이션이 정상 동작
      el.style.left = "";
      el.style.top = "";
      el.style.animationDuration = "";
      el.style.setProperty("--pdx", "");
      el.style.setProperty("--pdy", "");
      el.style.setProperty("--sdx", "");
      if (el._confettiTimeout) {
        clearTimeout(el._confettiTimeout);
        el._confettiTimeout = null;
      }
      return el;
    },

    release(el) {
      if (!el || !this._pool) return;
      // 실행 중이던 setTimeout 취소 — 재사용 시 충돌 방지
      if (el._confettiTimeout) {
        clearTimeout(el._confettiTimeout);
        el._confettiTimeout = null;
      }
      el.style.display = "none";
      el.style.visibility = "hidden";
      el.style.left = "";
      el.style.top = "";
      el.style.animationDuration = "";
      el.style.setProperty("--pdx", "");
      el.style.setProperty("--pdy", "");
      el.style.setProperty("--sdx", "");
      this._pool.push(el);
    },

    clear() {
      if (!this._pool) return;
      for (const el of this._pool) {
        if (el.parentNode) el.parentNode.removeChild(el);
      }
      this._pool = [];
    }
  };

  global.ParticlePool = ParticlePool;
})(window);
