# Ocean Rescue Pointer Coordinate / Renderer Adapter Boundary (WP-32B)

- Task ID: `AIDENGAME-OCEAN-RESCUE-WP32B-POINTER-COORDINATE-RENDERER-BOUNDARY-01`
- Captured: 2026-08-04
- Implementation base origin/main: `a8030a6756bcabe814a203d2be218e59ed86980b`
- Publication integration base origin/main: `a8030a6756bcabe814a203d2be218e59ed86980b`
- Result: PASS
- Migration state: `PHASE_8_READY` (Phase 7 COMPLETE, WP-32B COMPLETE)
- Pointer coordinate boundary state: `CHECKED_RUNTIME`
- Scene pointer intent state: `NORMALIZED_SHARED`
- Render coordinate adapter state: `TYPED_MINIMAL`
- Runtime output state: `DETERMINISTIC`
- Next executable work package: WP-33A

## Objective

WP-32B extracts the pointer coordinate transformations and scene
pointer-intent generation that were embedded ad hoc in `src/app.js` into one
real runtime boundary shared by the canonical ESM lane and the legacy
ordered-script lane:

- browser client coordinates -> Ocean Rescue logical coordinates;
- travel pointer event -> logical stage Y;
- rescue pointer event -> logical `{ x, y }`;
- the normalized `{ active, x, y }` pointer intent delivered to authored
  scenes;
- the minimal RenderRuntime coordinate-mapper API (`isReady()` +
  `mapClientToLogical`) that the boundary depends on.

The full RenderRuntime API, the Pixi display-object model, authored scene
implementation typing, and app orchestration decomposition are explicitly out
of scope.

## Pointer contract inventory

- `domains/ocean-rescue/src/contracts/pointer-input.ts` (type-only, new):
  `LogicalPoint`, `RenderMappedPoint`, `RenderCoordinateMapperApi`,
  `ActivePointerIntent`, `InactivePointerIntent`, `PointerIntent`,
  `ClientCoordinateCarrier`, `BoundingRect`, `RectProvider`, `PointerInputApi`.
  SHA-256: `3c00ff348672c0882cfabdd4f928c0ddb3f7b5fe1ba8658eaf61faacc7b494e8`
- `domains/ocean-rescue/src/pointer-input.js` (shared checked-JS runtime, new):
  the single implementation of `mapTravelStageY`, `mapRescuePoint`,
  `activeIntent`, `inactiveIntent`, registered as the frozen
  `OceanRescue.PointerInput` global. Both lanes execute this exact file.
  Because the legacy ordered-script builder rejects the raw dynamic-import
  token in script sources, the local checked-JS types are declared structurally
  with `@typedef`; the canonical ESM adapters reference the shared contract via
  the global declaration.
- `domains/ocean-rescue/src/esm/pointer-input.js` (canonical adapter, new):
  side-effect imports the shared implementation, fail-closes when the
  namespace or any API method is absent, exports the registered object.
- `domains/ocean-rescue/src/esm/render-runtime.js` (changed): `@ts-check` +
  global declaration reference + existence guard for `isReady` and
  `mapClientToLogical`.
- `domains/ocean-rescue/src/contracts/runtime-abi.ts` (changed): re-exports
  `LogicalPoint`, `RenderMappedPoint`, `RenderCoordinateMapperApi`,
  `PointerIntent`, `PointerInputApi` and adds the optional
  `RenderRuntime?: RenderCoordinateMapperApi` and
  `PointerInput?: PointerInputApi` slots.
- `domains/ocean-rescue/src/esm/app.js` (changed): imports `pointer-input.js`
  after `render-runtime.js` and before the legacy `app.js`.
- `domains/ocean-rescue/src/app.js` (changed): delegates
  `mapClientYToStage` to `PointerInput.mapTravelStageY(event, travelCanvas)`
  and `mapRescueCoordinates` to
  `PointerInput.mapRescuePoint(event, resolveVisibleInputCanvas())`; replaces
  every inline scene pointer-intent literal (`{ active: true, x, y }` /
  `{ active: false, x: null, y: null }`) with
  `PointerInput.activeIntent(mapped)` / `PointerInput.inactiveIntent()`.
- `domains/ocean-rescue/src/build-manifest.legacy.json` (changed):
  `pointer-input.js` inserted exactly once after `render-runtime.js` and before
  `app.js`; `OceanRescue.PointerInput` depends on `OceanRescue.RenderRuntime`;
  `OceanRescue.App` gains the `OceanRescue.PointerInput` dependency.
