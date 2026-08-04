"""
Focused real-browser (Chromium) test proving native pointer capture lifecycle
for Young Whale connection + towing gestures without API neutralization.

Uses browser-generated trusted pointer input (page.mouse) to verify:
- setPointerCapture is called on canvas
- gotpointercapture fires
- hasPointerCapture(pointerId) == true during gesture (after down, before up)
- releasePointerCapture is called on canvas
- lostpointercapture fires
- hasPointerCapture(pointerId) == false after up
- Application pointerActive returns to false
- Both consecutive gestures (connection + towing) complete the full lifecycle
"""

import socketserver
import threading
import time
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
PORT = 18770


class HTTPServerFixture:
    def __init__(self):
        self.server = None
        self.thread = None

    def start(self):
        class QuietHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

            def log_message(self, format: str, *args) -> None:
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


@pytest.fixture(scope="module")
def server():
    srv = HTTPServerFixture()
    url = srv.start()
    yield url
    srv.stop()


_INIT_SCRIPT = """
window.__pointerCaptureLog = [];
window.__canvasEventLog = [];

const _origSet = Element.prototype.setPointerCapture;
const _origRelease = Element.prototype.releasePointerCapture;

Element.prototype.setPointerCapture = function (pointerId) {
  window.__pointerCaptureLog.push({
    method: "set",
    pointerId: pointerId,
    targetId: this.id || this.tagName,
    ts: Date.now()
  });
  return _origSet.call(this, pointerId);
};

Element.prototype.releasePointerCapture = function (pointerId) {
  window.__pointerCaptureLog.push({
    method: "release",
    pointerId: pointerId,
    targetId: this.id || this.tagName,
    ts: Date.now()
  });
  return _origRelease.call(this, pointerId);
};
"""


def _install_canvas_event_observers(pg):
    pg.evaluate("""() => {
      const canvas = document.getElementById('ocean-rescue-canvas');
      if (!canvas) return;
      const types = [
        'pointerdown','pointermove','pointerup','pointercancel',
        'gotpointercapture','lostpointercapture'
      ];
      for (const t of types) {
        canvas.addEventListener(t, (e) => {
          window.__canvasEventLog.push({
            type: e.type,
            pointerId: e.pointerId,
            pointerType: e.pointerType,
            isTrusted: e.isTrusted,
            targetId: e.target.id,
            hasCapture: canvas.hasPointerCapture(e.pointerId),
            ts: Date.now()
          });
        }, { capture: true });
      }
    }""")


def _get_canvas_rect(pg):
    return pg.evaluate("""() => {
      const c = document.getElementById('ocean-rescue-canvas');
      const r = c.getBoundingClientRect();
      return { left: r.left, top: r.top, w: r.width, h: r.height };
    }""")


def _logical_to_client(rect, lx, ly):
    cx = rect["left"] + (lx / 1280) * rect["w"]
    cy = rect["top"] + (ly / 720) * rect["h"]
    return cx, cy


def _go_to_young_whale_rescue_active(pg, base_url):
    pg.goto(f"{base_url}/ocean-rescue/index.html")
    pg.wait_for_selector(
        "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=20000
    )
    if pg.locator("#ocean-rescue-profile-choice").is_visible():
        pg.click('[data-profile-animal-id="arctic-fox"]')
        pg.click("#ocean-rescue-profile-continue")

    pg.evaluate("""() => {
      OceanRescue.Missions.completeMission("sea-turtle");
      OceanRescue.Missions.completeMission("crab");
    }""")

    pg.reload()
    pg.wait_for_selector(
        "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=20000
    )
    if pg.locator("#ocean-rescue-profile-choice").is_visible():
        pg.click('[data-profile-animal-id="arctic-fox"]')
        pg.click("#ocean-rescue-profile-continue")

    pg.wait_for_function(
        """() => {
      const btn = document.querySelector('#ocean-rescue-mission-list [data-mission-id=young-whale]');
      return btn && !btn.disabled;
    }""",
        timeout=5000,
    )
    pg.click("#ocean-rescue-mission-list [data-mission-id=young-whale]")
    pg.wait_for_selector("#ocean-rescue-gup-select:not([hidden])", timeout=10000)
    pg.click("#ocean-rescue-gup-list [data-gup-id=gup-x]")
    pg.click("#ocean-rescue-gup-launch")
    pg.wait_for_selector("#ocean-rescue-launch:not([hidden])", timeout=10000)
    pg.click("#ocean-rescue-launch-skip")
    pg.wait_for_selector("#ocean-rescue-root[data-travel-scene=active]", timeout=15000)

    pg.evaluate("""() => {
      for (let i = 0; i < 1200; i++) {
        OceanRescue.Travel.step(50);
      }
    }""")

    pg.wait_for_function(
        """() => {
      const root = document.getElementById('ocean-rescue-root');
      return root && root.getAttribute('data-rescue-phase') === 'active';
    }""",
        timeout=15000,
    )

    pg.wait_for_function(
        """() => {
      const snap = OceanRescue.YoungWhale.getSnapshot();
      return snap.active && snap.stage === 'connection' && !snap.inputLocked;
    }""",
        timeout=5000,
    )


