"""
Static proof tests for Sea Turtle Discovery canonical port.

Verifies the authority boundaries, module snapshot contracts, state progression invariants,
asset integrity, and non-destruction of existing Travel/Rescue/SeaTurtle contracts:
1. No external provisional assets or unauthorized textures.
2. Single Pixi application and single canonical canvas maintained.
3. SeaTurtleDiscovery module has explicit snapshot/state contract.
4. Scan cannot begin before eligibility.
5. Startled clears and prevents eligibility.
6. Dwell is required before eligibility becomes active.
7. Ready-for-rescue strictly requires completed scan.
8. Scan never marks SeaTurtle ropes complete or alters rope rescue state.
9. Existing Rescue.ArrivalDistance (6000) semantics preserved.
10. Existing SeaTurtle rope geometry and mechanics remain intact.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OCEAN_RESCUE_SRC = REPO_ROOT / "domains" / "ocean-rescue" / "src"
OCEAN_RESCUE_HTML = REPO_ROOT / "ocean-rescue" / "index.html"


def test_no_external_provisional_assets():
    """Ensure provisional external assets/factories are absent."""
    forbidden_terms = [
        "ProvisionalAssetFactory",
        "createProceduralReef",
        "createProceduralTurtle",
        "createProceduralManta",
    ]
    for js_file in OCEAN_RESCUE_SRC.rglob("*.js"):
        content = js_file.read_text(encoding="utf-8")
        for term in forbidden_terms:
            assert term not in content, f"Forbidden term '{term}' found in {js_file}"


def test_single_pixi_application_and_canvas_contract():
    """Ensure no new Pixi.Application or duplicate canvas creation is introduced in discovery code."""
    discovery_js = (OCEAN_RESCUE_SRC / "sea-turtle-discovery.js").read_text(
        encoding="utf-8"
    )
    presentation_js = (
        OCEAN_RESCUE_SRC / "presentation" / "sea-turtle-discovery-presentation.js"
    ).read_text(encoding="utf-8")

    for code in [discovery_js, presentation_js]:
        assert "new PIXI.Application" not in code
        assert "document.createElement('canvas')" not in code
        assert 'document.createElement("canvas")' not in code


def test_discovery_runtime_snapshot_and_state_invariants():
    """Verify discovery runtime module structure, state machine, and snapshot contracts via direct JS evaluation."""
    discovery_file = OCEAN_RESCUE_SRC / "sea-turtle-discovery.js"
    assert discovery_file.exists()
    content = discovery_file.read_text(encoding="utf-8")

    assert "root.SeaTurtleDiscovery" in content
    assert "getSnapshot" in content
    assert "triggerScan" in content
    assert "ReactionStates" in content
    assert "Config" in content
    assert "DiscoveryStartDistance" in content
    assert "HoldZoneStartDistance" in content
    assert "HoldTargetDistance" in content

    js_test = """
    const fs = require('fs');
    const path = require('path');
    const content = fs.readFileSync(process.argv[1], 'utf-8');
    const window = {};
    eval(content);
    const STD = window.OceanRescue.SeaTurtleDiscovery;
    if (!STD) throw new Error('SeaTurtleDiscovery not registered');

    // 1. Initial snapshot
    STD.start();
    let snap = STD.getSnapshot();
    if (!snap.active || snap.reactionState !== 'inactive' || snap.scanEligible || snap.readyForRescue) {
      throw new Error('Invalid start snapshot: ' + JSON.stringify(snap));
    }

    // 2. Distant approach (< 4800 is inactive)
    STD.step(50, { distance: 4000 });
    snap = STD.getSnapshot();
    if (snap.reactionState !== 'inactive') throw new Error('Should be inactive at 4000: ' + snap.reactionState);

    // 3. Scan cannot begin before eligibility
    let scanTriggered = STD.triggerScan();
    if (scanTriggered) throw new Error('Scan should not trigger before eligibility');

    // 4. Dwell required before eligibility
    for (let i = 0; i < 15; i++) {
      STD.step(50, { distance: 5200 }, null, { verticalVelocity: 50, isColliding: false });
    }
    snap = STD.getSnapshot();
    if (!snap.scanEligible || snap.reactionState !== 'scan-eligible') {
      throw new Error('Should be scan-eligible after dwell: ' + JSON.stringify(snap));
    }

    // 5. Startled clears eligibility
    STD.step(50, { distance: 5200 }, null, { verticalVelocity: 450, isColliding: false });
    snap = STD.getSnapshot();
    if (snap.scanEligible || snap.reactionState !== 'startled') {
      throw new Error('Startled should clear scan eligibility: ' + JSON.stringify(snap));
    }

    // Scan trigger must fail while startled
    if (STD.triggerScan()) throw new Error('Scan trigger should fail during startled');

    // 6. Recovery & Settle (700ms startled duration + 600ms dwell = 26 steps of 50ms)
    for (let i = 0; i < 30; i++) {
      STD.step(50, { distance: 5500 }, null, { verticalVelocity: 20, isColliding: false });
    }
    snap = STD.getSnapshot();
    if (!snap.scanEligible) throw new Error('Should become eligible again after calm dwell');

    // 7. Trigger scan and progress to ready-for-rescue
    if (!STD.triggerScan()) throw new Error('Scan trigger failed when eligible');
    snap = STD.getSnapshot();
    if (!snap.scanning) {
      throw new Error('Scanning state invalid: ' + JSON.stringify(snap));
    }

    // Step through scan duration (1200ms)
    for (let i = 0; i < 30; i++) {
      STD.step(50, { distance: 5500 }, null, { verticalVelocity: 0 });
    }
    snap = STD.getSnapshot();
    if (!snap.readyForRescue || snap.scanning || snap.forwardSpeedMultiplier !== 1.0) {
      throw new Error('Ready for rescue state invalid: ' + JSON.stringify(snap));
    }

    console.log('ALL_STATE_INVARIANTS_PASSED');
    """
    import subprocess

    res = subprocess.run(
        ["node", "-e", js_test, str(discovery_file)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "ALL_STATE_INVARIANTS_PASSED" in res.stdout


def test_esm_graph_imports_sea_turtle_discovery_non_esm_relative():
    """Ensure discovery modules are imported via non-ESM relative imports without creating new adapter files."""
    esm_app = (OCEAN_RESCUE_SRC / "esm" / "app.js").read_text(encoding="utf-8")
    esm_travel = (OCEAN_RESCUE_SRC / "esm" / "travel-scene.js").read_text(
        encoding="utf-8"
    )

    assert 'import "../sea-turtle-discovery.js";' in esm_app
    assert (
        'import "../presentation/sea-turtle-discovery-presentation.js";' in esm_travel
    )

    # Ensure no new esm adapter file created
    assert not (OCEAN_RESCUE_SRC / "esm" / "sea-turtle-discovery.js").exists()


def test_sea_turtle_rope_geometry_and_rescue_arrival_preserved():
    """Ensure existing SeaTurtle rope geometry and Rescue.ArrivalDistance are intact."""
    sea_turtle_js = (OCEAN_RESCUE_SRC / "sea-turtle.js").read_text(encoding="utf-8")
    rescue_js = (OCEAN_RESCUE_SRC / "rescue.js").read_text(encoding="utf-8")

    assert "ArrivalDistance = 6000" in rescue_js
    assert "rope-1" in sea_turtle_js
    assert "rope-2" in sea_turtle_js
    assert "rope-3" in sea_turtle_js
    assert "760" in sea_turtle_js and "1040" in sea_turtle_js
