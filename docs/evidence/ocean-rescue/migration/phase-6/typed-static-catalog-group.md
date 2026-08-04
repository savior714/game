# Ocean Rescue Typed Static Catalog Group (WP-31B)

- Captured: 2026-08-04
- Implementation base origin/main: `1f4b82731c282410cbbd26795c2e19abc52d27bd`
- Publication integration base origin/main: `1f4b82731c282410cbbd26795c2e19abc52d27bd`
- Result: PASS
- Migration state: `PHASE_6_IN_PROGRESS` (WP-31A COMPLETE, WP-31B COMPLETE)
- Mission catalog state: `TYPED_CANONICAL`
- GUP catalog state: `TYPED_CANONICAL`
- Launch module state: `TYPED_CANONICAL`
- Legacy missions.js: `CONTROLLER_CANONICAL_PLUS_ROLLBACK`
- Legacy gups.js: `CONTROLLER_CANONICAL_PLUS_ROLLBACK`
- Legacy launch.js: `ROLLBACK_ONLY`
- Next executable work package: WP-31C
- Production authority: canonical ESM graph owns the typed static-data modules
- Rollback authority: `build-manifest.legacy.json` references unchanged
  `missions.js`, `gups.js`, and `launch.js`

## Objective

WP-31B migrates the mission catalog, GUP catalog, and the demonstrably static
launch content from untyped rollback-oriented JavaScript modules to strictly
typed canonical TypeScript modules while preserving all runtime values,
ordering, immutability, mutable controller behavior, browser behavior,
deterministic packaging, and the byte-identical legacy rollback sources.

Mission progression state and GUP selection state are not migrated in this
task; the unchanged legacy controllers continue to own that mutable state.

## Canonical versus legacy ownership

- Canonical ESM production/dev graph:
  - `src/main.js → src/esm/app.js`
  - `src/esm/missions.js → src/missions/catalog.ts` (typed catalog) and
    `src/missions.js` (unchanged controller)
  - `src/esm/gups.js → src/gups/catalog.ts` (typed catalog) and
    `src/gups.js` (unchanged controller)
  - `src/esm/launch.js → src/launch/launch.ts` (typed launch API; legacy
    `src/launch.js` is no longer executed by the canonical graph)
- Legacy rollback graph: `build-manifest.legacy.json` references unchanged
  `missions.js`, `gups.js`, and `launch.js` (plus `profile.js`).
- Legacy source SHA-256 before/after (unchanged):

```text
src/missions.js  f636fed0c9d0bb0b6746bcb7c7aaea19c6f9e81466096d8324aa514b24aa4d33
src/gups.js      bf10d685522bbb16d2886d2f8c73ee807295688f4f36a347f037db725172e219
src/launch.js    1e466a6a611545874e4099d4c55417a17f36a729cb0b2e841f64d87c5491cfce
```

## Typed modules

- `domains/ocean-rescue/src/missions/catalog.ts`
  - SHA-256: `eae6b05300fbf44e4010a085e2cfa4991b94f61941071c54ce4359120da3ade0`
  - Types: `MissionId`, `MissionCatalogEntry`, `MissionCatalog`; frozen
    catalog array with three frozen entries in canonical order; exports
    `Catalog` (alias `MissionsCatalog`).
- `domains/ocean-rescue/src/gups/catalog.ts`
  - SHA-256: `1140f0005e8c0d3230b98af51fe5a2676c48080546cb26fcd0320e112386dc3d`
  - Types: `GupId`, `GupCatalogEntry`, `GupCatalog`; frozen catalog array with
    three frozen entries in canonical order; exports `Catalog` (alias
    `GupsCatalog`).
- `domains/ocean-rescue/src/launch/launch.ts`
  - SHA-256: `975e3f6e639a0cb0ae76850ef7d480506d13c39b73b03bc50d9cd82a3279845c`
  - Types: `LaunchMissionId`, `LaunchCatalogEntry`, `LaunchCatalog`,
    `LaunchApi`; frozen launch catalog; `DurationMs = 6000`;
    `GoalDurationMs = 3000`; strictly typed `getMissionContent()`;
    frozen `Launch` API; temporary `window.OceanRescue.Launch` ABI; exports
    `Catalog`, `DurationMs`, `GoalDurationMs`, `getMissionContent`, `Launch`
    (alias `OceanRescueLaunch`).

## Adapter / facade design

- `src/esm/missions.js`: imports the typed mission catalog, side-effect
  imports the unchanged legacy controller `../missions.js`, validates the
  legacy API and catalog parity, and builds one frozen facade whose `Catalog`
  is the typed catalog and whose methods are the exact unchanged controller
  method references. The facade replaces the temporary
  `window.OceanRescue.Missions` ABI and is exported as `Missions`; the typed
  catalog is exported as `Catalog`.
- `src/esm/gups.js`: the same bounded pattern for GUP
  (`window.OceanRescue.Gups` facade + `Catalog` export).
