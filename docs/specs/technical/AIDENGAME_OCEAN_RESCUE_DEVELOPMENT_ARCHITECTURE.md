# AidenGame Ocean Rescue — Development Architecture

- **Version:** 1.0
- **Date:** 2026-08-03
- **Status:** CANONICAL
- **Owner:** Ocean Rescue development tooling
- **Parent product spec:** `../product/AIDENGAME_OCEAN_RESCUE_MVP_PRD.md`
- **Parent rendering spec:** `../product/AIDENGAME_OCEAN_RESCUE_RENDERING_MVP.md`
- **Related asset handoff spec:** `AIDENGAME_OCEAN_RESCUE_MANUAL_SVG_ASSET_HANDOFF.md`
- **Related migration plan:** `../../plans/PLAN_ocean_rescue_vite_esm_typescript_migration.md`
- **Applies to:** Ocean Rescue development source, build pipeline, and deployment artifact
- **Browser runtime:** HTML, CSS, JavaScript, locally bundled PixiJS
- **Renderer:** PixiJS v8 WebGL → Canvas fallback
- **Development module system:** ESM (PLANNED)
- **Development language:** TypeScript (PLANNED)
- **Development bundler:** Vite (PLANNED)
- **Package manager:** pnpm (PLANNED)
- **Deployment artifact:** single standalone HTML file

---

## 1. Purpose

This document defines the long-term development architecture for Ocean Rescue. It closes the authority gap between the current global-namespace JavaScript authoring model and the target TypeScript/ESM/Vite development model.

This document does not:

- deprecate or replace the standalone HTML deployment artifact
- redesign gameplay, progression, input, missions, or rendering contracts
- serve as a gameplay, visual design, or mission design specification
- authorize immediate migration execution

The core decision is: **keep the browser/PixiJS game as-is and improve the authoring experience by introducing ESM, TypeScript, and Vite as development tooling while preserving the standalone HTML deployment artifact.**

---

## 2. Authority and precedence

1. User requests and explicit constraints
2. Product and gameplay specifications (`AIDENGAME_OCEAN_RESCUE_MVP_PRD.md`)
3. Rendering MVP (`AIDENGAME_OCEAN_RESCUE_RENDERING_MVP.md`)
4. **This document** — development architecture canonical specification
5. Manual SVG Asset Handoff SSOT (`AIDENGAME_OCEAN_RESCUE_MANUAL_SVG_ASSET_HANDOFF.md`)
6. Executable tests and build contracts (`tests/`)
7. Migration plan (`PLAN_ocean_rescue_vite_esm_typescript_migration.md`)
8. Historical plans and reports

Rules:

- This architecture spec is the authority for long-term development technology decisions.
- The migration plan manages execution order and state; it cannot alter architecture decisions.
- The generated standalone HTML is a deployment artifact, not an authoring source.
- If tests and documentation conflict, the source code is not immediately modified to match documentation. The conflict root cause and canonical authority are investigated first.

---

## 3. Decision summary

### 3.1 Maintained

| Decision | Rationale |
|---|---|
| Browser platform | Deployment constraint from product PRD |
| PixiJS v8 renderer family | Current implementation baseline, stable |
| WebGL priority with Canvas fallback | Performance + resilience |
| Logical 1280x720 coordinate system | Cross-device consistency |
| DPR upper bound of 2 | Performance guardrail |
| Gameplay state authority in domain modules | Separation of concerns |
| Pointer normalization at single boundary | Consistent input handling |
| Canonical asset pipeline (SVG → raster atlas) | Proven deterministic build |
| Generated asset registry | Embedded in single HTML |
| Final standalone HTML deployment artifact | Product PRD constraint |
| Zero runtime external requests | Security and reliability |
| Static hosting | Deployment model |
| Existing Python asset and packaging tooling | Stable, proven |

### 3.2 Introduced (target state)

