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
    const qualityText = state.quality === "high" ? "고품질" : "저품질";
    status.textContent = `${mode} · ${state.timeScale}x · ${qualityText}`;
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

  function setQualityLevel(nextQuality) {
    state.quality = nextQuality === "low" ? "low" : "high";
    updateStatusText();
    render();
  }

  function applyResetState() {
    state.elapsedTime = 0;
    state.lastTs = 0;
    state.timeScale = 1;
    state.showLabels = true;
    state.quality = "high";
    planets.forEach((planet, index) => {
      planet.angle = initialAngles[index];
    });
    setPlaying(true);
  }

  function syncControlDefaults() {
    if (speed) speed.value = `${state.timeScale}x`;
    if (quality) quality.value = state.quality;
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
      const raw = event.target.value.replace("x", "");
      const parsed = Number(raw);
      if (!Number.isNaN(parsed)) {
        state.timeScale = parsed;
        updateStatusText();
      }
    });
  }
  if (quality) {
    quality.addEventListener("change", (event) => {
      setQualityLevel(event.target.value);
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
    setQualityLevel,
    applyResetState,
    updateStatusText,
    syncControlDefaults,
  };
}
