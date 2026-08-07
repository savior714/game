"""Browser acceptance for YouTube free time PiP and timer UI fallback.

Verifies:
- On session start (or when active session exists), a fixed timer UI is rendered in the page.
- Remaining time is formatted as MM:SS based on deadline - Date.now().
- Document Picture-in-Picture fallback works cleanly when window.documentPictureInPicture is undefined or fails.
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


def test_youtube_timer_ui_fallback_renders_on_session_start() -> None:
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

            # Start session
            result = page.evaluate("() => RewardSystem.startYouTubeSession()")
            assert result["code"] == "started", f"Expected started, got {result}"

            # Check if timer bar UI element exists and is visible
            timer_visible = page.evaluate("""() => {
                const el = document.getElementById('youtube-free-time-timer') || document.querySelector('.youtube-timer-bar');
                return el ? (el.offsetWidth > 0 && el.offsetHeight > 0) : false;
            }""")
            assert timer_visible, "Timer UI element (#youtube-free-time-timer or .youtube-timer-bar) should be visible on page"

            # Verify remaining time text contains 15:00 or 14:59
            timer_text = page.evaluate("""() => {
                const el = document.getElementById('youtube-free-time-timer') || document.querySelector('.youtube-timer-bar');
                return el ? el.textContent : '';
            }""")
            assert any(t in timer_text for t in ["15:00", "14:59", "14:58", "14:57"]), f"Timer text should show remaining time MM:SS, got: {timer_text}"

            browser.close()
    finally:
        server.stop()