| Decision | Purpose |
|---|---|
| ESM application source | Explicit module imports, tree-shaking |
| TypeScript for new and migrated modules | Type safety, IDE support, refactoring confidence |
| Vite development server | Fast HMR feedback loop |
| Vite application bundling | Deterministic production bundles |
| pnpm package management | Disk-efficient, strict dependency resolution |
| Explicit module imports | Remove global namespace dependency resolution |
| Source-level type checking | Catch errors before runtime |
| Bounded controller ownership | Each module owns specific lifecycle concerns |
| Reproducible Node toolchain | Consistent development environment |

### 3.3 Not introduced

| Exclusion | Reason |
|---|---|
| React | Unnecessary framework overhead for game UI |
| Next.js | Static HTML deployment, no SSR needed |
| Phaser | PixiJS v8 is already the renderer |
| Godot / Unity | Browser deployment constraint |
| Tauri | Browser deployment, no desktop app needed |
| Backend API | Client-side game, no server logic |
| Node runtime dependency | Build-time only; zero runtime network |
| Runtime CDN imports | Standalone HTML contract forbids external requests |
| Runtime code splitting requiring network | Standalone HTML contract |
| Multiple-file deployment replacing standalone HTML | Product PRD constraint |
| Whole-project framework migration | Incremental migration only |

---

## 4. Current architecture baseline

### 4.1 Source structure

```text
domains/ocean-rescue/src/
├─ build-manifest.json       (script ordering + dependency graph)
├─ index.template.html       (HTML skeleton with CSS/Script markers)
├─ style.css                 (game styles)
├─ vendor/
│  └─ pixi-8.19.0.min.js    (vendored PixiJS UMD)
├─ render-assets.generated.js (embedded atlas registry)
├─ render-runtime.js         (PixiJS bootstrap, atlas loading, rendering)
├─ state.js                  (phase state machine)
├─ profile.js                (localStorage persistence)
├─ missions.js               (mission catalog)
├─ gups.js                   (GUP catalog)
├─ launch.js                 (launch sequence content)
├─ travel.js                 (auto-forward loop)
├─ terrain.js                (obstacle system)
├─ travel-scene.js           (PixiJS travel scene)
├─ rescue.js                 (rescue arrival logic)
├─ sea-turtle.js             (mission 1 domain)
├─ sea-turtle-scene.js       (mission 1 PixiJS scene)
├─ crab.js                   (mission 2 domain)
├─ crab-scene.js             (mission 2 PixiJS scene)
├─ young-whale.js            (mission 3 domain)
├─ mission-success.js        (completion flow)
└─ app.js                    (orchestration hub)
```

### 4.2 Source graph

Total script entries: 19 (1 vendor, 1 generated-assets, 17 application)

**Vendor entries (1):**

| Namespace | File | Dependencies |
|---|---|---|
| `PIXI` | `vendor/pixi-8.19.0.min.js` | none |

**Generated-asset entries (1):**

| Namespace | File | Dependencies |
|---|---|---|
| `OceanRescue.RenderAssets` | `render-assets.generated.js` | none |

**Application entries (17):**

| Namespace | File | Direct dependencies |
|---|---|---|
| `OceanRescue.RenderRuntime` | `render-runtime.js` | `PIXI`, `OceanRescue.RenderAssets` |
| `OceanRescue.State` | `state.js` | none |
| `OceanRescue.Profile` | `profile.js` | none |
| `OceanRescue.Missions` | `missions.js` | none |
| `OceanRescue.Gups` | `gups.js` | none |
| `OceanRescue.Launch` | `launch.js` | none |
| `OceanRescue.Travel` | `travel.js` | none |
| `OceanRescue.Terrain` | `terrain.js` | none |
| `OceanRescue.TravelScene` | `travel-scene.js` | `OceanRescue.RenderRuntime` |
| `OceanRescue.Rescue` | `rescue.js` | none |
| `OceanRescue.SeaTurtle` | `sea-turtle.js` | none |
| `OceanRescue.SeaTurtleScene` | `sea-turtle-scene.js` | `OceanRescue.RenderRuntime`, `OceanRescue.SeaTurtle` |
| `OceanRescue.Crab` | `crab.js` | none |
| `OceanRescue.CrabScene` | `crab-scene.js` | `OceanRescue.RenderRuntime`, `OceanRescue.Crab` |
| `OceanRescue.YoungWhale` | `young-whale.js` | none |
| `OceanRescue.MissionSuccess` | `mission-success.js` | none |
| `OceanRescue.App` | `app.js` | `State`, `RenderRuntime`, `Profile`, `Missions`, `Gups`, `Launch`, `Travel`, `Terrain`, `Rescue`, `SeaTurtle`, `SeaTurtleScene`, `TravelScene`, `Crab`, `YoungWhale`, `MissionSuccess` |

