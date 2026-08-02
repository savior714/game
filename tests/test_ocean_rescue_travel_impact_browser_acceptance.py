"""
Real-browser (Chromium) acceptance test for the collision impact feedback.

Drives the published single HTML `/ocean-rescue/index.html` through the normal
product flow over loopback HTTP, forces a collision with the first authored
obstacle, and verifies the contact-anchored impact burst contract:

- Both renderer lanes are exercised: WebGL/WebGL2 (preferred) and Canvas
  fallback (`--disable-webgl`).
- The impact burst is anchored at the obstacle contact point: the
  `travel-collision-impact-root` container position matches the
  `data-travel-scene-impact-contact-*` diagnostics and differs from the fixed
  legacy x=260.
- Core / ring / rays children exist under the root; the bubble burst and the
  submarine flash overlay become visible; the collided obstacle group pulses
  while sibling groups stay at scale 1.
- The burst is bounded: `data-travel-scene-impact-active` returns to false and
  nodes are hidden after the effect window.
- Reduced-motion lane shows the static high-contrast cue (rays hidden, no
  obstacle pulse) and also ends within its bounded window.
- Zero external-origin requests, zero CSP violations, zero page/console errors.
"""

import os
import socketserver
import threading
import time
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
PORT = 18767
EVIDENCE_DIR = Path(
    os.environ.get(
        "OCEAN_RESCUE_TRAVEL_IMPACT_EVIDENCE_DIR",
        "/tmp/AIDENGAME-OCEAN-RESCUE-TRAVEL-COLLISION-IMPACT-BROWSER-ACCEPTANCE-01",
    )
)

LANES = ["webgl", "canvas"]


class HTTPServerFixture:
    def __init__(self):
        self.server = None
        self.thread = None

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
        return f"http://127.0.0.1:{PORT}"

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()


@pytest.fixture(scope="module")
def server():
    srv = HTTPServerFixture()
    url = srv.start()
    yield url
    srv.stop()


def _go_through_normal_flow(pg, base_url):
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


def _collect_impact(pg):
    return pg.evaluate(
        """() => {
      const root = document.getElementById('ocean-rescue-root');
      const attr = (name) => root ? root.getAttribute(name) : null;
      const diag = {};
      for (const name of [
        'data-travel-scene-impact-mode',
        'data-travel-scene-impact-active',
        'data-travel-scene-impact-phase',
        'data-travel-scene-impact-obstacle-id',
        'data-travel-scene-impact-contact-x',
        'data-travel-scene-impact-contact-y',
        'data-travel-scene-impact-core-visible',
        'data-travel-scene-impact-ring-visible',
        'data-travel-scene-impact-rays-visible',
        'data-travel-scene-impact-bubbles-visible',
        'data-travel-scene-impact-target-pulse',
        'data-travel-scene-impact-submarine-flash'
      ]) {
        diag[name] = attr(name);
      }
      const effects = OceanRescue.RenderRuntime.getContainer('effects');
      const gw = OceanRescue.RenderRuntime.getContainer('gameplayWorld');
      const impactRoot = effects.children.find(c => c.label === 'travel-collision-impact-root') || null;
      const rootPos = impactRoot
        ? { x: Math.round(impactRoot.x), y: Math.round(impactRoot.y), visible: impactRoot.visible }
        : null;
      const childLabels = impactRoot ? impactRoot.children.map(c => c.label) : [];
      const burst = effects.children.find(c => c.label === 'travel-collision-flash') || null;
      const submarine = OceanRescue.RenderRuntime.getContainer('submarine');
      const overlay = submarine.children.find(c => c.label === 'travel-submarine-impact-flash') || null;
      const groups = [];
      for (const child of gw.children) {
        if (child && String(child.label).indexOf('travel-obstacle-') === 0 && child.children) {
          groups.push({ label: child.label, scaleX: child.scale.x, visible: child.visible });
        }
      }
      const terrain = OceanRescue.Terrain.getSnapshot();
      return {
        diag: diag,
        impactRoot: rootPos,
        childLabels: childLabels,
        burst: burst ? { x: Math.round(burst.x), y: Math.round(burst.y), visible: burst.visible } : null,
        overlay: overlay ? { visible: overlay.visible } : null,
        groups: groups,
        terrainCollisionCount: terrain.collisionCount,
        terrainLastCollisionId: terrain.lastCollisionObstacleId
      };
    }"""
    )


