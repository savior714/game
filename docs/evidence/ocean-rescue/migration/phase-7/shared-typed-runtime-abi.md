# Ocean Rescue Shared Typed Runtime ABI (WP-32A)

- Task ID: `AIDENGAME-OCEAN-RESCUE-WP32A-SHARED-TYPED-RUNTIME-ABI-01`
- Captured: 2026-08-04
- Implementation base origin/main: `be51918d23b09e3b988e53d64f9b84163e9abd57`
- Publication integration base origin/main: `be51918d23b09e3b988e53d64f9b84163e9abd57`
- Result: PASS
- Migration state: `PHASE_7_IN_PROGRESS` (WP-32A COMPLETE)
- Shared mission ID state: `TYPE_AUTHORITY`
- Global OceanRescue ABI state: `TYPED_SHARED`
- Typed module ESM adapter state: `CHECKED_JS`
- Runtime output state: `BYTE_IDENTICAL`
- Next executable work package: WP-32B

## Objective

WP-32A establishes one minimal shared type boundary between the typed canonical
Ocean Rescue modules and the ESM compatibility adapters without changing any
runtime statement: the shared mission identifier authority, the runtime ABI
type module, the single global `window.OceanRescue` declaration, and checked-JS
ESM adapters. Normalized pointer intents, renderer-adapter contracts, and
application orchestration types are explicitly out of scope.

## Shared type modules

- `domains/ocean-rescue/src/contracts/mission.ts`
  - SHA-256: `a81620ca8e74906bfde702a0e32f73c0b20e47d68578e569b2ff9cab6e509497`
  - Type: `MissionId = "sea-turtle" | "crab" | "young-whale"` (type-only, no
    runtime JavaScript).
- `domains/ocean-rescue/src/contracts/runtime-abi.ts`
  - SHA-256: `83048f820ca034a7b585c1e9c35039f0ddb3865ecff64a53155b309782286200`
  - Type-only composes `ProfileApi`, `LaunchApi`, `StateApi`, `TravelApi`,
    `MissionCatalog`, `GupCatalog`, `MissionId`, `GupId` and defines
    `MissionProgressionSnapshot`, `MissionCompletionResult`, `MissionsApi`,
    `GupSelectionSnapshot`, `GupsApi`, `OceanRescueNamespace` (all optional
    slots; no index signature; no `any`).
- `domains/ocean-rescue/src/contracts/ocean-rescue-global.d.ts`
  - SHA-256: `71d8bfba2bbf24d2f1e61b4ae630f93719b2921d6650a3c24ffb97612b845843`
  - Single optional `Window.OceanRescue` declaration (module scoped).

## Shared identifier wiring

- `src/missions/catalog.ts` imports the shared `MissionId` and keeps the
  compatibility alias `export type MissionId = SharedMissionId;`.
- `src/launch/launch.ts` imports the shared `MissionId`, uses it for
  `LaunchCatalogEntry.missionId`, and keeps the compatibility alias
  `export type LaunchMissionId = MissionId;`. No separate launch string union
  remains.
- `ProfileAnimalId`, `GupId`, and `Phase` are left domain-local (no typed
  cross-module consumer is proven for them).

## Typed canonical module changes

The duplicated local `OceanRescueGlobalNamespace` interfaces were removed from
`profile/profile.ts`, `launch/launch.ts`, `state/state.ts`, and
`travel/travel.ts`; each now imports the shared `OceanRescueNamespace` type and
casts `window` through it. The emitted runtime registration statements
(`const win = window; const root = win.OceanRescue || {}; win.OceanRescue =
root; root.<Slot> = <Api>;`) are unchanged.

## Checked ESM adapters

All six `src/esm/*.js` adapters now start with `// @ts-check` and reference the
shared global declaration (`/// <reference path="../contracts/ocean-rescue-global.d.ts" />`):

- `profile.js`, `launch.js`, `state.js`, `travel.js`: typecheck with the shared
  declaration; no runtime statement change.
- `missions.js`, `gups.js`: typecheck with the shared declaration; the facade
  keeps the exact legacy controller method references (`getSnapshot:
  registered.getSnapshot`, etc.); the single global assignment
  `window.OceanRescue.Missions = Missions` carries a JSDoc type assertion that
  is erased by the minifier, so the production bundle stays byte-identical.

No `@ts-ignore`, `@ts-nocheck`, `@ts-expect-error`, `any`, or broad `Object`
type is introduced. Import order, fail-close messages, and method identity are
preserved.

## Type verification

- Effective config: `strict: true`, `noEmit: true`, `module: ESNext`,
  `moduleResolution: Bundler`, `allowJs: true`, `checkJs: false`
  (`domains/ocean-rescue/tsconfig.json`).
