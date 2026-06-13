export function attachControls(options) {
  const {
    state,
    planets,
    initialAngles,
    render,
  } = options;

  const controlsPanel = document.querySelector(".controls-panel");
  if (!controlsPanel) return;

  const playBtn = controlsPanel.querySelector('[data-action="play"]');
  const pauseBtn = controlsPanel.querySelector('[data-action="pause"]');
  const resetBtn = controlsPanel.querySelector('[data-action="reset"]');
  const speed = document.getElementById("time-scale");
  const quality = document.getElementById("render-quality");
  const labelToggle = controlsPanel.querySelector('input[type="checkbox"]');

  function updateStatusText() {
    const status = document.getElementById("simulation-status");
    if (!status) return;
    const mode = state.isPlaying ? "재생 중" : "일시정지";
    const renderModeText = state.renderMode === "3d" ? "3D" : "2D";
    status.textContent = `${mode} · ${Math.round(state.timeScale * 200)}% · ${renderModeText}`;
  }

  function renderPlayPauseButtons() {
    if (playBtn) {
      playBtn.classList.toggle("is-active", state.isPlaying);
    }
    if (pauseBtn) {
      pauseBtn.classList.toggle("is-active", !state.isPlaying);
    }
  }

  function setPlaying(nextState) {
    state.isPlaying = nextState;
    renderPlayPauseButtons();
    updateStatusText();
  }

  function setRenderMode(nextMode) {
    if (nextMode === "high") {
      state.renderMode = "3d";
    } else if (nextMode === "low") {
      state.renderMode = "2d";
    } else {
      state.renderMode = nextMode === "3d" ? "3d" : "2d";
    }
    updateStatusText();
    render();
  }

  function applyResetState() {
    state.elapsedTime = 0;
    state.lastTs = 0;
    state.timeScale = 0.5;
    state.showLabels = true;
    state.renderMode = "2d";
    planets.forEach((planet, index) => {
      planet.angle = initialAngles[index];
    });
    setPlaying(true);
  }

  function syncControlDefaults() {
    if (speed) speed.value = String(state.timeScale);
    if (quality) quality.value = state.renderMode;
    if (labelToggle) labelToggle.checked = state.showLabels;
    renderPlayPauseButtons();
    updateStatusText();
  }

  if (playBtn) {
    playBtn.addEventListener("click", () => setPlaying(true));
  }
  if (pauseBtn) {
    pauseBtn.addEventListener("click", () => setPlaying(false));
  }
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      applyResetState();
      syncControlDefaults();
      render();
    });
  }
  if (speed) {
    speed.addEventListener("change", (event) => {
      const raw = event.target.value;
      const parsed = Number(raw);
      if (!Number.isNaN(parsed)) {
        state.timeScale = parsed;
        updateStatusText();
      }
    });
  }
  if (quality) {
    quality.addEventListener("change", (event) => {
      setRenderMode(event.target.value);
    });
  }
  if (labelToggle) {
    labelToggle.addEventListener("change", (event) => {
      state.showLabels = Boolean(event.target.checked);
      updateStatusText();
      render();
    });
  }

  syncControlDefaults();

  return {
    setPlaying,
    setRenderMode,
    applyResetState,
    updateStatusText,
    syncControlDefaults,
  };
}
