# Ocean Rescue Typed Core State and Travel Contracts (WP-31C)

- Task: AIDENGAME-OCEAN-RESCUE-WP31C-TYPED-CORE-STATE-TRAVEL-CONTRACTS-01
- Captured: 2026-08-04
- Implementation base origin/main: `1bba2ce0d6d449116c82f7916f7dbef2f00696a9`
- Publication integration base origin/main: `1bba2ce0d6d449116c82f7916f7dbef2f00696a9`
- Result: PASS
- Migration state: `PHASE_6_COMPLETE` (WP-31A COMPLETE, WP-31B COMPLETE,
  WP-31C COMPLETE; current phase `PHASE_7_READY`)
- State module state: `TYPED_CANONICAL`
- Travel module state: `TYPED_CANONICAL`
- Legacy state.js: `ROLLBACK_ONLY`
- Legacy travel.js: `ROLLBACK_ONLY`
- Next executable work package: WP-32
- Production authority: canonical ESM graph owns the typed core state machine
  and the typed travel runtime contract
- Rollback authority: `build-manifest.legacy.json` references unchanged
  `state.js` and `travel.js`

## Objective

WP-31C migrates the core state machine (`src/state.js`) and the tightly coupled
travel runtime state (`src/travel.js`) from untyped rollback-oriented JavaScript
modules to strictly typed canonical TypeScript modules while preserving every
observable runtime contract: public API shape, return values, invalid-input
rejection, frozen object identity and immutability, transition order, state
mutation order, browser-visible flow, deterministic production artifact, the
byte-identical legacy rollback sources, and the temporary
`window.OceanRescue.State`/`window.OceanRescue.Travel` compatibility ABIs.

`src/app.js` orchestration, scenes, the renderer, and the mission controller
are not changed.

## Canonical versus legacy ownership

- Canonical ESM production/dev graph:
  - `src/main.js → src/esm/app.js`
  - `src/esm/state.js → src/state/state.ts` (typed canonical core state
    machine; legacy `src/state.js` is no longer executed by the canonical
    graph)
  - `src/esm/travel.js → src/travel/travel.ts` (typed canonical travel runtime
    contract; legacy `src/travel.js` is no longer executed by the canonical
    graph)
- Legacy rollback graph: `build-manifest.legacy.json` references unchanged
  `state.js` and `travel.js` (19 ordered entries, unchanged).
- Legacy source SHA-256 before/after (unchanged):

```text
src/state.js   ca8328a21dbe4d8719ebedb689574d03f1211749ce2b0e84016976498881d04d
src/travel.js  78a422ab86d93cb003ec33aecd6ede4a25b5d5d78ee534c86c28a84117518cec
```

## Typed modules

- `domains/ocean-rescue/src/state/state.ts`
  - SHA-256: `4b8c3a0d529d008b55b8eea6378fa01e901cdefbba3000aa97f60bd332311e66`
  - Types: `Phase`, `PhaseMap`, `TransitionMap`, `TransitionToken`,
    `StateSnapshot`, `StateApi`; frozen `Phases` (11 exact key/value pairs in
    order), frozen transition allow-list, initial `BOOT`/`ready === false`,
    transition locking, monotonically increasing transition IDs, frozen
    `{ id, from, to }` tokens, snapshot shape, `forcePhase` lock/token
    cleanup; exports `Phases`, `State` (alias `OceanRescueState`).
- `domains/ocean-rescue/src/travel/travel.ts`
  - SHA-256: `1376ea1056a447187292ca2018818438ac60424ee0afeaac3fd98c6af3901c73`
  - Types: `TravelBounds`, `TravelSnapshot`, `TravelApi`; frozen `Bounds`
    (`minY: 120`, `maxY: 600`, `startY: 360`), `AutoForwardSpeed === 120`,
    `TapSpeed === 360`, 50ms delta cap, forward multiplier default 1 and exact
    0..1 range rejection, tap-target movement and clear timing, drag pointer
    ownership, begin-drag `dragPrevStageY` clamping, move-drag previous-stage
    ordering, clamp ordering, start/stop reset scope, exact invalid-input
    return values; exports `Bounds`, `Travel` (alias `OceanRescueTravel`).

