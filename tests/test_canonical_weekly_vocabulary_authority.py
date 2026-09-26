"""Focused contract for Canonical Weekly Vocabulary Authority.

Verifies:
1. Single Authority: Weekly test and General English read from the identical canonical set.
2. Multi-Sense Identity: Multiple senses sharing the same spelling (e.g., bank/money vs bank/river)
   maintain distinct item identities, generate independent test items, and preserve distinct
   academy descriptions in general English question enrichment.
3. Migration & Fail-soft:
   - Shipped 2026-09-18 set bootstrap on fresh state
   - Idempotence on repeated calls (no duplicates)
   - Malformed legacy JSON resilience
   - Existing canonical truth is never silently overwritten by stale legacy keys
4. Legacy compatibility projection synchronization.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STORE_JS = ROOT / "domains/english/weekly-vocabulary-store.js"
DEFINITIONS_JS = ROOT / "domains/english/weekly-word-definitions.js"
TEST_ENGINE_JS = ROOT / "domains/english/weekly-test/weekly-test-engine.js"
WORDS_JS = ROOT / "domains/english/words.js"
ADVANCED_JS = ROOT / "domains/english/advanced-questions.js"
PROGRESS_JS = ROOT / "shared/domain/progress-engine.js"
ENGINE_JS = ROOT / "domains/english/engine.js"


def _node() -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required for JavaScript contract tests")
    return node


def test_canonical_store_bootstrap_and_idempotence() -> None:
    harness = f"""
const window = globalThis;
const storageMap = {{}};
const localStorage = {{
  getItem(k) {{ return Object.prototype.hasOwnProperty.call(storageMap, k) ? storageMap[k] : null; }},
  setItem(k, v) {{ storageMap[k] = String(v); }},
  removeItem(k) {{ delete storageMap[k]; }}
}};

{STORE_JS.read_text(encoding="utf-8")}

const Store = window.WeeklyVocabularyStore;
const set1 = Store.getCurrentSet();
const count1 = set1.items.length;
const ids1 = set1.items.map(it => it.itemId);

// Repeated call should be idempotent
const set2 = Store.getCurrentSet();
const count2 = set2.items.length;
const ids2 = set2.items.map(it => it.itemId);

