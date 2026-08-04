# WP-33A — Profile and Mission-Selection Flow Controller

## Status: COMPLETE

## Objective
Introduce a typed `ProfileMissionSelectionController` class in `src/controllers/profile-mission-selection.ts` and install it in the canonical ESM adapter `src/esm/app.js`.

## Scope
- `src/controllers/profile-mission-selection.ts`: typed controller with `renderProfileChoice`, `selectProfileAnimal`, `confirmProfileSelection`, `boot`, `renderMissionSelect`, `selectMission`
- `src/esm/app.js`: imports and installs the controller via `installProfileMissionSelectionController`
- `src/app.js`: legacy IIFE retained for rollback
- `src/contracts/runtime-abi.ts`: type-only ABI boundary

## Verification
- 6/6 WP-33A tests pass (browser flow + static ownership)
- WP-30 ESM module graph: 22/22 pass (includes `APP_ADAPTER_CONTROLLER_FILE` dict for `app.js`)
- Profile choice regression: 14/14 pass
- Mission progression regression: 13/13 pass
- GUP selection regression: 8/8 pass
- WP-03 scope decision: 3/3 pass
- Artifact drift: 6/6 pass
- WP-21 production bundle: 22/22 pass
- Production artifact deterministic: verified (`587d0c2d...` bundle, `c19cd0d2...` metadata, `b48e83af...` HTML)

## Artifact hashes
- Bundle: `587d0c2d...`
- Metadata: `c19cd0d2...`
- HTML: `b48e83af...`

## Changed paths
- `Justfile`: added `check-ocean-rescue-profile-mission-controller` recipe
- `tests/test_ocean_rescue_wp33a_profile_mission_controller.py`: rewritten with 6 tests
- `tests/test_ocean_rescue_wp30_esm_entry_module_graph.py`: added `APP_ADAPTER_CONTROLLER_FILE` dict, updated `ADAPTER_DEPS["app.js"]`, added `test_app_adapter_imports_profile_mission_selection_controller`, updated `test_implementation_modules_import_nothing`
- `ocean-rescue/index.html`: regenerated
- `domains/ocean-rescue/dist/ocean-rescue-app.js`: rebuilt
- `domains/ocean-rescue/dist/production-bundle-metadata.json`: rebuilt
- `docs/plans/PLAN_ocean_rescue_vite_esm_typescript_migration.md`: phase 8 status updated
