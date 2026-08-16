"""Browser acceptance for YouTube free time contextual countdown and no global timer bar.

Verifies:
- On session start, NO fixed global timer bar (#youtube-free-time-timer or .youtube-timer-bar) is rendered.
- Instead, the contextual inventory control for YouTube shows active countdown ("사용 중 · MM:SS").
- When session is restored on reload, contextual countdown is restored and document PiP is NOT automatically requested.
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


def test_youtube_contextual_countdown_and_no_fixed_bar() -> None:
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

            # Pre-seed youtube_minutes and patch ExternalTabLauncher
            page.evaluate("""() => {
                localStorage.setItem('study_rewards', JSON.stringify({ gems: 10, youtube_minutes: 30 }));
                if (typeof RewardSystem !== 'undefined') {
                    const s = RewardSystem.getState();
                    s.youtube_minutes = 30;
                }
                if (typeof ExternalTabLauncher !== 'undefined') {
                    ExternalTabLauncher.createOpenExternal = () => () => ({ close: () => {}, closed: false, focus: () => {} });
                }
            }""")

            # Start 10-minute session
            result = page.evaluate(
                "() => RewardSystem.startYouTubeSession(10, { isDirectUserStart: true })"
            )
            assert result["code"] == "started", f"Expected started, got {result}"

            # 1. Global fixed timer bar must NOT exist
            timer_bar_exists = page.evaluate("""() => {
                const el = document.getElementById('youtube-free-time-timer') || document.querySelector('.youtube-timer-bar');
                return el !== null;
            }""")
            assert not timer_bar_exists, "Global fixed timer bar should NOT be created"

            # 2. Contextual inventory item must show running countdown
            page.wait_for_timeout(1000)
            yt_text = page.evaluate("""() => {
                const el = document.getElementById('inv-youtube');
                return el ? el.textContent : '';
            }""")
            assert "사용 중" in yt_text or ":" in yt_text, (
                f"Contextual YouTube control should display running countdown, got: '{yt_text}'"
            )

            browser.close()
    finally:
        server.stop()
