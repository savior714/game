# AidenGame Ocean Rescue — Development Architecture

- **Version:** 1.4
- **Date:** 2026-08-03
- **Status:** CANONICAL
- **Owner:** Ocean Rescue development tooling
- **Parent product spec:** `../product/AIDENGAME_OCEAN_RESCUE_MVP_PRD.md`
- **Parent rendering spec:** `../product/AIDENGAME_OCEAN_RESCUE_RENDERING_MVP.md`
- **Related asset handoff spec:** `AIDENGAME_OCEAN_RESCUE_MANUAL_SVG_ASSET_HANDOFF.md`
- **Related migration plan:** `../../plans/PLAN_ocean_rescue_vite_esm_typescript_migration.md`
- **Applies to:** Ocean Rescue development source, build pipeline, and deployment artifact
- **Browser runtime:** HTML, CSS, JavaScript, locally bundled PixiJS
- **Renderer:** PixiJS v8, WebGL priority with Canvas fallback
- **Development module system:** ESM (PLANNED)
- **Development language:** TypeScript (PLANNED)
- **Development bundler:** Vite (PLANNED)
- **Package manager:** pnpm
- **Deployment artifact:** single standalone HTML file
- **Last external status verification:** 2026-08-03

### Current package, Node, and development-server boundary

- **Package boundary:** `domains/ocean-rescue`
- **Node:** 24.18.0
- **pnpm:** 11.17.0
- **Vite:** 8.1.5
- **TypeScript:** 7.0.2
- **Pixi package metadata:** 8.19.0
- **Lockfile:** `domains/ocean-rescue/pnpm-lock.yaml`
- **Development server:** `index.dev.html` + `vite.config.ts`, `just dev-ocean-rescue`
- **Shadow application bundle:** `vite.shadow.config.ts`, `just build-ocean-rescue-shadow-bundle`
- **State:** `SHADOW_BUNDLE`

Pixi boundary:

> `pixi.js` is pinned in package metadata.
> Production rendering still uses the vendored UMD path.
> WP-40 remains responsible for import and production cutover.

---

## 1. Purpose

This document defines the long-term development architecture for Ocean Rescue.
It closes the authority gap between the current global-namespace JavaScript authoring model and the target TypeScript/ESM/Vite development model.

This document does not:

- deprecate or replace the standalone HTML deployment artifact;
- redesign gameplay, progression, input, missions, or rendering contracts;
- serve as a gameplay, visual-design, or mission-design specification;
- authorize immediate migration execution;
- require other AidenGame domains to adopt this toolchain.

The core decision is:

> Keep the browser/PixiJS game and its standalone deployment contract, while replacing the inefficient authoring and module workflow with ESM, TypeScript, Vite, and pnpm through bounded migration work packages.

---

## 2. Authority and precedence

1. User requests and explicit constraints
2. Product and gameplay specification
3. Rendering MVP
4. **This development architecture specification**
5. Manual SVG Asset Handoff SSOT
6. Executable tests and build contracts
7. Migration plan
8. Historical plans and reports

Rules:

- This document is authoritative for long-term development technology and source/build boundaries.
- The migration plan manages execution order, work-package boundaries, and status; it cannot silently change architecture decisions.
- The generated standalone HTML is a deployment artifact, not an authoring source.
- Tests and executable build contracts remain authoritative evidence of actual behavior.
- If code, tests, and documentation conflict, do not immediately force code to match prose. Investigate the current intent and actual contract first.
- Ordinary implementation details may evolve without revising this spec when they remain inside the boundaries defined here.

---

## 3. Decision summary

### 3.1 Maintained contracts

| Decision | Contract |
|---|---|
| Platform | Browser-based static web game |
| Renderer family | PixiJS v8 |
| Renderer preference | WebGL first, Canvas fallback |
| Logical coordinates | 1280×720 |
| Renderer DPR | Upper bound of 2 |
| Gameplay authority | Domain state modules, never Pixi display objects |
| Pointer normalization | One browser-to-logical coordinate boundary |
| Visual source | Approved canonical SVG/high-resolution source |
| Runtime visual form | Deterministic raster atlases and generated registry |
| Deployment | One standalone `ocean-rescue/index.html` |
| Runtime network | No renderer CDN, module CDN, or external asset request |
| Hosting | Static hosting |
| Existing build tooling | Python validation, atlas, registry, packaging, drift checks |