**Namespaces total:** 19

### 4.3 Build graph

```text
canonical visual source (SVG/high-res raster)
→ atlas build (scripts/ocean_rescue/build_atlases.py)
→ atlas validation (scripts/ocean_rescue/validate_atlases.py)
→ generated asset registry (scripts/ocean_rescue/build_render_assets_registry.py)
→ application source inclusion (render-assets.generated.js)
→ HTML template (index.template.html)
→ single-HTML builder (scripts/ocean_rescue/build_single_html.py)
→ tracked deploy artifact (ocean-rescue/index.html)
→ artifact drift verification (tests/test_ocean_rescue_artifact_drift.py)
```

Commands:

```bash
just build-ocean-rescue          # full build
just check-ocean-rescue-drift    # artifact drift check
just build-ocean-rescue-atlases  # atlas build only
just build-ocean-rescue-render-package  # vendor + registry + HTML
just check-ocean-rescue-render-package  # render package integrity
```

### 4.4 Runtime ownership

`app.js` is the central orchestration hub. It owns:

| Responsibility | Description |
|---|---|
| Phase routing | `State.beginTransition` / `completeTransition` for all phase changes |
| DOM screen lifecycle | Show/hide mission-select, GUP-select, launch, stage, rescue, success sections |
| Pixi scene lifecycle | Mount/unmount TravelScene, SeaTurtleScene, CrabScene |
| Launch sequence | Timer-based briefing with skip support |
| Travel frame loop | `requestAnimationFrame` loop with delta-time stepping |
| Rescue site transition | Timer-based transition with auto-complete |
| Tutorial lifecycle | Timer-based tutorial with skip support |
| Mission-specific input | SeaTurtle rope input, Crab hold-and-drag, YoungWhale tow-line |
| Pointer capture | Single-pointer ownership, pointer-capture API |
| Timer ownership | Pauseable timer registry with freeze/rearm |
| Pause/resume | Full pause overlay with countdown resume |
| Mission completion | Success sequence, narration, Continue/Replay |
| Profile persistence | Animal selection, localStorage |
| Progression persistence | Mission completion, unlock, `New!` state |

---

## 5. Target architecture

### 5.1 Target flow

```text
TypeScript / ESM application source
→ Vite development server (fast HMR)
→ Vite deterministic application bundle
→ existing generated atlas registry injection
→ standalone packaging boundary
→ tracked ocean-rescue/index.html
```

### 5.2 Target structure (proposed, not final)

```text
domains/ocean-rescue/
├─ src/
│  ├─ main.ts                  (canonical ESM entry)
│  ├─ app/
│  │  ├─ orchestrator.ts
│  │  ├─ phase-router.ts
│  │  ├─ pause.ts
│  │  └─ input.ts
│  ├─ core/
│  │  ├─ state.ts
│  │  ├─ timer.ts
│  │  └─ pointer.ts
│  ├─ profile/
│  │  ├─ profile.ts
│  │  └─ persistence.ts
│  ├─ missions/
│  │  ├─ catalog.ts
│  │  ├─ sea-turtle.ts
│  │  ├─ crab.ts
│  │  └─ young-whale.ts
│  ├─ scenes/
│  │  ├─ render-runtime.ts
│  │  ├─ travel-scene.ts
│  │  ├─ sea-turtle-scene.ts
│  │  └─ crab-scene.ts
│  ├─ rendering/
│  │  └─ renderer-adapter.ts
│  └─ styles/
│     └─ game.css
├─ index.dev.html              (Vite dev entry)
├─ vite.config.ts              (PLANNED)
├─ tsconfig.json               (PLANNED)
└─ package boundary
```

