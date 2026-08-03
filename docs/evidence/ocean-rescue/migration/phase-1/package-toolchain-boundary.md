# Ocean Rescue Package and Node Tooling Boundary

- Captured: 2026-08-03
- Start HEAD: 7359ebb63a790adafb180d56836f414dc262fffd
- Start origin/main: 7359ebb63a790adafb180d56836f414dc262fffd
- Result: PASS
- Package boundary: `domains/ocean-rescue`
- Prior package state: npm bootstrap (`package-lock.json`, npm `node_modules`, `type: module`, Pixi exact `8.19.0`)
- Final package state: pnpm authority (`packageManager`, `pnpm-lock.yaml`, Vite/TypeScript devDependencies)
- Production authority: Legacy global-namespace source + Python standalone pipeline (unchanged)
- Excluded work: production source edits, manifest/asset edits, Pixi import cutover (WP-40), dev-server path (WP-11)

## Pre-existing npm/Pixi bootstrap

The domain previously had an npm package bootstrap at `domains/ocean-rescue`:

- `package.json`: `type: module`, exact `pixi.js@8.19.0`.
- `package-lock.json`: npm lockfile v3 containing the full PixiJS transitive dependency graph.
- `tests/test_ocean_rescue_pixi_toolchain.py`: an npm-lockfile contract that required `package-lock.json` + `lockfileVersion` and prohibited `pnpm-lock.yaml`.

PixiJS was (and remains) vendored as `src/vendor/pixi-8.19.0.min.js` and consumed through the ordered manifest build in production. The package files were bootstrapped tooling only; they did not feed the production artifact.

## Reconciliation decision

The pre-existing npm/Pixi adjacency must not be discarded. WP-10 kept the existing package identity and the exact Pixi pin, and extended the boundary to the canonical pnpm/Node/Vite/TypeScript build-time toolchain. The package-manager authority moved from npm to pnpm. The PixiJS dependency remains pinned in package metadata at `8.19.0`, matching the vendored runtime version.

The existing package JSON and its direct Pixi dependency were carried forward. npm lock resolution was carried forward through `corepack pnpm import` rather than regenerating a fresh dependency graph from scratch.

## Exact version authority

| Tool | Exact pin | License |
|---|---|---|
| Node.js | `24.18.0` (`.node-version`, `engines.node`) | Node.js |
| pnpm (project) | `11.17.0` (`packageManager`, `engines.pnpm`) | MIT |
| Vite | `8.1.5` (devDependency) | MIT |
| TypeScript | `7.0.2` (devDependency) | Apache-2.0 |
| PixiJS | `8.19.0` (dependency) | MIT |

Registry metadata observed (`npm view`): `pixi.js@8.19.0` MIT; `vite@8.1.5` MIT (`node ^20.19.0 || >=22.12.0`); `typescript@7.0.2` Apache-2.0; `pnpm@11.17.0` MIT (`node >=22.13`). All exact values matched the work-package contract, so no automatic version substitution was used.

## npm-to-pnpm lock migration

1. Backed up the npm lockfile to `/tmp/ocean-rescue-package-lock-before-wp10.json`.
2. Recorded the pre-existing PixiJS resolution: `8.19.0` with integrity `sha512-pq1O6emA/GFjjeF+8d3Pb5t7knD8FsnfWGqQcRjYjsqFZ7QdzG1XgjLDUu0DFJRbafjV5+g8iNLFBx0b9649lg==`.
3. Ran `corepack pnpm import`, which generated `pnpm-lock.yaml` from the existing npm resolution.
4. Removed the npm lockfile with `git rm domains/ocean-rescue/package-lock.json`.
5. Removed the ignored npm-generated install tree: `rm -rf domains/ocean-rescue/node_modules`.
6. Completed the lockfile against the reconciled package.json:
   - `corepack pnpm install --lockfile-only`
   - `corepack pnpm install --frozen-lockfile` (run twice).

The generated `pnpm-lock.yaml` preserved the PixiJS integrity value (`sha512-pq1O6emA/GFjjeF+8d3Pb5t7knD8FsnfWGqQcRjYjsqFZ7QdzG1XgjLDUu0DFJRbafjV5+g8iNLFBx0b9649lg==`) and the exact transitive dependency set, confirming `pnpm import` carried the prior npm resolution rather than rederiving it from scratch.

## Package files

- `domains/ocean-rescue/package.json` — identity preserved (`name`, `private`, `version`, `type: module`, `pixi.js: 8.19.0`); `packageManager: pnpm@11.17.0`, `engines`, exact Vite/TypeScript devDependencies added.
- `domains/ocean-rescue/.node-version` — contains exactly `24.18.0`.
- `domains/ocean-rescue/.npmrc` — `engine-strict=true`, `save-exact=true`; no credentials.
- `domains/ocean-rescue/tsconfig.json` — baseline `allowJs: true`, `checkJs: false`, `noEmit: true`, `skipLibCheck: true`; includes `src/**/*.js`; excludes `src/vendor/**` and `src/render-assets.generated.js`.
- `domains/ocean-rescue/pnpm-lock.yaml` — the single lock authority for the boundary.

## Corepack and frozen install

- Node: `24.18.0`.
- Corepack: `0.35.0`.
- Project pnpm via corepack (`packageManager`): `11.17.0`. A bare system `pnpm@10.34.5` remains installed and is not used by project commands.
- `corepack pnpm install --frozen-lockfile` run twice; second run reported "Already up to date" and the lockfile was unchanged.

