# Ocean Rescue Browser Functional Baseline

- **Captured:** 2026-08-03
- **Start HEAD:** `d1ec0134f29dc85176238b044fe8633dd37eb64b`
- **Start origin/main:** `d1ec0134f29dc85176238b044fe8633dd37eb64b`
- **Result:** PASS
- **Scope:** WP-02 Browser Functional Parity Baseline
- **Excluded scope:** WP-01 Static Build, WP-03 Target Device Performance, production source changes

## Harness And Commands

- **Test:** `tests/test_ocean_rescue_wp02_browser_baseline.py`
- **Browser:** Playwright Chromium `151.0.7922.34`, headless
- **Viewport:** `1280x720`
- **Locale:** `ko-KR`
- **Timezone:** `Asia/Seoul`
- **Local HTTP server:** Python `SimpleHTTPRequestHandler` on `127.0.0.1` with an OS-assigned free port
- **Evidence write policy:** committed JSON is written only with `OCEAN_RESCUE_WP02_WRITE_EVIDENCE=1`; ordinary pytest runs do not write evidence

Commands executed:

```bash
uv run pytest --collect-only -q tests/test_ocean_rescue_wp02_browser_baseline.py
# 1 test collected

uv run pytest -q tests/test_ocean_rescue_wp02_browser_baseline.py
# 1 passed

OCEAN_RESCUE_WP02_WRITE_EVIDENCE=1 uv run pytest -q tests/test_ocean_rescue_wp02_browser_baseline.py
# 1 passed; evidence JSON updated
```

## Startup And Renderer

| Property | Observed value |
|---|---|
| Ready attribute | `data-ocean-rescue-ready=true` |
| Canvas | present, backing `1280x720` |
| Canvas CSS rectangle | `left=0`, `top=0`, `width=1280`, `height=720` |
| Device pixel ratio | `1` |
| PixiJS | `8.19.0` |
| Renderer runtime | `ready` |
| Selected renderer backend | `webgl` |
| Logical coordinate contract | `1280x720` |

The selected backend was read from the production runtime diagnostic
`data-render-backend`. Canvas fallback execution was not claimed or tested by
this work package.

## Required Gameplay Flow

The observed phase sequence was:

```text
PROFILE
→ MISSION_SELECT
→ GUP_SELECT
→ LAUNCH
→ TRAVEL
→ RESCUE_ARRIVAL
→ SEA_TURTLE_RESCUE
→ MISSION_SUCCESS
```

- Profile: selected `arctic-fox` and continued from a fresh browser context.
- Mission: selected `sea-turtle`.
- GUP: selected `gup-x`.
- Launch: completed through the production skip button.
- Travel: started with `data-travel-runtime=active`.
- Arrival: public `OceanRescue.Travel.step(50, 1)` was called 989 times, producing `distance=6002.088`; the production animation frame then observed the real `ArrivalDistance` condition and entered `data-rescue-phase=site-transition`.
- Rescue arrival: site transition and tutorial were observed; the production “Tap anywhere to skip” interaction entered `data-rescue-phase=active`.
- Sea-turtle scene: `data-sea-turtle-scene=active`, `data-sea-turtle-active=true`.
- Rope release: `rope-1` advanced to `rope-2`, `rope-2` advanced to `rope-3`, and `rope-3` completed the turtle. Final completed count was `3`.
- Mission success: production success presentation was observed, followed by the production narration interactions and `data-mission-completion-recorded=true`.
- Success UI: mission-complete card was visible with title `Sea Turtle Rescue`.

The travel helper used only the existing public stepping API. It did not assign
travel state or call an arrival/success handler directly.

## Pause And Resume

Pause was activated during `TRAVEL`; the overlay was visible and
`data-pause-active=true`. A `MutationObserver` captured the full production
countdown sequence:

```json
["3", "2", "1", "Go!"]
```

After the countdown, `data-pause-active=false` and the overlay was dismissed.

## Pointer Mapping And Rescue Input

Mapping used the production canvas rectangle and the logical formula:

```text
logical_x = (client_x - rect.left) / rect.width × 1280
logical_y = (client_y - rect.top) / rect.height × 720
```

Tolerance was `0.5` logical pixels. Numerical assertions passed for:

| Point | Expected logical coordinates | Observed client coordinates |
|---|---:|---:|
| Logical center | `(640, 360)` | `(640, 360)` |
| Top-left safe point | `(10, 10)` | `(10, 10)` |
| Bottom-right safe point | `(1270, 710)` | `(1270, 710)` |
| Rope 1 start | `(760, 300)` | `(760, 300)` |
| Rope 1 end | `(1040, 330)` | `(1040, 330)` |

Rope endpoints were read from the production `OceanRescue.SeaTurtle.Ropes`
geometry, not guessed. Each rope used browser `page.mouse` pointer down,
multiple pointer moves along the rope, and pointer up. The capture observer
recorded all three event types for all three drags. Domain evidence showed:

| Drag | Active rope before | Active rope after | Completed count | Domain state changed |
|---|---|---|---:|---|
| Rope 1 | `rope-1` | `rope-2` | 1 | true |
| Rope 2 | `rope-2` | `rope-3` | 2 | true |
| Rope 3 | `rope-3` | none | 3 | true |

Therefore both numerical mapping and the browser pointer-events-to-domain-state
path passed. The stale always-true mapping expression is removed.

## Network And Console

Network evidence from the final run:

| Metric | Count |
|---|---:|
| Total requests | 1 |
| Local same-origin | 1 |
| External | 0 |
| External JavaScript | 0 |
| External stylesheet | 0 |
| External image/audio/font | 0 |
| Renderer CDN | 0 |
| API/XHR/fetch | 0 |
| Dynamic module | 0 |
| Request failures | 0 |

The only request was the local document, for example
`http://127.0.0.1:50822/ocean-rescue/index.html` in the evidence-writing run.

| Runtime category | Count |
|---|---:|
| Page errors | 0 |
| Console errors | 0 |
| Console warnings | 4 |
| Unexpected warnings | 0 |

All four warnings matched the exact observed Chrome internal warning family:

```text
GL Driver Message (OpenGL, Performance, GL_CLOSE_PATH_NV, High): GPU stall due to ReadPixels
```

They were recorded as benign WebGL GPU-stall warnings, not broadly ignored by
regex. No page or console errors occurred.

## Product Diff And Verdict

- **Product source diff:** empty for `domains/ocean-rescue/src`.
- **Generated assets and `ocean-rescue/index.html`:** unchanged by this work package.
- **Structured evidence:** `browser-functional-evidence.json` updated from the final run.
- **Pytest:** 1 collected, 1 passed.
- **Final result:** PASS.

## Acceptance Checklist

- [x] Browser ready and canvas startup recorded
- [x] Selected renderer backend recorded
- [x] Profile → mission → GUP → launch → travel observed
- [x] Rescue arrival and active sea-turtle scene observed
- [x] All three loops released through real browser pointer drag
- [x] Mission completion and success UI reached
- [x] Full pause countdown sequence observed
- [x] Numerical pointer mapping assertions passed
- [x] Actual pointer interaction changed domain state
- [x] External runtime requests: 0
- [x] Console errors: 0
- [x] Page errors: 0
- [x] pytest-collected regression test: 1
- [x] Product source diff: empty
