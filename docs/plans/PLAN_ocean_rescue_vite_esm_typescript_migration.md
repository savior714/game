# Ocean Rescue Vite / ESM / TypeScript Migration Plan

- **Status:** ACTIVE
- **Architecture SSOT:** `docs/specs/technical/AIDENGAME_OCEAN_RESCUE_DEVELOPMENT_ARCHITECTURE.md`
- **Created:** 2026-08-03
- **Scope:** Ocean Rescue development source migration from global-namespace JS to ESM/TypeScript/Vite
- **Execution model:** sequential bounded work packages
- **Current phase:** NOT_STARTED

---

## 1. Plan operating rules

- This plan is not an implementation command. Each phase is executed by one or more bounded work packages.
- Strongly coupled source, callers, tests, and configuration may be grouped in one work package.
- Artificial reduction to a single hypothesis or single failure domain is not required.
- Goals, allowed scope, verification bundles, rollback boundaries, and stop conditions are explicit.
- When local model context becomes unstable, phases are split into child work packages.
- Previous results are verified before selecting the next work package.
- Implementation state and documentation state are kept synchronized.
- When the actual repository diverges from this plan, the baseline is updated first.
- Independent defects discovered during execution are recorded as remaining work.
- Strongly coupled defects may be included after scope and verification are explicitly updated.

---

## 2. Phase 0 — Baseline and parity evidence

- **Status:** NOT_STARTED
- **Objective:** Capture immutable evidence of current working state before any changes
- **Included requirements:**
  - Production artifact baseline (byte-level hash of `ocean-rescue/index.html`)
  - Manifest graph (all 19 entries, dependency order, namespace list)
  - Representative gameplay flows (launch → travel → sea-turtle rescue → completion)
  - Browser startup smoke (Chrome headless)
  - Renderer backend detection (WebGL vs Canvas)
  - Zero external request evidence
  - Pause/resume parity evidence
  - Pointer mapping evidence (logical 1280x720)
  - Artifact hash (SHA-256 of tracked HTML)
  - Build determinism (two independent builds produce byte-identical output)
  - Performance baseline (frame timing on target device)
- **Depends on:** nothing
- **Authoritative path before:** `build-manifest.json` ordered scripts → `build_single_html.py`
- **Authoritative path after:** unchanged
- **Expected change scope:** zero product code changes; evidence files only
- **Explicit exclusions:**
  - Vite install
  - Package creation
  - Production source changes
  - Pixi import conversion
- **Verification bundle:**
  - `just build-ocean-rescue`
  - `just check-ocean-rescue-drift`
  - `just check-ocean-rescue-render-package`
  - Chrome headless smoke (existing test)
  - Manual gameplay walkthrough evidence
- **Stop conditions:**
  - All evidence captured and stored
  - Tracked artifact hash recorded
  - Build determinism proven
- **Rollback boundary:** no changes to roll back
- **Suggested work-package split:** single work package

---

## 3. Phase 1 — Package and Node tooling boundary

- **Status:** NOT_STARTED
- **Objective:** Establish pnpm package boundary with Vite and TypeScript dependencies without changing application source
- **Included requirements:**
  - `package.json` with pnpm, Vite, TypeScript as dev dependencies
  - `pnpm-lock.yaml` generated
  - `.nvmrc` or `.node-version` pinning Node.js version
  - Repository command integration (new `just` recipes for dev server, typecheck)
  - Toolchain documentation update
  - No application source changes
- **Depends on:** Phase 0
- **Authoritative path before:** `build-manifest.json` ordered scripts
- **Authoritative path after:** unchanged (package boundary is additive)
- **Expected change scope:** new files only (`package.json`, `pnpm-lock.yaml`, `.nvmrc`, Justfile additions)
- **Explicit exclusions:**
  - Source ESM conversion
  - Production cutover
  - Pixi import conversion
  - Any `src/*.js` modification
- **Verification bundle:**
  - `pnpm install` succeeds
  - `pnpm exec tsc --version` returns expected version
  - `pnpm exec vite --version` returns expected version
  - `just verify` still passes
  - `just build-ocean-rescue` still produces identical artifact
  - No product code changes in `git diff -- domains/ocean-rescue/src`
