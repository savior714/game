from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DISCUSS_WORKFLOW = ROOT / ".agents/workflows/discuss.md"
DISCUSS_SKILL = ROOT / ".agents/skills/discuss/SKILL.md"
SYNC_WORKFLOW = ROOT / ".agents/workflows/sync.md"
SYNC_SKILL = ROOT / ".agents/skills/sync/SKILL.md"
FILES = (DISCUSS_WORKFLOW, DISCUSS_SKILL, SYNC_WORKFLOW, SYNC_SKILL)
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


def test_discuss_sync_links_resolve() -> None:
    for document in FILES:
        assert document.is_file()
        for target in markdown_targets(document):
            assert target.exists(), f"{document}: broken link -> {target}"


def test_discuss_and_sync_pairs_reference_each_other() -> None:
    assert "../skills/discuss/SKILL.md" in read(DISCUSS_WORKFLOW)
    assert "../../workflows/discuss.md" in read(DISCUSS_SKILL)
    assert "../skills/sync/SKILL.md" in read(SYNC_WORKFLOW)
    assert "../../workflows/sync.md" in read(SYNC_SKILL)


def test_discuss_uses_one_decision_axis_without_mandatory_tool_or_note() -> None:
    workflow = read(DISCUSS_WORKFLOW)
    skill = read(DISCUSS_SKILL)
    combined = workflow + "\n" + skill

    assert CURRENT_SPEC in workflow
    assert "한 질문 = 한 결정축" in workflow
    assert "상호 배타적" in workflow
    assert "권장 기본값은 정확히 하나" in workflow
    assert "표시된 권장안과 본문 결론이 일치" in workflow
    assert "질문 도구나 선택 메뉴를 형식적으로 호출하지 않고" in workflow
    assert "파일을 만들지 않는다" in workflow
    assert "이미 확정된 축을 다시 질문하지 않는다." in workflow
    assert "필수 handoff menu" in workflow
    assert "자동으로 Blueprint" in workflow
    assert "단순 진행 기록용 `DISCUSS_*.md`를 자동 생성하지 않는다." in workflow
    assert "모든 논의에서 예외 질문을 형식적으로 삽입하지 않는다." in skill

    forbidden = (
        "AskQuestion",
        "question`(병용)",
        "Ambiguity-Zero",
        "same-session plan",
        "close 턴 필수",
        "18줄 이내",
        "2~3턴마다",
        "deep-research",
        "just route",
        "PROJECT_REFACTORING_BACKLOG",
    )
    for value in forbidden:
        assert value not in combined


def test_sync_compares_claims_without_fake_spec_sync_cli() -> None:
    workflow = read(SYNC_WORKFLOW)
    skill = read(SYNC_SKILL)
    combined = workflow + "\n" + skill

    assert "implementation drift" in workflow
    assert "documentation drift" in workflow
    assert "현재 `Justfile`의 `sync` recipe는 dependency/environment 동기화용 `uv sync`다." in workflow
    assert "MATCH" in skill
    assert "DOC_STALE" in skill
    assert "IMPLEMENTATION_VIOLATION" in skill
    assert "UNVERIFIED" in skill
    assert "현재 `just sync`는 `uv sync` recipe" in skill
    assert "PAUSED_REFERENCE_ONLY" in skill
    assert "모든 문서를 동시에 최신화하려 하지 않고" in skill

    forbidden = (
        "just sync --check",
        "@code-sync-lock",
        "renderer-route-smoke",
        "next.config",
        "proxy",
        "apps/renderer",
        "React",
        "Biome",
        "ConsultationPage",
        "Form catalog",
        "ROADMAP.md",
        "scripts/agent/sync.py",
        "spec_integrated_sync_roadmap",
        "자동 spec",
    )
    for value in forbidden:
        assert value not in combined