### 3.2 Target development contracts

| Decision | Purpose |
|---|---|
| ESM application source | Explicit module graph instead of implicit global ordering |
| TypeScript for new and migrated modules | Source diagnostics and safer refactoring |
| Vite development server | Fast HMR or reload feedback without mutating the production artifact |
| Vite application bundle | Reproducible application bundling before standalone packaging |
| pnpm | One strict package-management and lockfile authority |
| Canonical application entry | One explicit startup entry |
| Bounded controllers | Clear lifecycle, timer, input, and scene ownership |
| Reproducible Node toolchain | Stable build-time environment only |

### 3.3 Explicit exclusions

- React
- Next.js
- Phaser
- Godot
- Unity
- Tauri
- backend API or server runtime
- runtime Node dependency
- runtime CDN imports
- network-dependent code splitting
- replacing standalone HTML with a multi-file deployment
- whole-project framework migration
- all-at-once TypeScript conversion

---

## 4. Current architecture baseline

### 4.1 Current source layout

```text
domains/ocean-rescue/src/
├─ build-manifest.json
├─ build-manifest.legacy.json
├─ index.template.html
├─ style.css
├─ vendor/pixi-8.19.0.min.js
├─ render-assets.generated.js
├─ render-runtime.js
├─ state.js
├─ profile.js            (rollback-only since WP-31A)
├─ profile/profile.ts    (typed canonical profile module, WP-31A)
├─ missions.js           (unchanged mutable controller; canonical + rollback since WP-31B)
├─ missions/catalog.ts   (typed canonical mission catalog, WP-31B)
├─ gups.js               (unchanged mutable controller; canonical + rollback since WP-31B)
├─ gups/catalog.ts       (typed canonical GUP catalog, WP-31B)
├─ launch.js             (rollback-only since WP-31B)
├─ launch/launch.ts      (typed canonical launch API, WP-31B)
├─ travel.js
├─ terrain.js
├─ travel-scene.js
├─ rescue.js
├─ sea-turtle.js
├─ sea-turtle-scene.js
├─ crab.js
├─ crab-scene.js
├─ young-whale.js
├─ mission-success.js
└─ app.js
```

Since WP-30, the canonical ESM graph is authoritative: `src/main.js` imports
`src/esm/app.js`, which imports the `src/esm/*` compatibility adapters. Since
WP-31A, the profile adapter `src/esm/profile.js` imports and re-exports the
typed canonical module `src/profile/profile.ts` (which also registers the
temporary `window.OceanRescue.Profile` ABI); `src/profile.js` is unchanged and
is referenced only by the legacy rollback graph (`build-manifest.legacy.json`).

Since WP-31B, the mission and GUP adapters (`src/esm/missions.js`,
`src/esm/gups.js`) own the typed static-data catalogs
(`src/missions/catalog.ts`, `src/gups/catalog.ts`) and build one frozen facade
each whose `Catalog` is the typed catalog and whose methods are the unchanged
legacy controller methods from `src/missions.js` and `src/gups.js`; those two
legacy controllers remain in the canonical graph for their still-unmigrated
mutable state. The launch adapter `src/esm/launch.js` imports and re-exports
the complete typed launch API `src/launch/launch.ts`; `src/launch.js` is
unchanged and is referenced only by the legacy rollback graph.

### 4.2 Current source graph

`build-manifest.json` currently contains 19 ordered script entries:

- 1 vendor entry: `PIXI`
- 1 generated-assets entry: `OceanRescue.RenderAssets`
- 17 application entries under `window.OceanRescue.*`

The manifest duplicates information that a standard module graph would normally own:

- script file order;
- namespace identity;
- direct dependencies;
- vendor and generated-asset integrity hashes.

`app.js` directly coordinates most application subsystems and is the current orchestration hub.

### 4.3 Current build graph

```text
approved canonical visual source
→ atlas build
→ atlas validation
→ generated asset registry
→ ordered JavaScript inclusion
→ HTML template
→ Python standalone builder
→ tracked ocean-rescue/index.html
→ artifact drift verification
```

Current representative commands:

