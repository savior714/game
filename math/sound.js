/* ═══════════════════════════════════
   Web Audio API 효과음
   — 외부 라이브러리 없는 순수 Web API
═══════════════════════════════════ */
let _audCtx = null;

function _getACtx() {
  if (!_audCtx) _audCtx = new (window.AudioContext || window.webkitAudioContext)();
  return _audCtx;
}

function _tone(type, freqs, times, vol, dur) {
  try {
    const ctx  = _getACtx();
    const osc  = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type = type;
    const t = ctx.currentTime;
    freqs.forEach((f, i) => osc.frequency.setValueAtTime(f, t + (times[i] || 0)));
    gain.gain.setValueAtTime(vol, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + dur);
    osc.start(t);
    osc.stop(t + dur + 0.05);
  } catch(e) {}
}

/* 정답 — 밝은 상행 3음 */
function playCorrect() {
  _tone('sine', [523, 784, 1047], [0, 0.07, 0.14], 0.25, 0.38);
}

/* 오답 — 낮은 하행 버저 */
function playWrong() {
  _tone('sawtooth', [240, 160], [0, 0.12], 0.18, 0.28);
}

/* 시간초과 — 3단 하행음 */
function playTimeout() {
  _tone('square', [300, 200, 150], [0, 0.1, 0.2], 0.15, 0.38);
}

/* 구슬 드롭 — 짧은 탁 소리 */
function playDrop() {
  _tone('sine', [660, 440], [0, 0.04], 0.1, 0.12);
}

/* 구슬 합체 — 레벨별 음높이 */
function playMerge(level) {
  const notes = [262, 294, 330, 370, 415, 466, 523];
  const f = notes[Math.min(level - 1, notes.length - 1)];
  _tone('sine', [f, f * 1.5], [0, 0.05], 0.22, 0.45);
}
