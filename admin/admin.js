(function () {
  const listEl = document.getElementById('user-list');
  const statusEl = document.getElementById('status');
  const countEl = document.getElementById('user-count');

  function setStatus(msg, isErr) {
    if (!statusEl) return;
    statusEl.textContent = msg;
    statusEl.className = isErr ? 'text-sm text-red-600' : 'text-sm text-gray-500';
  }

  function renderRows(rows) {
    if (!listEl) return;
    if (!rows || rows.length === 0) {
      listEl.innerHTML =
        '<li class="py-8 text-center text-gray-400 text-sm">아직 등록된 계정이 없거나, SQL 백필 전이면 비어 있을 수 있습니다.</li>';
      if (countEl) countEl.textContent = '0';
      return;
    }
    if (countEl) countEl.textContent = String(rows.length);
    listEl.innerHTML = rows
      .map((r) => {
        const when = r.created_at
          ? new Date(r.created_at).toLocaleString('ko-KR')
          : '—';
        const em = (r.email || '').replace(/</g, '&lt;');
        return `<li class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 py-3 border-b border-gray-100 last:border-0">
          <span class="font-medium text-gray-900 break-all">${em}</span>
          <span class="text-xs text-gray-400 shrink-0">${when}</span>
        </li>`;
      })
      .join('');
  }

  async function loadUsers() {
    if (!window.supabaseClient || !window.Auth?.isAdmin()) return;
    setStatus('목록 불러오는 중…');
    const { data, error } = await window.supabaseClient
      .from('user_directory')
      .select('id, email, created_at')
      .order('created_at', { ascending: false });

    if (error) {
      console.error(error);
      setStatus('불러오기 실패: ' + (error.message || '알 수 없음'), true);
      renderRows([]);
      return;
    }
    setStatus('최신 목록입니다. 새로고침으로 갱신할 수 있습니다.');
    renderRows(data || []);
  }

  function refreshUi() {
    const u = window.Auth?.getUser();
    const gate = document.getElementById('gate');
    const panel = document.getElementById('admin-panel');
    const loginBtn = document.getElementById('btn-login');
    const logoutBtn = document.getElementById('btn-logout');

    if (!u) {
      if (gate) gate.classList.remove('hidden');
      if (panel) panel.classList.add('hidden');
      if (loginBtn) loginBtn.classList.remove('hidden');
      if (logoutBtn) logoutBtn.classList.add('hidden');
      setStatus('구글로 로그인해 주세요.');
      return;
    }

    if (loginBtn) loginBtn.classList.add('hidden');
    if (logoutBtn) logoutBtn.classList.remove('hidden');

    if (!window.Auth.isAdmin()) {
      if (gate) gate.classList.remove('hidden');
      if (panel) panel.classList.add('hidden');
      setStatus('이 페이지는 지정된 관리자 계정만 사용할 수 있습니다.', true);
      return;
    }

    if (gate) gate.classList.add('hidden');
    if (panel) panel.classList.remove('hidden');

    const me = document.getElementById('admin-email');
    if (me) me.textContent = u.email || '';

    loadUsers();
  }

  window.addEventListener('auth-changed', refreshUi);

  window.addEventListener('DOMContentLoaded', () => {
    const loginBtn = document.getElementById('btn-login');
    const logoutBtn = document.getElementById('btn-logout');
    const refreshBtn = document.getElementById('btn-refresh');

    if (loginBtn) {
      loginBtn.addEventListener('click', () => {
        const redirectTo = new URL('index.html', window.location.href).href;
        window.Auth?.signInGoogle({ redirectTo });
      });
    }
    if (logoutBtn) {
      logoutBtn.addEventListener('click', () => window.Auth?.signOut());
    }
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => loadUsers());
    }

    refreshUi();
  });
})();
