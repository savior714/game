"""마일스톤 추적기 — streak 분리 로직 검증 (Blueprint §4.1, §10.2)

핵심 규칙:
- rocketStreak: RocketCore와 공유, 로켓 발사 시 0 리셋
- milestoneStreak: 오답 시에만 0 리셋, 로켓 발사 시 유지
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKER = ROOT / "shared" / "domain" / "milestone-tracker.js"


def _read() -> str:
    return TRACKER.read_text(encoding="utf-8")


# ── 구조 검증 ──────────────────────────────────────────────


def test_has_both_streak_counters() -> None:
    """session 객체에 rocketStreak와 milestoneStreak가 모두 정의되어 있어야 함."""
    code = _read()
    assert "rocketStreak" in code, "rocketStreak 카운터가 없습니다."
    assert "milestoneStreak" in code, "milestoneStreak 카운터가 없습니다."


def test_streaks_incremented_together_on_correct() -> None:
    """record(correct)에서 두 streak가 모두 증가해야 함."""
    code = _read()
    record_fn = _extract_function(code, "function record")
    assert "rocketStreak++" in record_fn or "rocketStreak += 1" in record_fn, (
        "정답 시 rocketStreak가 증가하지 않습니다."
    )
    assert "milestoneStreak++" in record_fn or "milestoneStreak += 1" in record_fn, (
        "정답 시 milestoneStreak가 증가하지 않습니다."
    )


def test_only_milestone_streak_resets_on_wrong() -> None:
    """오답 시 milestoneStreak만 0으로 리셋되어야 함 (rocketStreak는 유지)."""
    code = _read()
    record_fn = _extract_function(code, "function record")

    else_block = _extract_else_block(record_fn)
    assert "milestoneStreak = 0" in else_block or "milestoneStreak=0" in else_block, (
        "오답 시 milestoneStreak가 0으로 리셋되지 않습니다."
    )
    assert (
        "rocketStreak = 0" not in else_block and "rocketStreak=0" not in else_block
    ), "오답 시 rocketStreak가 리셋됩니다. rocketStreak는 오답 시 유지되어야 합니다."


def test_rocket_launch_resets_only_rocket_streak() -> None:
    """onRocketLaunch에서 rocketStreak만 0으로 리셋, milestoneStreak는 유지."""
    code = _read()
    rocket_fn = _extract_function(code, "function onRocketLaunch")
    assert "rocketStreak = 0" in rocket_fn or "rocketStreak=0" in rocket_fn, (
        "로켓 발사 시 rocketStreak가 0으로 리셋되지 않습니다."
    )
    # milestoneStreak 리셋이 없어야 함
    assert (
        "milestoneStreak = 0" not in rocket_fn and "milestoneStreak=0" not in rocket_fn
    ), "로켓 발사 시 milestoneStreak도 리셋됩니다. milestoneStreak는 유지되어야 합니다."


def test_session_milestones_have_gems() -> None:
    """session_5/10/20 마일스톤이 보석(gems)을 지급해야 함."""
    code = _read()
    # SESSION_MILESTONES 배열에서 gems > 0인 항목이 있어야 함
    session_match = re.search(r"SESSION_MILESTONES\s*=\s*\[([\s\S]*?)\]", code)
    assert session_match, "SESSION_MILESTONES 배열이 없습니다."
    session_block = session_match.group(1)
    gems_count = (
        session_block.count('"gems":')
        + session_block.count("'gems':")
        + session_block.count("gems:")
    )
    assert gems_count >= 3, "SESSION_MILESTONES에 gems 필드가 없습니다."
    # session_5/10/20이 gems > 0을 가져야 함
    assert "gems: 1" in session_block, (
        "session_5/10/20 마일스톤이 보석을 지급해야 합니다 (gems: 1)."
    )


def test_achieved_tracking_for_all_milestones() -> None:
    """모든 마일스톤 키가 achieved 객체에 정의되어 있어야 함."""
    code = _read()
    expected_keys = [
        "streak_3",
        "streak_5",
        "streak_10",
        "streak_15",
        "session_3",
        "session_5",
        "session_10",
        "session_20",
        "first_answer",
        "first_subject_complete",
        "first_rocket",
    ]
    for key in expected_keys:
        assert f"'{key}'" in code or f'"{key}"' in code, (
            f"achieved 객체에 '{key}' 마일스톤 키가 없습니다."
        )


def test_end_session_returns_correct_count() -> None:
    """endSession()이 세션 내 정답 수를 반환해야 함 (세션 로그 연동용)."""
    code = _read()
    end_fn = _extract_function(code, "function endSession")
    assert "sessionCorrect" in end_fn, (
        "endSession()이 sessionCorrect를 반환하지 않습니다. "
        "세션 로그 기록에 필요합니다."
    )


def test_on_subject_complete_tracks_subjects() -> None:
    """onSubjectComplete가 lifetime.subjectsCompleted에 과목명을 추가해야 함."""
    code = _read()
    complete_fn = _extract_function(code, "function onSubjectComplete")
    assert "subjectsCompleted" in complete_fn, (
        "onSubjectComplete이 subjectsCompleted를 업데이트하지 않습니다."
    )


def test_lifetime_total_correct_increments() -> None:
    """lifetime.totalCorrect가 정답 시 증가해야 함."""
    code = _read()
    record_fn = _extract_function(code, "function record")
    assert "totalCorrect" in record_fn and ("++" in record_fn or "+= 1" in record_fn), (
        "lifetime.totalCorrect가 정답 시 증가하지 않습니다."
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


def _extract_else_block(fn_body: str) -> str:
    """function body에서 else 블록을 추출."""
    else_idx = fn_body.rfind("} else {")
    if else_idx == -1:
        return fn_body
    return fn_body[else_idx + 8 : -1]
