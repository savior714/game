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
GUARDIAN_JS = ROOT / "domains/reward/guardian/guardian.js"


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


def test_guardian_word_admission_and_unknown_words() -> None:
    """Verifies that Guardian admits valid English words even if not in WORDS catalog,
    while enriching known catalog words, and synchronizes to canonical store and SyncEngine.
    """
    harness = f"""
const window = globalThis;
window.alert = function () {{}};
window.confirm = function () {{ return true; }};
window.addEventListener = function () {{}};
if (typeof navigator !== 'undefined') {{
  try {{
    Object.defineProperty(navigator, 'onLine', {{ value: true, configurable: true, writable: true }});
  }} catch (e) {{
    navigator.onLine = true;
  }}
}} else {{
  window.navigator = {{ onLine: true }};
}}
window.Auth = {{
  getUser() {{ return {{ id: 'guardian-user-1' }}; }}
}};
const storageMap = {{}};
const localStorage = {{
  getItem(k) {{ return Object.prototype.hasOwnProperty.call(storageMap, k) ? storageMap[k] : null; }},
  setItem(k, v) {{ storageMap[k] = String(v); }},
  removeItem(k) {{ delete storageMap[k]; }}
}};

let pushedSyncKey = null;
let pushedSyncData = null;
window.SyncEngine = {{
  pushStats(k, v) {{
    pushedSyncKey = k;
    pushedSyncData = v;
  }}
}};

let rpcCalledWith = null;
let serverPayload = null;
window.supabaseClient = {{
  async rpc(fn, args) {{
    if (fn === 'register_weekly_english_set_as_guardian') {{
      rpcCalledWith = args;
      const current = window.WeeklyVocabularyStore.getCurrentSet();
      serverPayload = {{
        schemaVersion: 1,
        setId: current.setId,
        revision: (current.revision || 1) + 1,
        _mutationAuthority: 'server_rpc',
        items: args.p_candidate.items.map(it => ({{
          itemId: `${{current.setId}}_${{it.word}}`,
          word: it.word,
          answer: it.word,
          prompt: it.academyDescription || it.word,
          academyDescription: it.academyDescription || it.word,
          ko: it.ko || '',
          icon: it.icon || ''
        }}))
      }};
      return {{ data: {{ status: 'REGISTERED_REVISION' }}, error: null }};
    }}
    return {{ data: null, error: new Error('Unknown RPC') }};
  }},
  from(tbl) {{
    return {{
      select(cols) {{
        return {{
          eq(col1, val1) {{
            return {{
              eq(col2, val2) {{
                return {{
                  async single() {{
                    return {{ data: {{ payload: serverPayload }}, error: null }};
                  }}
                }};
              }}
            }};
          }}
        }};
      }}
    }};
  }}
}};

const elements = {{}};
window.document = {{
  getElementById(id) {{
    if (!elements[id]) {{
      elements[id] = {{ value: '', innerHTML: '', textContent: '', style: {{}} }};
    }}
    return elements[id];
  }},
  querySelectorAll() {{ return []; }},
  addEventListener() {{}}
}};

{STORE_JS.read_text(encoding="utf-8")}
{WORDS_JS.read_text(encoding="utf-8")}
if (typeof WORDS !== 'undefined') window.WORDS = WORDS;
{GUARDIAN_JS.read_text(encoding="utf-8")}

(async () => {{
  // 1. resolveWeeklyWord resolution tests
  const knownResolved = resolveWeeklyWord('apple', window.WORDS);
  const unknownResolved = resolveWeeklyWord('curiosity', window.WORDS);
  const hyphenResolved = resolveWeeklyWord('well-being', window.WORDS);
  const invalidResolved = resolveWeeklyWord('1234invalid!', window.WORDS);

  // 2. addWeeklyWord for word NOT in WORDS catalog
  document.getElementById('ww-en').value = 'curiosity';
  await addWeeklyWord();

  const canonicalAfterAdd = window.WeeklyVocabularyStore.getCurrentSet();
  const curiosityItem = canonicalAfterAdd.items.find(it => it.word === 'curiosity');

  console.log(JSON.stringify({{
    knownResolved,
    unknownResolved,
    hyphenResolved,
    invalidResolved,
    hasCuriosity: Boolean(curiosityItem),
    curiosityItem,
    pushedSyncKey,
    rpcCalled: Boolean(rpcCalledWith),
    mutationAuthority: canonicalAfterAdd._mutationAuthority
  }}));
}})();
"""
    result = subprocess.run(
        [_node(), "-e", harness],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    payload = json.loads(result.stdout)

    # 1. Catalog enrichment for known word
    assert payload["knownResolved"]["en"] == "apple"
    assert payload["knownResolved"]["ko"] == "사과"
    assert payload["knownResolved"]["icon"] == "🍎"

    # 2. Admission for valid word NOT in WORDS catalog
    assert payload["unknownResolved"]["en"] == "curiosity"
    assert payload["unknownResolved"]["ko"] == ""

    # 3. Hyphenated word admission
    assert payload["hyphenResolved"]["en"] == "well-being"

    # 4. Invalid token rejected
    assert payload["invalidResolved"] is None

    # 5. Successfully added via server RPC and hydrated into canonical store (no generic pushStats)
    assert payload["hasCuriosity"] is True
    assert payload["curiosityItem"]["word"] == "curiosity"
    assert payload["curiosityItem"]["answer"] == "curiosity"
    assert payload["rpcCalled"] is True
    assert payload["pushedSyncKey"] is None
    assert payload["mutationAuthority"] == "server_rpc"


def test_primary_criterion_weekly_set_a_to_b_replacement_and_no_leakage() -> None:
    """PRIMARY CRITERION verification:
    1. Register Set A (1 word in WORDS, 1 word NOT in WORDS, verbatim prompts).
    2. Verify General English and Weekly Test both consume Set A.
    3. Start Weekly Test session on Set A.
    4. Replace with Set B (different words and prompts).
    5. Verify both consumers now use Set B without code changes.
    6. Verify Set A prompts/answers do not remain in current test set.
    7. Verify prior Set A session is identified as stale and discarded cleanly.
    8. Verify spelling test grading and diff behavior on Set B.
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
const Engine = window.WeeklyTestEngine;

// ── STEP 1: Register Set A ──
// 'apple' is in WORDS catalog; 'curiosity' is NOT in WORDS catalog
const setA = {{
  schemaVersion: 1,
  setId: 'set-a-school-week-1',
  title: 'Week 1 School Test',
  items: [
    {{
      answer: 'apple',
      prompt: 'a round fruit with red or green skin',
      ko: '사과',
      icon: '🍎'
    }},
    {{
      answer: 'curiosity',
      prompt: 'a strong desire to know or learn something',
      ko: '호기심',
      icon: '🔍'
    }}
  ]
}};
Store.saveCurrentSet(setA);

// Consumer 1: General English reads Set A
loadWeeklyWords();
const generalEnglishWordsSetA = weeklyWords.slice();

// Consumer 2: Weekly Test reads Set A
const testSetA = Engine.buildTestSet();
const sessionA = Engine.createSession(testSetA, {{ shuffle: false }});
sessionA.answers[testSetA.items[0].id] = 'apple';
Engine.saveSession(sessionA);

// ── STEP 2: Replace with Set B (No code changes, pure runtime replacement) ──
// 'banana' is in WORDS catalog; 'galaxy' is NOT in WORDS catalog
const setB = {{
  schemaVersion: 1,
  setId: 'set-b-school-week-2',
  title: 'Week 2 School Test',
  items: [
    {{
      answer: 'banana',
      prompt: 'a long curved fruit with a yellow skin',
      ko: '바나나',
      icon: '🍌'
    }},
    {{
      answer: 'galaxy',
      prompt: 'a system of millions or billions of stars',
      ko: '은하',
      icon: '🌌'
    }}
  ]
}};
Store.saveCurrentSet(setB);

// Consumer 1: General English reloads and consumes Set B
loadWeeklyWords();
const generalEnglishWordsSetB = weeklyWords.slice();

// Consumer 2: Weekly Test builds Set B
const testSetB = Engine.buildTestSet();

// Stale session validation: previous session was for set-a, now expected set-b
const loadedSessionStale = Engine.loadSession(testSetB.setId);

// Create fresh session for Set B and grade
const sessionB = Engine.createSession(testSetB, {{ shuffle: false }});
sessionB.answers[testSetB.items[0].id] = 'banana';   // correct
sessionB.answers[testSetB.items[1].id] = 'galaxi';   // typo ('i' for 'y')
const gradedB = Engine.gradeSession(testSetB, sessionB);

// Diff test for typo on 'galaxy'
const galaxyDiff = Engine.computeSpellingDiff('galaxi', 'galaxy');

console.log(JSON.stringify({{
  generalEnglishSetA: generalEnglishWordsSetA.map(w => ({{ word: w.word, desc: w.academyDescription }})),
  testSetA: {{
    setId: testSetA.setId,
    items: testSetA.items.map(it => ({{ id: it.id, answer: it.answer, prompt: it.prompt }}))
  }},
  generalEnglishSetB: generalEnglishWordsSetB.map(w => ({{ word: w.word, desc: w.academyDescription }})),
  testSetB: {{
    setId: testSetB.setId,
    items: testSetB.items.map(it => ({{ id: it.id, answer: it.answer, prompt: it.prompt }}))
  }},
  loadedSessionStale,
  gradedB: {{
    total: gradedB.total,
    correct: gradedB.correct,
    results: gradedB.results
  }},
  galaxyDiff
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

    # 1. Set A consumed by both
    eng_a = payload["generalEnglishSetA"]
    assert len(eng_a) == 2
    assert {w["word"] for w in eng_a} == {"apple", "curiosity"}
    assert {w["desc"] for w in eng_a} == {
        "a round fruit with red or green skin",
        "a strong desire to know or learn something",
    }

    test_a = payload["testSetA"]
    assert test_a["setId"] == "set-a-school-week-1"
    assert len(test_a["items"]) == 2
    assert {it["answer"] for it in test_a["items"]} == {"apple", "curiosity"}
    apple_item_a = next(it for it in test_a["items"] if it["answer"] == "apple")
    assert apple_item_a["prompt"] == "a round fruit with red or green skin"
    curiosity_item_a = next(it for it in test_a["items"] if it["answer"] == "curiosity")
    assert curiosity_item_a["prompt"] == "a strong desire to know or learn something"

    # 2. Set B replaces Set A without code changes
    eng_b = payload["generalEnglishSetB"]
    assert len(eng_b) == 2
    assert {w["word"] for w in eng_b} == {"banana", "galaxy"}
    assert not any(w["word"] in ("apple", "curiosity") for w in eng_b)

    test_b = payload["testSetB"]
    assert test_b["setId"] == "set-b-school-week-2"
    assert len(test_b["items"]) == 2
    assert {it["answer"] for it in test_b["items"]} == {"banana", "galaxy"}
    assert not any(it["answer"] in ("apple", "curiosity") for it in test_b["items"])
    assert not any(
        it["prompt"]
        in (
            "a round fruit with red or green skin",
            "a strong desire to know or learn something",
        )
        for it in test_b["items"]
    )

    # 3. Stale Set A session discarded cleanly
    assert payload["loadedSessionStale"] is None

    # 4. Grading on Set B: 1 correct, 1 wrong
    graded_b = payload["gradedB"]
    assert graded_b["total"] == 2
    assert graded_b["correct"] == 1
    banana_result = next(r for r in graded_b["results"] if r["answer"] == "banana")
    assert banana_result["correct"] is True
    galaxy_result = next(r for r in graded_b["results"] if r["answer"] == "galaxy")
    assert galaxy_result["correct"] is False
    assert galaxy_result["given"] == "galaxi"

    # 5. Diff output accurately identifies substitution of 'i' for 'y'
    sub_ops = [op for op in payload["galaxyDiff"] if op["type"] == "substitution"]
    assert len(sub_ops) == 1
    assert sub_ops[0]["givenChar"] == "i"
    assert sub_ops[0]["expectedChar"] == "y"
