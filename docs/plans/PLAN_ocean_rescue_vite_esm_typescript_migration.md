# Ocean Rescue Vite / ESM / TypeScript Migration Plan

- **Status:** ACTIVE
- **Architecture SSOT:** `docs/specs/technical/AIDENGAME_OCEAN_RESCUE_DEVELOPMENT_ARCHITECTURE.md`
- **Created:** 2026-08-03
- **Updated:** 2026-08-04
- **Scope:** Ocean Rescue development-source migration from global-namespace JavaScript to ESM/TypeScript/Vite
- **Execution model:** sequential bounded work packages
- **Current phase:** PHASE_8_IN_PROGRESS
- **Next executable work package:** WP-33C
- **Production cutover gate:** SATISFIED by WP-02 functional parity, WP-20 deterministic shadow-bundle parity, WP-21 production application-bundle cutover, and WP-30 canonical ESM entry
- **Target-device release gate:** WP-03A must pass before MVP release, but it does not block WP-21
- **Automated performance harness:** WP-03B is non-blocking follow-up work, triggered by an observed regression or post-MVP stabilization need
- **Pre-phase SSOT closure:** COMPLETE
- **Phase 0 evidence root:** `docs/evidence/ocean-rescue/migration/phase-0/`
- **Phase 1 evidence root:** `docs/evidence/ocean-rescue/migration/phase-1/`
- **Phase 2 evidence root:** `docs/evidence/ocean-rescue/migration/phase-2/`
- **Phase 3 evidence root:** `docs/evidence/ocean-rescue/migration/phase-3/`
- **Phase 4 evidence root:** `docs/evidence/ocean-rescue/migration/phase-4/`

---

## 1. Plan operating rules

- This plan is not an implementation command.
- Each phase is executed by one or more bounded work packages.
- Strongly coupled source, callers, types, tests, and configuration may be grouped.
- Artificial reduction to a single hypothesis, failure domain, or binary criterion is not required.
- Every work package defines objective, included scope, excluded scope, verification bundle, stop conditions, and rollback boundary.
- Work is split when local-model context becomes unstable or rollback boundaries differ.
- Previous results are verified before selecting the next package.
- Implementation status and documentation status are kept synchronized.
- Independent defects are recorded as remaining work.
- Strongly coupled defects may be added only after scope and verification are updated.
- Product cutover and obsolete-path cleanup may be separate packages.
- Generated artifacts are never repaired by direct editing.
- A physical target-device smoke check is mandatory before MVP release, but unavailable hardware does not block a rollback-safe packaging cutover.
- Numeric performance thresholds become release gates only after they are measured, reviewed, and adopted as product contracts.

### Work-package map

| Track | Work package(s) |
|---|---|
| Phase 0 | WP-01, WP-02 |
| Release readiness | WP-03A target-device smoke |
| Conditional performance follow-up | WP-03B reproducible performance harness |
| Phase 1 | WP-10 |
| Phase 2 | WP-11 |
| Phase 3 | WP-20 |
| Phase 4 | WP-21 |
| Phase 5 | WP-30 |
| Phase 6 | WP-31A, WP-31B, WP-31C |
| Phase 7 | WP-32A, WP-32B |
| Phase 8 | WP-33A through WP-33H |
| Phase 9 | WP-40 |
| Phase 10 | WP-41A, WP-41B, WP-41C |
| Phase 11 | WP-50 |
| Phase 12 | WP-51 |
| Phase 13 | WP-52 grouped cleanup packages |
| Phase 14 | WP-53 |

---

## 2. Phase 0 — Baseline and parity evidence

- **Status:** COMPLETE (WP-01 PASS, WP-02 PASS)
- **Objective:** Capture the current production artifact and representative browser behavior before toolchain or source changes.
- **Depends on:** Pre-phase SSOT closure
- **Authoritative path before:** ordered manifest scripts and Python standalone builder
- **Authoritative path after:** unchanged
- **Expected change scope:** evidence files and plan status only
- **Explicit exclusions:** Vite install, package creation, source changes, production cutover
- **Rollback boundary:** evidence/status changes only

### WP-01 — Static build baseline

Included requirements:

- manifest graph and namespace inventory;
- tracked standalone HTML SHA-256;
- generated registry and vendored Pixi hashes;
- existing atlas/render-package/drift verification;
- two-run render-package byte determinism;
- HEAD artifact versus rebuilt artifact drift check;
- static self-contained packaging and forbidden-network contract evidence.

Verification bundle:

```bash
just check-ocean-rescue-atlases
just check-ocean-rescue-render-package
just check-ocean-rescue-drift
just build-ocean-rescue-render-package
just build-ocean-rescue-render-package
```

Stop conditions:

- static evidence stored under the Phase 0 evidence root;
- two new builds are byte-identical;
- rebuilt tracked outputs match HEAD;
- product paths remain unmodified after verification.

### WP-02 — Browser functional parity baseline

- **Status:** COMPLETE
- **Evidence:** `docs/evidence/ocean-rescue/migration/phase-0/browser-functional-baseline.md`
- **Structured evidence:** `docs/evidence/ocean-rescue/migration/phase-0/browser-functional-evidence.json`

Included requirements:

- browser startup smoke;
- renderer backend recording;
- launch → travel → sea-turtle rescue → completion;
- pause/resume;
- pointer mapping in logical 1280×720 coordinates;
- runtime console error evidence;
- runtime network request evidence;
- deterministic state or screenshot evidence where supported.

Stop conditions:

- representative browser flow passes;
- no unexpected console errors;
- no external runtime requests;
- evidence is reproducible by an existing or focused harness.

