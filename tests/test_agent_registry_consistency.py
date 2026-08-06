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
ROUTING_FILES = (*REGISTRY_FILES, CORE_ROUTING)
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

    ordered = (
        "사용자의 현재 요청",
        "AGENTS.md",
        "PROJECT_RULES.md",
        "최신 `origin/main`의 코드·테스트·설정",
    )
    for document in (load_order, core_routing):
        positions = [document.index(value) for value in ordered]
        assert positions == sorted(positions)

    assert (
        "사용자의 현재 요청 → AGENTS.md → PROJECT_RULES.md와 가장 가까운 "
        "product/technical spec → 최신 code/tests/config"
    ) in context_routing


def test_core_routing_declares_manual_current_tool_policy() -> None:
    routing = read(CORE_ROUTING)

    assert "현재 세션에 실제로 제공된 도구" in routing
    assert "현재 저장소에는 별도의 자동 route CLI" in routing
    assert "한 작업에는 하나의 failure domain" in routing
    assert "게시 직전 `origin/main` 이동 여부" in routing
    assert "대형 파일을 전체 교체할 때는 게시 전에 원본과 후보 diff" in routing


def test_registry_indexes_every_installed_workflow_and_skill() -> None:
    index = read(REGISTRY_FILES[3])

    for workflow in sorted((ROOT / ".agents/workflows").glob("*.md")):
        assert f"../workflows/{workflow.name}" in index

    for skill in sorted((ROOT / ".agents/skills").glob("*/SKILL.md")):
        relative = skill.relative_to(ROOT / ".agents/skills").as_posix()
        assert f"../skills/{relative}" in index
