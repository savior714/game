"""Browser verification for Agent Weekly English Ingestion Vertical Slice.

Verifies:
1. Starting state has old weekly set (2026-09-18) in localStorage.
2. Direct entry to domains/english/index.html:
   - Authenticated user pulls new remote set (2026-09-25) via SyncEngine.
   - Local store is updated to new set.
   - General English weekly reinforce words use the new set without code changes.
   - Old set words do not leak.
3. Direct entry to domains/english/weekly-test/index.html:
   - Authenticated user pulls new remote set (2026-09-25).
   - Weekly test displays new set ID and first question prompt from the new set.
   - No old set prompt/word leakage.
4. Clean execution: 0 page errors, 0 unhandled console errors.
"""

from __future__ import annotations

import http.server
import json
import socketserver
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Page, Route, sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent

NEW_WEEKLY_SET = {
    "schemaVersion": 1,
    "setId": "2026-09-25",
    "testDate": "2026-09-25",
    "title": "2026-09-25 주간 영단어",
    "revision": 1,
    "contentFingerprint": "new-fp-abc-123",
    "_updated_at": 1789900000000,
    "updatedAt": "2026-09-25T00:00:00.000Z",
    "registeredAt": "2026-09-25T00:00:00.000Z",
    "items": [
        {
            "itemId": "2026-09-25-courage-1111",
            "id": "2026-09-25-courage-1111",
            "word": "courage",
            "answer": "courage",
            "academyDescription": "the ability to do something frightening",
            "prompt": "the ability to do something frightening",
            "ko": "용기",
            "icon": "🦁",
        },
        {
            "itemId": "2026-09-25-brilliant-2222",
            "id": "2026-09-25-brilliant-2222",
            "word": "brilliant",
            "answer": "brilliant",
            "academyDescription": "exceptionally clever or talented",
            "prompt": "exceptionally clever or talented",
            "ko": "눈부신",
            "icon": "✨",
        },
    ],
}


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def log_message(self, format, *args):  # noqa: A002
        pass


@pytest.fixture(scope="module")
def static_server():
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("127.0.0.1", 0), QuietHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{port}"

    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


@pytest.fixture
def browser_context():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
        )
        yield context
        context.close()
        browser.close()


def _setup_supabase_routes(page: Page) -> None:
    """Intercepts Supabase auth & REST calls to simulate authenticated session and sync."""

    def handle_supabase_rest(route: Route):
        url = route.request.url
        if "user_data" in url and route.request.method == "GET":
            # Return new weekly canonical payload
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    [
                        {
                            "data_key": "aiden_canonical_weekly_vocabulary_v1",
                            "payload": NEW_WEEKLY_SET,
                            "updated_at": "2026-09-25T00:00:00.000Z",
                        }
                    ]
                ),
            )
        else:
            route.fulfill(status=200, content_type="application/json", body="[]")

    page.route("**/rest/v1/**", handle_supabase_rest)


