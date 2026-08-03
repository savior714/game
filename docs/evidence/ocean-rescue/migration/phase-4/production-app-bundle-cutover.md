# Ocean Rescue Production Application-Bundle Cutover

- Captured: 2026-08-04
- Implementation base origin/main: `07ee6a03fabcfbda21cc023079e3e9ec38b0a28d`
- WP-21 worktree: `AIDENGAME-OCEAN-RESCUE-PRODUCTION-APP-BUNDLE-CUTOVER-01` (detached at base)
- Result: PASS
- Migration state: `PRODUCTION_APP_BUNDLE`
- Production authority: Vite IIFE application bundle (`--mode production`), vendored Pixi still external
- Rollback path: builder `--mode legacy` reproduces the ordered 18-script artifact byte-for-byte
- Excluded work: ESM/TypeScript source conversion, manifest contraction, `pixi.js` package import, vendored Pixi removal (WP-30/WP-40)

## Objective

Switch standalone production packaging from the ordered application-script
manifest to a single deterministic Vite IIFE application bundle, through an
explicit production ownership switch in the Python standalone builder. The
vendored Pixi UMD remains a separate inline prerequisite script loaded before
the bundle. The legacy ordered-script path is retained behind `--mode legacy`
for rollback.

## Toolchain

- Node: `24.18.0` (`.node-version` pin)
- pnpm: `11.17.0` (`packageManager` pin, enforced via corepack)
- Vite: `8.1.5`
- TypeScript: `7.0.2`

## Ownership switch

The standalone builder now requires an explicit mode:

```bash
uv run python scripts/ocean_rescue/build_single_html.py --mode production \
  --manifest domains/ocean-rescue/src/build-manifest.json \
  --output ocean-rescue/index.html \
  --bundle domains/ocean-rescue/dist/ocean-rescue-app.js \
  --metadata domains/ocean-rescue/dist/production-bundle-metadata.json
```

- `--mode production` consumes the Vite bundle plus production metadata and
  validates the bundle boundary fail-closed (metadata schema/state/format,
  minifier, sourcemap, dynamic-import count, target, output files,
  vendor-external contract, module membership, bundle SHA, size).
- `--mode legacy` reads the manifest in the original ordered-script way and is
  never selected silently; it reproduced the pre-cutover artifact byte-for-byte.
- `just build-ocean-rescue` and `just build-ocean-rescue-render-package` run the
  Vite production build and then the builder in production mode.
- `just build-ocean-rescue-legacy-rollback` exercises the legacy path explicitly.

## Bundle boundary

- Vendor external: `vendor/pixi-8.19.0.min.js`, namespace `PIXI`, `external: true`
- Application script count: 18
- Application scripts in canonical order:
  `render-assets.generated.js`, `render-runtime.js`, `state.js`, `profile.js`,
  `missions.js`, `gups.js`, `launch.js`, `travel.js`, `terrain.js`,
  `travel-scene.js`, `rescue.js`, `sea-turtle.js`, `sea-turtle-scene.js`,
  `crab.js`, `crab-scene.js`, `young-whale.js`, `mission-success.js`, `app.js`
- Output format: IIFE, side-effect bootstrap only (no export value bound to a
  global; the bundle attaches the global `window.OceanRescue` namespace)
- `pixi.js` package import: excluded (none in config or bundle)
- Vendored Pixi: excluded from the bundle (inline script block before the bundle)

## Output files

- `dist/ocean-rescue-app.js` — application bundle
- `dist/production-bundle-metadata.json` — deterministic build metadata
- `ocean-rescue/index.html` — tracked standalone production artifact

`dist/` is git-ignored (untracked). No source maps, hashed filenames, extra
chunks, dynamic imports, or copied public-directory content are emitted. The
inline vendored Pixi block retains its untouched upstream `sourceMappingURL`
comment; the bundle itself carries no source map reference.

## Module membership

The build's `generateBundle` validation and the builder's boundary validation
proved the emitted entry chunk contains exactly the virtual entry plus each of
the 18 non-vendor sources exactly once, with no vendored Pixi source, no
`node_modules/pixi.js` module, and no unexpected module.
`dynamic_import_count == 0`.

## Bundle measurements

- `ocean-rescue-app.js`
  - bytes: 1,628,949
  - SHA-256: `dc555be1ff5cc33675ee6ba4185dee7cdb2b534bf015cab0802e8074594296a5`
  - gzip bytes: 1,091,617 (gzip: ~1,087 kB)
- `production-bundle-metadata.json`: 1,937 bytes,
  SHA-256 `a321b2d5256029721e3e6b7dd2b018dfc68725775a004061a3235c423f67b223`
- `ocean-rescue/index.html` (production artifact): 2,466,564 bytes,
  SHA-256 `03496d35fee11ad6821c0e5cbf2b6b149eaab543b1d819e64c6dafbfefbc6d7c`