## TypeScript baseline

`just typecheck-ocean-rescue` (and `just check-ocean-rescue-toolchain`) ran `tsc --project tsconfig.json --noEmit` successfully. The current JavaScript source parses cleanly with the `allowJs` baseline; semantic type checking (`checkJs`) is deliberately disabled for the package boundary stage. No source file was modified.

## Justfile commands

- `check-ocean-rescue-node-version` — PASS (`24.18.0`).
- `check-ocean-rescue-pnpm-version` — PASS (`11.17.0`).
- `sync-ocean-rescue-node` — PASS (frozen install).
- `typecheck-ocean-rescue` — PASS.
- `check-ocean-rescue-toolchain` — PASS (Node + pnpm + frozen install + Vite `8.1.5` + TypeScript `7.0.2` + typecheck).

## License inventory

Direct dependencies: `pixi.js@8.19.0` MIT; devDependencies `vite@8.1.5` MIT, `typescript@7.0.2` Apache-2.0; project pnpm tool `11.17.0` MIT.

Transitive licenses observed via `corepack pnpm licenses list`:

- MIT: 20 packages (`@oxc-project/types`, `@pixi/colord`, `@rolldown/binding-darwin-arm64`, `@rolldown/pluginutils`, `@types/earcut`, `@xmldom/xmldom`, `eventemitter3`, `fdir`, `fsevents`, `gifuct-js`, `ismobilejs`, `js-binary-schema-parser`, `nanoid`, `parse-svg-path`, `picomatch`, `pixi.js`, `postcss`, `rolldown`, `tinyglobby`, `vite`).
- Apache-2.0: `@typescript/typescript-darwin-arm64`, `detect-libc`, `typescript`.
- BSD-3-Clause: `@webgpu/types`, `source-map-js`, `tiny-lru`.
- ISC: `earcut`, `picocolors`.
- MPL-2.0: `lightningcss`, `lightningcss-darwin-arm64`.

All licenses are recognized permissive or permissive-copyleft open-source licenses with no repository policy prohibition. Verdict: PASS.

## Legacy artifact parity

- Before-change SHA-256:
  - `ocean-rescue/index.html` `cfd991d83524db6c7ad225da11ef7a9421300bdf588c4b905bf4e5556f776582`
  - `domains/ocean-rescue/src/render-assets.generated.js` `092673c6784fff9dc4b851fa636c54b5e5f4694ff245539cf1b446ad8228819e`
- After-change SHA-256 (after `just build-ocean-rescue-render-package`): identical.
- `just check-ocean-rescue-drift`: PASS.
- Product path diff (`domains/ocean-rescue/src`, `domains/ocean-rescue/assets`, `ocean-rescue/index.html`, `scripts/ocean_rescue`): empty.

## Browser regression

`uv run pytest -q tests/test_ocean_rescue_wp02_browser_baseline.py`: PASS (1 collected, 1 passed). No committed evidence was changed.

## Verification results

- `python3 -m json.tool` on `package.json` and `tsconfig.json`: PASS.
- `uv run pytest -q tests/test_ocean_rescue_pixi_toolchain.py`: PASS.
- `uv run ruff check` + `uv run ruff format --check` on the reconciled test: PASS.
- Exact versions: Node `v24.18.0`, pnpm `11.17.0`, Vite `vite/8.1.5`, TypeScript `Version 7.0.2`.
- Frozen install (2×): PASS, no lockfile change.
- `just typecheck-ocean-rescue`: PASS.
- `just check-ocean-rescue-toolchain`: PASS.
- Lock authority scan: only `./domains/ocean-rescue/pnpm-lock.yaml` is present.
- `just commit-gate-soft`: BLOCKED by repo-wide pre-existing format debt in six unrelated test files (not introduced by WP-10); WP-10 paths pass `ruff check`/`format --check`.
- `git diff --check`: PASS.

## Acceptance checklist

- [x] 기존 domain-local package boundary 보존
- [x] type: module 보존
- [x] pixi.js 8.19.0 보존
- [x] Node 24.18.0 exact
- [x] packageManager pnpm 11.17.0 exact
- [x] Vite 8.1.5 exact
- [x] TypeScript 7.0.2 exact
- [x] package-lock.json 제거
- [x] pnpm-lock.yaml 생성
- [x] pnpm import로 기존 Pixi resolution을 가능한 범위에서 보존
- [x] npm node_modules 제거 후 pnpm install
- [x] frozen install 2회 안정
- [x] competing lockfile 없음
- [x] TypeScript baseline PASS
- [x] 기존 Pixi toolchain test가 pnpm contract로 갱신
- [x] 중복 package-contract test를 만들지 않음
- [x] Justfile project commands PASS
- [x] license evidence 기록
- [x] production artifact hash 동일
- [x] drift PASS
- [x] WP-02 browser regression PASS
- [x] product source diff 없음
- [x] Architecture 실제 상태 반영
- [x] Plan Phase 1 COMPLETE
- [x] WP-03 계속 pending
- [x] WP-11 계속 NOT_STARTED

## Remaining migration work

- WP-03 target-device performance baseline remains required before WP-21.
- WP-11 (development-server compatibility lane) is the next executable work package.
- WP-40 owns the PixiJS source import and production cutover from the vendored UMD.
- Repo-wide `rig format` (format-mode) debt in six unrelated test files predates WP-10.