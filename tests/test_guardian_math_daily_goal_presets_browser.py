"""Browser E2E verification for Guardian Math Daily Goal Presets v1."""

from __future__ import annotations

import http.server
import json
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent


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
def tablet_guardian_page(static_server: str):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        # Galaxy Tab S10 landscape viewport baseline
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )
        page = context.new_page()
        page_errors: list[str] = []
        console_errors: list[str] = []

        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "console",
            lambda msg: (
                console_errors.append(msg.text) if msg.type == "error" else None
            ),
        )

        page.goto(f"{static_server}/domains/reward/guardian/index.html")
        page.wait_for_selector(
            "#math-daily-goal-presets-section", state="visible", timeout=5000
        )

        yield page, page_errors, console_errors, static_server

        context.close()
        browser.close()


@pytest.mark.browser
def test_guardian_math_presets_default_and_selection_persistence(
    tablet_guardian_page: tuple[Page, list[str], list[str], str],
) -> None:
    page, page_errors, console_errors, static_server = tablet_guardian_page

    # Fresh state: clear storage
    page.evaluate("() => localStorage.clear()")
    page.reload()
    page.wait_for_selector(
        "#math-daily-goal-presets-section", state="visible", timeout=5000
    )

    # 1. Verify default preset is standard (5)
    btn_standard = page.locator("#preset-btn-standard")
    btn_light = page.locator("#preset-btn-light")
    btn_challenge = page.locator("#preset-btn-challenge")

    expect(btn_standard).to_have_attribute("aria-pressed", "true")
    expect(btn_light).to_have_attribute("aria-pressed", "false")
    expect(btn_challenge).to_have_attribute("aria-pressed", "false")

    # 2. Select light (3)
    btn_light.click()
    page.wait_for_timeout(300)

    expect(btn_light).to_have_attribute("aria-pressed", "true")
    expect(btn_standard).to_have_attribute("aria-pressed", "false")

    # 3. Verify preference is saved in localStorage
    stored_pref_raw = page.evaluate(
        "() => localStorage.getItem('aiden_math_goal_preference_v1')"
    )
    assert stored_pref_raw is not None
    stored_pref = json.loads(stored_pref_raw)
    assert stored_pref["presetId"] == "light"

    # 4. Zero fake learning data mutation
    stored_stats = page.evaluate("() => localStorage.getItem('aiden_math_stats')")
    assert stored_stats is None

    # 5. Reload and ensure light (3) is still active
    page.reload()
    page.wait_for_selector(
        "#math-daily-goal-presets-section", state="visible", timeout=5000
    )
    expect(page.locator("#preset-btn-light")).to_have_attribute("aria-pressed", "true")
    expect(page.locator("#preset-btn-standard")).to_have_attribute(
        "aria-pressed", "false"
    )

    # 6. Navigate to child Math UI -> new goal created with targetCount = 3
    page.goto(f"{static_server}/domains/math/index.html")
    page.wait_for_selector("#daily-goal-count", state="visible", timeout=5000)

    goal_counter = page.locator("#daily-goal-count")
    expect(goal_counter).to_contain_text("0 / 3")

    stored_goal = page.evaluate(
        "() => JSON.parse(localStorage.getItem('aiden_math_daily_goal_v1'))"
    )
    assert stored_goal["targetCount"] == 3
    assert stored_goal["currentCount"] == 0

    assert page_errors == []
    assert console_errors == []


