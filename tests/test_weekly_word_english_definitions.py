"""Focused contract for the 8/7 spelling-test English definitions."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STORE_JS = ROOT / "domains/english/weekly-vocabulary-store.js"
DEFINITIONS_JS = ROOT / "domains/english/weekly-word-definitions.js"
INDEX_HTML = ROOT / "domains/english/index.html"
PROGRESS_JS = ROOT / "shared/domain/progress-engine.js"
WORDS_JS = ROOT / "domains/english/words.js"
ADVANCED_JS = ROOT / "domains/english/advanced-questions.js"
ENGINE_JS = ROOT / "domains/english/engine.js"

EXPECTED_DEFINITIONS = {
    "across": "from one side to the other side",
    "surround": "to be on all sides",
    "relaxing": "helping you to rest",
    "peaceful": "calm and not violent",
    "mystery": "a puzzle or secret",
    "clear": "see-through",
    "bottom": "the lowest part of something",
    "explore": "to look around and discover",
    "calm": "not moving much",
    "imagine": "to picture in your mind",
}


def _node() -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required for the production JavaScript harness")
    return node


def test_definition_catalog_and_question_enrichment_are_exact() -> None:
    harness = f"""
const window = globalThis;
{STORE_JS.read_text(encoding="utf-8")}
function buildQuestion(type, word) {{
  if (type === 'spelling') return {{ type, hint: word[1], word: word[0] }};
  if (type === 'sentence') return {{ type, koHint: word[1], word: word[0] }};
  return {{ type, main: word[1], word: word[0] }};
}}
{DEFINITIONS_JS.read_text(encoding="utf-8")}
const across = ['across', '가로질러', '↔️', 1];
const apple = ['apple', '사과', '🍎', 0];
console.log(JSON.stringify({{
  batchId: EnglishWeeklyWordDefinitions.batchId,
  definitions: EnglishWeeklyWordDefinitions.all,
  normalizedLookup: EnglishWeeklyWordDefinitions.get(' Across '),
  spelling: buildQuestion('spelling', across),
  sentence: buildQuestion('sentence', across),
  typing: buildQuestion('typing', across),
  unmapped: buildQuestion('typing', apple),
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

    assert payload["batchId"] == "2026-09-18"
    assert payload["definitions"] == EXPECTED_DEFINITIONS
    assert payload["normalizedLookup"] == EXPECTED_DEFINITIONS["across"]
    assert payload["spelling"]["hint"] == EXPECTED_DEFINITIONS["across"]
    assert payload["sentence"]["koHint"] == EXPECTED_DEFINITIONS["across"]
    assert payload["typing"]["main"] == EXPECTED_DEFINITIONS["across"]
    assert payload["typing"]["englishDefinition"] == EXPECTED_DEFINITIONS["across"]
    assert payload["unmapped"] == {"type": "typing", "main": "사과", "word": "apple"}


def test_missing_korean_meaning_uses_english_definition_as_prompt() -> None:
    """ko가 없는 주간 단어도 문제 본문(main/hint/koHint)이 비지 않아야 한다.

    학원 시험지 원문만 등록된 주간 단어는 ko가 ''이다. 이때 definition으로
    본문을 채우지 않으면 영어 퀴즈 화면에 문제 내용이 빈 채로 렌더링된다.
    """
    definition = "a strong desire to know or learn"
    harness = f"""
const window = globalThis;
const localStorage = {{
  _store: {{}},
  getItem(k) {{ return Object.prototype.hasOwnProperty.call(this._store, k) ? this._store[k] : null; }},
  setItem(k, v) {{ this._store[k] = String(v); }},
  removeItem(k) {{ delete this._store[k]; }},
  clear() {{ this._store = {{}}; }},
}};
const document = {{ getElementById: () => null }};
{PROGRESS_JS.read_text(encoding="utf-8")}
{WORDS_JS.read_text(encoding="utf-8")}
{ADVANCED_JS.read_text(encoding="utf-8")}
{STORE_JS.read_text(encoding="utf-8")}
{ENGINE_JS.read_text(encoding="utf-8")}
{DEFINITIONS_JS.read_text(encoding="utf-8")}
const definition = {json.dumps(definition)};
const meta = {{
  cat: 'animals',
  academyDescription: definition,
  weeklyItemId: '2026-10-16-curiosity-abc123',
  word: 'curiosity',
  isWeekly: true,
}};
const curiosity = ['curiosity', '', '🔍', 3];
const across = ['across', '', '↔️', 1];
console.log(JSON.stringify({{
  typing: buildQuestion('typing', curiosity, meta),
  spelling: buildQuestion('spelling', curiosity, meta),
  sentence: buildQuestion('sentence', curiosity, meta),
  kor2word: buildQuestion('kor2word', curiosity, meta),
  minimalPair: buildQuestion('minimal_pair', curiosity, meta),
  storedDefinition: buildQuestion('typing', across),
  unmapped: buildQuestion('typing', ['apple', '', '🍎', 0]),
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

    assert payload["typing"]["main"] == definition
    assert payload["spelling"]["hint"] == definition
    assert payload["sentence"]["koHint"] == definition
    assert payload["kor2word"]["main"] == definition
    assert payload["kor2word"]["hint"] is None, (
        "main과 hint에 같은 definition이 중복되면 안 된다"
    )
    assert payload["minimalPair"]["main"] == definition
    assert payload["minimalPair"]["hint"] == "비슷한 철자에 주목하세요!"
    assert payload["storedDefinition"]["main"] == EXPECTED_DEFINITIONS["across"]
    assert payload["unmapped"]["main"] == "", "정의가 없는 단어는 빈 본문을 유지한다"
    assert payload["unmapped"]["word"] == "apple"


def test_definition_script_loads_between_engine_and_ui() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    engine_pos = html.index('<script src="engine.js"></script>')
    definitions_pos = html.index('<script src="weekly-word-definitions.js"></script>')
    ui_pos = html.index('<script src="ui.js"></script>')
    assert engine_pos < definitions_pos < ui_pos
