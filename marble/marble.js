/* ═══════════════════════════════════
   마블 머지 — 독립 보상 게임
   각 과목 게임에서 iframe 오버레이로 호출
═══════════════════════════════════ */

/* ── 사운드 (Web Audio API) ─────── */
let _audCtx = null;
function _getACtx() {
  if (!_audCtx) _audCtx = new (window.AudioContext || window.webkitAudioContext)();
  return _audCtx;
}
function _tone(type, freqs, times, vol, dur) {
  try {
    const ctx = _getACtx(), osc = ctx.createOscillator(), gain = ctx.createGain();
    osc.connect(gain); gain.connect(ctx.destination);
    osc.type = type; const t = ctx.currentTime;
    freqs.forEach((f, i) => osc.frequency.setValueAtTime(f, t + (times[i] || 0)));
    gain.gain.setValueAtTime(vol, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + dur);
    osc.start(t); osc.stop(t + dur + 0.05);
  } catch(e) {}
}
function playDrop()       { _tone('sine', [660, 440], [0, 0.04], 0.1, 0.12); }
function playMerge(level) {
  const n = [262, 294, 330, 370, 415, 466, 523];
  const f = n[Math.min(level - 1, 6)];
  _tone('sine', [f, f * 1.5], [0, 0.05], 0.22, 0.45);
}

/* ── 구슬 등급 ──────────────────── */
const MB = [
  { r: 18, color: '#FFB3BA' },
  { r: 26, color: '#FFCE9A' },
  { r: 35, color: '#FFF89A' },
  { r: 46, color: '#BAFFC9' },
  { r: 58, color: '#BAE1FF' },
  { r: 71, color: '#D4BAFF' },
  { r: 85, color: '#FFB3B3' },
];
const MB_PTS = [10, 30, 60, 100, 150, 250, 600];

/* ── 물리 파라미터 ──────────────── */
const MB_G = 0.35, MB_D = 0.985, MB_R = 0.22, MB_W = 6;
const CW = 320, CH = 480, DLINE = 65, OVR_MS = 3000;

/* ── 상태 ───────────────────────── */
let _mbs = [], _mbScore = 0, _mbNext = 1;
let _mbCool = false, _mbOver = false, _mbDts = null, _mbRaf = null;
let _mbCvs = null, _mbCtx = null;

/* ── 닫기 (iframe postMessage or history) ── */
function mbClose() {
  if (_mbRaf) { cancelAnimationFrame(_mbRaf); _mbRaf = null; }
  if (window.parent !== window) window.parent.postMessage('closeMarble', '*');
  else history.back();
}

/* ── 초기화 ─────────────────────── */
function _mbInit() {
  _mbCvs  = document.getElementById('marble-canvas');
  _mbCtx  = _mbCvs.getContext('2d');
  _mbs    = []; _mbScore = 0; _mbOver = false; _mbDts = null; _mbCool = false;
  _mbNext = _mbPick();
  if (_mbRaf) cancelAnimationFrame(_mbRaf);
  document.getElementById('marble-over').style.display = 'none';
  _mbUpdateUI();
  _mbRaf = requestAnimationFrame(_mbTick);
}
function _mbPick() { const r = Math.random(); return r < 0.55 ? 1 : r < 0.85 ? 2 : 3; }

/* ── 입력 ───────────────────────── */
function onMbInput(e) {
  if (_mbOver || _mbCool) return;
  e.preventDefault();
  const rect = _mbCvs.getBoundingClientRect();
  const cx   = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
  let x = cx * (CW / rect.width);
  const t = MB[_mbNext - 1];
  x = Math.max(t.r + MB_W, Math.min(CW - t.r - MB_W, x));
  _mbs.push({ x, y: t.r + 4, vx: 0, vy: 1, r: t.r, lv: _mbNext, color: t.color, gone: false });
  playDrop();
  _mbNext = _mbPick(); _mbCool = true;
  setTimeout(() => { _mbCool = false; }, 380);
  _mbUpdateUI();
}