- Exact project command:
  `cd domains/ocean-rescue && corepack pnpm exec tsc --project tsconfig.json --noEmit`
- Diagnostics: exit 0.
- Standalone adapter typecheck (the six adapters compiled together with
  `--ignoreConfig ... --allowJs --checkJs false --noEmit`): exit 0.

## Type-only output

From a clean `production-bundle-metadata.json`:

```text
contracts/* modules in actual_module_files: none
dynamic_import_count: 0
sourcemap: false
application JS chunk: exactly one (ocean-rescue-app.js)
production output files: { ocean-rescue-app.js, production-bundle-metadata.json }
```

## Exact output identity (baseline == final)

```text
dist/ocean-rescue-app.js                         9992fe6a5acb9f889f15753cf600964b57172e3e7a0dac82d21f736fdda770d7  (byte-identical)
dist/production-bundle-metadata.json             0cd90e8878499fb284d0fbe60c99588b606ed73332b238f1ee2191744af5ee1d  (byte-identical)
ocean-rescue/index.html                          a43500664a4b82772c6e842121c62c5bbfe6288ba5cbe2c5afc72fd7f9f63643  (byte-identical)
dist/legacy-rollback.html                        9562d991a64852da59531e830742d6936c759eb8792179a1ce993a8cd49a2729  (byte-identical)
```

The baseline was captured from a clean pipeline before the type-only change and
re-measured after; all four artifacts are byte-identical.

## Module graph / membership

- Canonical graph includes: `profile/profile.ts`, `missions/catalog.ts`,
  `gups/catalog.ts`, `launch/launch.ts`, `state/state.ts`, `travel/travel.ts`,
  `missions.js` (controller), `gups.js` (controller), and all `src/esm/*`
  adapters.
- Canonical graph excludes: `profile.js`, `launch.js`, `state.js`, `travel.js`
  (rollback-only), and all `src/contracts/*` modules (type-only).
- Production `actual_module_files`: 38 entries, unchanged from baseline; no
  `contracts/` entry.

## Rollback

- Legacy rollback build (`--mode legacy`) is byte-identical to the pre-WP-32A
  baseline `9562d991a64852da59531e830742d6936c759eb8792179a1ce993a8cd49a2729`.
- Operational rollback (`just check-ocean-rescue-rollback`) PASS: the tracked
  artifact transitions bundle -> legacy -> bundle and restores byte-identical
  canonical production output.
- Legacy sources are unchanged (byte-identical).

## Verification

- `just check-ocean-rescue-toolchain` — PASS (Node 24.18.0, pnpm 11.17.0,
  Vite 8.1.5, TypeScript 7.0.2).
- `just check-ocean-rescue-shared-runtime-abi-types` — PASS (all groups):
  - `test_ocean_rescue_wp32a_shared_runtime_abi_types.py` — 17 passing
    (shared identifier, global ABI declaration, adapter typecheck, type-only
    output, exact output identity);
  - `test_ocean_rescue_wp31c_typed_core_state_travel.py` — 19 passing;
  - `test_ocean_rescue_wp31b_typed_static_catalogs.py` — 15 passing;
  - `test_ocean_rescue_wp31a_typed_profile.py` — 8 passing;
  - `test_ocean_rescue_wp30_esm_entry_module_graph.py` — 21 passing;
  - `test_ocean_rescue_wp21_production_bundle_cutover.py` — 19 passing;
  - `test_ocean_rescue_wp20_shadow_bundle.py` — 24 passing;
  - `just check-ocean-rescue-rollback` — PASS;
  - `test_ocean_rescue_artifact_drift.py` — 6 passing;
  - `test_ocean_rescue_wp03_scope_decision.py` — 3 passing.

## Exclusions retained

- `src/app.js` and `src/esm/app.js` are not typed or restructured (no `@ts-check`
  added to `app.js`); application orchestration decomposition is out of scope.
- No normalized pointer intent implementation; no renderer-adapter API; no
  renderer-owned gameplay model; no `TravelScene`/`Terrain`/`Rescue`/mission
  scene changes; no pause/timer ownership; no input architecture change.
- No mission progression or GUP selection runtime implementation change; legacy
  `missions.js` and `gups.js` are unchanged.
- No `ProfileAnimalId`, `GupId`, or `Phase` shared migration.
- No dependency, lockfile, TypeScript, Vite, Pixi, Node, or pnpm version change;
  no tsconfig strictness relaxation.
- No root Python typecheck debt repair; no WP-03A/WP-03B; no WP-33; no PR; no
  feature branch; no force push.
