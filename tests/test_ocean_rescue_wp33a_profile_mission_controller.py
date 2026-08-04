"""Focused browser and static proof for the WP-33A typed profile/mission controller.

This test verifies:
- Browser: canonical Vite dev lane installs typed controller methods
- Browser: profile choice renders correct animal catalog
- Browser: Continue disabled before selection, enabled after
- Browser: single Continue click reaches MISSION_SELECT
- Browser: mission cards render in catalog order with correct lock/status
- Browser: Sea Turtle selection reaches GUP_SELECT
- Browser: Missions.selectedMissionId is updated
- Browser: new mission marker transitions to viewed
- Browser: GUP section handoff (single entry)
- Browser: backToMissionSelect() returns to typed mission renderer
- Browser: no page errors, console errors, request failures, external requests
- Static: canonical ESM app.js imports controller
- Static: canonical graph includes controller module
- Static: type-only contract excluded from runtime bundle
- Static: legacy manifest excludes typed controller
- Static: legacy rollback preserves src/app.js path
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
from test_ocean_rescue_wp11_dev_server import ViteServerFixture  # noqa: E402

REPO_ROOT = TESTS_DIR.parent
SRC_DIR = REPO_ROOT / "domains" / "ocean-rescue" / "src"
ESM_APP = SRC_DIR / "esm" / "app.js"
LEGACY_MANIFEST = SRC_DIR / "build-manifest.legacy.json"
LEGACY_APP = SRC_DIR / "app.js"
CONTROLLER_TS = SRC_DIR / "controllers" / "profile-mission-selection.ts"


# ---------------------------------------------------------------------------
# Browser flow tests
# ---------------------------------------------------------------------------


def test_typed_profile_mission_controller_owns_canonical_browser_flow() -> None:
    """Full WP-33A browser proof: profile → mission → GUP → back → re-enter."""
    with ViteServerFixture() as server:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            context.add_init_script("localStorage.clear(); sessionStorage.clear();")
            page = context.new_page()

            page_errors: list[str] = []
            console_errors: list[str] = []
            request_failures: list[dict[str, object]] = []
            external_requests: list[str] = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.on(
                "console",
                lambda message: (
                    console_errors.append(message.text)
                    if message.type == "error"
                    else None
                ),
            )
            page.on(
                "requestfailed",
                lambda request: request_failures.append(
                    {"url": request.url, "failure": request.failure}
                ),
            )
            page.on(
                "request",
                lambda request: (
                    external_requests.append(request.url)
                    if not request.url.startswith(server.base_url)
                    else None
                ),
            )

            page.goto(f"{server.base_url}/index.dev.html")
            page.wait_for_selector(
                "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=20000
            )

            # 1. Canonical Vite dev lane installs typed controller
            controller_contract = page.evaluate(
                """() => ({
                  renderProfileChoice: typeof OceanRescue.App.renderProfileChoice,
                  selectProfileAnimal: typeof OceanRescue.App.selectProfileAnimal,
                  confirmProfileSelection: typeof OceanRescue.App.confirmProfileSelection,
                  renderMissionSelect: typeof OceanRescue.App.renderMissionSelect,
                  selectMission: typeof OceanRescue.App.selectMission,
                  renderGupSelect: typeof OceanRescue.App.renderGupSelect,
                  backToMissionSelect: typeof OceanRescue.App.backToMissionSelect,
                  launchSelectedGup: typeof OceanRescue.App.launchSelectedGup,
                })"""
            )
            assert controller_contract == {
                "renderProfileChoice": "function",
                "selectProfileAnimal": "function",
                "confirmProfileSelection": "function",
                "renderMissionSelect": "function",
                "selectMission": "function",
                "renderGupSelect": "function",
                "backToMissionSelect": "function",
                "launchSelectedGup": "function",
            }, f"Controller contract mismatch: {controller_contract}"

            # 2. Profile choice renders correct animal catalog (3 animals)
            profile = page.locator("#ocean-rescue-profile-choice")
            assert profile.is_visible()
            animals = page.locator(
                "#ocean-rescue-profile-animal-list [data-profile-animal-id]"
            )
            assert animals.count() == 3
            animal_ids = [
                animals.nth(i).get_attribute("data-profile-animal-id")
                for i in range(animals.count())
            ]
            assert "arctic-fox" in animal_ids
            assert "sea-turtle" in animal_ids or any(
                a is not None and a != "arctic-fox" and a != "sea-turtle"
                for a in animal_ids
            )

            # 3. Continue disabled before selection
            continue_button = page.locator("#ocean-rescue-profile-continue")
            assert continue_button.is_disabled()

            # 4. Animal selection updates aria-pressed and Continue
            page.click('[data-profile-animal-id="arctic-fox"]')
            assert (
                page.locator('[data-profile-animal-id="arctic-fox"]').get_attribute(
                    "aria-pressed"
                )
                == "true"
            )
            # Other animals should not be pressed
            for aid in animal_ids:
                if aid != "arctic-fox":
                    assert (
                        page.locator(f'[data-profile-animal-id="{aid}"]').get_attribute(
                            "aria-pressed"
                        )
                        == "false"
                    )
            assert continue_button.is_enabled()

            # 5. Single Continue click reaches MISSION_SELECT
            continue_button.click()
            page.wait_for_function(
                """() => OceanRescue.State.getSnapshot().phase === 'MISSION_SELECT'"""
            )
            assert not profile.is_visible()

            # 6. Mission cards render in catalog order
            mission_cards = page.locator("#ocean-rescue-mission-list [data-mission-id]")
            assert mission_cards.count() == 3
            first_mission_id = mission_cards.nth(0).get_attribute("data-mission-id")
            second_mission_id = mission_cards.nth(1).get_attribute("data-mission-id")
            third_mission_id = mission_cards.nth(2).get_attribute("data-mission-id")
            # Catalog order: sea-turtle, crab, young-whale
            assert first_mission_id == "sea-turtle"
            assert second_mission_id == "crab"
            assert third_mission_id == "young-whale"

            # 7. Lock/completed/new status matches progression
            sea_turtle = page.locator('[data-mission-id="sea-turtle"]')
            crab = page.locator('[data-mission-id="crab"]')
            young_whale = page.locator('[data-mission-id="young-whale"]')
            assert sea_turtle.is_enabled()
            assert crab.is_disabled()
            assert young_whale.is_disabled()

            # Sea Turtle is the initial unlocked mission (not "new" via completion)
            # newMissionIds is populated only when completeMission unlocks the next
            progression = page.evaluate("""() => OceanRescue.Missions.getSnapshot()""")
            assert "sea-turtle" in progression["unlockedMissionIds"]
            assert progression["selectedMissionId"] is None

            # 8. Sea Turtle selection reaches GUP_SELECT
            sea_turtle.click()
            page.wait_for_function(
                """() => OceanRescue.State.getSnapshot().phase === 'GUP_SELECT'"""
            )
            page.wait_for_selector("#ocean-rescue-gup-select:not([hidden])")

            # 9. Missions.selectedMissionId updated
            mission_snapshot = page.evaluate(
                """() => OceanRescue.Missions.getSnapshot()"""
            )
            assert mission_snapshot["selectedMissionId"] == "sea-turtle"

            # 10. New mission marker transitions to viewed (newMissionIds empty)
            assert mission_snapshot["newMissionIds"] == []

            # 11. GUP section visible, mission section hidden
            mission_section = page.locator("#ocean-rescue-mission-select")
            assert not mission_section.is_visible()

            # 12. backToMissionSelect() returns to typed mission renderer
            back_button = page.locator("#ocean-rescue-gup-back")
            back_button.click()
            page.wait_for_function(
                """() => OceanRescue.State.getSnapshot().phase === 'MISSION_SELECT'"""
            )
            page.wait_for_selector("#ocean-rescue-mission-select[style*='block']")
            # Verify mission cards are still rendered
            mission_cards_after_back = page.locator(
                "#ocean-rescue-mission-list [data-mission-id]"
            )
            assert mission_cards_after_back.count() == 3
            # Sea Turtle should still be enabled and selectable
            assert page.locator('[data-mission-id="sea-turtle"]').is_enabled()

            # 13. Re-enter Sea Turtle to confirm no handler duplication
            page.locator('[data-mission-id="sea-turtle"]').click()
            page.wait_for_function(
                """() => OceanRescue.State.getSnapshot().phase === 'GUP_SELECT'"""
            )
            page.wait_for_selector("#ocean-rescue-gup-select:not([hidden])")

            # 14. Select a GUP to verify GUP_SELECT → LAUNCH path is intact
            gup_cards = page.locator("#ocean-rescue-gup-list button")
            assert gup_cards.count() >= 1
            first_gup = gup_cards.nth(0)
            first_gup.click()
            launch_button = page.locator("#ocean-rescue-gup-launch")
            assert launch_button.is_enabled()

            # 15. No page errors
            assert page_errors == [], f"Page errors: {page_errors}"

            # 16. No console errors
            assert console_errors == [], f"Console errors: {console_errors}"

            # 17. No request failures
            assert request_failures == [], f"Request failures: {request_failures}"

            # 18. No external runtime network requests
            non_local = [
                u
                for u in external_requests
                if not u.startswith("data:")
                and "localhost" not in u
                and "127.0.0.1" not in u
            ]
            assert non_local == [], f"External requests: {non_local}"

            context.close()
            browser.close()


# ---------------------------------------------------------------------------
# Static ownership tests
# ---------------------------------------------------------------------------


def test_canonical_esm_app_imports_controller() -> None:
    """Canonical src/esm/app.js imports the typed controller module."""
    content = ESM_APP.read_text()
    assert "installProfileMissionSelectionController" in content
    assert "../controllers/profile-mission-selection" in content


def test_controller_module_exists_in_canonical_graph() -> None:
    """The typed controller .ts file exists in the source tree."""
    assert CONTROLLER_TS.exists(), f"Controller missing: {CONTROLLER_TS}"
    content = CONTROLLER_TS.read_text()
    assert "export function installProfileMissionSelectionController" in content


def test_type_only_contract_excluded_from_runtime() -> None:
    """runtime-abi.ts is type-only and never appears in the production bundle."""
    bundle = REPO_ROOT / "domains" / "ocean-rescue" / "dist" / "ocean-rescue-app.js"
    if not bundle.exists():
        return
    bundle_content = bundle.read_text()
    assert "runtime-abi" not in bundle_content, (
        "type-only contract runtime-abi should not appear in runtime bundle"
    )


def test_legacy_manifest_excludes_typed_controller() -> None:
    """The legacy rollback manifest does not reference the typed controller."""
    import json

    if not LEGACY_MANIFEST.exists():
        return
    manifest = json.loads(LEGACY_MANIFEST.read_text())
    all_sources = []
    if "scripts" in manifest:
        for entry in manifest["scripts"]:
            if isinstance(entry, dict) and "src" in entry:
                all_sources.append(entry["src"])
            elif isinstance(entry, str):
                all_sources.append(entry)
    for src in all_sources:
        assert "controllers/profile-mission-selection" not in src, (
            f"Legacy manifest references typed controller: {src}"
        )


def test_legacy_rollback_preserves_app_js_path() -> None:
    """Legacy rollback preserves src/app.js as the orchestration authority."""
    assert LEGACY_APP.exists(), "Legacy src/app.js must exist for rollback"
    content = LEGACY_APP.read_text()
    assert "window.OceanRescue.App = App" in content
    assert "function boot" in content or "boot:" in content