/* ── 물리 스텝 ──────────────────── */
function _mbStep() {
  for (const m of _mbs) {
    if (m.gone) continue;
    m.vy += MB_G; m.vx *= MB_D; m.vy *= MB_D; m.x += m.vx; m.y += m.vy;
    if (m.x - m.r < MB_W)      { m.x = m.r + MB_W;      m.vx =  Math.abs(m.vx) * MB_R; }
    if (m.x + m.r > CW - MB_W) { m.x = CW - MB_W - m.r; m.vx = -Math.abs(m.vx) * MB_R; }
    if (m.y + m.r > CH - MB_W) { m.y = CH - MB_W - m.r; m.vy = -Math.abs(m.vy) * MB_R; }
  }
  const merges = [];
  for (let i = 0; i < _mbs.length; i++) {
    for (let j = i + 1; j < _mbs.length; j++) {
      const a = _mbs[i], b = _mbs[j];
      if (a.gone || b.gone) continue;
      const dx = b.x - a.x, dy = b.y - a.y, d = Math.sqrt(dx*dx + dy*dy), mn = a.r + b.r;
      if (d < mn && d > 0.01) {
        const nx = dx/d, ny = dy/d, ov = (mn - d) * 0.5;
        a.x -= nx*ov; a.y -= ny*ov; b.x += nx*ov; b.y += ny*ov;
        const rv = (a.vx - b.vx)*nx + (a.vy - b.vy)*ny;
        if (rv > 0) {
          const imp = rv * (1 + MB_R) * 0.5;
          a.vx -= imp*nx; a.vy -= imp*ny; b.vx += imp*nx; b.vy += imp*ny;
        }
        if (a.lv === b.lv) merges.push([i, j]);
      }
    }
  }
  const seen = new Set();
  for (const [i, j] of merges) {
    if (seen.has(i) || seen.has(j)) continue;
    seen.add(i); seen.add(j);
    const a = _mbs[i], b = _mbs[j], nl = a.lv + 1;
    if (nl > MB.length) {
      _mbScore += MB_PTS[MB.length - 1] * 2; playMerge(7);
    } else {
      const nt = MB[nl - 1];
      _mbs.push({ x: (a.x+b.x)/2, y: (a.y+b.y)/2,
                  vx: (a.vx+b.vx)/2, vy: (a.vy+b.vy)/2 - 2,
                  r: nt.r, lv: nl, color: nt.color, gone: false });
      _mbScore += MB_PTS[nl - 1]; playMerge(nl);
    }
    _mbSpark(a.x, a.y); a.gone = true; b.gone = true; _mbUpdateUI();
  }
  _mbs = _mbs.filter(m => !m.gone);
}

/* ── 게임오버 감지 ──────────────── */
function _mbOverCheck() {
  const danger = _mbs.some(m => m.y - m.r < DLINE && Math.abs(m.vy) < 0.8 && Math.abs(m.vx) < 0.8);
  if (danger) {
    if (!_mbDts) _mbDts = Date.now();
    else if (Date.now() - _mbDts > OVR_MS) {
      _mbOver = true; cancelAnimationFrame(_mbRaf); _mbRaf = null;
      document.getElementById('mb-final').textContent = _mbScore;
      document.getElementById('marble-over').style.display = 'flex';
    }
  } else _mbDts = null;
}

/* ── 렌더링 ─────────────────────── */
function _mbRender() {
  const c = _mbCtx;
  c.clearRect(0, 0, CW, CH);
  c.fillStyle = '#1a1a2e'; c.fillRect(0, 0, CW, CH);
  c.save(); c.strokeStyle = 'rgba(255,80,80,0.5)';
  c.setLineDash([5, 4]); c.lineWidth = 1.5;
  c.beginPath(); c.moveTo(0, DLINE); c.lineTo(CW, DLINE); c.stroke();
  c.setLineDash([]); c.restore();
  for (const m of _mbs) {
    c.save(); c.shadowColor = m.color; c.shadowBlur = 8;
    const g = c.createRadialGradient(m.x - m.r*.3, m.y - m.r*.35, m.r*.08, m.x, m.y, m.r);
    g.addColorStop(0, '#fff'); g.addColorStop(0.35, m.color); g.addColorStop(1, _mbShade(m.color, -50));
    c.fillStyle = g; c.beginPath(); c.arc(m.x, m.y, m.r, 0, Math.PI*2); c.fill();
    c.shadowBlur = 0; c.fillStyle = 'rgba(0,0,0,0.6)';
    c.font = `bold ${Math.max(10, Math.round(m.r * .58))}px sans-serif`;
    c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(m.lv, m.x, m.y);
    c.restore();
  }
  if (!_mbOver) {
    const t = MB[_mbNext - 1]; c.save(); c.globalAlpha = 0.45;
    const g2 = c.createRadialGradient(CW/2 - t.r*.2, 28 - t.r*.2, t.r*.05, CW/2, 28, t.r*.6);
    g2.addColorStop(0, '#fff'); g2.addColorStop(1, t.color);
    c.fillStyle = g2; c.beginPath(); c.arc(CW/2, 28, t.r*.6, 0, Math.PI*2); c.fill();
    c.restore();
  }
}

/* ── 유틸 ───────────────────────── */
function _mbShade(hex, amt) {
  const n = parseInt(hex.replace('#', ''), 16);
  const r = Math.max(0, Math.min(255, (n >> 16) + amt));
  const g = Math.max(0, Math.min(255, ((n >> 8) & 0xff) + amt));
  const b = Math.max(0, Math.min(255, (n & 0xff) + amt));
  return `rgb(${r},${g},${b})`;
}
function _mbSpark(cx, cy) {
  const rect = _mbCvs.getBoundingClientRect();
  const sx = rect.left + cx * (rect.width / CW);
  const sy = rect.top  + cy * (rect.height / CH);
  const el = document.createElement('div');
  el.textContent = '✨';
  el.style.cssText = `position:fixed;left:${sx}px;top:${sy}px;transform:translate(-50%,-50%);` +
    `font-size:1.5rem;pointer-events:none;z-index:2000;animation:mb-spark 0.6s ease-out forwards;`;
  document.body.appendChild(el); setTimeout(() => el.remove(), 700);
}

/* ── UI / 게임 루프 ─────────────── */
function _mbUpdateUI() {
  const el = document.getElementById('mb-score-val');
  if (el) el.textContent = _mbScore;
}
function _mbTick() {
  _mbStep(); _mbOverCheck(); _mbRender();
  if (!_mbOver) _mbRaf = requestAnimationFrame(_mbTick);
}

_mbInit();
