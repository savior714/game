"""Focused contract for the 8/7 spelling-test English definitions."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEFINITIONS_JS = ROOT / "domains/english/weekly-word-definitions.js"
INDEX_HTML = ROOT / "domains/english/index.html"

EXPECTED_DEFINITIONS = {
    "amount": "how much of something there is",
    "material": "a solid substance such as wood, plastic, or metal",
    "space": "an empty area that is available to be used",
    "example": "something that shows what a group of things is like",
    "easily": "without problems or difficulties",
    "forms": "the shape or appearance of something",
    "planet": "a large object in space that moves around a star",
    "tasty": "dilicious ; having a pleasing flavor",
    "antarctica": "the continent that surrounds the South Pole",
    "survive": "to continue to live and grow",
}


def _node() -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required for the production JavaScript harness")
    return node


def test_definition_catalog_and_question_enrichment_are_exact() -> None:
    harness = f"""
const window = globalThis;
function buildQuestion(type, word) {{
  if (type === 'spelling') return {{ type, hint: word[1], word: word[0] }};
  if (type === 'sentence') return {{ type, koHint: word[1], word: word[0] }};
  return {{ type, main: word[1], word: word[0] }};
}}
{DEFINITIONS_JS.read_text(encoding='utf-8')}
const amount = ['amount', '양', '📊', 2];
const apple = ['apple', '사과', '🍎', 0];
console.log(JSON.stringify({{
  batchId: EnglishWeeklyWordDefinitions.batchId,
  definitions: EnglishWeeklyWordDefinitions.all,
  normalizedLookup: EnglishWeeklyWordDefinitions.get(' Antarctica '),
  spelling: buildQuestion('spelling', amount),
  sentence: buildQuestion('sentence', amount),
  typing: buildQuestion('typing', amount),
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

    assert payload["batchId"] == "2026-08-07"
    assert payload["definitions"] == EXPECTED_DEFINITIONS
    assert payload["normalizedLookup"] == EXPECTED_DEFINITIONS["antarctica"]
    assert payload["spelling"]["hint"] == EXPECTED_DEFINITIONS["amount"]
    assert payload["sentence"]["koHint"] == EXPECTED_DEFINITIONS["amount"]
    assert payload["typing"]["main"] == EXPECTED_DEFINITIONS["amount"]
    assert payload["typing"]["englishDefinition"] == EXPECTED_DEFINITIONS["amount"]
    assert payload["unmapped"] == {"type": "typing", "main": "사과", "word": "apple"}


def test_definition_script_loads_between_engine_and_ui() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    engine_pos = html.index('<script src="engine.js"></script>')
    definitions_pos = html.index('<script src="weekly-word-definitions.js"></script>')
    ui_pos = html.index('<script src="ui.js"></script>')
    assert engine_pos < definitions_pos < ui_pos