def _clear_observers(pg):
    pg.evaluate(
        "() => { window.__pointerCaptureLog = []; window.__canvasEventLog = []; }"
    )


def _get_capture_log(pg):
    return pg.evaluate("() => window.__pointerCaptureLog")


def _get_canvas_events(pg):
    return pg.evaluate("() => window.__canvasEventLog")


def _get_young_whale_snapshot(pg):
    return pg.evaluate("() => OceanRescue.YoungWhale.getSnapshot()")


def _drag_and_measure_capture(pg, rect, start_lx, start_ly, end_lx, end_ly, steps=25):
    """Perform a drag using page.mouse and measure capture state during the gesture.

    Returns dict with:
      - pointerId: the pointerId from the trusted pointerdown
      - hasCaptureDuring: hasPointerCapture result after down + before up
      - setCalled: whether setPointerCapture was called
      - releaseCalled: whether releasePointerCapture was called
    """
    sx, sy = _logical_to_client(rect, start_lx, start_ly)
    ex, ey = _logical_to_client(rect, end_lx, end_ly)

    pg.mouse.move(sx, sy)
    pg.mouse.down()

    pg.wait_for_function(
        """() => {
      const log = window.__canvasEventLog;
      return log.some(e => e.type === 'pointerdown' && e.isTrusted);
    }""",
        timeout=3000,
    )

    during = pg.evaluate("""() => {
      const c = document.getElementById('ocean-rescue-canvas');
      const log = window.__canvasEventLog;
      const down = log.find(e => e.type === 'pointerdown' && e.isTrusted);
      if (!down) return { hasCapture: false, pointerId: null };
      const snap = window.OceanRescue.YoungWhale.getSnapshot();
      return {
        hasCapture: c.hasPointerCapture(down.pointerId),
        pointerId: down.pointerId,
        pointerActive: snap.pointerActive
      };
    }""")

    pg.mouse.move(ex, ey, steps=steps)
    pg.mouse.up()

    pg.wait_for_function(
        """() => {
      const log = window.__canvasEventLog;
      return log.some(e => e.type === 'pointerup' && e.isTrusted);
    }""",
        timeout=3000,
    )

    after = pg.evaluate("""() => {
      const c = document.getElementById('ocean-rescue-canvas');
      const log = window.__canvasEventLog;
      const up = log.find(e => e.type === 'pointerup' && e.isTrusted);
      if (!up) return { hasCapture: false };
      return { hasCapture: c.hasPointerCapture(up.pointerId) };
    }""")

    cap = _get_capture_log(pg)
    evts = _get_canvas_events(pg)

    return {
        "pointerId": during["pointerId"],
        "hasCaptureDuring": during["hasCapture"],
        "hasCaptureAfter": after["hasCapture"],
        "pointerActiveDuring": during["pointerActive"],
        "setCalled": any(c["method"] == "set" for c in cap),
        "releaseCalled": any(c["method"] == "release" for c in cap),
        "gotCapture": any(e["type"] == "gotpointercapture" for e in evts),
        "lostCapture": any(e["type"] == "lostpointercapture" for e in evts),
        "downEvent": next(
            (e for e in evts if e["type"] == "pointerdown" and e["isTrusted"]), None
        ),
        "upEvent": next(
            (e for e in evts if e["type"] == "pointerup" and e["isTrusted"]), None
        ),
    }