- `src/esm/launch.js`: imports and re-exports the typed launch module, verifies
  `window.OceanRescue.Launch` registers the same frozen API object, and no
  longer side-effect-imports `../launch.js`.
- `src/app.js` still consumes the temporary globals
  (`window.OceanRescue.Missions/Gups/Launch`); the compatibility ABI is
  preserved and the application orchestration is not converted.

Required invariants (proven on the real compiled/transformed modules):

```text
window.OceanRescue.Missions === Missions ESM export
window.OceanRescue.Missions.Catalog === typed mission catalog export
window.OceanRescue.Gups === Gups ESM export
window.OceanRescue.Gups.Catalog === typed GUP catalog export
window.OceanRescue.Launch === Launch ESM export
window.OceanRescue.Launch.Catalog === typed launch catalog export
```

## Type verification

- Effective config: `strict: true`, `noEmit: true`, `module: ESNext`,
  `moduleResolution: Bundler`, `allowJs: true`, `checkJs: false`
  (`domains/ocean-rescue/tsconfig.json`).
- Exact compiler command:
  `cd domains/ocean-rescue && corepack pnpm exec tsc --project tsconfig.json --noEmit`
- Diagnostics: exit 0. No suppressions, no `any`, no `@ts-ignore`,
  `@ts-nocheck`, or `@ts-expect-error`, no strictness relaxation, no
  WP-32-style shared cross-domain type module.

## Catalog parity matrix

The behavioral matrix runs the real typed modules and the real ESM adapters
(transpiled by the installed TypeScript package) against the unchanged legacy
sources and proves byte-identical parity for:

- mission catalog: array length/order, property names/values, frozen status,
  `getSnapshot`, `isUnlocked`, `selectMission`, `completeMission`,
  `markMissionViewed` return values, persistence payloads, removal attempts,
  thrown/not-thrown behavior, and storage failure isolation across 27
  scenarios (fresh, selection, locked/invalid selection, ordered completion,
  next-mission unlock, New-badge insertion/removal, repeated completion,
  full progression, hydrate, malformed JSON/primitive/array, wrong schema
  version, unknown mission id, out-of-order completion, storage get/set/remove
  throws, non-function storage);
- GUP catalog: array length/order, property names/values, frozen status, and
  `getSnapshot`, `selectGup`, `prepareSelection`, `confirmSelection` return
  values across 11 scenarios;
- launch: catalog order/values, `DurationMs === 6000`,
  `GoalDurationMs === 3000`, and exact `getMissionContent()` lookup for every
  valid mission ID and for unknown string, empty string, undefined, null,
  number, object, array, NaN, and boolean.

Runtime immutability is proven: APIs, catalogs, and entries are frozen;
`push` on any catalog rejects; property assignment on frozen entries and APIs
is rejected; the exact enumerable API shapes match the legacy contracts.

## Module graph

- Canonical graph includes: `missions/catalog.ts`, `gups/catalog.ts`,
  `launch/launch.ts`, `missions.js` (controller), `gups.js` (controller),
  plus `profile/profile.ts`.
- Canonical graph excludes: `launch.js` (rollback-only) and `profile.js`
  (rollback-only).
- One canonical root (`src/main.js`), no dynamic imports, no bare imports, no
  duplicate implementation, no secondary production JS chunk.
- Rollback manifest (`build-manifest.legacy.json`) still references
  `missions.js`, `gups.js`, and `launch.js` (19 ordered entries, unchanged).
- `vite.bundle.ts` now fail-closes if the rollback-only `launch.js` ever
  enters the application bundle (matching the existing `profile.js` guard).

## Production membership

From `production-bundle-metadata.json` `actual_module_files`:

```text
missions/catalog.ts  present (typed canonical)
gups/catalog.ts      present (typed canonical)
launch/launch.ts     present (typed canonical)
profile/profile.ts   present (typed canonical)
missions.js          present (unchanged controller)
gups.js              present (unchanged controller)
launch.js            absent (rollback-only)
profile.js           absent (rollback-only)
```

## Determinism

- Two clean `vite.production.config.ts` builds: byte-identical bundle and
  metadata.
- Two standalone HTML builds: byte-identical.
- Tracked `ocean-rescue/index.html` matches a clean production rebuild
  (`test_tracked_artifact_matches_clean_production_rebuild` and
  `tests/test_ocean_rescue_artifact_drift.py`).
- Recorded hashes (single clean rebuild):

```text
dist/ocean-rescue-app.js                          e1907b5adc478e1e9ba80b6730689c87693bf658a5ad15549d07f39f800f059f
dist/production-bundle-metadata.json              f1c18966081ef49e40035f3be4049489da98b9f90c26ed603940abbe0b501ef0
ocean-rescue/index.html                          900cea0e1d93036ffdf46cbbb48fd70ff9776c3bff66f30d9383b6b368969e0b
```