Closure: PASS. The focused pytest harness collects one test and verifies the
full representative sea-turtle mission flow, pause/resume countdown, pointer
mapping, actual drag state changes, runtime errors, and network requests.

### WP-03A — Target-device release smoke

- **Status:** NOT_STARTED — waiting for an authorized physical Android tablet
- **Role:** MVP release gate; not a WP-21 production-packaging cutover prerequisite
- **Target:** Galaxy Tab S10-class landscape device or an explicitly accepted equivalent

Included requirements:

- tracked production artifact opens on the physical device in landscape;
- WebGL or WebGL2 is selected;
- effective renderer DPR is numeric and no greater than 2;
- the representative sea-turtle mission can be entered and completed;
- actual touch interaction performs the rope drag;
- pause and resume work without leaving the scene frozen or advancing while paused;
- no page crash, WebGL context loss, external runtime dependency, or visibly sustained freeze occurs;
- one short diagnostic capture may be retained when practical, but a bespoke automated harness is not required.

Stop conditions:

- a short, reproducible checklist records the device model, Android/browser versions, artifact SHA-256, renderer backend, DPR, touch result, pause/resume result, and overall verdict;
- WP-03A must pass before the MVP is declared release-ready;
- an unavailable device leaves the release gate pending but does not block WP-21 or subsequent rollback-safe migration work.

No canonical numeric frame-time or FPS SLA is defined at this stage. The previous
proposal for two automated 120-second runs and fixed percentile thresholds is
withdrawn as a cutover gate because those numbers were not derived from an
accepted Ocean Rescue product baseline.

### WP-03B — Reproducible target-device performance harness

- **Status:** BACKLOG_NON_BLOCKING
- **Trigger:** an observed device-performance regression, repeated manual-testing burden, or post-MVP stabilization decision
- **Role:** longitudinal regression measurement; not an MVP packaging-cutover prerequisite

Possible scope when triggered:

- automated physical-browser connection and provenance;
- repeatable touch injection;
- sustained frame-timing capture;
- percentile and long-stall analysis;
- structured evidence suitable for before/after comparisons;
- thresholds adopted only after baseline review.

Dependency rule:

- WP-01: COMPLETE.
- WP-02: COMPLETE.
- Phase 0: COMPLETE.
- Phase 1 entry condition: SATISFIED.
- WP-03A: pending release-readiness work.
- WP-03B: non-blocking backlog.
- WP-21 may begin after WP-20 because functional parity, deterministic shadow bundling, and rollback boundaries are already established.
- MVP release remains blocked until WP-03A passes.

---

## 3. Phase 1 — Package and Node tooling boundary

- **Status:** COMPLETE
- **Work package:** WP-10
- **Objective:** Establish the pnpm, Node, Vite, and TypeScript build-time boundary without changing application source.
- **Included requirements:**
  - package-boundary placement decision;
  - `package.json`;
  - `pnpm-lock.yaml`;
  - pnpm version pin;
  - active Node LTS pin;
  - supported Vite 8.1.x exact pin;
  - supported TypeScript exact pin;
  - repository `just` commands for package install and type checking;
  - license and lock integrity evidence;
  - documentation update.
- **Depends on:** WP-01 and WP-02
- **Authoritative path before:** legacy build pipeline
- **Authoritative path after:** unchanged; package boundary is additive
- **Expected change scope:** package/version files, lockfile, Justfile, focused docs/tests if needed
- **Explicit exclusions:** source ESM conversion, production cutover, Pixi package import
- **Verification bundle:** frozen install, tool versions, existing repository checks, unchanged Ocean Rescue artifact
- **Stop conditions:** reproducible package boundary exists and legacy production output is unchanged
- **Rollback boundary:** remove package/version files and related command additions

Closure: PASS.

Historical status at Phase 1 completion; superseded for current scheduling:

```text
Phase 1: COMPLETE
WP-10: COMPLETE
Current phase: PHASE_2_READY_WITH_WP03_PENDING
Next executable work package: WP-11
Package state: PACKAGE_BOUNDARY_READY
```

Historical status carried at that time; superseded by the WP-03 scope decision:

```text
WP-01: COMPLETE
WP-02: COMPLETE
WP-03: NOT_STARTED
Phase 0: PARTIAL_COMPLETE
WP-03 required before WP-21
```

---

## 4. Phase 2 — Development-server compatibility lane

- **Status:** COMPLETE
- **Work package:** WP-11
- **Objective:** Run the existing global-namespace source through Vite development serving without changing the production pipeline.
- **Included requirements:**
  - development-only HTML entry;
  - minimal Vite development configuration;
  - reuse or deterministic derivation of current script order;
  - bounded compatibility bootstrap only where required;
  - `just` development command;
  - browser parity for representative flow;
  - no mutation of tracked production artifacts.
- **Depends on:** WP-10
- **Authoritative path before:** ordered manifest scripts
- **Authoritative path after:** unchanged for production; Vite is development-only
- **Expected change scope:** dev entry, Vite configuration, command integration, focused harness/tests
- **Explicit exclusions:** production bundle, ESM conversion, TypeScript source conversion, manifest removal
- **Verification bundle:** Vite startup, browser flow, pause/resume, console, network, legacy artifact drift
- **Stop conditions:** current game is usable through the dev server and the production path is unchanged
- **Rollback boundary:** remove dev entry/configuration/command

Closure: PASS.

Historical status at Phase 2 completion; superseded for current scheduling:

