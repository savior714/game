/**
 * Procedural WebAudio engine for Dino Escape.
 *
 * No audio files: wind, drums, roars, chomps and UI blips are synthesized.
 * Everything is created lazily after a user gesture so browsers never block it.
 */

const clamp01 = (value) => Math.max(0, Math.min(1, value));
const lerp = (a, b, t) => a + (b - a) * t;
const midiToFreq = (midi) => 440 * 2 ** ((midi - 69) / 12);

const PENTATONIC = [62, 64, 67, 69, 72, 74, 77, 79, 81, 84];

/**
 * Ambience is a bed, not a lead. Each layer keeps a low gain and a narrow,
 * slow-moving filter so the mix breathes like wind instead of hissing like
 * untuned static (the old 520 Hz / Q 0.55 band plus a 2.4 kHz highpass read as
 * a continuous "shhh" and buried the music).
 */
const BIOME_AMBIENCE = {
  jungle: { wind: 300, air: 900, windGain: 0.028, airGain: 0.006, rumble: 0 },
  desert: { wind: 240, air: 1400, windGain: 0.024, airGain: 0.009, rumble: 0 },
  volcano: { wind: 150, air: 620, windGain: 0.03, airGain: 0.003, rumble: 0.03 },
};

export function createAudioEngine(initialSettings = {}) {
  let ctx = null;
  let master = null;
  let compressor = null;
  let sfxBus = null;
  let musicBus = null;
  let ambienceBus = null;
  let reverbSend = null;
  let reverb = null;
  let reverbReturn = null;
  let noiseBuffer = null;
  let windSource = null;
  let leavesSource = null;
  let windFilter = null;
  let leavesFilter = null;
  let windGain = null;
  let leavesGain = null;
  let droneGain = null;
  let droneFilter = null;
  let rumbleGain = null;
  let tensionGain = null;
  let slideSource = null;
  let slideGain = null;
  let slideFilter = null;
  let step = 0;
  let nextStepTime = 0;
  let nextHeartbeat = 0;
  let bar = 0;
  let failed = false;

  const settings = {
    sound: initialSettings.sound ?? true,
    music: initialSettings.music ?? true,
    sfxVolume: clamp01(initialSettings.sfxVolume ?? 0.7),
    musicVolume: clamp01(initialSettings.musicVolume ?? 0.5),
  };

  const state = {
    mode: "menu",
    biome: "jungle",
    threat: 0,
    suspended: false,
  };

  function makeNoiseBuffer(seconds = 2) {
    const length = Math.floor(ctx.sampleRate * seconds);
    const buffer = ctx.createBuffer(1, length, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < length; i += 1) {
      data[i] = Math.random() * 2 - 1;
    }
    return buffer;
  }

  function makeImpulse(seconds = 1.7, decay = 3.2) {
    const length = Math.floor(ctx.sampleRate * seconds);
    const buffer = ctx.createBuffer(2, length, ctx.sampleRate);
    for (let channel = 0; channel < 2; channel += 1) {
      const data = buffer.getChannelData(channel);
      for (let i = 0; i < length; i += 1) {
        const t = i / length;
        data[i] = (Math.random() * 2 - 1) * (1 - t) ** decay * (channel === 0 ? 0.8 : 0.65);
      }
    }
    return buffer;
  }

  function makeSoftClipCurve(amount = 2.4) {
    const samples = 1024;
    const curve = new Float32Array(samples);
    for (let i = 0; i < samples; i += 1) {
      const x = (i / (samples - 1)) * 2 - 1;
      curve[i] = Math.tanh(x * amount) * 0.75;
    }
    return curve;
  }

  const softClipCurve = typeof Float32Array !== "undefined" ? makeSoftClipCurve() : null;

  async function unlock() {
    if (failed) {
      return false;
    }
    if (!ctx) {
      const Context = window.AudioContext || window.webkitAudioContext;
      if (!Context) {
        failed = true;
        return false;
      }
      try {
        ctx = new Context();
      } catch (error) {
        failed = true;
        console.warn("Dino Escape: WebAudio unavailable", error);
        return false;
      }
      master = ctx.createGain();
      master.gain.value = 0;
      compressor = ctx.createDynamicsCompressor();
      compressor.threshold.value = -16;
      compressor.knee.value = 18;
      compressor.ratio.value = 5;
      compressor.attack.value = 0.005;
      compressor.release.value = 0.24;
      master.connect(compressor);
      compressor.connect(ctx.destination);

      sfxBus = ctx.createGain();
      sfxBus.gain.value = settings.sfxVolume;
      musicBus = ctx.createGain();
      musicBus.gain.value = settings.music ? settings.musicVolume * 0.8 : 0;
      ambienceBus = ctx.createGain();
      ambienceBus.gain.value = settings.sound ? 0.6 : 0;
      sfxBus.connect(master);
      musicBus.connect(master);
      ambienceBus.connect(master);

      reverb = ctx.createConvolver();
      reverb.buffer = makeImpulse();
      reverbReturn = ctx.createGain();
      reverbReturn.gain.value = 0.34;
      reverb.connect(reverbReturn);
      reverbReturn.connect(master);
      reverbSend = ctx.createGain();
      reverbSend.gain.value = 0.55;
      reverbSend.connect(reverb);

      noiseBuffer = makeNoiseBuffer();
      startAmbience();
      startDrone();
      applySettings(true);
      nextStepTime = ctx.currentTime + 0.15;
      nextHeartbeat = ctx.currentTime + 1;
    }
    if (ctx.state === "suspended") {
      try {
        await ctx.resume();
      } catch (error) {
        console.warn("Dino Escape: audio resume failed", error);
      }
    }
    applySettings(true);
    return ctx.state === "running";
  }

  function startAmbience() {
    // Low, slowly-modulated wind: filtered noise plus two very slow LFOs that
    // open the filter and swell the gain, so the pad never sits on one pitch.
    windSource = ctx.createBufferSource();
    windSource.buffer = noiseBuffer;
    windSource.loop = true;
    windFilter = ctx.createBiquadFilter();
    windFilter.type = "lowpass";
    windFilter.frequency.value = BIOME_AMBIENCE.jungle.wind;
    windFilter.Q.value = 0.9;
    windGain = ctx.createGain();
    windGain.gain.value = BIOME_AMBIENCE.jungle.windGain;
    windSource.connect(windFilter);
    windFilter.connect(windGain);
    // Slow stereo drift: a wall of centred noise reads as a hiss, a moving
    // stereo image reads as air around the player.
    if (typeof ctx.createStereoPanner === "function") {
      const windPan = ctx.createStereoPanner();
      windPan.pan.value = 0;
      windGain.connect(windPan);
      windPan.connect(ambienceBus);
      const panDrift = ctx.createOscillator();
      panDrift.type = "sine";
      panDrift.frequency.value = 0.043;
      const panDepth = ctx.createGain();
      panDepth.gain.value = 0.34;
      panDrift.connect(panDepth);
      panDepth.connect(windPan.pan);
      panDrift.start();
    } else {
      windGain.connect(ambienceBus);
    }
    windSource.start();

    const gust = ctx.createOscillator();
    gust.type = "sine";
    gust.frequency.value = 0.07;
    const gustDepth = ctx.createGain();
    gustDepth.gain.value = 0.012;
    gust.connect(gustDepth);
    gustDepth.connect(windGain.gain);
    gust.start();

    const drift = ctx.createOscillator();
    drift.type = "sine";
    drift.frequency.value = 0.031;
    const driftDepth = ctx.createGain();
    driftDepth.gain.value = 130;
    drift.connect(driftDepth);
    driftDepth.connect(windFilter.frequency);
    drift.start();

    // A whisper of high air for movement, kept far below the old hiss.
    leavesSource = ctx.createBufferSource();
    leavesSource.buffer = noiseBuffer;
    leavesSource.loop = true;
    leavesSource.playbackRate.value = 0.6;
    leavesFilter = ctx.createBiquadFilter();
    leavesFilter.type = "highpass";
    leavesFilter.frequency.value = BIOME_AMBIENCE.jungle.air;
    leavesFilter.Q.value = 0.7;
    leavesGain = ctx.createGain();
    leavesGain.gain.value = BIOME_AMBIENCE.jungle.airGain;
    leavesSource.connect(leavesFilter);
    leavesFilter.connect(leavesGain);
    leavesGain.connect(ambienceBus);
    leavesSource.start();

    rumbleGain = ctx.createGain();
    rumbleGain.gain.value = 0;
    const rumbleSource = ctx.createBufferSource();
    rumbleSource.buffer = noiseBuffer;
    rumbleSource.loop = true;
    const rumbleFilter = ctx.createBiquadFilter();
    rumbleFilter.type = "lowpass";
    rumbleFilter.frequency.value = 75;
    rumbleSource.connect(rumbleFilter);
    rumbleFilter.connect(rumbleGain);
    rumbleGain.connect(ambienceBus);
    rumbleSource.start();
  }

  function startDrone() {
    droneGain = ctx.createGain();
    droneGain.gain.value = 0.02;
    droneFilter = ctx.createBiquadFilter();
    droneFilter.type = "lowpass";
    droneFilter.frequency.value = 190;
    droneFilter.Q.value = 1.2;
    droneGain.connect(droneFilter);
    droneFilter.connect(musicBus);
    for (const [freq, detune] of [
      [55, -7],
      [82.5, 9],
      [110, 4],
    ]) {
      const osc = ctx.createOscillator();
      osc.type = "sawtooth";
      osc.frequency.value = freq;
      osc.detune.value = detune;
      osc.connect(droneGain);
      osc.start();
    }

    tensionGain = ctx.createGain();
    tensionGain.gain.value = 0;
    const tension = ctx.createOscillator();
    tension.type = "triangle";
    tension.frequency.value = 233;
    const tensionFilter = ctx.createBiquadFilter();
    tensionFilter.type = "bandpass";
    tensionFilter.frequency.value = 580;
    tensionFilter.Q.value = 2.4;
    tension.connect(tensionFilter);
    tensionFilter.connect(tensionGain);
    tensionGain.connect(musicBus);
    tension.start();
  }

  function applySettings(instant = false) {
    if (!ctx) {
      return;
    }
    const t = ctx.currentTime;
    const ramp = instant ? 0.02 : 0.18;
    master.gain.cancelScheduledValues(t);
    const musicPaused = state.mode === "paused";
    master.gain.setTargetAtTime(settings.sound ? 0.85 : 0.0001, t, ramp);
    sfxBus.gain.setTargetAtTime(settings.sfxVolume, t, ramp);
    musicBus.gain.setTargetAtTime(
      settings.music && !musicPaused ? settings.musicVolume * 0.8 : 0.0001,
      t,
      ramp,
    );
    // Wind is ambience, not music: it follows the master sound switch and
    // drops back (rather than vanishing) while the game is paused.
    ambienceBus.gain.setTargetAtTime(
      settings.sound ? (musicPaused ? 0.22 : 0.6) : 0.0001,
      t,
      ramp,
    );
  }

  function setSettings(next) {
    Object.assign(settings, {
      sound: next.sound ?? settings.sound,
      music: next.music ?? settings.music,
      sfxVolume: clamp01(next.sfxVolume ?? settings.sfxVolume),
      musicVolume: clamp01(next.musicVolume ?? settings.musicVolume),
    });
    applySettings();
  }

  function canPlaySfx() {
    return Boolean(ctx && !failed && settings.sound);
  }

  function connectPanned(node, pan = 0, reverbAmount = 0.12) {
    if (typeof ctx.createStereoPanner === "function") {
      const panner = ctx.createStereoPanner();
      panner.pan.value = Math.max(-1, Math.min(1, pan));
      node.connect(panner);
      panner.connect(sfxBus);
      if (reverbAmount > 0 && reverbSend) {
        const send = ctx.createGain();
        send.gain.value = reverbAmount;
        panner.connect(send);
        send.connect(reverbSend);
      }
      return panner;
    }
    node.connect(sfxBus);
    return node;
  }

  function envelope(gainNode, start, peak, attack, decay) {
    const gain = gainNode.gain;
    gain.cancelScheduledValues(start);
    gain.setValueAtTime(0.0001, start);
    gain.exponentialRampToValueAtTime(Math.max(0.0002, peak), start + attack);
    gain.exponentialRampToValueAtTime(0.0001, start + attack + decay);
  }

  function noiseBurst({ duration = 0.2, filterType = "lowpass", frequency = 800, q = 1, gain = 0.12, pan = 0, time = 0, rate = 1, reverbAmount = 0.1 }) {
    if (!canPlaySfx()) {
      return;
    }
    const start = time || ctx.currentTime;
    const source = ctx.createBufferSource();
    source.buffer = noiseBuffer;
    source.playbackRate.value = rate;
    const filter = ctx.createBiquadFilter();
    filter.type = filterType;
    filter.frequency.value = frequency;
    filter.Q.value = q;
    const amp = ctx.createGain();
    envelope(amp, start, gain, 0.008, duration);
    source.connect(filter);
    filter.connect(amp);
    connectPanned(amp, pan, reverbAmount);
    source.start(start);
    source.stop(start + duration + 0.06);
    source.onended = () => {
      source.disconnect();
      filter.disconnect();
      amp.disconnect();
    };
  }

  function tone({ frequency = 440, endFrequency = frequency, type = "sine", duration = 0.25, gain = 0.08, pan = 0, time = 0, attack = 0.006, reverbAmount = 0.08 }) {
    if (!canPlaySfx()) {
      return;
    }
    const start = time || ctx.currentTime;
    const osc = ctx.createOscillator();
    osc.type = type;
    osc.frequency.setValueAtTime(frequency, start);
    if (endFrequency !== frequency) {
      osc.frequency.exponentialRampToValueAtTime(Math.max(20, endFrequency), start + duration);
    }
    const amp = ctx.createGain();
    envelope(amp, start, gain, attack, duration);
    osc.connect(amp);
    connectPanned(amp, pan, reverbAmount);
    osc.start(start);
    osc.stop(start + duration + attack + 0.05);
    osc.onended = () => {
      osc.disconnect();
      amp.disconnect();
    };
  }

  function footstep(strength = 1, pan = 0, rex = false) {
    if (!canPlaySfx()) {
      return;
    }
    const now = ctx.currentTime;
    if (rex) {
      noiseBurst({ duration: 0.14, filterType: "lowpass", frequency: 150, gain: 0.16 * strength, pan, time: now, reverbAmount: 0.06 });
      tone({ frequency: 62, endFrequency: 38, type: "sine", duration: 0.18, gain: 0.11 * strength, time: now, reverbAmount: 0.05 });
    } else {
      noiseBurst({
        duration: 0.055,
        filterType: "lowpass",
        frequency: 420 + Math.random() * 160,
        gain: 0.055 * strength,
        pan,
        time: now,
        rate: 0.9 + Math.random() * 0.25,
        reverbAmount: 0.02,
      });
    }
  }

  function jump() {
    noiseBurst({ duration: 0.16, filterType: "bandpass", frequency: 900, q: 0.8, gain: 0.07, reverbAmount: 0.05 });
    tone({ frequency: 300, endFrequency: 620, type: "triangle", duration: 0.14, gain: 0.035 });
  }

  function land(strength = 1) {
    noiseBurst({ duration: 0.16, filterType: "lowpass", frequency: 300, gain: 0.1 * strength, reverbAmount: 0.04 });
    tone({ frequency: 90, endFrequency: 52, type: "sine", duration: 0.16, gain: 0.06 * strength });
  }

  function slideStart() {
    if (!canPlaySfx() || slideSource) {
      return;
    }
    slideSource = ctx.createBufferSource();
    slideSource.buffer = noiseBuffer;
    slideSource.loop = true;
    const filter = ctx.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.value = 1300;
    filter.Q.value = 0.7;
    slideGain = ctx.createGain();
    slideGain.gain.value = 0.001;
    slideSource.connect(filter);
    filter.connect(slideGain);
    slideGain.connect(sfxBus);
    slideSource.start();
    slideGain.gain.setTargetAtTime(0.055, ctx.currentTime, 0.04);
    slideFilter = filter;
  }

  function slideStop() {
    if (!slideSource) {
      return;
    }
    const source = slideSource;
    const gain = slideGain;
    const filter = slideFilter;
    slideSource = null;
    slideGain = null;
    slideFilter = null;
    const now = ctx.currentTime;
    gain.gain.cancelScheduledValues(now);
    gain.gain.setTargetAtTime(0.0001, now, 0.06);
    source.stop(now + 0.28);
    source.onended = () => {
      source.disconnect();
      filter.disconnect();
      gain.disconnect();
    };
  }

  function amber(chain = 0) {
    if (!canPlaySfx()) {
      return;
    }
    const note = PENTATONIC[Math.min(PENTATONIC.length - 1, chain % PENTATONIC.length)];
    const now = ctx.currentTime;
    const pan = (Math.random() * 2 - 1) * 0.28;
    tone({ frequency: midiToFreq(note), type: "triangle", duration: 0.16, gain: 0.06, pan, time: now, reverbAmount: 0.28 });
    tone({ frequency: midiToFreq(note + 12), type: "sine", duration: 0.12, gain: 0.028, pan, time: now + 0.015, reverbAmount: 0.24 });
  }

  function baitPickup() {
    tone({ frequency: 196, endFrequency: 294, type: "triangle", duration: 0.2, gain: 0.055, reverbAmount: 0.16 });
  }

  function shieldPickup() {
    const now = ctx.currentTime;
    [880, 1174, 1568].forEach((freq, index) => {
      tone({ frequency: freq, type: "sine", duration: 0.5 - index * 0.06, gain: 0.05, time: now + index * 0.045, reverbAmount: 0.45 });
    });
  }

  function shieldBreak() {
    noiseBurst({ duration: 0.38, filterType: "highpass", frequency: 1800, gain: 0.12, reverbAmount: 0.4 });
    tone({ frequency: 1480, endFrequency: 620, type: "sine", duration: 0.4, gain: 0.05, reverbAmount: 0.4 });
  }

  function hit() {
    const now = ctx.currentTime;
    noiseBurst({ duration: 0.3, filterType: "lowpass", frequency: 700, gain: 0.2, time: now, reverbAmount: 0.16 });
    tone({ frequency: 150, endFrequency: 42, type: "sawtooth", duration: 0.38, gain: 0.12, time: now, reverbAmount: 0.12 });
  }

  function geyser() {
    if (!canPlaySfx()) {
      return;
    }
    const now = ctx.currentTime;
    noiseBurst({
      duration: 0.9,
      filterType: "bandpass",
      frequency: 480,
      q: 0.9,
      gain: 0.19,
      time: now,
      rate: 0.75,
      reverbAmount: 0.3,
    });
    tone({ frequency: 96, endFrequency: 44, type: "sawtooth", duration: 0.7, gain: 0.07, time: now, reverbAmount: 0.22 });
  }

  function roar(intensity = 1) {
    if (!canPlaySfx()) {
      return;
    }
    const start = ctx.currentTime;
    const duration = 1.35;
    const safeIntensity = Math.max(0.25, intensity);
    const out = ctx.createGain();
    out.gain.setValueAtTime(0.0001, start);
    out.gain.exponentialRampToValueAtTime(0.11 * safeIntensity, start + 0.16);
    out.gain.setValueAtTime(0.11 * safeIntensity, start + 0.62);
    out.gain.exponentialRampToValueAtTime(0.0001, start + duration);

    const shaper = ctx.createWaveShaper();
    shaper.curve = softClipCurve;
    shaper.oversample = "2x";
    const lowpass = ctx.createBiquadFilter();
    lowpass.type = "lowpass";
    lowpass.frequency.setValueAtTime(900, start);
    lowpass.frequency.exponentialRampToValueAtTime(380, start + duration);
    lowpass.Q.value = 4;
    lowpass.connect(shaper);
    shaper.connect(out);
    connectPanned(out, 0, 0.5);

    // Growl oscillators.
    for (const [freq, detune, level] of [
      [58, -12, 0.9],
      [87, 9, 0.55],
      [116, 4, 0.28],
    ]) {
      const osc = ctx.createOscillator();
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(freq * 1.16, start);
      osc.frequency.exponentialRampToValueAtTime(freq, start + 0.5);
      osc.frequency.exponentialRampToValueAtTime(freq * 0.86, start + duration);
      osc.detune.value = detune;
      const gain = ctx.createGain();
      gain.gain.value = level;
      const lfo = ctx.createOscillator();
      lfo.type = "sine";
      lfo.frequency.value = 17 + Math.random() * 4;
      const lfoGain = ctx.createGain();
      lfoGain.gain.value = 0.35;
      lfo.connect(lfoGain);
      lfoGain.connect(gain.gain);
      osc.connect(gain);
      gain.connect(lowpass);
      osc.start(start);
      osc.stop(start + duration + 0.1);
      lfo.start(start);
      lfo.stop(start + duration + 0.1);
      osc.onended = () => {
        osc.disconnect();
        gain.disconnect();
        lfo.disconnect();
        lfoGain.disconnect();
      };
    }

    // Breath noise.
    const breath = ctx.createBufferSource();
    breath.buffer = noiseBuffer;
    const breathFilter = ctx.createBiquadFilter();
    breathFilter.type = "bandpass";
    breathFilter.frequency.setValueAtTime(440, start);
    breathFilter.frequency.exponentialRampToValueAtTime(190, start + duration);
    breathFilter.Q.value = 1.3;
    const breathGain = ctx.createGain();
    breathGain.gain.setValueAtTime(0.0001, start);
    breathGain.gain.exponentialRampToValueAtTime(0.045 * safeIntensity, start + 0.25);
    breathGain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
    breath.connect(breathFilter);
    breathFilter.connect(breathGain);
    breathGain.connect(lowpass);
    breath.start(start);
    breath.stop(start + duration + 0.05);
    breath.onended = () => {
      breath.disconnect();
      breathFilter.disconnect();
      breathGain.disconnect();
      lowpass.disconnect();
      shaper.disconnect();
      out.disconnect();
    };
  }

  function chomp() {
    const now = ctx.currentTime;
    noiseBurst({ duration: 0.1, filterType: "lowpass", frequency: 480, gain: 0.14, time: now, reverbAmount: 0.08 });
    noiseBurst({ duration: 0.09, filterType: "lowpass", frequency: 360, gain: 0.11, time: now + 0.18, reverbAmount: 0.08 });
    tone({ frequency: 74, endFrequency: 44, type: "square", duration: 0.12, gain: 0.05, time: now + 0.02 });
  }

  function baitThrow() {
    noiseBurst({ duration: 0.25, filterType: "bandpass", frequency: 700, q: 1.2, gain: 0.06, rate: 0.8, reverbAmount: 0.1 });
  }

  function milestone() {
    const now = ctx.currentTime;
    [72, 76, 79, 84].forEach((note, index) => {
      tone({
        frequency: midiToFreq(note),
        type: "triangle",
        duration: 0.34,
        gain: 0.05,
        time: now + index * 0.07,
        reverbAmount: 0.35,
      });
    });
    noiseBurst({ duration: 0.45, filterType: "highpass", frequency: 4200, gain: 0.035, time: now, reverbAmount: 0.3 });
  }

  function biomeShift() {
    const now = ctx.currentTime;
    noiseBurst({ duration: 1.6, filterType: "bandpass", frequency: 600, q: 0.6, gain: 0.05, time: now, reverbAmount: 0.5 });
    tone({ frequency: 65, endFrequency: 49, type: "sine", duration: 1.8, gain: 0.08, time: now, reverbAmount: 0.45 });
    [62, 65, 69].forEach((note, index) => {
      tone({ frequency: midiToFreq(note), type: "sine", duration: 2.4, gain: 0.028, attack: 0.5, time: now + index * 0.14, reverbAmount: 0.6 });
    });
  }

  function gameOver() {
    const now = ctx.currentTime;
    [57, 53, 50, 45].forEach((note, index) => {
      tone({ frequency: midiToFreq(note), type: "triangle", duration: 0.7, gain: 0.05, attack: 0.02, time: now + 0.35 + index * 0.22, reverbAmount: 0.45 });
    });
    tone({ frequency: 70, endFrequency: 35, type: "sine", duration: 1.6, gain: 0.12, time: now + 0.1, reverbAmount: 0.35 });
  }

  function uiClick() {
    tone({ frequency: 660, endFrequency: 880, type: "triangle", duration: 0.07, gain: 0.03, reverbAmount: 0.04 });
  }

  function uiBack() {
    tone({ frequency: 440, endFrequency: 300, type: "triangle", duration: 0.09, gain: 0.028, reverbAmount: 0.03 });
  }

  /* Music scheduler ------------------------------------------------- */
  /*
   * A composed bed rather than a random sprinkle: 104 BPM, four-on-the-floor
   * kick, snare on 2 and 4, shakers, a moving bass line, sustained pad chords
   * and a pentatonic pluck motif. The motif is fixed (not random) so a child
   * can recognise the tune; the threat level only adds intensity on top.
   */

  const MUSIC = Object.freeze({
    bpm: 104,
    stepsPerBar: 16,
    bars: 64,
    bassPattern: [38, 38, 36, 41, 38, 38, 43, 36],
    // Indices into PENTATONIC, one bar's worth of pickups.
    motif: [0, 2, 4, 2, 5, 4, 2, 0, 1, 3, 5, 3, 6, 5, 3, 1],
    motifSlots: [0, 3, 6, 10, 12],
  });

  function scheduleKick(time, gain = 0.42) {
    const osc = ctx.createOscillator();
    osc.type = "sine";
    osc.frequency.setValueAtTime(118, time);
    osc.frequency.exponentialRampToValueAtTime(44, time + 0.18);
    const amp = ctx.createGain();
    envelope(amp, time, gain, 0.004, 0.24);
    osc.connect(amp);
    amp.connect(musicBus);
    const send = ctx.createGain();
    send.gain.value = 0.05;
    amp.connect(send);
    send.connect(reverbSend);
    osc.start(time);
    osc.stop(time + 0.32);
    osc.onended = () => {
      osc.disconnect();
      amp.disconnect();
      send.disconnect();
    };
  }

  function scheduleSnare(time, gain = 0.17) {
    const source = ctx.createBufferSource();
    source.buffer = noiseBuffer;
    const filter = ctx.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.value = 1900;
    filter.Q.value = 0.9;
    const amp = ctx.createGain();
    envelope(amp, time, gain, 0.002, 0.14);
    source.connect(filter);
    filter.connect(amp);
    amp.connect(musicBus);
    const send = ctx.createGain();
    send.gain.value = 0.16;
    amp.connect(send);
    send.connect(reverbSend);
    source.start(time);
    source.stop(time + 0.2);
    source.onended = () => {
      source.disconnect();
      filter.disconnect();
      amp.disconnect();
      send.disconnect();
    };
    const body = ctx.createOscillator();
    body.type = "triangle";
    body.frequency.setValueAtTime(196, time);
    body.frequency.exponentialRampToValueAtTime(150, time + 0.09);
    const bodyAmp = ctx.createGain();
    envelope(bodyAmp, time, gain * 0.5, 0.002, 0.1);
    body.connect(bodyAmp);
    bodyAmp.connect(musicBus);
    body.start(time);
    body.stop(time + 0.15);
    body.onended = () => {
      body.disconnect();
      bodyAmp.disconnect();
    };
  }

  function scheduleHat(time, gain = 0.045) {
    const source = ctx.createBufferSource();
    source.buffer = noiseBuffer;
    source.playbackRate.value = 1.9;
    const filter = ctx.createBiquadFilter();
    filter.type = "highpass";
    filter.frequency.value = 7200;
    const amp = ctx.createGain();
    envelope(amp, time, gain, 0.001, 0.05);
    source.connect(filter);
    filter.connect(amp);
    amp.connect(musicBus);
    source.start(time);
    source.stop(time + 0.08);
    source.onended = () => {
      source.disconnect();
      filter.disconnect();
      amp.disconnect();
    };
  }

  function scheduleBass(time, midi, gain = 0.2) {
    const osc = ctx.createOscillator();
    osc.type = "triangle";
    osc.frequency.value = midiToFreq(midi);
    const sub = ctx.createOscillator();
    sub.type = "sine";
    sub.frequency.value = midiToFreq(midi - 12);
    const filter = ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.setValueAtTime(520, time);
    filter.frequency.exponentialRampToValueAtTime(220, time + 0.4);
    filter.Q.value = 4;
    const amp = ctx.createGain();
    envelope(amp, time, gain, 0.012, 0.5);
    const subAmp = ctx.createGain();
    envelope(subAmp, time, gain * 0.5, 0.012, 0.45);
    osc.connect(filter);
    filter.connect(amp);
    sub.connect(subAmp);
    amp.connect(musicBus);
    subAmp.connect(musicBus);
    osc.start(time);
    osc.stop(time + 0.7);
    sub.start(time);
    sub.stop(time + 0.7);
    osc.onended = () => {
      osc.disconnect();
      sub.disconnect();
      filter.disconnect();
      amp.disconnect();
      subAmp.disconnect();
    };
  }

  function schedulePad(time, notes, gain = 0.05) {
    for (const midi of notes) {
      const osc = ctx.createOscillator();
      osc.type = "sine";
      osc.frequency.value = midiToFreq(midi);
      osc.detune.value = Math.random() * 8 - 4;
      const filter = ctx.createBiquadFilter();
      filter.type = "lowpass";
      filter.frequency.value = 1300;
      const amp = ctx.createGain();
      amp.gain.setValueAtTime(0.0001, time);
      amp.gain.exponentialRampToValueAtTime(gain, time + 0.9);
      amp.gain.setValueAtTime(gain, time + 3.0);
      amp.gain.exponentialRampToValueAtTime(0.0001, time + 4.4);
      osc.connect(filter);
      filter.connect(amp);
      amp.connect(musicBus);
      const send = ctx.createGain();
      send.gain.value = 0.4;
      amp.connect(send);
      send.connect(reverbSend);
      osc.start(time);
      osc.stop(time + 4.6);
      osc.onended = () => {
        osc.disconnect();
        filter.disconnect();
        amp.disconnect();
        send.disconnect();
      };
    }
  }

  function schedulePluck(time, midi, gain = 0.12) {
    const osc = ctx.createOscillator();
    osc.type = "triangle";
    osc.frequency.value = midiToFreq(midi);
    const click = ctx.createOscillator();
    click.type = "sine";
    click.frequency.value = midiToFreq(midi + 12);
    const filter = ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.setValueAtTime(3400, time);
    filter.frequency.exponentialRampToValueAtTime(1200, time + 0.35);
    const amp = ctx.createGain();
    envelope(amp, time, gain, 0.004, 0.38);
    const clickAmp = ctx.createGain();
    envelope(clickAmp, time, gain * 0.28, 0.002, 0.09);
    osc.connect(filter);
    filter.connect(amp);
    amp.connect(musicBus);
    click.connect(clickAmp);
    clickAmp.connect(musicBus);
    const send = ctx.createGain();
    send.gain.value = 0.3;
    amp.connect(send);
    send.connect(reverbSend);
    osc.start(time);
    osc.stop(time + 0.5);
    click.start(time);
    click.stop(time + 0.14);
    osc.onended = () => {
      osc.disconnect();
      click.disconnect();
      filter.disconnect();
      amp.disconnect();
      clickAmp.disconnect();
      send.disconnect();
    };
  }

  function scheduleStep(stepIndex, time, barIndex) {
    const motif = MUSIC.motif;
    if (state.mode === "menu") {
      // A calm version of the same tune so the start screen has music too.
      if (stepIndex === 0 && barIndex % 2 === 0) {
        schedulePad(time, barIndex % 4 === 0 ? [50, 53, 57] : [46, 50, 53], 0.036);
        scheduleBass(time, barIndex % 4 === 0 ? 38 : 34, 0.1);
      }
      if (stepIndex % 4 === 0) {
        const slot = (stepIndex / 4 + barIndex * 2) % motif.length;
        schedulePluck(time, PENTATONIC[motif[slot]] + 12, 0.05);
      }
      return;
    }
    if (state.mode === "caught" || state.mode === "paused" || state.mode === "intro") {
      return;
    }
    const threat = clamp01(state.threat);
    const intensity = state.mode === "running" ? 1 : 0.4;
    const kickSteps = [0, 6, 10, 14];
    if (kickSteps.includes(stepIndex)) {
      scheduleKick(time, (stepIndex === 0 ? 0.42 : 0.28) * intensity);
    }
    if (stepIndex === 4 || stepIndex === 12) {
      scheduleSnare(time, (stepIndex === 12 ? 0.19 : 0.15) * intensity);
    }
    if (stepIndex % 2 === 0) {
      scheduleHat(time, (stepIndex % 4 === 0 ? 0.05 : 0.028) * (0.7 + threat * 0.5));
    }
    if (stepIndex === 0 || stepIndex === 8) {
      scheduleBass(time, MUSIC.bassPattern[barIndex % MUSIC.bassPattern.length], 0.2);
      if (stepIndex === 0 && barIndex % 2 === 0) {
        schedulePad(time, barIndex % 8 === 0 ? [50, 53, 57] : [48, 51, 55], 0.044);
      }
    }
    const motifSlot = MUSIC.motifSlots.indexOf(stepIndex);
    if (motifSlot >= 0 && (barIndex % 2 === 0 || threat > 0.4)) {
      const note = PENTATONIC[motif[(barIndex * 5 + motifSlot) % motif.length]];
      schedulePluck(time, note + (threat > 0.6 ? 12 : 0), 0.12 * (0.75 + threat * 0.35));
    }
  }

  function tick() {
    if (!ctx || failed || !settings.music || state.suspended) {
      nextStepTime = 0;
      return;
    }
    if (ctx.state !== "running") {
      return;
    }
    const now = ctx.currentTime;
    if (nextStepTime === 0 || nextStepTime < now - 0.5) {
      nextStepTime = now + 0.08;
    }
    const bpm = MUSIC.bpm + state.threat * 6;
    const stepDuration = 60 / bpm / 4;
    let guard = 0;
    while (nextStepTime < now + 0.2 && guard < 24) {
      scheduleStep(step, nextStepTime, bar);
      nextStepTime += stepDuration;
      step = (step + 1) % MUSIC.stepsPerBar;
      if (step === 0) {
        bar = (bar + 1) % MUSIC.bars;
      }
      guard += 1;
    }
    if (state.mode === "running" && state.threat > 0.5) {
      const interval = lerp(1.25, 0.62, state.threat);
      while (nextHeartbeat < now + 0.2) {
        scheduleKick(nextHeartbeat, 0.16 * state.threat);
        scheduleKick(nextHeartbeat + 0.13, 0.09 * state.threat);
        nextHeartbeat += interval;
      }
    } else {
      nextHeartbeat = now + 0.8;
    }
    const targetTension = state.mode === "running" ? state.threat : 0;
    tensionGain.gain.setTargetAtTime(targetTension * 0.026, now, 0.4);
    droneFilter.frequency.setTargetAtTime(170 + state.threat * 120, now, 0.6);
  }

  function setMode(mode) {
    state.mode = mode;
    if (!ctx) {
      return;
    }
    const now = ctx.currentTime;
    if (mode === "paused") {
      musicBus.gain.setTargetAtTime(0.0001, now, 0.15);
      ambienceBus.gain.setTargetAtTime(0.25, now, 0.2);
      slideStop();
    } else if (mode === "menu") {
      musicBus.gain.setTargetAtTime(settings.music ? settings.musicVolume * 0.65 : 0.0001, now, 0.3);
      ambienceBus.gain.setTargetAtTime(settings.sound ? 0.5 : 0.0001, now, 0.3);
    } else if (mode === "caught") {
      musicBus.gain.setTargetAtTime(settings.music ? settings.musicVolume * 0.4 : 0.0001, now, 0.3);
      ambienceBus.gain.setTargetAtTime(settings.sound ? 0.4 : 0.0001, now, 0.3);
      slideStop();
    } else {
      applySettings();
    }
    if (mode !== "paused") {
      nextStepTime = Math.max(nextStepTime, now + 0.1);
    }
  }

  function setThreat(level) {
    state.threat = clamp01(level);
  }

  function setBiome(id) {
    state.biome = id;
    if (!ctx) {
      return;
    }
    const target = BIOME_AMBIENCE[id] ?? BIOME_AMBIENCE.jungle;
    const now = ctx.currentTime;
    windFilter.frequency.setTargetAtTime(target.wind, now, 1.2);
    windGain.gain.setTargetAtTime(target.windGain, now, 1.2);
    leavesFilter.frequency.setTargetAtTime(target.air, now, 1.2);
    leavesGain.gain.setTargetAtTime(target.airGain, now, 1.2);
    rumbleGain.gain.setTargetAtTime(target.rumble, now, 1.2);
  }

  function suspend() {
    state.suspended = true;
    slideStop();
    if (ctx && ctx.state === "running") {
      ctx.suspend().catch(() => {});
    }
  }

  function resume() {
    state.suspended = false;
    if (ctx && ctx.state === "suspended") {
      ctx.resume().catch(() => {});
      nextStepTime = ctx.currentTime + 0.15;
    }
  }

  function dispose() {
    slideStop();
    if (!ctx) {
      return;
    }
    try {
      windSource?.stop();
      leavesSource?.stop();
      ctx.close();
    } catch (error) {
      console.warn("Dino Escape: audio dispose failed", error);
    }
    ctx = null;
  }

  return {
    unlock,
    tick,
    setMode,
    setThreat,
    setBiome,
    setSettings,
    suspend,
    resume,
    dispose,
    footstep,
    jump,
    land,
    slideStart,
    slideStop,
    amber,
    baitPickup,
    shieldPickup,
    shieldBreak,
    hit,
    geyser,
    roar,
    chomp,
    baitThrow,
    milestone,
    biomeShift,
    gameOver,
    uiClick,
    uiBack,
    /** Diagnostics for tests and the `?debug` panel. */
    debugSnapshot() {
      return {
        unlocked: Boolean(ctx),
        contextState: ctx ? ctx.state : "none",
        mode: state.mode,
        biome: state.biome,
        threat: state.threat,
        step,
        bar,
        nextStepTime: Number(nextStepTime.toFixed(3)),
        time: ctx ? Number(ctx.currentTime.toFixed(3)) : 0,
        musicGain: musicBus ? Number(musicBus.gain.value.toFixed(3)) : 0,
        ambienceGain: ambienceBus ? Number(ambienceBus.gain.value.toFixed(3)) : 0,
      };
    },
    /** Taps the master bus so a test can measure that real signal is playing. */
    tapAnalyser(fftSize = 2048) {
      if (!ctx || !master) {
        return null;
      }
      const analyser = ctx.createAnalyser();
      analyser.fftSize = fftSize;
      analyser.smoothingTimeConstant = 0;
      master.connect(analyser);
      return analyser;
    },
    get isUnlocked() {
      return Boolean(ctx);
    },
  };
}
