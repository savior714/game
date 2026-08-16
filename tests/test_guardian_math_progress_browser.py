"""Browser verification for Guardian Math Progress Snapshot v1 vertical slice."""

from __future__ import annotations

import http.server
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
            "#math-progress-snapshot-section", state="visible", timeout=5000
        )

        yield page, page_errors, console_errors, static_server

        context.close()
        browser.close()


@pytest.mark.browser
def test_guardian_math_progress_empty_state_on_fresh_profile(
    tablet_guardian_page: tuple[Page, list[str], list[str], str],
) -> None:
    page, page_errors, console_errors, _ = tablet_guardian_page

    # Clear any storage to guarantee fresh profile
    page.evaluate("() => localStorage.clear()")
    page.reload()
    page.wait_for_selector(
        "#math-progress-snapshot-section", state="visible", timeout=5000
    )

    section = page.locator("#math-progress-snapshot-section")
    expect(section).to_be_visible()
    expect(section).to_contain_text("수학 학습 진도 스냅샷")
    expect(section).to_contain_text("오늘의 수학 목표")
    expect(section).to_contain_text("아직 기록된 수학 학습 증거가 없습니다")

    assert page_errors == []
    assert console_errors == []


@pytest.mark.browser
def test_guardian_math_progress_snapshot_with_canonical_evidence(
    tablet_guardian_page: tuple[Page, list[str], list[str], str],
) -> None:
    page, page_errors, console_errors, _ = tablet_guardian_page

    # Seed canonical math evidence and daily goal
    page.evaluate(
        """() => {
        const now = Date.now();
        // 1. Math evidence: 4 correct for math.add.within_10 (MASTERED), 3 wrong for math.add.within_20.carry (STRUGGLING)
        const evidenceData = {
          schemaVersion: 1,
          lastUpdated: new Date(now).toISOString(),
          items: [
            { id: 'ev-1', timestamp: now - 4000, skillId: 'math.add.within_10', op: '+', a: 2, b: 3, result: 5, correct: true, attempts: 1 },
            { id: 'ev-2', timestamp: now - 3000, skillId: 'math.add.within_10', op: '+', a: 4, b: 1, result: 5, correct: true, attempts: 1 },
            { id: 'ev-3', timestamp: now - 2000, skillId: 'math.add.within_10', op: '+', a: 5, b: 2, result: 7, correct: true, attempts: 1 },
            { id: 'ev-4', timestamp: now - 1000, skillId: 'math.add.within_10', op: '+', a: 3, b: 3, result: 6, correct: true, attempts: 1 },

            { id: 'ev-5', timestamp: now - 3000, skillId: 'math.add.within_20.carry', op: '+', a: 8, b: 7, result: 15, correct: false, attempts: 2 },
            { id: 'ev-6', timestamp: now - 2000, skillId: 'math.add.within_20.carry', op: '+', a: 9, b: 6, result: 15, correct: false, attempts: 2 },
            { id: 'ev-7', timestamp: now - 1000, skillId: 'math.add.within_20.carry', op: '+', a: 7, b: 5, result: 12, correct: false, attempts: 2 },
          ]
        };
        localStorage.setItem('aiden_math_learning_evidence_v1', JSON.stringify(evidenceData));

        // 2. Daily goal for today
        const today = new Date(now).toISOString().split('T')[0];
        const goalData = {
          schemaVersion: 1,
          date: today,
          goalId: `goal-${today}-math.add.within_10-v1`,
          skillId: 'math.add.within_10',
          skillName: '10 이하의 덧셈',
          shortName: '10 이하 덧셈',
          targetCount: 5,
          currentCount: 4,
          completed: false,
          completedAt: null,
          rewardGranted: false,
          rewardReceiptId: `receipt-math-goal-${today}-math.add.within_10-v1`,
          lastUpdated: new Date(now).toISOString()
        };
        localStorage.setItem('aiden_math_daily_goal_v1', JSON.stringify(goalData));
    }"""
    )

    page.reload()
    page.wait_for_selector(
        "#math-progress-snapshot-section", state="visible", timeout=5000
    )

    section = page.locator("#math-progress-snapshot-section")
    expect(section).to_be_visible()

    # Verify Today Goal
    expect(section).to_contain_text("오늘의 수학 목표")
    expect(section).to_contain_text("10 이하의 덧셈")
    expect(section).to_contain_text("4 / 5 완료")
    expect(section).to_contain_text("도전 중")

    # Verify Attention Priority
    expect(section).to_contain_text("지금 살펴볼 스킬")
    expect(section).to_contain_text("받아올림이 있는 20 이하의 덧셈")
    expect(section).to_contain_text("도움이 필요해요")

    # Verify Mastered Strengths
    expect(section).to_contain_text("잘하고 있어요 (숙달 완료)")
    expect(section).to_contain_text("10 이하 덧셈")

    # Verify Detailed Skill Breakdown
    expect(section).to_contain_text("교육과정 스킬별 학습 현황")
    expect(section).to_contain_text("2022-2수01-05")
    expect(section).to_contain_text("총 4회 시도")
    expect(section).to_contain_text("4 / 4 정답")

    assert page_errors == []
    assert console_errors == []


