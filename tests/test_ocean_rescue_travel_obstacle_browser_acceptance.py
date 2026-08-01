"""
Focused real-browser (Chromium) acceptance test for the authored travel-obstacle
sprite implementation (predecessor commit 516e908, origin/main).

Drives the published single HTML `/ocean-rescue/index.html` through the normal
product flow (mission select -> GUP select -> launch -> skip -> travel) over
loopback HTTP and verifies the complete travel-obstacle acceptance criterion:

- Both renderer lanes are exercised: WebGL/WebGL2 (preferred, no flags) and
  Canvas fallback (Chromium launched with `--disable-webgl`).
- Every lane runs twice; binary diagnostics and obstacle identity must be
  identical across runs (determinism checkpoint).
- Obstacles are authored `PIXI.Sprite`s (not placeholders / Graphics) backed by
  the generated atlas texture `terrain.coral-column`, with finite non-zero
  position and live movement tied to `Travel.distance`.
- Collision feedback, pause freeze, resume advance, and rescue arrival exit from
  `TravelScene` all complete through public UI / public read-only state.
- Zero external-origin requests, zero reference-image requests, zero CSP
  violations, zero page/console errors.
- One 1280x720 screenshot per backend (after readiness) with SHA-256 and
  metadata written to the evidence directory.

The loopback HTTP fixture and Playwright launch are the same pattern used by
`tests/test_nonmath_browser_acceptance.py`.
"""

import hashlib
import json
import os
import socketserver
import threading
import time
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
PORT = 18766
EVIDENCE_DIR = Path(
    os.environ.get(
        "OCEAN_RESCUE_TRAVEL_EVIDENCE_DIR",
        "/tmp/AIDENGAME-OCEAN-RESCUE-TRAVEL-OBSTACLE-BROWSER-ACCEPTANCE-CLOSEOUT-01",
    )
)

LANES = ["webgl", "canvas"]
RUN_INDICES = [0, 1]

REFERENCE_PATHS = (
    "/docs/reference/ocean-rescue/",
    "/artifacts/ocean-rescue/reference-",
    "reference-visual-",
)


class HTTPServerFixture:
    """Static loopback HTTP server for repo root."""

    def __init__(self):
        self.server = None
        self.thread = None
        self.base_url = None

    def start(self):
        class QuietHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

            def log_message(self, *args):
                pass

        socketserver.TCPServer.allow_reuse_address = True
        self.server = socketserver.TCPServer(("127.0.0.1", PORT), QuietHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.5)
        self.base_url = f"http://127.0.0.1:{PORT}"
        return self.base_url

    def stop(self):
        if self.server:
            self.server.shutdown()


@pytest.fixture(scope="module")
def server():
    srv = HTTPServerFixture()
    url = srv.start()
    yield url
    srv.stop()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _collect_readiness(pg):
    """Read-only readiness diagnostics plus live obstacle sprite summary."""
    return pg.evaluate(
        """() => {
      const root = document.getElementById('ocean-rescue-root');
      const attr = (name) => root ? root.getAttribute(name) : null;
      const diag = {};
      for (const name of [
        'data-ocean-rescue-ready',
        'data-render-runtime',
        'data-render-backend',
        'data-render-logical-width',
        'data-render-logical-height',
        'data-travel-scene',
        'data-travel-scene-animation',
        'data-travel-scene-environment',
        'data-travel-scene-obstacle-count',
        'data-travel-scene-obstacle-renderer',
        'data-travel-scene-visible-obstacle-count',
        'data-travel-scene-nonfinite-obstacle-count',
        'data-travel-scene-placeholder-obstacle-count',
        'data-travel-scene-first-visible-obstacle-id',
        'data-travel-scene-first-visible-obstacle-alias',
        'data-travel-scene-legacy-visible',
        'data-travel-scene-gup-id'
      ]) {
        diag[name] = attr(name);
      }
      const gw = OceanRescue.RenderRuntime.getContainer('gameplayWorld');
      const sprites = [];
      for (const child of gw.children) {
        if (child && String(child.label).indexOf('travel-obstacle-') === 0) {
          const t = child.texture;
          sprites.push({
            label: child.label,
            isSprite: child instanceof PIXI.Sprite,
            hasFrame: !!(t && t.frame && t.frame.width > 0 && t.frame.height > 0),
            frameWidth: t && t.frame ? t.frame.width : 0,
            frameHeight: t && t.frame ? t.frame.height : 0,
            textureLabel: t ? t.label : null,
            sourceWidth: t && t.source ? t.source.width : 0,
            sourceHeight: t && t.source ? t.source.height : 0,
            x: child.x,
            y: child.y,
            visible: child.visible,
            renderable: child.renderable
          });
        }
      }
      const travel = OceanRescue.Travel.getSnapshot();
      const terrain = OceanRescue.Terrain.getSnapshot();
      return {
        diag: diag,
        sprites: sprites,
        travelDistance: travel.distance,
        travelY: travel.y,
        terrainCollisionCount: terrain.collisionCount,
        terrainLastCollisionId: terrain.lastCollisionObstacleId,
        terrainForwardSpeedMultiplier: terrain.forwardSpeedMultiplier,
        terrainCollisionActive: terrain.collisionActive,
        cspViolations: window.__cspViolations || []
      };
    }"""
    )