console.log(JSON.stringify({{
  schemaVersion: set1.schemaVersion,
  setId: set1.setId,
  count1,
  count2,
  ids1,
  ids2,
  legacyStorage: JSON.parse(storageMap['englishWeeklyWords'] || 'null'),
  canonicalStorage: JSON.parse(storageMap['aiden_canonical_weekly_vocabulary_v1'] || 'null')
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

    assert payload["schemaVersion"] == 1
    assert payload["setId"] == "2026-09-18"
    assert payload["count1"] == 10
    assert payload["count2"] == 10
    assert payload["ids1"] == payload["ids2"]
    assert len(set(payload["ids1"])) == 10  # all unique

    # Legacy projection synchronized
    assert isinstance(payload["legacyStorage"], list)
    assert len(payload["legacyStorage"]) == 10
    assert payload["legacyStorage"][0]["en"] == "across"

    # Canonical storage persisted
    assert payload["canonicalStorage"]["setId"] == "2026-09-18"
    assert len(payload["canonicalStorage"]["items"]) == 10


def test_single_authority_weekly_test_and_general_english() -> None:
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

// 1. Weekly test items
const testSet = window.WeeklyTestEngine.buildTestSet();
const acrossTestItem = testSet.items.find(it => it.answer === 'across');

// 2. General english weekly candidate
loadWeeklyWords();
const acrossWeeklyCandidate = weeklyWords.find(w => (w.word || w.en) === 'across');

// 3. Question generation with across candidate
const acrossMeta = {{
  cat: 'concepts',
  isWeekly: true,
  weeklyItemId: acrossWeeklyCandidate.weeklyItemId,
  word: acrossWeeklyCandidate.word,
  academyDescription: acrossWeeklyCandidate.academyDescription
}};
const acrossQ = buildQuestion('sentence', ['across', '가로질러', '↔️', 1], acrossMeta);

console.log(JSON.stringify({{
  testItem: acrossTestItem,
  weeklyCandidate: acrossWeeklyCandidate,
  question: acrossQ
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

    test_item = payload["testItem"]
    candidate = payload["weeklyCandidate"]
    question = payload["question"]

    # Identical item identity
    assert test_item["id"] == candidate["weeklyItemId"]
    assert test_item["id"] == question["weeklyItemId"]

    # Identical verbatim academy description
    expected_desc = "from one side to the other side"
    assert test_item["prompt"] == expected_desc
    assert candidate["academyDescription"] == expected_desc
    assert question["englishDefinition"] == expected_desc
    assert question["koHint"] == expected_desc


def test_multi_sense_identity_fixture() -> None:
    """Fixture containing two distinct senses of 'bank' (money vs river).

    Verifies:
    - Distinct itemIds
    - Weekly test generates 2 independent questions without prompt collision
    - Session grading treats them independently
    - General English enrichment preserves sense-specific academy description
      without collapsing to a global spelling lookup
    """
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
const customSet = {{
  schemaVersion: 1,
  setId: '2026-multi-sense-test',
  title: 'Multi-Sense Fixture',
  items: [
    Store.createItem('2026-multi-sense-test', {{
      word: 'bank',
      academyDescription: 'a place where people keep money',
      ko: '은행',
      icon: '🏦'
    }}),
    Store.createItem('2026-multi-sense-test', {{
      word: 'bank',
      academyDescription: 'the land beside a river',
      ko: '강둑',
      icon: '🌊'
    }})
  ]
}};
Store.saveCurrentSet(customSet);

// 1. Weekly Test Engine
const testSet = window.WeeklyTestEngine.buildTestSet();
const session = window.WeeklyTestEngine.createSession(testSet, {{ shuffle: false }});

// Answer first bank correctly, second incorrectly
session.answers[testSet.items[0].id] = 'bank';
session.answers[testSet.items[1].id] = 'wrongbank';
const graded = window.WeeklyTestEngine.gradeSession(testSet, session);

// 2. General English Consumer
loadWeeklyWords();
const moneyItem = weeklyWords.find(w => w.academyDescription === 'a place where people keep money');
const riverItem = weeklyWords.find(w => w.academyDescription === 'the land beside a river');

const moneyQ = buildQuestion('sentence', ['bank', '은행', '🏦', 1], {{
  cat: 'places',
  isWeekly: true,
  weeklyItemId: moneyItem.weeklyItemId,
  word: moneyItem.word,
  academyDescription: moneyItem.academyDescription
}});

const riverQ = buildQuestion('sentence', ['bank', '강둑', '🌊', 1], {{
  cat: 'places',
  isWeekly: true,
  weeklyItemId: riverItem.weeklyItemId,
  word: riverItem.word,
  academyDescription: riverItem.academyDescription
}});

console.log(JSON.stringify({{
  item0: customSet.items[0],
  item1: customSet.items[1],
  testSetCount: testSet.items.length,
  testItem0: testSet.items[0],
  testItem1: testSet.items[1],
  gradedResults: graded.results,
  gradedCorrect: graded.correct,
  moneyQDesc: moneyQ.englishDefinition,
  moneyQItemId: moneyQ.weeklyItemId,
  riverQDesc: riverQ.englishDefinition,
  riverQItemId: riverQ.weeklyItemId
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

    # 1. Distinct deterministic item IDs
    item0 = payload["item0"]
    item1 = payload["item1"]
    assert item0["itemId"] != item1["itemId"]
    assert "bank" in item0["itemId"]
    assert "bank" in item1["itemId"]

    # 2. Weekly Test: both questions present and prompts not mixed
    assert payload["testSetCount"] == 2
    assert payload["testItem0"]["id"] == item0["itemId"]
    assert payload["testItem0"]["prompt"] == "a place where people keep money"
    assert payload["testItem1"]["id"] == item1["itemId"]
    assert payload["testItem1"]["prompt"] == "the land beside a river"

    # 3. Independent grading
    assert payload["gradedCorrect"] == 1
    results = payload["gradedResults"]
    assert len(results) == 2
    assert results[0]["id"] == item0["itemId"]
    assert results[0]["correct"] is True
    assert results[1]["id"] == item1["itemId"]
    assert results[1]["correct"] is False

    # 4. General English question enrichment maintains specific sense
    assert payload["moneyQItemId"] == item0["itemId"]
    assert payload["moneyQDesc"] == "a place where people keep money"
    assert payload["riverQItemId"] == item1["itemId"]
    assert payload["riverQDesc"] == "the land beside a river"


def test_migration_resilience_and_no_silent_overwrite() -> None:
    harness = f"""
const window = globalThis;
const storageMap = {{}};
const localStorage = {{
  getItem(k) {{ return Object.prototype.hasOwnProperty.call(storageMap, k) ? storageMap[k] : null; }},
  setItem(k, v) {{ storageMap[k] = String(v); }},
  removeItem(k) {{ delete storageMap[k]; }}
}};

{STORE_JS.read_text(encoding="utf-8")}
const Store = window.WeeklyVocabularyStore;

// 1. Malformed legacy data does not crash app
storageMap['englishWeeklyWords'] = '{{broken json';
const setAfterBrokenLegacy = Store.getCurrentSet();
const brokenLegacySafe = setAfterBrokenLegacy.items.length === 10;

// 2. Once canonical set exists, modifying legacy key must NOT silently overwrite canonical store
storageMap['englishWeeklyWords'] = JSON.stringify([{{ en: 'staleWord', ko: '오래된', icon: '' }}]);
const setAfterStaleLegacy = Store.getCurrentSet();
const stillCanonical = setAfterStaleLegacy.items.some(it => it.word === 'across');
const notStale = !setAfterStaleLegacy.items.some(it => it.word === 'staleWord');

// 3. Malformed canonical storage fails soft to default set
storageMap['aiden_canonical_weekly_vocabulary_v1'] = 'not-json';
const setAfterBrokenCanonical = Store.getCurrentSet();
const brokenCanonicalSafe = setAfterBrokenCanonical.items.length === 10;

console.log(JSON.stringify({{
  brokenLegacySafe,
  stillCanonical,
  notStale,
  brokenCanonicalSafe
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

    assert payload["brokenLegacySafe"] is True
    assert payload["stillCanonical"] is True
    assert payload["notStale"] is True
    assert payload["brokenCanonicalSafe"] is True
