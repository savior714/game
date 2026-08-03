# Ocean Rescue Static Build Baseline

- **Captured:** 2026-08-03T13:31:46+09:00
- **Start HEAD:** 59e3011b9a29451816292a9128a1aaa36faeb8f9
- **Start origin/main:** 2ef661317b224f594f0fe9ebf2aeecac7b1227cb
- **Result:** PASS
- **Scope:** WP-01 Static Build Baseline
- **Excluded scope:** WP-02 Browser Functional Parity, WP-03 Target Device Performance

## Environment

- **Date:** 2026-08-03T13:31:46+09:00
- **OS:** macOS 26.6 (25G72)
- **Arch:** arm64
- **Python:** 3.14.4
- **uv:** 0.11.7
- **just:** 1.49.0
- **Node:** v24.18.0
- **Chrome:** 150.0.7871.188
- **Chromium:** NOT_FOUND

## Manifest graph

```json
{
  "total": 19,
  "vendor": 1,
  "generated_assets": 1,
  "application": 17,
  "duplicate_namespaces": [],
  "forward_or_missing_dependencies": []
}
```

Entries (index → namespace → kind → depends_on → has_sha256):

| Index | Namespace | Kind | depends_on | sha256 |
|-------|-----------|------|------------|--------|
| 0 | PIXI | vendor | [] | yes |
| 1 | OceanRescue.RenderAssets | generated-assets | [] | yes |
| 2 | OceanRescue.RenderRuntime | app | [PIXI, OceanRescue.RenderAssets] | no |
| 3 | OceanRescue.State | app | [] | no |
| 4 | OceanRescue.Profile | app | [] | no |
| 5 | OceanRescue.Missions | app | [] | no |
| 6 | OceanRescue.Gups | app | [] | no |
| 7 | OceanRescue.Launch | app | [] | no |
| 8 | OceanRescue.Travel | app | [] | no |
| 9 | OceanRescue.Terrain | app | [] | no |
| 10 | OceanRescue.TravelScene | app | [OceanRescue.RenderRuntime] | no |
| 11 | OceanRescue.Rescue | app | [] | no |
| 12 | OceanRescue.SeaTurtle | app | [] | no |
| 13 | OceanRescue.SeaTurtleScene | app | [OceanRescue.RenderRuntime, OceanRescue.SeaTurtle] | no |
| 14 | OceanRescue.Crab | app | [] | no |
| 15 | OceanRescue.CrabScene | app | [OceanRescue.RenderRuntime, OceanRescue.Crab] | no |
| 16 | OceanRescue.YoungWhale | app | [] | no |
| 17 | OceanRescue.MissionSuccess | app | [] | no |
| 18 | OceanRescue.App | app | [14 deps] | no |

**Duplicate namespaces:** 0
**Forward/missing dependencies:** 0

## Initial hashes

```
61b28b24d2c49836cc6ea0dabb530d612c7e85155706f9180f0a233150ba94f0  ocean-rescue/index.html
092673c6784fff9dc4b851fa636c54b5e5f4694ff245539cf1b446ad8228819e  domains/ocean-rescue/src/render-assets.generated.js
83b2d7edf27bb77460f5f5f5e25cd73c91b77a53f44c80ac63096d6c0b5cfda7  domains/ocean-rescue/src/vendor/pixi-8.19.0.min.js
```

Generated files:

```
6de43eb8e56e944fadb22d6d2b247b118e7f2346b27a921bae6dbdf51f73c071  domains/ocean-rescue/assets/generated/atlas-manifest.json
9c75969c3cbc6b037604dfbef6d81da28c76a26b2242f7070182c0aeb2bfadd9  domains/ocean-rescue/assets/generated/characters/characters-0.json
b9ad42ac939bb3dd860c523b42a1d77b915b9c92d50dc6c0e600201f126f4546  domains/ocean-rescue/assets/generated/characters/characters-0.png
d27ee6522bcb61eef70a7ab42de7d6694ae92d1fd9db4a6bfe7a723c5d8ee3bc  domains/ocean-rescue/assets/generated/effects-ui/effects-ui-0.json
594e6eafac1c6a2a492afad9459d1acdd084f7b359fa6e3c93201043ab2d753a  domains/ocean-rescue/assets/generated/effects-ui/effects-ui-0.png
6a289c5b258880597e129260ce86a5c3c1f89e82df46f337ce6177df668a8dad  domains/ocean-rescue/assets/generated/pixi-assets-manifest.json
cf2ef1f330a9da6859d3539f6145dd1776428273acc6867afd2832a196410daf  domains/ocean-rescue/assets/generated/scene/scene-0.json
bc8de21db85ba7bdee653bf2b85f05e98e39f04a05f0a5ca7d85c095db9db16d  domains/ocean-rescue/assets/generated/scene/scene-0.png
```

