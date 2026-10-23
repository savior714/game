"""Bootstrap kernel — ensure repo root is importable for tools.tdd_gate_plugin and classify tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

pytest_plugins = ["tools.tdd_gate_plugin"]


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "browser: marks browser automation tests (Playwright)"
    )
    config.addinivalue_line(
        "markers", "live: marks tests requiring real Supabase or live network services"
    )
    config.addinivalue_line("markers", "slow: marks slow tests taking over 5 seconds")


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Automatically tag tests based on file path, name, or module imports.

    This ensures that tests importing Playwright or hitting real external services
    are classified under `browser` or `live`, preventing accidental execution during
    standard fast unit/policy validation runs.
    """
    for item in items:
        file_path = str(item.fspath).lower()
        module = getattr(item, "module", None)
        module_source = ""
        if module and hasattr(module, "__file__") and module.__file__:
            try:
                if not hasattr(module, "_cached_source"):
                    module._cached_source = Path(module.__file__).read_text(
                        encoding="utf-8", errors="ignore"
                    )
                module_source = module._cached_source
            except Exception:
                pass

        # 1. Browser tests: playwright in imports or browser in filename
        is_browser = (
            "_browser" in file_path
            or "browser_" in file_path
            or "playwright" in file_path
            or "from playwright" in module_source
            or "import playwright" in module_source
        )
        # Exception: test_playwright_git_workflow_consistency.py is a pure markdown doc link check
        if "test_playwright_git_workflow_consistency.py" in file_path:
            is_browser = False

        if is_browser:
            item.add_marker(pytest.mark.browser)

        # 2. Live external services / real DB tests
        is_live = (
            "_real_db" in file_path
            or "real_db_" in file_path
            or "verify_live_supabase" in file_path
            or "test_supabase_production" in file_path
            or "test_live_" in file_path
            or "LIVE_SUPABASE_URL" in module_source
        )
        if is_live:
            item.add_marker(pytest.mark.live)


# ── Browser auth harness ───────────────────────────────────────────────────
# Login gate는 확인된 Supabase session 없이는 모든 child-facing surface를 막는다.
# 제품 코드에는 테스트용 bypass를 두지 않고, Playwright init script에서
#   (1) Supabase SDK stub  → CDN/네트워크 없이 결정적으로 동작
#   (2) localStorage session → Auth.getSession()이 로그인 사용자를 반환
# 을 심는다. 브라우저 테스트는 기본적으로 "이미 로그인된 아이" 상태로 시작한다.
#
#   @pytest.mark.signed_out     세션을 심지 않아 로그인 gate 화면을 검증한다.
#   @pytest.mark.real_supabase  stub 없이 실제 CDN SDK를 사용한다(네트워크 필요).
_E2E_SUPABASE_PROJECT_REF = "rxjefpmvlygunrukccgg"
_E2E_SESSION_STORAGE_KEY = f"sb-{_E2E_SUPABASE_PROJECT_REF}-auth-token"
_E2E_SESSION_USER = {
    "id": "00000000-0000-4000-8000-000000000001",
    "aud": "authenticated",
    "role": "authenticated",
    "email": "e2e@example.test",
    "email_confirmed_at": "2026-01-01T00:00:00Z",
    "phone": "",
    "confirmed_at": "2026-01-01T00:00:00Z",
    "last_sign_in_at": "2026-01-01T00:00:00Z",
    "app_metadata": {"provider": "google", "providers": ["google"]},
    "user_metadata": {"full_name": "Aiden E2E"},
    "identities": [],
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}
_E2E_SESSION = {
    "access_token": "e2e-access-token",
    "token_type": "bearer",
    "expires_in": 3600,
    "expires_at": 4102444800,
    "refresh_token": "e2e-refresh-token",
    "user": _E2E_SESSION_USER,
}

_E2E_SUPABASE_STUB_JS = r"""
(() => {
  if (window.__aidenE2EStub) return;
  window.__aidenE2EStub = true;

  const KEY = %(key)s;
  const readSession = () => {
    try {
      const raw = localStorage.getItem(KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (error) {
      return null;
    }
  };
  const listeners = new Set();
  const emit = (event, session) => {
    listeners.forEach((listener) => {
      try {
        listener(event, session);
      } catch (error) {
        console.error('[e2e supabase stub]', error);
      }
    });
  };
  const query = {};
  ['select', 'insert', 'update', 'upsert', 'delete', 'eq', 'neq', 'in', 'is',
   'order', 'limit', 'range', 'match', 'filter', 'or'].forEach((name) => {
    query[name] = () => query;
  });
  query.maybeSingle = () => Promise.resolve({ data: null, error: null });
  query.single = () => Promise.resolve({ data: null, error: null });
  query.then = (resolve, reject) =>
    Promise.resolve({ data: [], error: null }).then(resolve, reject);
  query.catch = (reject) => Promise.resolve({ data: [], error: null }).catch(reject);

  const client = {
    auth: {
      async getSession() {
        return { data: { session: readSession() }, error: null };
      },
      async getUser() {
        const session = readSession();
        return { data: { user: session && session.user ? session.user : null }, error: null };
      },
      onAuthStateChange(callback) {
        listeners.add(callback);
        setTimeout(() => {
          try {
            callback('INITIAL_SESSION', readSession());
          } catch (error) {
            console.error('[e2e supabase stub]', error);
          }
        }, 0);
        return {
          data: {
            subscription: {
              unsubscribe() {
                listeners.delete(callback);
              },
            },
          },
        };
      },
      async signOut() {
        try {
          localStorage.removeItem(KEY);
          localStorage.removeItem(KEY + '-user');
        } catch (error) {
          /* ignore */
        }
        emit('SIGNED_OUT', null);
        return { error: null };
      },
      async signInWithOAuth(options) {
        window.__aidenE2ELastSignIn = options;
        return {
          data: {
            provider: options && options.provider,
            url: 'https://accounts.google.com/o/oauth2/v2/auth',
          },
          error: null,
        };
      },
      async setSession() {
        return { data: { session: readSession() }, error: null };
      },
    },
    from() {
      return query;
    },
    rpc() {
      return Promise.resolve({ data: null, error: null });
    },
    channel() {
      return {
        on() {
          return this;
        },
        subscribe() {
          return this;
        },
        unsubscribe() {},
      };
    },
    removeChannel() {
      return Promise.resolve();
    },
  };

  const stub = { createClient: () => client };
  try {
    Object.defineProperty(window, 'supabase', {
      configurable: true,
      writable: true,
      value: stub,
    });
  } catch (error) {
    window.supabase = stub;
  }

})();
""" % {"key": json.dumps(_E2E_SESSION_STORAGE_KEY)}

