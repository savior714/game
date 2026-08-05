"""Static proof for the WP-33E sea-turtle controller boundary scaffold.

Verifies:

A. controller file exists at the expected path
B. installer import exists in esm/app.js
C. installer order is correct (WP-33A < WP-33B < WP-33C < WP-33D < WP-33E)
D. controller does not contain addEventListener
E. controller does not reference Crab or Young Whale
F. controller does not contain mission-success progression functions
G. controller does not contain direct setTimeout calls
H. legacy manifest does not include the controller file
I. src/app.js still contains the existing sea-turtle implementation

This is a static-source contract test. No browser or runtime verification.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

REPO_ROOT = TESTS_DIR.parent
SRC_DIR = REPO_ROOT / "domains" / "ocean-rescue" / "src"
ESM_APP = SRC_DIR / "esm" / "app.js"
LEGACY_APP = SRC_DIR / "app.js"
CONTROLLER = SRC_DIR / "controllers" / "sea-turtle-lifecycle.ts"
LEGACY_MANIFEST = SRC_DIR / "build-manifest.legacy.json"


def test_controller_file_exists() -> None:
    """A: the typed controller file must exist at the expected path."""
    assert CONTROLLER.exists(), f"controller missing: {CONTROLLER}"


def test_installer_import_exists() -> None:
    """B: esm/app.js must import the sea-turtle lifecycle controller."""
    text = ESM_APP.read_text(encoding="utf-8")
    assert (
        'import { installSeaTurtleLifecycleController } from "../controllers/sea-turtle-lifecycle"'
        in text
    ), "esm/app.js must import installSeaTurtleLifecycleController"


def test_installer_order_is_correct() -> None:
    """C: installer chain order must be A < B < C < D < E."""
    text = ESM_APP.read_text(encoding="utf-8")

    installer_order = [
        "ProfileMissionSelection",
        "LaunchTravel",
        "RescueSiteTutorial",
        "PauseTimerResume",
        "SeaTurtleLifecycle",
    ]
    positions = []
    for name in installer_order:
        pattern = rf"const\s+\w+\s*=\s*install{name}Controller\s*\("
        match = re.search(pattern, text)
        assert match is not None, (
            f"missing installer for {name}: pattern {pattern!r} not found"
        )
        positions.append((name, match.start()))

    assert len(positions) == 5, f"expected 5 installers, found {len(positions)}"
    for i in range(len(positions) - 1):
        assert positions[i][1] < positions[i + 1][1], (
            f"{positions[i][0]} must appear before {positions[i + 1][0]}"
        )


def test_controller_has_no_add_event_listener() -> None:
    """D: the typed controller must not register DOM event listeners."""
    text = CONTROLLER.read_text(encoding="utf-8")
    matches = re.findall(r"\.addEventListener\s*\(", text)
    assert matches == [], (
        f"controller must not call addEventListener, found {len(matches)}"
    )


def test_controller_has_no_crab_or_young_whale() -> None:
    """E: the controller must not reference Crab or Young Whale."""
    text = CONTROLLER.read_text(encoding="utf-8")
    crab_matches = re.findall(r"\bCrab\b", text)
    young_whale_matches = re.findall(r"\bYoung\s+Whale\b", text)
    assert crab_matches == [], (
        f"controller must not reference Crab, found {len(crab_matches)}"
    )
    assert young_whale_matches == [], (
        f"controller must not reference Young Whale, found {len(young_whale_matches)}"
    )


def test_controller_has_no_mission_success_progression() -> None:
    """F: the controller must not contain mission-success progression functions."""
    text = CONTROLLER.read_text(encoding="utf-8")

    forbidden_patterns = [
        r"function\s+completeMissionSuccess",
        r"function\s+renderMissionSuccess",
        r"function\s+advanceMissionSuccessStage",
        r"completeMissionSuccess",
        "Missions.completeMission",
        "State.beginTransition",
    ]
    for pattern in forbidden_patterns:
        matches = re.findall(pattern, text)
        assert matches == [], (
            f"controller must not contain {pattern!r}, found: {matches}"
        )


def test_controller_has_no_direct_set_timeout() -> None:
    """G: the controller must not contain direct setTimeout calls."""
    text = CONTROLLER.read_text(encoding="utf-8")
    matches = re.findall(r"setTimeout\s*\(", text)
    assert matches == [], (
        f"controller must not call setTimeout directly, found {len(matches)}"
    )


def test_legacy_manifest_excludes_controller() -> None:
    """H: the legacy manifest must not include the typed controller file."""
    manifest = json.loads(LEGACY_MANIFEST.read_text(encoding="utf-8"))
    legacy_files = {e["file"] for e in manifest["scripts"]}
    assert "controllers/sea-turtle-lifecycle.ts" not in legacy_files, (
        "typed controller must not appear in legacy manifest"
    )


def test_legacy_app_retains_sea_turtle_implementation() -> None:
    """I: src/app.js must still contain the existing sea-turtle implementation."""
    text = LEGACY_APP.read_text(encoding="utf-8")

    required_patterns = [
        "startSeaTurtleInteraction",
        "handleSeaTurtlePointerDown",
        "onRescuePointerMove",
        "onRescuePointerUp",
        "beginSeaTurtleSuccessFeedback",
        "beginSeaTurtleFailureFeedback",
        "completeSeaTurtleFeedback",
        "completeSeaTurtleSuccess",
    ]
    for pattern in required_patterns:
        assert pattern in text, (
            f"legacy app.js must retain {pattern!r} — "
            f"sea-turtle behavior has not been migrated yet"
        )