def _go_through_normal_flow(pg, base_url):
    """Mission -> GUP -> launch -> skip -> travel, using public UI only."""
    pg.goto(f"{base_url}/ocean-rescue/index.html")
    pg.wait_for_selector(
        "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=20000
    )
    pg.click("#ocean-rescue-mission-list [data-mission-id=sea-turtle]")
    pg.wait_for_selector("#ocean-rescue-gup-select:not([hidden])", timeout=10000)
    pg.click("#ocean-rescue-gup-list [data-gup-id=gup-x]")
    pg.click("#ocean-rescue-gup-launch")
    pg.wait_for_selector("#ocean-rescue-launch:not([hidden])", timeout=10000)
    pg.click("#ocean-rescue-launch-skip")
    pg.wait_for_selector("#ocean-rescue-root[data-travel-scene=active]", timeout=15000)


def _move_gup_into_obstacle_band(pg, target_logical_y=300):
    """Public canvas tap that eases the GUP to a y intersecting obstacle 1."""
    rect = pg.evaluate(
        """() => {
      const c = document.getElementById('ocean-rescue-canvas');
      const r = c.getBoundingClientRect();
      return { left: r.left, top: r.top, w: r.width, h: r.height };
    }"""
    )
    client_y = rect["top"] + (target_logical_y / 720) * rect["h"]
    client_x = rect["left"] + rect["w"] / 2
    pg.mouse.click(client_x, client_y)


def _wait_for_collision(pg, timeout_s=25):
    start = time.time()
    while time.time() - start < timeout_s:
        state = pg.evaluate(
            """() => {
          const t = OceanRescue.Terrain.getSnapshot();
          return {
            collisionCount: t.collisionCount,
            lastCollisionId: t.lastCollisionObstacleId,
            forwardSpeedMultiplier: t.forwardSpeedMultiplier,
            collisionActive: t.collisionActive
          };
        }"""
        )
        if state["collisionCount"] >= 1:
            return state
        time.sleep(0.2)
    return state


def _wait_for_arrival(pg, timeout_s=70):
    start = time.time()
    while time.time() - start < timeout_s:
        state = pg.evaluate(
            """() => {
          const root = document.getElementById('ocean-rescue-root');
          const t = OceanRescue.Travel.getSnapshot();
          return {
            travelScene: root.getAttribute('data-travel-scene'),
            rescueSequence: root.getAttribute('data-rescue-sequence'),
            rescuePhase: root.getAttribute('data-rescue-phase'),
            distance: t.distance
          };
        }"""
        )
        if state["travelScene"] != "active" or state["rescueSequence"] == "active":
            return state
        time.sleep(0.5)
    return state


