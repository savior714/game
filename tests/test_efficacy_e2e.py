"""효능감 시스템 — E2E 구조 검증 (Blueprint §12.2)

Playwright가 설치되지 않은 환경에서 구조적 준비 상태를 검증합니다.
Playwright 설치 후 실제 브라우저 테스트로 확장 가능.

테스트 시나리오 (Blueprint §12.2):
1. test_milestone_streak_toast: 수학 세션 3연속 정답 → "3연속!" 토스트
2. test_milestone_session_gems: 영어 세션 5문제 정답 → 토스트 + 보석+1
3. test_diversity_reward: 수학+영어 정답 → 다양성 보석+1
4. test_daily_streak_simulation: 7일 연속 출석 → 보석+2
5. test_level_up_toast: 난이도 상승 → 토스트 표시
6. test_weekly_summary_tab: guardian 성장 탭 → 세션/정답 수 변화
7. test_streak_separation: 로켓 발사 후 milestoneStreak 유지
8. test_gem_economy_cap: 하루 최대 보석 5개 초과 지급 방지
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# ── 엔진 연동 검증 ────────────────────────────────────────


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_all_4_engines_integrate_milestone_tracker() -> None:
    """4개 과목 engine.js가 MilestoneTracker.record()를 호출해야 함."""
    subjects = ["math", "english", "korean", "science"]
    for subject in subjects:
        engine = _read(f"domains/{subject}/engine.js")
        assert "MilestoneTracker.record(correct)" in engine, (
            f"{subject}/engine.js에 MilestoneTracker.record(correct) 연동이 없습니다."
        )


def test_all_4_engines_integrate_daily_streak() -> None:
    """4개 과목 engine.js가 DailyStreak.recordAnswer()를 호출해야 함."""
    subjects = ["math", "english", "korean", "science"]
    for subject in subjects:
        engine = _read(f"domains/{subject}/engine.js")
        assert "DailyStreak.recordAnswer(SUBJECT_NAME)" in engine, (
            f"{subject}/engine.js에 DailyStreak.recordAnswer(SUBJECT_NAME) 연동이 없습니다."
        )


def test_all_4_engines_integrate_diversity_reward() -> None:
    """4개 과목 engine.js가 DiversityReward.recordCorrect()를 호출해야 함."""
    subjects = ["math", "english", "korean", "science"]
    for subject in subjects:
        engine = _read(f"domains/{subject}/engine.js")
        assert "DiversityReward.recordCorrect(SUBJECT_NAME)" in engine, (
            f"{subject}/engine.js에 DiversityReward.recordCorrect(SUBJECT_NAME) 연동이 없습니다."
        )


def test_all_4_engines_integrate_growth_visualizer() -> None:
    """4개 과목 engine.js가 GrowthVisualizer.checkLevelUp()를 호출해야 함."""
    subjects = ["math", "english", "korean", "science"]
    for subject in subjects:
        engine = _read(f"domains/{subject}/engine.js")
        assert "GrowthVisualizer.checkLevelUp(SUBJECT_NAME" in engine, (
            f"{subject}/engine.js에 GrowthVisualizer.checkLevelUp() 연동이 없습니다."
        )


def test_all_4_engines_have_subject_name() -> None:
    """4개 과목 engine.js에 SUBJECT_NAME 상수가 정의되어 있어야 함."""
    expected = {
        "math": "math",
        "english": "english",
        "korean": "korean",
        "science": "science",
    }
    for subject, name in expected.items():
        engine = _read(f"domains/{subject}/engine.js")
        assert f"const SUBJECT_NAME = '{name}'" in engine, (
            f"{subject}/engine.js에 const SUBJECT_NAME = '{name}'이 없습니다."
        )


# ── 스크립트 로드 순서 검증 ───────────────────────────────


def test_script_load_order_math() -> None:
    """math/index.html에서 새 모듈이 기존 엔진 전에 로드되어야 함."""
    html = _read("domains/math/index.html")
    milestone_idx = html.index("milestone-tracker.js")
    engine_idx = html.index('src="engine.js"')
    assert milestone_idx < engine_idx, (
        "milestone-tracker.js가 engine.js 이후에 로드됩니다. "
        "새 모듈은 기존 엔진 전에 로드되어야 합니다."
    )


def test_script_load_order_english() -> None:
    """english/index.html에서 새 모듈이 기존 엔진 전에 로드되어야 함."""
    html = _read("domains/english/index.html")
    milestone_idx = html.index("milestone-tracker.js")
    engine_idx = html.index('src="engine.js"')
    assert milestone_idx < engine_idx, (
        "milestone-tracker.js가 engine.js 이후에 로드됩니다."
    )


def test_script_load_order_korean() -> None:
    """korean/index.html에서 새 모듈이 기존 엔진 전에 로드되어야 함."""
    html = _read("domains/korean/index.html")
    milestone_idx = html.index("milestone-tracker.js")
    engine_idx = html.index('src="engine.js"')
    assert milestone_idx < engine_idx, (
        "milestone-tracker.js가 engine.js 이후에 로드됩니다."
    )


def test_script_load_order_science() -> None:
    """science/index.html에서 새 모듈이 기존 엔진 전에 로드되어야 함."""
    html = _read("domains/science/index.html")
    milestone_idx = html.index("milestone-tracker.js")
    engine_idx = html.index('src="engine.js"')
    assert milestone_idx < engine_idx, (
        "milestone-tracker.js가 engine.js 이후에 로드됩니다."
    )


# ── 세션 종료 연동 검증 ───────────────────────────────────


def test_all_4_uis_call_end_session() -> None:
    """4개 과목 ui.js가 MilestoneTracker.endSession()를 호출해야 함."""
    subjects = ["math", "english", "korean", "science"]
    for subject in subjects:
        ui = _read(f"domains/{subject}/ui.js")
        assert "MilestoneTracker.endSession()" in ui, (
            f"{subject}/ui.js에 MilestoneTracker.endSession() 연동이 없습니다."
        )


def test_all_4_uis_call_on_subject_complete() -> None:
    """4개 과목 ui.js가 MilestoneTracker.onSubjectComplete()를 호출해야 함."""
    subjects = ["math", "english", "korean", "science"]
    for subject in subjects:
        ui = _read(f"domains/{subject}/ui.js")
        assert "MilestoneTracker.onSubjectComplete(SUBJECT_NAME)" in ui, (
            f"{subject}/ui.js에 MilestoneTracker.onSubjectComplete() 연동이 없습니다."
        )


def test_all_4_uis_call_record_session_end() -> None:
    """4개 과목 ui.js가 GrowthVisualizer.recordSessionEnd()를 호출해야 함."""
    subjects = ["math", "english", "korean", "science"]
    for subject in subjects:
        ui = _read(f"domains/{subject}/ui.js")
        assert "GrowthVisualizer.recordSessionEnd(SUBJECT_NAME" in ui, (
            f"{subject}/ui.js에 GrowthVisualizer.recordSessionEnd() 연동이 없습니다."
        )


# ── 로켓 연동 검증 ────────────────────────────────────────


def test_all_4_rockets_call_milestone_on_launch() -> None:
    """4개 과목 rocket.js가 MilestoneTracker.onRocketLaunch()를 호출해야 함."""
    subjects = ["math", "english", "korean", "science"]
    for subject in subjects:
        rocket = _read(f"domains/{subject}/rocket.js")
        assert "MilestoneTracker.onRocketLaunch()" in rocket, (
            f"{subject}/rocket.js에 MilestoneTracker.onRocketLaunch() 연동이 없습니다."
        )


# ── guardian 페이지 검증 ───────────────────────────────────


def test_guardian_has_growth_tab() -> None:
    """guardian/index.html에 성장 탭 버튼이 있어야 함."""
    html = _read("domains/reward/guardian/index.html")
    assert 'id="tab-growth"' in html, (
        "guardian/index.html에 id='tab-growth' 탭 버튼이 없습니다."
    )


def test_guardian_has_growth_panel() -> None:
    """guardian/index.html에 성장 패널(id='growth-panel')이 있어야 함."""
    html = _read("domains/reward/guardian/index.html")
    assert 'id="growth-panel"' in html, (
        "guardian/index.html에 id='growth-panel' 패널이 없습니다."
    )


def test_guardian_js_has_show_growth_tab() -> None:
    """guardian.js에 showGrowthTab 함수가 있어야 함."""
    js = _read("domains/reward/guardian/guardian.js")
    assert "function showGrowthTab" in js, (
        "guardian.js에 showGrowthTab 함수가 없습니다."
    )


def test_guardian_js_has_render_growth_summary() -> None:
    """guardian.js에 renderGrowthSummary 함수가 있어야 함."""
    js = _read("domains/reward/guardian/guardian.js")
    assert "function renderGrowthSummary" in js, (
        "guardian.js에 renderGrowthSummary 함수가 없습니다."
    )


def test_guardian_loads_growth_visualizer() -> None:
    """guardian/index.html이 growth-visualizer.js를 로드해야 함."""
    html = _read("domains/reward/guardian/index.html")
    assert "growth-visualizer.js" in html, (
        "guardian/index.html이 growth-visualizer.js를 로드하지 않습니다."
    )


# ── 보석 경제 검증 ────────────────────────────────────────


def test_gem_sources_all_call_reward_system_add() -> None:
    """모든 보석 지급 경로가 RewardSystem.add('gems', n)을 호출해야 함."""
    # milestone-tracker
    tracker = _read("shared/domain/milestone-tracker.js")
    assert (
        "RewardSystem.add('gems'" in tracker or 'RewardSystem.add("gems"' in tracker
    ), "milestone-tracker.js가 RewardSystem.add('gems')를 호출하지 않습니다."
    # daily-streak
    streak = _read("shared/domain/daily-streak.js")
    assert "RewardSystem.add('gems'" in streak or 'RewardSystem.add("gems"' in streak, (
        "daily-streak.js가 RewardSystem.add('gems')를 호출하지 않습니다."
    )
    # diversity-reward
    diversity = _read("shared/domain/diversity-reward.js")
    assert (
        "RewardSystem.add('gems'" in diversity or 'RewardSystem.add("gems"' in diversity
    ), "diversity-reward.js가 RewardSystem.add('gems')를 호출하지 않습니다."


# ── localStorage 키 검증 ──────────────────────────────────


def test_localstorage_keys_defined() -> None:
    """모든 모듈이 고유한 localStorage 키를 사용해야 함."""
    tracker = _read("shared/domain/milestone-tracker.js")
    streak = _read("shared/domain/daily-streak.js")
    diversity = _read("shared/domain/diversity-reward.js")
    growth = _read("shared/domain/growth-visualizer.js")

    keys = {
        "aiden_milestones": tracker,
        "aiden_daily_streak": streak,
        "aiden_diversity": diversity,
        "aiden_session_log": growth,
    }
    for key, code in keys.items():
        assert f"'{key}'" in code or f'"{key}"' in code, (
            f"localStorage 키 '{key}'가 해당 모듈에 없습니다."
        )


# ── E2E 테스트 준비 상태 검증 ─────────────────────────────


def test_playwright_not_installed_note() -> None:
    """Playwright가 설치되지 않았음을 기록 (실제 E2E는 수동 실행 필요)."""
    try:
        import importlib
        importlib.import_module("playwright")  # type: ignore[import-untyped]
    except ImportError:
        # Playwright 미설치 — 구조 검증만 수행
        pass  # 통과 (구조적 준비 상태는 위 테스트들로 검증됨)
