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


def test_definition_script_loads_between_engine_and_ui() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    engine_pos = html.index('<script src="engine.js"></script>')
    definitions_pos = html.index('<script src="weekly-word-definitions.js"></script>')
    ui_pos = html.index('<script src="ui.js"></script>')
    assert engine_pos < definitions_pos < ui_pos