def _run_scenario(pg, backend, run_index, base_url, screenshot_path):
    page_errors = []
    console_errors = []
    requests = []

    pg.on("pageerror", lambda e: page_errors.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and console_errors.append(m.text))
    pg.on("request", lambda r: requests.append(r.url))

    _go_through_normal_flow(pg, base_url)

    readiness = _collect_readiness(pg)
    diag = readiness["diag"]
    sprites = readiness["sprites"]
    assert diag["data-ocean-rescue-ready"] == "true"
    assert diag["data-render-runtime"] == "ready"
    assert diag["data-travel-scene"] == "active"
    assert diag["data-travel-scene-animation"] == "running"
    assert diag["data-travel-scene-environment"] == "coral-reef"
    assert diag["data-render-logical-width"] == "1280"
    assert diag["data-render-logical-height"] == "720"

    assert diag["data-render-backend"] == backend
    assert diag["data-travel-scene-gup-id"] == "gup-x"
    assert diag["data-travel-scene-obstacle-count"] == "5"

    # Sprite-backed authored obstacles (criterion: sprite renderer, no placeholder).
    assert diag["data-travel-scene-obstacle-renderer"] == "sprite"
    assert diag["data-travel-scene-placeholder-obstacle-count"] == "0"
    assert diag["data-travel-scene-nonfinite-obstacle-count"] == "0"
    assert diag["data-travel-scene-visible-obstacle-count"] in ("1", "2", "3")
    assert diag["data-travel-scene-legacy-visible"] == "false"
    assert diag["data-travel-scene-first-visible-obstacle-id"] == "coral-column-1"
    assert (
        diag["data-travel-scene-first-visible-obstacle-alias"] == "terrain.coral-column"
    )

    # Live PIXI.Sprite in gameplayWorld with atlas-backed texture.
    assert len(sprites) == 5, f"expected 5 obstacle sprites, got {len(sprites)}"
    first = sprites[0]
    assert first["isSprite"] is True
    assert first["visible"] is True
    assert first["renderable"] is True
    assert first["hasFrame"] is True
    assert first["textureLabel"] == "terrain.coral-column"
    assert first["frameWidth"] > 0 and first["frameHeight"] > 0
    assert first["sourceWidth"] > 0 and first["sourceHeight"] > 0
    assert first["x"] > 0 and first["y"] > 0

    # Readiness evidence: one 1280x720 screenshot per backend while travel is
    # active and the first authored obstacle is on screen.
    if screenshot_path is not None:
        pg.screenshot(path=str(screenshot_path), full_page=False)

    # Live movement tied to Travel.distance (read both atomically per frame).
    def _sample():
        return pg.evaluate(
            """() => {
          const gw = OceanRescue.RenderRuntime.getContainer('gameplayWorld');
          return {
            d: OceanRescue.Travel.getSnapshot().distance,
            x: gw.children.find(c => String(c.label).indexOf('travel-obstacle-') === 0).x
          };
        }"""
        )

    s1 = _sample()
    time.sleep(0.5)
    s2 = _sample()
    d1, x1 = s1["d"], s1["x"]
    d2, x2 = s2["d"], s2["x"]
    assert d2 > d1, f"travel distance did not advance: {d1} -> {d2}"
    assert x2 < x1, f"obstacle did not move left: {x1} -> {x2}"
    assert abs((d2 - d1) - (x1 - x2)) < 1.5, (
        f"obstacle movement not tied to distance: d={d2 - d1}, x={x1 - x2}"
    )

    # Collision feedback against the first authored obstacle.
    _move_gup_into_obstacle_band(pg)
    collision = _wait_for_collision(pg)
    assert collision["collisionCount"] >= 1, "no collision recorded"
    assert collision["lastCollisionId"] == "coral-column-1", (
        f"wrong obstacle collided: {collision['lastCollisionId']}"
    )

    # Pause freezes the travel scene; resume advances it again.
    pg.click("#ocean-rescue-pause-button")
    pg.wait_for_selector("#ocean-rescue-root[data-pause-active=true]", timeout=10000)
    time.sleep(0.4)
    pd1 = pg.evaluate("() => OceanRescue.Travel.getSnapshot().distance")
    time.sleep(0.5)
    pd2 = pg.evaluate("() => OceanRescue.Travel.getSnapshot().distance")
    assert pd1 == pd2, f"travel kept advancing while paused: {pd1} vs {pd2}"

    pg.click("#ocean-rescue-pause-resume")
    pg.wait_for_selector("#ocean-rescue-root[data-pause-active=false]", timeout=12000)
    time.sleep(0.5)
    rd1 = pg.evaluate("() => OceanRescue.Travel.getSnapshot().distance")
    time.sleep(0.5)
    rd2 = pg.evaluate("() => OceanRescue.Travel.getSnapshot().distance")
    assert rd2 > rd1, f"travel did not advance after resume: {rd1} -> {rd2}"

    # Rescue arrival exits TravelScene through normal gameplay.
    arrival = _wait_for_arrival(pg)
    assert arrival["travelScene"] == "unmounted", f"travel not exited: {arrival}"
    assert arrival["rescueSequence"] == "active", (
        f"rescue sequence not started: {arrival}"
    )
    assert arrival["rescuePhase"] == "site-transition"

    # No external requests, no reference images, no CSP violations, no errors.
    base = f"{base_url}/"
    external = sorted(u for u in set(requests) if not u.startswith(base))
    assert external == [], f"external-origin requests: {external}"
    reference = sorted(
        u
        for u in set(requests)
        if any(p in u for p in REFERENCE_PATHS) and u.startswith(base)
    )
    assert reference == [], f"reference-image requests: {reference}"
    assert not page_errors, f"page errors: {page_errors}"
    assert not console_errors, f"console errors: {console_errors}"
    csp_violations = pg.evaluate("() => window.__cspViolations || []")
    assert not csp_violations, f"CSP violations: {csp_violations}"

    return {
        "backend": backend,
        "run_index": run_index,
        "readiness": readiness,
        "sprites": sprites,
        "collision": collision,
        "arrival": arrival,
        "movement": {"d1": d1, "d2": d2, "x1": x1, "x2": x2},
        "pause": {"d1": pd1, "d2": pd2},
        "resume": {"d1": rd1, "d2": rd2},
        "externalRequests": external,
        "referenceRequests": reference,
        "pageErrors": page_errors,
        "consoleErrors": console_errors,
        "cspViolations": csp_violations,
        "requestCount": len(set(requests)),
    }


