/** DOM presentation layer: HUD, screens, toasts, settings and records. */

import { formatMeters } from "./util.js";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

function byId(id) {
  const element = document.getElementById(id);
  if (!element) {
    throw new Error(`Dino Escape page is missing #${id}`);
  }
  return element;
}

function setText(element, value, cache) {
  if (!element) {
    return;
  }
  const stringValue = String(value);
  if (cache && cache.last === stringValue) {
    return;
  }
  element.textContent = stringValue;
  if (cache) {
    cache.last = stringValue;
  }
}

export function createHud() {
  const el = {
    hud: byId("hud"),
    canvas: byId("dino-escape-canvas"),
    fxDanger: document.querySelector(".fx-danger"),
    fxSpeed: document.querySelector(".fx-speed"),
    flash: byId("dino-hit-flash"),
    distance: byId("hud-distance"),
    best: byId("hud-best"),
    gap: byId("hud-gap"),
    gapFill: byId("hud-gap-fill"),
    biome: byId("hud-biome"),
    biomeNext: byId("hud-biome-next"),
    biomeFill: byId("hud-biome-fill"),
    biomeChip: byId("biome-chip"),
    amber: byId("hud-amber"),
    combo: byId("hud-combo"),
    comboFill: byId("hud-combo-fill"),
    comboCard: byId("combo-chip"),
    shield: byId("hud-shield"),
    shieldChip: byId("shield-chip"),
    bait: byId("hud-bait"),
    touchBaitCount: byId("touch-bait-count"),
    stamina: byId("stamina"),
    staminaFill: byId("hud-stamina-fill"),
    speed: byId("hud-speed"),
    tutorial: byId("tutorial-hint"),
    rexcam: byId("rexcam"),
    rexcamWindow: byId("rexcam-window"),
    rexcamDistance: byId("rexcam-distance"),
    rexcamState: byId("rexcam-state"),
    toastLayer: byId("toast-layer"),
    banner: byId("biome-banner"),
    bannerTitle: byId("biome-banner-title"),
    bannerSub: byId("biome-banner-sub"),
    announce: byId("announce"),
    screenStart: byId("screen-start"),
    screenPause: byId("screen-pause"),
    screenGameover: byId("screen-gameover"),
    screenSettings: byId("screen-settings"),
    screenError: byId("screen-error"),
    boot: byId("boot-screen"),
    errorMessage: byId("error-message"),
    btnStart: byId("btn-start"),
    btnStartSettings: byId("btn-start-settings"),
    btnResume: byId("btn-resume"),
    btnRetry: byId("btn-retry"),
    btnPause: byId("btn-pause"),
    btnSettings: byId("btn-settings"),
    btnSettingsClose: byId("btn-settings-close"),
    btnSound: byId("btn-sound"),
    startSound: byId("start-sound"),
    btnRetryLoad: byId("btn-retry-load"),
    pauseDistance: byId("pause-distance"),
    pauseGap: byId("pause-gap"),
    pauseAmber: byId("pause-amber"),
    statDistance: byId("stat-distance"),
    statAmber: byId("stat-amber"),
    statCombo: byId("stat-combo"),
    statHits: byId("stat-hits"),
    statBest: byId("stat-best"),
    newRecord: byId("new-record"),
    startBest: byId("start-best"),
    startBestCombo: byId("start-best-combo"),
    startRuns: byId("start-runs"),
    settingSound: byId("setting-sound"),
    settingMusic: byId("setting-music"),
    settingShake: byId("setting-shake"),
    sfxVolume: byId("sfx-volume"),
    musicVolume: byId("music-volume"),
    sfxValue: byId("sfx-volume-value"),
    musicValue: byId("music-volume-value"),
    qualityGroup: byId("setting-quality"),
    touchButtons: {
      jump: byId("btn-jump"),
      slide: byId("btn-slide"),
      sprint: byId("btn-sprint"),
      bait: byId("btn-bait"),
    },
    keyHints: byId("key-hints"),
    touchControls: byId("touch-controls"),
  };

  const cache = {
    distance: { last: "" },
    best: { last: "" },
    gap: { last: "" },
    amber: { last: "" },
    combo: { last: "" },
    shield: { last: "" },
    bait: { last: "" },
    speed: { last: "" },
    biome: { last: "" },
    biomeNext: { last: "" },
    rexDistance: { last: "" },
    rexState: { last: "" },
    stamina: { last: "" },
    comboWidth: { last: -1 },
    gapWidth: { last: -1 },
    biomeWidth: { last: -1 },
  };

  let onAction = () => {};
  let settingsReturnFocus = null;
  let settingsUnderlyingScreen = null;
  let bannerTimer = 0;
  let flashTimer = 0;
  let tutorialTimer = 0;
  let touchDetected = false;
  let rexCamRect = null;
  let screenState = "start";
  const toasts = [];

  function markTouch() {
    if (touchDetected) {
      return;
    }
    touchDetected = true;
    document.body.classList.add("is-touch");
  }

  if (window.matchMedia && window.matchMedia("(hover: none) and (pointer: coarse)").matches) {
    touchDetected = true;
    document.body.classList.add("is-touch");
  }
  window.addEventListener("pointerdown", (event) => {
    if (event.pointerType === "touch") {
      markTouch();
    }
  }, { passive: true });

  function dispatch(action, payload, event) {
    onAction(action, payload, event);
  }

  function bindClick(element, action, payload) {
    element.addEventListener("click", (event) => {
      event.preventDefault();
      dispatch(action, payload, event);
    });
  }

  function bindActions(callback) {
    onAction = callback;
    for (const element of document.querySelectorAll("[data-action]")) {
      const action = element.dataset.action;
      if (!action) {
        continue;
      }
      element.addEventListener("click", (event) => {
        event.preventDefault();
        dispatch(action, undefined, event);
      });
    }
    bindClick(el.btnStart, "start");
    bindClick(el.btnResume, "resume");
    bindClick(el.btnRetry, "retry");
    bindClick(el.btnRetryLoad, "reload");

    for (const button of el.qualityGroup.querySelectorAll("[data-quality]")) {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        dispatch("quality", button.dataset.quality, event);
      });
    }
    el.sfxVolume.addEventListener("input", () => {
      dispatch("sfx-volume", Number(el.sfxVolume.value) / 100);
    });
    el.musicVolume.addEventListener("input", () => {
      dispatch("music-volume", Number(el.musicVolume.value) / 100);
    });

    document.addEventListener("keydown", (event) => {
      if (el.screenSettings.hidden) {
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        dispatch("close-settings", undefined, event);
      } else if (event.key === "Tab") {
        trapFocus(event);
      }
    });
  }

  function trapFocus(event) {
    const panel = el.screenSettings.querySelector(".panel--settings");
    if (!panel) {
      return;
    }
    const focusable = [...panel.querySelectorAll(FOCUSABLE)].filter((node) => {
      return node.offsetParent !== null || node === document.activeElement;
    });
    if (focusable.length === 0) {
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function hideScreenElement(element) {
    element.hidden = true;
    element.classList.remove("is-open");
    element.inert = false;
  }

  function showScreenElement(element) {
    element.hidden = false;
    element.classList.add("is-open");
    element.inert = false;
  }

  function showScreen(name) {
    screenState = name;
    hideScreenElement(el.screenStart);
    hideScreenElement(el.screenPause);
    hideScreenElement(el.screenGameover);
    let target = null;
    if (name === "start") {
      target = el.screenStart;
      showScreenElement(el.screenStart);
    } else if (name === "pause") {
      target = el.screenPause;
      showScreenElement(el.screenPause);
    } else if (name === "gameover") {
      target = el.screenGameover;
      showScreenElement(el.screenGameover);
    }
    if (target) {
      target.scrollTop = 0;
    }
  }

  function focusPrimary() {
    if (screenState === "pause") {
      el.btnResume.focus({ preventScroll: true });
    } else if (screenState === "gameover") {
      el.btnRetry.focus({ preventScroll: true });
    } else if (screenState === "start") {
      el.btnStart.focus({ preventScroll: true });
    }
  }

  function blurActive() {
    if (document.activeElement instanceof HTMLElement) {
      document.activeElement.blur();
    }
  }

  function setHudVisible(visible) {
    el.hud.dataset.visible = visible ? "true" : "false";
    el.hud.inert = !visible;
    el.hud.setAttribute("aria-hidden", visible ? "false" : "true");
    if (visible) {
      requestAnimationFrame(() => measureRexCam());
    }
  }

  function openSettings() {
    if (!el.screenSettings.hidden) {
      return;
    }
    settingsReturnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    settingsUnderlyingScreen =
      screenState === "pause"
        ? el.screenPause
        : screenState === "start"
          ? el.screenStart
          : screenState === "gameover"
            ? el.screenGameover
            : null;
    if (settingsUnderlyingScreen) {
      settingsUnderlyingScreen.inert = true;
    }
    el.screenSettings.hidden = false;
    el.screenSettings.classList.add("is-open");
    // The panel was display:none one task ago, so focus it after the browser
    // has laid it out; a plain rAF can run before that style recalc and be
    // silently dropped.
    window.setTimeout(() => {
      if (!el.screenSettings.hidden) {
        el.btnSettingsClose.focus({ preventScroll: true });
      }
    }, 0);
  }

  function closeSettings() {
    if (el.screenSettings.hidden) {
      return;
    }
    el.screenSettings.hidden = true;
    el.screenSettings.classList.remove("is-open");
    if (settingsUnderlyingScreen) {
      settingsUnderlyingScreen.inert = false;
    }
    const returnTarget = settingsReturnFocus;
    settingsUnderlyingScreen = null;
    settingsReturnFocus = null;
    requestAnimationFrame(() => {
      if (returnTarget && returnTarget.isConnected && returnTarget.offsetParent !== null) {
        returnTarget.focus({ preventScroll: true });
      } else if (screenState === "pause") {
        el.btnResume.focus({ preventScroll: true });
      } else if (screenState === "start") {
        el.btnStart.focus({ preventScroll: true });
      } else if (screenState === "gameover") {
        el.btnRetry.focus({ preventScroll: true });
      } else {
        el.btnPause.focus({ preventScroll: true });
      }
    });
  }

  function isSettingsOpen() {
    return !el.screenSettings.hidden;
  }

  function updateRun(view) {
    setText(el.distance, formatMeters(view.distance), cache.distance);
    setText(el.best, formatMeters(view.best), cache.best);
    setText(el.gap, `${Math.max(0, view.gap).toFixed(1)}m`, cache.gap);
    setText(el.rexcamDistance, `${Math.max(0, view.gap).toFixed(1)}m`, cache.rexDistance);
    setText(el.amber, String(view.amber), cache.amber);
    setText(el.combo, `x${view.comboMultiplier}`, cache.combo);
    setText(el.shield, String(view.shield), cache.shield);
    setText(el.bait, String(view.bait), cache.bait);
    setText(el.touchBaitCount, String(view.bait), cache.bait);
    setText(el.speed, String(Math.round(view.speedKmh)), cache.speed);
    setText(el.biome, view.biomeName, cache.biome);
    setText(
      el.biomeNext,
      view.nextBiome ? `다음 지역 ${view.nextBiomeDistance}m` : "최종 지역",
      cache.biomeNext,
    );
    setText(
      el.rexcamState,
      view.eating ? "FEEDING" : view.danger > 0.82 ? "CRITICAL" : view.danger > 0.5 ? "CLOSING IN" : "FOLLOWING",
      cache.rexState,
    );

    const gapWidth = Math.max(0, Math.min(100, (view.gap / 15.5) * 100));
    if (Math.abs(gapWidth - cache.gapWidth.last) > 0.4) {
      el.gapFill.style.width = `${gapWidth.toFixed(1)}%`;
      cache.gapWidth.last = gapWidth;
    }
    const biomeWidth = Math.max(0, Math.min(100, view.biomeProgress * 100));
    if (Math.abs(biomeWidth - cache.biomeWidth.last) > 0.4) {
      el.biomeFill.style.width = `${biomeWidth.toFixed(1)}%`;
      cache.biomeWidth.last = biomeWidth;
    }
    const comboRatio = Math.max(0, Math.min(1, view.comboRatio));
    const comboWidth = comboRatio * 100;
    if (Math.abs(comboWidth - cache.comboWidth.last) > 0.5) {
      el.comboFill.style.transform = `scaleX(${comboRatio.toFixed(3)})`;
      cache.comboWidth.last = comboWidth;
    }
    el.comboCard.classList.toggle("is-visible", view.chain >= 2);
    el.shieldChip.classList.toggle("is-on", view.shield > 0);
    el.shieldChip.classList.toggle("is-off", view.shield <= 0);
    el.stamina.classList.toggle("is-active", view.sprinting || view.stamina < 0.98);
    el.stamina.classList.toggle("is-empty", view.staminaLocked);
    el.staminaFill.style.transform = `scaleX(${Math.max(0, Math.min(1, view.stamina)).toFixed(3)})`;
    const danger = Math.max(0, Math.min(1, view.danger));
    el.hud.classList.toggle("is-caution", danger > 0.45);
    el.hud.classList.toggle("is-danger", danger > 0.75);
    el.hud.style.setProperty("--danger-level", (danger * 0.55).toFixed(3));
    if (view.biomeAccent) {
      el.hud.style.setProperty("--biome-accent", view.biomeAccent);
      el.biomeChip.style.setProperty("--biome-accent", view.biomeAccent);
    }
  }

  function setSpeedFx(value) {
    el.hud.style.setProperty("--speed", Math.max(0, Math.min(1, value)).toFixed(3));
  }

  function updatePause(view) {
    el.pauseDistance.textContent = `${formatMeters(view.distance)} M`;
    el.pauseGap.textContent = `${Math.max(0, view.gap).toFixed(1)} m`;
    el.pauseAmber.textContent = String(view.amber);
  }

  function showGameOver(result) {
    el.statDistance.textContent = formatMeters(result.distance);
    el.statAmber.textContent = String(result.amber);
    el.statCombo.textContent = `x${result.bestChain}`;
    el.statHits.textContent = String(result.hits);
    el.statBest.textContent = `${formatMeters(result.best)} M`;
    el.newRecord.hidden = !result.newRecord;
    showScreen("gameover");
    requestAnimationFrame(() => el.btnRetry.focus({ preventScroll: true }));
  }

  function hideAllScreens() {
    hideScreenElement(el.screenStart);
    hideScreenElement(el.screenPause);
    hideScreenElement(el.screenGameover);
    screenState = null;
  }

  function toast(message, options = {}) {
    const tone = options.tone ?? "info";
    const duration = options.duration ?? 1700;
    const item = document.createElement("div");
    item.className = `toast toast--${tone}`;
    if (options.icon) {
      const icon = document.createElement("span");
      icon.className = "toast-icon";
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = options.icon;
      item.append(icon);
    }
    const text = document.createElement("span");
    text.textContent = message;
    item.append(text);
    el.toastLayer.append(item);
    toasts.push(item);
    while (toasts.length > 3) {
      const oldest = toasts.shift();
      oldest.remove();
    }
    window.setTimeout(() => {
      item.classList.add("is-out");
      window.setTimeout(() => {
        item.remove();
        const index = toasts.indexOf(item);
        if (index >= 0) {
          toasts.splice(index, 1);
        }
      }, 260);
    }, duration);
    return item;
  }

  function announce(message) {
    el.announce.textContent = "";
    requestAnimationFrame(() => {
      el.announce.textContent = message;
    });
  }

  function showBiomeBanner(biome) {
    el.bannerTitle.textContent = biome.name;
    el.bannerSub.textContent = biome.english;
    el.banner.hidden = false;
    el.banner.classList.remove("is-out");
    void el.banner.offsetWidth;
    window.clearTimeout(bannerTimer);
    bannerTimer = window.setTimeout(() => {
      el.banner.classList.add("is-out");
      window.setTimeout(() => {
        el.banner.hidden = true;
        el.banner.classList.remove("is-out");
      }, 400);
    }, 4000);
  }

  function flash(tone = "light", duration = 240) {
    el.flash.classList.toggle("is-danger", tone === "danger");
    el.flash.style.opacity = tone === "danger" ? "0.55" : "0.32";
    window.clearTimeout(flashTimer);
    flashTimer = window.setTimeout(() => {
      el.flash.style.opacity = "0";
    }, duration);
  }

  function setTutorial(message, { sticky = false } = {}) {
    window.clearTimeout(tutorialTimer);
    if (!message) {
      el.tutorial.classList.remove("is-visible");
      return;
    }
    el.tutorial.textContent = message;
    el.tutorial.classList.add("is-visible");
    if (!sticky) {
      tutorialTimer = window.setTimeout(() => {
        el.tutorial.classList.remove("is-visible");
      }, 3600);
    }
  }

  function setSoundState(sound) {
    el.btnSound.setAttribute("aria-pressed", String(sound));
    el.btnSound.setAttribute("aria-label", sound ? "소리 끄기" : "소리 켜기");
    el.startSound.setAttribute("aria-pressed", String(sound));
    const label = el.startSound.querySelector(".audio-pill-label");
    if (label) {
      label.textContent = sound ? "소리 켜짐" : "소리 꺼짐";
    }
    el.settingSound.setAttribute("aria-checked", String(sound));
  }

  function setMusicState(music) {
    el.settingMusic.setAttribute("aria-checked", String(music));
  }

  function setShakeState(shake) {
    el.settingShake.setAttribute("aria-checked", String(shake));
  }

  function setQualityState(quality) {
    for (const button of el.qualityGroup.querySelectorAll("[data-quality]")) {
      button.setAttribute("aria-pressed", String(button.dataset.quality === quality));
    }
  }

  function setVolumes(sfxVolume, musicVolume) {
    const sfx = Math.round(sfxVolume * 100);
    const music = Math.round(musicVolume * 100);
    el.sfxVolume.value = String(sfx);
    el.musicVolume.value = String(music);
    el.sfxValue.textContent = String(sfx);
    el.musicValue.textContent = String(music);
  }

  function syncProfile(profile) {
    el.startBest.textContent = `${formatMeters(profile.bestDistance)} M`;
    el.startBestCombo.textContent = `x${Math.max(1, profile.bestCombo)}`;
    el.startRuns.textContent = String(profile.runs);
    setSoundState(profile.settings.sound);
    setMusicState(profile.settings.music);
    setShakeState(profile.settings.shake);
    setQualityState(profile.settings.quality);
    setVolumes(profile.settings.sfxVolume, profile.settings.musicVolume);
  }

  function measureRexCam() {
    if (el.rexcamWindow.offsetWidth < 10 || getComputedStyle(el.rexcam).display === "none") {
      rexCamRect = null;
      return null;
    }
    const rect = el.rexcamWindow.getBoundingClientRect();
    const canvasRect = el.canvas.getBoundingClientRect();
    rexCamRect = {
      x: rect.left - canvasRect.left,
      y: rect.top - canvasRect.top,
      width: rect.width,
      height: rect.height,
      canvasWidth: canvasRect.width,
      canvasHeight: canvasRect.height,
      visible:
        rect.width > 10 &&
        rect.height > 10 &&
        el.hud.dataset.visible === "true" &&
        !el.hud.inert,
    };
    return rexCamRect;
  }

  function getRexCamRect() {
    return rexCamRect;
  }

  function hideBoot() {
    if (el.boot.hidden) {
      return;
    }
    el.boot.classList.add("is-done");
    window.setTimeout(() => {
      el.boot.hidden = true;
    }, 720);
  }

  function showError(message) {
    el.boot.hidden = true;
    el.errorMessage.textContent = message;
    el.screenError.hidden = false;
    el.screenError.classList.add("is-open");
    document.querySelectorAll(".hud, .screen--start").forEach((node) => {
      if (node !== el.screenError) {
        node.hidden = true;
        node.classList.remove("is-open");
      }
    });
    requestAnimationFrame(() => el.btnRetryLoad.focus({ preventScroll: true }));
  }

  function setScreenVisible(name) {
    if (name) {
      showScreen(name);
    }
  }

  return {
    elements: el,
    touchButtons: el.touchButtons,
    bindActions,
    setHudVisible,
    showScreen,
    hideAllScreens,
    setScreenVisible,
    focusPrimary,
    blurActive,
    openSettings,
    closeSettings,
    isSettingsOpen,
    updateRun,
    updatePause,
    showGameOver,
    toast,
    announce,
    showBiomeBanner,
    flash,
    setTutorial,
    setSpeedFx,
    setSoundState,
    setMusicState,
    setShakeState,
    setQualityState,
    setVolumes,
    syncProfile,
    measureRexCam,
    getRexCamRect,
    hideBoot,
    showError,
    markTouch,
    get screenState() {
      return screenState;
    },
  };
}
