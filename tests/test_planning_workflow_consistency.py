from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLANNING = ROOT / ".agents/core/planning.md"
PLAN_WORKFLOW = ROOT / ".agents/workflows/plan.md"
GO_WORKFLOW = ROOT / ".agents/workflows/go.md"
ARCHIVE_WORKFLOW = ROOT / ".agents/workflows/archive.md"
WORKFLOW_FILES = (PLANNING, PLAN_WORKFLOW, GO_WORKFLOW, ARCHIVE_WORKFLOW)
CURRENT_SPEC = "docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def markdown_targets(path: Path) -> list[Path]:
    targets: list[Path] = []
    for raw_target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", read(path)):
        target = raw_target.split("#", 1)[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        targets.append((path.parent / target).resolve())
    return targets


def test_planning_workflow_links_resolve() -> None:
    for workflow in WORKFLOW_FILES:
        assert workflow.is_file()
        for target in markdown_targets(workflow):
            assert target.exists(), f"{workflow}: broken link -> {target}"


def test_chat_planning_is_default_and_blueprint_is_explicit_only() -> None:
    planning = read(PLANNING)
    workflow = read(PLAN_WORKFLOW)

    assert "일반적인 계획 요청은 채팅에서 처리한다." in planning
    assert "위 요청만으로 `docs/plans/` 파일을 만들지 않는다." in planning
    assert (
        "사용자가 파일 생성 또는 기존 Blueprint 사용을 명시적으로 요청한 경우에만"
        in planning
    )
    assert (
        "사용자가 **저장소에 Blueprint 또는 plan 문서를 만들라고 명시적으로 요청한 경우에만**"
        in workflow
    )
    assert "일반적인 “계획해줘”, “다음 작업 정리”, “이어서 진행”" in workflow


def test_planning_preserves_current_product_direction_and_atomic_work() -> None:
    combined = "\n".join(read(path) for path in (PLANNING, PLAN_WORKFLOW, GO_WORKFLOW))

    assert CURRENT_SPEC in combined
    assert "Math, English, Korean, Science" in combined
    assert "한 failure domain" in combined
    assert "한 binary criterion" in combined
    assert "Ocean Rescue" in combined
    assert "동결" in combined


def test_handoff_and_archive_do_not_create_status_document_churn() -> None:
    handoff = read(GO_WORKFLOW)
    archive = read(ARCHIVE_WORKFLOW)

    assert "다음 중 하나가 바뀐 경우에만 갱신한다." in handoff
    assert "과목별 진행률" in handoff
    assert "장기 일정" in handoff
    assert (
        "사용자가 **기존 저장소 Blueprint의 아카이브를 명시적으로 요청한 경우에만**"
        in archive
    )
    assert "현재 authority 문서" in archive
    assert (
        "다음 실행 경계나 authority가 바뀌지 않았다면 `MEMORY.md`를 수정하지 않는다."
        in archive
    )


def test_planning_docs_remove_foreign_and_automatic_plan_assumptions() -> None:
    combined = "\n".join(read(path) for path in WORKFLOW_FILES)
    forbidden = (
        "apps/renderer",
        "artifacts/verify/verify-last-result.json",
        "just plans-steer",
        "docs/plans/ROADMAP.md",
        "Linear-Issue",
        "LINEAR_API_KEY",
        "Google Antigravity",
        "Artifact-First (채팅 전용 계획 금지)",
        "채팅에만 장문 계획 (Blueprint 없음)",
        "docs/agent-context/memory/project_",
        "git add .",
        "archive() 함수",
    )
    for value in forbidden:
        assert value not in combined


def test_documented_plan_commands_exist_in_justfile() -> None:
    justfile = read(ROOT / "Justfile")
    plan_workflow = read(PLAN_WORKFLOW)

    commands = (
        "plan-preread",
        "plan-lint",
        "plan-task-close",
        "plan-close",
    )
    for command in commands:
        assert f"{command}:" in justfile or f"{command} " in justfile
        assert f"just {command}" in plan_workflow


def test_product_tests_are_decoupled_from_schedule_state_by_policy() -> None:
    planning = read(PLANNING)
    workflow = read(PLAN_WORKFLOW)

    assert "제품 테스트는 다음을 검증하지 않는다." in planning
    assert "다음 WP" in planning
    assert "현재 WP" in planning
    assert "문서의 COMPLETE 문자열" in planning
    assert (
        "제품 테스트에 계획 진행률이나 다음 작업 assertion을 추가하지 않는다."
        in workflow
    )
