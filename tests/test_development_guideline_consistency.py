from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_guidance_uses_domain_owners_instead_of_a_conflicting_global_order() -> None:
    agents = read("AGENTS.md")
    docs_index = read("docs/README.md")
    load_order = read("agents/registry/LOAD_ORDER.md")
    context = read("agents/registry/CONTEXT_ROUTING.md")
    routing = read("agents/core/routing.md")
    planning = read("agents/core/planning.md")
    principles = read("agents/core/principles.md")

    for document in (agents, docs_index, load_order, context, routing):
        assert "ACTIVE_PRODUCT_SCOPE.md" in document
        assert "PROJECT_RULES.md" in document

    assert "권위는 질문의 domain에 따라 고른다" in agents
    assert "질문의 domain별 owner" in load_order
    assert "전역 문서 서열 대신 질문의 domain별 owner" in context
    assert "전역 서열 대신 질문의 domain별 owner" in routing
    assert "제품 목표·우선순위" in planning
    assert "ACTIVE_PRODUCT_SCOPE.md" in principles

    stale_linear_orders = (
        "사용자의 현재 요청 → AGENTS.md → PROJECT_RULES.md와 가장 가까운",
        "충돌 시 다음 순서를 적용한다.",
    )
    for document in (docs_index, load_order, context, routing):
        for stale_order in stale_linear_orders:
            assert stale_order not in document


def test_product_priority_is_not_mistaken_for_feature_freeze() -> None:
    scope = read("docs/specs/product/ACTIVE_PRODUCT_SCOPE.md")
    project_rules = read("PROJECT_RULES.md")
    docs_index = read("docs/README.md")
    principles = read("agents/core/principles.md")
    discover = read("agents/workflows/discover.md")
    investigate = read("agents/workflows/investigate.md")
    refactor = read("agents/skills/refactor/SKILL.md")
    architecture = read("agents/skills/improve-codebase-architecture/SKILL.md")
    sync = read("agents/skills/sync/SKILL.md")
    readme = read("README.md")

    assert "Ocean Rescue | active reward-game product" in scope
    assert "Space Explorer | `PAUSED_REFERENCE_ONLY`" in scope
    assert "Space Explorer `PAUSED_REFERENCE_ONLY` 참고" in project_rules
    assert "Space Explorer 동결 참고" not in project_rules
    assert "Ocean Rescue는 더 이상 제품 차원에서 동결된 feature가 아니다." in docs_index
    assert "Ocean Rescue는 active feature" in discover
    assert "Ocean Rescue는 active feature" in investigate
    assert "Active feature가 현재 기본 priority가 아니라는 이유만으로" in refactor
    assert "Ocean Rescue는 active feature" in architecture
    assert "Ocean Rescue가 active reward-game feature" in sync
    assert "디렉터리 전체가 동결된 것은 아니다" in readme
    assert "Space Explorer | 배포된 artifact·`PAUSED_REFERENCE_ONLY`" in readme
    assert "운영중·개발 동결" not in readme
    assert "Space Explorer" in principles

    obsolete_claims = (
        "동결된 Ocean Rescue·실험 기능",
        "Ocean Rescue와 `experiments/`의 architecture 개선은 현재 방향에서 제외된다.",
        "Ocean Rescue가 현재 development freeze 상태임",
        "현재 신규 architecture migration은 동결 상태다.",
        "Ocean Rescue·실험 기능은 동결 정책 위반 여부만 조사할 수 있으며",
        "Ocean Rescue와 `experiments/`처럼 동결된 표면",
    )
    guidance = "\n".join(
        (
            principles,
            discover,
            investigate,
            refactor,
            architecture,
            sync,
        )
    )
    for claim in obsolete_claims:
        assert claim not in guidance