- **Stop conditions:**
  - Package boundary established
  - All tools accessible
  - Existing build pipeline unaffected
- **Rollback boundary:** remove `package.json`, `pnpm-lock.yaml`, `.nvmrc`, Justfile additions
- **Suggested work-package split:** single work package (all items share same rollback boundary and verification)

---

## 4. Phase 2 — Development-server compatibility lane

- **Status:** NOT_STARTED
- **Objective:** Run existing global-namespace source on Vite dev server without production builder changes
- **Included requirements:**
  - Dev-only HTML entry (`index.dev.html`) that loads existing scripts
  - Dev-only Vite configuration (minimal, no build optimization)
  - Bounded compatibility bootstrap (global namespace bridging if needed)
  - Development command (`just dev-ocean-rescue` or equivalent)
  - Representative flow parity on dev server
- **Depends on:** Phase 1
- **Authoritative path before:** `build-manifest.json` ordered scripts
- **Authoritative path after:** unchanged (dev server is additive)
- **Expected change scope:** new files only (`index.dev.html`, `vite.config.ts` minimal)
- **Explicit exclusions:**
  - Production bundle cutover
  - Legacy manifest removal
  - Application source ESM conversion
  - TypeScript conversion
- **Verification bundle:**
  - Vite dev server starts and serves Ocean Rescue
  - Game loads and runs in browser via dev server
  - Travel flow works
  - Sea-turtle rescue works
  - Pause/resume works
  - No console errors
  - `just build-ocean-rescue` still produces identical artifact
- **Stop conditions:**
  - Dev server serves existing game
  - All representative flows work
  - Production builder unaffected
- **Rollback boundary:** remove `index.dev.html`, `vite.config.ts`, dev command
- **Suggested work-package split:** single work package

---

## 5. Phase 3 — Shadow production bundle

- **Status:** NOT_STARTED
- **Objective:** Build a Vite production bundle from existing source alongside legacy builder
- **Included requirements:**
  - Vite production application bundle configuration
  - Existing script ordering compatibility (global namespaces preserved)
  - Namespace availability verification
  - Startup parity between legacy and shadow bundle
  - Deterministic output
  - Artifact inspection (bundle contents, size)
- **Depends on:** Phase 2
- **Authoritative path before:** `build-manifest.json` ordered scripts (authoritative)
- **Authoritative path after:** `build-manifest.json` remains authoritative; shadow is experimental
- **Expected change scope:** Vite config updates, shadow build output (not tracked)
- **Explicit exclusions:**
  - Production path switch
  - Legacy manifest removal
  - Legacy builder changes
- **Verification bundle:**
  - Shadow bundle builds successfully
  - Shadow bundle contains all expected namespaces
  - Shadow bundle startup matches legacy startup
  - Legacy `just build-ocean-rescue` produces identical artifact
  - No regression in existing tests
- **Stop conditions:**
  - Shadow bundle parity proven
  - Legacy builder unaffected
- **Rollback boundary:** remove Vite production config; legacy builder unchanged
- **Suggested work-package split:** single work package

---

## 6. Phase 4 — Production application bundle cutover

- **Status:** NOT_STARTED
- **Objective:** Switch standalone builder to consume Vite application bundle instead of ordered scripts
- **Included requirements:**
  - Standalone builder ingests Vite bundle output
  - Old ordered application scripts replaced by bundled entry
  - Artifact parity (byte-identical or functionally identical)
  - Browser parity (all flows work)
  - Rollback path documented
- **Depends on:** Phase 3
- **Authoritative path before:** `build-manifest.json` ordered scripts
- **Authoritative path after:** Vite bundle entry
- **Expected change scope:** `build_single_html.py` or Vite build config, `build-manifest.json` updates
- **Explicit exclusions:**
  - Legacy cleanup
  - Global namespace removal
  - Pixi package import conversion
  - TypeScript conversion
- **Verification bundle:**
  - New artifact matches legacy artifact (or proven functional equivalence)
  - All existing tests pass
  - Chrome headless smoke passes
  - Manual gameplay walkthrough
  - Artifact drift test passes
- **Stop conditions:**
  - Production cutover complete
  - Rollback path verified
- **Rollback boundary:** revert builder changes, restore legacy script ordering
- **Suggested work-package split:** single work package (high risk, single verification)