```text
Phase 2: COMPLETE
WP-11: COMPLETE
Current phase: PHASE_3_READY_WITH_WP03_PENDING
Next executable work package: WP-20
Dev-server state: DEV_SERVER_COMPAT
```

Evidence: `docs/evidence/ocean-rescue/migration/phase-2/development-server-compatibility.md`

---

## 5. Phase 3 — Shadow production bundle

- **Status:** COMPLETE
- **Work package:** WP-20
- **Objective:** Produce a deterministic Vite application bundle beside the legacy production path.
- **Included requirements:**
  - Vite production-bundle configuration;
  - preservation of current global initialization semantics;
  - expected namespace-presence evidence;
  - shadow startup parity;
  - bundle-content and size inspection;
  - two-run byte determinism.
- **Depends on:** WP-11
- **Authoritative path before:** legacy ordered scripts
- **Authoritative path after:** legacy remains authoritative; bundle is shadow-only
- **Expected change scope:** Vite configuration, untracked/ignored shadow output, focused tests
- **Explicit exclusions:** production ownership switch, manifest contraction, legacy builder modification
- **Verification bundle:** shadow build, namespace/startup parity, deterministic output, unchanged legacy artifact
- **Stop conditions:** shadow bundle parity is proven without touching production authority
- **Rollback boundary:** remove shadow build configuration

Closure: PASS.

Historical WP-20 closure snapshot; retained as provenance and superseded for current scheduling:

```text
Phase 3: COMPLETE
WP-20: COMPLETE
Current phase: PHASE_4_READY_WITH_WP03_PENDING
Next executable work package: WP-03
Shadow bundle state: SHADOW_BUNDLE
WP-21 remains blocked until WP-03 completes
WP-21 is the next production-cutover package only after WP-03 passes
```

Historical status carried at WP-20 completion; superseded by the WP-03 scope decision:

```text
WP-01: COMPLETE
WP-02: COMPLETE
WP-03: NOT_STARTED
Phase 0: PARTIAL_COMPLETE
WP-03 required before WP-21
```

Current scheduling authority:

```text
Phase 0: COMPLETE
Phase 3: COMPLETE
Phase 4: COMPLETE
Phase 5: COMPLETE
Phase 6: COMPLETE
Phase 7: COMPLETE
WP-20: COMPLETE
WP-21: COMPLETE
WP-30: COMPLETE
WP-31A: COMPLETE
WP-31B: COMPLETE
WP-31C: COMPLETE
WP-32A: COMPLETE
WP-32B: COMPLETE
WP-33A: COMPLETE
WP-33B: COMPLETE
Current phase: PHASE_8_IN_PROGRESS
Next executable work package: WP-33C
Production bundle state: PRODUCTION_APP_BUNDLE
ESM entry state: CANONICAL_MAIN_JS
Manifest state: CONTRACTED_CANONICAL_PLUS_LEGACY_ROLLBACK
Profile module state: TYPED_CANONICAL
Mission catalog state: TYPED_CANONICAL
GUP catalog state: TYPED_CANONICAL
Launch module state: TYPED_CANONICAL
State module state: TYPED_CANONICAL
Travel module state: TYPED_CANONICAL
Legacy profile.js: ROLLBACK_ONLY
Legacy missions.js: CONTROLLER_CANONICAL_PLUS_ROLLBACK
Legacy gups.js: CONTROLLER_CANONICAL_PLUS_ROLLBACK
Legacy launch.js: ROLLBACK_ONLY
Legacy state.js: ROLLBACK_ONLY
Legacy travel.js: ROLLBACK_ONLY
Shared mission ID state: TYPE_AUTHORITY
Global OceanRescue ABI state: TYPED_SHARED
Typed module ESM adapter state: CHECKED_JS
Pointer coordinate boundary state: CHECKED_RUNTIME
Scene pointer intent state: NORMALIZED_SHARED
Render coordinate adapter state: TYPED_MINIMAL
Runtime output state: DETERMINISTIC
WP-03A target-device smoke: REQUIRED_BEFORE_MVP_RELEASE
WP-03B automated performance harness: BACKLOG_NON_BLOCKING
```

Evidence: `docs/evidence/ocean-rescue/migration/phase-3/shadow-production-bundle.md`

---

## 6. Phase 4 — Production application-bundle cutover

- **Status:** COMPLETE (WP-21 PASS)
- **Work package:** WP-21
- **Objective:** Switch standalone production packaging from ordered application scripts to the Vite application bundle through a temporary compatibility packaging boundary.
- **Included requirements:**
  - standalone builder consumes the Vite application bundle;
  - one explicit production ownership switch;
  - temporary compatibility path retained for rollback;
  - browser functional parity;
  - artifact drift contract updated to the new path;
  - source-map and external-asset behavior explicitly controlled.
- **Depends on:** WP-20 and WP-02
- **Release constraint:** WP-03A remains mandatory before MVP release, but does not block this rollback-safe packaging cutover
- **Authoritative path before:** ordered application scripts
- **Authoritative path after:** Vite application bundle through temporary standalone packaging
- **Expected change scope:** standalone builder or packaging adapter, manifest, Vite config, focused tests
- **Explicit exclusions:** global namespace removal, TypeScript module conversion, Pixi package import, legacy cleanup, WP-03B performance-harness implementation
- **Verification bundle:**
  - legacy output versus new output: functional/runtime equivalence;
  - packaging differences reviewed and documented;
  - new build A versus new build B: byte-identical deterministic output;
  - browser representative flow;
  - renderer backend, pause/resume, pointer, network, drift evidence;
  - explicit rollback verification to the legacy ordered-script path.
