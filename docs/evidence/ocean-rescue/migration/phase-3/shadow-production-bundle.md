# Ocean Rescue Deterministic Shadow Production Bundle

- Captured: 2026-08-03
- Implementation base origin/main: `5b2e7c880146cec14568daef72d30a41406fc0fc`
- WP-20 implementation commit: `33f3d43d7e7c83bcddda9edbfdebfe2934f5f33b`
- Publication verification at WP-20 completion: local HEAD and origin/main both pointed to the WP-20 implementation commit
- Result: PASS
- Migration state: `SHADOW_BUNDLE`
- Production authority: Legacy global-namespace source + Python standalone pipeline (unchanged)
- Excluded work: production ownership switch, ESM/TypeScript source conversion, manifest contraction, `pixi.js` package import, vendored Pixi removal (WP-40)

## Objective

Produce a deterministic Vite IIFE application bundle beside the legacy production
path without switching production ownership. The bundle combines exactly the 18
non-vendor legacy global-namespace scripts, in canonical manifest order, while the
vendored Pixi UMD remains a separate prerequisite script loaded before the bundle.

## Toolchain

- Node: `24.18.0` (`.node-version` pin)
- pnpm: `11.17.0` (`packageManager` pin, enforced via corepack)
- Vite: `8.1.5`
- TypeScript: `7.0.2`

## Bundle boundary

- Vendor external: `vendor/pixi-8.19.0.min.js`, namespace `PIXI`, `external: true`
- Application script count: 18
- Application scripts in canonical order:
  `render-assets.generated.js`, `render-runtime.js`, `state.js`, `profile.js`,
  `missions.js`, `gups.js`, `launch.js`, `travel.js`, `terrain.js`,
  `travel-scene.js`, `rescue.js`, `sea-turtle.js`, `sea-turtle-scene.js`,
  `crab.js`, `crab-scene.js`, `young-whale.js`, `mission-success.js`, `app.js`
- Output format: IIFE (`OceanRescueShadowBundle` global, side-effect bootstrap only)
- `pixi.js` package import: excluded (none in config or bundle)
- Vendored Pixi: excluded from the bundle (loaded as a separate classic script)

## Output files

- `dist/ocean-rescue-app.shadow.js` — application bundle
- `dist/index.shadow.html` — generated shadow document
- `dist/shadow-bundle-metadata.json` — deterministic build metadata

`dist/` is git-ignored (untracked). No source maps, hashed filenames, extra
chunks, dynamic imports, or copied public-directory content are emitted.

## Module membership

The build's `generateBundle` validation proved the emitted entry chunk contains
exactly the virtual entry plus each of the 18 non-vendor sources exactly once,
with no vendored Pixi source, no `node_modules/pixi.js` module, and no
unexpected module. `dynamic_import_count == 0`.

## Bundle measurements

- `ocean-rescue-app.shadow.js`
  - bytes: 1,628,949
  - SHA-256: `dc555be1ff5cc33675ee6ba4185dee7cdb2b534bf015cab0802e8074594296a5`
  - gzip bytes: 1,091,617 (gzip: ~1,087 kB)
- `index.shadow.html`: 8,564 bytes, SHA-256 `d34c07a0b8a0bffb8fa4751cd633a5955f7570fe9eda61381b3e2d20d37cc38d`
- `shadow-bundle-metadata.json`: 1,937 bytes, SHA-256 `a321b2d5256029721e3e6b7dd2b018dfc68725775a004061a3235c423f67b223`

Size is recorded as evidence only; no arbitrary size-failure threshold is imposed.

## Determinism (two clean builds)

Build A and build B from identical inputs produced identical relative file lists,
identical raw bytes for every file, and identical SHA-256 values.

- Build A hashes: `dc555be1…` / `d34c07a0…` / `a321b2d5…`
- Build B hashes: `dc555be1…` / `d34c07a0…` / `a321b2d5…`
- Byte identity: identical

## Browser parity (representative flow)

Playwright headless Chromium served `domains/ocean-rescue` as the local HTTP
root and loaded `/dist/index.shadow.html`:

- startup `data-ocean-rescue-ready=true`;
- `PIXI.VERSION == 8.19.0`, WebGL/Canvas renderer, 1280×720 logical canvas;
- profile → mission → GUP → launch → travel;
- pause/resume countdown `3,2,1,Go!` exactly;
- rescue arrival and three rope pointer drags with real domain-state changes;
- mission success/completion recorded;
- zero external-origin requests; zero fetch/XHR/API requests; zero request
  failures; zero page errors; zero console errors; no unexpected warnings.

Document shape:

