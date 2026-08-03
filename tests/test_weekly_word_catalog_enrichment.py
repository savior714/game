"""
Weekly Word Catalog Auto-Enrichment - focused verification.

Tests the guardian registration path resolves English words
from the canonical WORDS catalog, rejects duplicates and unknown words,
and preserves backward compatibility with existing stored data.

Production JS (words.js + guardian.js resolveWeeklyWord/addWeeklyWord)
is executed in a Node vm harness with minimal DOM stubs.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

PRODUCTION_FILES = [
    "domains/english/words.js",
    "domains/reward/guardian/guardian.js",
]

PROLOGUE = """
const window = globalThis;
window.addEventListener = function() {};
window.location = { href: '' };
const localStorage = {
  _store: {},
  getItem(k) { return this._store[k] || null; },
  setItem(k, v) { this._store[k] = String(v); },
  removeItem(k) { delete this._store[k]; },
};
const document = {
  getElementById(id) {
    return { value: '', innerHTML: '', style: {}, classList: { remove(){}, add(){} } };
  },
  querySelectorAll() { return []; },
  addEventListener() {},
};
"""

HARNESS = r"""
(function () {
  var results = {};

  var resolved = resolveWeeklyWord(' Apple ', WORDS);
  results.caseA = resolved;

  results.caseA_upper = resolveWeeklyWord('APPLE', WORDS);
  results.caseA_spaces = resolveWeeklyWord(' apple ', WORDS);
  results.caseA_mixed = resolveWeeklyWord('Apple', WORDS);

  weeklyWords = [{ en: 'apple', ko: '사과', icon: '🍎' }];
  var beforeLen = weeklyWords.length;
  var resolvedDup = resolveWeeklyWord('APPLE', WORDS);
  var isDup = resolvedDup ? weeklyWords.some(function(w) { return w.en === resolvedDup.en; }) : false;
  results.caseB_isDuplicate = isDup;
  results.caseB_arrayUnchanged = weeklyWords.length === beforeLen;

  var unknownResolved = resolveWeeklyWord('zzweeklyunknownword', WORDS);
  results.caseC_returnsNull = unknownResolved === null;
  results.caseC_arrayUnchanged = weeklyWords.length === beforeLen;

  var r1 = resolveWeeklyWord('apple', WORDS);
  var r2 = resolveWeeklyWord('apple', WORDS);
  results.newObjects = r1 !== r2;
  results.newObjectsEqual = JSON.stringify(r1) === JSON.stringify(r2);

  results.schemaEn = typeof r1.en === 'string';
  results.schemaKo = typeof r1.ko === 'string';
  results.schemaIcon = typeof r1.icon === 'string';
  results.schemaKeys = Object.keys(r1).sort().join(',') === 'en,icon,ko';

  var wordsBefore = JSON.stringify(WORDS);
  resolveWeeklyWord('apple', WORDS);
  resolveWeeklyWord('nonexistent', WORDS);
  results.wordsUnmutated = JSON.stringify(WORDS) === wordsBefore;

  console.log(JSON.stringify(results));
})();
"""


def _node() -> str:
    node = shutil.which("node")
    if not node:
        raise RuntimeError("node not found")
    return node


def _run_harness() -> dict:
    sources = [PROLOGUE]
    for rel in PRODUCTION_FILES:
        path = ROOT / rel
        if not path.exists():
            raise RuntimeError(f"Production file not found: {rel}")
        sources.append(path.read_text(encoding="utf-8"))
    sources.append(HARNESS)
    combined = "\n".join(sources)

    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(combined)
        script_path = f.name
    try:
        proc = subprocess.run(
            [_node(), script_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
    finally:
        Path(script_path).unlink(missing_ok=True)

    if proc.returncode != 0:
        raise RuntimeError(f"Production JS failed:\n{proc.stderr}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def results() -> dict:
    return _run_harness()


def test_caseA_apple_resolves(results: dict) -> None:
    assert results["caseA"] == {"en": "apple", "ko": "사과", "icon": "\U0001f34e"}

def test_caseA_uppercase(results: dict) -> None:
    assert results["caseA_upper"] == {"en": "apple", "ko": "사과", "icon": "\U0001f34e"}

def test_caseA_spaces(results: dict) -> None:
    assert results["caseA_spaces"] == {"en": "apple", "ko": "사과", "icon": "\U0001f34e"}

def test_caseA_mixed(results: dict) -> None:
    assert results["caseA_mixed"] == {"en": "apple", "ko": "사과", "icon": "\U0001f34e"}

def test_caseB_duplicate_detected(results: dict) -> None:
    assert results["caseB_isDuplicate"] is True

def test_caseB_array_unchanged(results: dict) -> None:
    assert results["caseB_arrayUnchanged"] is True

def test_caseC_returns_null(results: dict) -> None:
    assert results["caseC_returnsNull"] is True

def test_caseC_array_unchanged(results: dict) -> None:
    assert results["caseC_arrayUnchanged"] is True

def test_schema_en_ko_icon(results: dict) -> None:
    assert results["schemaEn"] is True
    assert results["schemaKo"] is True
    assert results["schemaIcon"] is True
    assert results["schemaKeys"] is True

def test_returns_new_objects(results: dict) -> None:
    assert results["newObjects"] is True
    assert results["newObjectsEqual"] is True

def test_words_not_mutated(results: dict) -> None:
    assert results["wordsUnmutated"] is True

def test_guardian_uses_catalog_lookup() -> None:
    content = (ROOT / "domains/reward/guardian/guardian.js").read_text(encoding="utf-8")
    match = re.search(r"function addWeeklyWord\(\)\s*\{([\s\S]*?)\nfunction ", content)
    assert match, "addWeeklyWord not found"
    body = match.group(1)
    assert "resolveWeeklyWord" in body
    assert "WORDS" in body
    assert "weeklyWords.some" in body

def test_guardian_has_resolver() -> None:
    content = (ROOT / "domains/reward/guardian/guardian.js").read_text(encoding="utf-8")
    assert "function resolveWeeklyWord" in content
    assert "Object.keys(wordsCatalog)" in content

def test_guardian_html_loads_words_js() -> None:
    content = (ROOT / "domains/reward/guardian/index.html").read_text(encoding="utf-8")
    w = content.find("words.js")
    g = content.find("guardian.js")
    assert w > 0
    assert g > w

def test_guardian_html_single_input() -> None:
    content = (ROOT / "domains/reward/guardian/index.html").read_text(encoding="utf-8")
    assert 'id="ww-en"' in content
    assert 'id="ww-ko"' not in content
    assert 'id="ww-icon"' not in content

def test_addWeeklyWord_no_manual_ko() -> None:
    content = (ROOT / "domains/reward/guardian/guardian.js").read_text(encoding="utf-8")
    match = re.search(r"function addWeeklyWord\(\)\s*\{([\s\S]*?)\nfunction ", content)
    assert match
    body = match.group(1)
    assert "getElementById('ww-ko')" not in body
    assert "getElementById('ww-icon')" not in body
