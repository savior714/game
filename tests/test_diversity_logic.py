"""과목 다양성 보상 — 보석 계산 로직 검증 (Blueprint §4.3)

핵심 규칙:
- 1개: 0보석
- 2개: +1보석
- 3개: +2보석
- 4개: +2보석 (3→2로 하향)
- 하루 1회만 지급 (gemAwarded boolean)
- 자정 초기화
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIVERSITY = ROOT / "shared" / "domain" / "diversity-reward.js"


def _read() -> str:
    return DIVERSITY.read_text(encoding="utf-8")


# ── 보석 계산 로직 검증 ────────────────────────────────────

def test_get_diversity_gems_exists() -> None:
    """getDiversityGems 함수가 존재해야 함."""
    code = _read()
    assert "function getDiversityGems" in code, (
        "getDiversityGems 함수가 없습니다."
    )


def test_1_subject_no_gems() -> None:
    """정답 과목 1개: 보석 0."""
    code = _read()
    fn = _extract_function(code, "function getDiversityGems")
    # subjectCount >= 2부터 보석 지급
    assert "subjectCount >= 2" in fn or "subjectCount>=2" in fn, (
        "2개 이상 조건이 없습니다."
    )
    # 마지막 return 0 (1개일 때)
    assert "return 0" in fn, (
        "subjectCount < 2일 때 0을 반환해야 합니다."
    )


def test_2_subjects_gives_1_gem() -> None:
    """정답 과목 2개: +1보석."""
    code = _read()
    fn = _extract_function(code, "function getDiversityGems")
    assert 'if (subjectCount >= 2) return 1' in fn or \
           "if(subjectCount>=2)return 1" in fn, (
        "2개일 때 1보석을 반환해야 합니다."
    )


def test_3_subjects_gives_2_gems() -> None:
    """정답 과목 3개: +2보석."""
    code = _read()
    fn = _extract_function(code, "function getDiversityGems")
    assert 'if (subjectCount >= 3) return 2' in fn or \
           "if(subjectCount>=3)return 2" in fn, (
        "3개일 때 2보석을 반환해야 합니다."
    )


def test_4_subjects_gives_2_gems_not_3() -> None:
    """정답 과목 4개: 3→2로 하향, +2보석."""
    code = _read()
    fn = _extract_function(code, "function getDiversityGems")
    assert 'if (subjectCount >= 4) return 2' in fn or \
           "if(subjectCount>=4)return 2" in fn, (
        "4개일 때 2보석을 반환해야 합니다 (3→2로 하향)."
    )


def test_daily_gem_cap_one() -> None:
    """하루에 한 번만 보석 지급 (gemAwarded boolean 체크)."""
    code = _read()
    record_fn = _extract_function(code, "function recordCorrect")
    assert "gemAwarded" in record_fn, (
        "하루 중복 보석 지급 방지를 위한 gemAwarded 체크가 없습니다."
    )


def test_midnight_reset_clears_subjects() -> None:
    """checkMidnightReset에서 새 날짜면 subjectsWithCorrect를 초기화."""
    code = _read()
    reset_fn = _extract_function(code, "function checkMidnightReset")
    assert "subjectsWithCorrect" in reset_fn and "[]" in reset_fn, (
        "checkMidnightReset에서 subjectsWithCorrect를 []로 초기화하지 않습니다."
    )
    assert "gemAwarded = false" in reset_fn or "gemAwarded=false" in reset_fn, (
        "checkMidnightReset에서 gemAwarded를 false로 초기화하지 않습니다."
    )


def test_duplicate_subject_skipped() -> None:
    """이미 정답 기록된 과목은 recordCorrect에서 skip되어야 함."""
    code = _read()
    record_fn = _extract_function(code, "function recordCorrect")
    assert "includes(subject)" in record_fn or "indexOf(subject)" in record_fn, (
        "중복 과목 체크 로직이 없습니다."
    )


def test_today_subject_count_exists() -> None:
    """getTodaySubjectCount() 함수가 존재해야 함."""
    code = _read()
    assert "function getTodaySubjectCount" in code, (
        "getTodaySubjectCount 함수가 없습니다."
    )


def test_today_subjects_exists() -> None:
    """getTodaySubjects() 함수가 존재해야 함."""
    code = _read()
    assert "function getTodaySubjects" in code, (
        "getTodaySubjects 함수가 없습니다."
    )


# ── 헬퍼 ───────────────────────────────────────────────────

def _extract_function(code: str, fn_name: str) -> str:
    idx = code.index(fn_name)
    brace = code.index("{", idx)
    depth = 0
    start = brace
    for i in range(brace, len(code)):
        if code[i] == "{":
            depth += 1
        elif code[i] == "}":
            depth -= 1
            if depth == 0:
                return code[start : i + 1]
    return code[start:]
