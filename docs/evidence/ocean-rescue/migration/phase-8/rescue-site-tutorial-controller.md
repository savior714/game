# WP-33C — Rescue-site Transition and Tutorial Controller

## Status

COMPLETE

## Objective

Move canonical ownership of the coherent
`TRAVEL → RESCUE_SITE_TRANSITION → RESCUE_TUTORIAL → RESCUE_ACTIVE`
flow from the monolithic legacy `src/app.js` closure into the typed
`src/controllers/rescue-site-tutorial.ts` controller while retaining the legacy
ordered-script implementation as the rollback authority.

## Typed ownership

The WP-33C controller owns:

- travel-arrival validation and rescue sequence identity;
- transition into `RESCUE_SITE_TRANSITION`;
- rescue overlay, situation, companion, and ready-state presentation;
- authored sea-turtle/crab scene preparation and failure diagnostics;
- semantic site-transition and tutorial timers;
- transition into `RESCUE_TUTORIAL`;
- tutorial presentation, classes, skip handling, and automatic completion;
- transition into `RESCUE_ACTIVE`;
- stage-pointer consumption during transition/tutorial;
- cancellation of pending site/tutorial runtime when returning to the menu;
- invocation of the existing mission-specific interaction handoff.

## Retained host bridges

The controller receives narrow host bridges for:

- pauseable timer scheduling/cancellation;
- current pause state and pause-button synchronization;
- travel runtime shutdown;
- active rescue-sequence storage shared with downstream legacy lifecycles;
- shared canvas/context and generic rescue-site painting;
- mission-specific interaction startup.

## WP-33D boundary

The controller does not own or copy:

- pauseable timer registries;
- elapsed/remaining timer records;
- freeze/rearm behavior;
- pause overlay;
- resume countdown;
- pause-menu orchestration outside its narrow cancellation hook.

## WP-33E–G boundary

The controller does not own or copy:

- sea-turtle rope state, pointer input, feedback, assistance, or success;
- crab hold/drag state, feedback, assistance, or success;
- young-whale connect/tow state, pointer input, feedback, assistance, or success.

After entering `RESCUE_ACTIVE`, it calls the host's single
`startRescueInteraction(sequence)` bridge. The existing mission-specific
lifecycles remain authoritative until their own bounded work packages.

## Static listener ownership

The exactly-once `bindStaticControls()` owner remains in legacy `src/app.js`.
Its stage `pointerdown` listener dispatches dynamically through
`App.handleRescueStagePointerDown(event)`, allowing the canonical ESM lane to
use the typed controller without registering a duplicate listener.

## Rollback boundary

The legacy ordered manifest continues to execute `src/app.js` without importing
the typed controller. Reverting the controller installation, host bridges,
direct-caller dispatch, tests, artifacts, and documentation restores the prior
canonical arrangement while preserving the legacy lane throughout.

## Required repository verification

```bash
just check-ocean-rescue-rescue-site-tutorial-controller
uv run pytest tests/test_ocean_rescue_wp33c_rescue_site_tutorial_controller.py -q
uv run pytest tests/test_ocean_rescue_wp33c_rescue_site_tutorial_controller.py -q
uv run pytest tests/test_ocean_rescue_wp33c_rescue_site_tutorial_controller.py -q
just build-ocean-rescue
just build-ocean-rescue
uv run pytest tests/test_ocean_rescue_artifact_drift.py -q
just check-ocean-rescue-rollback
git diff --check
```

Only after all verification passes should this document be changed to
`COMPLETE`, artifact hashes/results be recorded, and the migration plan advance
to WP-33D.

## Verification results

- Focused test pass count: 6/6
- WP-33C repeated runs: 3/3 (all 6 tests pass each run)
- Existing regression results:
  - test_ocean_rescue_rescue_site_tutorial.py: 8/8 PASS
  - test_ocean_rescue_pause_lifecycle.py: 8/8 PASS
  - test_ocean_rescue_authored_sea_turtle_scene.py: 25/25 PASS
  - test_ocean_rescue_crab_authored_scene.py: 15/15 PASS
  - test_ocean_rescue_wp33b_launch_travel_controller.py: 7/7 PASS
  - test_ocean_rescue_wp30_esm_entry_module_graph.py: 22/22 PASS
- Production bundle SHA-256: 97bd04daa7a96c09362cd736ee7e3ee45631b2ba972db3466e47e2e95e3ac731
- Metadata SHA-256: 0e0e47e97c0529a75e055feb668635355d63704162cd6c6e20cae27ae9e9e3c9
- Standalone HTML SHA-256: 038bfab69fa07e1b5302088e6906d7c2bfb903e5bffd57bcc054f6a5e3ae8966
- Deterministic build: 2 runs byte-identical
- Rollback: PASS (`just check-ocean-rescue-rollback`)
- WP-21 production bundle cutover: 22/22 PASS
- Artifact drift: 6/6 PASS
- Pinned TypeScript: PASS (`just typecheck-ocean-rescue`)
- Changed paths:
  - domains/ocean-rescue/src/controllers/rescue-site-tutorial.ts (new)
  - domains/ocean-rescue/src/controllers/launch-travel.ts (modified)
  - domains/ocean-rescue/src/contracts/runtime-abi.ts (modified)
  - domains/ocean-rescue/src/esm/app.js (modified)
  - domains/ocean-rescue/src/app.js (modified)
  - tests/test_ocean_rescue_wp33c_rescue_site_tutorial_controller.py (new)
  - tests/test_ocean_rescue_wp30_esm_entry_module_graph.py (modified)
  - Justfile (modified)
  - docs/evidence/ocean-rescue/migration/phase-8/rescue-site-tutorial-controller.md (modified)
  - domains/ocean-rescue/dist/ocean-rescue-app.js (regenerated)
  - domains/ocean-rescue/dist/production-bundle-metadata.json (regenerated)
  - ocean-rescue/index.html (regenerated)
