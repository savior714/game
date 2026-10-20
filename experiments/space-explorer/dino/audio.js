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

const BIOME_AMBIENCE = {
  jungle: { wind: 520, windGain: 0.05, leaves: 0.016, rumble: 0 },
  desert: { wind: 360, windGain: 0.042, leaves: 0.008, rumble: 0 },
  volcano: { wind: 210, windGain: 0.055, leaves: 0.004, rumble: 0.035 },
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
      ambienceBus.gain.value = settings.music ? 0.7 : 0;
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
    windSource = ctx.createBufferSource();
    windSource.buffer = noiseBuffer;
    windSource.loop = true;
    windFilter = ctx.createBiquadFilter();
    windFilter.type = "bandpass";
    windFilter.frequency.value = BIOME_AMBIENCE.jungle.wind;
    windFilter.Q.value = 0.55;
    windGain = ctx.createGain();
    windGain.gain.value = BIOME_AMBIENCE.jungle.windGain;
    windSource.connect(windFilter);
    windFilter.connect(windGain);
    windGain.connect(ambienceBus);
    windSource.start();

    leavesSource = ctx.createBufferSource();
    leavesSource.buffer = noiseBuffer;
    leavesSource.loop = true;
    leavesFilter = ctx.createBiquadFilter();
    leavesFilter.type = "highpass";
    leavesFilter.frequency.value = 2400;
    leavesGain = ctx.createGain();
    leavesGain.gain.value = BIOME_AMBIENCE.jungle.leaves;
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
    droneGain.gain.value = 0.028;
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
    ambienceBus.gain.setTargetAtTime(
      settings.music ? (musicPaused ? 0.25 : 0.7) : 0.0001,
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

  function scheduleKick(time, gain = 0.16) {
    const osc = ctx.createOscillator();
    osc.type = "sine";
    osc.frequency.setValueAtTime(112, time);
    osc.frequency.exponentialRampToValueAtTime(42, time + 0.2);
    const amp = ctx.createGain();
    envelope(amp, time, gain, 0.004, 0.26);
    osc.connect(amp);
    amp.connect(musicBus);
    const send = ctx.createGain();
    send.gain.value = 0.06;
    amp.connect(send);
    send.connect(reverbSend);
    osc.start(time);
    osc.stop(time + 0.34);
    osc.onended = () => {
      osc.disconnect();
      amp.disconnect();
      send.disconnect();
    };
  }

  function scheduleTom(time, gain = 0.07, frequency = 190) {
    const source = ctx.createBufferSource();
    source.buffer = noiseBuffer;
    const filter = ctx.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.value = frequency;
    filter.Q.value = 1.8;
    const amp = ctx.createGain();
    envelope(amp, time, gain, 0.005, 0.2);
    source.connect(filter);
    filter.connect(amp);
    amp.connect(musicBus);
    const send = ctx.createGain();
    send.gain.value = 0.12;
    amp.connect(send);
    send.connect(reverbSend);
    source.start(time);
    source.stop(time + 0.28);
    source.onended = () => {
      source.disconnect();
      filter.disconnect();
      amp.disconnect();
      send.disconnect();
    };
  }

  function scheduleShaker(time, gain = 0.018) {
    const source = ctx.createBufferSource();
    source.buffer = noiseBuffer;
    source.playbackRate.value = 1.7;
    const filter = ctx.createBiquadFilter();
    filter.type = "highpass";
    filter.frequency.value = 5200;
    const amp = ctx.createGain();
    envelope(amp, time, gain, 0.002, 0.07);
    source.connect(filter);
    filter.connect(amp);
    amp.connect(musicBus);
    source.start(time);
    source.stop(time + 0.1);
    source.onended = () => {
      source.disconnect();
      filter.disconnect();
      amp.disconnect();
    };
  }

  function scheduleBass(time, midi) {
    const osc = ctx.createOscillator();
    osc.type = "triangle";
    osc.frequency.value = midiToFreq(midi);
    const filter = ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 320;
    const amp = ctx.createGain();
    envelope(amp, time, 0.055, 0.02, 0.6);
    osc.connect(filter);
    filter.connect(amp);
    amp.connect(musicBus);
    osc.start(time);
    osc.stop(time + 0.8);
    osc.onended = () => {
      osc.disconnect();
      filter.disconnect();
      amp.disconnect();
    };
  }

  function schedulePad(time, notes) {
    for (const midi of notes) {
      const osc = ctx.createOscillator();
      osc.type = "sine";
      osc.frequency.value = midiToFreq(midi);
      osc.detune.value = Math.random() * 8 - 4;
      const filter = ctx.createBiquadFilter();
      filter.type = "lowpass";
      filter.frequency.value = 1100;
      const amp = ctx.createGain();
      amp.gain.setValueAtTime(0.0001, time);
      amp.gain.exponentialRampToValueAtTime(0.02, time + 1.1);
      amp.gain.setValueAtTime(0.02, time + 3.2);
      amp.gain.exponentialRampToValueAtTime(0.0001, time + 4.6);
      osc.connect(filter);
      filter.connect(amp);
      amp.connect(musicBus);
      const send = ctx.createGain();
      send.gain.value = 0.4;
      amp.connect(send);
      send.connect(reverbSend);
      osc.start(time);
      osc.stop(time + 4.8);
      osc.onended = () => {
        osc.disconnect();
        filter.disconnect();
        amp.disconnect();
        send.disconnect();
      };
    }
  }

  function scheduleStep(stepIndex, time, barIndex) {
    if (state.mode === "menu") {
      if (stepIndex === 0 && barIndex % 2 === 0) {
        schedulePad(time, barIndex % 4 === 0 ? [50, 53, 57] : [46, 50, 53]);
        scheduleBass(time, barIndex % 4 === 0 ? 38 : 34);
      }
      return;
    }
    if (state.mode === "caught" || state.mode === "paused" || state.mode === "intro") {
      return;
    }
    const threat = clamp01(state.threat);
    const intensity = state.mode === "running" ? 1 : 0.4;
    const kickSteps = [0, 6, 10, 14];
    const tomSteps = [3, 8, 12];
    if (kickSteps.includes(stepIndex)) {
      scheduleKick(time, stepIndex === 0 ? 0.15 * intensity : 0.09 * intensity);
    }
    if (tomSteps.includes(stepIndex) || (threat > 0.55 && stepIndex % 4 === 3)) {
      scheduleTom(time, 0.045 * intensity, 150 + (stepIndex % 5) * 40);
    }
    if (stepIndex % 2 === 0 || threat > 0.65) {
      scheduleShaker(time, (stepIndex % 4 === 0 ? 0.016 : 0.009) * (0.6 + threat));
    }
    if (stepIndex === 0) {
      const bassPattern = [38, 38, 36, 41, 38, 38, 43, 36];
      scheduleBass(time, bassPattern[barIndex % bassPattern.length]);
      if (barIndex % 4 === 0) {
        schedulePad(time, barIndex % 8 === 0 ? [50, 53, 57] : [48, 51, 55]);
      }
    }
  }

  function tick() {
    if (!ctx || failed || !settings.music || state.suspended) {
      nextStepTime = 0;
      return;
    }
    const now = ctx.currentTime;
    if (nextStepTime === 0) {
      nextStepTime = now + 0.1;
    }
    let guard = 0;
    while (nextStepTime < now + 0.2 && guard < 24) {
      scheduleStep(step, nextStepTime, bar);
      nextStepTime += 60 / 104 / 4;
      step = (step + 1) % 16;
      if (step === 0) {
        bar = (bar + 1) % 64;
      }
      guard += 1;
    }
    if (state.mode === "running" && state.threat > 0.5) {
      const interval = lerp(1.25, 0.62, state.threat);
      while (nextHeartbeat < now + 0.2) {
        scheduleKick(nextHeartbeat, 0.055 * state.threat);
        scheduleKick(nextHeartbeat + 0.13, 0.032 * state.threat);
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
      ambienceBus.gain.setTargetAtTime(settings.music ? 0.55 : 0.0001, now, 0.3);
    } else if (mode === "caught") {
      musicBus.gain.setTargetAtTime(settings.music ? settings.musicVolume * 0.4 : 0.0001, now, 0.3);
      ambienceBus.gain.setTargetAtTime(settings.music ? 0.4 : 0.0001, now, 0.3);
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
    leavesGain.gain.setTargetAtTime(target.leaves, now, 1.2);
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
    get isUnlocked() {
      return Boolean(ctx);
    },
  };
}
