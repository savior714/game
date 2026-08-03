# Ocean Rescue Canonical ESM Entry and Module Graph

- Captured: 2026-08-04
- Implementation base origin/main: `c1ca664c6be341ce4196d36e249b423ac76bd032`
- Result: PASS
- Migration state: `PHASE_6_READY`
- Production authority: canonical ESM entry `src/main.js` bundles through the
  Vite IIFE application bundle; vendored Pixi stays external
- Application dependency authority: ESM import graph owned by `src/main.js`
- Canonical manifest: contracted to template/styles/vendor/generated/entry/assets
- Legacy rollback manifest: `build-manifest.legacy.json` (immutable ordered set)
- Dev lane: one classic vendored Pixi script + one module `src/main.js`
- Rollback path: `just rollback-ocean-rescue-to-legacy` + `--mode legacy` consume
  the legacy manifest to reproduce the ordered 19-script artifact
- Excluded work: all-module TypeScript conversion, controller decomposition,
  `pixi.js` package import, vendored Pixi removal (WP-31A/WP-40)

## Objective

WP-30 establishes one canonical ESM application entry (`src/main.js`) and makes
the ESM import graph authoritative for application dependency ordering, replacing
the ordered application-script list in `build-manifest.json` and the legacy
`depends_on` graph. Temporary compatibility adapters in `src/esm/` side-effect
load the unchanged legacy IIFE implementations and re-export their
`window.OceanRescue.*` namespaces so neither the legacy source files nor the
global namespace are modified this package.

## Toolchain

- Node: `24.18.0` (`.node-version` pin)
- pnpm: `11.17.0` (`packageManager` pin, enforced via corepack)
- Vite: `8.1.5`
- TypeScript: `7.0.2`

## Canonical entry and adapter graph

- `src/main.js` imports exactly `./esm/app.js`.
- `src/esm/*.js` provides 18 compatibility adapters:
  render-assets, render-runtime, state, profile, missions, gups, launch, travel,
  terrain, travel-scene, rescue, sea-turtle, sea-turtle-scene, crab, crab-scene,
  young-whale, mission-success, app.
- Every adapter:
  - uses only static relative `import "…"` statements;
  - imports its direct application dependency adapters explicitly (derived from
    the actual source reads, not the manifest `depends_on`);
  - side-effect-imports exactly one legacy implementation file;
  - reads `window.OceanRescue.<Name>` and throws when the namespace is absent;
  - exports that namespace.
- The graph reachable from `src/main.js` is acyclic, single-rooted, and covers
  each legacy implementation file exactly once. `src/main.js` plus 18 adapters
  plus the 18 legacy implementation files (including `render-assets.generated.js`)
  produce 38 bundled modules.
- The legacy IIFE files and their `window.OceanRescue.*` assignments were not
  modified in this package.

## Manifest ownership split

The canonical manifest was contracted:

```json
{
  "template": "index.template.html",
  "styles": ["style.css"],
  "vendor": { "file": "vendor/pixi-8.19.0.min.js", "namespace": "PIXI", "kind": "vendor", "sha256": "…" },
  "generated": { "file": "render-assets.generated.js", "sha256": "…" },
  "entry": "main.js",
  "assets": []
}
```

The ordered 19-entry script list (1 vendored Pixi + 18 application scripts) is
preserved byte-for-byte as `build-manifest.legacy.json` and is the only rollback
authority for `--mode legacy` packaging.

## Production lane

- `vite.bundle.ts` no longer synthesizes a virtual ordered entry. The real
  `src/main.js` is the lib entry; the plugin walks the static relative import
  graph, verifies single chunk / IIFE / zero dynamic imports, keeps vendored Pixi
  external, excludes `node_modules/pixi.js`, requires every graph module exactly
  once, and emits deterministic metadata recording `entry`, vendor, the legacy
  application-script membership, expected namespaces, and actual module files.
- `vite.production.config.ts` and `vite.shadow.config.ts` call the shared
  `createBundleLaneConfig` with a real entry path.
- `build_single_html.py --mode production` loads the contracted canonical
  manifest, validates the `vendor` and `generated` pins, cross-checks the bundle
  metadata against the legacy manifest membership, and packages vendor + bundle
  into the two-inline-block standalone artifact.
- Determinism: two clean production builds are byte-identical (bundle + packaged
  artifact).

## Dev lane

- `vite.config.ts` serves one classic vendored Pixi script followed by one
  module `src/main.js` (no 18 classic script tags). The template markers,
  manifest/template validation, and relevant-source full-reload behavior are
  retained.

## Verification

- `tests/test_ocean_rescue_wp30_esm_entry_module_graph.py` — 16 passing checks:
  single canonical root, adapter shape (static relative imports, exactly-one
  legacy side-effect import, namespace guard + export), explicit direct
  dependency edges, graph acyclicity, full reachability, exactly-once legacy
  coverage, static-relative-only imports, and canonical/legacy manifest split.
- WP-21 production-bundle cutover suite: 19 passing (metadata schema updated to
  entry/legacy membership, two-block standalone shape, rollback to legacy
  manifest, browser parity).
- WP-20 shadow bundle: 24 passing (entry/metadata updates, shadow browser parity).
- WP-11 dev-server lane: 15 passing (module main.js entry, classic Pixi, browser
  parity, full reload).
- `tsc --project tsconfig.json --noEmit`: exit 0.
- Artifact drift, render packaging, source scaffold, builder, and authored-scene
  contract suites updated to the new manifest ownership and all pass.

Pre-existing unrelated failures (unchanged by WP-30):
`test_git_workflow_guardrails::test_justfile_typecheck_has_resilient_fallback_and_exclusions`
and `test_ocean_rescue_pixi_backend_smoke_contract::test_lock_pinned_pixi`.

## Rollback

- Operational rollback: `just rollback-ocean-rescue-to-legacy` runs the legacy
  pipeline against `build-manifest.legacy.json` and rewrites the tracked
  `ocean-rescue/index.html` to the exact ordered 19-script artifact.
- Proof-only: `just build-ocean-rescue-legacy-proof` writes
  `dist/legacy-rollback.html` without touching the canonical artifact.
- Source rollback boundary: revert to the pre-WP-30 `vite.bundle.ts` virtual
  ordered entry and the full ordered `build-manifest.json`.
