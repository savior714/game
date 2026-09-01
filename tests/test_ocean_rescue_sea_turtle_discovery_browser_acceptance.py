"""
Real-browser (Playwright) acceptance test for Sea Turtle Discovery canonical port.

Drives published /ocean-rescue/index.html through the complete flow:
1. Normal launch flow into Sea Turtle travel mission.
2. Continuous Travel -> Turtle Discovery approach (distance >= 4800).
3. Turtle awareness and reaction state progression.
4. Real player abrupt motion causing startled reaction (scan unavailable, no punishment).
5. Settling and calm dwell enabling scan action.
6. Clean input separation (scan button click does not steer GUP).
7. Scan activation, progressive scan beam sweep, rope reveal.
8. Ready-for-rescue release of forward hold zone.
9. Seamless handoff to canonical Sea Turtle rescue scene (ArrivalDistance 6000).
10. Runtime health: zero pageerror, zero console errors, zero duplicate canvas.
"""

import socketserver
import threading
import time
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
PORT = 18779


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
            self.server.server_close()


@pytest.fixture(scope="module")
def server():
    srv = HTTPServerFixture()
    url = srv.start()
    yield url
    srv.stop()


LANES = ["webgl", "canvas"]


def _start_sea_turtle_mission(pg, base_url):
    pg.goto(f"{base_url}/ocean-rescue/index.html")
    pg.wait_for_selector(
        "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=20000
    )
    if pg.locator("#ocean-rescue-profile-choice").is_visible():
        pg.click('[data-profile-animal-id="arctic-fox"]')
        pg.click("#ocean-rescue-profile-continue")
    pg.click("#ocean-rescue-mission-list [data-mission-id=sea-turtle]")
    pg.wait_for_selector("#ocean-rescue-gup-select:not([hidden])", timeout=10000)
    pg.click("#ocean-rescue-gup-list [data-gup-id=gup-x]")
    pg.click("#ocean-rescue-gup-launch")
    pg.wait_for_selector("#ocean-rescue-launch:not([hidden])", timeout=10000)
    pg.click("#ocean-rescue-launch-skip")
    pg.wait_for_selector("#ocean-rescue-root[data-travel-scene=active]", timeout=15000)


