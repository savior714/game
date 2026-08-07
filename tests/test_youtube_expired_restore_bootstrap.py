"""Browser acceptance for YouTube expired session restore on bootstrap.

Verifies:
- Pre-seeded 'running' session whose endsAt <= now is restored to 'expired' status on page bootstrap.
- Persisted session.status becomes 'expired' with finite expiredAt timestamp.
- #yt-expired-overlay is automatically visible without user interaction.
- No external windows are opened, no extra reward inventory is deducted, no new sessions created.
- Quality gates: 0 page errors, 0 console errors, 0 failed asset requests.
"""

from __future__ import annotations

import socketserver
import threading
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
LOGICAL_WIDTH = 1280
LOGICAL_HEIGHT = 720


class HTTPServerFixture:
    def __init__(self) -> None:
        self.server: socketserver.TCPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self, directory: Path | None = None) -> str:
        serve_dir = directory or REPO_ROOT

        class QuietHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(serve_dir), **kwargs)

            def log_message(self, format: str, *args) -> None:
                return

        self.server = socketserver.TCPServer(("127.0.0.1", 0), QuietHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def stop(self) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=2)


def _instrument(page: Page, base_url: str):
    page_errors: list[str] = []
    console_errors: list[str] = []
    request_failures: list[dict[str, object]] = []
    youtube_requests: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on(
        "console",
        lambda message: (
            console_errors.append(message.text) if message.type == "error" else None
        ),
    )
    page.on(
        "requestfailed",
        lambda request: request_failures.append(
            {"url": request.url, "failure": request.failure}
        ),
    )
    page.on(
        "request",
        lambda request: (
            youtube_requests.append(request.url)
            if "youtube" in request.url and not request.url.startswith(base_url)
            else None
        ),
    )
    return page_errors, console_errors, request_failures, youtube_requests


def _assert_quality_gates(errors) -> None:
    page_errors, console_errors, request_failures, youtube_requests = errors
    assert page_errors == [], f"page errors: {page_errors}"
    assert console_errors == [], f"console errors: {console_errors}"
    assert request_failures == [], f"request failures: {request_failures}"
    assert youtube_requests == [], f"unexpected youtube domain requests: {youtube_requests}"


def test_youtube_expired_session_restored_on_bootstrap() -> None:
    server = HTTPServerFixture()
    base_url = server.start()
    domain_url = f"{base_url}/domains/math/index.html"

    errors = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                viewport={"width": LOGICAL_WIDTH, "height": LOGICAL_HEIGHT},
            )
            page_errors, console_errors, request_failures, youtube_requests = _instrument(
                page, base_url
            )

            # Instrument window.open to track any external launches
            page.add_init_script("""() => {
                window._launchCalls = [];
                const origOpen = window.open.bind(window);
                window.open = function(url, target, features) {
                    window._launchCalls.push(url);
                    return { close: () => {} };
                };
            }""")

            # Navigate to establish origin, seed localStorage, then reload to test bootstrap
            page.goto(domain_url, wait_until="domcontentloaded", timeout=15000)

            # Pre-seed an elapsed running session (endsAt < now) before bootstrap
            page.evaluate("""() => {
                const now = Date.now();
                const session = {
                    schemaVersion: 1,
                    sessionId: 'yt-expired-seed-123',
                    status: 'running',
                    startedAt: now - 1000000,
                    endsAt: now - 100000,
                    durationMs: 900000,
                    chargedMinutes: 15,
                    source: 'reward',
                    warningEmittedAt: null,
                    expiredAt: null,
                    acknowledgedAt: null
                };
                localStorage.setItem('study_youtube_free_time_session_v1', JSON.stringify(session));
                localStorage.setItem('study_rewards', JSON.stringify({ gems: 5, youtube_minutes: 15 }));
            }""")

            # Reload page to trigger real RewardSystem.init() bootstrap with seeded storage
            page.reload(wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)

            # 1. Verify window.open was NOT called (0 external launches)
            launch_calls = page.evaluate("() => window._launchCalls || []")
            assert len(launch_calls) == 0, f"Expected 0 launch calls, got {launch_calls}"

            # 2. Check persisted session in localStorage
            stored_session = page.evaluate("""() => {
                const raw = localStorage.getItem('study_youtube_free_time_session_v1');
                return raw ? JSON.parse(raw) : null;
            }""")
            assert stored_session is not None, "Session should exist in localStorage"
            assert stored_session["status"] == "expired", f"Expected persisted status 'expired', got '{stored_session.get('status')}'"
            assert isinstance(stored_session.get("expiredAt"), (int, float)), f"Expected finite expiredAt, got {stored_session.get('expiredAt')}"

            # 3. Check #yt-expired-overlay visibility
            overlay_visible = page.evaluate("""() => {
                const el = document.getElementById('yt-expired-overlay');
                return el ? (el.offsetWidth > 0 && el.offsetHeight > 0) : false;
            }""")
            assert overlay_visible, "#yt-expired-overlay should be visible on bootstrap for expired session"

            # 4. Check reward inventory was not modified
            rewards = page.evaluate("""() => {
                const raw = localStorage.getItem('study_rewards');
                return raw ? JSON.parse(raw) : null;
            }""")
            assert rewards["youtube_minutes"] == 15, f"Inventory should remain 15, got {rewards.get('youtube_minutes')}"

            # 5. Check no running timer bar or PiP was started
            running_timer = page.evaluate("""() => {
                const el = document.getElementById('youtube-free-time-timer');
                return el ? (el.offsetWidth > 0 && el.offsetHeight > 0) : false;
            }""")
            assert not running_timer, "Running timer bar should NOT be rendered for expired session"

            browser.close()
    finally:
        server.stop()

    errors = (page_errors, console_errors, request_failures, youtube_requests)
    _assert_quality_gates(errors)