- **Stop conditions:** new production ownership works and rollback to legacy ordering is verified
- **Rollback boundary:** restore legacy manifest ordering and previous builder input

Closure: PASS. The standalone builder now consumes a single deterministic Vite
IIFE application bundle (vendored Pixi stays external) produced by a dedicated
production Vite config. Production ownership has one explicit switch
(`--mode production`); the `--mode legacy` path reproduces the ordered-script
artifact for rollback. Determinism, drift, artifact shape, static contract,
browser functional parity, forbidden-network, and legacy rollback are verified
by `tests/test_ocean_rescue_wp21_production_bundle_cutover.py` together with
the reconciled drift/render-packaging/shadow-bundle/scaffold suites.

Operational rollback closure: the tracked canonical deployment artifact
`ocean-rescue/index.html` transitions bundle -> legacy -> bundle. `just
rollback-ocean-rescue-to-legacy` atomically rewrites that canonical file to the
current-source legacy ordered-script artifact, verified byte-identical to a
clean current-source legacy build (the immutable pre-WP-21 baseline
`cfd991d8...` is historical evidence, not a live artifact gate), and `just
build-ocean-rescue` restores the bundle-owned artifact. `just
build-ocean-rescue-legacy-proof` writes only a proof artifact to
`dist/legacy-rollback.html`; it does not touch the canonical artifact.

Evidence: `docs/evidence/ocean-rescue/migration/phase-4/production-app-bundle-cutover.md`

---

## 7. Phase 5 — Canonical ESM entry and module graph

- **Status:** COMPLETE (WP-30 PASS)
- **Work package:** WP-30
- **Objective:** Establish one canonical ESM application entry and make imports authoritative for application dependencies.
- **Included requirements:** canonical entry, explicit imports, temporary compatibility adapters, application-manifest contraction, focused module-graph validation
- **Depends on:** WP-21
- **Authoritative path before:** manifest `depends_on` graph plus globals
- **Authoritative path after:** ESM import graph
- **Expected change scope:** entry module, import/bootstrap adapters, Vite config, manifest/tests
- **Explicit exclusions:** all-module TypeScript conversion, controller decomposition, Pixi package conversion
- **Verification bundle:** import resolution, cycle evidence, production build, browser parity, deterministic packaging
- **Stop conditions:** import graph owns application dependency order
- **Rollback boundary:** restore legacy bootstrap and manifest graph

Closure: PASS. `src/main.js` is the single canonical entry importing `./esm/app.js`;
`src/esm/*` compatibility adapters import their direct dependencies explicitly,
side-effect-load exactly one legacy implementation each, and export the
`window.OceanRescue.*` namespace. The ordered application list was removed from
`build-manifest.json` (now contracted to template/styles/vendor/generated/entry/
assets) and preserved as `build-manifest.legacy.json` for rollback. Production
and dev lanes both start from `src/main.js`; the dev server serves one classic
vendored Pixi script plus one module `main.js`. The module-graph validator
(`tests/test_ocean_rescue_wp30_esm_entry_module_graph.py`) proves single-root,
acyclic, exactly-once legacy coverage, and static relative imports only.

Evidence: `docs/evidence/ocean-rescue/migration/phase-5/canonical-esm-entry-module-graph.md`

---

## 8. Phase 6 — Typed leaf and domain modules

- **Status:** COMPLETE (WP-31C PASS)
- **Objective:** Convert bounded modules to TypeScript without decomposing application orchestration.
- **Depends on:** WP-30
- **Authoritative path before:** JavaScript domain modules
- **Authoritative path after:** migrated TypeScript modules
- **Explicit exclusions:** simultaneous conversion of unrelated mission controllers; renderer conversion

### WP-31A — Profile vertical slice

- **Status:** COMPLETE (WP-31A PASS)
- **Objective:** Migrate the profile model, persistence schema, storage validation, and exported API to a strictly typed TypeScript module while retaining the legacy `src/profile.js` unchanged as the rollback authority.
- **Typed module:** `domains/ocean-rescue/src/profile/profile.ts`
- **Compatibility adapter:** `domains/ocean-rescue/src/esm/profile.js` imports and re-exports the typed module, validates the temporary `window.OceanRescue.Profile` global ABI, and no longer side-effect-imports `../profile.js`.
- **Ownership after:**
  - canonical ESM production/dev graph: `src/main.js → src/esm/app.js → src/esm/profile.js → src/profile/profile.ts`
  - legacy rollback graph: `build-manifest.legacy.json → src/profile.js`
- **Verified:** strict `tsc --noEmit`; typed behavioral matrix; legacy-versus-typed parity; WP-30 module graph; production module membership (typed module in, rollback `profile.js` out); deterministic production build; profile browser flow (first visit, selection, stored payload, reload hydration, invalid-payload cleanup); operational legacy rollback byte-identical to baseline.

Closure status after WP-31A; superseded for current scheduling:

```text
Phase 5: COMPLETE
Phase 6: IN_PROGRESS
WP-31A: COMPLETE
Profile module state: TYPED_CANONICAL
Legacy profile.js: ROLLBACK_ONLY
Next executable work package: WP-31B
```

Evidence: `docs/evidence/ocean-rescue/migration/phase-6/typed-profile-vertical-slice.md`

### WP-31B — Static catalog group

- **Status:** COMPLETE (WP-31B PASS)
- **Objective:** Migrate the mission catalog, GUP catalog, and the demonstrably
  static launch content to strictly typed canonical TypeScript modules while
  preserving all runtime values, ordering, immutability, mutable controller
  behavior, browser behavior, deterministic packaging, and the byte-identical
  legacy rollback sources.