```bash
just build-ocean-rescue
just check-ocean-rescue-drift
just build-ocean-rescue-atlases
just check-ocean-rescue-atlases
just build-ocean-rescue-render-package
just check-ocean-rescue-render-package
```

### 4.4 Current orchestration concentration

The current application hub owns or coordinates:

- phase routing;
- DOM screen lifecycle;
- Pixi scene mount/unmount;
- launch sequence;
- travel animation frame;
- rescue-site transition and tutorial;
- mission-specific input;
- pointer capture;
- timer registry;
- pause/resume;
- mission success and replay/continue;
- profile persistence;
- progression persistence.

This concentration is not itself proof of a gameplay defect. It is a development and refactoring risk that the migration must reduce without changing semantics.

### 4.5 Sources of development friction

The main friction is not “using HTML.” It is the combination of:

- global namespace dependency resolution;
- manually duplicated manifest ordering;
- missing compile-time module and type information;
- authoring source and generated deploy artifact being operationally close;
- concentrated orchestration ownership;
- tests carrying part of the burden normally handled by a compiler and bundler;
- rebuild-heavy feedback for ordinary browser changes.

---

## 5. Target architecture

### 5.1 Target flow

```text
TypeScript / ESM application source
→ Vite development server for local feedback
→ deterministic Vite application bundle
→ existing generated atlas registry
→ standalone packaging boundary
→ tracked ocean-rescue/index.html
```

### 5.2 Proposed source shape

The exact final paths are decided by migration work packages after inspecting the then-current repository.
The target conceptual boundaries are:

```text
domains/ocean-rescue/
├─ src/
│  ├─ main.ts
│  ├─ app/
│  ├─ core/
│  ├─ profile/
│  ├─ missions/
│  ├─ scenes/
│  ├─ rendering/
│  └─ styles/
├─ index.dev.html
├─ vite.config.ts
├─ tsconfig.json
└─ package boundary
```

This diagram is directional, not permission to move every file in one work package.

---

## 6. Source-of-truth matrix

| Concern | Canonical authoring source | Derived/output |
|---|---|---|
| Gameplay state | Domain modules | Renderer snapshots |
| Application source | TS/ESM modules (target) | Vite application bundle |
| Styles | Source CSS | Bundled/inlined CSS |
| Visual source | Approved canonical SVG/raster source | Raster atlases |
| Asset metadata | `art-packet.json` and approval data | Generated registry |
| Renderer state | Gameplay-derived adapter state | Pixi display tree |
| Deployment | Packaging contract | Standalone HTML |
| Verification | Tests and harness source | Reports, hashes, screenshots |

Authority rules:

- `ocean-rescue/index.html` is a tracked deployment artifact and is never edited directly.
- Artifact changes originate from canonical source and the build pipeline.
- Pixi display objects are not gameplay state.
- Shadow or compatibility paths must not independently mutate gameplay state.

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

### 7.2 Node build tooling (target)

| Tool | Responsibility |
|---|---|
| pnpm | Package and lockfile authority |
| Vite | Development server and application bundling |
| TypeScript | Source diagnostics and type checking |
| ESM graph | Application dependency authority |

Node tooling is build-time only and must not become a production runtime dependency.

### 7.3 Python build tooling (maintained)

| Responsibility | Current owner |
|---|---|
| Canonical asset validation | Existing Ocean Rescue scripts |
| SVG/raster/atlas processing | Existing atlas pipeline |
| Generated asset registry | `build_render_assets_registry.py` |
| Standalone packaging | `build_single_html.py` or its explicit successor |
| Artifact drift | Existing focused tests |

### 7.4 Repository command layer

`just` remains the repository-level command entrypoint.
New Node commands become current documentation only after their implementation work package publishes them.

---

## 8. Module and ownership rules

1. New production code must not expand `window.OceanRescue.*` usage.
2. Temporary global adapters are allowed only in declared migration states.
3. Static ESM imports are the target default.
4. Circular dependencies are forbidden.
5. Renderer modules must not own or redefine gameplay state.
6. Scene modules must not redefine success, progression, save, or pause semantics.
7. DOM lifecycle and Pixi scene lifecycle owners must be explicit.
8. Timer and animation-frame owners must be explicit.
9. Browser pointer coordinates are normalized once into logical coordinates.
10. Imports should avoid unnecessary side effects.
11. Leaf modules are migrated before high-coupling orchestration where practical.
12. Strongly coupled source, callers, types, tests, and configuration may be grouped in one coherent work package.
13. Independent mission subsystems are not converted together when the context or rollback boundary becomes unstable.
14. Cutover and cleanup may be separate work packages.

