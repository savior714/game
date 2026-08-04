# WP-33B — Launch and Travel Flow Controller

## Status

COMPLETE

## Objective

Move canonical ownership of the coherent `GUP_SELECT → LAUNCH → TRAVEL`
flow from the monolithic legacy `src/app.js` closure into the typed
`src/controllers/launch-travel.ts` controller while retaining the unchanged
legacy behavior as the ordered-manifest rollback authority.

## Typed ownership

The WP-33B controller owns:

- GUP selection rendering, selection, back navigation, and launch confirmation;
- launch sequence identity, presentation, skip and automatic completion;
- goal-banner semantic lifecycle;
- travel run identity and requestAnimationFrame lifecycle;
- Travel and Terrain start/step/stop coordination;
- TravelScene prepare/activate/sync/exit coordination;
- travel progress computation, presentation, and compatibility API;
- travel pointer tap/drag/capture lifecycle;
- narrow travel pause, resume, and stop hooks;
- invocation of the existing rescue-arrival handoff.

## Retained host bridges

WP-33D continues to own timer and pause infrastructure. The controller receives
only:

- `schedulePauseableTimer(owner, durationMs, callback)`;
- `cancelPauseableTimer(owner)`;
- `isPauseActive()`;
- `syncPauseButton()`.

The controller does not contain the pauseable timer registry, freeze/rearm
records, pause overlay, or resume countdown.

Shared render bridge functions remain in the legacy host because mission-specific
legacy renderers still use them:

- `resolveVisibleInputCanvas()`;
- `resolvePaintCanvas()`;
- `resolvePaintContext()`.

## WP-33C boundary

Travel arrival calls `handoffTravelArrival()`. The legacy host continues to own:

- rescue mission/content resolution;
- `RESCUE_SITE_TRANSITION` phase transition;
- rescue sequence creation;
- authored rescue-scene preparation;
- site-transition and tutorial timers;
- tutorial presentation and skip behavior.

The host delegates travel runtime cleanup back to `App.stopTravelRuntime()` so
there is only one canonical travel run state.

## Direct callers

The existing exactly-once `bindStaticControls()` owner remains in `src/app.js`,
but GUP back, launch, and launch-skip listeners dispatch through the installed
`App` facade. Pause, resume, menu exit, and rescue-arrival callers likewise use
narrow typed runtime hooks. No second static-control binding layer is added.

## Compatibility

`window.OceanRescue.TravelProgress.compute` remains available and is replaced by
the typed controller implementation in the canonical ESM lane. The legacy lane
continues to publish the existing implementation.

The new controller is excluded from `build-manifest.legacy.json`.

## Verification required before closure

```bash
just check-ocean-rescue-launch-travel-controller
uv run pytest tests/test_ocean_rescue_wp33b_launch_travel_controller.py -q
uv run pytest tests/test_ocean_rescue_wp33b_launch_travel_controller.py -q
uv run pytest tests/test_ocean_rescue_wp33b_launch_travel_controller.py -q
git diff --check
```

Then run the canonical production builder twice, prove byte determinism and
artifact drift, verify rollback, update artifact hashes and pass counts in this
document, and only then change the status to `COMPLETE` and advance the plan to
WP-33C.

## Rollback boundary

Revert the WP-33B controller installation, App host bridges, direct-caller
dispatch changes, tests, generated artifacts, and documentation. The legacy
ordered manifest and legacy implementation remain available throughout.

## Verification results

### Focused test

```
tests/test_ocean_rescue_wp33b_launch_travel_controller.py: 6 passed
```

### Browser verification (3 consecutive runs)

```
Run 1: 6 passed
Run 2: 6 passed
Run 3: 6 passed
Total: 18/18
```

Quality gates per run:
- page error 0
- console error 0
- requestfailed 0
- external runtime request 0
- launch skip/auto-complete single transition
- travel pointer capture lifecycle
- pause/resume travel continuation
- rescue-arrival handoff after travel stopped

### Production bundle SHA-256

```
ocean-rescue-app.js:       aaf5a6473cd74c75247c532f3da5a500ef9eeed8b96004bef0a62d2f84a9ea11
production-bundle-metadata: df2bb0fc364a2cc0e3882ae51e312e28df1c66e88962329ae02f1b5dbb1a56b4
ocean-rescue/index.html:   6a0004cc1f41e401c2bf90661c384a8c615ed7617b8392fe48580753036bf44e
```

### Deterministic build

Two consecutive `just build-ocean-rescue` runs produced byte-identical artifacts.

### Rollback

```
just check-ocean-rescue-rollback: PASS
test_operational_rollback_restores_legacy_and_bundle: PASS
```

### Full focused recipe

```
just check-ocean-rescue-launch-travel-controller: PASS
  - WP-33B focused test: 6 passed
  - WP-33A regression: 6 passed
  - launch presentation: 8 passed
  - travel movement: 8 passed
  - pause lifecycle: 8 passed
  - WP-32B pointer/renderer boundary: 22 passed
  - WP-30 module graph: 22 passed
  - WP-21 production bundle cutover: 22 passed
  - artifact drift: 6 passed
  - rollback: PASS
  - WP-03 scope decision: 3 passed
```

## Changed paths

- `domains/ocean-rescue/src/controllers/launch-travel.ts` (new)
- `domains/ocean-rescue/src/contracts/runtime-abi.ts` (extended)
- `domains/ocean-rescue/src/esm/app.js` (ordered WP-33A then WP-33B install)
- `domains/ocean-rescue/src/app.js` (legacy App bridges, direct caller dispatch)
- `tests/test_ocean_rescue_wp33b_launch_travel_controller.py` (new)
- `tests/test_ocean_rescue_wp30_esm_entry_module_graph.py` (ordered controller chain)
- `tests/test_ocean_rescue_wp32b_pointer_renderer_boundary.py` (ABI type assertion)
- `docs/evidence/ocean-rescue/migration/phase-8/launch-travel-flow-controller.md` (new)
- `Justfile` (added check-ocean-rescue-launch-travel-controller recipe)
- `domains/ocean-rescue/dist/ocean-rescue-app.js` (regenerated)
- `domains/ocean-rescue/dist/production-bundle-metadata.json` (regenerated)
- `ocean-rescue/index.html` (regenerated)