- **Typed modules:**
  - `domains/ocean-rescue/src/missions/catalog.ts` (typed canonical mission
    catalog);
  - `domains/ocean-rescue/src/gups/catalog.ts` (typed canonical GUP catalog);
  - `domains/ocean-rescue/src/launch/launch.ts` (complete typed launch API:
    frozen launch catalog, `DurationMs`, `GoalDurationMs`, typed
    `getMissionContent()`, frozen `Launch` API, temporary global ABI).
- **Compatibility adapters:**
  - `src/esm/missions.js` side-effect imports the unchanged legacy controller
    `../missions.js`, validates the legacy API and catalog parity, and builds
    one frozen facade whose `Catalog` is the typed catalog and whose methods
    are the unchanged controller method references; the facade replaces the
    temporary `window.OceanRescue.Missions` ABI and is exported with the typed
    catalog.
  - `src/esm/gups.js` applies the same bounded pattern for GUP.
  - `src/esm/launch.js` imports and re-exports the typed launch module and no
    longer side-effect-imports `../launch.js`.
- **Ownership after:**
  - canonical ESM production/dev graph:
    `src/main.js → src/esm/app.js → src/esm/{missions,gups,launch}.js`; the
    mission/GUP adapters reach both their typed catalog and their unchanged
    legacy controller; the launch adapter reaches the typed launch module only;
  - legacy rollback graph: `build-manifest.legacy.json → missions.js, gups.js,
    launch.js` (all unchanged); `launch.js` is rollback-only.
- **Verified:** strict `tsc --noEmit`; typed static-catalog behavioral matrix;
  legacy-versus-typed parity for mission and GUP controllers; launch content and
  lookup parity; runtime identity and immutability on the real
  compiled/transformed modules; WP-30 module graph (typed modules in, rollback
  `launch.js`/`profile.js` out, controllers retained); production/shadow module
  membership; deterministic production bundle + standalone HTML; tracked-artifact
  match; browser static-catalog flow (mission cards, GUP cards, launch
  briefing/goal/timing) with clean page/console/network quality; operational
  legacy rollback byte-identical to the pre-WP-31B baseline; legacy sources
  byte-identical.

Closure status after WP-31B; superseded for current scheduling:

```text
Phase 5: COMPLETE
Phase 6: IN_PROGRESS
WP-31A: COMPLETE
WP-31B: COMPLETE
Mission catalog state: TYPED_CANONICAL
GUP catalog state: TYPED_CANONICAL
Launch module state: TYPED_CANONICAL
Legacy missions.js: CONTROLLER_CANONICAL_PLUS_ROLLBACK
Legacy gups.js: CONTROLLER_CANONICAL_PLUS_ROLLBACK
Legacy launch.js: ROLLBACK_ONLY
Next executable work package: WP-31C
```

Evidence: `docs/evidence/ocean-rescue/migration/phase-6/typed-static-catalog-group.md`

### WP-31C — Core state and tightly coupled travel contracts

- **Status:** COMPLETE (WP-31C PASS)
- **Objective:** Migrate the core state machine and the tightly coupled travel
  runtime state to strictly typed canonical TypeScript modules while preserving
  every observable runtime contract and the byte-identical legacy rollback
  sources.
- **Typed modules:**
  - `domains/ocean-rescue/src/state/state.ts` (typed canonical core state
    machine: `Phase`, `PhaseMap`, `TransitionMap`, `TransitionToken`,
    `StateSnapshot`, `StateApi`; frozen `Phases`, frozen transition allow-list,
    transition locking, monotonic transition IDs, frozen tokens, snapshots,
    `forcePhase` cleanup, temporary `window.OceanRescue.State` ABI);
  - `domains/ocean-rescue/src/travel/travel.ts` (typed canonical travel runtime
    contract: `TravelBounds`, `TravelSnapshot`, `TravelApi`; frozen `Bounds`,
    `AutoForwardSpeed === 120`, `TapSpeed === 360`, 50ms delta cap, forward
    multiplier 0..1 with exact rejection, tap-target movement and clear timing,
    drag pointer ownership, clamp ordering, exact invalid-input return values,
    temporary `window.OceanRescue.Travel` ABI).
- **Compatibility adapters:**
  - `src/esm/state.js` imports and re-exports the typed state module and no
    longer side-effect-imports `../state.js`;
  - `src/esm/travel.js` imports and re-exports the typed travel module and no
    longer side-effect-imports `../travel.js`.
- **Ownership after:**
  - canonical ESM production/dev graph:
    `src/main.js → src/esm/app.js → src/esm/{state,travel}.js →
    src/state/state.ts / src/travel/travel.ts`;
  - legacy rollback graph: `build-manifest.legacy.json → state.js, travel.js`
    (both unchanged); both are rollback-only.
- **Verified:** strict `tsc --noEmit`; typed behavioral matrix (27 State
  scenarios, 35 Travel scenarios) with legacy-versus-typed parity in strict
  mode; runtime identity and immutability on the real compiled/transformed
  modules; WP-30 module graph (typed state/travel in, rollback
  state.js/travel.js out, existing typed modules/controllers retained);
  production/shadow module membership; deterministic production bundle +
  standalone HTML; tracked-artifact match; browser state/travel flow
  (deterministic profile -> mission -> GUP -> launch -> TRAVEL -> distance
  progress -> tap and drag Y reflection -> RESCUE_SITE_TRANSITION) with clean
  page/console/network quality and no leftover transition lock; operational
  legacy rollback byte-identical to the pre-WP-31C baseline; legacy sources
  byte-identical.

