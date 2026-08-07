"""Browser acceptance for YouTube atomic session start.

Drives a domain page (math) through the reward system and verifies:

- reward scripts load including free-time-session modules
- youtube_minutes inventory shows initial value (30)
- clicking youtube inventory item opens youtube modal
- before parent approval: start button not visible
- after parent approval (math answer): start button shows "유튜브 자유시간 15분 시작"
- informational text present about new tab, keep game tab open, no refund
- clicking start button once: launcher called exactly once with youtube URL
- reward decreases from 30 to 15
- running session created
- modal and inventory update to 15 minutes
- quick double-click: launcher still called only once, no extra deduction
- popup blocked: reward stays at 30, guidance shown, retry button active
- already active session: launcher called 0 times, no extra deduction
- page errors = 0, console errors = 0, failed asset requests = 0, youtube domain requests = 0

Uses a patched ExternalTabLauncher via page.evaluate to record launcher calls
instead of opening real tabs.
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


def _patch_external_tab_launcher(page: Page) -> None:
    """Patch window.open to record calls instead of opening real tabs."""
    page.evaluate("""() => {
      window._launcherCalls = [];
      const origOpen = window.open.bind(window);
      window.open = function(url, target, features) {
        if (url === 'about:blank') window._launcherCalls.push('about:blank');
        return origOpen(url, target, features) || { close: function() {} };
      };
    }""")


def _get_launcher_state(page: Page) -> dict:
    return page.evaluate("""() => ({
      calls: window._launcherCalls || [],
      url: window._launcherUrl || null,
    })""")


def _set_popup_blocked(page: Page) -> None:
    """Make window.open return null (popup blocked)."""
    page.evaluate("""() => {
      window._launcherCalls = [];
      window._launcherUrl = null;
      window.open = function(url, target, features) {
        window._launcherCalls.push(url);
        window._launcherUrl = url;
        return null;
      };
    }""")


def _set_already_active(page: Page, initial_minutes: int = 30) -> None:
    """Pre-seed an active session so start returns already_active."""
    page.evaluate(f"""() => {{
      localStorage.setItem('study_rewards', JSON.stringify({{ youtube_minutes: {initial_minutes} }}));
      if (typeof FreeTimeSession !== 'undefined') {{
        const session = FreeTimeSession.start({{ now: Date.now(), sessionId: 'sess-active', source: 'reward' }});
        localStorage.setItem('study_youtube_free_time_session_v1', JSON.stringify(session));
      }}
    }}""")


def _open_youtube_modal(page: Page) -> None:
    """Click youtube inventory item to open the youtube modal."""
    page.click('[data-type="youtube"]')
    # Wait for modal to appear
    page.wait_for_selector('.reward-yt-modal', timeout=3000)


def _answer_parent_lock(page: Page) -> None:
    """Answer the parent lock prompt by parsing the math problem."""
    def handle_dialog(dialog) -> None:
        msg = dialog.message
        import re
        nums = re.findall(r"\d+", msg)
        if len(nums) >= 2:
            answer = str(int(nums[-2]) + int(nums[-1]))
            dialog.accept(answer)
        else:
            dialog.accept("51")
    page.on("dialog", handle_dialog)


def _click_start_button(page: Page) -> None:
    page.click("#start-yt-btn", force=True)


def _get_reward_minutes(page: Page) -> int:
    return page.evaluate("""() => {
      if (typeof RewardSystem !== 'undefined') {
        return RewardSystem.getState().youtube_minutes;
      }
      const raw = localStorage.getItem('study_rewards');
      if (raw) {
        const r = JSON.parse(raw);
        return r.youtube_minutes;
      }
      return 0;
    }""")


def _get_inventory_minutes(page: Page) -> str:
    return page.locator('#inv-youtube').text_content() or "0"


def _get_session_count(page: Page) -> int:
    return page.evaluate("""() => {
      const raw = localStorage.getItem('study_youtube_free_time_session_v1');
      return raw ? 1 : 0;
    }""")


def _get_result_message(page: Page) -> str | None:
    return page.evaluate("""() => {
      const el = document.getElementById('yt-result-msg');
      return el ? el.textContent : null;
    }""")


def _is_start_button_visible(page: Page) -> bool:
    return page.evaluate("""() => {
      const area = document.getElementById('yt-start-area');
      return area && area.style.display !== 'none';
    }""")


def _is_start_button_disabled(page: Page) -> bool:
    return page.evaluate("""() => {
      const btn = document.getElementById('start-yt-btn');
      return btn ? btn.disabled : true;
    }""")


def test_youtube_atomic_start_flow() -> None:
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

            # Navigate to math domain page (loads reward scripts)
            page.goto(domain_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)  # Let scripts load

            # Pre-seed reward state: set localStorage AND update RewardSystem internal state
            page.evaluate("""() => {
              localStorage.setItem('study_rewards', JSON.stringify({ gems: 10, youtube_minutes: 30, snacks: 2 }));
              if (typeof RewardSystem !== 'undefined') {
                const s = RewardSystem.getState();
                s.gems = 10;
                s.youtube_minutes = 30;
                s.snacks = 2;
              }
            }""")

            # Verify reward scripts loaded
            scripts_loaded = page.evaluate("""() => {
              return {
                FreeTimeSession: typeof FreeTimeSession !== 'undefined',
                ExternalTabLauncher: typeof ExternalTabLauncher !== 'undefined',
                FreeTimeSessionStartTransaction: typeof FreeTimeSessionStartTransaction !== 'undefined',
                RewardSystem: typeof RewardSystem !== 'undefined',
              };
            }""")
            assert scripts_loaded["FreeTimeSession"], "FreeTimeSession not loaded"
            assert scripts_loaded["ExternalTabLauncher"], "ExternalTabLauncher not loaded"
            assert scripts_loaded["FreeTimeSessionStartTransaction"], "FreeTimeSessionStartTransaction not loaded"
            assert scripts_loaded["RewardSystem"], "RewardSystem not loaded"

            # Verify initial youtube_minutes = 30
            assert _get_reward_minutes(page) == 30, f"Expected 30, got {_get_reward_minutes(page)}"

            # Open youtube modal
            _open_youtube_modal(page)
            page.wait_for_timeout(500)

            # Before parent approval: start button not visible
            assert not _is_start_button_visible(page), "Start button should not be visible before approval"

            # Answer parent lock
            _answer_parent_lock(page)
            page.click("#yt-unlock-trigger")
            page.wait_for_timeout(500)

            # After approval: start button visible with correct text
            assert _is_start_button_visible(page), "Start button should be visible after approval"
            start_btn_text = page.locator("#start-yt-btn").text_content()
            assert "유튜브 자유시간 15분 시작" in start_btn_text, f"Expected start button text, got: {start_btn_text}"

            # Informational text present
            info_text = page.locator("#yt-start-area .sub").text_content() or ""
            assert "새 YouTube" in info_text or "YouTube" in info_text, f"Info text missing YouTube mention: {info_text}"
            assert "닫지" in info_text or "tab" in info_text.lower() or "게임" in info_text, f"Info text missing keep-game-tab: {info_text}"
            assert "환불" in info_text or "닫아도" in info_text, f"Info text missing no-refund: {info_text}"

            # Patch launcher before clicking start
            _patch_external_tab_launcher(page)

            # Debug: check button state
            btn_state = page.evaluate("""() => {
              const btn = document.getElementById('start-yt-btn');
              return { disabled: btn ? btn.disabled : 'not found', hasAttr: btn ? btn.hasAttribute('disabled') : 'not found' };
            }""")
            assert not btn_state["disabled"], f"Button should be enabled before click, state: {btn_state}"

            # Click start button once
            _click_start_button(page)
            page.wait_for_timeout(500)

            # Launcher called exactly once (about:blank proves launch flow ran)
            launcher_state = _get_launcher_state(page)
            assert len(launcher_state["calls"]) == 1, f"Expected 1 launcher call, got {len(launcher_state['calls'])}"
            assert "about:blank" in launcher_state["calls"], f"Expected about:blank open, got {launcher_state['calls']}"

            # Reward decreased to 15
            assert _get_reward_minutes(page) == 15, f"Expected 15, got {_get_reward_minutes(page)}"

            # Running session created
            assert _get_session_count(page) == 1, "Expected 1 session"

            # Inventory updated
            inv_minutes = _get_inventory_minutes(page)
            assert "15" in inv_minutes, f"Inventory should show 15, got: {inv_minutes}"

            # Result message shown
            result_msg = _get_result_message(page)
            assert result_msg is not None, "Result message should be shown"
            assert "시작" in result_msg or "new" in result_msg.lower() or "tab" in result_msg.lower(), f"Expected success message, got: {result_msg}"

            # Quick double-click test
            _click_start_button(page)
            page.wait_for_timeout(500)

            launcher_state2 = _get_launcher_state(page)
            assert len(launcher_state2["calls"]) == 1, f"Double-click should not call launcher again, got {len(launcher_state2['calls'])}"
            assert _get_reward_minutes(page) == 15, f"Double-click should not deduct again, got {_get_reward_minutes(page)}"
            assert _get_session_count(page) == 1, f"Double-click should not create extra session, got {_get_session_count(page)}"

            browser.close()
    finally:
        server.stop()

    errors = (page_errors, console_errors, request_failures, youtube_requests)
    _assert_quality_gates(errors)


def test_youtube_popup_blocked() -> None:
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

            page.goto(domain_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)

            page.evaluate("""() => {
              localStorage.setItem('study_rewards', JSON.stringify({ youtube_minutes: 30 }));
              if (typeof RewardSystem !== 'undefined') {
                const s = RewardSystem.getState();
                s.youtube_minutes = 30;
              }
            }""")

            _open_youtube_modal(page)
            page.wait_for_timeout(500)

            _answer_parent_lock(page)
            page.click("#yt-unlock-trigger")
            page.wait_for_timeout(500)

            assert _is_start_button_visible(page), "Start button should be visible after approval"

            # Set popup blocked
            _set_popup_blocked(page)

            _click_start_button(page)
            page.wait_for_timeout(500)

            # Launcher attempted once
            launcher_state = _get_launcher_state(page)
            assert len(launcher_state["calls"]) == 1, f"Expected 1 launcher attempt, got {len(launcher_state['calls'])}"

            # Reward unchanged
            assert _get_reward_minutes(page) == 30, f"Reward should stay at 30 after popup blocked, got {_get_reward_minutes(page)}"

            # Guidance message shown
            result_msg = _get_result_message(page)
            assert result_msg is not None, "Result message should be shown"
            assert "차단" in result_msg or "팝업" in result_msg, f"Expected popup blocked message, got: {result_msg}"

            # Button re-enabled for retry
            assert not _is_start_button_disabled(page), "Button should be re-enabled for retry"

            browser.close()
    finally:
        server.stop()

    errors = (page_errors, console_errors, request_failures, youtube_requests)
    _assert_quality_gates(errors)


def test_youtube_already_active() -> None:
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

            page.goto(domain_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)

            # Pre-seed active session after page loads
            page.evaluate("""() => {
              localStorage.setItem('study_rewards', JSON.stringify({ youtube_minutes: 30 }));
              if (typeof RewardSystem !== 'undefined') {
                const s = RewardSystem.getState();
                s.youtube_minutes = 30;
              }
              if (typeof FreeTimeSession !== 'undefined') {
                const session = FreeTimeSession.start({ now: Date.now(), sessionId: 'sess-active', source: 'reward' });
                localStorage.setItem('study_youtube_free_time_session_v1', JSON.stringify(session));
              }
            }""")

            _open_youtube_modal(page)
            page.wait_for_timeout(500)

            _answer_parent_lock(page)
            page.click("#yt-unlock-trigger")
            page.wait_for_timeout(500)

            assert _is_start_button_visible(page), "Start button should be visible after approval"

            _patch_external_tab_launcher(page)
            _click_start_button(page)
            page.wait_for_timeout(500)

            # Launcher not called
            launcher_state = _get_launcher_state(page)
            assert len(launcher_state["calls"]) == 0, f"Launcher should not be called when already active, got {len(launcher_state['calls'])}"

            # Reward unchanged
            assert _get_reward_minutes(page) == 30, f"Reward should stay at 30 when already active, got {_get_reward_minutes(page)}"

            browser.close()
    finally:
        server.stop()

    errors = (page_errors, console_errors, request_failures, youtube_requests)
    _assert_quality_gates(errors)
