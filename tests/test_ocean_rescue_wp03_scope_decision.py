"""Guard the right-sized WP-03 target-device policy."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PLAN = (
    REPO_ROOT / "docs" / "plans" / "PLAN_ocean_rescue_vite_esm_typescript_migration.md"
)


def test_current_schedule_allows_wp30_before_physical_device_smoke() -> None:
    plan = PLAN.read_text(encoding="utf-8")
    header = plan.split("\n---\n", maxsplit=1)[0]

    assert "**Current phase:** PHASE_7_IN_PROGRESS" in header
    assert "**Next executable work package:** WP-32B" in header
    assert "**Production cutover gate:** SATISFIED" in header
    assert "WP-03A must pass before MVP release, but it does not block WP-21" in header
    assert "WP-03B is non-blocking follow-up work" in header

    assert "PHASE_4_READY_WITH_WP03_PENDING" not in header
    assert "Next executable work package:** WP-03" not in header
    assert "WP-03 required before WP-21" not in header


def test_wp03_is_split_into_release_smoke_and_non_blocking_harness() -> None:
    plan = PLAN.read_text(encoding="utf-8")

    assert "### WP-03A — Target-device release smoke" in plan
    assert (
        "MVP release gate; not a WP-21 production-packaging cutover prerequisite"
        in plan
    )
    assert "No canonical numeric frame-time or FPS SLA is defined" in plan

    assert "### WP-03B — Reproducible target-device performance harness" in plan
    assert "**Status:** BACKLOG_NON_BLOCKING" in plan
    assert "thresholds adopted only after baseline review" in plan

    assert "**Depends on:** WP-20 and WP-02" in plan
    assert "WP-03A remains mandatory before MVP release" in plan


def test_superseded_wp03_blocking_language_is_historical_only() -> None:
    plan = PLAN.read_text(encoding="utf-8")

    historical_marker = (
        "Historical WP-20 closure snapshot; retained as provenance "
        "and superseded for current scheduling:"
    )
    blocked_marker = "WP-21 remains blocked until WP-03"
    current_marker = "Current scheduling authority:"

    assert historical_marker in plan
    assert current_marker in plan
    assert plan.index(historical_marker) < plan.index(blocked_marker)
    assert plan.index(blocked_marker) < plan.index(current_marker)

    current = plan[plan.index(current_marker) :]
    assert "Next executable work package: WP-32B" in current
    assert "WP-21: COMPLETE" in current
    assert "WP-30: COMPLETE" in current
    assert "WP-31A: COMPLETE" in current
    assert "WP-31B: COMPLETE" in current
    assert "WP-31C: COMPLETE" in current
    assert "WP-32A: COMPLETE" in current
    assert "Profile module state: TYPED_CANONICAL" in current
    assert "Mission catalog state: TYPED_CANONICAL" in current
    assert "GUP catalog state: TYPED_CANONICAL" in current
    assert "Launch module state: TYPED_CANONICAL" in current
    assert "State module state: TYPED_CANONICAL" in current
    assert "Travel module state: TYPED_CANONICAL" in current
    assert "Legacy profile.js: ROLLBACK_ONLY" in current
    assert "Legacy missions.js: CONTROLLER_CANONICAL_PLUS_ROLLBACK" in current
    assert "Legacy gups.js: CONTROLLER_CANONICAL_PLUS_ROLLBACK" in current
    assert "Legacy launch.js: ROLLBACK_ONLY" in current
    assert "Legacy state.js: ROLLBACK_ONLY" in current
    assert "Legacy travel.js: ROLLBACK_ONLY" in current
    assert "WP-03B automated performance harness: BACKLOG_NON_BLOCKING" in current