## Adapter design

- `src/esm/state.js`: imports and re-exports the typed state module, verifies
  `window.OceanRescue.State` registers the same frozen API object, and no
  longer side-effect-imports `../state.js`.
- `src/esm/travel.js`: imports and re-exports the typed travel module, verifies
  `window.OceanRescue.Travel` registers the same frozen API object, and no
  longer side-effect-imports `../travel.js`.
- `src/app.js` still consumes the temporary globals
  (`window.OceanRescue.State`, `window.OceanRescue.Travel`); the compatibility
  ABIs are preserved and the application orchestration is not converted.

Required invariants (proven on the real compiled/transformed modules and in the
browser):

```text
window.OceanRescue.State === State ESM export
window.OceanRescue.Travel === Travel ESM export
```

## Type verification

- Effective config: `strict: true`, `noEmit: true`, `module: ESNext`,
  `moduleResolution: Bundler`, `allowJs: true`, `checkJs: false`
  (`domains/ocean-rescue/tsconfig.json`).
- Exact compiler command:
  `cd domains/ocean-rescue && corepack pnpm exec tsc --project tsconfig.json --noEmit`
- Diagnostics: exit 0. No suppressions, no `any`, no `@ts-ignore`,
  `@ts-nocheck`, or `@ts-expect-error`, no strictness relaxation beyond the
  existing `skipLibCheck`, no dynamic import, no bare import, no runtime
  dependency addition, no WP-32-style shared cross-domain type module.

## Behavioral parity matrix

The behavioral matrix runs the real typed modules and the real ESM adapters
(transpiled by the installed TypeScript package) against the unchanged legacy
sources. Both implementations run in strict mode to match the real ESM/bundle
execution context (imported modules are always strict). Parity is asserted by
byte-identical JSON of the full result record.

### State (27 scenarios)

Initial snapshot; `markReady` first call; repeated `markReady`; BOOT →
PROFILE_CHOICE; BOOT → MISSION_SELECT; forbidden BOOT → TRAVEL; same-phase
rejection; invalid string phase; non-string phase (42, null, object,
undefined); second-transition rejection while locked; valid token completion;
stale token completion; forged-ID token; forged-from token; forged-to token;
null token; undefined token; primitive token; empty-object token; valid
`forcePhase`; invalid `forcePhase`; `forcePhase` cleanup of an active
transition; full phase progression (monotonic transition IDs 1..9); MISSION
COMPLETE → MISSION_SELECT; MISSION COMPLETE → LAUNCH; snapshot mutation
attempt; token mutation attempt; API mutation attempt; Phases mutation attempt.

Compared for each scenario: return values, thrown/not-thrown, snapshot,
transition token shape (`{ id, from, to }`, frozen status, enumerable keys),
transition ID sequence, frozen status, and exact enumerable API shape.

### Travel (35 scenarios)

Initial snapshot; inactive `stop`; inactive `step`; inactive `tapTo`; inactive
`beginDrag`; `start`; repeated `start`; positive step; delta > 50 cap;
multiplier omitted; multiplier 0; multiplier 1; multiplier negative; multiplier
> 1; NaN multiplier; Infinity multiplier; invalid delta (0, negative, NaN,
Infinity, string, null, object); tap above maxY; tap below minY; tap equal
current Y; tap movement completion; drag begin; second drag begin rejection;
wrong-pointer move; correct-pointer move; drag clamping; wrong-pointer end;
correct-pointer end; tap while dragging rejection; stop during tap; stop during
drag; restart after stop; Bounds mutation attempt; snapshot mutation attempt;
API mutation attempt.

Floating-point results are compared byte-exactly (full JSON number
representation) at each execution step; no rounding is used to hide
differences.

