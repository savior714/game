"""Focused regression contract for English Weekly Word Test vertical slice."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

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
