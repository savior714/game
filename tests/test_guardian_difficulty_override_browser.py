"""Browser E2E verification for the guardian difficulty baseline override.

The guardian difficulty save must store a separate baseline preference and
must never rewrite the child's per-level learning statistics.
"""

from __future__ import annotations

import http.server
import json
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent

ENGLISH_DOMAINS = [
    "animals",
    "fruits",
    "nature",
    "vehicles",
    "colors",
    "numbers",
    "clothing",
    "body",
    "food",
    "objects",
]

SEED_ENGLISH_STATS = """() => {
  const levels = {};
  for (let i = 0; i < 7; i++) {
    if (i === 0) levels[i] = { attempts: 10, correct: 10, totalTime: 60 };
    else if (i === 1) levels[i] = { attempts: 8, correct: 7, totalTime: 50 };
    else if (i === 2) levels[i] = { attempts: 4, correct: 1, totalTime: 40 };
    else levels[i] = { attempts: 0, correct: 0, totalTime: 0 };
  }
  const stats = { _updated_at: 1 };
  for (const domain of %s) {
    stats[domain] = { levels: JSON.parse(JSON.stringify(levels)), weaknesses: {} };
  }
  localStorage.setItem('aiden_english_stats', JSON.stringify(stats));
}""" % json.dumps(ENGLISH_DOMAINS)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Serve the repository root without request-log noise."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def log_message(self, format, *args):  # noqa: A002
        pass


@pytest.fixture(scope="module")
def static_server():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.server_address
    yield f"http://{host}:{port}"

    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


@pytest.fixture
def guardian_page(static_server: str):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )
        page = context.new_page()
        page_errors: list[str] = []
        console_errors: list[str] = []
        request_failures: list[str] = []

        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "requestfailed",
            lambda request: request_failures.append(
                f"{request.url}: {request.failure}"
            ),
        )
        page.on(
            "console",
            lambda msg: (
                console_errors.append(msg.text) if msg.type == "error" else None
            ),
        )

        page.goto(f"{static_server}/domains/reward/guardian/index.html")
        page.wait_for_selector(
            "#difficulty-control-panel", state="attached", timeout=5000
        )

        try:
            yield page, page_errors, console_errors, static_server
            assert request_failures == []
        finally:
            context.close()
            browser.close()


def open_english_difficulty_panel(page: Page) -> None:
    page.click("#tab-english")
    page.wait_for_selector("#difficulty-control-panel", state="visible", timeout=5000)


@pytest.mark.browser
def test_guardian_difficulty_save_keeps_learning_stats_untouched(
    guardian_page: tuple[Page, list[str], list[str], str],
) -> None:
    page, page_errors, console_errors, _ = guardian_page
    page.evaluate("() => localStorage.clear()")
    page.evaluate(SEED_ENGLISH_STATS)
    page.reload()
    open_english_difficulty_panel(page)

    status = page.locator("#difficulty-status")
    expect(status).to_contain_text("자동 (아이 풀이 기록)")
    expect(page.locator("#level-slider")).to_have_value("2")

    stats_before = page.evaluate("() => localStorage.getItem('aiden_english_stats')")

    page.locator("#level-slider").fill("4")
    page.click("#save-btn")
    page.wait_for_timeout(300)

    expect(status).to_contain_text("보호자 설정 Lv.4")
    stored_override = json.loads(
        page.evaluate(
            "() => localStorage.getItem('aiden_english_guardian_base_level_v1')"
        )
    )
    assert stored_override["schemaVersion"] == 1
    assert stored_override["level"] == 4
    assert page.evaluate("() => localStorage.getItem('aiden_english_stats')") == (
        stats_before
    )

    page.click("#reset-difficulty-btn")
    expect(status).to_contain_text("자동 (아이 풀이 기록)")
    assert (
        page.evaluate(
            "() => localStorage.getItem('aiden_english_guardian_base_level_v1')"
        )
        is None
    )
    expect(page.locator("#level-slider")).to_have_value("2")
    assert page.evaluate("() => localStorage.getItem('aiden_english_stats')") == (
        stats_before
    )

    assert page_errors == []
    assert console_errors == []


@pytest.mark.browser
def test_child_engine_uses_guardian_baseline_without_record_rewrite(
    guardian_page: tuple[Page, list[str], list[str], str],
) -> None:
    page, page_errors, console_errors, static_server = guardian_page
    page.evaluate("() => localStorage.clear()")
    page.evaluate(SEED_ENGLISH_STATS)
    page.reload()
    open_english_difficulty_panel(page)

    page.locator("#level-slider").fill("4")
    page.click("#save-btn")
    page.wait_for_timeout(300)
    stats_before = page.evaluate("() => localStorage.getItem('aiden_english_stats')")

    page.goto(f"{static_server}/domains/english/index.html")
    page.wait_for_function("() => typeof window.getBaseDiffLevel === 'function'")
    assert page.evaluate("() => window.getBaseDiffLevel('animals')") == 4
    assert page.evaluate("() => localStorage.getItem('aiden_english_stats')") == (
        stats_before
    )

    page.goto(f"{static_server}/domains/reward/guardian/index.html")
    open_english_difficulty_panel(page)
    page.click("#reset-difficulty-btn")

    page.goto(f"{static_server}/domains/english/index.html")
    page.wait_for_function("() => typeof window.getBaseDiffLevel === 'function'")
    assert page.evaluate("() => window.getBaseDiffLevel('animals')") == 2
    assert page.evaluate("() => localStorage.getItem('aiden_english_stats')") == (
        stats_before
    )

    assert page_errors == []
    assert console_errors == []