- `Justfile` (changed): new `check-ocean-rescue-pointer-renderer-boundary`
  focused recipe.

Scene consumers (`sea-turtle-scene.js`, `crab-scene.js`) are unchanged: both
consume the exact `PointerIntent` from `PointerInput` through
`sync(current, intent)`, keep their internal finite-normalization, and retain
their missing-intent fallback.

## Baseline behavior matrix (captured)

The pre-extraction `app.js` formulas were recorded from the base SHA and are
embedded verbatim in the parity test (`_REFERENCE_TRAVEL`,
`_REFERENCE_RESCUE`) to prove behavior parity. The full matrix is executed
against the real `src/pointer-input.js` in a fresh isolated VM:

- Travel: valid fallback map; valid renderer map; clientX fallback to
  `rect.left`; mapped non-finite Y -> null; invalid clientY -> null; missing
  canvas -> null; invalid rect/null -> null; invalid height -> null; renderer
  not ready -> fallback; renderer ready -> renderer map.
- Rescue: valid fallback map; valid renderer map; invalid rect fields -> null;
  invalid dimensions -> null; non-finite mapped coordinates -> null; renderer
  `inside: false` still returns the finite point; exact X/Y numeric results.
- Intent: active exact shape and key order; inactive exact shape and key
  order; plain object; non-frozen; separate call identity; invalid active input
  baseline (missing/null point or non-finite coords -> inactive intent).

## Checked-JS diagnostics

- Effective config: `strict: true`, `noEmit: true`, `module: ESNext`,
  `moduleResolution: Bundler`, `allowJs: true`, `checkJs: false`
  (`domains/ocean-rescue/tsconfig.json`).
- Project command:
  `cd domains/ocean-rescue && corepack pnpm exec tsc --project tsconfig.json --noEmit`
  — exit 0.
- Standalone checked-JS typecheck of `src/pointer-input.js`,
  `src/esm/pointer-input.js`, `src/esm/render-runtime.js` with
  `--ignoreConfig ... --allowJs --checkJs false --noEmit` — exit 0.
- No `@ts-ignore`, `@ts-nocheck`, `@ts-expect-error`, `any`, or strictness
  relaxation in any pointer file.

## Canonical graph membership

From `production-bundle-metadata.json` (40 module files):

```text
esm/pointer-input.js          present (exactly once)
pointer-input.js              present (exactly once)
esm/render-runtime.js         present
render-runtime.js             present
contracts/*                   absent (type-only contracts never enter the bundle)
dynamic_import_count: 0
sourcemap: false
application JS chunk: exactly one
```

## Legacy manifest membership / order

```text
... vendor/pixi-8.19.0.min.js
... render-assets.generated.js
... render-runtime.js
+   pointer-input.js           (OceanRescue.PointerInput, depends on OceanRescue.RenderRuntime)
... state.js ... mission-success.js
... app.js                     (depends_on now includes OceanRescue.PointerInput)
```

Legacy ordered-script artifact builds cleanly with 20 inline scripts and no
external script references.

## Determinism and artifact identity

```text
dist/ocean-rescue-app.js             06d84baf27c84c3e2f055e08d4ddd63ef855f0080a18bace04be0e9d5050cf47  (two clean builds byte-identical)
dist/production-bundle-metadata.json 0dc939a962da74c32fe3b2c337b29e6df3b3d0996f0be316c6090a5094b4a7d4  (two clean builds byte-identical)
ocean-rescue/index.html              6d276a8d5145d8dc2eb451f2f1b88cfc9898ad45f74e24ab19e969ca7bd741c2  (tracked artifact == clean rebuild)
clean legacy rollback artifact       5ecd88978aace5a566ccdf623a58fb6a487ad11f6579b8a8cfd172460a7a5959  (deterministic current-source legacy build)
```

The pre-WP-32B artifact SHA (`a43500664a4b82772c6e842121c62c5bbfe6288ba5cbe2c5afc72fd7f9f63643`)
is recorded as the baseline only; WP-32B is a runtime module extraction, so the
post-change artifact is intentionally not byte-identical to the pre-change
baseline. The post-change contract is determinism (two clean builds
byte-identical) plus tracked-artifact/clean-rebuild equality, both verified.

## Rollback

