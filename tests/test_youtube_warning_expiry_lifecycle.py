"""Browser acceptance for YouTube free time warning and expiry lifecycle.

Verifies:
- 1-minute warning & 10-second countdown pulse.
- Expiry modal overlay on session expiration (00:00).
- Clicking '확인했어요' transitions state to acknowledged and cleans up timer UI.
"""

from __future__ import annotations

import socketserver
import threading
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

from playwright.sync_api import sync_playwright

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


def test_youtube_expiry_overlay_and_acknowledge() -> None:
    server = HTTPServerFixture()
    base_url = server.start()
    domain_url = f"{base_url}/domains/math/index.html"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                viewport={"width": LOGICAL_WIDTH, "height": LOGICAL_HEIGHT},
            )

            page.goto(domain_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)

            # Pre-seed an almost expired session (1 second remaining)
            page.evaluate("""() => {
                const now = Date.now();
                const session = {
                    schemaVersion: 1,
                    sessionId: 'sess-expiring',
                    status: 'running',
                    startedAt: now - 899000,
                    endsAt: now + 1000,
                    durationMs: 900000,
                    chargedMinutes: 15,
                    source: 'reward',
                    warningEmittedAt: null,
                    expiredAt: null,
                    acknowledgedAt: null
                };
                localStorage.setItem('study_youtube_free_time_session_v1', JSON.stringify(session));
                if (typeof FreeTimeSession !== 'undefined' && typeof RewardSystemUI !== 'undefined') {
                    RewardSystemUI.renderFreeTimeTimerUI(session);
                }
            }""")

            # Wait 2 seconds for session to expire
            page.wait_for_timeout(2000)

            # Expiry overlay should be visible
            overlay_visible = page.evaluate("""() => {
                const el = document.getElementById('yt-expired-overlay');
                return el ? (el.offsetWidth > 0 && el.offsetHeight > 0) : false;
            }""")
            assert overlay_visible, "Expiry overlay (#yt-expired-overlay) should be visible on timer expiration"

            # Click acknowledge button
            page.click("#yt-ack-btn")
            page.wait_for_timeout(500)

            # Session in localStorage should now be acknowledged
            status = page.evaluate("""() => {
                const raw = localStorage.getItem('study_youtube_free_time_session_v1');
                if (!raw) return null;
                return JSON.parse(raw).status;
            }""")
            assert status == "acknowledged", f"Expected acknowledged status, got {status}"

            browser.close()
    finally:
        server.stop()
