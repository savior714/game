"""Guard stable target-device release and performance policy."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCE = (
    REPO_ROOT / "docs" / "plans" / "PLAN_ocean_rescue_vite_esm_typescript_migration.md"
)


def test_release_smoke_and_performance_harness_have_distinct_roles() -> None:
    reference = REFERENCE.read_text(encoding="utf-8")

    assert "### WP-03A — Target-device release smoke" in reference
    assert (
        "MVP release gate; not a WP-21 production-packaging cutover prerequisite"
        in reference
    )
    assert "WP-03A remains mandatory before MVP release" in reference
    assert "No canonical numeric frame-time or FPS SLA is defined" in reference

    assert "### WP-03B — Reproducible target-device performance harness" in reference
    assert "Classification:** `BACKLOG_NON_BLOCKING`" in reference
    assert "thresholds adopted only after baseline review" in reference
    assert (
        "WP-03B가 없다는 이유로 현재 production packaging이나 일반 과목 안정화 작업을 차단하지 않는다."
        in reference
    )


def test_target_device_policy_is_product_contract_not_schedule_state() -> None:
    reference = REFERENCE.read_text(encoding="utf-8")
    section = reference.split("## 7. Target-device release와 성능 정책", maxsplit=1)[1]
    section = section.split("## 8. 검증 참고", maxsplit=1)[0]

    assert "release acceptance와 후속 측정의 역할을 구분한다" in section
    assert "두 항목을 하나의 일정 문자열로 결합하지 않는다" in section
    assert "Next executable work package" not in section
    assert "Current scheduling authority" not in section
    assert "WP COMPLETE" not in section
