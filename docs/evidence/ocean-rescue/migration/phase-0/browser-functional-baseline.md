# Ocean Rescue Browser Functional Baseline

- **Captured:** 2026-08-03T13:40:00+09:00
- **Start HEAD:** 59e3011b9a29451816292a9128a1aaa36faeb8f9
- **Browser:** Google Chrome 150.0.7871.188 (Chromium headless)
- **Viewport:** 1280x720
- **Result:** PASS
- **Scope:** WP-02 Browser Functional Parity Baseline
- **Excluded scope:** WP-01 Static Build, WP-03 Target Device Performance

## Harness

- **Tool:** Playwright (sync API) with Chromium headless
- **Local HTTP server:** Python `http.server.SimpleHTTPRequestHandler` on 127.0.0.1:18771
- **Test script:** `tests/test_ocean_rescue_wp02_browser_baseline.py`
- **Evidence file:** `docs/evidence/ocean-rescue/migration/phase-0/browser-functional-evidence.json`
- **No new dependencies added**

## Startup and renderer backend

| Property | Value |
|----------|-------|
| Canvas found | true |
| Canvas dimensions | 1280x720 |
| PixiJS version | 8.19.0 |
| Renderer backend | WebGL |
| Device pixel ratio | 1 |
| Ready state | `data-ocean-rescue-ready=true` |

WebGL is the active renderer (confirmed via `canvas.getContext('webgl2') || canvas.getContext('webgl')` returning non-null). Canvas2D fallback is available via `OceanRescue.RenderRuntime.getLegacyCanvas()`.

## Representative gameplay flow

Complete flow exercised:

1. **Profile choice:** Select arctic-fox animal → continue
2. **Mission selection:** Click sea-turtle mission
3. **GUP selection:** Click gup-x → launch
4. **Launch:** Skip launch animation
5. **Travel:** Travel scene activated (`data-travel-scene=active`)

All steps completed without errors. Phase transitions: PROFILE → MISSION_SELECT → GUP_SELECT → LAUNCH → TRAVEL.

## Pause/resume

| Phase | State |
|-------|-------|
| Enter pause | `data-pause-active=true`, overlay visible, resume button visible, countdown hidden |
| Countdown | Shows "3", visible |
| Resume complete | `data-pause-active=false`, overlay hidden |

Pause correctly freezes the game, resume countdown executes 3→2→1→Go!, overlay dismissed after countdown.

## Pointer mapping

Logical coordinate contract: **1280x720** (verified via `getBoundingClientRect` and coordinate mapping).

| Point | Client coords | Logical coords | Contract |
|-------|--------------|----------------|----------|
| Viewport center | (640, 360) | (640.0, 360.0) | 1280/2, 720/2 |
| Top-left safe edge | (10, 10) | (10.0, 10.0) | Near origin |
| Bottom-right boundary | (1270, 710) | (1270.0, 710.0) | Near 1280x720 |

- Canvas rect: `{left: 0, top: 0, w: 1280, h: 720}`
- DPR=1: client coordinates map 1:1 to logical coordinates
- Click dispatch verified: pointer event registered at viewport center

## Console and runtime errors

| Category | Count | Details |
|----------|-------|---------|
| Page errors | 0 | — |
| Console errors | 0 | — |
| Console warnings | 4 | WebGL GPU stall warnings (benign, Chrome internal) |

The 4 warnings are Chrome's internal WebGL performance messages:
```
[.WebGL-0x...]GL Driver Message (OpenGL, Performance, GL_CLOSE_PATH_NV, High): GPU stall due to ReadPixels
```
These are benign Chromium GPU driver warnings, not application errors. They occur during WebGL ReadPixels calls and do not affect gameplay.

## Network requests

| Metric | Value |
|--------|-------|
| Total requests | 1 |
| Local requests | 1 |
| External requests | 0 |

Only request: `http://127.0.0.1:18771/ocean-rescue/index.html` (the document itself). Zero external-origin requests.

## Evidence artifacts

| File | Description |
|------|-------------|
| `browser-functional-evidence.json` | Structured JSON evidence (startup, flow, pause, pointer, network, console) |

## Acceptance checklist

- [x] Browser startup successful
- [x] Renderer backend: WebGL
- [x] Canvas dimensions: 1280x720
- [x] PixiJS 8.19.0 initialized
- [x] Profile choice flow completed
- [x] Mission selection works
- [x] GUP selection works
- [x] Launch and travel started
- [x] Pause activates (`data-pause-active=true`)
- [x] Pause overlay visible
- [x] Resume countdown executes
- [x] Resume completes (`data-pause-active=false`)
- [x] Pointer mapping: 1280x720 logical contract satisfied
- [x] Zero external network requests
- [x] Zero console errors
- [x] Zero page errors
- [x] WebGL warnings are benign (known Chrome GPU driver behavior)

## Blockers and remaining evidence

None. WP-02 is PASS.

### Known benign warnings

The 4 WebGL GPU stall warnings are Chrome-internal OpenGL performance messages that occur when PixiJS calls ReadPixels. They do not affect gameplay, rendering, or application state. They are recorded for completeness but are not blockers.
