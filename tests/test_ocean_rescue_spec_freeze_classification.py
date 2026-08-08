from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_INDEX = ROOT / "docs/README.md"
FREEZE_NOTICE = ROOT / "docs/specs/OCEAN_RESCUE_FREEZE_NOTICE.md"
OCEAN_SPECS = (
    ROOT / "docs/specs/product/AIDENGAME_OCEAN_RESCUE_MVP_PRD.md",
    ROOT / "docs/specs/product/AIDENGAME_OCEAN_RESCUE_RENDERING_MVP.md",
    ROOT / "docs/specs/technical/AIDENGAME_OCEAN_RESCUE_DEVELOPMENT_ARCHITECTURE.md",
    ROOT / "docs/specs/technical/AIDENGAME_OCEAN_RESCUE_MANUAL_SVG_ASSET_HANDOFF.md",
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


def test_ocean_rescue_freeze_notice_links_resolve() -> None:
    for document in (DOC_INDEX, FREEZE_NOTICE):
        assert document.is_file()
        for target in markdown_targets(document):
            assert target.exists(), f"{document}: broken link -> {target}"


def test_every_ocean_rescue_spec_is_classified_as_frozen_reference() -> None:
    index = read(DOC_INDEX)
    notice = read(FREEZE_NOTICE)

    assert "## 5. Ocean Rescue spec 동결 분류" in index
    assert "OCEAN_RESCUE_FREEZE_NOTICE.md" in index
    for spec in OCEAN_SPECS:
        assert spec.is_file()
        assert spec.name in index
        assert spec.name in notice

    assert index.count("`PAUSED_REFERENCE_ONLY`") >= len(OCEAN_SPECS)
    assert "내부 maturity label을 실행 우선순위로 오인하지 않았는가" in index


def test_internal_maturity_labels_are_decoupled_from_execution_priority() -> None:
    notice = read(FREEZE_NOTICE)

    assert "상태:** `PAUSED_REFERENCE_ONLY`" in notice
    assert CURRENT_SPEC in notice
    assert "내부 계약 성숙도" in notice
    assert "현재 저장소의 실행 우선순위나 자동 재개 지시가 아니다" in notice
    assert "`IMPLEMENTATION_READY` ≠ 지금 구현 시작" in notice
    assert "`CANONICAL` ≠ 현재 제품 최우선" in notice
    assert "과거 migration plan의 단계 ≠ 현재 next work" in notice


def test_freeze_notice_matches_current_scope_and_exceptions() -> None:
    notice = read(FREEZE_NOTICE)

    assert "Math, English, Korean, Science" in notice
    assert "신규 mission" in notice
    assert "추가 TypeScript·ESM controller ownership 이전" in notice
    assert "신규 SVG/cutout/atlas production asset 제작" in notice
    assert "배포 entry가 열리지 않음" in notice
    assert "데이터 손상" in notice
    assert "보안 또는 credential 노출" in notice
    assert "독립 failure domain" in notice
    assert "한 failure domain과 binary criterion 하나" in notice


def test_freeze_notice_does_not_expand_exception_scope() -> None:
    notice = read(FREEZE_NOTICE)

    assert (
        "drift, rollback 검증 실패 또는 테스트 실패만으로는 예외가 성립하지 않는다"
        in notice
    )
    assert "- source, build metadata, tracked artifact의 명확한 drift" not in notice
    assert "- rollback 불능" not in notice
    assert "배포 차단 치명적 회귀, 데이터 손상 또는 보안 문제를 직접 증명" in notice


def test_freeze_notice_does_not_rewrite_product_contracts_as_schedule_state() -> None:
    notice = read(FREEZE_NOTICE)

    assert "문서 본문을 과거 기록으로 폐기한 것은 아니다." in notice
    assert "최신 main의 code, tests, build config, generated artifact와 drift" in notice
    assert "내부 status가 자동 실행 지시로 사용되지 않음" in notice
    assert "과목별 진행률" not in notice
    assert "다음 WP:" not in notice