## Browser flow

Verified in a real browser against the tracked standalone artifact from a
deterministic storage state (valid profile seeded, empty progression):

1. Mission selection appears with the three mission cards in canonical order
   (sea-turtle, crab, young-whale) and exact titles, companions, summaries,
   and initial lock/availability state (Available / Locked / Locked; only
   sea-turtle enabled; no New badges).
2. Selecting the first mission enters GUP selection with the three GUP cards
   in canonical order (gup-c, gup-i, gup-x) and exact names and descriptions.
3. Selecting and confirming GUP-I enters the launch sequence; the briefing is
   the exact typed launch briefing for sea-turtle, the GUP name is GUP-I, and
   the companion label is "Peso:".
4. Timing contract verified through the runtime objects:
   `Launch.DurationMs === 6000`, `Launch.GoalDurationMs === 3000`;
   `getMissionContent("sea-turtle")` returns the typed briefing/goal; unknown
   lookup returns null.
5. Runtime identity/immutability in the page: mission/GUP/launch catalogs and
   APIs frozen; mutation attempts (push, property assignment, DurationMs
   write) do not alter values.
6. Skipping the launch shows the goal banner with the exact typed goal
   ("Rescue the sea turtle!").
7. No page error, no console error, no request failure, no forbidden external
   request; single application startup (`data-ocean-rescue-ready="true"`,
   `OceanRescue.App` present).

## Rollback

- Legacy rollback build (`--mode legacy`) references all three legacy files
  and is byte-identical to the pre-WP-31B baseline
  `cfd991d83524db6c7ad225da11ef7a9421300bdf588c4b905bf4e5556f776582`.
- Operational rollback (`just rollback-ocean-rescue-to-legacy`) transitioned
  the canonical artifact to the legacy ordered-script artifact and back; the
  tracked artifact is restored to canonical production mode with exactly two
  inline classic scripts.
- Legacy sources (`missions.js`, `gups.js`, `launch.js`) are byte-identical
  (SHA-256 values above).

## Verification

- `just check-ocean-rescue-toolchain` — PASS (Node 24.18.0, pnpm 11.17.0,
  Vite 8.1.5, TypeScript 7.0.2).
- `corepack pnpm exec tsc --project tsconfig.json --noEmit` — exit 0, no
  suppressions.
- `tests/test_ocean_rescue_wp31b_typed_static_catalogs.py` — 15 passing
  (static ownership, legacy byte identity, strict typecheck, behavioral
  matrix + parity, determinism, membership, rollback, browser flow).
- `tests/test_ocean_rescue_mission_progression.py` — 13 passing.
- `tests/test_ocean_rescue_gup_selection.py` — 8 passing.
- `tests/test_ocean_rescue_launch_presentation.py` — 8 passing.
- `tests/test_ocean_rescue_wp31a_typed_profile.py` — 8 passing.
- `tests/test_ocean_rescue_wp30_esm_entry_module_graph.py` — 22 passing
  (three-category adapter contract: unmigrated, controller+typed, migrated
  typed; typed reachability; rollback exclusions; manifest retention).
- `tests/test_ocean_rescue_wp21_production_bundle_cutover.py` — 19 passing
  (typed membership, determinism, two-block artifact, rollback byte-identity,
  browser parity, documentation state).
- `tests/test_ocean_rescue_wp20_shadow_bundle.py` — 25 passing (shadow
  membership incl. typed static modules and launch.js exclusion).
- `tests/test_ocean_rescue_profile_choice.py` — 14 passing.
- `tests/test_ocean_rescue_artifact_drift.py`, `test_ocean_rescue_source_scaffold.py`,
  `test_ocean_rescue_wp11_dev_server.py`, `test_ocean_rescue_wp03_scope_decision.py`
  — PASS.

## Unrelated baseline failures (unchanged by WP-31B)

- `test_ocean_rescue_pixi_backend_smoke_contract::test_lock_pinned_pixi`
  (stale package-lock versus pnpm authority).
- `test_git_workflow_guardrails::test_justfile_typecheck_has_resilient_fallback_and_exclusions`
  (root typecheck gate contract).

## Exclusions retained

- No mission progression TypeScript conversion; no mission persistence,
  storage-key, or schema change; no GUP mutable-state TypeScript conversion;
  no state-machine, travel, terrain, renderer, rescue-domain, or
  mission-specific gameplay conversion; no application-orchestration
  conversion; no direct ESM conversion of `app.js`; no shared WP-32 boundary
  type module; no speculative generic catalog framework; no catalog redesign;
  no content wording changes; no new missions or GUPs; no visual/asset change;
  no timer behavior change; no source maps; no code splitting; no dependency
  addition or upgrade; no Pixi migration; no stale package-lock repair; no
  root typecheck-gate repair; no WP-03A/WP-03B work; no pull request.