---

## 7. Phase 5 — Canonical ESM entry and module graph

- **Status:** NOT_STARTED
- **Objective:** Introduce canonical `main.ts` entry with explicit imports, replacing global namespace resolution
- **Included requirements:**
  - Canonical `main.ts` entry
  - Explicit `import` statements for all module dependencies
  - Module dependency authority (import graph replaces `depends_on` manifest)
  - Application manifest contraction (reduced entries)
  - Compatibility boundary (temporary global namespace adapter if needed)
- **Depends on:** Phase 4
- **Authoritative path before:** `build-manifest.json` `depends_on` graph
- **Authoritative path after:** ESM import graph in `main.ts`
- **Expected change scope:** new `main.ts`, Vite config updates, `build-manifest.json` contraction
- **Explicit exclusions:**
  - All modules TypeScript conversion
  - App controller decomposition
  - Pixi import conversion
- **Verification bundle:**
  - `main.ts` imports resolve correctly
  - Vite builds successfully
  - Application runs identically
  - All existing tests pass
- **Stop conditions:**
  - ESM entry working
  - Import graph authoritative
  - Legacy manifest entries reduced
- **Rollback boundary:** revert to legacy manifest ordering
- **Suggested work-package split:** bootstrap + focused tests may be grouped

---

## 8. Phase 6 — Typed leaf modules

- **Status:** NOT_STARTED
- **Objective:** Convert isolated data/model modules from JS to TypeScript
- **Initial candidates:**
  - `profile.js` → `profile.ts` (persistence boundary)
  - `missions.js` → `missions.ts` (catalog)
  - `gups.js` → `gups.ts` (catalog)
  - `launch.js` → `launch.ts` (content data)
  - `state.js` → `state.ts` (state machine)
- **Depends on:** Phase 5
- **Authoritative path before:** `*.js` source files
- **Authoritative path after:** `*.ts` source files
- **Expected change scope:** individual module `.js` → `.ts` conversions
- **Explicit exclusions:**
  - Multiple independent mission controller conversions in one package
  - App controller decomposition
  - Renderer module conversion
- **Verification bundle:**
  - TypeScript compiles without errors
  - Application runs identically
  - Focused domain tests pass
  - No regressions
- **Stop conditions:**
  - Each module compiles and passes tests
  - Application parity maintained
- **Rollback boundary:** revert individual module to `.js`
- **Suggested work-package split:** one work package per module group (profile + state, missions + GUPs + launch)

---

## 9. Phase 7 — Shared boundary types

- **Status:** NOT_STARTED
- **Objective:** Define TypeScript interfaces for cross-module contracts
- **Included requirements:**
  - Gameplay snapshot types (phase state, travel state, rescue state)
  - Phase ID type definitions
  - Normalized pointer intent types
  - Renderer adapter contract types
  - Persistence schema types (profile, progression)
- **Depends on:** Phase 6
- **Authoritative path before:** implicit contracts in JS
- **Authoritative path after:** TypeScript interfaces
- **Expected change scope:** new type definition files, module signature updates
- **Explicit exclusions:**
  - Speculative framework abstractions
  - Excessive generic abstractions
  - Renderer-owned gameplay model
- **Verification bundle:**
  - TypeScript compiles without errors
  - No runtime behavior changes
  - Application parity maintained
- **Stop conditions:**
  - Shared types defined
  - Cross-module contracts typed
  - No regressions
- **Rollback boundary:** remove type files, revert signatures
- **Suggested work-package split:** single work package

---

## 10. Phase 8 — Application orchestration decomposition

- **Status:** NOT_STARTED
- **Objective:** Break `app.js` into bounded controller modules with clear ownership
- **Recommended work-package grouping:**
  1. Profile and mission-selection flow
  2. Launch and travel flow
  3. Rescue-site transition and tutorial flow
  4. Pause/timer lifecycle
  5. Sea-turtle mission lifecycle
  6. Crab mission lifecycle
  7. Young-whale mission lifecycle
  8. Mission-success and return flow
- **Depends on:** Phase 7
- **Authoritative path before:** `app.js` monolith
- **Authoritative path after:** bounded controller modules
- **Expected change scope:** `app.js` decomposition into multiple files
- **Explicit exclusions:**
  - All groups in one work package
  - Gameplay semantics changes
  - Rendering changes