- exactly two scripts: `/src/vendor/pixi-8.19.0.min.js` then `/dist/ocean-rescue-app.shadow.js`;
- no individual non-vendor source-script requests;
- no Vite dev client (`/@vite/`, `/@fs/`, `/node_modules/.vite`);
- no module scripts, no code splitting;
- `window.PIXI`, `window.OceanRescue.App`, `window.OceanRescue.RenderAssets`
  present; all 18 manifest non-vendor namespaces present.

The browser test loads only the shadow bundle — never the 18 legacy source
scripts alongside it.

## Namespace evidence

Runtime `window.OceanRescue` keys observed: `RenderAssets`, `RenderRuntime`,
`State`, `Profile`, `Missions`, `Gups`, `Launch`, `Travel`, `Terrain`,
`TravelScene`, `Rescue`, `SeaTurtle`, `SeaTurtleScene`, `Crab`, `CrabScene`,
`YoungWhale`, `MissionSuccess`, `App` (plus `TravelProgress`).

## Network / console evidence

- External requests: 0
- API/fetch/XHR requests: 0
- Request failures: 0
- Page errors: 0
- Console errors: 0
- Unexpected warnings: 0

## Legacy hashes before/after

| Path | Before | After |
|---|---|---|
| `ocean-rescue/index.html` | `cfd991d83524db6c7ad225da11ef7a9421300bdf588c4b905bf4e5556f776582` | identical |
| `domains/ocean-rescue/src/build-manifest.json` | `9057557bb341ebcda4cfbe29f189f092874cb1c4ad18d6e8f4bfcb80bfd58300` | identical |
| `domains/ocean-rescue/src/index.template.html` | `85aaf26fe32339f8a5215efbcfb868ae1e2875e64b477cd73577361f58178e4e` | identical |
| `domains/ocean-rescue/src/render-assets.generated.js` | `092673c6784fff9dc4b851fa636c54b5e5f4694ff245539cf1b446ad8228819e` | identical |
| `domains/ocean-rescue/src/vendor/pixi-8.19.0.min.js` | `83b2d7edf27bb77460f5f5f5e25cd73c91b77a53f44c80ac63096d6c0b5cfda7` | identical |

Product-path diff (`domains/ocean-rescue/src`, `domains/ocean-rescue/assets`,
`ocean-rescue/index.html`, `scripts/ocean_rescue`): empty.

## Focused verification results

- `python3 -m json.tool domains/ocean-rescue/package.json` / `tsconfig.json`: PASS
- `corepack pnpm install --frozen-lockfile` (twice, lockfile stable): PASS
- `just check-ocean-rescue-node-version` / `check-ocean-rescue-pnpm-version` /
  `check-ocean-rescue-toolchain` / `typecheck-ocean-rescue`: PASS
- `just build-ocean-rescue-shadow-bundle`: PASS (deterministic)
- `just check-ocean-rescue-shadow-bundle`: PASS (23)
- `uv run pytest -q tests/test_ocean_rescue_wp11_dev_server.py`: PASS (15)
- `uv run pytest -q tests/test_ocean_rescue_wp02_browser_baseline.py`: PASS (1)
- `uv run pytest -q tests/test_ocean_rescue_pixi_toolchain.py`: PASS (21)
- Combined run (WP-20 + WP-11 + WP-02 + pixi toolchain): PASS (60)
- `just check-ocean-rescue-drift`: PASS
- `just check-ocean-rescue-render-package`: PASS
- `ruff check` / `ruff format --check` on touched Python tests: PASS
- `git diff --check`: PASS
- `just commit-gate-hard`: PASS
- `just commit-gate-soft`: FAIL only on unchanged pre-existing Ruff format debt in
  unrelated test files (`test_guardian_event_binding.py`,
  `test_ocean_rescue_profile_choice.py`, `test_ocean_rescue_source_scaffold.py`,
  `test_reward_auth_sync_compat_loaders.py`,
  `test_weekly_word_catalog_enrichment.py`) — identical to the pre-change baseline

## Rollback boundary

Remove `domains/ocean-rescue/vite.shadow.config.ts`, the `build:shadow` package
script, the `tsconfig.json` include entry, the Justfile shadow recipes, and the
WP-20 test file. `dist/` is ignored/untracked and never published. Legacy
production path is untouched and remains authoritative.

## Remaining work

- WP-03 target-device performance baseline required before WP-21.
- WP-21 production application-bundle cutover, blocked until WP-03 is complete.
- WP-40 owns the `pixi.js` package import and production cutover from the
  vendored UMD.
- Pre-existing unrelated Ruff format debt remains unchanged.
