from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_INDEX = ROOT / "docs/README.md"
SPACE_REFERENCE = ROOT / "docs/SPACE_EXPLORER_PLAN.md"
OCEAN_REFERENCE = ROOT / "docs/plans/PLAN_ocean_rescue_vite_esm_typescript_migration.md"
CURRENT_SPEC = "docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md"


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


def test_current_and_frozen_documents_are_classified_separately() -> None:
    index = read(DOC_INDEX)

    assert "## 2. 현재 실행 권위" in index
    assert "## 3. 동결 기술 참고" in index
    assert (
        CURRENT_SPEC in index
        or "specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md" in index
    )
    assert "SPACE_EXPLORER_PLAN.md" in index
    assert "PLAN_ocean_rescue_vite_esm_typescript_migration.md" in index
    assert index.count("PAUSED_REFERENCE_ONLY") >= 2
    assert (
        "과거 plan, evidence, 완료 보고, WP 번호는 현재 실행 순서를 정하지 않는다."
        in index
    )


def test_frozen_feature_references_do_not_publish_next_work() -> None:
    references = (read(SPACE_REFERENCE), read(OCEAN_REFERENCE))

    for document in references:
        assert "PAUSED_REFERENCE_ONLY" in document
        assert (
            CURRENT_SPEC in document
            or "specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md" in document
        )
        assert "없음" in document or "NONE_WHILE_PAUSED" in document
        assert "사용자가 현재 요청에서 명시적으로" in document
        assert (
            "현재 작업 선택의 권위가 아니다" in document
            or "현재 실행 순서를 정하지 않는다" in document
            or "현재 작업 선택의 근거로 사용하지 않는다" in document
        )

    ocean = references[1]
    assert "한 failure domain" in ocean
    assert "한 binary criterion" in ocean
    assert (
        "테스트에서 `다음 WP`, `현재 WP`, `WP COMPLETE` 같은 일정 상태를 검증하지 않는다."
        in ocean
    )


def test_frozen_ocean_plan_does_not_expand_operational_exceptions() -> None:
    ocean = read(OCEAN_REFERENCE)

    assert (
        "artifact drift, rollback 검증 실패 또는 테스트 실패만으로는 운영 예외가 성립하지 않는다"
        in ocean
    )
    assert "- 현재 배포 artifact가 source/build 계약과 불일치함" not in ocean
    assert "- rollback이 동작하지 않음" not in ocean
    assert "배포 차단 치명적 회귀, 데이터 손상 또는 보안 문제를 직접 증명" in ocean


def test_frozen_space_plan_does_not_expand_operational_exceptions() -> None:
    space = read(SPACE_REFERENCE)

    assert (
        "page error, console error, failed request 또는 정적 자산 이상만으로는 운영 예외가 성립하지 않는다"
        in space
    )
    assert "- 현재 배포에서 페이지 오류가 발생함" not in space
    assert "- 기존 정적 자산 손상" not in space
    assert "배포 차단 치명적 회귀, 데이터 손상 또는 보안 문제를 직접 증명" in space


def test_readme_labels_frozen_tooling_as_reference() -> None:
    readme = read(ROOT / "README.md")

    assert "docs/README.md" in readme
    assert "Ocean Rescue toolchain 참고 — 현재 개발 동결" in readme
    assert (
        "현재 작업 목록이 아니라 유지보수·치명적 회귀 대응을 위한 기술 참고" in readme
    )
    assert "docs/SPACE_EXPLORER_PLAN.md" in readme
    assert "docs/plans/PLAN_ocean_rescue_vite_esm_typescript_migration.md" in readme
    assert "`experiments/space-explorer.html`" in readme
    assert "`verify.sh`" in readme