def test_branch_and_workspace_defaults_yield_to_assigned_session_constraints() -> None:
    harness = read(".agent-harness.yml")
    agents = read("AGENTS.md")
    project_rules = read("PROJECT_RULES.md")
    execution = read("agents/core/execution.md")
    git_policy = read("agents/workflows/git.md")
    profile = read("agents/project/PROFILE.md")
    opencode = read("agents/core/opencode_tools.md")
    delegation = read("agents/project/LOCAL_LLM_DELEGATION.md")
    parallel_tracks = read("agents/project/PARALLEL_TRACKS.md")
    a_track_runbook = read("docs/plans/PLAN_A_TRACK_RUNTIME_EXECUTION_RUNBOOK.md")
    track_b_runbook = read("docs/plans/AIDENGAME_OCEAN_RESCUE_TRACK_B_EXECUTION_RUNBOOK.md")

    assert 'canonical_branch: "main"' in harness
    assert "main_only: false" in harness
    for document in (agents, project_rules, execution, git_policy, profile, opencode, delegation):
        assert "실행 환경" in document or "session/runtime" in document
    assert "pins another workspace/ref takes precedence" in track_b_runbook
    assert "AGENTS.md` owns repository execution safety and owner routing" in track_b_runbook
    assert "실행 환경이 workspace/ref나 권한을 지정하면" in parallel_tracks
    assert "트랙 선택만으로 개별 surface의 paused/frozen" in parallel_tracks
    assert "상태를 해제하지 않는다" in parallel_tracks
    assert "할당된 workspace/ref" in parallel_tracks
    assert "실행 환경이 workspace/ref를 지정하면 해당 경계 우선" in a_track_runbook
    assert "이는 Ocean Rescue feature 전체의 동결 선언이 아니다." in a_track_runbook

    assert "기본 통합 기준은 `origin/main`" in project_rules
    assert "필수 검증 범위·계층·PASS/BLOCKED 판정" in project_rules
    assert "RISK_DIRECTED_VERIFICATION.md" in project_rules
    assert "선택된 remote publish ref" in execution
    assert "기본 통합 기준이자 기본 게시" in git_policy
    assert "Default integration branch: `main`" in profile

    machine_specific_workspace = "/Users/seungjulee/Desktop/Dev/.worktrees/game"
    for document in (execution, opencode, delegation, parallel_tracks, a_track_runbook, track_b_runbook):
        assert machine_specific_workspace not in document


def test_result_verdicts_and_reporting_format_have_a_single_owner() -> None:
    reporting = read("agents/core/reporting.md")
    agents = read("AGENTS.md")
    verification = read("agents/core/verification.md")
    risk = read("agents/RISK_DIRECTED_VERIFICATION.md")
    index = read("agents/registry/RULE_INDEX.md")
    a_track_runbook = read("docs/plans/PLAN_A_TRACK_RUNTIME_EXECUTION_RUNBOOK.md")
    track_b_runbook = read("docs/plans/AIDENGAME_OCEAN_RESCUE_TRACK_B_EXECUTION_RUNBOOK.md")

    assert "RESULT: PASS | BLOCKED" in reporting
    assert "RESULT: PASS | PARTIAL" not in agents
    assert "`PARTIAL`을 별도 verdict로 만들지 않는다" in reporting
    assert "`BLOCKED`로 기록하고" in agents
    assert "PUBLISH: NOT_APPLICABLE" in reporting
    assert "RESULT: PASS | BLOCKED" in track_b_runbook
    assert "RESULT: PASS | FAIL | BLOCKED" not in track_b_runbook
    assert "PUBLISH: PUBLISHED | NOT_APPLICABLE | BLOCKED" in track_b_runbook
    assert "`agents/core/reporting.md`" in track_b_runbook
    assert "RESULT: PASS | BLOCKED" in a_track_runbook
    assert "RESULT: PASS | FAIL | BLOCKED" not in a_track_runbook
    assert "PUBLISH: PUBLISHED | NOT_APPLICABLE | BLOCKED" in a_track_runbook
    assert "agents/core/reporting.md`가 소유한다" in a_track_runbook

    assert "RISK_DIRECTED_VERIFICATION.md" in verification
    assert "결과 판정을 재정의하지 않는다" in risk
    assert "필수 검증 범위와 PASS/BLOCKED 판정" in risk
    assert "RISK_DIRECTED_VERIFICATION.md" in index

    for relative in (
        "agents/core/opencode_tools.md",
        "agents/workflows/diagnose.md",
        "agents/workflows/plan.md",
        "agents/workflows/sync.md",
        "agents/registry/LOAD_ORDER.md",
    ):
        document = read(relative)
        assert "reporting.md" in document
        assert "RESULT / CHANGE / VERIFY" not in document
