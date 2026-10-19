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
            "#math-progress-snapshot-section", state="visible", timeout=5000
        )

        try:
            yield page, page_errors, console_errors, static_server
            assert request_failures == []
        finally:
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

    overview = page.locator("#guardian-math-status-overview")
    expect(overview).to_be_visible()
    expect(overview.locator('[data-math-status="NOT_STARTED"] dd')).to_have_text("12개")
    for status in ("MASTERED", "PRACTICING", "NEEDS_REVIEW", "STRUGGLING"):
        expect(overview.locator(f'[data-math-status="{status}"] dd')).to_have_text(
            "0개"
        )
    expect(overview).to_contain_text("실력이 부족하다는 뜻은 아니에요")

    learning_map = page.locator("#guardian-math-learning-map")
    expect(learning_map).to_be_visible()
    expect(
        learning_map.locator('details[data-skill-status="NOT_STARTED"]')
    ).to_have_count(12)
    for operation, count in (("+", 5), ("-", 5), ("×", 2)):
        group = learning_map.locator(f'[data-math-operation="{operation}"]')
        expect(group.locator("details")).to_have_count(count)
        expect(group).to_contain_text(f"숙달 0 / {count}")

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


@pytest.mark.browser
@pytest.mark.parametrize("viewport", [(1280, 800), (800, 1280), (360, 800)])
def test_guardian_math_learning_map_explains_states_without_changing_records(
    tablet_guardian_page: tuple[Page, list[str], list[str], str],
    viewport: tuple[int, int],
) -> None:
    page, page_errors, console_errors, _ = tablet_guardian_page
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})

    before = page.evaluate(
        """() => {
        const now = Date.now();
        const cases = [
          { skillId: 'math.add.within_10', correct: true, count: 4, age: 0 },
          { skillId: 'math.add.within_20.carry', correct: false, count: 3, age: 0 },
          { skillId: 'math.subtract.within_10', correct: true, count: 4, age: 50 * 60 * 60 * 1000 },
          { skillId: 'math.multiply.basic_facts', correct: true, count: 1, age: 0 },
        ];
        const items = cases.flatMap(entry => Array.from({ length: entry.count }, (_, index) => ({
          id: `${entry.skillId}-${index}`,
          skillId: entry.skillId,
          correct: entry.correct,
          attempts: entry.correct ? 1 : 2,
          timestamp: now - entry.age - (entry.count - index) * 1000,
        })));
        localStorage.setItem('aiden_math_learning_evidence_v1', JSON.stringify({
          schemaVersion: 1, lastUpdated: new Date(now).toISOString(), items,
        }));
        MathDailyGoalEngine.initOrGetDailyGoal({
          now, skillCatalog: MathSkills.MATH_SKILLS, skillOrder: MathSkills.MATH_SKILL_ORDER,
        });
        MathDailyGoalEngine.saveGoalPreference('challenge', { now });
        localStorage.setItem('study_rewards', JSON.stringify({ gems: 9, youtube_minutes: 10 }));
        return Object.fromEntries(Object.entries(localStorage));
    }"""
    )
    page.reload()

    overview = page.locator("#guardian-math-status-overview")
    for status, count in (
        ("MASTERED", 1),
        ("PRACTICING", 1),
        ("NEEDS_REVIEW", 1),
        ("STRUGGLING", 1),
        ("NOT_STARTED", 8),
    ):
        expect(overview.locator(f'[data-math-status="{status}"] dd')).to_have_text(
            f"{count}개"
        )
    expect(overview).to_contain_text("12개 학습 내용 중 4개에 풀이 기록")
    expect(overview).to_contain_text("학년 전체의 진도나 점수가 아닙니다")

    learning_map = page.locator("#guardian-math-learning-map")
    for operation, name, skill_count in (
        ("+", "덧셈", 5),
        ("-", "뺄셈", 5),
        ("×", "곱셈", 2),
    ):
        group = learning_map.get_by_role("region", name=f"{name} 학습 현황")
        expect(group).to_have_attribute("data-math-operation", operation)
        expect(group.locator("details")).to_have_count(skill_count)
    rendered_ids = learning_map.locator("details").evaluate_all(
        "elements => elements.map(element => element.dataset.skillId)"
    )
    catalog_ids = page.evaluate("() => Object.keys(MathSkills.MATH_SKILLS)")
    assert sorted(rendered_ids) == sorted(catalog_ids)

    struggling = learning_map.locator('[data-skill-id="math.add.within_20.carry"]')
    expect(struggling).to_have_attribute("data-skill-status", "STRUGGLING")
    expect(struggling.locator("summary")).to_contain_text("도움이 필요해요")
    struggling.locator("summary").click()
    expect(struggling.get_by_text("0 / 3 정답", exact=True)).to_be_visible()
    struggling.locator("summary").press("Enter")
    expect(struggling).not_to_have_attribute("open", "")

    mastered = learning_map.locator('[data-skill-id="math.add.within_10"]')
    mastered.locator("summary").focus()
    mastered.locator("summary").press("Enter")
    expect(mastered.get_by_text("4 / 4 정답", exact=True)).to_be_visible()
    expect(mastered.get_by_text("2022-2수01-05", exact=True)).to_be_visible()

    bounds = page.locator("#math-progress-snapshot-section").evaluate(
        """section => Array.from(section.querySelectorAll('summary, dl, h4, h5')).map(element => {
            const rect = element.getBoundingClientRect();
            return { left: rect.left, right: rect.right };
        })"""
    )
    assert all(bound["left"] >= 0 and bound["right"] <= viewport[0] for bound in bounds)

    # Opening explanations, resizing and reloading must not fabricate learning or rewards.
    page.reload()
    expect(page.locator("#guardian-math-status-overview")).to_be_visible()
    after = page.evaluate("() => Object.fromEntries(Object.entries(localStorage))")
    assert after == before
    assert page_errors == []
    assert console_errors == []
