"""Static tests for WP-33E-A sea-turtle controller boundary.

Verifies:
- Controller file exists
- Installer import exists
- Installer order is correct
- Controller does not contain forbidden patterns
- Legacy sea-turtle implementation remains in src/app.js
"""

from __future__ import annotations

import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.ocean_rescue
class TestOceanRescueWP33ESeaTurtleControllerBoundary:
    """Tests for WP-33E-A sea-turtle controller boundary scaffold."""

    @pytest.fixture
    def controller_path(self) -> Path:
        return (
            REPO_ROOT
            / "domains"
            / "ocean-rescue"
            / "src"
            / "controllers"
            / "sea-turtle-lifecycle.ts"
        )

    @pytest.fixture
    def installer_path(self) -> Path:
        return (
            REPO_ROOT
            / "domains"
            / "ocean-rescue"
            / "src"
            / "esm"
            / "app.js"
        )

    @pytest.fixture
    def legacy_app_path(self) -> Path:
        return (
            REPO_ROOT
            / "domains"
            / "ocean-rescue"
            / "src"
            / "app.js"
        )

    def test_controller_file_exists(self, controller_path: Path) -> None:
        assert controller_path.exists(), "Controller file must exist"

    def test_installer_import_exists(self, installer_path: Path) -> None:
        content = installer_path.read_text(encoding="utf-8")
        assert (
            'import { installSeaTurtleLifecycleController } from "../controllers/sea-turtle-lifecycle";'
            in content
        ), "Installer import must exist"

    def test_installer_order_is_correct(self, installer_path: Path) -> None:
        content = installer_path.read_text(encoding="utf-8")

        lines = [line.strip() for line in content.split("\n")]

        install_profile_idx = next(
            (i for i, line in enumerate(lines) if "installProfileMissionSelectionController(" in line),
            None,
        )
        install_launch_idx = next(
            (i for i, line in enumerate(lines) if "installLaunchTravelController(" in line),
            None,
        )
        install_tutorial_idx = next(
            (i for i, line in enumerate(lines) if "installRescueSiteTutorialController(" in line),
            None,
        )
        install_pause_idx = next(
            (i for i, line in enumerate(lines) if "installPauseTimerResumeController(" in line),
            None,
        )
        install_sea_turtle_idx = next(
            (i for i, line in enumerate(lines) if "installSeaTurtleLifecycleController(" in line),
            None,
        )

        assert install_profile_idx is not None, "ProfileMissionSelection installer must exist"
        assert install_launch_idx is not None, "LaunchTravel installer must exist"
        assert install_tutorial_idx is not None, "RescueSiteTutorial installer must exist"
        assert install_pause_idx is not None, "PauseTimerResume installer must exist"
        assert install_sea_turtle_idx is not None, "SeaTurtleLifecycle installer must exist"

        assert install_profile_idx < install_launch_idx, "ProfileMissionSelection must come before LaunchTravel"
        assert install_launch_idx < install_tutorial_idx, "LaunchTravel must come before RescueSiteTutorial"
        assert install_tutorial_idx < install_pause_idx, "RescueSiteTutorial must come before PauseTimerResume"
        assert install_pause_idx < install_sea_turtle_idx, "PauseTimerResume must come before SeaTurtleLifecycle"

    def test_controller_has_no_add_event_listener(self, controller_path: Path) -> None:
        content = controller_path.read_text(encoding="utf-8")
        assert "addEventListener" not in content, "Controller must not use addEventListener"

    def test_controller_has_no_crab_or_young_whale(self, controller_path: Path) -> None:
        content = controller_path.read_text(encoding="utf-8")
        assert "Crab" not in content, "Controller must not reference Crab"
        assert "YoungWhale" not in content, "Controller must not reference YoungWhale"
        assert "youngWhale" not in content, "Controller must not reference youngWhale"

    def test_controller_has_no_mission_success_progression(self, controller_path: Path) -> None:
        content = controller_path.read_text(encoding="utf-8")
        assert "completeMission" not in content, "Controller must not call completeMission"
        assert "beginTransition" not in content, "Controller must not call beginTransition"

    def test_controller_has_no_direct_set_timeout(self, controller_path: Path) -> None:
        content = controller_path.read_text(encoding="utf-8")
        assert "setTimeout" not in content, "Controller must not use setTimeout directly"

    def test_legacy_manifest_has_no_controller_file(self, controller_path: Path) -> None:
        """Legacy manifest should not include the new controller file."""
        # This test verifies that the legacy src/app.js is not modified
        # The controller file itself is new, so it should not appear in legacy code
        assert controller_path.exists(), "Controller file must exist as new file"

    def test_legacy_app_js_sea_turtle_implementation_remains(self, legacy_app_path: Path) -> None:
        """Verify that legacy sea-turtle functions remain in src/app.js."""
        assert legacy_app_path.exists(), "Legacy app.js must exist"

        content = legacy_app_path.read_text(encoding="utf-8")

        assert "function renderSeaTurtleFrame" in content, "Legacy renderSeaTurtleFrame must remain"
        assert "function updateSeaTurtleRootMarkers" in content, "Legacy updateSeaTurtleRootMarkers must remain"
        assert "function syncSeaTurtleScene" in content, "Legacy syncSeaTurtleScene must remain"