---

## 9. Build contracts

### 9.1 Development path

- The dev server provides fast HMR or reload feedback.
- Ordinary dev-server use does not modify tracked production artifacts.
- The browser starts through an explicit development entry.
- Source diagnostics are available before production packaging.
- Representative gameplay behavior remains equivalent to the current production path.

No numeric reload-time SLA is defined until measured evidence exists.

### 9.2 Production path

- Exact dependency versions are locked.
- Vite output is deterministic within the same environment and inputs.
- Atlas validation runs before final packaging.
- Generated registry drift remains detectable.
- Final output remains one standalone HTML file.
- Runtime network primitives and external resource references remain rejected.
- Build failures fail closed.
- Source-map handling is explicitly decided before production cutover.
- The stable repository command remains reproducible.

### 9.3 Equivalence and determinism

Two different comparisons must not be conflated:

- **Legacy output vs new output:** functional/runtime equivalence is required; byte identity is not expected after bundling changes.
- **New build run A vs new build run B:** byte-identical output is required for the same inputs and environment.

---

## 10. Toolchain policy and verified external status

### 10.1 Policy

- pnpm is the only target package manager for Ocean Rescue.
- npm, yarn, and pnpm lockfiles must not coexist as competing authorities.
- The lockfile is authoritative for exact dependency versions.
- Plugins are added only for a concrete work-package requirement.
- A single-file bundling plugin is not assumed in advance.
- Development dependencies and browser runtime dependencies are distinguished.
- A package upgrade and an architecture cutover are grouped only when they share the same objective and rollback boundary.
- Toolchain changes must not alter gameplay, atlas, or standalone deployment contracts.

### 10.2 External status verified on 2026-08-03

| Tool | Repository state | Official observation | Architecture decision |
|---|---|---|---|
| Vite | Installed as exact devDependency `8.1.5` under `domains/ocean-rescue` | Official release policy lists `vite@8.1` as the regular-patch line; Vite 8.1 was announced 2026-06-23 | Locked to exact 8.1.5 in package metadata; development-server compatibility lane complete (WP-11) |
| PixiJS | Vendored 8.19.0; package metadata pins exact 8.19.0 | Official June 2026 post publishes 8.19.0, while the official versions page still labels 8.18.1 as stable | Keep 8.19.0; import and production cutover is WP-40 |
| TypeScript | Installed as exact devDependency `7.0.2` | Version selection is implementation-time and lockfile-controlled | Locked to exact 7.0.2; `checkJs: false` baseline only |
| pnpm | Pinned `packageManager` `11.17.0`; `pnpm-lock.yaml` authority | Active package manager; exact version now pinned | Exact pin enforced via corepack |
| Node.js | Pinned `.node-version` `24.18.0` | Build-time runtime must use an active supported line | Pinned exact 24.18.0 for build-time only |

Official references:

- Vite releases: `https://vite.dev/releases`
- Vite 8.1 announcement: `https://vite.dev/blog/announcing-vite8-1`
- PixiJS June 2026 update: `https://pixijs.com/blog/june-2026`
- PixiJS versions page: `https://pixijs.com/versions`

This table is evidence for migration planning, not a permanently live “latest version” tracker.

---

## 11. Migration states

State progression follows the implementation plan:

```text
LEGACY_GLOBAL
→ PACKAGE_BOUNDARY_READY
→ DEV_SERVER_COMPAT
→ SHADOW_BUNDLE
→ PRODUCTION_BUNDLE
→ ESM_ENTRY
→ TYPED_MODULES
→ TYPED_CONTROLLERS
→ PACKAGE_PIXI
→ TYPED_SCENES
→ LEGACY_GRAPH_REMOVED
→ MIGRATION_COMPLETE
```

