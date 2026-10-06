from __future__ import annotations

from datetime import date
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_SCOPE = "docs/specs/product/ACTIVE_PRODUCT_SCOPE.md"
COMPLETED_RELIABILITY = "docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md"
MEMORY_VERIFY = "uv run pytest -q tests/test_active_product_scope_policy.py"


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_active_product_scope_is_the_single_product_direction_pointer() -> None:
    agents = read("AGENTS.md")
    project_rules = read("PROJECT_RULES.md")
    readme = read("README.md")
    docs_index = read("docs/README.md")
    memory = read("docs/agent-context/memory/MEMORY.md")

    for document in (agents, project_rules, readme, memory):
        assert ACTIVE_SCOPE in document

    assert "ACTIVE_PRODUCT_SCOPE.md" in docs_index
    assert "현재 제품 방향 단일 SSOT" in docs_index
    assert "ACTIVE_PRODUCT_SCOPE.md" in agents
    assert "Math mastery/adaptive loop" in readme


DIRECTION_OWNER_EXEMPT = (
    # The SSOT itself, plus documents that name subjects rather than restating direction.
    ACTIVE_SCOPE,
    "docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md",
    "docs/specs/product/AIDENGAME_OCEAN_RESCUE_MVP_PRD.md",
    "docs/specs/product/AIDENGAME_OCEAN_RESCUE_RENDERING_MVP.md",
    "docs/specs/product/AIDENGAME_YOUTUBE_FREE_TIME_SESSION.md",
)

RESTATED_DIRECTION_SENTENCES = (
    "현재 기본 방향은 Math, English, Korean, Science 일반 문제풀이 신뢰성 안정화다",
    "현재 기본 개발 방향은 일반 과목 문제풀이 안정화",
    "범위가 없는 요청은 현재 일반 과목 안정화 방향을 따른다",
    "현재 기본 개발 방향은 일반 과목",
    "일반 과목 문제풀이 신뢰성 우선",
    "네 과목 모두 안정화 후 신규 기능 재개",
    "현재 우선순위: Math, English, Korean, Science",
    "현재 확정된 방향은 `docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md`에 있다",
    "범위가 없는 진단은 `docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md`를 따른다",
    "범위가 지정되지 않은 조사는 일반 과목 안정화 계약을 기준으로 한다",
    "범위가 지정되지 않은 review follow-up은 일반 과목 안정화 우선순위를 따른다",
    "현재 일반 과목 안정화 계약은",
    "현재 일반 과목 안정화 방향과 실행 우선순위는",
    "범위가 없는 다음 작업은 일반 과목 공통 브라우저 진단으로 시작한다",
    "현재 기본 대상은 Math, English, Korean, Science",
    "첫 실행은 네 과목 공통 진단",
)


DELEGATED_DIRECTION_DOCS = (
    "agents/core/principles.md",
    "agents/core/planning.md",
    "agents/core/routing.md",
    "agents/core/opencode_tools.md",
    "agents/core/error_patterns.md",
    "agents/registry/LOAD_ORDER.md",
    "agents/registry/CONTEXT_ROUTING.md",
    "agents/registry/WORKFLOW_AND_SKILL_INDEX.md",
    "agents/workflows/go.md",
    "agents/workflows/plan.md",
    "agents/workflows/diagnose.md",
    "agents/workflows/investigate.md",
    "agents/workflows/discuss.md",
    "agents/workflows/review.md",
    "agents/workflows/refactor.md",
    "agents/workflows/sync.md",
    "agents/workflows/improve-codebase-architecture.md",
    "agents/skills/discover/SKILL.md",
    "docs/specs/technical/SPEC_orchestration.md",
)


def scoped_documents() -> list[str]:
    documents = []
    for pattern in ("agents/**/*.md", "docs/specs/technical/*.md"):
        for path in sorted(ROOT.glob(pattern)):
            relative = path.relative_to(ROOT).as_posix()
            if relative not in DIRECTION_OWNER_EXEMPT:
                documents.append(relative)
    return documents


def test_subordinate_docs_route_direction_to_ssot_instead_of_restating_it() -> None:
    documents = [
        relative
        for relative in scoped_documents()
        if relative in DELEGATED_DIRECTION_DOCS
    ]

    assert sorted(documents) == sorted(DELEGATED_DIRECTION_DOCS)
    for relative in documents:
        text = read(relative)
        for restated in RESTATED_DIRECTION_SENTENCES:
            assert restated not in text, (
                f"{relative}: restates product direction -> {restated}"
            )