- **Verification bundle:**
  - TypeScript compiles
  - All phase transitions work
  - All mission flows complete
  - Pause/resume works
  - Application parity maintained
- **Stop conditions:**
  - Each controller group verified independently
  - No regressions in any flow
- **Rollback boundary:** revert to monolithic `app.js`
- **Suggested work-package split:** one work package per group (groups 1-2 may be combined if tightly coupled)

---

## 11. Phase 9 — Scene and renderer modules

- **Status:** NOT_STARTED
- **Objective:** Migrate PixiJS scene modules to ESM/TypeScript
- **Included requirements:**
  - `render-runtime.js` → `render-runtime.ts` (ESM)
  - `travel-scene.js` → `travel-scene.ts`
  - `sea-turtle-scene.js` → `sea-turtle-scene.ts`
  - `crab-scene.js` → `crab-scene.ts`
  - Gameplay snapshot adapter types
  - Display-tree lifecycle ownership documentation
  - Pointer-intent boundary types
  - Renderer capability typing
- **Depends on:** Phase 8
- **Authoritative path before:** `*-scene.js` and `render-runtime.js`
- **Authoritative path after:** `*-scene.ts` and `render-runtime.ts`
- **Expected change scope:** scene module conversions
- **Explicit exclusions:**
  - Gameplay semantics migration
  - Visual redesign
  - Asset pipeline rewrite
- **Verification bundle:**
  - TypeScript compiles
  - All scenes render correctly
  - WebGL and Canvas fallback paths work
  - Pointer mapping parity
  - Application parity maintained
- **Stop conditions:**
  - All scene modules converted
  - Rendering parity verified
- **Rollback boundary:** revert scene modules to `.js`
- **Suggested work-package split:** render-runtime first, then scene modules individually

---

## 12. Phase 10 — PixiJS package-import cutover

- **Status:** NOT_STARTED
- **Objective:** Replace vendored PixiJS UMD with package import
- **Included requirements:**
  - Repository-pinned version reconciliation with official stable
  - Official stable/support status verification
  - Package import (`import * as PIXI from 'pixi.js'`)
  - License evidence
  - Bundle inclusion verification
  - Renderer initialization parity
  - WebGL/Canvas fallback preservation
  - Zero runtime network requests
  - Artifact verification
- **Depends on:** Phase 9
- **Authoritative path before:** `vendor/pixi-8.19.0.min.js` vendored UMD
- **Authoritative path after:** `pixi.js` package dependency
- **Expected change scope:** `package.json`, Vite config, import statements
- **Explicit exclusions:**
  - PixiJS version upgrade (separate work package if needed)
  - Vendored UMD deletion (may be separate cleanup)
- **Verification bundle:**
  - Package import resolves
  - PixiJS version matches expected
  - WebGL initialization works
  - Canvas fallback works
  - Zero external runtime requests
  - Artifact contains bundled PixiJS
  - All existing tests pass
- **Stop conditions:**
  - Package import working
  - Rendering parity verified
  - Rollback path available (re-vendor if needed)
- **Rollback boundary:** re-vendor PixiJS UMD
- **Suggested work-package split:** single work package

---

## 13. Phase 11 — Legacy manifest and global contraction

- **Status:** NOT_STARTED
- **Objective:** Remove obsolete manifest entries, global namespace compatibility, and stale scaffold assertions
- **Included requirements:**
  - Remove obsolete application script entries from manifest
  - Remove obsolete `depends_on` relationships
  - Remove compatibility namespace adapters
  - Remove stale scaffold assertions that validate legacy structure
  - Contract builder to match new module graph
- **Depends on:** Phase 10
- **Authoritative path before:** legacy manifest with all original entries
- **Authoritative path after:** contracted manifest
- **Expected change scope:** `build-manifest.json`, test updates
- **Explicit exclusions:**
  - Deletion before zero-reference proof
  - Unrelated test cleanup
- **Verification bundle:**
  - Zero references to removed entries proven (grep)
  - All tests pass
  - Build succeeds
  - Artifact drift passes
- **Stop conditions:**
  - Manifest contracted
  - All references removed
  - No regressions
