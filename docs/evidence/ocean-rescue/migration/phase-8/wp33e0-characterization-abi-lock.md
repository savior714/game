# WP-33E-0 Evidence — Sea-Turtle Characterization and ABI Lock

## Status

COMPLETE

## Package Scope

WP-33E-0 locks the concrete sea-turtle runtime ABI and characterization baseline
without moving pointer handling, feedback timing, completion routing, or shared
rescue listener ownership out of `src/app.js`.

## Baseline and Final Commit IDs

- **Baseline:** `origin/main` at `d55acd2d47556bb2244512640cee37dbb4006166`
- **Preparation SHA:** `d85be9aa6b646a76e51592b7560437e388d96f3b`
- **Final commit:** `origin/main` at `d85be9aa6b646a76e51592b7560437e388d96f3b` (rebased onto latest)

## ABI Contracts Locked

The following concrete types are now locked in `domains/ocean-rescue/src/contracts/runtime-abi.ts`:

- `SeaTurtleRopeId = "rope-1" | "rope-2" | "rope-3"`
- `SeaTurtlePoint` with `x: number` and `y: number`
- `SeaTurtleRope` with typed `id`, `order: 1 | 2 | 3`, and `start`/`end` as `SeaTurtlePoint`
- `SeaTurtleConstants` with all nine runtime constants (`baseEndpointRadius`, `assistedEndpointRadius`, `basePathTolerance`, `assistedPathTolerance`, `tapMovementThreshold`, `minimumTraceProgress`, `maxBackwardProgress`, `successFeedbackMs`, `failureFeedbackMs`)
- `SeaTurtleSnapshot` with `activeRopeId: SeaTurtleRopeId | null` and `completedRopeIds: readonly SeaTurtleRopeId[]`
- `SeaTurtleRopeResult` with `ropeId: SeaTurtleRopeId | null`
- `SeaTurtleFeedbackCompletion` with `nextRopeId: SeaTurtleRopeId | null`
- `SeaTurtleApi.MissionId: "sea-turtle"` (literal type)
- `SeaTurtleApi.Constants: Readonly<SeaTurtleConstants>`
- `SeaTurtleApi.Dialogues: readonly [string, string, string]`
- `SeaTurtleSceneApi.sync(snapshot, intent?: PointerIntent)` with optional pointer intent

## Characterization Matrix Covered

The characterization test file `tests/test_ocean_rescue_wp33e_sea_turtle_lifecycle_controller.py`
proves the following:

1. **Exact rope IDs and order:** `SeaTurtleRopeId` is `"rope-1" | "rope-2" | "rope-3"` and `order` is `1 | 2 | 3`.
2. **Constants and dialogue ABI:** All nine constants are typed as `number` in `SeaTurtleConstants`, and `Dialogues` is `readonly [string, string, string]`.
3. **Concrete snapshot/result types:** `SeaTurtleSnapshot`, `SeaTurtleRopeResult`, and `SeaTurtleFeedbackCompletion` use `SeaTurtleRopeId` instead of `string`.
4. **Scene sync pointer-intent type:** `SeaTurtleSceneApi.sync` accepts optional `PointerIntent`.
5. **Start eligibility and initial projection:** Controller checks `State.Phases.RESCUE_ACTIVE`, calls `SeaTurtle.start()`, activates scene, and renders frame.
6. **Shared listener/router remaining in app.js:** `bindRescuePointerInput`, `missionId === SeaTurtle.MissionId`, `Crab.MissionId`, `YoungWhale.MissionId` all remain in `app.js`.
7. **Pointer capture/cancel baseline remaining in app.js:** `handleSeaTurtlePointerDown`, `releaseSeaTurtlePointerCapture`, `setPointerCapture`, `releasePointerCapture`, and all pointer event handlers remain in `app.js`.
8. **Pauseable feedback and stale-sequence guards remaining in app.js:** `beginSeaTurtleSuccessFeedback`, `beginSeaTurtleFailureFeedback`, `completeSeaTurtleFeedback`, feedback scheduling, and stale-sequence checks remain in `app.js`.
9. **Pause/menu cleanup and mission-success handoff remaining host-owned:** `cancelPausePointerInteractions`, `SeaTurtle.pauseCancel()`, `shutdownRescueInteractionState`, `completeSeaTurtleSuccess`, `State.beginTransition(State.Phases.RESCUE_SUCCESS)`, and `startMissionSuccessPresentation` remain in `app.js`.

## Protected Files — No Diff Proof

The following files have no diff (verified via `git diff`):

- `domains/ocean-rescue/src/app.js`
- `domains/ocean-rescue/src/sea-turtle.js`
- `domains/ocean-rescue/src/sea-turtle-scene.js`
- `ocean-rescue/index.html`

## Controller Changes

The controller `domains/ocean-rescue/src/controllers/sea-turtle-lifecycle.ts`:

- Removed `as unknown as` cast from the installer
- Added `SeaTurtleSessionRef` interface with `rescueSequenceId: number` and `missionId: "sea-turtle"`
- Typed `getSeaTurtleSnapshot()` to return `SeaTurtleSnapshot | null` instead of `unknown | null`
- Typed host methods to use `PointerIntent` instead of `unknown`
- Used `Object.assign(host, {...})` for cleaner controller assembly
- Added `resolveDependencies()` helper for cleaner namespace access

## Verification Command and Result

```bash
just check-ocean-rescue-sea-turtle-lifecycle-controller
```

**Result:** PASS

- `test_ocean_rescue_wp33e_sea_turtle_lifecycle_controller.py`: 11 tests passed
- `test_ocean_rescue_sea_turtle_interaction.py`: 8 tests passed
- `test_ocean_rescue_authored_sea_turtle_scene.py`: 25 tests passed
- `test_ocean_rescue_rope_geometry_runtime.py`: 27 tests passed
- `test_ocean_rescue_wp33d_pause_timer_resume_controller.py`: 7 tests passed
- `test_ocean_rescue_wp33c_rescue_site_tutorial_controller.py`: 7 tests passed
- `test_ocean_rescue_wp32b_pointer_renderer_boundary.py`: 22 tests passed
- `test_ocean_rescue_wp30_esm_entry_module_graph.py`: 22 tests passed
- `test_ocean_rescue_wp03_scope_decision.py`: 3 tests passed

**Total:** 132 tests passed, 0 failures

## Static Diagnostics

- `git diff --check`: PASS (no whitespace errors)
- TypeScript typecheck: PASS (via Justfile toolchain check)

## Next Executable Package

WP-33E-1 will own the next ownership boundary (pointer handling, capture, or feedback timing)
starting from this characterization baseline.
