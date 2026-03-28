window.SupabaseConfig = {
  // TODO: 개발 환경에 맞는 Supabase URL 및 anon 키로 대체하세요.
  URL: 'https://rxjefpmvlygunrukccgg.supabase.co',
  KEY: 'sb_publishable_86T5zbV_IUXZDvQig6mofg_tlHYeHVx'
};

if (typeof supabase !== 'undefined') {
  window.supabaseClient = supabase.createClient(SupabaseConfig.URL, SupabaseConfig.KEY);
}

window.Auth = (() => {
  let currentUser = null;

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

  async function init() {
    if (!window.supabaseClient) return;

    const { data: { session } } = await supabaseClient.auth.getSession();
    currentUser = session?.user || null;
    notifyAuthChange();

    supabaseClient.auth.onAuthStateChange((event, session) => {
      currentUser = session?.user || null;
      notifyAuthChange();
    });
  }

  function notifyAuthChange() {
    window.dispatchEvent(new CustomEvent('auth-changed', { detail: { user: currentUser } }));
  }

  async function signInGoogle(opts) {
    if (!window.supabaseClient) return alert('Supabase 설정이 필요합니다.');
    const redirectTo =
      opts && typeof opts.redirectTo === 'string' ? opts.redirectTo : window.location.origin;
    const { error } = await supabaseClient.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo }
    });
    if (error) console.error('Sign in error', error);
  }

  async function signOut() {
    if (!window.supabaseClient) return;
    await supabaseClient.auth.signOut();
  }

  function getUser() {
    return currentUser;
  }

  // 초기화 진행
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  return { init, signInGoogle, signOut, getUser, isAdmin };
})();