@pytest.mark.browser
class TestYoungWhaleNativePointerCapture:
    def test_connection_and_towing_capture_lifecycle(self, server):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                locale="ko-KR",
                timezone_id="Asia/Seoul",
            )
            context.add_init_script(_INIT_SCRIPT)
            pg = context.new_page()

            page_errors = []
            console_errors = []
            requests_log = []

            pg.on("pageerror", lambda e: page_errors.append(str(e)))
            pg.on(
                "console",
                lambda m: console_errors.append(m.text) if m.type == "error" else None,
            )
            pg.on("request", lambda r: requests_log.append(r.url))

            _go_to_young_whale_rescue_active(pg, server)
            _install_canvas_event_observers(pg)
            rect = _get_canvas_rect(pg)

            # ── Gesture 1: debris-1 connection ──
            _clear_observers(pg)
            g1 = _drag_and_measure_capture(pg, rect, 780, 260, 275, 420, steps=25)

            assert g1["downEvent"] is not None, "no trusted pointerdown"
            assert g1["downEvent"]["isTrusted"], "pointerdown not trusted"
            assert g1["setCalled"], f"setPointerCapture not called: {g1}"
            assert g1["gotCapture"], f"no gotpointercapture: {g1}"
            assert g1["hasCaptureDuring"], (
                f"hasPointerCapture false during gesture: pid={g1['pointerId']}"
            )
            assert g1["pointerActiveDuring"], (
                f"pointerActive false during gesture: {g1}"
            )

            assert g1["upEvent"] is not None, "no trusted pointerup"
            assert g1["upEvent"]["isTrusted"], "pointerup not trusted"
            assert g1["releaseCalled"], f"releasePointerCapture not called: {g1}"
            assert g1["lostCapture"], f"no lostpointercapture: {g1}"
            assert not g1["hasCaptureAfter"], (
                f"hasPointerCapture true after up: pid={g1['pointerId']}"
            )

            pg.wait_for_function(
                """() => {
          const snap = OceanRescue.YoungWhale.getSnapshot();
          return snap.feedback === null && !snap.inputLocked;
        }""",
                timeout=5000,
            )

            snap1_post = _get_young_whale_snapshot(pg)
            assert not snap1_post["pointerActive"], (
                f"pointerActive not false: {snap1_post}"
            )
            assert snap1_post["stage"] == "towing", f"stage not towing: {snap1_post}"
            assert snap1_post["activeDebrisId"] == "debris-1"
            assert snap1_post["completedDebrisIds"] == []

            # ── Gesture 2: debris-1 towing ──
            _clear_observers(pg)
            g2 = _drag_and_measure_capture(pg, rect, 340, 420, 180, 190, steps=25)

            assert g2["downEvent"] is not None, "no second pointerdown"
            assert g2["downEvent"]["isTrusted"], "second pointerdown not trusted"
            assert g2["setCalled"], f"second setPointerCapture not called: {g2}"
            assert g2["gotCapture"], f"no second gotpointercapture: {g2}"
            assert g2["hasCaptureDuring"], (
                f"hasPointerCapture false during 2nd gesture: pid={g2['pointerId']}"
            )
            assert g2["pointerActiveDuring"], (
                f"pointerActive false during 2nd gesture: {g2}"
            )

            assert g2["upEvent"] is not None, "no second pointerup"
            assert g2["upEvent"]["isTrusted"], "second pointerup not trusted"
            assert g2["releaseCalled"], f"second releasePointerCapture not called: {g2}"
            assert g2["lostCapture"], f"no second lostpointercapture: {g2}"
            assert not g2["hasCaptureAfter"], (
                f"hasPointerCapture true after 2nd up: pid={g2['pointerId']}"
            )

            pg.wait_for_function(
                """() => {
          const snap = OceanRescue.YoungWhale.getSnapshot();
          return snap.feedback === null && !snap.inputLocked;
        }""",
                timeout=5000,
            )

            snap2_post = _get_young_whale_snapshot(pg)
            assert not snap2_post["pointerActive"], (
                f"pointerActive not false 2nd: {snap2_post}"
            )
            assert snap2_post["stage"] == "connection", (
                f"stage not connection: {snap2_post}"
            )
            assert snap2_post["activeDebrisId"] == "debris-2"
            assert snap2_post["completedDebrisIds"] == ["debris-1"]

            # ── Quality gates ──
            assert len(page_errors) == 0, f"page errors: {page_errors}"
            assert len(console_errors) == 0, f"console errors: {console_errors}"

            external = [
                u
                for u in requests_log
                if not u.startswith("http://127.0.0.1:")
                and "data:" not in u
                and "blob:" not in u
            ]
            assert len(external) == 0, f"external requests: {external}"

            context.close()
            browser.close()