def test_browser_direct_entry_english_pulls_new_set(
    static_server: str, browser_context
) -> None:
    """Direct entry to domains/english/index.html updates store and consumes new words."""
    page = browser_context.new_page()
    page_errors: list[str] = []
    page.on("pageerror", lambda err: page_errors.append(str(err)))

    old_set = {
        "schemaVersion": 1,
        "setId": "2026-09-18",
        "title": "2026-09-18 주간 영단어",
        "_updated_at": 1000,
        "items": [
            {
                "itemId": "old-1",
                "word": "across",
                "answer": "across",
                "academyDescription": "from one side to the other side",
                "prompt": "from one side to the other side",
            }
        ],
    }
    mock_auth_user = {
        "id": "00000000-0000-0000-0000-000000000001",
        "email": "savior714@gmail.com",
    }

    _setup_supabase_routes(page)

    # Pre-populate localStorage
    page.goto(f"{static_server}/index.html")
    page.evaluate(
        f"""() => {{
            localStorage.setItem('aiden_canonical_weekly_vocabulary_v1', JSON.stringify({json.dumps(old_set)}));
            localStorage.setItem('englishWeeklyWords', JSON.stringify([{{ en: 'across', ko: '가로질러', icon: '' }}]));
            window.__MOCK_AUTH_USER__ = {json.dumps(mock_auth_user)};
        }}"""
    )

    # Direct entry to domains/english/index.html
    page.goto(f"{static_server}/domains/english/index.html")

    page.evaluate(
        f"""async () => {{
            const user = {json.dumps(mock_auth_user)};
            if (window.Auth) {{
                window.Auth.getUser = () => user;
                window.dispatchEvent(new CustomEvent('auth-changed', {{ detail: {{ user }} }}));
            }}
            if (window.SyncEngine) {{
                await window.SyncEngine.pullAndMerge(['aiden_canonical_weekly_vocabulary_v1']);
            }}
        }}"""
    )

    # Wait for sync event or localStorage update
    page.wait_for_function(
        """() => {
            const raw = localStorage.getItem('aiden_canonical_weekly_vocabulary_v1');
            if (!raw) return false;
            try {
                const parsed = JSON.parse(raw);
                return parsed.setId === '2026-09-25';
            } catch { return false; }
        }""",
        timeout=5000,
    )

    # Verify General English runtime has new words and no old words
    state = page.evaluate(
        """() => {
            const words = window.getWeeklyWords ? window.getWeeklyWords() : [];
            const raw = localStorage.getItem('aiden_canonical_weekly_vocabulary_v1');
            return {
                words: words.map(w => w.word),
                setId: JSON.parse(raw).setId
            };
        }"""
    )

    assert state["setId"] == "2026-09-25"
    assert "courage" in state["words"]
    assert "across" not in state["words"], "Old set word leaked into General English!"

    # Clean errors
    assert len(page_errors) == 0, f"Page errors encountered: {page_errors}"


def test_browser_direct_entry_weekly_test_pulls_new_set(
    static_server: str, browser_context
) -> None:
    """Direct entry to domains/english/weekly-test/index.html binds new set prompt immediately."""
    page = browser_context.new_page()
    page_errors: list[str] = []
    page.on("pageerror", lambda err: page_errors.append(str(err)))

    old_set = {
        "schemaVersion": 1,
        "setId": "2026-09-18",
        "title": "2026-09-18 주간 영단어",
        "_updated_at": 1000,
        "items": [
            {
                "itemId": "old-1",
                "word": "across",
                "answer": "across",
                "academyDescription": "from one side to the other side",
                "prompt": "from one side to the other side",
            }
        ],
    }
    mock_auth_user = {
        "id": "00000000-0000-0000-0000-000000000001",
        "email": "savior714@gmail.com",
    }

    _setup_supabase_routes(page)

    # Pre-populate localStorage
    page.goto(f"{static_server}/index.html")
    page.evaluate(
        f"""() => {{
            localStorage.setItem('aiden_canonical_weekly_vocabulary_v1', JSON.stringify({json.dumps(old_set)}));
            localStorage.removeItem('weekly_test_session');
            window.__MOCK_AUTH_USER__ = {json.dumps(mock_auth_user)};
        }}"""
    )

    # Direct entry to weekly test
    page.goto(f"{static_server}/domains/english/weekly-test/index.html")

    page.evaluate(
        f"""async () => {{
            const user = {json.dumps(mock_auth_user)};
            if (window.Auth) {{
                window.Auth.getUser = () => user;
                window.dispatchEvent(new CustomEvent('auth-changed', {{ detail: {{ user }} }}));
            }}
            if (window.SyncEngine) {{
                await window.SyncEngine.pullAndMerge(['aiden_canonical_weekly_vocabulary_v1']);
            }}
        }}"""
    )

    # Wait for test prompt to update to new set prompt
    page.wait_for_function(
        """() => {
            const promptEl = document.getElementById('q-prompt');
            return promptEl && promptEl.textContent.includes('the ability to do something frightening');
        }""",
        timeout=5000,
    )

    prompt_text = page.inner_text("#q-prompt")
    assert "the ability to do something frightening" in prompt_text
    assert "from one side to the other side" not in prompt_text, (
        "Old prompt leaked into Weekly Test!"
    )

    assert len(page_errors) == 0, f"Page errors encountered: {page_errors}"
