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
    "belly": "the part of the body below the chest and above the legs",
    "glide": "to move easily without stopping and without effort or noise",
    "sleek": "smooth or shiny",
    "waterproof": "not allowing water to go through",
    "huddle": "to move close together",
    "feather": "one of the soft and light parts of a bird that grows from the skin and covers the body",
    "throat": "the space inside the neck down which food and air can go through",
    "waddle": "to walk using short steps while rocking from side to side",
    "fuzzy": "furry, hairy",
    "hunt": "to chase and try to catch and kill an animal or bird for food",
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
const belly = ['belly', '배', '🤰', 1];
const apple = ['apple', '사과', '🍎', 0];
console.log(JSON.stringify({{
  batchId: EnglishWeeklyWordDefinitions.batchId,
  definitions: EnglishWeeklyWordDefinitions.all,
  normalizedLookup: EnglishWeeklyWordDefinitions.get(' Belly '),
  spelling: buildQuestion('spelling', belly),
  sentence: buildQuestion('sentence', belly),
  typing: buildQuestion('typing', belly),
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

    assert payload["batchId"] == "2026-08-14"
    assert payload["definitions"] == EXPECTED_DEFINITIONS
    assert payload["normalizedLookup"] == EXPECTED_DEFINITIONS["belly"]
    assert payload["spelling"]["hint"] == EXPECTED_DEFINITIONS["belly"]
    assert payload["sentence"]["koHint"] == EXPECTED_DEFINITIONS["belly"]
    assert payload["typing"]["main"] == EXPECTED_DEFINITIONS["belly"]
    assert payload["typing"]["englishDefinition"] == EXPECTED_DEFINITIONS["belly"]
    assert payload["unmapped"] == {"type": "typing", "main": "사과", "word": "apple"}


def test_definition_script_loads_between_engine_and_ui() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    engine_pos = html.index('<script src="engine.js"></script>')
    definitions_pos = html.index('<script src="weekly-word-definitions.js"></script>')
    ui_pos = html.index('<script src="ui.js"></script>')
    assert engine_pos < definitions_pos < ui_pos