| State | Authoritative source | Production path | Entry condition |
|---|---|---|---|
| `LEGACY_GLOBAL` | Global JavaScript source | Ordered manifest scripts | Initial state |
| `PACKAGE_BOUNDARY_READY` | Package files plus legacy source | Legacy production pipeline | Phase 1 complete |
| `DEV_SERVER_COMPAT` | Legacy source plus dev entry | Legacy production pipeline | Phase 2 complete |
| `SHADOW_BUNDLE` (**current**) | Vite shadow configuration plus legacy source | Legacy path remains authoritative | Phase 3 complete |
| `PRODUCTION_BUNDLE` | Vite application bundle | Standalone builder consumes temporary bundle packaging | Phase 4 complete |
| `ESM_ENTRY` | Canonical ESM entry and import graph | Vite bundle | Phase 5 complete |
| `TYPED_MODULES` | Typed leaf/domain modules | Vite bundle | Phases 6–7 relevant contracts complete |
| `TYPED_CONTROLLERS` | Typed bounded controllers | Vite bundle | Phase 8 complete |
| `PACKAGE_PIXI` | `pixi.js` package import and typed render runtime | Vite bundle | Phase 9 complete |
| `TYPED_SCENES` | Typed ESM scene modules | Vite bundle | Phase 10 complete |
| `LEGACY_GRAPH_REMOVED` | TS/ESM application graph | Finalized standalone packaging | Required Phases 11–13 cleanup complete |
| `MIGRATION_COMPLETE` | Canonical TS/ESM application source | Deterministic standalone HTML | Phase 14 complete |

---

## 12. Dual-path rules

When legacy and new paths coexist:

1. Exactly one production-authoritative path is declared.
2. Shadow paths exist only for parity verification.
3. A shadow path must not independently mutate gameplay state.
4. Silent fallback between old and new paths is forbidden.
5. Parity failure is not converted into success by fallback.
6. Production cutover is one explicit ownership switch.
7. Legacy cleanup may follow later.
8. A rollback path is not removed before zero-reference and rollback-need evidence exists.

---

## 13. Cutover and rollback

Every cutover work package records:

- baseline hashes and runtime evidence;
- changed ownership;
- affected paths;
- verification bundle;
- legacy/new functional-equivalence results;
- new-build determinism results;
- browser evidence;
- rollback procedure;
- retained compatibility path;
- remaining cleanup.

Strongly coupled changes with the same rollback boundary may be grouped.
Changes with different rollback boundaries are separated.

---

## 14. Verification architecture

Verification layers are selected according to work-package risk:

| Layer | Purpose |
|---|---|
| Package/lock integrity | Reproducible dependency graph |
| TypeScript diagnostics | Source contract validation |
| Module graph validation | Import resolution and cycle prevention |
| Focused domain tests | Gameplay/domain behavior |
| Controller lifecycle tests | Phase, timer, pause, and ownership behavior |
| Scene contract tests | Mount, unmount, sync, and pointer intents |
| Browser startup smoke | Real browser startup |
| Representative gameplay flow | Launch, travel, rescue, completion |
| Pointer parity | Browser-to-logical mapping |
| Pause/resume parity | Timer freeze and rearm |
| Renderer backend evidence | WebGL and Canvas behavior |
| Runtime network evidence | No external request |
| Application-bundle determinism | Repeatable Vite output |
| Atlas determinism | Existing asset pipeline stability |
| Standalone artifact drift | Tracked output matches rebuild |
| Target-device performance | Measured only where relevant |

A full suite does not replace the focused verification needed for each changed contract.

---

## 15. Non-goals

- engine replacement;
- gameplay redesign;
- new missions;
- visual redesign;
- atlas pipeline rewrite;
- all-JavaScript-at-once conversion;
- whole `app.js` rewrite;
- backend introduction;
- runtime network imports;
- standalone artifact removal;
- direct editing of generated artifacts;
- unrelated cleanup;
- executing the entire migration in one work package.

---

## 16. Change control

The following changes require revision of this architecture specification:

- renderer-family replacement;
- standalone artifact deprecation;
- backend or runtime-network introduction;
- package-manager replacement;
- asset-representation change;
- gameplay-authority ownership change;
- TypeScript/ESM strategy reversal;
- fundamental reassignment of Node and Python responsibilities.

Ordinary module migration and bounded controller extraction follow the migration plan without requiring a spec revision.
