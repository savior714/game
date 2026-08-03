# Ocean Rescue Typed Profile Vertical Slice (WP-31A)

- Captured: 2026-08-04
- Implementation base origin/main: `d2f92a01414f61f70ec0ece276a6e288203f888d`
- Publication integration base origin/main: `d2f92a01414f61f70ec0ece276a6e288203f888d`
- Result: PASS
- Migration state: `PHASE_6_IN_PROGRESS` (WP-31A COMPLETE)
- Profile module state: `TYPED_CANONICAL`
- Legacy profile.js: `ROLLBACK_ONLY`
- Next executable work package: WP-31B
- Production authority: canonical ESM graph owns the typed profile module
- Rollback authority: `build-manifest.legacy.json` references unchanged `profile.js`

## Objective

WP-31A migrates the Ocean Rescue profile model, persistence schema, storage
validation, and exported API from the legacy global-namespace JavaScript
implementation to a strictly typed TypeScript module, without changing runtime
behavior, converting application orchestration, or weakening the legacy
rollback path. The legacy `src/profile.js` is retained byte-for-byte and is used
only by the legacy rollback graph.

## Ownership

- Canonical ESM production/dev graph:
  `src/main.js → src/esm/app.js → src/esm/profile.js → src/profile/profile.ts`
- Legacy rollback graph:
  `build-manifest.legacy.json → src/profile.js`
- `src/profile.js` SHA-256 before: `bf97dfe2db22da02dde8f118d0770d568de8bc0ddccf9d4e2e23f86ce2d37951`
- `src/profile.js` SHA-256 after: `bf97dfe2db22da02dde8f118d0770d568de8bc0ddccf9d4e2e23f86ce2d37951` (unchanged)

## Typed module

- Path: `domains/ocean-rescue/src/profile/profile.ts`
- Adapter: `domains/ocean-rescue/src/esm/profile.js` imports the typed module,
  verifies `window.OceanRescue.Profile` registers the same frozen API object, and
  re-exports it. The adapter no longer side-effect-imports `../profile.js`.
- tsconfig: `src/**/*.ts` added to `include`; `strict`, `noEmit`, `allowJs`,
  `checkJs: false`, `module: ESNext`, `moduleResolution: Bundler` retained.

### Exported profile types

- `ProfileAnimalId` (`"arctic-fox" | "beaver" | "red-panda"`)
- `ProfileAnimal` (frozen catalog entry)
- `ProfileSnapshot` (immutable public snapshot)
- `ProfileStoredPayloadV1` (versioned stored payload)
- `SanitizedProfilePayload` (validated stored payload after sanitization)
- `ProfileStorage` (narrow storage capability)
- `ProfileApi` (public frozen API)

### Temporary global compatibility ABI

- The module registers `window.OceanRescue.Profile` (consumed by `src/app.js`)
  and exports the identical frozen API object through ESM.
- No shared cross-module type file is introduced (WP-32 owns shared boundary
  types). No `any`, no `@ts-ignore`/`@ts-nocheck`/`@ts-expect-error`, no
  strictness relaxation.

### Storage schema

- Key: `aidengame.oceanRescue.profile`
- Schema version: `1`
- Player name: `Aiden`
- Payload: `{ "schemaVersion": 1, "playerName": "Aiden", "animalId": "<id>" }`
- Accepted `animalId` values: `arctic-fox`, `beaver`, `red-panda`

## Behavioral matrix

Verified against the real typed implementation (transpiled by the installed
TypeScript package in a test-only Node harness) and compared for parity against
the unchanged legacy `src/profile.js`:

1. fresh state with no stored payload;
2. each of the three valid animal IDs;
3. invalid string ID;
4. non-string ID (42) and null;
5. valid selection and successful persistence (exact versioned payload write);
6. confirmation without selection;
7. second confirmation after completion;
8. valid stored payload hydration (chosen restored, `complete` true,
   `selectedAnimalId` stays null);
9. malformed JSON (best-effort removal);
10. parsed primitive (best-effort removal);
11. parsed array (best-effort removal);
12. missing schema version (rejected + removal);
13. wrong schema version (rejected + removal);
14. wrong player name (rejected + removal);
15. unknown animal ID (rejected + removal);
16. storage `getItem` throws (no-profile, no throw);
17. storage `setItem` throws (`confirmSelection` returns true, `complete` stays
    false, chosen animal preserved);
