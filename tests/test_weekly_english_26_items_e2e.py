"""Focused regression contract and browser verification for 26-item weekly vocabulary.

Verifies:
1. Weekly Test engine accepts 26 items without truncation or item loss.
2. Weekly Test session preserves all 26 item identities regardless of shuffle order.
3. General English consumer loads all 26 items into its active reinforcement pool.
4. Playwright browser flow runs a complete 26-item test session from '1 / 26' to '26 / 26'.
"""

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
STORE_JS = ROOT / "domains/english/weekly-vocabulary-store.js"
DEFINITIONS_JS = ROOT / "domains/english/weekly-word-definitions.js"
TEST_ENGINE_JS = ROOT / "domains/english/weekly-test/weekly-test-engine.js"
PROGRESS_JS = ROOT / "shared/domain/progress-engine.js"
WORDS_JS = ROOT / "domains/english/words.js"
ADVANCED_JS = ROOT / "domains/english/advanced-questions.js"
ENGINE_JS = ROOT / "domains/english/engine.js"

CANONICAL_26_ITEMS = [
    {
        "word": "across",
        "academyDescription": "from one side to the other side",
        "ko": "가로질러",
        "icon": "↔️",
    },
    {
        "word": "surround",
        "academyDescription": "to be on all sides",
        "ko": "둘러싸다",
        "icon": "🔄",
    },
    {
        "word": "relaxing",
        "academyDescription": "helping you to rest",
        "ko": "편안한",
        "icon": "🛋️",
    },
    {
        "word": "peaceful",
        "academyDescription": "calm and not violent",
        "ko": "평화로운",
        "icon": "🕊️",
    },
    {
        "word": "mystery",
        "academyDescription": "a puzzle or secret",
        "ko": "수수께끼",
        "icon": "🧩",
    },
    {
        "word": "clear",
        "academyDescription": "see-through",
        "ko": "투명한",
        "icon": "🪟",
    },
    {
        "word": "bottom",
        "academyDescription": "the lowest part of something",
        "ko": "바닥",
        "icon": "⬇️",
    },
    {
        "word": "explore",
        "academyDescription": "to look around and discover",
        "ko": "탐험하다",
        "icon": "🧭",
    },
    {
        "word": "calm",
        "academyDescription": "not moving much",
        "ko": "고요한",
        "icon": "🧘",
    },
    {
        "word": "imagine",
        "academyDescription": "to picture in your mind",
        "ko": "상상하다",
        "icon": "💭",
    },
    {
        "word": "courage",
        "academyDescription": "the ability to do something frightening",
        "ko": "용기",
        "icon": "🦁",
    },
    {
        "word": "brilliant",
        "academyDescription": "exceptionally clever or talented",
        "ko": "눈부신",
        "icon": "✨",
    },
    {
        "word": "harvest",
        "academyDescription": "the process of gathering crops",
        "ko": "수확",
        "icon": "🌾",
    },
    {
        "word": "whisper",
        "academyDescription": "to speak very softly",
        "ko": "속삭이다",
        "icon": "🤫",
    },
    {
        "word": "journey",
        "academyDescription": "an act of traveling from one place to another",
        "ko": "여행",
        "icon": "🧳",
    },
    {
        "word": "ancient",
        "academyDescription": "belonging to the very distant past",
        "ko": "고대의",
        "icon": "🏺",
    },
    {
        "word": "treasure",
        "academyDescription": "a quantity of precious items",
        "ko": "보물",
        "icon": "💎",
    },
    {
        "word": "shelter",
        "academyDescription": "a place giving temporary protection",
        "ko": "대피소",
        "icon": "🏠",
    },
    {
        "word": "shadow",
        "academyDescription": "a dark area produced by a body",
        "ko": "그림자",
        "icon": "👥",
    },
    {
        "word": "glance",
        "academyDescription": "take a brief or hurried look",
        "ko": "힐끗 보다",
        "icon": "👀",
    },
    {
        "word": "furious",
        "academyDescription": "extremely angry",
        "ko": "몹시 화난",
        "icon": "😡",
    },
    {
        "word": "delight",
        "academyDescription": "great pleasure",
        "ko": "기쁨",
        "icon": "😄",
    },
    {
        "word": "comfort",
        "academyDescription": "a state of physical ease",
        "ko": "안락",
        "icon": "☕",
    },
    {
        "word": "brave",
        "academyDescription": "ready to face danger",
        "ko": "용감한",
        "icon": "🛡️",
    },
    {
        "word": "gentle",
        "academyDescription": "mild in temperament or behavior",
        "ko": "부드러운",
        "icon": "🌸",
    },
    {
        "word": "honest",
        "academyDescription": "free of deceit and truthful",
        "ko": "정직한",
        "icon": "🤝",
    },
]

