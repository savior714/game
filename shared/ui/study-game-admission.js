/** Shared per-entry learning gate for the short-play reward games. */
(function (global) {
  'use strict';
  const root = new URL('../../', document.currentScript.src);
  const KEY = 'aiden_study_game_admission_v1';
  // Minimum per-admission learning workload (see ACTIVE_PRODUCT_SCOPE.md).
  // Not tied to gem rewards: quiz gems come only from the 20-streak rocket launch.
  const REQUIRED = 5;
  const DURATION = 5 * 60 * 1000;
  const games = {
    electricity: ['experiments/electricity/index.html', '⚡ 발전소'],
    dino: ['experiments/space-explorer/dino-escape.html', '🦖 공룡 게임'],
    marble: ['experiments/marble/index.html', '🎮 마블 게임'],
    bubble: ['experiments/bubble/index.html', '🫧 버블 게임'],
    'ocean-rescue': ['ocean-rescue/index.html', '🌊 바다 구조대']
  };
  const subjects = { math: '🔢 수학', english: '🔤 영어', korean: '📚 국어', science: '🔬 과학' };
  const path = location.pathname;
  const gameAt = (url) => Object.keys(games).find(id => {
    const target = new URL(games[id][0], root).pathname;
    return url.pathname === target || url.pathname === target.replace(/index\.html$/, '');
  });
  const currentGame = gameAt(location);
  const subject = Object.keys(subjects).find(id => {
    const target = new URL(`domains/${id}/index.html`, root).pathname;
    return path === target || path === target.replace(/index\.html$/, '');
  });
  let dialog;
  let banner;
  let timer;

  function read() {
    try {
      const s = JSON.parse(sessionStorage.getItem(KEY));
      if (!s || s.version !== 1 || !Object.hasOwn(games, s.game) || !Object.hasOwn(subjects, s.subject)) return null;
      if (!Number.isInteger(s.correct) || s.correct < 0 || s.correct > REQUIRED) return null;
      if (s.phase === 'learning') return s;
      if (s.phase === 'playing' && s.correct === REQUIRED && Number.isFinite(s.startedAt) &&
          Number.isFinite(s.deadline) && s.deadline - s.startedAt === DURATION && s.startedAt <= Date.now()) return s;
    } catch (_) { /* Unavailable or corrupt storage never grants access. */ }
    return null;
  }
  function save(s) {
    try { sessionStorage.setItem(KEY, JSON.stringify(s)); return true; }
    catch (_) { alert('학습 기록을 저장할 수 없어요. 브라우저 저장 공간을 확인해 주세요.'); return false; }
  }
  function clear() { try { sessionStorage.removeItem(KEY); } catch (_) { /* Stay locked. */ } }
  function home() {
    clear();
    document.documentElement.dataset.studyGameLocked = 'true';
    global.location.replace(new URL('index.html', root).href);
  }
  function element(tag, text) {
    const el = document.createElement(tag);
    if (text) el.textContent = text;
    return el;
  }
  function button(text, action) {
    const el = element('button', text);
    el.type = 'button';
    el.addEventListener('click', action);
    return el;
  }
  function request(game) {
    if (!Object.hasOwn(games, game) || global.AidenAuthGate?.isLocked()) return;
    if (dialog) { dialog.close(); dialog.remove(); }
    dialog = element('dialog');
    dialog.className = 'study-game-choice';
    dialog.setAttribute('aria-labelledby', 'study-game-title');
    const title = element('h2', '어떤 과목을 풀고 싶어?');
    title.id = 'study-game-title';
    dialog.append(title, element('p', `${games[game][1]} 입장 전에 정답 ${REQUIRED}개에 도전해요!`),
      element('p', '보석 1개를 얻을 만큼 공부하면 5분 동안 놀 수 있어요. 보석은 쓰지 않아요.'));
    const choices = element('div');
    choices.className = 'study-game-subjects';
    Object.entries(subjects).forEach(([id, name]) => choices.append(button(name, () => {
      if (!save({ version: 1, phase: 'learning', game, subject: id, correct: 0 })) return;
      global.location.assign(new URL(`domains/${id}/index.html`, root).href);
    })));
    dialog.append(choices, button(currentGame ? '홈으로 돌아가기' : '취소', () => {
      if (currentGame) home(); else dialog.close();
    }));
    if (currentGame) dialog.addEventListener('cancel', event => { event.preventDefault(); home(); });
    document.body.append(dialog);
    dialog.showModal();
  }
  function renderLearning() {
    const s = read();
    if (!subject || !s || s.phase !== 'learning' || s.subject !== subject) return;
    if (!banner) {
      banner = element('aside');
      banner.className = 'study-game-progress';
      banner.setAttribute('aria-live', 'polite');
      document.body.prepend(banner);
    }
    banner.replaceChildren(element('span', `${games[s.game][1]} · 정답 ${s.correct} / ${REQUIRED} · 완료하면 5분 놀이`));
    if (s.correct === REQUIRED) banner.append(button('🎉 게임 입장하기', () => {
      const ready = read();
      if (!ready || ready.phase !== 'learning' || ready.subject !== subject || ready.correct !== REQUIRED) return;
      const startedAt = Date.now();
      if (save({ ...ready, phase: 'playing', startedAt, deadline: startedAt + DURATION })) {
        global.location.assign(new URL(games[ready.game][0], root).href);
      }
    }));
    banner.append(button('그만하기', () => { clear(); banner.remove(); banner = null; }));
  }
  function recordAnswer(answerSubject, correct) {
    const s = read();
    if (global.AidenAuthGate?.isLocked() || !correct || !s || s.phase !== 'learning' || s.subject !== answerSubject || subject !== answerSubject || s.correct >= REQUIRED) return;
    if (save({ ...s, correct: s.correct + 1 })) renderLearning();
  }
  function isPlaying(game) {
    const s = read();
    return !!s && s.phase === 'playing' && s.game === game && s.deadline > Date.now();
  }
  function checkGame() {
    const s = read();
    if (!s || s.phase !== 'playing' || s.game !== currentGame || s.deadline <= Date.now()) {
      if (timer) clearInterval(timer);
      if (s && s.phase === 'playing') { home(); return; }
      document.documentElement.dataset.studyGameLocked = 'true';
      if ((!dialog || !dialog.open) && !global.AidenAuthGate?.isLocked()) request(currentGame);
      return;
    }
    delete document.documentElement.dataset.studyGameLocked;
    if (!banner) {
      banner = element('aside');
      banner.className = 'study-game-clock';
      document.body.append(banner);
    }
    const seconds = Math.ceil((s.deadline - Date.now()) / 1000);
    banner.textContent = `⏱ ${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')} 남음 · 5분 뒤 홈으로 돌아가요`;
  }
  global.StudyGameAdmission = { request, recordAnswer, isPlaying };
  const style = element('style');
  style.textContent = `
    html[data-study-game-locked] body > :not(.study-game-choice):not(#aiden-auth-gate):not(script):not(style) { visibility: hidden !important; }
    .study-game-choice { box-sizing:border-box; width:min(92vw,480px); max-height:90dvh; overflow:auto; border:2px solid #67e8f9; border-radius:24px; padding:28px; background:#102235; color:#fff; font:18px/1.6 system-ui; }
    .study-game-choice::backdrop { background:rgba(3,10,22,.94); }
    .study-game-choice h2 { font-size:25px; margin:0 0 12px; }
    .study-game-subjects { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin:20px 0; }
    .study-game-choice button,.study-game-progress button { min-height:48px; padding:8px 16px; border:1px solid #67e8f9; border-radius:12px; background:#164e63; color:white; font:inherit; cursor:pointer; }
    .study-game-choice button:focus-visible,.study-game-progress button:focus-visible { outline:3px solid #fde047; outline-offset:3px; }
    .study-game-progress { position:relative; z-index:60; display:flex; flex-wrap:wrap; align-items:center; justify-content:center; gap:12px; padding:12px; background:#102235; color:white; font:16px/1.5 system-ui; }
    .study-game-clock { position:fixed; bottom:12px; left:50%; transform:translateX(-50%); z-index:9999; max-width:90vw; padding:8px 16px; border-radius:18px; background:#102235; color:white; font:14px/1.5 system-ui; pointer-events:none; }
  `;
  document.head.append(style);
  if (currentGame) document.documentElement.dataset.studyGameLocked = 'true';
  function init() {
    if (currentGame) {
      checkGame();
      if (isPlaying(currentGame)) timer = setInterval(checkGame, 250);
      global.addEventListener('pageshow', checkGame);
      global.addEventListener('auth-gate-unlocked', checkGame);
      document.addEventListener('visibilitychange', checkGame);
    } else {
      const s = read();
      if (s && s.phase === 'playing') clear(); // Leaving a game ends that entry, even before five minutes.
      renderLearning();
      global.addEventListener('pageshow', () => {
        const restored = read();
        if (restored && restored.phase === 'playing') clear();
        if (banner) { banner.remove(); banner = null; }
        renderLearning();
      });
    }
    document.addEventListener('keydown', event => {
      const item = event.target.closest('#reward-inventory [data-type="marble"], #reward-inventory [data-type="bubble"]');
      if (item && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); item.click(); }
    });
    document.addEventListener('click', event => {
      const link = event.target.closest('a[href]');
      if (!link) return;
      const url = new URL(link.href, location.href);
      const game = url.origin === root.origin && gameAt(url);
      if (game) { event.preventDefault(); request(game); }
    }, true);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})(window);