18. storage `removeItem` throws (cleanup swallowed);
19. missing or unusable storage methods (no persistence capability);
20. snapshot and API runtime immutability (frozen, mutation rejected).

Legacy-versus-typed parity compares return values, snapshots, serialized storage
writes, removal attempts, thrown/not-thrown behavior, global API shape, and
catalog order/values. Result: byte-identical for every scenario.

## Production module membership

- `profile/profile.ts` present in `actual_module_files`.
- `profile.js` (rollback-only) absent from the canonical graph and from
  `actual_module_files`.
- All 17 other unmigrated legacy implementations remain in the canonical graph.
- No duplicate profile implementation, no dynamic import, no bare import, no
  secondary JS chunk.

## Determinism

- Production bundle A/B: byte-identical (two clean `vite.production.config.ts`
  builds).
- Standalone HTML A/B: byte-identical.
- Tracked `ocean-rescue/index.html` matches a clean production rebuild
  (`check-ocean-rescue-drift` + WP-21 rebuild-match pass).

## Browser profile flow

Verified in a real browser against the tracked standalone artifact:

- A. First visit: profile-choice screen appears, three animals in canonical
  order, continue starts disabled, valid selection enables continue,
  confirmation enters mission selection, exact versioned payload is stored.
- B. Reload: valid stored profile hydrates, profile choice is skipped, mission
  selection appears, chosen animal preserved.
- C. Invalid stored payload: no completion, best-effort cleanup removes it,
  profile-choice appears.
- D. Runtime quality: no page error, no console error, no request failure, no
  forbidden external request, renderer/application startup healthy.

## Rollback

- `just rollback-ocean-rescue-to-legacy` reproduces the legacy ordered 19-script
  artifact; operational rollback SHA matches the pre-WP-31A baseline
  `cfd991d83524db6c7ad225da11ef7a9421300bdf588c4b905bf4e5556f776582`
  byte-for-byte.
- After rollback proof, `just build-ocean-rescue` restored the canonical typed
  production artifact (`8fcf181615b04cf33b90d924026467f2877db3b8a9cca9ff5a1407c1c5568ee9`).
- Final tracked artifact is canonical production mode with exactly two inline
  classic scripts.

## Verification

- `just check-ocean-rescue-toolchain` — PASS (Node 24.18.0, pnpm 11.17.0, Vite
  8.1.5, TypeScript 7.0.2).
- `just typecheck-ocean-rescue` / `corepack pnpm exec tsc --project
  tsconfig.json --noEmit` — exit 0, no suppressions.
- `tests/test_ocean_rescue_wp31a_typed_profile.py` — 8 passing (static
  contract, strict tsc, behavioral matrix + parity, browser flow).
- `tests/test_ocean_rescue_wp30_esm_entry_module_graph.py` — 19 passing
  (generalized two-category adapter contract, typed reachability, legacy
  exclusion, manifest retention).
- `tests/test_ocean_rescue_wp21_production_bundle_cutover.py` — 19 passing
  (typed membership, determinism, two-block artifact, rollback byte-identity,
  browser parity).
- `tests/test_ocean_rescue_wp20_shadow_bundle.py` — 24 passing.
- `tests/test_ocean_rescue_profile_choice.py` — 14 passing (legacy rollback
  behavior evidence retained).
- `just check-ocean-rescue-dev-server` — 15 passing.
- `just check-ocean-rescue-rollback` — PASS.
- `tests/test_ocean_rescue_artifact_drift.py`, `test_ocean_rescue_source_scaffold.py`,
  `test_ocean_rescue_wp03_scope_decision.py` — PASS.

## Unrelated baseline failures (unchanged by WP-31A)

- `test_ocean_rescue_pixi_backend_smoke_contract::test_lock_pinned_pixi`
  (stale package-lock versus pnpm authority).
- `test_git_workflow_guardrails::test_justfile_typecheck_has_resilient_fallback_and_exclusions`
  (root typecheck gate contract).

## Exclusions retained

- No WP-31B work; no missions/gups/launch/state/travel/renderer conversion; no
  app.js conversion; no shared boundary type package; no profile redesign; no
  new animal choice; no player-name/storage-key/schema-version change; no
  migration of existing stored payload; no persistence-failure semantic change;
  no gameplay/visual/asset change; no Pixi package import; no vendored Pixi
  removal; no dependency upgrade; no new dependency; no checkJs repo-wide
  enablement; no source maps; no code splitting; no runtime network dependency;
  no WP-03A execution; no WP-03B harness; no pull request.