def test_direction_routing_targets_actually_name_the_ssot() -> None:
    documents = scoped_documents()

    routed = [
        relative
        for relative in documents
        if "ACTIVE_PRODUCT_SCOPE.md" in read(relative)
    ]

    assert len(routed) >= 15
    for relative in documents:
        text = read(relative)
        if ACTIVE_SCOPE not in text:
            continue
        for raw_target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            target = raw_target.split("#", 1)[0]
            if not target or "://" in target:
                continue
            assert (ROOT / relative).parent.joinpath(target).resolve().is_file(), (
                f"{relative}: broken direction link -> {target}"
            )


def test_completed_reliability_contract_is_not_used_as_current_direction() -> None:
    completion_phrases = ("안정화 중", "안정화 방향", "안정화 계약", "안정화 우선순위")

    offenders = [
        (relative, phrase)
        for relative in DELEGATED_DIRECTION_DOCS
        for phrase in completion_phrases
        if phrase in read(relative)
    ]

    assert offenders == []


def test_agents_kernel_routes_instead_of_restating_delegated_contracts() -> None:
    agents = read("AGENTS.md")

    assert "권위 순서" in agents
    assert "권위 라우팅" in agents
    assert "Bounded execution invariants" in agents
    assert ACTIVE_SCOPE in agents

    for restated in (
        "Math curriculum skill → mastery → adaptive daily goal",
        "reliability stabilization은 완료된 baseline",
        "PAUSED_REFERENCE_ONLY",
        "V0 `BASELINE`",
        "just commit-gate-hard",
        "git worktree add",
        "WORKTREE_ROOT=",
    ):
        assert restated not in agents, restated


def test_scope_encodes_grilled_product_decisions_without_rpg_or_runtime_llm_drift() -> (
    None
):
    scope = read(ACTIVE_SCOPE)

    required = (
        "아이가 자발적으로 다시 들어온다",
        "부모 도움 없이 핵심 학습 흐름을 사용할 수 있다",
        "실제 학습 성취가 누적된다",
        "Galaxy Tab S10",
        "landscape-first",
        "세부 skill mastery",
        "Math",
        "deterministic",
        "spaced review",
        "약점 개선과 성공 경험의 균형",
        "학습 완료 후 즐기는 실제 보상 게임",
        "현실 보상 구매 시 보석은 실제로 차감",
        "local-first",
        "export/import backup",
        "runtime에서 LLM이 문제를 즉석 생성하지 않는다",
        "Space Explorer | `PAUSED_REFERENCE_ONLY`",
    )
    for value in required:
        assert value in scope

    assert "캐릭터 레벨업 중심 구조" in scope
    assert "RPG식 끝없는 meta progression" in scope
    assert "네 과목 전체 skill taxonomy 선설계" in scope


def test_core_quiz_reliability_is_completed_reference_not_current_priority() -> None:
    completed = read(COMPLETED_RELIABILITY)
    docs_index = read("docs/README.md")
    scope = read(ACTIVE_SCOPE)

    assert "Status:** `COMPLETED_REFERENCE`" in completed
    assert ACTIVE_SCOPE in completed
    assert "더 이상 현재 개발 우선순위나 다음 작업을 소유하지 않는다" in completed
    assert "`COMPLETED_REFERENCE`" in docs_index
    assert "reliability stabilization은 완료된 baseline" in scope


def test_memory_handoff_tracks_active_scope_and_stays_compact() -> None:
    memory = read("docs/agent-context/memory/MEMORY.md")

    assert len(memory.splitlines()) <= 200
    assert ACTIVE_SCOPE in memory
    assert "Math curriculum skill → mastery → adaptive daily goal" in memory
    assert "ProgressEngine" in memory
    assert "free-time-session.js" in memory
    assert MEMORY_VERIFY in memory

    match = re.search(r"^last_verified:\s*(\d{4}-\d{2}-\d{2})$", memory, re.MULTILINE)
    assert match is not None
    assert date.fromisoformat(match.group(1)) >= date(2026, 8, 16)


def test_scope_keeps_progress_tracking_out_of_product_ssot() -> None:
    scope = read(ACTIVE_SCOPE)

    assert "진행률을 이 문서에 계속 기록" in scope
    assert "개별 작업 완료, 커밋 SHA, 테스트 PASS 횟수" in scope