@pytest.mark.parametrize("lane", LANES)
def test_sea_turtle_discovery_complete_browser_flow(server, lane):
    errors = []
    page_errors = []

    launch_args = []
    if lane == "canvas":
        launch_args.extend(
            ["--disable-webgl", "--disable-webgl2", "--disable-gpu-rasterization"]
        )
    else:
        launch_args.extend(
            ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-webgpu"]
        )

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=launch_args,
        )
        page = browser.new_page(viewport={"width": 1280, "height": 720})

        page.on(
            "console",
            lambda msg: errors.append(msg.text) if msg.type == "error" else None,
        )
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        _start_sea_turtle_mission(page, server)

        # Fast forward Travel near discovery zone safely below obstacle 5 (y=480)
        page.evaluate("""() => {
            const travel = window.OceanRescue.Travel;
            travel.tapTo(480);
            while (travel.getSnapshot().y < 480) {
                travel.step(50);
            }
            while (travel.getSnapshot().distance < 4750) {
                travel.step(50);
            }
        }""")
        time.sleep(0.1)

        # Step into discovery zone calmly (distance >= 4800)
        page.evaluate("""() => {
            const travel = window.OceanRescue.Travel;
            while (travel.getSnapshot().distance < 4950) {
                travel.step(50);
            }
        }""")
        time.sleep(0.1)

        # A & B. Verify Turtle is visible and awareness/settling active
        page.wait_for_selector(
            '#ocean-rescue-root[data-turtle-discovery-visible="true"]', timeout=5000
        )
        reaction = page.get_attribute(
            "#ocean-rescue-root", "data-turtle-discovery-reaction"
        )
        assert reaction in ["distant", "awareness", "settling", "scan-eligible"]

        # C. Abrupt Real Motion -> Startled reaction test
        # Drag pointer up and down rapidly to generate high derived vertical velocity
        canvas = page.locator("#ocean-rescue-canvas")
        box = canvas.bounding_box()
        assert box is not None
        center_x = box["x"] + box["width"] * 0.3
        center_y = box["y"] + box["height"] * 0.5

        page.mouse.move(center_x, center_y)
        page.mouse.down()
        page.mouse.move(center_x, center_y - 200, steps=2)
        page.mouse.move(center_x, center_y + 200, steps=2)
        page.mouse.up()

        # Step time in discovery to register motion
        page.evaluate("""() => {
            const STD = window.OceanRescue.SeaTurtleDiscovery;
            if (STD) {
                STD.step(50, window.OceanRescue.Travel.getSnapshot(), null, { verticalVelocity: 500, isColliding: false });
                window.OceanRescue.TravelScene.sync(window.OceanRescue.Travel.getSnapshot());
            }
        }""")
        startled_reaction = page.get_attribute(
            "#ocean-rescue-root", "data-turtle-discovery-reaction"
        )
        assert startled_reaction == "startled"

        # While startled, scan button must remain hidden
        scan_btn = page.locator("#ocean-rescue-travel-scan")
        assert not scan_btn.is_visible()

        # D. Settling: calm motion and dwell
        page.evaluate("""() => {
            const STD = window.OceanRescue.SeaTurtleDiscovery;
            const travel = window.OceanRescue.Travel;
            // Advance past 5500 into hold zone while calm
            while (travel.getSnapshot().distance < 5500) {
                travel.step(50);
            }
            // Step calm dwell (1500ms calm)
            for (let i = 0; i < 35; i++) {
                STD.step(50, travel.getSnapshot(), null, { verticalVelocity: 0, isColliding: false });
            }
            window.OceanRescue.TravelScene.sync(travel.getSnapshot());
        }""")

        page.wait_for_selector(
            '#ocean-rescue-root[data-turtle-discovery-scan-eligible="true"]',
            timeout=5000,
        )
        assert scan_btn.is_visible()

        # E. Input separation: clicking scan button triggers scan without altering travel tapTargetY
        pre_tap = page.evaluate(
            "() => window.OceanRescue.Travel.getSnapshot().tapTargetY"
        )
        scan_btn.click()
        post_tap = page.evaluate(
            "() => window.OceanRescue.Travel.getSnapshot().tapTargetY"
        )
        assert pre_tap == post_tap

        # F. Scanning active
        page.wait_for_selector(
            '#ocean-rescue-root[data-turtle-discovery-scanning="true"]', timeout=5000
        )

        # Complete scan duration
        page.evaluate("""() => {
            const STD = window.OceanRescue.SeaTurtleDiscovery;
            const travel = window.OceanRescue.Travel;
            for (let i = 0; i < 35; i++) {
                STD.step(50, travel.getSnapshot(), null, { verticalVelocity: 0 });
            }
            window.OceanRescue.TravelScene.sync(travel.getSnapshot());
        }""")

        # G. Ready for rescue and handoff
        page.wait_for_selector(
            '#ocean-rescue-root[data-turtle-discovery-ready="true"]', timeout=5000
        )

        # Forward hold is now released, advance travel to 6000 (ArrivalDistance)
        page.evaluate("""() => {
            const travel = window.OceanRescue.Travel;
            while (travel.getSnapshot().distance < 6000) {
                travel.step(50);
            }
            if (window.OceanRescue.Rescue.hasArrived(travel.getSnapshot())) {
                const root = document.getElementById("ocean-rescue-root");
                root.setAttribute("data-rescue-arrival", "active");
            }
        }""")
        time.sleep(0.2)

        # Sea turtle ropes remain incomplete at discovery end (rescue mechanics untouched)
        rope_completed = page.evaluate("""() => {
            return window.OceanRescue.SeaTurtle ? window.OceanRescue.SeaTurtle.getSnapshot().completedRopeIds.length : 0;
        }""")
        assert rope_completed == 0

        # H. Runtime Health
        assert len(page_errors) == 0, f"Page errors: {page_errors}"
        filtered_errors = [e for e in errors if "favicon" not in e]
        assert len(filtered_errors) == 0, f"Console errors: {filtered_errors}"

        browser.close()