## Focused validation

### check-ocean-rescue-atlases
- **Command:** `uv run pytest -q tests/test_ocean_rescue_atlas_pipeline.py`
- **Result:** PASS (all tests passed)

### check-ocean-rescue-render-package
- **Command:** `uv run pytest -q tests/test_ocean_rescue_render_packaging.py tests/test_ocean_rescue_artifact_drift.py`
- **Result:** PASS (all tests passed)

### check-ocean-rescue-drift
- **Command:** `uv run pytest tests/test_ocean_rescue_artifact_drift.py -q`
- **Result:** PASS (all tests passed)

## Render-package determinism

### Run A
- **Command:** `just build-ocean-rescue-render-package`
- **Artifacts:**
  - `61b28b24d2c49836cc6ea0dabb530d612c7e85155706f9180f0a233150ba94f0  ocean-rescue/index.html`
  - `092673c6784fff9dc4b851fa636c54b5e5f4694ff245539cf1b446ad8228819e  domains/ocean-rescue/src/render-assets.generated.js`

### Run B
- **Command:** `just build-ocean-rescue-render-package`
- **Artifacts:**
  - `61b28b24d2c49836cc6ea0dabb530d612c7e85155706f9180f0a233150ba94f0  ocean-rescue/index.html`
  - `092673c6784fff9dc4b851fa636c54b5e5f4694ff245539cf1b446ad8228819e  domains/ocean-rescue/src/render-assets.generated.js`

### Comparison
- **Run A vs Run B:** IDENTICAL (byte-identical)
- **Generated A vs Generated B:** IDENTICAL

## HEAD artifact drift

- **Command:** `git diff --exit-code -- domains/ocean-rescue/src/render-assets.generated.js domains/ocean-rescue/assets/generated ocean-rescue/index.html`
- **Exit code:** 0
- **Result:** No drift — rebuilt output matches tracked HEAD exactly

## Static standalone/network contract

Verified via existing `test_ocean_rescue_render_packaging.py`:

| Check | Result |
|-------|--------|
| No `<script src=...>` external scripts | PASS |
| No `<link rel="stylesheet" href=...>` | PASS |
| No dynamic `import()` | PASS |
| No `asset://` references | PASS |
| External resources count = 0 (Chrome headless) | PASS |
| Two clean builds byte-identical | PASS |
| Tracked artifact matches clean rebuild | PASS |
| Single deployable file | PASS |
| Script ordering: vendor → registry → app | PASS |
| Manifest script count matches artifact | PASS |

**Note on PixiJS internal `fetch()` calls:** The vendored PixiJS library contains `fetch()` calls for texture loading infrastructure. These are internal loader calls that load from the same origin (local resources). The CDN URL strings (basis/ktx transcoders) are configuration constants inside PixiJS, not runtime requests for this game.

## Final product-path diff

```
git diff -- domains/ocean-rescue/src domains/ocean-rescue/assets ocean-rescue/index.html
```

Result: EMPTY (no product changes)

## Acceptance checklist

- [x] JSON parse success
- [x] Duplicate namespaces: 0
- [x] Forward/missing dependencies: 0
- [x] Pre-build hashes recorded
- [x] Clean state confirmed (exit code 0)
- [x] Atlas validation: PASS
- [x] Render-package validation: PASS
- [x] Drift validation: PASS
- [x] Run A vs Run B: byte-identical
- [x] HEAD vs Run B: no drift
- [x] Static contract: no external resources
- [x] Product path diff: empty

## Blockers and remaining evidence

None. WP-01 is PASS.