- **Rollback boundary:** restore manifest entries
- **Suggested work-package split:** single work package per obsolete entry group

---

## 14. Phase 12 — Standalone packaging consolidation

- **Status:** NOT_STARTED
- **Objective:** Finalize standalone HTML packaging to consume Vite output directly
- **Included requirements:**
  - Vite output ingestion by standalone builder
  - CSS/JS inline policy
  - Source-map policy (inclusion or exclusion in artifact)
  - Asset URL rejection (no external references)
  - Deterministic packaging
  - Artifact drift verification
  - Zero external requests verification
- **Depends on:** Phase 11
- **Authoritative path before:** builder consumes ordered scripts
- **Authoritative path after:** builder consumes Vite bundle
- **Expected change scope:** `build_single_html.py` updates, packaging config
- **Explicit exclusions:**
  - Standalone HTML contract removal
  - Multiple-file deployment
- **Verification bundle:**
  - Standalone HTML builds deterministically
  - Artifact is self-contained
  - Zero external requests
  - Artifact drift passes
  - All gameplay flows work
- **Stop conditions:**
  - Packaging finalized
  - Contract preserved
- **Rollback boundary:** revert builder to consume ordered scripts
- **Suggested work-package split:** single work package

---

## 15. Phase 13 — Obsolete tooling cleanup

- **Status:** NOT_STARTED
- **Objective:** Remove unused vendor files, builder branches, and stale documentation
- **Candidates:**
  - Unused vendor UMD files (after package import proven)
  - Unused builder branches
  - Obsolete manifest schema fields
  - Obsolete compatibility harnesses
  - Stale documentation references
  - Stale tests validating legacy structure only
- **Depends on:** Phase 12
- **Authoritative path before:** includes obsolete artifacts
- **Authoritative path after:** clean repository
- **Expected change scope:** file deletions, documentation updates
- **Explicit exclusions:**
  - Deletion before rollback need assessment
  - Unrelated code cleanup
- **Verification bundle:**
  - Zero references to deleted files
  - All tests pass
  - Build succeeds
  - No regressions
- **Stop conditions:**
  - Obsolete artifacts removed
  - References proven zero
- **Rollback boundary:** restore deleted files from git history
- **Suggested work-package split:** one work package per deletion group (vendor, builder, tests, docs)

---

## 16. Phase 14 — Migration closeout

- **Status:** NOT_STARTED
- **Objective:** Verify all migration targets are achieved
- **Complete state:**
  - Canonical TS/ESM application source
  - Vite development server working
  - Vite production application bundle working
  - Deterministic standalone HTML
  - Locally bundled PixiJS (package import)
  - Preserved gameplay state authority
  - Preserved atlas pipeline
  - Representative gameplay parity
  - Pointer parity
  - Pause/resume parity
  - Renderer backend evidence
  - Zero runtime external requests
  - Legacy application global graph removed
  - Current documentation aligned
- **Depends on:** Phase 13
- **Authoritative path before:** all migration phases
- **Authoritative path after:** migration complete
- **Expected change scope:** final verification, documentation alignment
- **Explicit exclusions:**
  - New feature development
  - Unrelated improvements
- **Verification bundle:**
  - Full test suite passes
  - TypeScript compiles
  - Vite builds
  - Standalone artifact builds deterministically
  - Chrome headless smoke passes
  - Manual gameplay walkthrough
  - All existing tests pass
  - Documentation accurate
- **Stop conditions:**
  - All acceptance criteria met
  - Documentation aligned
- **Rollback boundary:** entire migration (comprehensive rollback procedure documented)
- **Suggested work-package split:** single work package

---

## 17. Short-circuit and stop rules

- If the goal of a phase is already satisfied by prior work, duplicate implementation is skipped.
- Parity is verified before any cutover.
- If production cutover fails, the legacy production path is retained.
- Toolchain installation failure is not worked around with source hacks.
- Browser verification absence is not replaced by unit test success.
- Generated artifact drift is not resolved by direct HTML editing.
- Performance regression is not hidden by unrelated visual removal.
- If the official stable version differs from the repository pin, reconciliation is performed first.
- If work package scope exceeds local model context stability, it is split into bounded child work packages.
- Independent defects are not forced into the current work package scope.
- Strongly coupled defects may be included after scope and verification are updated.