Final paths are determined at each migration work package after verifying the current repository.

---

## 6. Source-of-truth matrix

| Concern | Canonical authoring source | Derived/output |
|---|---|---|
| Gameplay state | Domain modules (state.js, missions.js, etc.) | Renderer snapshot |
| Application source | TS/ESM modules (PLANNED) | Bundled JS |
| Styles | Source CSS | Inlined CSS in HTML |
| Visual source | Approved canonical assets (SVG/raster) | Raster atlases |
| Asset metadata | art-packet.json + art-approval.json | Generated registry |
| Renderer state | Gameplay-derived adapter state | Pixi display tree |
| Deployment | Packaging contract | Standalone HTML |
| Verification | Test harness source | Reports/screenshots |

Authority rules:

- `ocean-rescue/index.html` is a tracked deployment artifact. It is never edited directly.
- Artifact changes originate from canonical source and the build pipeline.
- PixiJS display objects are not gameplay state. They are derived renderer state.

---

## 7. Runtime and build-time boundary

### 7.1 Browser runtime

| Contract | Detail |
|---|---|
| Language | HTML, CSS, JavaScript |
| Renderer | Locally bundled PixiJS v8 |
| Node runtime | None |
| Package manager | None |
| Module CDN | None |
| External asset fetch | Zero |
| Backend requirement | None |
| Development server requirement | None |

### 7.2 Node build tooling (PLANNED)

| Tool | Role |
|---|---|
| pnpm | Package management |
| Vite | Development server + application bundling |
| TypeScript | Source-level type checking |
| Application module graph | ES module imports |
| Development server | Fast HMR feedback loop |
| Application bundling | Deterministic production output |
| Source-level type checking | Error detection before runtime |

### 7.3 Python build tooling (existing)

| Tool | Role |
|---|---|
| Atlas validation | SVG/source validation, rasterization, atlas generation |
| Generated asset registry | `build_render_assets_registry.py` |
| Single-HTML builder | `build_single_html.py` |
| Artifact drift checks | `test_ocean_rescue_artifact_drift.py` |

### 7.4 Repository command layer

`just` remains the repository command entrypoint. Actual commands are documented in the Justfile. New development commands (Vite dev server, TypeScript checking) are added only by the corresponding migration work packages.

---

## 8. Module rules

Normative rules for migration:

1. New production code must not expand `window.OceanRescue.*` usage.
2. Temporary compatibility adapters are permitted only in explicitly declared migration states.
3. Static ESM imports are the default for new code.
4. Circular dependencies are forbidden.
5. The renderer must not change or own gameplay state.
6. Scene modules must not redefine success, progression, save semantics, or pause behavior.
7. DOM lifecycle and Pixi scene lifecycle owners must be clearly separated.
8. Timer and animation frame owners must be clearly separated.
9. Pointer coordinate normalization occurs at a single boundary.
10. Module imports must not create unnecessary side effects.
11. Leaf modules are migrated first (profile, missions, GUPs, terrain, etc.).
12. Strongly coupled controllers, types, callers, and focused tests may be grouped in one work package.
13. Large-scale simultaneous conversion of multiple mission subsystems is separated when it exceeds bounded context.

---

## 9. Build contract

### 9.1 Development (PLANNED)

