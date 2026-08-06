from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DISCOVER_WORKFLOW = ROOT / ".agents/workflows/discover.md"
DISCOVER_SKILL = ROOT / ".agents/skills/discover/SKILL.md"
REFACTOR_WORKFLOW = ROOT / ".agents/workflows/refactor.md"
REFACTOR_SKILL = ROOT / ".agents/skills/refactor/SKILL.md"
ARCH_WORKFLOW = ROOT / ".agents/workflows/improve-codebase-architecture.md"
ARCH_SKILL = ROOT / ".agents/skills/improve-codebase-architecture/SKILL.md"
FILES = (
    DISCOVER_WORKFLOW,
    DISCOVER_SKILL,
    REFACTOR_WORKFLOW,
    REFACTOR_SKILL,
    ARCH_WORKFLOW,
    ARCH_SKILL,
)
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


def test_discover_refactor_architecture_links_resolve() -> None:
    for document in FILES:
        assert document.is_file()
        for target in markdown_targets(document):
            assert target.exists(), f"{document}: broken link -> {target}"


def test_workflow_and_skill_pairs_reference_each_other() -> None:
    pairs = (
        (DISCOVER_WORKFLOW, DISCOVER_SKILL, "discover"),
        (REFACTOR_WORKFLOW, REFACTOR_SKILL, "refactor"),
        (ARCH_WORKFLOW, ARCH_SKILL, "improve-codebase-architecture"),
    )
    for workflow, skill, name in pairs:
        assert f"../skills/{name}/SKILL.md" in read(workflow)
        assert f"../../workflows/{name}.md" in read(skill)


def test_discover_is_read_first_without_auto_queue_or_blueprint() -> None:
    workflow = read(DISCOVER_WORKFLOW)
    skill = read(DISCOVER_SKILL)
    combined = workflow + "\n" + skill

    assert CURRENT_SPEC in workflow
    assert "기본적으로 read-only다." in workflow
    assert "queue JSON, timestamp Blueprint, backlog를 자동 생성하지 않는다." in workflow
    assert "첫 actionable candidate 하나" in workflow
    assert "동일 책임의 두 번째 실제 사용처" in workflow
    assert "자동으로 queue·artifact·Blueprint를 발급하지 않는다." in skill
    assert "최대 3개" in workflow

    forbidden = (
        "discover-seed",
        "discover-validate",
        "discover-emit",
        "discover-dead-seed",
        "impact_pilot.json",
        "hygiene_pilot.json",
        "PLAN_discover_implement",
        "DISC-R01",
        "AskQuestion",
        "야간 반복 루프",
        "500줄 초과",
    )
    for value in forbidden:
        assert value not in combined


def test_refactor_requires_real_repetition_and_preserves_current_scope() -> None:
    workflow = read(REFACTOR_WORKFLOW)
    skill = read(REFACTOR_SKILL)
    combined = workflow + "\n" + skill

    assert "동일 책임이 두 개 이상의 실제 caller에서 반복" in workflow
    assert "첫 대표 과목을 선제적으로 shared engine으로 이전하지 않는다." in workflow
    assert "두 번째 과목" in workflow
    assert "동결" in workflow
    assert "별도 plan handoff를 강제하지 않고" in workflow
    assert "public behavior" in skill
    assert "pass-through wrapper" in skill
    assert "plan·evidence 상태 변경 없음" in skill

    forbidden = (
        "EMR 프로젝트",
        "AskQuestion",
        "DISCUSS_*.md",
        "각 단계마다 한 턴",
        "`/plan` (기본 권장)",
        "RGR(Red-Green-Refactor) 패치",
    )
    for value in forbidden:
        assert value not in combined


def test_architecture_uses_real_seams_without_forced_option_expansion() -> None:
    workflow = read(ARCH_WORKFLOW)
    skill = read(ARCH_SKILL)
    combined = workflow + "\n" + skill

    assert "실제 caller" in workflow
    assert "deletion test" in workflow
    assert "실제 두 번째 adapter·caller" in workflow
    assert "file length나 AI 탐색 편의만으로" in workflow
    assert "여러 interface안을 형식적으로 생성" in workflow
    assert "caller 하나뿐이고 교체 가능성도 없으면 hypothetical seam을 만들지 않는다." in skill
    assert "현재 신규 architecture migration은 동결" in skill
    assert "method 수가 적다는 이유만으로 deep module은 아니다." in skill

    forbidden = (
        "Matt Pocock",
        "docs/plans/adr",
        "Design Twice (or Thrice)",
        "Option A (Minimal)",
        "Option B (Flexible)",
        "Option C (Common Case)",
        "Option D (Ports & Adapters)",
        "Which of these would you like to explore?",
        "Use these terms exactly",
    )
    for value in forbidden:
        assert value not in combined