_E2E_SESSION_SEED_JS = r"""
(() => {
  try {
    const key = %(key)s;
    if (!localStorage.getItem(key)) {
      localStorage.setItem(key, %(session)s);
    }
  } catch (error) {
    // about:blank 등 storage를 쓸 수 없는 문서에서는 무시한다.
  }
})();
""" % {
    "key": json.dumps(_E2E_SESSION_STORAGE_KEY),
    "session": json.dumps(json.dumps(_E2E_SESSION)),
}

_E2E_OCEAN_ADMISSION_SEED_JS = r"""
(() => {
  try {
    const pathname = window.location && window.location.pathname ? window.location.pathname : "";
    if (!(/\/ocean-rescue\/|\/domains\/ocean-rescue\//).test(pathname)) {
      return;
    }
    const key = "aiden_study_game_admission_v1";
    if (!sessionStorage.getItem(key)) {
      const startedAt = Date.now();
      sessionStorage.setItem(key, JSON.stringify({
        version: 1,
        phase: "playing",
        game: "ocean-rescue",
        subject: "math",
        correct: 5,
        startedAt,
        deadline: startedAt + 300000
      }));
    }
  } catch (error) {
    // about:blank 등 storage를 쓸 수 없는 문서에서는 무시한다.
  }
})();
"""

_UNENTITLED_STUDY_MODULES = {
    "test_study_game_admission_browser",
    "test_ocean_rescue_daily_goal_gate_browser",
    "test_math_reward_ocean_rescue_gate_browser",
}

_E2E_AUTH_MODE = {"value": "signed_in", "seed_ocean_admission": True}


def _e2e_auth_init_script(mode: str, seed_ocean_admission: bool = True) -> str:
    parts = []
    if mode != "real_supabase":
        parts.append(_E2E_SUPABASE_STUB_JS)
    if mode == "signed_in":
        parts.append(_E2E_SESSION_SEED_JS)
    if seed_ocean_admission:
        parts.append(_E2E_OCEAN_ADMISSION_SEED_JS)
    return "\n".join(parts)


@pytest.fixture(autouse=True)
def _e2e_auth_mode(request: pytest.FixtureRequest):
    if request.node.get_closest_marker("signed_out"):
        mode = "signed_out"
    elif request.node.get_closest_marker("real_supabase"):
        mode = "real_supabase"
    else:
        mode = "signed_in"
    module_name = getattr(request.node.module, "__name__", "").rsplit(".", 1)[-1]
    seed_ocean = (
        request.node.get_closest_marker("unentitled_study_game") is None
        and module_name not in _UNENTITLED_STUDY_MODULES
    )
    _E2E_AUTH_MODE["value"] = mode
    _E2E_AUTH_MODE["seed_ocean_admission"] = seed_ocean
    try:
        yield mode
    finally:
        _E2E_AUTH_MODE["value"] = "signed_in"
        _E2E_AUTH_MODE["seed_ocean_admission"] = True


@pytest.fixture(autouse=True, scope="session")
def _seed_signed_in_browser_session():
    """Playwright가 만든 모든 Page가 로그인 상태에서 시작하도록 init script를 심는다.

    Playwright가 없는 환경(unit/policy 전용 실행)에서는 아무 것도 하지 않는다.
    """
    try:
        from playwright.sync_api import Page
    except Exception:
        yield
        return

    original_goto = Page.goto

    def goto_with_session(self, *args, **kwargs):
        # init script는 이후 모든 navigation에 적용되며, 중복 주입은 JS guard로 무해하다.
        try:
            script = _e2e_auth_init_script(
                str(_E2E_AUTH_MODE["value"]),
                bool(_E2E_AUTH_MODE["seed_ocean_admission"]),
            )
            if script:
                self.add_init_script(script=script)
        except Exception:
            pass
        return original_goto(self, *args, **kwargs)

    Page.goto = goto_with_session
    try:
        yield
    finally:
        Page.goto = original_goto