CANONICAL_26_SET = {
    "schemaVersion": 1,
    "setId": "2026-11-06",
    "testDate": "2026-11-06",
    "title": "2026-11-06 주간 영단어",
    "items": [
        {
            **it,
            "id": f"2026-11-06-{it['word']}-{i}",
            "itemId": f"2026-11-06-{it['word']}-{i}",
            "answer": it["word"],
            "prompt": it["academyDescription"],
        }
        for i, it in enumerate(CANONICAL_26_ITEMS)
    ],
}


def _node() -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required for JavaScript contract tests")
    return node


def test_weekly_test_engine_26_items_session_and_grading() -> None:
    """Verifies WeeklyTestEngine builds, shuffles, and grades an exact 26-item set without truncation."""
    harness = f"""
const window = globalThis;
const storageMap = {{}};
const localStorage = {{
  getItem(k) {{ return Object.prototype.hasOwnProperty.call(storageMap, k) ? storageMap[k] : null; }},
  setItem(k, v) {{ storageMap[k] = String(v); }},
  removeItem(k) {{ delete storageMap[k]; }}
}};

{STORE_JS.read_text(encoding="utf-8")}
{DEFINITIONS_JS.read_text(encoding="utf-8")}
{TEST_ENGINE_JS.read_text(encoding="utf-8")}

const Store = window.WeeklyVocabularyStore;
const Engine = window.WeeklyTestEngine;

// Hydrate 26 items into store
const set26 = {json.dumps(CANONICAL_26_SET)};
Store.saveCurrentSet(set26);

// Build test set
const testSet = Engine.buildTestSet();
const sessionShuffled = Engine.createSession(testSet, {{ shuffle: true }});
const sessionUnshuffled = Engine.createSession(testSet, {{ shuffle: false }});

// Complete all 26 answers
for (const item of sessionShuffled.items) {{
  sessionShuffled.answers[item.id] = item.answer;
}}
const graded = Engine.gradeSession(testSet, sessionShuffled);

console.log(JSON.stringify({{
  buildTestSetCount: testSet.items.length,
  shuffledCount: sessionShuffled.items.length,
  unshuffledCount: sessionUnshuffled.items.length,
  origIds: testSet.items.map(it => it.id),
  shuffledIds: sessionShuffled.items.map(it => it.id),
  gradedTotal: graded.total,
  gradedCorrect: graded.correct,
  gradedPercent: Math.round((graded.correct / graded.total) * 100)
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

    # 1. buildTestSet length == 26
    assert payload["buildTestSetCount"] == 26
    # 2. session items length == 26
    assert payload["shuffledCount"] == 26
    assert payload["unshuffledCount"] == 26

    # 3. Item identity set equality (no truncation, no duplicate loss)
    orig_set = set(payload["origIds"])
    shuffled_set = set(payload["shuffledIds"])
    assert len(orig_set) == 26
    assert orig_set == shuffled_set
    assert len(payload["shuffledIds"]) == 26

    # 4. Grading results total == 26
    assert payload["gradedTotal"] == 26
    assert payload["gradedCorrect"] == 26
    assert payload["gradedPercent"] == 100


def test_general_english_consumer_loads_all_26_items_into_pool() -> None:
    """Verifies General English quiz engine loads all 26 words into selection pool without truncating."""
    harness = f"""
const window = globalThis;
const storageMap = {{}};
const localStorage = {{
  getItem(k) {{ return Object.prototype.hasOwnProperty.call(storageMap, k) ? storageMap[k] : null; }},
  setItem(k, v) {{ storageMap[k] = String(v); }},
  removeItem(k) {{ delete storageMap[k]; }}
}};

