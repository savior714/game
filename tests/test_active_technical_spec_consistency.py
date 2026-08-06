from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_INDEX = ROOT / "docs/README.md"
DESIGN = ROOT / "docs/specs/technical/DESIGN.md"
ORCHESTRATION = ROOT / "docs/specs/technical/SPEC_orchestration.md"


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


def test_active_technical_spec_links_resolve() -> None:
    for document in (DOC_INDEX, DESIGN, ORCHESTRATION):
        assert document.is_file()
        for target in markdown_targets(document):
            assert target.exists(), f"{document}: broken link -> {target}"


def test_design_reference_uses_current_runtime_entries_without_fake_rewrite() -> None:
    design = read(DESIGN)

    assert "status: STABLE_REFERENCE_NOT_CURRENT_PRIORITY" in design
    assert "Runtime Entry and Routing SSOT" in design
    assert "`index.html`" in design
    assert "`experiments/space-explorer/index.html`" in design
    assert "`experiments/space-explorer/main.js`" in design
    assert "`ocean-rescue/index.html`" in design
    assert "`vercel.json`" in design
    assert '"rewrites": []' in design
    assert "`/space-explorer.html`" in design
    assert "현재 entry가 아니다" in design
    assert "순수 시각 리디자인·장식·애니메이션 개선은 안정화 이후" in design

    forbidden = (
        "/space-explorer.html` ->",
        "Design SSOT",
        "author: Antigravity",
        "신규 UI는 이 패턴을 우선 상속",
    )
    for value in forbidden:
        assert value not in design


def test_orchestration_is_optional_legacy_library_not_execution_authority() -> None:
    spec = read(ORCHESTRATION)

    assert "status: LEGACY_REFERENCE_ONLY" in spec
    assert "current_execution_authority: AGENTS.md" in spec
    assert "현재 AidenGame 작업의 필수 실행 파이프라인이나 자동 dispatch authority가 아니다." in spec
    assert "자동 실행하지 않는다." in spec
    assert "한 failure domain" in spec
    assert "한 binary criterion" in spec
    assert "scripts/agent/orchestration/spec.py" in spec
    assert "tests/test_orchestration_pipeline.py" in spec
    assert "legacy enum과 helper 존재를 현재 작업 의무로 확대 해석하지 않는다." in spec
    assert "존재하지 않는 `just route` 또는 route manifest를 필수 gate로 요구" in spec
    assert "모든 작업을 analyzer → dispatcher → auditor → fixer → final auditor로 강제" in spec

    forbidden = (
        "AGENTS.md §2.3",
        "Each TaskSpec → one `task` tool call",
        "Structured 5-phase multi-agent orchestration with typed contracts",
    )
    for value in forbidden:
        assert value not in spec


def test_docs_index_classifies_stable_and_legacy_technical_references() -> None:
    index = read(DOC_INDEX)

    assert "## 4. 안정·legacy 기술 참고" in index
    assert "specs/technical/DESIGN.md" in index
    assert "STABLE_REFERENCE_NOT_CURRENT_PRIORITY" in index
    assert "specs/technical/SPEC_orchestration.md" in index
    assert "LEGACY_REFERENCE_ONLY" in index
    assert "현재 필수 workflow 아님" in index