Runtime immutability is proven: `State`, `Travel`, `Phases`, `Bounds`, every
snapshot, and every transition token are frozen; mutation attempts reject; the
exact enumerable API shapes match the legacy contracts.

## Module graph

- Canonical graph includes: `state/state.ts`, `travel/travel.ts`, plus
  `profile/profile.ts`, `missions/catalog.ts`, `gups/catalog.ts`,
  `launch/launch.ts`, `missions.js` (controller), `gups.js` (controller).
- Canonical graph excludes: `state.js`, `travel.js`, `launch.js`,
  `profile.js` (all rollback-only).
- One canonical root (`src/main.js`), no dynamic imports, no bare imports, no
  duplicate implementation, no secondary production JS chunk.
- Rollback manifest (`build-manifest.legacy.json`) still references `state.js`
  and `travel.js` (19 ordered entries, unchanged).
- `vite.bundle.ts` now fail-closes if the rollback-only `state.js` or
  `travel.js` ever enters the application bundle (matching the existing
  `profile.js`/`launch.js` guards).

## Production membership

From `production-bundle-metadata.json` `actual_module_files`:

```text
state/state.ts       present (typed canonical)
travel/travel.ts     present (typed canonical)
profile/profile.ts   present (typed canonical)
missions/catalog.ts  present (typed canonical)
gups/catalog.ts      present (typed canonical)
launch/launch.ts     present (typed canonical)
missions.js          present (unchanged controller)
gups.js              present (unchanged controller)
state.js             absent (rollback-only)
travel.js            absent (rollback-only)
launch.js            absent (rollback-only)
profile.js           absent (rollback-only)
```

`dynamic_import_count: 0`; `sourcemap: false`; exactly one application JS
chunk.

## Determinism

- Two clean `vite.production.config.ts` builds: byte-identical bundle and
  metadata.
- Two standalone HTML builds: byte-identical.
- Tracked `ocean-rescue/index.html` matches a clean production rebuild
  (`test_tracked_artifact_matches_clean_production_rebuild`,
  `test_tracked_artifact_matches_clean_production_rebuild`, and
  `tests/test_ocean_rescue_artifact_drift.py`).
- Recorded hashes (single clean rebuild):

```text
dist/ocean-rescue-app.js                          ec5b4deea8f9e5198d8fb6a80033aac89caecaadd93508a0e096ee27adceac3f
dist/production-bundle-metadata.json              0073d32a703327b68b7f4660d09e572e27a89c0c41b404009e12cd0ae270c9a2
ocean-rescue/index.html                          658507f9d7731a9f470f3fa69f9ed7f1be3cf608435bfcf29f91741149679cd4
```

## Browser flow

Verified in a real browser against the tracked standalone artifact from a
deterministic storage state (valid profile seeded, empty progression) with a
controlled `requestAnimationFrame` clock (deterministic timestamps, no real
waiting):

1. Seeded profile skips the profile choice and reaches mission selection.
2. Selecting the first mission (sea-turtle) enters GUP selection; selecting
   GUP-X and confirming enters the launch sequence (phase `LAUNCH`).
3. During LAUNCH the runtime globals are verified: `State` and `Travel`
   frozen, `Phases` in canonical order (11 entries, BOOT first,
   MISSION_COMPLETE last), `Bounds === { minY: 120, maxY: 600, startY: 360 }`
   frozen, `AutoForwardSpeed === 120`, `TapSpeed === 360`, and no transition
   lock remains.
4. Skipping the launch reaches `TRAVEL` with an active travel snapshot
   (`active === true`, `distance === 0`, `y === 360`, `tapTargetY === null`,
   `dragging === false`, `pointerId === null`) and no transition lock.
5. Under the deterministic clock the travel distance advances.
6. A tap on the canvas sets a Y target within [120, 600]; the deterministic
   frames move Y to exactly the target and clear the tap target.
7. A drag on the canvas begins with the pointer id, moves Y, and ends with
   `dragging === false` and `pointerId === null` while preserving Y.