- Legacy ordered-script build with the inserted `pointer-input.js`: PASS
  (builds cleanly, `OceanRescue.PointerInput` registers before `app.js`).
- Operational rollback (`just check-ocean-rescue-rollback`) PASS: the tracked
  artifact transitions bundle -> legacy -> bundle, the legacy state equals a
  clean current-source legacy build (20 ordered scripts), and the canonical
  production artifact is restored to `6d276a8d...`.
- A representative travel/rescue pointer flow under the legacy lane is proven
  by the Node harnesses that execute `app.js` + `pointer-input.js` in the
  legacy script order.

## Verification

- `just check-ocean-rescue-toolchain` — PASS (Node 24.18.0, pnpm 11.17.0,
  Vite 8.1.5, TypeScript 7.0.2, strict project typecheck exit 0).
- `just check-ocean-rescue-pointer-renderer-boundary` — PASS (all groups):
  - `test_ocean_rescue_wp32b_pointer_renderer_boundary.py` — 22 passing
    (static contract, checked-JS diagnostics, travel/rescue/intent matrix,
    exact baseline parity, canonical graph membership, browser parity for
    travel tap/drag, pause blocking, sea-turtle, and crab);
  - `test_ocean_rescue_travel_movement.py` — 8 passing;
  - `test_ocean_rescue_render_runtime.py` — 6 passing;
  - `test_ocean_rescue_sea_turtle_interaction.py` — 8 passing;
  - `test_ocean_rescue_crab_interaction.py` — 9 passing;
  - `test_ocean_rescue_pause_lifecycle.py` — 8 passing;
  - `test_ocean_rescue_wp32a_shared_runtime_abi_types.py` — 17 passing;
  - `test_ocean_rescue_wp31c_typed_core_state_travel.py` — 19 passing;
  - `test_ocean_rescue_wp30_esm_entry_module_graph.py` — 21 passing;
  - `test_ocean_rescue_wp21_production_bundle_cutover.py` — 21 passing;
  - `test_ocean_rescue_wp20_shadow_bundle.py` — 24 passing;
  - `just check-ocean-rescue-rollback` — PASS;
  - `test_ocean_rescue_artifact_drift.py` — 6 passing;
  - `test_ocean_rescue_wp03_scope_decision.py` — 3 passing.

## Browser assertions

- Travel: mission + GUP selection, launch -> travel, pointer tap reflected in Y
  (`tapTargetY` ~ 300), pointer drag reflected in Y, pointer ID release,
  pause blocks pointer interaction, resume works, arrival proceeds.
- Sea Turtle: rescue active, authored scene active
  (`data-sea-turtle-scene=active`), three rope pointer down/move/up drags each
  complete a rope, success feedback contract, pointer capture released between
  interactions (subsequent interactions succeed).
- Crab: rescue active, authored scene active (`data-crab-scene=active`),
  tap-armed pointer down/up on rock then drop-zone tap completes a rock,
  feedback contract, capture released.
- No page errors, no unexpected console errors, no request failures, no
  external runtime requests, no duplicate initialization across both browser
  flows.

## Unrelated lint baseline

`just lint` fails on exactly the pre-existing format-only files, unchanged by
this work package:

- `tests/test_guardian_event_binding.py`
- `tests/test_ocean_rescue_profile_choice.py`
- `tests/test_reward_auth_sync_compat_loaders.py`
- `tests/test_weekly_word_catalog_enrichment.py`
- `tests/test_weekly_word_english_definitions.py`

All changed Python test files pass `ruff check` and `ruff format --check`.

## Explicit exclusions retained

- No app controller decomposition; no `app.js` full typecheck; no profile /
  mission-selection / launch-travel / rescue / pause-timer controller split.
- No RenderRuntime TypeScript migration; no full RenderRuntime API typing
  (deferred to WP-40); no Pixi package/runtime migration; no Pixi
  display-object types.
- No TravelScene / SeaTurtleScene / CrabScene implementation typing (WP-41
  family); no Young Whale scene; no terrain or mission gameplay snapshot
  shared migration; no Sea Turtle / Crab / Young Whale domain logic change.
- No renderer backend, visual, balance, speed/duration, dependency, lockfile,
  or tool-version change; no TypeScript compiler API integration; no
  Vite experimental bundled dev mode.
- No WP-03A/WP-03B; no unrelated lint repair; no PR; no feature branch; no
  force push.
