"""세션 로그 — 저장/90일 자동삭제 로직 검증 (Blueprint §4.4.3, §10.2)

핵심 규칙:
- aiden_session_log 키에 날짜별 세션 기록 저장
- 각 세션에 time, subject, correct, total, domains 포함
- 90일 초과 날짜는 recordSessionEnd에서 자동 삭제
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROWTH = ROOT / "shared" / "domain" / "growth-visualizer.js"


def _read() -> str:
    return GROWTH.read_text(encoding="utf-8")


# ── 세션 로그 스키마 검증 ──────────────────────────────────


def test_session_log_storage_key() -> None:
    """aiden_session_log 키를 사용해야 함."""
    code = _read()
    assert "aiden_session_log" in code, (
        "세션 로그 localStorage 키 'aiden_session_log'가 없습니다."
    )


def test_record_session_end_exists() -> None:
    """recordSessionEnd 함수가 존재해야 함."""
    code = _read()
    assert "function recordSessionEnd" in code, "recordSessionEnd 함수가 없습니다."


def test_session_log_has_time_field() -> None:
    """세션 로그 항목에 time 필드가 ISO 형식으로 저장되어야 함."""
    code = _read()
    fn = _extract_function(code, "function recordSessionEnd")
    assert "toISOString" in fn, "세션 로그에 ISO 시간 형식(toISOString)이 없습니다."


def test_session_log_has_subject_field() -> None:
    """세션 로그 항목에 subject 필드가 포함되어야 함."""
    code = _read()
    fn = _extract_function(code, "function recordSessionEnd")
    assert "subject" in fn, "세션 로그 항목에 subject 필드가 없습니다."


def test_session_log_has_correct_and_total() -> None:
    """세션 로그 항목에 correct와 total 필드가 포함되어야 함."""
    code = _read()
    fn = _extract_function(code, "function recordSessionEnd")
    assert "correct" in fn and "total" in fn, (
        "세션 로그 항목에 correct와 total 필드가 없습니다."
    )


# ── 90일 자동 삭제 검증 ───────────────────────────────────


def test_90_day_cleanup_exists() -> None:
    """recordSessionEnd에서 90일 초과 날짜를 자동 삭제해야 함."""
    code = _read()
    fn = _extract_function(code, "function recordSessionEnd")
    assert "90" in fn, "90일 자동 삭제 로직이 없습니다."


def test_90_day_cleanup_logic() -> None:
    """90일 이전 날짜는 delete로 제거되어야 함."""
    code = _read()
    fn = _extract_function(code, "function recordSessionEnd")
    assert "delete log[" in fn or "delete log[" in fn, (
        "90일 초과 날짜 삭제(delete) 로직이 없습니다."
    )


def test_cutoff_date_calculation() -> None:
    """cutoff 날짜가 현재 날짜 - 90일로 계산되어야 함."""
    code = _read()
    fn = _extract_function(code, "function recordSessionEnd")
    assert "getDate() - 90" in fn or "getDate()-90" in fn, (
        "cutoff 날짜 계산(getDate() - 90)이 없습니다."
    )


# ── 주간 요약 검증 ─────────────────────────────────────────


def test_get_weekly_summary_exists() -> None:
    """getWeeklySummary 함수가 존재해야 함."""
    code = _read()
    assert "function getWeeklySummary" in code, "getWeeklySummary 함수가 없습니다."


def test_weekly_summary_includes_subjects() -> None:
    """주간 요약이 4개 과목(math, english, korean, science)을 포함해야 함."""
    code = _read()
    fn = _extract_function(code, "function getWeeklySummary")
    for subject in ["math", "english", "korean", "science"]:
        assert f"'{subject}'" in fn or f'"{subject}"' in fn, (
            f"주간 요약에 '{subject}' 과목이 없습니다."
        )


def test_weekly_summary_session_change() -> None:
    """주간 요약에 sessionChange(세션 수 변화)가 포함되어야 함."""
    code = _read()
    fn = _extract_function(code, "function getWeeklySummary")
    assert "sessionChange" in fn or "session_change" in fn, (
        "주간 요약에 세션 수 변화(sessionChange)가 없습니다."
    )


def test_weekly_summary_avg_accuracy() -> None:
    """주간 요약에 avgAccuracy(정확도)가 포함되어야 함."""
    code = _read()
    fn = _extract_function(code, "function getWeeklySummary")
    assert "avgAccuracy" in fn or "avg_accuracy" in fn, (
        "주간 요약에 정확도(avgAccuracy)가 없습니다."
    )


# ── 숙련도 바 검증 ─────────────────────────────────────────


def test_show_proficiency_bar_exists() -> None:
    """showProficiencyBar 함수가 존재해야 함."""
    code = _read()
    assert "function showProficiencyBar" in code, "showProficiencyBar 함수가 없습니다."


def test_calculate_proficiency_exists() -> None:
    """calculateProficiency 함수가 존재해야 함."""
    code = _read()
    assert "function calculateProficiency" in code, (
        "calculateProficiency 함수가 없습니다."
    )


def test_proficiency_calculated_as_percentage() -> None:
    """숙련도는 correct/attempts * 100으로 계산되어야 함."""
    code = _read()
    fn = _extract_function(code, "function calculateProficiency")
    assert "* 100" in fn or "*100" in fn, "숙련도 계산에 퍼센트 변환(* 100)이 없습니다."


# ── 난이도 상승 토스트 검증 ───────────────────────────────


def test_check_level_up_exists() -> None:
    """checkLevelUp 함수가 존재해야 함."""
    code = _read()
    assert "function checkLevelUp" in code, "checkLevelUp 함수가 없습니다."


def test_level_up_message_format() -> None:
    """난이도 상승 토스트 메시지에 old→new 레벨 정보가 포함되어야 함."""
    code = _read()
    fn = _extract_function(code, "function checkLevelUp")
    assert "→" in fn or "->" in fn, "난이도 상승 메시지에 레벨 변화 표시(→)가 없습니다."


def test_level_up_duplicate_prevention() -> None:
    """세션당 1회만 표시 (levelUpShown 플래그)."""
    code = _read()
    assert "levelUpShown" in code, (
        "난도 상승 중복 방지를 위한 levelUpShown 플래그가 없습니다."
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