def _collect_impact_snapshot():
    """Return a JS source string that builds one impact snapshot in-page."""
    return """() => {
      const root = document.getElementById('ocean-rescue-root');
      const attr = (name) => root ? root.getAttribute(name) : null;
      const diag = {};
      for (const name of [
        'data-travel-scene-impact-mode',
        'data-travel-scene-impact-active',
        'data-travel-scene-impact-phase',
        'data-travel-scene-impact-obstacle-id',
        'data-travel-scene-impact-contact-x',
        'data-travel-scene-impact-contact-y',
        'data-travel-scene-impact-core-visible',
        'data-travel-scene-impact-ring-visible',
        'data-travel-scene-impact-rays-visible',
        'data-travel-scene-impact-bubbles-visible',
        'data-travel-scene-impact-target-pulse',
        'data-travel-scene-impact-submarine-flash'
      ]) {
        diag[name] = attr(name);
      }
      const effects = OceanRescue.RenderRuntime.getContainer('effects');
      const gw = OceanRescue.RenderRuntime.getContainer('gameplayWorld');
      const impactRoot = effects.children.find(c => c.label === 'travel-collision-impact-root') || null;
      const rootPos = impactRoot
        ? { x: Math.round(impactRoot.x), y: Math.round(impactRoot.y), visible: impactRoot.visible }
        : null;
      const childLabels = impactRoot ? impactRoot.children.map(c => c.label) : [];
      const burst = effects.children.find(c => c.label === 'travel-collision-flash') || null;
      const submarine = OceanRescue.RenderRuntime.getContainer('submarine');
      const overlay = submarine.children.find(c => c.label === 'travel-submarine-impact-flash') || null;
      const groups = [];
      for (const child of gw.children) {
        if (child && String(child.label).indexOf('travel-obstacle-') === 0 && child.children) {
          groups.push({ label: child.label, scaleX: child.scale.x, visible: child.visible });
        }
      }
      const terrain = OceanRescue.Terrain.getSnapshot();
      return {
        diag: diag,
        impactRoot: rootPos,
        childLabels: childLabels,
        burst: burst ? { x: Math.round(burst.x), y: Math.round(burst.y), visible: burst.visible } : null,
        overlay: overlay ? { visible: overlay.visible } : null,
        groups: groups,
        terrainCollisionCount: terrain.collisionCount,
        terrainLastCollisionId: terrain.lastCollisionObstacleId
      };
    }"""


def _wait_for_impact_active(pg, timeout_s=25):
    start = time.time()
    while time.time() - start < timeout_s:
        state = _collect_impact(pg)
        if state["diag"]["data-travel-scene-impact-active"] == "true":
            return state
        time.sleep(0.05)
    return state


def _wait_for_impact_idle(pg, timeout_s=15):
    start = time.time()
    while time.time() - start < timeout_s:
        state = _collect_impact(pg)
        if state["diag"]["data-travel-scene-impact-active"] == "false":
            return state
        time.sleep(0.05)
    return state


def _sample_impact_window(pg, sample_ms=600):
    """Sample the impact window inside the page with a single evaluate."""
    return pg.evaluate(
        """async ({ sampleMs, snapshotSource }) => {
      const snapshotFn = eval('(' + snapshotSource + ')');
      const samples = [];
      const start = performance.now();
      while (performance.now() - start < sampleMs) {
        const s = snapshotFn();
        if (s.diag['data-travel-scene-impact-active'] === 'true') {
          samples.push(s);
        }
        await new Promise((resolve) => setTimeout(resolve, 30));
      }
      return samples;
    }""",
        {"sampleMs": sample_ms, "snapshotSource": _collect_impact_snapshot()},
    )


def _run_scenario(pg, backend, base_url, reduced_motion):
    page_errors = []
    console_errors = []
    requests = []

    pg.on("pageerror", lambda e: page_errors.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and console_errors.append(m.text))
    pg.on("request", lambda r: requests.append(r.url))

    if reduced_motion:
        pg.emulate_media(reduced_motion="reduce")

    _go_through_normal_flow(pg, base_url)
    _move_gup_into_obstacle_band(pg)
    first = _wait_for_impact_active(pg)
    samples = _sample_impact_window(pg)
    idle = _wait_for_impact_idle(pg)

    base = f"{base_url}/"
    external = sorted(u for u in set(requests) if not u.startswith(base))

    return {
        "backend": backend,
        "reducedMotion": reduced_motion,
        "first": first,
        "samples": samples,
        "idle": idle,
        "externalRequests": external,
        "pageErrors": page_errors,
        "consoleErrors": console_errors,
        "requestCount": len(set(requests)),
    }


