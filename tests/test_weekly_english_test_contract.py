"""Focused regression contract for English Weekly Word Test vertical slice."""

from __future__ import annotations

import http.server
import json
from pathlib import Path
import shutil
import socketserver
import subprocess
import threading

from playwright.sync_api import Page, expect, sync_playwright
import pytest

ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "index.html"
ENGLISH_INDEX_HTML = ROOT / "domains/english/index.html"
WEEKLY_TEST_INDEX_HTML = ROOT / "domains/english/weekly-test/index.html"
WEEKLY_TEST_ENGINE_JS = ROOT / "domains/english/weekly-test/weekly-test-engine.js"
WEEKLY_TEST_UI_JS = ROOT / "domains/english/weekly-test/weekly-test-ui.js"
DEFINITIONS_JS = ROOT / "domains/english/weekly-word-definitions.js"


def _node() -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required for JavaScript contract tests")
    return node


def test_main_and_english_pages_have_direct_weekly_test_links() -> None:
    main_html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'href="./domains/english/weekly-test/index.html"' in main_html
    assert "주간 영단어 시험" in main_html

    english_html = ENGLISH_INDEX_HTML.read_text(encoding="utf-8")
    assert 'href="weekly-test/index.html"' in english_html

    weekly_test_html = WEEKLY_TEST_INDEX_HTML.read_text(encoding="utf-8")
    assert 'href="../../../index.html"' in weekly_test_html
    assert "홈으로" in weekly_test_html


def test_weekly_test_html_contract() -> None:
    content = WEEKLY_TEST_INDEX_HTML.read_text(encoding="utf-8")

    # 불필요한 구 워크플로 화면 및 버튼 제거 검증
    assert 'id="start-screen"' not in content
    assert 'id="review-screen"' not in content
    assert 'id="prev-btn"' not in content
    assert 'id="retry-wrong-btn"' not in content

    # 필수 신규 요소 존재 검증
    assert 'id="test-screen"' in content
    assert 'id="answer-input"' in content
    assert 'id="check-btn"' in content
    assert 'id="next-btn"' in content
    assert 'id="feedback-box"' in content
    assert 'id="spelling-diff-container"' in content
    assert 'id="result-screen"' in content
    assert 'id="result-restart-btn"' in content

    # 학습 evidence 스크립트 연결 검증
    assert "milestone-tracker.js" in content
    assert "daily-streak.js" in content
    assert "diversity-reward.js" in content