{STORE_JS.read_text(encoding="utf-8")}
{DEFINITIONS_JS.read_text(encoding="utf-8")}
{TEST_ENGINE_JS.read_text(encoding="utf-8")}
{PROGRESS_JS.read_text(encoding="utf-8")}
{WORDS_JS.read_text(encoding="utf-8")}
{ADVANCED_JS.read_text(encoding="utf-8")}
{ENGINE_JS.read_text(encoding="utf-8")}

const Store = window.WeeklyVocabularyStore;
const set26 = {json.dumps(CANONICAL_26_SET)};
Store.saveCurrentSet(set26);

loadWeeklyWords();

const poolWords = typeof window.getWeeklyWords === 'function'
  ? window.getWeeklyWords()
  : (window.weeklyWords || []);

console.log(JSON.stringify({{
  poolCount: poolWords.length,
  poolWords: poolWords.map(w => ({{ word: w.word, desc: w.academyDescription || w.desc }}))
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

    assert payload["poolCount"] == 26
    loaded_words = {w["word"] for w in payload["poolWords"]}
    expected_words = {it["word"] for it in CANONICAL_26_SET["items"]}
    assert loaded_words == expected_words


# ── Playwright Browser Verification ─────────────────────────


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


@pytest.mark.browser
def test_weekly_test_browser_26_items_full_flow(static_server: str, page: Page) -> None:
    """Browser E2E test verifying 26-item weekly test session:
    1. Injects 26-item canonical set into localStorage.
    2. Opens weekly-test page and verifies q-number shows '1 / 26'.
    3. Solves each of the 26 items sequentially up to the 26th question.
    4. Reaches result screen showing '26 / 26' and 100%.
    """
    page_errors: list[str] = []
    console_errors: list[str] = []

    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on(
        "console",
        lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
    )

    # 1. Navigate to origin to allow setting localStorage
    page.goto(f"{static_server}/index.html")

    # Inject 26-item canonical set into localStorage
    set_json = json.dumps(CANONICAL_26_SET)
    page.evaluate(f"""() => {{
        localStorage.clear();
        localStorage.setItem('aiden_canonical_weekly_vocabulary_v1', '{set_json}');
    }}""")

    # 2. Open weekly-test page directly
    page.goto(f"{static_server}/domains/english/weekly-test/index.html")
    page.wait_for_selector("#test-screen", state="visible")

    # Verify initial q-number is 1 / 26
    q_number = page.locator("#q-number")
    expect(q_number).to_have_text("1 / 26")

    input_el = page.locator("#answer-input")
    expect(input_el).to_be_visible()

    check_btn = page.locator("#check-btn")

    # 3. Solve all 26 questions
    for q_idx in range(1, 27):
        expect(input_el).to_be_visible()
        expect(input_el).to_be_enabled()
        expect(check_btn).to_be_visible()
        expect(q_number).to_have_text(f"{q_idx} / 26")

        # Get the correct answer for current question from engine session
        curr_answer = page.evaluate(
            "() => { const s = WeeklyTestEngine.loadSession(); return s.items[s.currentIndex].answer; }"
        )
        input_el.fill(curr_answer)
        check_btn.click()

        if q_idx < 26:
            # Wait for auto-advance to next question index
            page.wait_for_function(
                f"() => WeeklyTestEngine.loadSession().currentIndex === {q_idx}",
                timeout=5000,
            )
            expect(input_el).to_be_enabled()
            expect(check_btn).to_be_visible()

    # 4. Result screen shows 26 / 26 and 100%
    expect(page.locator("#result-screen")).to_be_visible(timeout=5000)
    expect(page.locator("#result-score")).to_have_text("26 / 26")
    expect(page.locator("#result-pct")).to_have_text("100%")
    expect(page.locator("#perfect-msg")).to_be_visible()

    # 5. Clean execution: 0 page errors, 0 unhandled console errors
    assert len(page_errors) == 0, f"page errors: {page_errors}"
    assert len(console_errors) == 0, f"console errors: {console_errors}"