| Contract | Detail |
|---|---|
| Fast feedback | Vite HMR, sub-second reload |
| Deterministic startup entry | `main.ts` canonical entry |
| No production artifact mutation | Dev server does not modify tracked HTML |
| Explicit browser entry | `index.dev.html` |
| Source-level diagnostics | TypeScript compiler errors |
| Gameplay flow parity | Current game works identically |

### 9.2 Production

| Contract | Detail |
|---|---|
| Pinned dependency graph | Lockfile |
| Deterministic bundle | Vite production build |
| Atlas validation before packaging | Existing Python pipeline |
| Generated registry drift detection | Existing test suite |
| Standalone HTML generation | `build_single_html.py` |
| Deploy artifact drift detection | `test_ocean_rescue_artifact_drift.py` |
| No external runtime requests | Existing build validation |
| Fail-closed build | Existing error handling |
| Source map policy | Decided per work package |
| Stable entrypoint | `main.ts` |
| Reproducible command path | `just build-ocean-rescue` |

---

## 10. Toolchain policy

| Rule | Detail |
|---|---|
| Package manager | pnpm only |
| Lockfile conflict | npm/yarn/pnpm lockfiles must not coexist |
| Version authority | Lockfile is authoritative for exact versions |
| Documentation | Supported line and compatibility policy documented |
| Plugin adoption | Added only when a work package has clear need |
| Single-file plugin | Not a prerequisite |
| Dev vs runtime deps | Explicitly separated |
| Upgrade vs cutover | Not forced into the same work package |
| Pin vs official stable | Reconciliation performed first if they differ |
| Toolchain selection | Does not change existing PixiJS/atlas/gameplay contracts |

### External toolchain status

| Tool | Repository pin | Official stable/supported | Compatibility note | Decision |
|---|---|---|---|---|
| PixiJS | 8.19.0 | v8.x current | Pin is current stable | Maintain pin, reconcile at Phase 10 |
| Vite | ABSENT | 8.2.0 (Jul 2026) | Not yet installed | Install at Phase 1 |
| TypeScript | ABSENT | 7.0 | Not yet installed | Install at Phase 1 |
| pnpm | ABSENT | Active, current | Not yet installed | Install at Phase 1 |
| Node.js | ABSENT (.nvmrc) | LTS | No version pin | Pin at Phase 1 |

Toolchain exact versions are locked by lockfile at implementation time. This specification does not force specific versions.

---

## 11. Migration states

### 11.1 State definitions

```text
LEGACY_GLOBAL          — Current state: window.OceanRescue global namespaces
DEV_SERVER_COMPAT      — Existing source runs on Vite dev server
PACKAGE_BOUNDARY_READY — pnpm package boundary established
SHADOW_BUNDLE          — Vite production bundle built alongside legacy
PRODUCTION_BUNDLE      — Standalone builder consumes Vite bundle
ESM_ENTRY              — Canonical main.ts entry with explicit imports
TYPED_MODULES          — TypeScript applied to leaf modules
TYPED_CONTROLLERS      — TypeScript applied to orchestration modules
PACKAGE_PIXI           — PixiJS loaded as package dependency
LEGACY_GRAPH_REMOVED   — Legacy global namespace graph removed
MIGRATION_COMPLETE     — All targets achieved
```

### 11.2 State details