@pytest.mark.browser
def test_guardian_read_only_guarantee_after_reload(
    tablet_guardian_page: tuple[Page, list[str], list[str], str],
) -> None:
    page, page_errors, console_errors, _ = tablet_guardian_page

    raw_before = page.evaluate(
        "() => localStorage.getItem('aiden_math_learning_evidence_v1')"
    )
    goal_before = page.evaluate(
        "() => localStorage.getItem('aiden_math_daily_goal_v1')"
    )

    # Reload multiple times
    page.reload()
    page.wait_for_selector(
        "#math-progress-snapshot-section", state="visible", timeout=5000
    )
    page.reload()
    page.wait_for_selector(
        "#math-progress-snapshot-section", state="visible", timeout=5000
    )

    raw_after = page.evaluate(
        "() => localStorage.getItem('aiden_math_learning_evidence_v1')"
    )
    goal_after = page.evaluate("() => localStorage.getItem('aiden_math_daily_goal_v1')")

    assert raw_before == raw_after
    assert goal_before == goal_after


@pytest.mark.browser
def test_child_math_ui_does_not_leak_guardian_details(
    tablet_guardian_page: tuple[Page, list[str], list[str], str],
) -> None:
    page, page_errors, console_errors, static_server = tablet_guardian_page

    # Navigate to Math child UI
    page.goto(f"{static_server}/domains/math/index.html")
    page.wait_for_selector("#question", state="visible", timeout=5000)

    body_text = page.locator("body").inner_text()

    # Ensure Guardian-specific taxonomies and labels are not leaked to the child
    assert "도움이 필요해요" not in body_text
    assert "STRUGGLING" not in body_text
    assert "복습할 때예요" not in body_text
    assert "2022-2수01-05" not in body_text
    assert "보호자 전용 진도표" not in body_text

    assert page_errors == []


@pytest.mark.browser
def test_guardian_fail_soft_on_corrupted_storage(
    tablet_guardian_page: tuple[Page, list[str], list[str], str],
) -> None:
    page, page_errors, console_errors, _ = tablet_guardian_page

    # Inject malformed JSON into storage
    page.evaluate(
        """() => {
        localStorage.setItem('aiden_math_learning_evidence_v1', '{"malformed JSON... invalid');
        localStorage.setItem('aiden_math_daily_goal_v1', 'null');
    }"""
    )

    page.reload()
    page.wait_for_selector(
        "#math-progress-snapshot-section", state="visible", timeout=5000
    )

    section = page.locator("#math-progress-snapshot-section")
    expect(section).to_be_visible()
    expect(section).to_contain_text("수학 학습 진도 스냅샷")
    expect(section).to_contain_text("아직 기록된 수학 학습 증거가 없습니다")

    assert page_errors == []