def test_weekly_test_engine_normalization_and_grading() -> None:
    harness = f"""
const window = globalThis;
{DEFINITIONS_JS.read_text(encoding="utf-8")}
{WEEKLY_TEST_ENGINE_JS.read_text(encoding="utf-8")}

const Engine = window.WeeklyTestEngine;
const item = {{ id: 'across', answer: 'across', prompt: 'from one side to the other side' }};

const results = {{
  normUpper: Engine.normalizeAnswer('  ACROSS  '),
  normNFKC: Engine.normalizeAnswer('\\uff41\\uff43\\uff52\\uff4f\\uff53\\uff53'),
  normSpaces: Engine.normalizeAnswer('a   cross'),
  gradeExact: Engine.gradeAnswer(item, 'across'),
  gradeUpper: Engine.gradeAnswer(item, 'ACROSS'),
  gradeSpaces: Engine.gradeAnswer(item, '  across  '),
  gradeNFKC: Engine.gradeAnswer(item, '\\uff41\\uff43\\uff52\\uff4f\\uff53\\uff53'),
  gradeTypoExtra: Engine.gradeAnswer(item, 'accross'),
  gradeTypoSub: Engine.gradeAnswer(item, 'acrozz'),
  gradeTypoMissing: Engine.gradeAnswer(item, 'acros'),
  gradeEmpty: Engine.gradeAnswer(item, '   '),
}};
console.log(JSON.stringify(results));
"""
    result = subprocess.run(
        [_node(), "-e", harness],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    payload = json.loads(result.stdout)

    assert payload["normUpper"] == "across"
    assert payload["normNFKC"] == "across"
    assert payload["normSpaces"] == "a cross"
    assert payload["gradeExact"] is True
    assert payload["gradeUpper"] is True
    assert payload["gradeSpaces"] is True
    assert payload["gradeNFKC"] is True
    assert payload["gradeTypoExtra"] is False
    assert payload["gradeTypoSub"] is False
    assert payload["gradeTypoMissing"] is False
    assert payload["gradeEmpty"] is False


def test_weekly_test_engine_spelling_diff_deterministic() -> None:
    harness = f"""
const window = globalThis;
{DEFINITIONS_JS.read_text(encoding="utf-8")}
{WEEKLY_TEST_ENGINE_JS.read_text(encoding="utf-8")}

const Engine = window.WeeklyTestEngine;

const exactDiff = Engine.computeSpellingDiff('across', 'across');
const subDiff = Engine.computeSpellingDiff('mistery', 'mystery');
const extraDiff = Engine.computeSpellingDiff('accross', 'across');
const missingDiff = Engine.computeSpellingDiff('suround', 'surround');

console.log(JSON.stringify({{
  exactDiff,
  subDiff,
  extraDiff,
  missingDiff,
}}));
"""
    result = subprocess.run(
        [_node(), "-e", harness],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    payload = json.loads(result.stdout)

    # 1. exact match
    exact = payload["exactDiff"]
    assert all(op["type"] == "match" for op in exact)
    assert "".join(op["char"] for op in exact) == "across"

    # 2. substitution ('mistery' vs 'mystery')
    sub = payload["subDiff"]
    sub_ops = [op for op in sub if op["type"] == "substitution"]
    assert len(sub_ops) == 1
    assert sub_ops[0]["givenChar"] == "i"
    assert sub_ops[0]["expectedChar"] == "y"

    # 3. extra letter ('accross' vs 'across')
    extra = payload["extraDiff"]
    extra_ops = [op for op in extra if op["type"] == "extra"]
    assert len(extra_ops) == 1
    assert extra_ops[0]["char"] == "c"

    # 4. missing letter ('suround' vs 'surround')
    missing = payload["missingDiff"]
    missing_ops = [op for op in missing if op["type"] == "missing"]
    assert len(missing_ops) == 1
    assert missing_ops[0]["char"] == "r"


def test_weekly_test_engine_session_and_shuffle() -> None:
    harness = f"""
const window = globalThis;
{DEFINITIONS_JS.read_text(encoding="utf-8")}
{WEEKLY_TEST_ENGINE_JS.read_text(encoding="utf-8")}

const Engine = window.WeeklyTestEngine;
const testSet = Engine.buildTestSet();
const session1 = Engine.createSession(testSet, {{ shuffle: true }});
const session2 = Engine.createSession(testSet, {{ shuffle: false }});

console.log(JSON.stringify({{
  totalItems: testSet.items.length,
  session1Count: session1.items.length,
  session1Ids: session1.items.map(it => it.id),
  session2Ids: session2.items.map(it => it.id),
  originalIds: testSet.items.map(it => it.id),
  status: session1.status,
  currentIndex: session1.currentIndex,
}}));
"""
    result = subprocess.run(
        [_node(), "-e", harness],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    payload = json.loads(result.stdout)

    assert payload["totalItems"] == 10
    assert payload["session1Count"] == 10
    assert payload["status"] == "in_progress"
    assert payload["currentIndex"] == 0

    # 10개 단어가 중복/누락 없이 모두 존재하는지 검증
    orig_set = set(payload["originalIds"])
    s1_set = set(payload["session1Ids"])
    assert orig_set == s1_set
    assert len(payload["session1Ids"]) == 10

    # shuffle: false 시 원본 순서 유지
    assert payload["session2Ids"] == payload["originalIds"]


def test_weekly_test_ui_composing_and_guard_contracts() -> None:
    ui_code = WEEKLY_TEST_UI_JS.read_text(encoding="utf-8")

    # IME composition 방어
    assert "isComposing" in ui_code
    assert "keyCode === 229" in ui_code

    # 더블 엔터 / 중복 제출 방어
    assert "isSubmitting" in ui_code

    # auto-next 타이머 정리 누수 방지
    assert "clearAutoNextTimer" in ui_code

    # diff 렌더링 시 innerHTML 사용자 입력 interpolation 금지
    assert "createElement" in ui_code
    assert "textContent" in ui_code


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format, *args):
        pass


@pytest.fixture(scope="module")
def static_server():
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("127.0.0.1", 0), QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    yield f"http://{host}:{port}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )
        browser_page = context.new_page()
        yield browser_page
        context.close()
        browser.close()


def test_weekly_test_browser_flow(static_server: str, page: Page) -> None:
    page_errors: list[str] = []
    console_errors: list[str] = []
    failed_requests: list[str] = []

    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on(
        "console",
        lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on(
        "requestfailed",
        lambda req: failed_requests.append(f"{req.url} {req.failure}"),
    )

    # 1. 메인 진입 후 주간 영단어 시험 카드 클릭
    page.goto(f"{static_server}/index.html")
    weekly_card = page.locator('a[href="./domains/english/weekly-test/index.html"]')
    expect(weekly_card).to_be_visible()
    weekly_card.click()

    # 2. weekly-test 진입 및 1번 문제 즉시 노출 & autofocus
    page.wait_for_selector("#test-screen", state="visible")
    expect(page.locator("#q-number")).to_have_text("1 / 10")
    input_el = page.locator("#answer-input")
    expect(input_el).to_be_visible()
    expect(input_el).to_be_focused()

    # 3. 오답 입력 -> diff 시각화 및 자동 이동 중단
    input_el.fill("completelywrong")
    page.locator("#check-btn").click()

    expect(page.locator("#feedback-box")).to_be_visible()
    expect(page.locator("#feedback-wrong")).to_be_visible()
    expect(page.locator("#spelling-diff-container")).to_be_visible()
    expect(page.locator("#next-btn")).to_be_visible()

    # 4. 수동 다음 문제 클릭
    page.locator("#next-btn").click()
    expect(page.locator("#q-number")).to_have_text("2 / 10")

    # 5. 나머지 9문제 정답 입력 (자동 이동)
    for q_idx in range(2, 11):
        expect(input_el).to_be_visible()
        curr_answer = page.evaluate(
            "() => { const s = WeeklyTestEngine.loadSession(); return s.items[s.currentIndex].answer; }"
        )
        input_el.fill(curr_answer)
        page.locator("#check-btn").click()
        if q_idx < 10:
            page.wait_for_function(
                f"() => WeeklyTestEngine.loadSession().currentIndex === {q_idx}",
                timeout=5000,
            )

    # 6. 결과 화면 도달 및 점수 확인
    expect(page.locator("#result-screen")).to_be_visible(timeout=5000)
    expect(page.locator("#result-score")).to_have_text("9 / 10")
    expect(page.locator("#wrong-section")).to_be_visible()

    # 7. 시험 다시 보기
    restart_btn = page.locator("#result-restart-btn")
    expect(restart_btn).to_be_visible()
    restart_btn.click()

    expect(page.locator("#test-screen")).to_be_visible()
    expect(page.locator("#q-number")).to_have_text("1 / 10")
    expect(input_el).to_be_focused()

    assert len(page_errors) == 0, f"page errors: {page_errors}"
    assert len(console_errors) == 0, f"console errors: {console_errors}"
    assert len(failed_requests) == 0, f"failed requests: {failed_requests}"
