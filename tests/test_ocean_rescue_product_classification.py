from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_SCOPE = ROOT / "docs/specs/product/ACTIVE_PRODUCT_SCOPE.md"
DOC_INDEX = ROOT / "docs/README.md"
MIGRATION_REFERENCE = (
    ROOT / "docs/plans/PLAN_ocean_rescue_vite_esm_typescript_migration.md"
)
FREEZE_NOTICE = ROOT / "docs/specs/OCEAN_RESCUE_FREEZE_NOTICE.md"
OCEAN_SPECS = (
    ROOT / "docs/specs/product/AIDENGAME_OCEAN_RESCUE_MVP_PRD.md",
    ROOT / "docs/specs/product/AIDENGAME_OCEAN_RESCUE_RENDERING_MVP.md",
    ROOT / "docs/specs/technical/AIDENGAME_OCEAN_RESCUE_DEVELOPMENT_ARCHITECTURE.md",
    ROOT / "docs/specs/technical/AIDENGAME_OCEAN_RESCUE_MANUAL_SVG_ASSET_HANDOFF.md",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_ocean_rescue_is_active_reward_game_not_product_level_frozen() -> None:
    scope = read(ACTIVE_SCOPE)
    index = read(DOC_INDEX)

    assert "Ocean Rescue | active reward-game product" in scope
    assert "학습 완료 후 즐기는 실제 보상 게임" in scope
    assert "Ocean Rescue gameplay 안에 산수/퀴즈 문제를 억지로 삽입하지 않는다" in scope
    assert "## 4. Active feature reference" in index
    assert index.count("`ACTIVE_FEATURE_REFERENCE`") >= len(OCEAN_SPECS)
    assert not FREEZE_NOTICE.exists()


def test_all_ocean_rescue_specs_remain_reachable_as_feature_contracts() -> None:
    index = read(DOC_INDEX)

    for spec in OCEAN_SPECS:
        assert spec.is_file()
        assert spec.name in index


def test_migration_reference_is_stable_technical_context_not_next_work() -> None:
    migration = read(MIGRATION_REFERENCE)

    assert "STABLE_TECHNICAL_REFERENCE_NOT_CURRENT_PRIORITY" in migration
    assert "Ocean Rescue feature 자체" in migration
    assert "active reward game" in migration
    assert "과거 migration 단계나 WP를 자동 재개하지 않는다" in migration
    assert "현재 기본 제품 priority는 Math skill/mastery adaptive loop" in migration


def test_cross_feature_learning_gate_is_owned_by_active_scope() -> None:
    scope = read(ACTIVE_SCOPE)

    assert "현재 목표를 완료해야 Ocean Rescue 자유시간을 사용할 수 있다" in scope
    assert "goal 완료" in scope
    assert "gems + free-time" in scope
    assert "→ Ocean Rescue / 허용된 자유시간 콘텐츠" in scope