| State | Authoritative source | Production path | Compatibility | Allowed overlap | Forbidden mutation | Entry condition |
|---|---|---|---|---|---|---|
| LEGACY_GLOBAL | `src/*.js` global namespaces | `build-manifest.json` ordered scripts | Full legacy | None | None | Initial |
| DEV_SERVER_COMPAT | `src/*.js` globals + dev entry | Legacy build pipeline | Dev-only HTML entry | Legacy + dev paths | Production bundle changes | Phase 0 complete |
| PACKAGE_BOUNDARY_READY | `package.json` + lockfile | Legacy build pipeline | None | None | Source ESM conversion | pnpm + Vite installed |
| SHADOW_BUNDLE | Vite config + `src/*.js` | Legacy + shadow bundle | Shadow only | Legacy + shadow paths | Legacy manifest changes | Vite builds successfully |
| PRODUCTION_BUNDLE | Vite config + legacy manifest | Standalone builder consumes bundle | Builder adapted | Legacy + new paths | Legacy script ordering | Parity verified |
| ESM_ENTRY | `main.ts` | Vite entry | None | None | Legacy global expansion | Explicit imports working |
| TYPED_MODULES | `*.ts` leaf modules | Vite entry | None | None | Untyped module expansion | Types pass for leaves |
| TYPED_CONTROLLERS | `*.ts` controllers | Vite entry | None | None | Controller changes | Types pass for controllers |
| PACKAGE_PIXI | `package.json` pixi.js | Vite entry | None | None | Vendored UMD removal before rollback proof | Package import verified |
| LEGACY_GRAPH_REMOVED | ESM modules only | Vite entry | None | None | Global namespace revival | All references to globals = 0 |
| MIGRATION_COMPLETE | TS/ESM modules | Standalone HTML via Vite | None | None | Migration regression | All acceptance criteria met |

---

## 12. Dual-path rules

During migration when old and new paths coexist:

1. One authoritative path is designated. The shadow path must not independently change gameplay state.
2. Shadow paths exist only for parity verification.
3. Silent fallback between old/new is forbidden.
4. Parity failure is not treated as success.
5. Production cutover is performed as a single ownership switch.
6. Cutover and legacy cleanup may be separated.
7. Rollback path is not removed until zero references are proven.

---

## 13. Cutover and rollback

Each cutover work package must include:

- Baseline evidence (hashes, screenshots, test results)
- Changed ownership description
- Affected paths
- Parity checks performed
- Artifact comparison results
- Browser verification evidence
- Rollback procedure
- Legacy path retention or removal decision
- Remaining cleanup items

Strongly coupled changes with the same rollback boundary may be performed together. Changes with different rollback boundaries are separated into follow-up work packages.

---

## 14. Verification architecture

Minimum verification layers (applied per work package based on risk):

| Layer | Description |
|---|---|
| Package/lock integrity | pnpm install, lockfile consistency |
| TypeScript diagnostics | `tsc --noEmit` or equivalent |
| Module graph validation | Import resolution, circular dependency check |
| Focused domain tests | Existing Python tests for Ocean Rescue |
| Controller lifecycle tests | Phase transitions, pause/resume |
| Scene contract tests | Scene mount/unmount, sync |
| Browser startup smoke | Chrome headless verification |
| Representative gameplay flow | Travel → rescue → completion |
| Pointer mapping parity | Logical coordinate mapping |
| Pause/resume parity | Timer freeze/rearm |
| Renderer backend evidence | WebGL vs Canvas detection |
| Zero external request evidence | Network pattern validation |
| Deterministic application bundle | Byte-identical rebuilds |
| Deterministic atlas outputs | Atlas rebuild determinism |
| Standalone artifact drift | Tracked artifact matches rebuild |
| Performance evidence | Frame rate, memory (where affected) |

---

## 15. Non-goals

- Engine replacement (PixiJS is retained)
- Gameplay redesign
- New missions
- Visual redesign
- Atlas pipeline rewrite
- All-JavaScript-at-once TypeScript conversion
- Whole `app.js` rewrite
- React introduction
- Backend introduction
- Runtime network imports
- Standalone artifact removal
- Generated artifact manual editing
- Unrelated code cleanup
- Migration phase entire execution in one task

---

## 16. Change control

The following changes require architecture specification revision:

- Renderer family replacement (e.g., PixiJS to Three.js)
- Standalone artifact deprecation
- Backend or runtime network introduction
- Package manager replacement (e.g., pnpm to yarn)
- Asset representation change (e.g., atlas to runtime SVG)
- Gameplay authority ownership change
- TypeScript/ESM strategy reversal
- Fundamental Python/Node responsibility boundary change

Ordinary module migration follows the migration plan without requiring architecture revision.
