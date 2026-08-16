from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_INDEX = ROOT / "docs/README.md"
ACTIVE_SCOPE = ROOT / "docs/specs/product/ACTIVE_PRODUCT_SCOPE.md"
SPACE_REFERENCE = ROOT / "docs/SPACE_EXPLORER_PLAN.md"
OCEAN_REFERENCE = ROOT / "docs/plans/PLAN_ocean_rescue_vite_esm_typescript_migration.md"
COMPLETED_RELIABILITY = ROOT / "docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def local_markdown_targets(path: Path) -> list[Path]:
    targets: list[Path] = []
    for raw_target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", read(path)):
        target = raw_target.split("#", 1)[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        targets.append((path.parent / target).resolve())
    return targets


def test_document_index_links_resolve() -> None:
    assert DOC_INDEX.is_file()
    for target in local_markdown_targets(DOC_INDEX):
        assert target.exists(), f"broken docs index link: {target}"


def test_active_completed_and_frozen_documents_are_classified_separately() -> None:
    index = read(DOC_INDEX)

    assert "## 2. 현재 권위 문서" in index
    assert "ACTIVE_PRODUCT_SCOPE.md" in index
    assert "현재 제품 방향 단일 SSOT" in index

    assert "## 3. 완료된 제품 계약" in index
    assert "CORE_QUIZ_RELIABILITY_STABILIZATION.md" in index
    assert "`COMPLETED_REFERENCE`" in index

    assert "## 4. Active feature reference" in index
    assert "AIDENGAME_OCEAN_RESCUE_MVP_PRD.md" in index
    assert "`ACTIVE_FEATURE_REFERENCE`" in index
    assert "PLAN_ocean_rescue_vite_esm_typescript_migration.md" in index
    assert "`STABLE_TECHNICAL_REFERENCE_NOT_CURRENT_PRIORITY`" in index

    assert "## 5. 동결 기술 참고" in index
    assert "SPACE_EXPLORER_PLAN.md" in index
    assert "`PAUSED_REFERENCE_ONLY`" in index

    assert "OCEAN_RESCUE_FREEZE_NOTICE.md" not in index
    assert "과거 plan, evidence, 완료 보고, WP 번호" in index


def test_active_scope_owns_product_priority_not_completed_or_feature_references() -> None:
    scope = read(ACTIVE_SCOPE)
    completed = read(COMPLETED_RELIABILITY)
    ocean = read(OCEAN_REFERENCE)
    space = read(SPACE_REFERENCE)

    assert "CANONICAL_ACTIVE_PRODUCT_SSOT" in scope
    assert "현재 최우선 개발 방향" in scope

    assert "COMPLETED_REFERENCE" in completed
    assert "더 이상 현재 개발 우선순위나 다음 작업을 소유하지 않는다" in completed

    assert "STABLE_TECHNICAL_REFERENCE_NOT_CURRENT_PRIORITY" in ocean
    assert "Ocean Rescue feature 자체" in ocean
    assert "active reward game" in ocean

    assert "PAUSED_REFERENCE_ONLY" in space
    assert "명시적으로 결정" in space


def test_readme_uses_active_scope_and_current_feature_classification() -> None:
    readme = read(ROOT / "README.md")

    assert "docs/specs/product/ACTIVE_PRODUCT_SCOPE.md" in readme
    assert "Math mastery/adaptive loop" in readme
    assert "Ocean Rescue | 운영중·active feature" in readme
    assert "Space Explorer | 운영중 artifact·개발 동결" in readme
    assert "Ocean Rescue toolchain" in readme
    assert "현재 개발 동결" not in readme
    assert "docs/plans/PLAN_ocean_rescue_vite_esm_typescript_migration.md" in readme
    assert "`verify.sh`" in readme