@pytest.mark.browser
class TestTravelImpactBrowserAcceptance:
    @pytest.mark.parametrize("backend", LANES)
    @pytest.mark.parametrize("reduced_motion", [False, True])
    def test_impact_burst_per_lane(self, server, backend, reduced_motion):
        evidence = EVIDENCE_DIR / backend
        evidence.mkdir(parents=True, exist_ok=True)

        launch_args = ["--disable-webgl"] if backend == "canvas" else []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=launch_args)
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
            result = _run_scenario(pg, backend, server, reduced_motion)
            context.close()
            browser.close()

        label = "reduced" if reduced_motion else "full"
        (evidence / f"{backend}-{label}-metadata.json").write_text(
            __import__("json").dumps(
                {
                    "backend": backend,
                    "reducedMotion": reduced_motion,
                    "first": result["first"],
                    "samples": result["samples"],
                    "idle": result["idle"],
                    "requestCount": result["requestCount"],
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )

        assert result["externalRequests"] == [], result["externalRequests"]
        assert result["pageErrors"] == [], result["pageErrors"]
        assert result["consoleErrors"] == [], result["consoleErrors"]

        first = result["first"]
        samples = result["samples"]
        assert samples, "no impact samples collected"

        diag = first["diag"]
        assert diag["data-travel-scene-impact-active"] == "true", diag
        assert diag["data-travel-scene-impact-mode"] == "contact-burst-v1", diag
        assert diag["data-travel-scene-impact-obstacle-id"] == "coral-column-1", diag
        contact_x = float(diag["data-travel-scene-impact-contact-x"])
        contact_y = float(diag["data-travel-scene-impact-contact-y"])
        assert contact_x >= 0 and contact_x <= 1280, f"contact x out of range: {contact_x}"
        assert contact_y >= 0 and contact_y <= 720, f"contact y out of range: {contact_y}"
        assert contact_x > 261, (
            f"contact x must not be the fixed legacy 260, got {contact_x}"
        )

        root = first["impactRoot"]
        assert root is not None, "impact root missing"
        assert root["visible"] is True, "impact root must be visible"
        assert abs(root["x"] - contact_x) <= 1.0, (
            f"root x must match contact x: root {root['x']} vs diag {contact_x}"
        )
        assert abs(root["y"] - contact_y) <= 1.0, (
            f"root y must match contact y: root {root['y']} vs diag {contact_y}"
        )

        burst = first["burst"]
        if reduced_motion:
            assert burst is not None, "burst sprite must exist"
            assert burst["visible"] is False, (
                "burst must stay hidden under reduced motion (static cue)"
            )
        else:
            assert burst is not None and burst["visible"] is True, "burst must be visible"
            assert abs(burst["x"] - contact_x) <= 1.0, (
                f"burst must be anchored at contact x: {burst['x']} vs {contact_x}"
            )

        labels = first["childLabels"]
        assert "travel-collision-impact-core" in labels, labels
        assert "travel-collision-impact-ring" in labels, labels
        assert "travel-collision-impact-rays" in labels, labels

        rays_visible = any(
            s["diag"]["data-travel-scene-impact-rays-visible"] == "true"
            for s in samples
        )
        target = next(
            (g for g in first["groups"] if g["label"] == "travel-obstacle-0"),
            None,
        )
        assert target is not None, "target obstacle group missing"

        if reduced_motion:
            assert not rays_visible, (
                "rays must stay hidden under reduced motion"
            )
            peak_target_scale = max(
                (
                    next(
                        (g for g in s["groups"] if g["label"] == "travel-obstacle-0"),
                        {"scaleX": 1.0},
                    )["scaleX"]
                    for s in samples
                )
            )
            assert abs(peak_target_scale - 1) < 0.01, (
                f"no obstacle pulse under reduced motion, peak {peak_target_scale}"
            )
        else:
            assert rays_visible, "rays must be visible during full motion burst"
            peak_target_scale = max(
                next(
                    (g for g in s["groups"] if g["label"] == "travel-obstacle-0"),
                    {"scaleX": 1.0},
                )["scaleX"]
                for s in samples
            )
            assert peak_target_scale > 1.001, (
                f"target group must pulse, peak {peak_target_scale}"
            )
            for s in samples:
                for group in s["groups"]:
                    if group["label"] != "travel-obstacle-0":
                        assert abs(group["scaleX"] - 1) < 0.001, (
                            f"sibling group must stay at scale 1: {group}"
                        )

        overlay_visible = any(
            s["overlay"] is not None and s["overlay"]["visible"] for s in samples
        )
        assert overlay_visible, "submarine flash overlay must be visible"
        assert first["terrainCollisionCount"] >= 1, "no collision recorded"
        assert first["terrainLastCollisionId"] == "coral-column-1"

        idle = result["idle"]
        idle_diag = idle["diag"]
        assert idle_diag["data-travel-scene-impact-active"] == "false", idle_diag
        assert idle_diag["data-travel-scene-impact-obstacle-id"] == "", idle_diag
        assert idle["impactRoot"]["visible"] is False, "root must be hidden after reset"
