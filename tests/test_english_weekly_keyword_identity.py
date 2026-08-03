"""
주간 시험 단어(isWeekly) 문제의 출제 대상(rendered/scored target)이
등록한 키워드와 동일한지 검증한다.

production JS(progress-engine.js, words.js, advanced-questions.js, engine.js)를
Node `vm` 계열로 직접 로드해 실제 문제 생성 코드를 실행한다.
- 쇼핑 대화문(shopping_dialogue)은 일반 단어에서만 허용되어야 한다.
- 주간 단어 문제에서는 `shopping_dialogue`가 절대 생성되지 않아야 한다.
- 주간 단어 문제의 `word`/`_wordEn`/`answer`(또는 spelling blank)는
  선택된 `englishWeeklyWords[].en`과 동일해야 한다.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

PRODUCTION_FILES = [
    "shared/domain/progress-engine.js",
    "domains/english/words.js",
    "domains/english/advanced-questions.js",
    "domains/english/engine.js",
]

ALLOWED_WEEKLY_TYPES = {"kor2word", "spelling", "minimal_pair", "sentence", "typing"}

WEEKLY_WORD = "planet"

# engine.js를 직접 실행하기 위한 최소 브라우저 전역 stub
PROLOGUE = """
const window = globalThis;
const localStorage = {
  _store: {},
  getItem(k) { return Object.prototype.hasOwnProperty.call(this._store, k) ? this._store[k] : null; },
  setItem(k, v) { this._store[k] = String(v); },
  removeItem(k) { delete this._store[k]; },
  clear() { this._store = {}; },
};
const document = { getElementById: () => null };
"""

# production JS를 실제로 호출하고 결과를 JSON으로 출력하는 harness
HARNESS = r"""
(function () {
  var queue = [];
  var queued = false;
  var defaultCounter = 0;
  // 낮은 불일치 결정적 시퀀스: 상수 난수는 makeSpellingChoices의
  // while 루프가 같은 인덱스를 반복 선택해 무한 루프가 될 수 있으므로
  // 호출마다 값이 퍼지도록 한다. 모두 (0,1) 범위를 순회한다.
  function defaultRandom() {
    return ((defaultCounter++ * 0.6180339887498949) % 1);
  }
  function nextRandom() {
    if (queued && queue.length) return queue.shift();
    return defaultRandom();
  }
  Math.random = nextRandom;

  function withRandom(values, fn) {
    queued = true;
    queue.length = 0;
    queue.push.apply(queue, values);
    try { return fn(); } finally { queued = false; queue.length = 0; }
  }

  function resetState() {
    recentQuestions.length = 0;
    wrongPatterns.length = 0;
    weeklyTypeHistory = {};
  }

  function setWeekly(words) {
    localStorage.setItem('englishWeeklyWords', JSON.stringify(words));
    loadWeeklyWords();
  }

  function forceLevel(level) {
    for (var i = 0; i < level; i++) {
      stats[currentCat].levels[i] = { attempts: 3, correct: 3, totalTime: 0 };
    }
  }

  var FIXTURE = [{ en: 'planet', ko: '행성', icon: '' }];

  function plain(q) {
    return {
      type: q.type,
      word: q.word,
      _wordEn: q._wordEn,
      isWeekly: q.isWeekly,
      answer: q.answer,
      blankIndices: q.blankIndices || null,
      blanks: q.blanks || null,
      id: q.id || null,
      _level: q._level,
    };
  }

  function genWeeklyQuestion(level, randValues) {
    return withRandom(randValues, function () {
      resetState();
      setWeekly(FIXTURE);
      forceLevel(level);
      return plain(generateQuestion());
    });
  }

  var case1 = genWeeklyQuestion(3, [0.0, 0.0, 0.8, 0.0]);

  var case2 = [];
  var levelSeqs = {
    0: [[0.0, 0.0, 0.1], [0.0, 0.0, 0.4], [0.0, 0.0, 0.9]],
    1: [[0.0, 0.0, 0.2], [0.0, 0.0, 0.5], [0.0, 0.0, 0.95]],
    2: [[0.0, 0.0, 0.1], [0.0, 0.0, 0.5], [0.0, 0.0, 0.99]],
    3: [[0.0, 0.0, 0.8], [0.0, 0.0, 0.1], [0.0, 0.0, 0.99]],
    4: [[0.0, 0.0, 0.7], [0.0, 0.0, 0.5], [0.0, 0.0, 0.99]],
    5: [[0.0, 0.0, 0.75], [0.0, 0.0, 0.3], [0.0, 0.0, 0.99]],
    6: [[0.0, 0.0, 0.8], [0.0, 0.0, 0.2], [0.0, 0.0, 0.99]],
  };
  Object.keys(levelSeqs).forEach(function (level) {
    levelSeqs[level].forEach(function (seq) {
      case2.push({ level: Number(level), q: genWeeklyQuestion(Number(level), seq) });
    });
  });

  var case3 = [];
  resetState();
  setWeekly(FIXTURE);
  forceLevel(3);
  for (var i = 0; i < 12; i++) {
    // 매 반복마다 주간 게이트와 단어 선택만 결정적으로 고정하고,
    // 그 뒤의 유형 선택·빌드 단계는 결정적 기본 난수를 사용한다.
    case3.push(plain(withRandom([0.0, 0.0], function () { return _generateCandidate(); })));
  }

  var case5 = null;
  withRandom([0.8, 0.8, 0.2, 0.0, 0.8], function () {
    resetState();
    setWeekly(FIXTURE);
    forceLevel(3);
    wrongPatterns.unshift({ cat: currentCat, level: 3, en: 'planet', isWeekly: true });
    case5 = plain(generateQuestion());
  });

  var case4 = null;
  withRandom([0.5], function () {
    resetState();
    setWeekly([]);
    case4 = plain(buildQuestion('shopping_dialogue', ['apple', '사과', '🍎', 0], { cat: 'fruits' }));
  });

  console.log(JSON.stringify({ case1: case1, case2: case2, case3: case3, case4: case4, case5: case5 }));
})();
"""


def _node() -> str:
    node = shutil.which("node")
    if not node:
        raise RuntimeError(
            "node 실행 파일을 찾을 수 없습니다. production JS를 직접 실행할 수 없습니다."
        )
    return node


def _run_report() -> dict:
    sources = [PROLOGUE]
    for rel in PRODUCTION_FILES:
        path = ROOT / rel
        if not path.exists():
            raise RuntimeError(f"production 파일을 찾을 수 없습니다: {rel}")
        sources.append(path.read_text(encoding="utf-8"))
    sources.append(HARNESS)
    combined = "\n".join(sources)

    with tempfile.NamedTemporaryFile(
        "w", suffix=".js", delete=False, encoding="utf-8"
    ) as f:
        f.write(combined)
        script_path = f.name
    try:
        proc = subprocess.run(
            [_node(), script_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        Path(script_path).unlink(missing_ok=True)

    if proc.returncode != 0:
        raise RuntimeError(
            "production JS 실행 실패:\n%s\n%s" % (proc.stdout, proc.stderr)
        )
    try:
        report = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as exc:
        raise RuntimeError(
            "harness 출력을 파싱할 수 없습니다. stdout=%r" % proc.stdout
        ) from exc
    return report


@pytest.fixture(scope="module")
def report() -> dict:
    return _run_report()


def _assert_weekly_contract(q: dict, expected_word: str) -> None:
    msg = "A generated weekly question is not bound to the selected weekly keyword."
    assert q["isWeekly"] is True, msg
    assert q["_wordEn"] == expected_word, msg
    assert q["word"] == expected_word, msg
    assert q["type"] != "shopping_dialogue", msg
    assert q["type"] in ALLOWED_WEEKLY_TYPES, msg
    if q["type"] == "spelling":
        assert q["blankIndices"] is not None and q["blanks"] is not None, msg
        for pos, idx in enumerate(q["blankIndices"]):
            assert 0 <= idx < len(expected_word), msg
            assert q["blanks"][pos]["char"] == expected_word[idx], msg
    else:
        assert q["answer"] == expected_word, msg


def test_weekly_question_bound_to_selected_keyword(report: dict) -> None:
    _assert_weekly_contract(report["case1"], WEEKLY_WORD)


def test_weekly_question_bound_at_every_level(report: dict) -> None:
    entries = report["case2"]
    assert len(entries) == 21, f"예상 21개(레벨당 3개), 실제 {len(entries)}"
    levels_checked = {entry["level"] for entry in entries}
    assert levels_checked == set(range(7)), (
        f"레벨 커버리지 부족: {sorted(levels_checked)}"
    )
    for entry in entries:
        _assert_weekly_contract(entry["q"], WEEKLY_WORD)


def test_weekly_type_rotation_never_shopping_dialogue(report: dict) -> None:
    questions = report["case3"]
    assert len(questions) >= 12
    types = set()
    for q in questions:
        _assert_weekly_contract(q, WEEKLY_WORD)
        types.add(q["type"])
    assert types == ALLOWED_WEEKLY_TYPES, (
        f"주간 유형 순환이 허용 집합을 벗어남: {types}"
    )


def test_weekly_wrongpattern_reinforcement_bound_to_keyword(report: dict) -> None:
    _assert_weekly_contract(report["case5"], WEEKLY_WORD)


def test_ordinary_shopping_dialogue_preserved(report: dict) -> None:
    q = report["case4"]
    assert q is not None
    assert q["type"] == "shopping_dialogue", "일반 단어 shopping_dialogue 생성이 제거됨"
    assert q["word"] == "apple"
    assert q["answer"], "일반 shopping_dialogue 정답이 비어있음"
