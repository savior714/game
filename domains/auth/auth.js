(function initAuthModule(global) {
  'use strict';

  // gate와 호환 loader가 canonical module을 중복 실행하지 않게 한다.
  if (global.Auth) {
    try {
      global.dispatchEvent(new Event('aiden-auth-module-loaded'));
    } catch (e) {
      /* ignore */
    }
    return;
  }

  global.SupabaseConfig = {
    // TODO: 개발 환경에 맞는 Supabase URL 및 anon 키로 대체하세요.
    URL: 'https://rxjefpmvlygunrukccgg.supabase.co',
    KEY: 'sb_publishable_86T5zbV_IUXZDvQig6mofg_tlHYeHVx'
  };

  if (typeof supabase !== 'undefined' && !global.supabaseClient) {
    global.supabaseClient = supabase.createClient(global.SupabaseConfig.URL, global.SupabaseConfig.KEY);
  }

  global.Auth = (() => {
    let currentUser = null;
    let ready = false;
    let initStarted = false;
    let resolveReady = null;

    /** 최초 세션 확인이 끝났음을 gate와 sync가 기다릴 수 있는 단일 신호. */
    const readyPromise = new Promise((resolve) => {
      resolveReady = resolve;
    });

    /** 관리자 대시보드 접근 허용 구글 계정(본인 이메일 1개만 넣으면 됨). 배포 전 반드시 본인 주소로 수정하세요. */
    const ADMIN_EMAILS = ['savior714@gmail.com'].map((e) => e.trim().toLowerCase());

    function normalizeEmail(email) {
      return String(email || '')
        .trim()
        .toLowerCase();
    }

    function isAdmin() {
      const e = normalizeEmail(currentUser?.email);
      return Boolean(e && ADMIN_EMAILS.includes(e));
    }

    function markReady() {
      if (ready) return;
      ready = true;
      notifyAuthChange();
      try {
        window.dispatchEvent(new CustomEvent('auth-ready', { detail: { user: currentUser } }));
      } catch (e) {
        /* ignore */
      }
      if (resolveReady) {
        resolveReady(currentUser);
        resolveReady = null;
      }
    }

    async function init() {
      if (initStarted) return readyPromise;
      initStarted = true;

      try {
        if (!window.supabaseClient) return;

        const { data: { session } } = await window.supabaseClient.auth.getSession();
        currentUser = session?.user || null;

        window.supabaseClient.auth.onAuthStateChange((event, session) => {
          currentUser = session?.user || null;
          notifyAuthChange();
        });
      } catch (e) {
        console.warn('[Auth] 초기화 실패 — 로그인 세션을 확인할 수 없습니다:', e);
        currentUser = null;
      } finally {
        markReady();
      }

      return readyPromise;
    }

    function notifyAuthChange() {
      window.dispatchEvent(new CustomEvent('auth-changed', { detail: { user: currentUser } }));
    }

    async function signInGoogle(opts) {
      const silent = Boolean(opts && opts.silent);
      try {
        if (!window.supabaseClient) {
          if (!silent) alert('Supabase 설정이 필요합니다.');
          return false;
        }
        const redirectTo =
          opts && typeof opts.redirectTo === 'string' ? opts.redirectTo : window.location.origin;
        const { error } = await window.supabaseClient.auth.signInWithOAuth({
          provider: 'google',
          options: { redirectTo }
        });
        if (error) {
          console.error('Sign in error', error);
          return false;
        }
        return true;
      } catch (e) {
        console.warn('[Auth] signInGoogle 실패:', e);
        return false;
      }
    }

    async function signOut() {
      try {
        if (!window.supabaseClient) return;
        await window.supabaseClient.auth.signOut();
      } catch (e) {
        console.warn('[Auth] signOut 실패:', e);
      }
    }

    function getUser() {
      return currentUser;
    }

    /** 최초 세션 확인 완료 여부. 확인 전에는 gate가 fail-closed로 유지된다. */
    function whenReady() {
      return readyPromise;
    }

    function isReady() {
      return ready;
    }

    // 초기화 진행
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
    } else {
      init();
    }

    return { init, signInGoogle, signOut, getUser, isAdmin, isReady, whenReady };
  })();

  try {
    global.dispatchEvent(new Event('aiden-auth-module-loaded'));
  } catch (e) {
    /* ignore */
  }
})(window);