Closure status after WP-31C; superseded for current scheduling:

```text
Phase 6: COMPLETE
WP-31A: COMPLETE
WP-31B: COMPLETE
WP-31C: COMPLETE
State module state: TYPED_CANONICAL
Travel module state: TYPED_CANONICAL
Legacy state.js: ROLLBACK_ONLY
Legacy travel.js: ROLLBACK_ONLY
Next executable work package: WP-32
```

Evidence: `docs/evidence/ocean-rescue/migration/phase-6/typed-core-state-travel-contracts.md`

---

## 9. Phase 7 — Shared boundary types

- **Status:** COMPLETE
- **Work packages:** WP-32A (COMPLETE), WP-32B (COMPLETE)
- **Objective:** Type actual cross-module contracts after enough concrete modules exist.
- **Included requirements:** gameplay snapshots, phase IDs, normalized pointer intents, renderer-adapter contracts, persistence schemas where shared
- **Depends on:** WP-31A, WP-31B, WP-31C as applicable
- **Authoritative path before:** implicit JavaScript contracts
- **Authoritative path after:** explicit TypeScript boundary types
- **Expected change scope:** type modules and direct signatures/callers
- **Explicit exclusions:** speculative framework types, excessive generics, renderer-owned gameplay model
- **Verification bundle:** TypeScript diagnostics, focused tests, no runtime behavior change
- **Stop conditions:** current cross-module boundaries are typed without speculative abstraction
- **Rollback boundary:** remove shared types and revert affected signatures

### WP-32A — Shared typed runtime ABI

- **Status:** COMPLETE (WP-32A PASS)
- **Objective:** Establish one minimal shared type boundary between the typed
  canonical modules and the ESM compatibility adapters without changing any
  runtime statement: the mission identifier authority, the runtime ABI type
  module, the single global `window.OceanRescue` declaration, and checked-JS
  ESM adapters.
- **Shared type modules:**
  - `domains/ocean-rescue/src/contracts/mission.ts` (shared `MissionId`:
    `"sea-turtle" | "crab" | "young-whale"`);
  - `domains/ocean-rescue/src/contracts/runtime-abi.ts` (composes
    `ProfileApi`, `LaunchApi`, `StateApi`, `TravelApi`, `MissionCatalog`,
    `GupCatalog`, `MissionId`, `GupId` and defines `MissionProgressionSnapshot`,
    `MissionCompletionResult`, `MissionsApi`, `GupSelectionSnapshot`, `GupsApi`,
    `OceanRescueNamespace`);
  - `domains/ocean-rescue/src/contracts/ocean-rescue-global.d.ts` (single
    optional `Window.OceanRescue` declaration).
- **Typed module changes:** `missions/catalog.ts` and `launch/launch.ts` consume
  the shared `MissionId` (compatibility aliases retained); `profile.ts`,
  `launch.ts`, `state.ts`, and `travel.ts` drop their duplicated local
  `OceanRescueGlobalNamespace` interfaces and use the shared namespace type.
- **ESM adapters:** all six `src/esm/*.js` adapters gain `// @ts-check` plus the
  shared global declaration reference and minimal JSDoc type annotations; the
  mission/GUP facades keep the exact legacy controller method references.
- **Verified:** strict `tsc --noEmit`; standalone adapter typecheck with zero
  diagnostics; shared identifier authority used by both catalogs; single global
  declaration with no index signature and no `any`; local namespace interfaces
  removed; production bundle, metadata, standalone HTML, and legacy rollback
  artifact byte-identical to the pre-WP-32A baseline; shared contracts never
  enter the production bundle; WP-31A/B/C, WP-30, WP-21, WP-20, rollback,
  artifact-drift, and WP-03 focused bundles all PASS.
- **Status snapshot:**
  - Shared mission ID: `TYPE_AUTHORITY`
  - Global OceanRescue ABI: `TYPED_SHARED`
  - Typed module ESM adapters: `CHECKED_JS`
  - Runtime output: `BYTE_IDENTICAL`

Evidence: `docs/evidence/ocean-rescue/migration/phase-7/shared-typed-runtime-abi.md`

### WP-32B — Pointer intent and renderer-adapter contracts

- **Status:** COMPLETE (WP-32B PASS)
- **Objective:** Extract the pointer coordinate transformations and scene
  pointer-intent generation that were embedded ad hoc in `src/app.js` into one
  real runtime boundary shared by the canonical ESM lane and the legacy
  ordered-script lane.
- **Pointer coordinate boundary state:** `CHECKED_RUNTIME`
- **Scene pointer intent state:** `NORMALIZED_SHARED`
- **Render coordinate adapter state:** `TYPED_MINIMAL`
- **Shared type module:**
  - `domains/ocean-rescue/src/contracts/pointer-input.ts` (type-only:
    `LogicalPoint`, `RenderMappedPoint`, `RenderCoordinateMapperApi`,
    `ActivePointerIntent`, `InactivePointerIntent`, `PointerIntent`,
    `ClientCoordinateCarrier`, `BoundingRect`, `RectProvider`,
    `PointerInputApi`).
- **Shared checked-JS runtime:**
  - `domains/ocean-rescue/src/pointer-input.js` owns the exact travel stage-Y
    mapping, rescue `{ x, y }` mapping, and the active/inactive
    pointer-intent constructors, registered as the frozen
    `OceanRescue.PointerInput` global; it is executed unchanged by both lanes
    and depends only on the minimal `RenderRuntime` coordinate-mapper subset
    (`isReady()` + `mapClientToLogical`).