@pytest.mark.browser
class TestTravelObstacleBrowserAcceptance:
    @pytest.mark.parametrize("backend", LANES)
    def test_travel_obstacle_lane_twice(self, server, backend):
        """Run the full acceptance scenario twice per lane, compare determinism."""
        evidence = EVIDENCE_DIR / backend
        evidence.mkdir(parents=True, exist_ok=True)

        launch_args = ["--disable-webgl"] if backend == "canvas" else []
        results = {}
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=launch_args)
            for run_index in RUN_INDICES:
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    locale="ko-KR",
                    timezone_id="Asia/Seoul",
                )
                context.add_init_script(
                    "window.__cspViolations = [];"
                    "document.addEventListener('securitypolicyviolation',"
                    "  function (e) { window.__cspViolations.push(e.blockedURI); });"
                )
                pg = context.new_page()

                screenshot_path = evidence / f"{backend}-run-{run_index}-readiness.png"
                result = _run_scenario(pg, backend, run_index, server, screenshot_path)
                sha = _sha256(screenshot_path)

                readiness = result["readiness"]
                summary = {
                    "backend": backend,
                    "run_index": run_index,
                    "lane": backend,
                    "viewport": "1280x720",
                    "screenshot": screenshot_path.name,
                    "screenshot_sha256": sha,
                    "binary_diagnostics": readiness["diag"],
                    "obstacle_identity": {
                        "count": len(readiness["sprites"]),
                        "first": {
                            "label": readiness["sprites"][0]["label"],
                            "textureLabel": readiness["sprites"][0]["textureLabel"],
                            "visible": readiness["sprites"][0]["visible"],
                            "isSprite": readiness["sprites"][0]["isSprite"],
                            "hasFrame": readiness["sprites"][0]["hasFrame"],
                        },
                    },
                    "collision": result["collision"],
                    "arrival": result["arrival"],
                    "movement_delta_d": result["movement"]["d2"]
                    - result["movement"]["d1"],
                    "movement_delta_x": result["movement"]["x1"]
                    - result["movement"]["x2"],
                    "pause_frozen": result["pause"]["d1"] == result["pause"]["d2"],
                    "resume_advanced": result["resume"]["d2"] > result["resume"]["d1"],
                    "request_count": result["requestCount"],
                    "external_requests": result["externalRequests"],
                    "reference_requests": result["referenceRequests"],
                    "page_errors": result["pageErrors"],
                    "console_errors": result["consoleErrors"],
                    "csp_violations": result["cspViolations"],
                }
                meta_path = evidence / f"{backend}-run-{run_index}-metadata.json"
                meta_path.write_text(
                    json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
                )
                results[run_index] = summary

                assert result["externalRequests"] == []
                assert result["referenceRequests"] == []
                assert result["pageErrors"] == []
                assert result["consoleErrors"] == []
                assert result["cspViolations"] == []

                context.close()
            browser.close()

        run0, run1 = results[0], results[1]
        stable = [
            "data-render-backend",
            "data-travel-scene-obstacle-renderer",
            "data-travel-scene-visible-obstacle-count",
            "data-travel-scene-nonfinite-obstacle-count",
            "data-travel-scene-placeholder-obstacle-count",
            "data-travel-scene-first-visible-obstacle-id",
            "data-travel-scene-first-visible-obstacle-alias",
            "data-travel-scene-legacy-visible",
        ]
        for key in stable:
            assert run0["binary_diagnostics"][key] == run1["binary_diagnostics"][key], (
                f"diagnostic {key} differs across runs: "
                f"{run0['binary_diagnostics'][key]} vs {run1['binary_diagnostics'][key]}"
            )
        assert run0["obstacle_identity"] == run1["obstacle_identity"], (
            "obstacle identity differs across runs"
        )
        assert run0["pause_frozen"] is True
        assert run1["pause_frozen"] is True
        assert run0["resume_advanced"] is True
        assert run1["resume_advanced"] is True
        assert run0["collision"]["lastCollisionId"] == "coral-column-1"
        assert run1["collision"]["lastCollisionId"] == "coral-column-1"
        assert run0["arrival"]["travelScene"] == "unmounted"
        assert run1["arrival"]["travelScene"] == "unmounted"
        assert run0["arrival"]["rescueSequence"] == "active"
        assert run1["arrival"]["rescueSequence"] == "active"
