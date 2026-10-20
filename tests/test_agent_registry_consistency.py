from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_FILES = (
    ROOT / ".agents/registry/LOAD_ORDER.md",
    ROOT / ".agents/registry/CONTEXT_ROUTING.md",
    ROOT / ".agents/registry/RULE_INDEX.md",
    ROOT / ".agents/registry/WORKFLOW_AND_SKILL_INDEX.md",
)
CORE_ROUTING = ROOT / ".agents/core/routing.md"
CORE_EXECUTION = ROOT / ".agents/core/execution.md"
ROUTING_FILES = (*REGISTRY_FILES, CORE_ROUTING)
CURRENT_SPEC = "docs/specs/product/ACTIVE_PRODUCT_SCOPE.md"


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


def test_routing_links_resolve_to_existing_files() -> None:
    for routing_file in ROUTING_FILES:
        assert routing_file.is_file()
        for target in markdown_targets(routing_file):
            assert target.exists(), f"{routing_file}: broken link -> {target}"


def test_routing_uses_aidengame_paths_and_real_commands_only() -> None:
    combined = "\n".join(read(path) for path in ROUTING_FILES)

    foreign_or_removed = (
        "apps/renderer",
        "packages/",
        "src/domain",
        "src/api",
        "FHIR",
        "KR Core",
        "Zustand",
        "PROJECT_SKILL_ROUTING.json",
        "SKILL_CATALOG.json",
        "just route ",
        "route-smart",
        "route-gate-check",
        "context-t0-estimate",
        "context-budget-validate",
        "AGENTS.md §0",
        "PROJECT_RULES > AGENTS",
        "Google Antigravity",
        "Cursor IDE",
        "StrReplace",
        "replace_file_content",
    )
    for value in foreign_or_removed:
        assert value not in combined

    assert CURRENT_SPEC in combined
    assert "domains/math/" in combined
    assert "domains/english/" in combined
    assert "domains/korean/" in combined
    assert "domains/science/" in combined


def test_routing_precedence_matches_agents_contract() -> None:
    load_order = read(REGISTRY_FILES[0])
    context_routing = read(REGISTRY_FILES[1])
    core_routing = read(CORE_ROUTING)

    for document in (load_order, context_routing, core_routing):
        assert "domain별 owner" in document or "domain에 따라" in document
        assert "ACTIVE_PRODUCT_SCOPE.md" in document
        assert "PROJECT_RULES.md" in document
        assert "구현 증거" in document or "implementation evidence" in document

    assert "사용자의 현재 요청 → AGENTS.md → PROJECT_RULES.md" not in context_routing
    assert "CORE_QUIZ_RELIABILITY_STABILIZATION.md" in core_routing
    assert "해당 완료 계약이나 실제 회귀를 다룰 때만" in core_routing


def test_core_routing_declares_manual_current_tool_policy() -> None:
    routing = read(CORE_ROUTING)

    assert "현재 세션에 실제로 제공된 도구" in routing
    assert "현재 저장소에는 별도의 자동 route CLI" in routing
    assert "한 작업에는 하나의 failure domain" in routing
    assert "선택된 publish ref 이동 여부" in routing
    assert "대형 파일을 전체 교체할 때는 게시 전에 원본과 후보 diff" in routing


def test_rule_index_classifies_core_routing_as_current_policy() -> None:
    index = read(REGISTRY_FILES[2])
    execution = read(CORE_EXECUTION)
    routing = read(CORE_ROUTING)

    assert "[`routing.md`](../core/routing.md)" in index
    assert "legacy reference" not in index
    assert "[`routing.md`](routing.md)" in execution
    assert "현재 세션에 실제로 제공된 도구" in routing


def test_registry_indexes_every_installed_workflow_and_skill() -> None:
    index = read(REGISTRY_FILES[3])

    for workflow in sorted((ROOT / ".agents/workflows").glob("*.md")):
        assert f"../workflows/{workflow.name}" in index

    for skill in sorted((ROOT / ".agents/skills").glob("*/SKILL.md")):
        relative = skill.relative_to(ROOT / ".agents/skills").as_posix()
        assert f"../skills/{relative}" in index
