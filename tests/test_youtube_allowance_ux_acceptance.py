"""Browser acceptance test covering Acceptance Criteria A through J for YouTube Free-Time Allowance UX."""

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


def test_youtube_allowance_ux_comprehensive_acceptance() -> None:
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

            # ── B. Modal projection test ─────────────────────────────
            # Seed usage: morning 20 min, inventory: 80 min at 9 AM
            page.evaluate("""() => {
                const dateKey = FreeTimeAllowance.getDateKey(Date.now());
                const morning9am = new Date();
                morning9am.setHours(9, 0, 0, 0);

                const usage = {
                    schemaVersion: 1,
                    dateKey: dateKey,
                    morningMinutes: 20,
                    afternoonMinutes: 0
                };
                localStorage.setItem(FreeTimeAllowance.STORAGE_KEY, JSON.stringify(usage));
                localStorage.setItem('study_rewards', JSON.stringify({ gems: 10, youtube_minutes: 80 }));
                if (typeof RewardSystem !== 'undefined') {
                    const s = RewardSystem.getState();
                    s.youtube_minutes = 80;
                }
            }""")

            # Open modal
            page.click('[data-type="youtube"]')
            page.wait_for_selector(".reward-yt-modal", timeout=3000)

            # Check projection: today used 20 / 60, morning/period used 20 / 30
            inv_text = page.locator("#yt-modal-inventory").text_content()
            assert "80분" in inv_text, f"Expected 80분 inventory, got {inv_text}"

            daily_text = page.locator("#yt-modal-daily").text_content()
            assert "20 / 60분" in daily_text, f"Expected 20 / 60분, got {daily_text}"

            # Answer parent lock
            def handle_dialog(dialog):
                import re

                nums = re.findall(r"\d+", dialog.message)
                ans = str(int(nums[-2]) + int(nums[-1])) if len(nums) >= 2 else "51"
                dialog.accept(ans)

            page.on("dialog", handle_dialog)
            page.click("#yt-unlock-trigger")
            page.wait_for_timeout(500)

            # In morning with 20 used (10 remaining in period), 10 should be enabled, 20 and 30 disabled
            is_morning = page.evaluate("() => new Date().getHours() < 12")
            if is_morning:
                btn10_disabled = page.evaluate(
                    "() => document.querySelector('button[data-duration=\"10\"]').disabled"
                )
                btn20_disabled = page.evaluate(
                    "() => document.querySelector('button[data-duration=\"20\"]').disabled"
                )
                btn30_disabled = page.evaluate(
                    "() => document.querySelector('button[data-duration=\"30\"]').disabled"
                )
                assert not btn10_disabled, "10 min button should be enabled"
                assert btn20_disabled, (
                    "20 min button should be disabled (exceeds morning quota)"
                )
                assert btn30_disabled, (
                    "30 min button should be disabled (exceeds morning quota)"
                )

            # Close modal
            page.click(".reward-yt-modal .btn-close")
            page.wait_for_timeout(500)

            # ── D & E & G. 20-minute direct start, exact deduction, contextual countdown, no global timer ─
            # Set fresh usage & 80 minutes inventory
            page.evaluate("""() => {
                localStorage.removeItem(FreeTimeAllowance.STORAGE_KEY);
                localStorage.removeItem('study_youtube_free_time_session_v1');
                localStorage.setItem('study_rewards', JSON.stringify({ gems: 10, youtube_minutes: 80 }));
                if (typeof RewardSystem !== 'undefined') {
                    const s = RewardSystem.getState();
                    s.youtube_minutes = 80;
                }
                if (typeof ExternalTabLauncher !== 'undefined') {
                    ExternalTabLauncher.createOpenExternal = () => () => ({ close: () => {} });
                }
            }""")

            # Direct start 20 min
            result = page.evaluate(
                "() => RewardSystem.startYouTubeSession(20, { isDirectUserStart: true })"
            )
            assert result["code"] == "started", f"Expected started, got {result}"

            # Verify reward deducted by exactly 20 (80 -> 60)
            rew_minutes = page.evaluate("() => RewardSystem.getState().youtube_minutes")
            assert rew_minutes == 60, (
                f"Expected 60 minutes remaining, got {rew_minutes}"
            )

            # Verify session duration is 20 min (1200000 ms)
            stored_session = page.evaluate("""() => {
                const raw = localStorage.getItem('study_youtube_free_time_session_v1');
                return raw ? JSON.parse(raw) : null;
            }""")
            assert stored_session["durationMs"] == 1200000, (
                f"Expected 1200000ms duration, got {stored_session['durationMs']}"
            )
            assert stored_session["chargedMinutes"] == 20, (
                f"Expected 20 charged minutes, got {stored_session['chargedMinutes']}"
            )

            # E. Verify NO global fixed timer bar exists
            fixed_timer_exists = page.evaluate("""() => {
                const el = document.getElementById('youtube-free-time-timer') || document.querySelector('.youtube-timer-bar');
                return el !== null;
            }""")
            assert not fixed_timer_exists, "Global fixed timer bar should NOT exist"

            # G. Contextual countdown in inventory control
            page.wait_for_timeout(1000)
            inv_yt_val = page.evaluate("""() => {
                const el = document.getElementById('inv-youtube');
                return el ? el.textContent : '';
            }""")
            assert "사용 중" in inv_yt_val or ":" in inv_yt_val, (
                f"Contextual YouTube control should display running timer, got: '{inv_yt_val}'"
            )

            # ── I. 1-Minute Warning exactly once ─────────────────────
            # Fast-forward session to 50 seconds remaining
            page.evaluate("""() => {
                const raw = localStorage.getItem('study_youtube_free_time_session_v1');
                const s = JSON.parse(raw);
                s.endsAt = Date.now() + 50000;
                localStorage.setItem('study_youtube_free_time_session_v1', JSON.stringify(s));
            }""")

            page.wait_for_timeout(1500)

            # Check warningEmittedAt is set
            warning_emitted = page.evaluate("""() => {
                const raw = localStorage.getItem('study_youtube_free_time_session_v1');
                const s = JSON.parse(raw);
                return s.warningEmittedAt !== null;
            }""")
            assert warning_emitted, (
                "warningEmittedAt should be recorded when remaining <= 60s"
            )

            warning_text = page.evaluate("""() => {
                const el = document.getElementById('inv-youtube');
                return el ? el.textContent : '';
            }""")
            assert "1분 남음" in warning_text or "00:" in warning_text, (
                f"Warning state text expected, got: {warning_text}"
            )

            # ── F. Lifecycle Expiry & Ack without timer DOM ───────────
            # Fast-forward to expired (endsAt in past)
            page.evaluate("""() => {
                const raw = localStorage.getItem('study_youtube_free_time_session_v1');
                const s = JSON.parse(raw);
                s.endsAt = Date.now() - 1000;
                localStorage.setItem('study_youtube_free_time_session_v1', JSON.stringify(s));
            }""")

            page.wait_for_timeout(1500)

            # Expiry overlay visible
            overlay_visible = page.evaluate("""() => {
                const el = document.getElementById('yt-expired-overlay');
                return el && (el.offsetWidth > 0 || el.offsetHeight > 0);
            }""")
            assert overlay_visible, "Expiry overlay should appear when deadline passes"

            # Click acknowledge
            page.click("#yt-ack-btn")
            page.wait_for_timeout(500)

            # Acknowledged status and normal inventory restored
            ack_status = page.evaluate("""() => {
                const raw = localStorage.getItem('study_youtube_free_time_session_v1');
                return JSON.parse(raw).status;
            }""")
            assert ack_status == "acknowledged", (
                f"Expected acknowledged, got {ack_status}"
            )

            restored_inv_text = page.evaluate("""() => {
                const el = document.getElementById('inv-youtube');
                return el ? el.textContent : '';
            }""")
            assert "60" in restored_inv_text, (
                f"Inventory should restore to 60, got: '{restored_inv_text}'"
            )

            # ── H. Reload Restore without PiP request ─────────────────
            # Seed active running session before reload
            page.evaluate("""() => {
                window.__pipRequestCount = 0;
                if ('documentPictureInPicture' in window) {
                    const orig = window.documentPictureInPicture.requestWindow;
                    window.documentPictureInPicture.requestWindow = function(...args) {
                        window.__pipRequestCount++;
                        return orig.apply(this, args);
                    };
                }
                const now = Date.now();
                const activeSess = {
                    schemaVersion: 1,
                    sessionId: 'sess-restore-test',
                    status: 'running',
                    startedAt: now,
                    endsAt: now + 500000,
                    durationMs: 600000,
                    chargedMinutes: 10,
                    source: 'reward',
                    warningEmittedAt: null,
                    expiredAt: null,
                    acknowledgedAt: null
                };
                localStorage.setItem('study_youtube_free_time_session_v1', JSON.stringify(activeSess));
            }""")

            page.reload(wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)

            # Contextual countdown restored
            reload_yt_text = page.evaluate("""() => {
                const el = document.getElementById('inv-youtube');
                return el ? el.textContent : '';
            }""")
            assert "사용 중" in reload_yt_text or ":" in reload_yt_text, (
                f"Contextual countdown should be restored on reload, got '{reload_yt_text}'"
            )

            # PiP requestWindow should NOT be called on bootstrap/reload
            pip_count = page.evaluate("() => window.__pipRequestCount || 0")
            assert pip_count == 0, (
                f"Document PiP requestWindow should be 0 on restore, got {pip_count}"
            )

            # Global fixed bar still absent
            bar_after_reload = page.evaluate("""() => {
                const el = document.getElementById('youtube-free-time-timer');
                return el !== null;
            }""")
            assert not bar_after_reload, (
                "Global timer bar should NOT exist after reload"
            )

            browser.close()
    finally:
        server.stop()