@pytest.mark.browser
def test_guardian_math_presets_existing_goal_stability(
    tablet_guardian_page: tuple[Page, list[str], list[str], str],
) -> None:
    page, page_errors, console_errors, static_server = tablet_guardian_page

    # Seed existing 2/5 daily goal created today
    page.evaluate(
        """() => {
        const now = Date.now();
        const d = new Date(now);
        const today = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
        const goalData = {
          schemaVersion: 1,
          date: today,
          goalId: `goal-${today}-math.add.within_10-v1`,
          skillId: 'math.add.within_10',
          skillName: '10 이하의 덧셈',
          shortName: '10 이하 덧셈',
          targetCount: 5,
          currentCount: 2,
          completed: false,
          completedAt: null,
          rewardGranted: false,
          rewardReceiptId: `receipt-math-goal-${today}-math.add.within_10-v1`,
          lastUpdated: new Date(now).toISOString()
        };
        localStorage.setItem('aiden_math_daily_goal_v1', JSON.stringify(goalData));
        localStorage.removeItem('aiden_math_goal_preference_v1');
    }"""
    )

    page.reload()
    page.wait_for_selector(
        "#math-daily-goal-presets-section", state="visible", timeout=5000
    )

    # Guardian changes preference to challenge (7)
    page.click("#preset-btn-challenge")
    page.wait_for_timeout(300)

    expect(page.locator("#preset-btn-challenge")).to_have_attribute(
        "aria-pressed", "true"
    )

    # HARD RULE: Existing today goal is NOT mutated or completed prematurely
    stored_goal = page.evaluate(
        "() => JSON.parse(localStorage.getItem('aiden_math_daily_goal_v1'))"
    )
    assert stored_goal["targetCount"] == 5
    assert stored_goal["currentCount"] == 2
    assert stored_goal["completed"] is False
    assert stored_goal["rewardGranted"] is False

    # Check child UI: still shows 2 / 5
    page.goto(f"{static_server}/domains/math/index.html")
    page.wait_for_selector("#daily-goal-count", state="visible", timeout=5000)
    expect(page.locator("#daily-goal-count")).to_contain_text("2 / 5")

    # Next day simulation: init new goal applies challenge (7)
    page.evaluate(
        """() => {
        const tomorrow = Date.now() + 86400000;
        const newGoal = MathDailyGoalEngine.initOrGetDailyGoal({
          now: tomorrow,
          skillCatalog: MathSkills.MATH_SKILLS,
          skillOrder: MathSkills.MATH_SKILL_ORDER,
        });
        return newGoal;
    }"""
    )

    stored_tomorrow_goal = page.evaluate(
        "() => JSON.parse(localStorage.getItem('aiden_math_daily_goal_v1'))"
    )
    assert stored_tomorrow_goal["targetCount"] == 7
    assert stored_tomorrow_goal["currentCount"] == 0

    assert page_errors == []
    assert console_errors == []


@pytest.mark.browser
def test_guardian_subject_tabs_legacy_isolation(
    tablet_guardian_page: tuple[Page, list[str], list[str], str],
) -> None:
    page, page_errors, console_errors, _ = tablet_guardian_page

    presets_section = page.locator("#math-daily-goal-presets-section")
    diff_panel = page.locator("#difficulty-control-panel")
    preview_section = page.locator("#preview-section")

    # 1. In Math tab:
    # Presets section is visible, difficulty panel & preview are hidden
    expect(presets_section).to_be_visible()
    expect(diff_panel).to_be_hidden()
    expect(preview_section).to_be_hidden()

    # 2. Switch to English tab:
    # Presets section is hidden, difficulty panel & preview are visible
    page.click("#tab-english")
    expect(presets_section).to_be_hidden()
    expect(diff_panel).to_be_visible()
    expect(preview_section).to_be_visible()

    # 3. Switch to Korean tab:
    page.click("#tab-korean")
    expect(presets_section).to_be_hidden()
    expect(diff_panel).to_be_visible()
    expect(preview_section).to_be_visible()

    # 4. Switch to Science tab:
    page.click("#tab-science")
    expect(presets_section).to_be_hidden()
    expect(diff_panel).to_be_visible()
    expect(preview_section).to_be_visible()

    # 5. Switch back to Math tab:
    page.click("#tab-math")
    expect(presets_section).to_be_visible()
    expect(diff_panel).to_be_hidden()
    expect(preview_section).to_be_hidden()

    assert page_errors == []
    assert console_errors == []