- **Canonical adapter and cutover:**
  - `domains/ocean-rescue/src/esm/pointer-input.js` imports the shared
    implementation and fail-closes on the contract;
  - `domains/ocean-rescue/src/esm/render-runtime.js` gains `@ts-check` and an
    existence guard for the coordinate-mapper subset;
  - `domains/ocean-rescue/src/esm/app.js` registers PointerInput after
    RenderRuntime and before the legacy `app.js`;
  - `src/app.js` delegates `mapClientYToStage`/`mapRescueCoordinates` to the
    boundary and replaces every inline scene pointer-intent literal with
    `PointerInput.activeIntent`/`PointerInput.inactiveIntent`;
  - `build-manifest.legacy.json` inserts `pointer-input.js` once after
    `render-runtime.js` and before `app.js` and records the
    `OceanRescue.PointerInput` dependency on `OceanRescue.App`.
- **Owned subset:** WP-32B owns only the coordinate/pointer subset. Full
  RenderRuntime API typing is WP-40; authored scene implementation typing is
  the WP-41 family; app orchestration decomposition is WP-33.
- **Verified:** strict `tsc --noEmit`; standalone checked-JS diagnostics for
  the pointer runtime, pointer adapter, and render adapter; the real
  `pointer-input.js` travel/rescue/intent matrix plus exact behavioral parity
  with the pre-extraction `app.js` formulas; app delegation and orchestration
  markers; canonical graph membership (pointer modules in, type-only contracts
  out); two clean production builds byte-identical; two standalone HTML builds
  byte-identical; tracked artifact matches a clean rebuild; legacy rollback
  with the inserted `pointer-input.js`; operational bundle -> legacy -> bundle
  transition; and focused browser parity for travel tap/drag, pause blocking,
  sea-turtle pointer interaction, and crab pointer interaction.
- **Status snapshot:**
  - Pointer coordinate boundary: `CHECKED_RUNTIME`
  - Scene pointer intent: `NORMALIZED_SHARED`
  - Render coordinate adapter: `TYPED_MINIMAL`
  - Runtime output: `DETERMINISTIC`

Evidence: `docs/evidence/ocean-rescue/migration/phase-7/pointer-coordinate-renderer-boundary.md`

---

## 10. Phase 8 — Application orchestration decomposition

- **Status:** READY (WP-32B complete)
- **Objective:** Replace monolithic orchestration with bounded controller ownership.
- **Depends on:** WP-32A and WP-32B
- **Authoritative path before:** central `app.js` orchestration
- **Authoritative path after:** typed bounded controllers
- **Explicit exclusions:** all controller groups in one package; gameplay or visual redesign

Recommended work packages:

| ID | Controller group |
|---|---|
| WP-33A | Profile and mission-selection flow |
| WP-33B | Launch and travel flow |
| WP-33C | Rescue-site transition and tutorial |
| WP-33D | Pause, timers, and resume countdown |
| WP-33E | Sea-turtle mission lifecycle |
| WP-33F | Crab mission lifecycle |
| WP-33G | Young-whale mission lifecycle |
| WP-33H | Mission-success, replay, continue, and return |

Each package includes direct callers, types, focused tests, and ownership documentation where needed.

Verification bundle:

- TypeScript diagnostics;
- affected phase transitions;
- timer/input ownership;
- pause/resume where relevant;
- browser parity;
- production build determinism.

Rollback boundary: revert the affected controller group to the previous orchestration implementation.

---

## 11. Phase 9 — PixiJS package import and render-runtime migration

- **Status:** NOT_STARTED
- **Work package:** WP-40
- **Objective:** Replace the global vendored Pixi dependency at the render-runtime boundary with a pinned package import and typed ESM runtime.
- **Included requirements:**
  - official/package metadata reconciliation for repository pin 8.19.0;
  - `pixi.js` dependency pin;
  - license evidence;
  - package import;
  - `render-runtime` ESM/TypeScript migration;
  - renderer initialization parity;
  - WebGL priority and Canvas fallback;
  - local bundle inclusion;
  - zero runtime network requests;
  - vendored UMD retained temporarily for rollback.
- **Depends on:** Phase 8 controller packages required by the runtime boundary
- **Authoritative path before:** global `PIXI` vendored UMD
- **Authoritative path after:** package import in typed render runtime
- **Expected change scope:** package files, render runtime, imports/configuration, focused tests
- **Explicit exclusions:** individual scene migration; vendored file deletion; unrelated Pixi upgrade
- **Verification bundle:** package/version evidence, renderer backends, browser scenes, network, deterministic bundle, artifact drift
- **Stop conditions:** package import and typed render runtime are production-authoritative with rollback retained
- **Rollback boundary:** restore global vendored runtime path

Note (recorded by WP-10): the `pixi.js` dependency metadata already exists as
an exact `8.19.0` pin under `domains/ocean-rescue`. WP-40 owns the source
import, the typed render-runtime cutover, the production authority switch, and
the vendored rollback handling. The package-metadata pin added by WP-10 is not
the import/production cutover itself.

---

## 12. Phase 10 — Scene module migration

- **Status:** NOT_STARTED
- **Objective:** Convert Pixi scene modules after package types and typed render runtime exist.
- **Depends on:** WP-40
- **Authoritative path before:** JavaScript scene modules using the compatibility boundary
- **Authoritative path after:** typed ESM scene modules
- **Explicit exclusions:** gameplay-semantic changes, visual redesign, asset-pipeline rewrite

Work packages:

- **WP-41A:** travel scene
- **WP-41B:** sea-turtle scene
- **WP-41C:** crab scene

