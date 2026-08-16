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
    assert "Math curriculum skill → mastery → adaptive daily goal" in agents
    assert "Math mastery/adaptive loop" in readme


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
    agents = read("AGENTS.md")

    assert "Status:** `COMPLETED_REFERENCE`" in completed
    assert ACTIVE_SCOPE in completed
    assert "더 이상 현재 개발 우선순위나 다음 작업을 소유하지 않는다" in completed
    assert "`COMPLETED_REFERENCE`" in docs_index
    assert "reliability stabilization은 완료된 baseline" in agents


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
