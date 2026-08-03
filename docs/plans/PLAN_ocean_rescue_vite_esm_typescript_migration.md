# Ocean Rescue Vite / ESM / TypeScript Migration Plan

- **Status:** ACTIVE
- **Architecture SSOT:** `docs/specs/technical/AIDENGAME_OCEAN_RESCUE_DEVELOPMENT_ARCHITECTURE.md`
- **Created:** 2026-08-03
- **Updated:** 2026-08-03
- **Scope:** Ocean Rescue development-source migration from global-namespace JavaScript to ESM/TypeScript/Vite
- **Execution model:** sequential bounded work packages
- **Current phase:** PHASE_0_READY
- **Pre-phase SSOT closure:** COMPLETE
- **Phase 0 evidence root:** `docs/evidence/ocean-rescue/migration/phase-0/`

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

### Work-package map

| Phase | Work package(s) |
|---|---|
| Phase 0 | WP-01, WP-02, WP-03 |
| Phase 1 | WP-10 |
| Phase 2 | WP-11 |
| Phase 3 | WP-20 |
| Phase 4 | WP-21 |
| Phase 5 | WP-30 |
| Phase 6 | WP-31A, WP-31B, WP-31C |
| Phase 7 | WP-32 |
| Phase 8 | WP-33A through WP-33H |
| Phase 9 | WP-40 |
| Phase 10 | WP-41A, WP-41B, WP-41C |
| Phase 11 | WP-50 |
| Phase 12 | WP-51 |
| Phase 13 | WP-52 grouped cleanup packages |
| Phase 14 | WP-53 |

---

## 2. Phase 0 — Baseline and parity evidence

- **Status:** NOT_STARTED
- **Objective:** Capture the current production and runtime baseline before toolchain or source changes.
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

### WP-03 — Target-device performance baseline

Included requirements:

- Galaxy Tab S10-class landscape device;
- DPR upper-bound confirmation;
- touch/pointer interaction;
- frame timing and sustained-run stability;
- renderer backend observation;
- performance evidence appropriate for later cutover comparison.

Dependency rule:

- Phase 1 may begin after WP-01 and WP-02 pass.
- WP-03 must pass before Phase 4 production cutover.
- Phase 0 remains partially open until WP-03 passes.

---

## 3. Phase 1 — Package and Node tooling boundary

- **Status:** NOT_STARTED
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

---

## 4. Phase 2 — Development-server compatibility lane

- **Status:** NOT_STARTED
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

---

## 5. Phase 3 — Shadow production bundle

- **Status:** NOT_STARTED
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

---

## 6. Phase 4 — Production application-bundle cutover

- **Status:** NOT_STARTED
- **Work package:** WP-21
- **Objective:** Switch standalone production packaging from ordered application scripts to the Vite application bundle through a temporary compatibility packaging boundary.
- **Included requirements:**
  - standalone builder consumes the Vite application bundle;
  - one explicit production ownership switch;
  - temporary compatibility path retained for rollback;
  - browser functional parity;
  - artifact drift contract updated to the new path;
  - source-map and external-asset behavior explicitly controlled.
- **Depends on:** WP-20 and WP-03
- **Authoritative path before:** ordered application scripts
- **Authoritative path after:** Vite application bundle through temporary standalone packaging
- **Expected change scope:** standalone builder or packaging adapter, manifest, Vite config, focused tests
- **Explicit exclusions:** global namespace removal, TypeScript module conversion, Pixi package import, legacy cleanup
- **Verification bundle:**
  - legacy output versus new output: functional/runtime equivalence;
  - packaging differences reviewed and documented;
  - new build A versus new build B: byte-identical deterministic output;
  - browser representative flow;
  - renderer backend, pause/resume, pointer, network, drift evidence.
- **Stop conditions:** new production ownership works and rollback to legacy ordering is verified
- **Rollback boundary:** restore legacy manifest ordering and previous builder input

---

## 7. Phase 5 — Canonical ESM entry and module graph

- **Status:** NOT_STARTED
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

---

## 8. Phase 6 — Typed leaf and domain modules

- **Status:** NOT_STARTED
- **Objective:** Convert bounded modules to TypeScript without decomposing application orchestration.
- **Depends on:** WP-30
- **Authoritative path before:** JavaScript domain modules
- **Authoritative path after:** migrated TypeScript modules
- **Explicit exclusions:** simultaneous conversion of unrelated mission controllers; renderer conversion

### WP-31A — Profile vertical slice

- profile model;
- persistence schema and validation;
- direct callers;
- backward-compatible storage behavior;
- focused tests.

### WP-31B — Static catalog group

- mission catalog;
- GUP catalog;
- launch/content data that is demonstrably static;
- direct callers and focused tests.

### WP-31C — Core state and tightly coupled travel contracts

- state machine;
- phase identifiers;
- state snapshots;
- only the travel/domain contracts that share the same rollback boundary;
- focused transition tests.

Verification bundle for each package:

- TypeScript diagnostics;
- focused domain tests;
- application and browser parity;
- deterministic production build.

Rollback boundary: revert the affected module group to its previous source form.

---

## 9. Phase 7 — Shared boundary types

- **Status:** NOT_STARTED
- **Work package:** WP-32
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

---

## 10. Phase 8 — Application orchestration decomposition

- **Status:** NOT_STARTED
- **Objective:** Replace monolithic orchestration with bounded controller ownership.
- **Depends on:** WP-32
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
  - legacy application-global graph removed;
  - current documentation aligned.
- **Expected change scope:** final verification evidence, plan/spec/current-state documentation
- **Explicit exclusions:** new features and unrelated improvements
- **Verification bundle:** full repository suite, TypeScript, Vite build, standalone determinism, browser walkthrough, target-device comparison, documentation assertions
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
- Do not upgrade or downgrade PixiJS solely because official pages disagree; reconcile package metadata in WP-40.
- Split a package when context stability or rollback boundaries require it.
- Do not force independent defects into current scope.
- Update scope and verification before including a strongly coupled defect.
- Keep all implementation phases `NOT_STARTED` until their corresponding work package actually begins.