Each package includes:

- snapshot and adapter typing;
- mount/unmount ownership;
- pointer-intent boundary;
- WebGL and Canvas evidence;
- visual and interaction parity;
- focused tests.

Rollback boundary: restore the affected scene module to its prior implementation.

---

## 13. Phase 11 — Legacy manifest and global contraction

- **Status:** NOT_STARTED
- **Work package:** WP-50
- **Objective:** Remove obsolete application manifest entries, `depends_on` relationships, compatibility namespaces, and legacy-only assertions after zero-reference evidence.
- **Depends on:** WP-41A, WP-41B, WP-41C and any required controller conversions
- **Authoritative path before:** ESM graph plus compatibility remnants
- **Authoritative path after:** ESM graph without application-global authority
- **Expected change scope:** manifest, adapters, builder contract, focused tests
- **Explicit exclusions:** deletion without zero-reference proof; unrelated test cleanup
- **Verification bundle:** zero-reference scan, TypeScript, build, browser parity, artifact drift
- **Stop conditions:** removed entries have no runtime or rollback responsibility
- **Rollback boundary:** restore the removed compatibility group

---

## 14. Phase 12 — Standalone packaging consolidation

- **Status:** NOT_STARTED
- **Work package:** WP-51
- **Objective:** Finalize standalone packaging after production cutover and remove the temporary compatibility packaging introduced in Phase 4.
- **Included requirements:**
  - final Vite-output input contract;
  - temporary packaging-adapter removal;
  - CSS/JS inline policy;
  - source-map policy;
  - external and emitted asset URL rejection;
  - deterministic standalone output;
  - drift and zero-request verification.
- **Depends on:** WP-50
- **Authoritative path before:** temporary Vite-bundle packaging introduced by Phase 4
- **Authoritative path after:** final standalone packaging contract
- **Expected change scope:** standalone builder/successor, Vite output contract, tests, focused docs
- **Explicit exclusions:** standalone-contract removal; multi-file production deployment
- **Verification bundle:** self-contained artifact, new-build byte determinism, browser flow, network, drift
- **Stop conditions:** temporary packaging is gone and the final contract is explicit and reproducible
- **Rollback boundary:** restore the Phase 4 temporary packaging adapter

---

## 15. Phase 13 — Obsolete tooling cleanup

- **Status:** NOT_STARTED
- **Work package family:** WP-52
- **Objective:** Remove obsolete artifacts only after current production and rollback paths no longer use them.
- **Depends on:** WP-51
- **Candidate groups:**
  - vendored Pixi UMD;
  - obsolete builder branches;
  - obsolete manifest schema fields;
  - obsolete compatibility harnesses;
  - stale tests validating only removed structure;
  - stale documentation references.
- **Expected change scope:** one coherent deletion group per package where practical
- **Explicit exclusions:** unrelated cleanup; deletion before zero-reference and rollback-need evidence
- **Verification bundle:** zero references, build, tests, browser flow, artifact drift
- **Stop conditions:** each deleted group has no remaining authority or rollback role
- **Rollback boundary:** restore the specific deletion group from Git history

---

## 16. Phase 14 — Migration closeout

- **Status:** NOT_STARTED
- **Work package:** WP-53
- **Objective:** Verify the complete target state and align documentation/status with reality.
- **Depends on:** Required WP-52 cleanup groups
- **Complete-state checklist:**
  - canonical TypeScript/ESM application source;
  - Vite development server;
  - deterministic Vite application bundle;
  - deterministic standalone HTML;
  - local PixiJS package bundle;
  - gameplay authority preserved;
  - atlas pipeline preserved;
  - representative gameplay parity;
  - pointer and pause/resume parity;
  - WebGL and Canvas evidence;
  - zero runtime external requests;
  - WP-03A physical target-device release smoke completed before MVP release;
  - any adopted performance thresholds are backed by recorded baseline evidence;
  - legacy application-global graph removed;
  - current documentation aligned.
- **Expected change scope:** final verification evidence, plan/spec/current-state documentation
- **Explicit exclusions:** new features and unrelated improvements
- **Verification bundle:** full repository suite, TypeScript, Vite build, standalone determinism, browser walkthrough, target-device smoke/comparison where available, documentation assertions
- **Stop conditions:** every closeout item is evidenced; otherwise reopen the phase that owns the failed contract
- **Rollback boundary:** revert closeout status and documentation only; earlier implementation phases retain their own rollback procedures

---

## 17. Short-circuit and stop rules

- Skip duplicate implementation when a goal is already satisfied and evidenced.
- Verify parity before every production ownership switch.
- Retain the legacy production path if cutover fails.
- Do not work around toolchain installation failure with source hacks.
- Do not replace browser verification with unit-test success.
- Do not resolve artifact drift by editing generated HTML.
- Do not hide performance regression by removing unrelated visuals.
- Do not invent or lower a numeric performance SLA to obtain PASS; establish and review a baseline first.
- Do not treat unavailable physical hardware as a blocker for WP-21 when the cutover remains bounded, reversible, and covered by browser parity.
- Do not declare the MVP release-ready before WP-03A passes on an accepted physical target device.
- Trigger WP-03B only when its regression value justifies the harness cost.
- Do not upgrade or downgrade PixiJS solely because official pages disagree; reconcile package metadata in WP-40.
- Split a package when context stability or rollback boundaries require it.
- Do not force independent defects into current scope.
- Update scope and verification before including a strongly coupled defect.
- Keep all implementation phases `NOT_STARTED` until their corresponding work package actually begins.
