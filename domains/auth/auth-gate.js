/**
 * AidenGame 로그인 gate.
 *
 * session이 확인되기 전에는 child-facing 기능 surface를 fail-closed로 가린다.
 * - Supabase/Auth 모듈을 아직 읽지 못했으면 pending 상태를 유지한다.
 * - 확인된 session이 없으면 로그인 카드만 노출하고 배경 surface는 조작할 수 없다.
 * - session이 확인된 경우에만 gate를 제거한다.
 *
 * 각 기능 페이지는 <body> 시작 직후 이 script를 한 번만 불러온다.
 */
(function initAuthGate(global) {
  'use strict';

  if (global.AidenAuthGate) return;

  const doc = global.document;
  if (!doc) return;

  const GATE_ID = 'aiden-auth-gate';
  const STYLE_ID = 'aiden-auth-gate-style';
  const SUPABASE_SCRIPT_ID = 'supabase-js';
  const AUTH_SCRIPT_ID = 'aiden-canonical-auth';
  const SUPABASE_URL = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2';
  const AUTH_READY_TIMEOUT_MS = 10000;
  const PENDING_CLASS = 'aiden-auth-pending';
  const LOCKED_CLASS = 'aiden-auth-locked';

  const currentScript = doc.currentScript;
  const authScriptSrc = currentScript && currentScript.src
    ? new URL('auth.js', currentScript.src).href
    : null;

  let state = 'pending';
  let gate = null;
  let refs = null;
  let authStarted = false;

  const COPY = {
    pending: {
      icon: '🔐',
      title: '로그인 확인 중…',
      desc: '잠시만 기다려 주세요.',
      button: null,
      hint: ''
    },
    locked: {
      icon: '🔐',
      title: '로그인이 필요해요',
      desc: '구글 계정으로 로그인하면 학습 기록과 보상이 내 계정에 저장돼요.',
      button: '구글로 로그인',
      hint: '처음이라면 보호자와 함께 로그인해 주세요.'
    },
    signing: {
      icon: '🔐',
      title: '로그인이 필요해요',
      desc: '구글 로그인 화면으로 이동하고 있어요.',
      button: '이동 중…',
      hint: ''
    },
    error: {
      icon: '⚠️',
      title: '로그인을 확인할 수 없어요',
      desc: '인터넷 연결을 확인한 뒤 다시 시도해 주세요.',
      button: '다시 시도',
      hint: ''
    },
    unlocked: {
      icon: '',
      title: '',
      desc: '',
      button: null,
      hint: ''
    }
  };

  const STYLE = `
    html.aiden-auth-pending,
    html.aiden-auth-locked {
      overflow: hidden !important;
    }
    html.aiden-auth-pending body,
    html.aiden-auth-locked body {
      overflow: hidden !important;
    }
    html.aiden-auth-pending body > *:not(#aiden-auth-gate),
    html.aiden-auth-locked body > *:not(#aiden-auth-gate) {
      visibility: hidden !important;
    }
    .aiden-auth-gate {
      position: fixed;
      inset: 0;
      z-index: 2147483000;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: max(20px, env(safe-area-inset-top)) 20px max(20px, env(safe-area-inset-bottom));
      background:
        radial-gradient(circle at 20% 15%, rgba(215, 255, 0, 0.14), transparent 42%),
        radial-gradient(circle at 82% 88%, rgba(56, 189, 248, 0.16), transparent 46%),
        #07090e;
      color: #f8fafc;
      font-family: Pretendard, "Pretendard Variable", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      box-sizing: border-box;
    }
    .aiden-auth-gate[hidden] {
      display: none !important;
    }
    .aiden-auth-gate *,
    .aiden-auth-gate *::before,
    .aiden-auth-gate *::after {
      box-sizing: border-box;
    }
    .aiden-auth-gate__card {
      width: min(92vw, 480px);
      padding: clamp(24px, 5vw, 44px);
      border: 1px solid rgba(215, 255, 0, 0.3);
      border-radius: 28px;
      background: linear-gradient(160deg, rgba(15, 23, 42, 0.98), rgba(2, 6, 23, 0.98));
      box-shadow: 0 24px 80px rgba(0, 0, 0, 0.55), 0 0 0 1px rgba(255, 255, 255, 0.04) inset;
      text-align: center;
      outline: none;
    }
    .aiden-auth-gate__card:focus-visible {
      box-shadow: 0 0 0 3px #d7ff00, 0 24px 80px rgba(0, 0, 0, 0.55);
    }
    .aiden-auth-gate__icon {
      width: 72px;
      height: 72px;
      margin: 0 auto 18px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 24px;
      background: rgba(215, 255, 0, 0.12);
      border: 1px solid rgba(215, 255, 0, 0.28);
      font-size: 34px;
      line-height: 1;
    }
    html.aiden-auth-pending .aiden-auth-gate__icon,
    html.aiden-auth-locked .aiden-auth-gate__icon {
      animation: aiden-auth-gate-pulse 1.8s ease-in-out infinite;
    }
    .aiden-auth-gate__title {
      margin: 0 0 10px;
      font-size: clamp(22px, 4vw, 28px);
      font-weight: 900;
      letter-spacing: -0.02em;
      color: #f8fafc;
    }
    .aiden-auth-gate__desc {
      margin: 0 auto 22px;
      max-width: 34em;
      font-size: clamp(14px, 2.6vw, 16px);
      font-weight: 600;
      line-height: 1.6;
      color: #cbd5e1;
      word-break: keep-all;
    }
    .aiden-auth-gate__button {
      width: 100%;
      min-height: 58px;
      padding: 0 20px;
      border: 0;
      border-radius: 16px;
      background: #d7ff00;
      color: #0b0f14;
      font-family: inherit;
      font-size: 17px;
      font-weight: 900;
      letter-spacing: -0.01em;
      cursor: pointer;
      transition: transform 0.15s ease, background-color 0.15s ease;
    }
    .aiden-auth-gate__button:hover {
      background: #c7ee00;
      transform: translateY(-1px);
    }
    .aiden-auth-gate__button:active {
      transform: translateY(0);
    }
    .aiden-auth-gate__button:focus-visible {
      outline: 3px solid #ffffff;
      outline-offset: 3px;
    }
    .aiden-auth-gate__button:disabled {
      cursor: wait;
      opacity: 0.72;
      transform: none;
    }
    .aiden-auth-gate__hint {
      min-height: 1.4em;
      margin: 14px 0 0;
      font-size: 12px;
      font-weight: 600;
      line-height: 1.5;
      color: #94a3b8;
      word-break: keep-all;
    }
    @keyframes aiden-auth-gate-pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.55; }
    }
    @media (prefers-reduced-motion: reduce) {
      html.aiden-auth-pending .aiden-auth-gate__icon,
      html.aiden-auth-locked .aiden-auth-gate__icon {
        animation: none;
      }
      .aiden-auth-gate__button {
        transition: none;
      }
    }
  `;

  function injectStyle() {
    if (doc.getElementById(STYLE_ID)) return;
    const style = doc.createElement('style');
    style.id = STYLE_ID;
    style.textContent = STYLE;
    (doc.head || doc.documentElement).appendChild(style);
  }

  function createElement(tagName, className) {
    const element = doc.createElement(tagName);
    if (className) element.className = className;
    return element;
  }

  function buildGate() {
    const root = createElement('div', 'aiden-auth-gate');
    root.id = GATE_ID;
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-modal', 'true');
    root.setAttribute('aria-labelledby', 'aiden-auth-gate-title');

    const card = createElement('div', 'aiden-auth-gate__card');
    card.tabIndex = -1;

    const icon = createElement('div', 'aiden-auth-gate__icon');
    icon.setAttribute('aria-hidden', 'true');

    const title = createElement('h2', 'aiden-auth-gate__title');
    title.id = 'aiden-auth-gate-title';

    const desc = createElement('p', 'aiden-auth-gate__desc');

    const button = createElement('button', 'aiden-auth-gate__button');
    button.type = 'button';
    button.hidden = true;
    button.disabled = true;
    button.addEventListener('click', onGateAction);

    const hint = createElement('p', 'aiden-auth-gate__hint');
    hint.setAttribute('aria-live', 'polite');

    card.appendChild(icon);
    card.appendChild(title);
    card.appendChild(desc);
    card.appendChild(button);
    card.appendChild(hint);
    root.appendChild(card);

    refs = { root, card, icon, title, desc, button, hint };
    return root;
  }

  function render() {
    if (!refs) return;

    const copy = COPY[state] || COPY.pending;
    refs.icon.textContent = copy.icon;
    refs.title.textContent = copy.title;
    refs.desc.textContent = copy.desc;
    refs.hint.textContent = copy.hint;
    refs.button.textContent = copy.button || '';
    refs.button.hidden = !copy.button;
    refs.button.disabled = state === 'pending' || state === 'signing';
    refs.root.setAttribute('aria-busy', state === 'pending' ? 'true' : 'false');

    if (state === 'unlocked') {
      refs.root.hidden = true;
      refs.root.setAttribute('aria-hidden', 'true');
    } else {
      refs.root.hidden = false;
      refs.root.removeAttribute('aria-hidden');
    }

    const root = doc.documentElement;
    root.classList.toggle(PENDING_CLASS, state === 'pending');
    root.classList.toggle(LOCKED_CLASS, state !== 'unlocked' && state !== 'pending');
    setBackgroundInert(state !== 'unlocked');
  }

  function setState(nextState) {
    const previous = state;
    state = nextState;
    render();
    if (state !== 'unlocked' && previous !== state) focusGate();
  }

  function focusGate() {
    if (!refs) return;
    if (!refs.button.hidden && !refs.button.disabled) {
      refs.button.focus();
    } else {
      refs.card.focus();
    }
  }

  function setBackgroundInert(inert) {
    if (!doc.body) return;
    const children = Array.prototype.slice.call(doc.body.children || []);
    children.forEach((child) => {
      if (child === gate) return;
      const tag = String(child.tagName || '').toUpperCase();
      if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'LINK') return;

      if (inert) {
        child.setAttribute('inert', '');
        child.setAttribute('data-auth-gate-inert', '');
      } else if (typeof child.hasAttribute === 'function' && child.hasAttribute('data-auth-gate-inert')) {
        child.removeAttribute('inert');
        child.removeAttribute('data-auth-gate-inert');
      }
    });
  }

  function emit(name, detail) {
    try {
      global.dispatchEvent(new CustomEvent(name, { detail }));
    } catch (e) {
      /* ignore */
    }
  }

  function unlock(user) {
    if (state === 'unlocked') return;
    setState('unlocked');
    emit('auth-gate-unlocked', { user });
  }

  function lock() {
    if (state === 'locked') return;
    setState('locked');
    emit('auth-gate-locked', {});
  }

  function showError(reason) {
    if (reason) console.warn('[AuthGate] 로그인 상태를 확인할 수 없습니다:', reason);
    if (state === 'error') return;
    setState('error');
    emit('auth-gate-locked', { reason: 'auth-unavailable' });
  }

  function onGateAction() {
    if (state === 'locked') {
      void signIn();
    } else if (state === 'error') {
      global.location.reload();
    }
  }

  async function signIn() {
    const auth = global.Auth;
    if (!auth || typeof auth.signInGoogle !== 'function') {
      showError('sign-in-unavailable');
      return;
    }

    setState('signing');
    const redirectTo = global.location && global.location.origin
      ? global.location.origin
      : undefined;

    let outcome = 'failed';
    try {
      outcome = await Promise.race([
        Promise.resolve(auth.signInGoogle({ redirectTo, silent: true })).then((result) => (
          result === false ? 'failed' : 'ok'
        )),
        new Promise((resolve) => {
          setTimeout(() => resolve('timeout'), 8000);
        })
      ]);
    } catch (e) {
      console.warn('[AuthGate] signInGoogle 실패:', e);
      outcome = 'failed';
    }

    if (outcome === 'failed') {
      showError('sign-in-failed');
    } else if (outcome === 'timeout' && state === 'signing') {
      setState('locked');
    }
  }

  function loadScript(src, id) {
    return new Promise((resolve, reject) => {
      const existing = doc.getElementById(id);
      if (existing) {
        const loaded = id === SUPABASE_SCRIPT_ID
          ? typeof global.supabase !== 'undefined'
          : Boolean(global.Auth);
        if (loaded) {
          resolve();
          return;
        }
        existing.addEventListener('load', () => resolve(), { once: true });
        existing.addEventListener('error', () => reject(new Error(`failed to load ${src}`)), { once: true });
        return;
      }

      const script = doc.createElement('script');
      script.id = id;
      script.src = src;
      script.async = true;
      script.addEventListener('load', () => resolve(), { once: true });
      script.addEventListener('error', () => reject(new Error(`failed to load ${src}`)), { once: true });
      (doc.head || doc.documentElement).appendChild(script);
    });
  }

  function ensureSupabase() {
    if (typeof global.supabase !== 'undefined') return Promise.resolve();
    return loadScript(SUPABASE_URL, SUPABASE_SCRIPT_ID);
  }

  function ensureAuth() {
    if (global.Auth) return Promise.resolve();
    if (!authScriptSrc) return Promise.reject(new Error('auth script url missing'));
    return ensureSupabase()
      .then(() => loadScript(authScriptSrc, AUTH_SCRIPT_ID))
      .then(() => {
        if (!global.Auth) throw new Error('Auth module missing');
      });
  }

  function fallbackReady(auth) {
    if (auth.getUser && auth.getUser()) return Promise.resolve();
    return new Promise((resolve) => {
      let settled = false;
      let timer = null;

      function done() {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        global.removeEventListener('auth-changed', done);
        resolve();
      }

      global.addEventListener('auth-changed', done);
      timer = setTimeout(done, 1500);
    });
  }

  function waitForSession() {
    const auth = global.Auth;
    if (!auth || typeof auth.getUser !== 'function') {
      return Promise.reject(new Error('Auth.getUser missing'));
    }

    const ready = typeof auth.whenReady === 'function'
      ? Promise.resolve(auth.whenReady())
      : fallbackReady(auth);

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error('auth ready timeout'));
      }, AUTH_READY_TIMEOUT_MS);

      ready
        .then(() => {
          clearTimeout(timer);
          resolve(auth.getUser() || null);
        })
        .catch((error) => {
          clearTimeout(timer);
          reject(error);
        });
    });
  }

  function startAuth() {
    if (authStarted) return;
    authStarted = true;

    ensureAuth()
      .then(waitForSession)
      .then((user) => {
        if (user) {
          unlock(user);
        } else if (!global.supabaseClient) {
          showError('supabase client missing');
        } else {
          lock();
        }
      })
      .catch((error) => {
        showError(error && error.message ? error.message : error);
      });
  }

  function mount() {
    if (gate) return;
    injectStyle();
    gate = buildGate();
    doc.body.appendChild(gate);
    render();
    focusGate();
  }

  global.addEventListener('auth-changed', (event) => {
    const detailUser = event && event.detail && Object.prototype.hasOwnProperty.call(event.detail, 'user')
      ? event.detail.user
      : undefined;
    const user = detailUser !== undefined
      ? detailUser
      : (global.Auth && typeof global.Auth.getUser === 'function' ? global.Auth.getUser() : null);

    if (user) {
      unlock(user);
    } else if (state === 'unlocked' || state === 'locked' || state === 'signing') {
      lock();
    }
  });

  doc.addEventListener('keydown', (event) => {
    if (state === 'unlocked' || !refs) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    if (event.key !== 'Tab') return;

    const focusable = [];
    if (!refs.button.hidden && !refs.button.disabled) focusable.push(refs.button);
    focusable.push(refs.card);
    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (focusable.indexOf(doc.activeElement) === -1) {
      event.preventDefault();
      first.focus();
      return;
    }
    if (event.shiftKey && doc.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && doc.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }, true);

  injectStyle();
  doc.documentElement.classList.add(PENDING_CLASS);

  if (doc.body) {
    mount();
  } else {
    doc.addEventListener('DOMContentLoaded', mount, { once: true });
  }

  startAuth();

  global.AidenAuthGate = Object.freeze({
    getState() {
      return state;
    },
    isLocked() {
      return state !== 'unlocked';
    }
  });
})(window);