Size is recorded as evidence only; no arbitrary size-failure threshold is imposed.

## Artifact shape

The production document contains exactly two inline `<script>` blocks in order:
the vendored Pixi UMD (block 0) then the application bundle (block 1). No
external, `src`-attributed, or module scripts are present. `data-ocean-rescue-ready`
marker and the completion-action contract are preserved.

## Determinism (two clean builds)

The WP-21 focused suite builds the bundle twice from identical inputs and
asserts identical relative file lists, identical raw bytes, and identical
SHA-256 values for every emitted file, plus identical final artifacts.

## Browser parity (representative flow)

Playwright headless Chromium served `domains/ocean-rescue` as the local HTTP
root and loaded `/ocean-rescue/index.html` (the production artifact):

- startup `data-ocean-rescue-ready=true`;
- `PIXI.VERSION == 8.19.0`, WebGL/Canvas renderer, 1280×720 logical canvas;
- profile → mission → GUP → launch → travel;
- pause/resume countdown `3,2,1,Go!` exactly;
- rescue arrival and three rope pointer drags with real domain-state changes;
- mission success/completion recorded;
- zero external-origin requests; zero fetch/XHR/API requests; zero request
  failures; zero page errors; zero console errors; no unexpected warnings.

Document shape:

- exactly two inline scripts: vendored Pixi then the app bundle;
- no individual non-vendor source-script requests;
- no Vite dev client (`/@vite/`, `/@fs/`, `/node_modules/.vite`);
- no module scripts, no code splitting;
- `window.PIXI`, `window.OceanRescue.App` present.

## Namespace evidence

Runtime `window.OceanRescue` keys observed: `RenderAssets`, `RenderRuntime`,
`State`, `Profile`, `Missions`, `Gups`, `Launch`, `Travel`, `Terrain`,
`TravelScene`, `Rescue`, `SeaTurtle`, `SeaTurtleScene`, `Crab`, `CrabScene`,
`YoungWhale`, `MissionSuccess`, `App` (plus `TravelProgress`).

## Legacy rollback verification

The `--mode legacy` path is verified to reproduce the pre-cutover ordered
artifact. Legacy output (18 ordered script blocks) is built and compared against
the production output to prove the rollback boundary restores the previous
authoritative path.

## Network / console evidence

- External requests: 0
- API/fetch/XHR requests: 0
- Request failures: 0
- Page errors: 0
- Console errors: 0
- Unexpected warnings: 0

## Product-path changes (tracked)

| Path | Change |
|---|---|
| `ocean-rescue/index.html` | regenerated production artifact (2,466,564 bytes, 2 inline blocks) |
| `scripts/ocean_rescue/build_single_html.py` | `--mode production/legacy`, atomic write, fail-closed boundary validation |
| `domains/ocean-rescue/package.json`, `tsconfig.json`, `vite.shadow.config.ts` | production build wired |
| `domains/ocean-rescue/vite.bundle.ts`, `vite.production.config.ts` | shared bundle algorithm + narrow production config (new) |
| `Justfile` | `build-ocean-rescue` / render-package in production mode; legacy-rollback recipes; drift in production mode |

Untouched: `domains/ocean-rescue/src/build-manifest.json`,
`domains/ocean-rescue/src/index.template.html`,
`domains/ocean-rescue/src/render-assets.generated.js`,
`domains/ocean-rescue/src/vendor/pixi-8.19.0.min.js`.

## Focused verification results

- `just build-ocean-rescue`: PASS (toolchain, pixi vendor, atlases, registry,
  Vite production build, packaging)
- `uv run pytest -q tests/test_ocean_rescue_wp21_production_bundle_cutover.py`: PASS
- `uv run pytest -q tests/test_ocean_rescue_wp03_scope_decision.py`: PASS
- `uv run pytest -q tests/test_ocean_rescue_artifact_drift.py`: PASS
- `uv run pytest -q tests/test_ocean_rescue_render_packaging.py`: PASS
- `uv run pytest -q tests/test_ocean_rescue_wp20_shadow_bundle.py`: PASS
- `uv run pytest -q tests/test_ocean_rescue_source_scaffold.py`: PASS
- `uv run pytest -q tests/test_ocean_rescue_builder.py`: PASS
- `just check-ocean-rescue-drift`: PASS
- `ruff check` / py_compile on touched Python: PASS

## Rollback boundary

Restore the legacy ordered-script manifest ordering and previous builder input:
run the builder with `--mode legacy` (reproduced byte-for-byte), or revert this
worktree (production paths plus builder). `dist/` is ignored/untracked and never
published. The legacy path remains available via `--mode legacy`.

## Remaining work

- WP-30 canonical ESM entry and module graph (next executable work package).
- WP-03A target-device smoke remains mandatory before MVP release.
- WP-40 owns the `pixi.js` package import and removal of the vendored UMD.
- Pre-existing unrelated Ruff format debt remains unchanged.
