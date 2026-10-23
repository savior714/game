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


def _read_rel(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


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


def test_session_milestones_do_not_grant_gems() -> None:
    """세션 누적 마일스톤(session_3/5/10/20)은 격려 토스트만 제공해야 함 (보석 없음).

    정답 개수 기반 보석은 20연속 정답의 로켓 발사 보상으로만 지급한다.
    """
    code = _read()
    session_match = re.search(r"SESSION_MILESTONES\s*=\s*\[([\s\S]*?)\]", code)
    assert session_match, "SESSION_MILESTONES 배열이 없습니다."
    entries = re.findall(r"\{[^{}]*\}", session_match.group(1))
    assert entries, "SESSION_MILESTONES에 항목이 없습니다."
    for entry in entries:
        gems = re.search(r"gems:\s*(\d+)", entry)
        assert gems, f"SESSION_MILESTONES 항목에 gems 필드가 없습니다: {entry}"
        assert int(gems.group(1)) == 0, (
            f"세션 누적 마일스톤이 보석을 지급합니다: {entry} — "
            "정답 보석은 20연속 로켓 발사 보상으로만 지급해야 합니다."
        )


def test_streak_milestones_do_not_grant_gems() -> None:
    """연속 정답 마일스톤(streak_3/5/10/15)도 격려 토스트만 제공해야 함 (보석 없음)."""
    code = _read()
    streak_match = re.search(r"STREAK_MILESTONES\s*=\s*\[([\s\S]*?)\]", code)
    assert streak_match, "STREAK_MILESTONES 배열이 없습니다."
    entries = re.findall(r"\{[^{}]*\}", streak_match.group(1))
    assert entries, "STREAK_MILESTONES에 항목이 없습니다."
    for entry in entries:
        gems = re.search(r"gems:\s*(\d+)", entry)
        assert gems, f"STREAK_MILESTONES 항목에 gems 필드가 없습니다: {entry}"
        assert int(gems.group(1)) == 0, (
            f"연속 정답 마일스톤이 보석을 지급합니다: {entry} — "
            "정답 보석은 20연속 로켓 발사 보상으로만 지급해야 합니다."
        )


def test_quiz_gem_only_from_20_streak_rocket_launch() -> None:
    """정답 기반 보석의 유일한 지급 경로는 20연속 정답 로켓 발사(+1)여야 함."""
    # 마일스톤 트래커에는 보석 지급 마일스톤이 없어야 함
    assert "gems: 1" not in _read(), (
        "milestone-tracker.js에 gems: 1 마일스톤이 있습니다. "
        "정답 보석은 rocket-core.js의 20연속 로켓 발사 보상으로만 지급합니다."
    )

    # 로켓은 연속 20정답에 발사한다
    rocket = _read_rel("shared/ui/rocket-core.js")
    assert re.search(r"target\.LAUNCH_STREAK\s*=\s*20\b", rocket), (
        "로켓 발사 기준 연속 정답 수(LAUNCH_STREAK) 기본값이 20이 아닙니다."
    )
    for subject in ("math", "english", "korean", "science"):
        engine = _read_rel(f"domains/{subject}/engine.js")
        assert re.search(r"LAUNCH_STREAK\s*=\s*20\b", engine), (
            f"{subject}/engine.js의 LAUNCH_STREAK가 20이 아닙니다."
        )

    # 발사 시 보석 1개를 지급한다
    assert 'playEntranceAndAddGem("rp-rocket"' in rocket, (
        "로켓 발사 시 보석 지급(playEntranceAndAddGem) 호출이 없습니다."
    )
    reward_ui = _read_rel("domains/reward/reward_ui.js")
    assert re.search(r"add\('gems',\s*1\b", reward_ui), (
        "로켓 발사 보석 지급량이 1개가 아닙니다."
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
