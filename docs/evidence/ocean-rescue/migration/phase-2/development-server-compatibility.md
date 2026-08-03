# Ocean Rescue Development-Server Compatibility Lane

- Captured: 2026-08-03
- Start HEAD: a5536d256c997d3ef74c60b3b87323fa87fd262e
- Start origin/main: a5536d256c997d3ef74c60b3b87323fa87fd262e
- Result: PASS
- Package boundary: `domains/ocean-rescue`
- Dev-server state: `DEV_SERVER_COMPAT`
- Production authority: Legacy global-namespace source + Python standalone pipeline (unchanged)
- Excluded work: production bundle, ESM conversion, TypeScript source conversion, manifest removal, Pixi import cutover (WP-40)

## Objective

Run the existing global-namespace source through a Vite development server (development only)
without changing the production pipeline. The dev server derives the canonical script order from
`src/build-manifest.json` and `src/index.template.html`, so there is no second source of truth for
script ordering.

## Dev entry

`domains/ocean-rescue/index.dev.html` is a thin development-only entry. It contains exactly one
placeholder comment `<!-- OCEAN_RESCUE_DEV_ENTRY -->` and no game DOM. The Vite plugin replaces the
CSS/scripts placeholder comments in the served HTML with the derived stylesheet link and ordered
script tags. The entry does not load any runtime state on its own.

## Vite configuration

`domains/ocean-rescue/vite.config.ts`:

- `transformIndexHtml` with `order: "pre"` derives the canonical document from
  `src/build-manifest.json` + `src/index.template.html` and replaces
  `<!-- OCEAN_RESCUE_CSS -->` / `<!-- OCEAN_RESCUE_SCRIPTS -->`.
- Scripts remain classic global scripts (no `type="module"`, no ESM conversion, no runtime manifest
  fetch, vendored Pixi unchanged).
- Path-safety guard rejects URL schemes, `//`, `..`, and escapes from the src root for every
  manifest entry.
- Full reload: the classic scripts are outside Vite's ESM HMR graph, so `handleHotUpdate` never
  fires. `configureServer` registers `server.watcher.on("all", ...)` and sends
  `{ type: "full-reload" }` for relevant source changes under the src root.
- Server: host `127.0.0.1`, port `5173`, `strictPort` (config plus `just dev-ocean-rescue` flags).

## Package files

- `package.json` — added `dev` script (`vite --config vite.config.ts --host 127.0.0.1 --port 5173
  --strictPort`) and exact devDependency `@types/node: 24.13.3`.
- `pnpm-lock.yaml` — adds `@types/node@24.13.3` + `undici-types@7.18.2` (both MIT); Vite resolves as
  `8.1.5(@types/node@24.13.3)`.
- `tsconfig.json` — `include` adds `vite.config.ts`.

## Justfile commands

- `dev-ocean-rescue` — starts the development server (`http://127.0.0.1:5173/index.dev.html`).
- `check-ocean-rescue-dev-server` — runs the WP-11 dev-server test contracts.

## Server-derived HTML contract

Served `/index.dev.html` matches the production `index.template.html` structure:

- stylesheet link `style.css` before scripts;
- exactly 19 classic scripts in canonical manifest order (first `vendor/pixi-8.19.0.min.js`, last
  `app.js`);
- no `fetch(/src/build-manifest.json)` runtime call;
- no `<script type="module">` runtime bootstrap.

## Browser parity (representative flow)

Playwright headless Chromium through the Vite dev server (`/index.dev.html`):

- app startup to `data-ocean-rescue-ready=true`;
- PixiJS `8.19.0` WebGL/Canvas renderer active;
- profile → mission → GUP → launch → travel;
- pause/resume with countdown `3,2,1,Go!`;
- three rope pointer drags and mission completion;
- `window.PIXI`, `window.OceanRescue.App`, `window.OceanRescue.RenderAssets` present;
- zero external/API network requests; zero page/console errors.

## Full reload on source change

A relevant source file under the src root (`__wp11_reload_trigger__.js`) is written while the page is
loaded with an `window.__wp11ReloadMarker`. The server watcher fires, sends `{ type: "full-reload" }`,
and the page reloads (marker cleared, app becomes ready again). The reload was confirmed by marker
polling rather than `framenavigated` (frame identity changes on reload are not a reliable signal).

## Verification results

- `python3 -m json.tool` on `package.json` and `tsconfig.json`: PASS.
- Frozen install `corepack pnpm install --frozen-lockfile` run twice; second run "Already up to
  date", no lockfile change.
- `just check-ocean-rescue-node-version` / `check-ocean-rescue-pnpm-version` /
  `check-ocean-rescue-toolchain` / `typecheck-ocean-rescue`: PASS.
- `just check-ocean-rescue-drift`: PASS (`test_ocean_rescue_artifact_drift.py`).
- `just check-ocean-rescue-render-package`: PASS (`render_packaging` + `artifact_drift`).
- `uv run pytest -q tests/test_ocean_rescue_pixi_toolchain.py`: PASS (21).
- `uv run pytest -q tests/test_ocean_rescue_wp11_dev_server.py`: PASS (15).
- `uv run pytest -q tests/test_ocean_rescue_wp02_browser_baseline.py`: PASS (1).
- Combined run (pixi_toolchain + WP-11 + WP-02): PASS (37).
- `ruff check` + `ruff format --check` on the three touched test files: PASS.
- `git diff --check`: PASS.

## Legacy artifact parity

- Before-change SHA-256:
  - `ocean-rescue/index.html` `cfd991d83524db6c7ad225da11ef7a9421300bdf588c4b905bf4e5556f776582`
  - `domains/ocean-rescue/src/render-assets.generated.js` `092673c6784fff9dc4b851fa636c54b5e5f4694ff245539cf1b446ad8228819e`
  - `domains/ocean-rescue/src/build-manifest.json` `9057557bb341ebcda4cfbe29f189f092874cb1c4ad18d6e8f4bfcb80bfd58300`
  - `domains/ocean-rescue/src/index.template.html` `85aaf26fe32339f8a5215efbcfb868ae1e2875e64b477cd73577361f58178e4e`
- After-change SHA-256: identical.
- `just check-ocean-rescue-drift`: PASS.
- Product path diff (`domains/ocean-rescue/src`, `domains/ocean-rescue/assets`, `ocean-rescue/index.html`, `scripts/ocean_rescue`): empty.

## Acceptance checklist

- [x] 개발 전용 HTML entry 존재
- [x] 최소 Vite dev configuration
- [x] manifest에서 script order를 결정적으로 재사용/유도
- [x] production pipeline 미변경
- [x] `just dev-ocean-rescue` command
- [x] 대표 flow browser parity PASS
- [x] pause/resume parity PASS
- [x] console/network clean
- [x] full-reload on source change PASS
- [x] legacy artifact hash 동일
- [x] drift PASS
- [x] WP-02 regression PASS
- [x] Vite entry는 개발 전용 (production artifact에 미반영)
- [x] Plan Phase 2 COMPLETE
- [x] WP-03 계속 NOT_STARTED
- [x] WP-20이 다음 work package

## Remaining migration work

- WP-03 target-device performance baseline remains required before WP-21.
- WP-20 (shadow production bundle) is the next executable work package.
- WP-40 owns the PixiJS source import and production cutover from the vendored UMD.
- Repo-wide pre-existing format debt in unrelated test files predates WP-10 (documented in phase-1).