8. Advancing the authoritative travel distance to `ArrivalDistance` (6000) and
   letting the travel loop run reaches `RESCUE_SITE_TRANSITION` with
   `transitionLocked === false` and `ready === true`.
9. No page error, no console error, no request failure, no forbidden external
   request; single application startup (`data-ocean-rescue-ready="true"`, one
   `OceanRescue.App` namespace).

## Rollback

- Legacy rollback build (`--mode legacy`) references both `state.js` and
  `travel.js` and is byte-identical to the pre-WP-31C baseline
  `cfd991d83524db6c7ad225da11ef7a9421300bdf588c4b905bf4e5556f776582`.
- Operational rollback (`just rollback-ocean-rescue-to-legacy`) transitioned
  the canonical artifact to the legacy ordered-script artifact and back; the
  tracked artifact is restored to canonical production mode with exactly two
  inline classic scripts.
- Legacy sources (`state.js`, `travel.js`) are byte-identical (SHA-256 values
  above).

## Verification

- `just check-ocean-rescue-typed-core-state-travel` — PASS (the focused
  command for this work package).
- `just check-ocean-rescue-toolchain` — PASS (Node 24.18.0, pnpm 11.17.0,
  Vite 8.1.5, TypeScript 7.0.2).
- `corepack pnpm exec tsc --project tsconfig.json --noEmit` — exit 0, no
  suppressions.
- `tests/test_ocean_rescue_wp31c_typed_core_state_travel.py` — 19 passing
  (static ownership, legacy byte identity, strict typecheck, behavioral
  matrix + parity, determinism, membership, rollback, browser flow).
- `tests/test_ocean_rescue_state_machine.py` — 7 passing.
- `tests/test_ocean_rescue_travel_movement.py` — 8 passing.
- `tests/test_ocean_rescue_launch_presentation.py` — 8 passing.
- `tests/test_ocean_rescue_wp31b_typed_static_catalogs.py` — 15 passing.
- `tests/test_ocean_rescue_wp31a_typed_profile.py` — 8 passing.
- `tests/test_ocean_rescue_wp30_esm_entry_module_graph.py` — 21 passing
  (four-category adapter contract: unmigrated, controller+typed, migrated
  typed incl. state/travel; typed reachability; rollback exclusions for all
  four rollback-only files; manifest retention).
- `tests/test_ocean_rescue_wp21_production_bundle_cutover.py` — 19 passing
  (typed state/travel membership, determinism, two-block artifact, rollback
  byte-identity, browser parity, documentation state).
- `tests/test_ocean_rescue_wp20_shadow_bundle.py` — 24 passing (shadow
  membership incl. typed state/travel and state.js/travel.js exclusion).
- `tests/test_ocean_rescue_artifact_drift.py`, `test_ocean_rescue_wp11_dev_server.py`,
  `test_ocean_rescue_wp03_scope_decision.py` — PASS.

## Unrelated baseline failures (unchanged by WP-31C)

- `test_ocean_rescue_pixi_backend_smoke_contract::test_lock_pinned_pixi`
  (stale package-lock versus pnpm authority).
- `test_git_workflow_guardrails::test_justfile_typecheck_has_resilient_fallback_and_exclusions`
  (root typecheck gate contract).

## Exclusions retained

- No `app.js` orchestration decomposition; no mission progression controller
  migration; no GUP selection controller migration; no render runtime
  migration; no Pixi package/runtime migration; no TravelScene migration; no
  Terrain/Rescue/mission scene migration; no pause/timer ownership change; no
  input architecture redesign; no renderer backend change; no UI/UX redesign;
  no game balance change; no duration/speed constant change; no WP-03A/WP-03B
  work; no WP-32 shared boundary types; no WP-33 controller decomposition; no
  package/dependency upgrade; no TypeScript/Vite/Pixi/pnpm/Node version
  change; no root Python typecheck debt; no unrelated formatting; no pull
  request; no feature branch.
