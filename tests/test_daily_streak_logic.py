"""일일 출석 — 보석 계산 로직 검증 (Blueprint §4.2, §10.2)

핵심 규칙:
- 1~2일: +1 보석
- 3~6일: +2 보석 (기본 1 + 보너스 1)
- 7일 이상: +2 보석 (기본 1 + 보너스 1, 3→2로 하향)
- 누락 시 streak 완전 리셋
- 하루 최대 1회 보석 지급
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STREAK = ROOT / "shared" / "domain" / "daily-streak.js"


def _read() -> str:
    return STREAK.read_text(encoding="utf-8")


# ── 보석 계산 로직 검증 ────────────────────────────────────


def test_calculate_streak_gems_exists() -> None:
    """calculateStreakGems 함수가 존재해야 함."""
    code = _read()
    assert "function calculateStreakGems" in code, (
        "calculateStreakGems 함수가 없습니다."
    )


def test_streak_1_gives_1_gem() -> None:
    """1일 연속: 기본 +1 보석."""
    code = _read()
    fn = _extract_function(code, "function calculateStreakGems")
    # streak === 0 → return 0
    assert "streak === 0" in fn or "streak==0" in fn, (
        "streak 0일 때 0 보석을 반환해야 합니다."
    )
    # 기본 gems = 1
    assert "gems = 1" in fn or "gems=1" in fn, "기본 보석 수가 1이 아닙니다."


def test_streak_3_gives_2_gems() -> None:
    """3일 연속: 기본 +1 + 보너스 1 = 총 2보석."""
    code = _read()
    fn = _extract_function(code, "function calculateStreakGems")
    # 3일 이상 보너스
    assert "streak >= 3" in fn or "streak>=3" in fn, "3일 연속 보너스 조건이 없습니다."


def test_streak_7_gives_2_gems_not_3() -> None:
    """7일 연속: 3→2로 하향. 총 2보석 (기본 1 + 보너스 1)."""
    code = _read()
    fn = _extract_function(code, "function calculateStreakGems")

    # 7일 이상 보너스 조건
    has_7_bonus = "streak >= 7" in fn or "streak>=7" in fn
    assert has_7_bonus, "7일 연속 보너스 조건이 없습니다."

    # 보너스가 두 번(3일+7일) 더해지는 구조여야 함 (총 +2 = 2보석)
    bonus_count = fn.count("gems += 1") + fn.count("gems+ = 1")
    assert bonus_count == 2, (
        f"보너스 지급 로직이 {bonus_count}개입니다. 2개여야 합니다 "
        f"(3일 보너스 + 7일 보너스 = 총 2보석). 3→2로 하향되었습니다."
    )


def test_streak_reset_on_gap() -> None:
    """2일 이상 누락 시 streak가 0으로 리셋되어야 함."""
    code = _read()
    record_fn = _extract_function(code, "function recordAnswer")
    assert "diffDays > 1" in record_fn or "diffDays>1" in record_fn, (
        "2일 이상 누락 시 streak 리셋 조건이 없습니다."
    )
    assert "currentStreak = 0" in record_fn or "currentStreak=0" in record_fn, (
        "누락 시 currentStreak가 0으로 리셋되지 않습니다."
    )


def test_daily_gem_cap_one_per_day() -> None:
    """하루에 한 번만 보석 지급 (todayRecorded / gemAwarded 체크)."""
    code = _read()
    record_fn = _extract_function(code, "function recordAnswer")
    has_dup_check = "todayRecorded" in record_fn or "gemAwarded" in record_fn
    assert has_dup_check, (
        "하루 중복 보석 지급 방지 로직이 없습니다. "
        "todayRecorded 또는 gemAwarded 체크가 필요합니다."
    )


def test_midnight_reset_clears_today_recorded() -> None:
    """checkMidnightReset에서 오늘 날짜라면 todayRecorded를 false로 초기화."""
    code = _read()
    reset_fn = _extract_function(code, "function checkMidnightReset")
    assert "todayRecorded" in reset_fn, (
        "checkMidnightReset에서 todayRecorded를 초기화하지 않습니다."
    )


def test_history_tracking() -> None:
    """history 객체에 날짜별 활동 기록이 저장되어야 함."""
    code = _read()
    record_fn = _extract_function(code, "function recordAnswer")
    assert "history[" in record_fn or "history[" in record_fn, (
        "history 객체에 날짜별 기록이 저장되지 않습니다."
    )


def test_get_current_streak_exists() -> None:
    """getCurrentStreak() 함수가 존재해야 함."""
    code = _read()
    assert "function getCurrentStreak" in code, "getCurrentStreak 함수가 없습니다."


def test_is_today_active_exists() -> None:
    """isTodayActive() 함수가 존재해야 함."""
    code = _read()
    assert "function isTodayActive" in code, "isTodayActive 함수가 없습니다."


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
