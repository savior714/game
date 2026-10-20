/*!
 * AIDEN POWER ISLAND 3D — 프로시저럴 사운드 & 손맛 폴리 엔진
 * 외부 오디오 파일 없이 Web Audio API만으로 기계음·스파크·천둥·점등 화음을 합성한다.
 */

const SCALE_HZ = [261.63, 329.63, 392.0, 523.25, 659.25, 783.99, 1046.5];

export function createSoundEngine(initialEnabled = true) {
  let ctx = null;
  let noiseBuffer = null;
  let enabled = Boolean(initialEnabled);
  let lastRubAt = 0;
  let lastTickAt = 0;

  function ensure() {
    if (!enabled || typeof window === "undefined") return null;
    if (!ctx) {
      const Ctor = window.AudioContext || window.webkitAudioContext;
      if (!Ctor) return null;
      try {
        ctx = new Ctor();
      } catch {
        return null;
      }
    }
    if (ctx.state === "suspended" && typeof ctx.resume === "function") {
      ctx.resume().catch(() => {});
    }
    if (!noiseBuffer && ctx.createBuffer) {
      const length = Math.floor(ctx.sampleRate * 0.6);
      noiseBuffer = ctx.createBuffer(1, length, ctx.sampleRate);
      const channel = noiseBuffer.getChannelData(0);
      for (let i = 0; i < length; i += 1) {
        channel[i] = Math.random() * 2 - 1;
      }
    }
    return ctx;
  }

  function tone({
    freq = 440,
    toFreq = 0,
    dur = 0.14,
    type = "sine",
    gain = 0.08,
    delay = 0,
  }) {
    const ac = ensure();
    if (!ac) return;
    const start = ac.currentTime + delay;
    const osc = ac.createOscillator();
    const amp = ac.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(Math.max(24, freq), start);
    if (toFreq > 0) {
      osc.frequency.exponentialRampToValueAtTime(
        Math.max(24, toFreq),
        start + dur
      );
    }
    amp.gain.setValueAtTime(0.0001, start);
    amp.gain.linearRampToValueAtTime(gain, start + Math.min(0.014, dur * 0.35));
    amp.gain.exponentialRampToValueAtTime(0.0001, start + dur);
    osc.connect(amp);
    amp.connect(ac.destination);
    osc.start(start);
    osc.stop(start + dur + 0.03);
  }

  function noiseBurst({
    dur = 0.16,
    filterFreq = 1600,
    q = 2.2,
    gain = 0.08,
    delay = 0,
  }) {
    const ac = ensure();
    if (!ac || !noiseBuffer) return;
    const start = ac.currentTime + delay;
    const src = ac.createBufferSource();
    src.buffer = noiseBuffer;
    const filter = ac.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.setValueAtTime(filterFreq, start);
    filter.Q.setValueAtTime(q, start);
    const amp = ac.createGain();
    amp.gain.setValueAtTime(0.0001, start);
    amp.gain.linearRampToValueAtTime(gain, start + 0.008);
    amp.gain.exponentialRampToValueAtTime(0.0001, start + dur);
    src.connect(filter);
    filter.connect(amp);
    amp.connect(ac.destination);
    src.start(start);
    src.stop(start + dur + 0.02);
  }

  return {
    get enabled() {
      return enabled;
    },
    setEnabled(value) {
      enabled = Boolean(value);
      if (enabled) ensure();
    },
    unlock() {
      ensure();
    },
    tick() {
      tone({
        freq: 520 + Math.random() * 180,
        dur: 0.06,
        type: "triangle",
        gain: 0.045,
      });
    },
    pop() {
      tone({
        freq: 340,
        toFreq: 760,
        dur: 0.11,
        type: "triangle",
        gain: 0.06,
      });
    },
    crankTick(rpm) {
      const now = typeof performance !== "undefined" ? performance.now() : 0;
      if (now - lastTickAt < 38) return;
      lastTickAt = now;
      const ratio = Math.min(1, Math.abs(rpm || 0) / 240);
      tone({
        freq: 190 + ratio * 620,
        toFreq: 240 + ratio * 740,
        dur: 0.048,
        type: "triangle",
        gain: 0.03 + ratio * 0.035,
      });
    },
    switchThrow(closed) {
      if (closed) {
        tone({ freq: 115, toFreq: 72, dur: 0.09, type: "triangle", gain: 0.1 });
        noiseBurst({ dur: 0.09, filterFreq: 2400, q: 3.5, gain: 0.07 });
        tone({ freq: 330, dur: 0.14, type: "sine", gain: 0.06, delay: 0.04 });
        tone({ freq: 495, dur: 0.18, type: "sine", gain: 0.06, delay: 0.09 });
        tone({ freq: 660, dur: 0.24, type: "sine", gain: 0.065, delay: 0.14 });
      } else {
        noiseBurst({ dur: 0.11, filterFreq: 1900, q: 2.8, gain: 0.065 });
        tone({
          freq: 430,
          toFreq: 68,
          dur: 0.34,
          type: "sawtooth",
          gain: 0.065,
        });
      }
    },
    rubSqueak(speed = 0.6) {
      const now = typeof performance !== "undefined" ? performance.now() : 0;
      if (now - lastRubAt < 75) return;
      lastRubAt = now;
      noiseBurst({
        dur: 0.07,
        filterFreq: 950 + speed * 900,
        q: 4.2,
        gain: 0.035 + speed * 0.03,
      });
    },
    staticSnap() {
      noiseBurst({ dur: 0.055, filterFreq: 3200, q: 4.5, gain: 0.06 });
      tone({ freq: 880, toFreq: 1420, dur: 0.08, type: "sine", gain: 0.05 });
    },
    discharge() {
      noiseBurst({ dur: 0.14, filterFreq: 2200, q: 2.4, gain: 0.07 });
      tone({ freq: 520, toFreq: 130, dur: 0.24, type: "sawtooth", gain: 0.055 });
    },
    thunderBolt() {
      noiseBurst({ dur: 0.26, filterFreq: 2100, q: 1.6, gain: 0.11 });
      noiseBurst({ dur: 0.42, filterFreq: 420, q: 0.9, gain: 0.1, delay: 0.05 });
      tone({ freq: 112, toFreq: 38, dur: 0.48, type: "sawtooth", gain: 0.085 });
      tone({
        freq: 1180,
        toFreq: 520,
        dur: 0.19,
        type: "square",
        gain: 0.04,
        delay: 0.02,
      });
    },
    fireworkBurst() {
      noiseBurst({ dur: 0.18, filterFreq: 1500, q: 1.5, gain: 0.055 });
      tone({ freq: 784, dur: 0.16, type: "sine", gain: 0.045, delay: 0.03 });
      tone({ freq: 1046, dur: 0.2, type: "sine", gain: 0.04, delay: 0.1 });
    },
    landmarkLit(index = 0) {
      const base = SCALE_HZ[Math.min(SCALE_HZ.length - 1, Math.max(0, index))];
      tone({ freq: base, dur: 0.18, type: "triangle", gain: 0.065 });
      tone({
        freq: base * 1.5,
        dur: 0.24,
        type: "sine",
        gain: 0.055,
        delay: 0.08,
      });
    },
    chime() {
      tone({ freq: 523.25, dur: 0.15, type: "sine", gain: 0.075 });
      tone({ freq: 659.25, dur: 0.16, type: "sine", gain: 0.075, delay: 0.08 });
      tone({ freq: 783.99, dur: 0.2, type: "sine", gain: 0.08, delay: 0.16 });
      tone({ freq: 1046.5, dur: 0.3, type: "sine", gain: 0.085, delay: 0.25 });
    },
    gust() {
      noiseBurst({ dur: 0.34, filterFreq: 540, q: 1.4, gain: 0.065 });
    },
    splash() {
      noiseBurst({ dur: 0.24, filterFreq: 1100, q: 1.2, gain: 0.06 });
    },
  };
}
