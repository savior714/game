"""
Real-browser (Chromium) acceptance test for the TRAVEL distance progress HUD.

Drives the published single HTML `/ocean-rescue/index.html` through the normal
product flow over loopback HTTP and verifies the progress bar contract:

- HUD is hidden outside TRAVEL and visible during TRAVEL.
- The bar always equals ``round(min(distance / Rescue.ArrivalDistance, 1) * 100)``
  derived from the authoritative ``OceanRescue.Travel.getSnapshot()``.
- The value increases monotonically as the GUP travels.
- While paused the value is frozen; after resume it continues from the same value.
- Exiting to the mission menu hides and resets the HUD; a new run starts at 0%.
- Both renderer lanes are exercised: WebGL/WebGL2 (preferred) and Canvas
  fallback (`--disable-webgl`).
- Zero external-origin requests, zero CSP violations, zero page/console errors.

Sampling runs inside the page through a single async ``page.evaluate`` so that
protocol round-trips are not starved by the software-WebGL renderer, matching
the pattern proven by the existing collision-impact browser acceptance test.
The arrival-transition hide is covered deterministically by the VM harness in
``test_ocean_rescue_travel_progress_hud.py`` (real-time arrival takes ~50s).
"""

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
PORT = 18768
EVIDENCE_DIR = Path(
    os.environ.get(
        "OCEAN_RESCUE_TRAVEL_PROGRESS_EVIDENCE_DIR",
        "/tmp/AIDENGAME-OCEAN-RESCUE-TRAVEL-DISTANCE-PROGRESS-HUD-01",
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


def _expected_percent(distance: float, arrival: float) -> int:
    ratio = max(0.0, min(1.0, distance / arrival))
    return round(ratio * 100)


_COLLECT_BODY = """() => {
  const el = document.getElementById('ocean-rescue-travel-progress');
  const bar = document.getElementById('ocean-rescue-travel-progress-bar');
  const value = document.getElementById('ocean-rescue-travel-progress-value');
  const label = document.getElementById('ocean-rescue-travel-progress-label');
  const help = document.getElementById('ocean-rescue-travel-help');
  const root = document.getElementById('ocean-rescue-root');
  const travel = OceanRescue.Travel.getSnapshot();
  return {
    hidden: el ? el.hidden : null,
    value: bar ? bar.value : null,
    text: value ? value.textContent : null,
    state: el ? el.getAttribute('data-travel-progress-state') : null,
    percent: el ? el.getAttribute('data-travel-progress-percent') : null,
    distance: el ? el.getAttribute('data-travel-progress-distance') : null,
    arrival: el ? el.getAttribute('data-travel-progress-arrival-distance') : null,
    label: label ? label.textContent.trim() : null,
    help: help ? help.textContent.replace(/\\s+/g, ' ').trim() : null,
    travelDistance: travel.distance,
    arrivalDistance: OceanRescue.Rescue.ArrivalDistance,
    phase: OceanRescue.State.getSnapshot().phase,
    paused: root ? root.getAttribute('data-pause-active') : null,
  };
}"""


def _collect_progress(pg):
    return pg.evaluate(_COLLECT_BODY)


def _sample_progress_window(pg, sample_ms=1200, step_ms=80):
    source = (
        "async ({ sampleMs, stepMs, collectSource }) => {"
        "  const collect = eval('(' + collectSource + ')');"
        "  const samples = [];"
        "  const start = performance.now();"
        "  while (performance.now() - start < sampleMs) {"
        "    samples.push(collect());"
        "    await new Promise((resolve) => setTimeout(resolve, stepMs));"
        "  }"
        "  return samples;"
        "}"
    )
    return pg.evaluate(
        source,
        {"sampleMs": sample_ms, "stepMs": step_ms, "collectSource": _COLLECT_BODY},
    )


def _frozen_samples(pg, gap_ms=400):
    source = (
        "async ({ gapMs, collectSource }) => {"
        "  const collect = eval('(' + collectSource + ')');"
        "  const a = collect();"
        "  await new Promise((resolve) => setTimeout(resolve, gapMs));"
        "  const b = collect();"
        "  return { a, b };"
        "}"
    )
    return pg.evaluate(source, {"gapMs": gap_ms, "collectSource": _COLLECT_BODY})


_READABILITY_BODY = """() => {
  const panel = document.getElementById('ocean-rescue-travel-progress');
  const bar = document.getElementById('ocean-rescue-travel-progress-bar');
  const value = document.getElementById('ocean-rescue-travel-progress-value');
  const label = document.getElementById('ocean-rescue-travel-progress-label');
  const help = document.getElementById('ocean-rescue-travel-help');
  const cs = (el) => getComputedStyle(el);
  const rect = (el) => el.getBoundingClientRect();
  const panelRect = rect(panel);
  const helpRect = rect(help);
  return {
    hidden: panel.hidden,
    state: panel.getAttribute('data-travel-progress-state'),
    helpText: help.textContent.replace(/\\s+/g, ' ').trim(),
    label: label ? label.textContent.trim() : null,
    barHeight: parseFloat(cs(bar).height),
    barWidth: parseFloat(cs(bar).width),
    percentFontSize: parseFloat(cs(value).fontSize),
    panelPaddingTop: parseFloat(cs(panel).paddingTop),
    panelPaddingLeft: parseFloat(cs(panel).paddingLeft),
    panelRadius: parseFloat(cs(panel).borderRadius),
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
    innerHeight: window.innerHeight,
    panelLeft: panelRect.left,
    panelRight: panelRect.right,
    panelBottom: panelRect.bottom,
    helpTop: helpRect.top,
    helpRight: helpRect.right,
  };
}"""


def _readability_report(pg):
    return pg.evaluate(_READABILITY_BODY)


def _go_through_normal_flow(pg, base_url):
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


def _assert_copy_contract(s):
    assert s["label"] and (
        "progress" in s["label"].lower() or "rescue" in s["label"].lower()
    ), f"missing progress label: {s}"
    assert s["help"], f"missing travel help copy: {s}"
    lower = s["help"].lower()
    assert "drag" in lower, f"help must teach drag: {s['help']!r}"
    assert "tap" in lower, f"help must teach tap: {s['help']!r}"
    assert "dodge" in lower or "avoid" in lower or "obstacle" in lower, (
        f"help must hint at obstacles: {s['help']!r}"
    )


def _verify_active_travel_snapshots(samples, label):
    assert samples, f"{label}: no samples collected"
    assert samples[0]["hidden"] is False, f"{label}: HUD must be visible during TRAVEL"
    prev = -1
    for s in samples:
        assert s["phase"] == "TRAVEL", f"{label}: unexpected phase {s['phase']}"
        assert s["state"] == "active", f"{label}: {s}"
        assert s["arrival"] == "6000", f"{label}: {s}"
        assert s["value"] == _expected_percent(
            s["travelDistance"], s["arrivalDistance"]
        ), f"{label}: HUD must mirror authoritative distance: {s}"
        assert s["value"] >= prev, (
            f"{label}: value must be monotonic non-decreasing: {prev} -> {s['value']}"
        )
        prev = s["value"]
        _assert_copy_contract(s)
    return samples


def _run_travel_and_resume(pg, base_url):
    _go_through_normal_flow(pg, base_url)
    first = _collect_progress(pg)
    assert first["hidden"] is False, "progress HUD must be visible during TRAVEL"
    assert first["phase"] == "TRAVEL"
    assert first["state"] == "active", first
    assert first["value"] <= 3, (
        f"progress should be near 0 right after launch, got {first['value']}"
    )

    samples = _verify_active_travel_snapshots(
        [first] + _sample_progress_window(pg), "travel"
    )
    assert samples[-1]["value"] > first["value"], (
        "progress must advance over the sampling window"
    )

    pg.click("#ocean-rescue-pause-button")
    pg.wait_for_selector("#ocean-rescue-root[data-pause-active=true]", timeout=5000)
    frozen = _frozen_samples(pg)
    assert frozen["a"]["value"] == frozen["b"]["value"], (
        "value must be frozen while paused"
    )
    assert frozen["a"]["travelDistance"] == frozen["b"]["travelDistance"], (
        "distance must be frozen while paused"
    )

    pg.click("#ocean-rescue-pause-resume")
    pg.wait_for_selector("#ocean-rescue-root[data-pause-active=false]", timeout=10000)
    resumed = _sample_progress_window(pg, sample_ms=900, step_ms=90)
    assert resumed, "no samples after resume"
    assert resumed[0]["hidden"] is False, "HUD must be visible again after resume"
    assert resumed[0]["value"] >= frozen["a"]["value"], (
        f"resume must continue from frozen value: {frozen['a']['value']} -> {resumed[0]['value']}"
    )
    assert resumed[-1]["value"] > frozen["a"]["value"], (
        "progress must resume increasing after resume"
    )
    _verify_active_travel_snapshots(resumed, "resume")
    return {"first": first, "last": resumed[-1], "frozen": frozen["a"]}


def _run_menu_exit_and_second_run(pg, base_url):
    _go_through_normal_flow(pg, base_url)
    samples = _verify_active_travel_snapshots(
        [_collect_progress(pg)] + _sample_progress_window(pg, sample_ms=500), "menu"
    )

    pg.click("#ocean-rescue-pause-button")
    pg.wait_for_selector("#ocean-rescue-root[data-pause-active=true]", timeout=5000)
    pg.click("#ocean-rescue-pause-menu-button")
    pg.wait_for_selector("#ocean-rescue-mission-select", timeout=8000)
    menu = _collect_progress(pg)
    assert menu["hidden"] is True, "HUD must be hidden on mission select"
    assert menu["state"] == "hidden", menu
    assert menu["value"] == 0, "HUD value must reset to 0 on mission select"

    _relaunch_second_run(pg)
    second = _collect_progress(pg)
    assert second["hidden"] is False, "HUD must be visible on the second run"
    assert second["state"] == "active", second
    assert second["value"] == _expected_percent(
        second["travelDistance"], second["arrivalDistance"]
    )
    assert second["value"] <= 3, f"second run must start near 0%, got {second['value']}"
    return {"menu": menu, "second": second, "travel": samples}


def _relaunch_second_run(pg):
    pg.click("#ocean-rescue-mission-list [data-mission-id=sea-turtle]")
    pg.wait_for_selector("#ocean-rescue-gup-select:not([hidden])", timeout=10000)
    pg.click("#ocean-rescue-gup-list [data-gup-id=gup-x]")
    pg.click("#ocean-rescue-gup-launch")
    pg.wait_for_selector("#ocean-rescue-launch:not([hidden])", timeout=10000)
    pg.click("#ocean-rescue-launch-skip")
    pg.wait_for_selector("#ocean-rescue-root[data-travel-scene=active]", timeout=15000)


def _run_scenario(pg, base_url):
    page_errors = []
    console_errors = []
    requests = []

    pg.on("pageerror", lambda e: page_errors.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and console_errors.append(m.text))
    pg.on("request", lambda r: requests.append(r.url))

    # Non-TRAVEL phase: HUD must be hidden before any mission is started.
    pg.goto(f"{base_url}/ocean-rescue/index.html")
    pg.wait_for_selector(
        "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=20000
    )
    initial = _collect_progress(pg)
    assert initial["hidden"] is True, "progress HUD must be hidden before TRAVEL"
    _assert_copy_contract(initial)

    travel = _run_travel_and_resume(pg, base_url)

    menu = _run_menu_exit_and_second_run(pg, base_url)

    base = f"{base_url}/"
    external = sorted(u for u in set(requests) if not u.startswith(base))
    csp = pg.evaluate("() => window.__cspViolations || []")

    return {
        "initial": initial,
        "travel": travel,
        "menu": menu,
        "externalRequests": external,
        "pageErrors": page_errors,
        "consoleErrors": console_errors,
        "cspViolations": csp,
        "requestCount": len(set(requests)),
    }


@pytest.mark.browser
class TestTravelProgressBrowserAcceptance:
    @pytest.mark.parametrize("backend", LANES)
    def test_progress_hud_per_lane(self, server, backend):
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
            result = _run_scenario(pg, server)
            context.close()
            browser.close()

        (evidence / f"{backend}-progress.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        )

        assert result["externalRequests"] == [], result["externalRequests"]
        assert result["pageErrors"] == [], result["pageErrors"]
        assert result["consoleErrors"] == [], result["consoleErrors"]
        assert result["cspViolations"] == [], result["cspViolations"]

    @pytest.mark.browser
    def test_progress_hud_readability_at_320px(self, server):
        evidence = EVIDENCE_DIR / "readability-320px"
        evidence.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--disable-webgl"])
            context = browser.new_context(
                viewport={"width": 320, "height": 568},
                locale="en-US",
            )
            pg = context.new_page()
            _go_through_normal_flow(pg, server)
            report = _readability_report(pg)
            context.close()
            browser.close()

        (evidence / "readability.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        )

        assert report["hidden"] is False, "HUD must be visible during TRAVEL"
        assert report["state"] == "active", report
        assert report["label"] and "progress" in report["label"].lower(), report
        assert report["helpText"] and "drag" in report["helpText"].lower(), report
        assert report["helpText"] and "tap" in report["helpText"].lower(), report

        assert report["scrollWidth"] <= report["innerWidth"], (
            f"no horizontal page overflow at 320px: {report}"
        )
        assert (
            report["panelLeft"] >= 0 and report["panelRight"] <= report["innerWidth"]
        ), f"progress panel must stay inside the 320px viewport: {report}"
        assert report["panelBottom"] <= report["innerHeight"], (
            f"progress panel must stay inside the vertical viewport: {report}"
        )
        assert report["helpTop"] >= 0 and report["helpRight"] <= report["innerWidth"], (
            f"help bubble must stay inside the 320px viewport: {report}"
        )

        assert report["barHeight"] >= 16, f"bar height below minimum: {report}"
        assert report["barWidth"] >= 140, f"bar width below minimum: {report}"
        assert report["percentFontSize"] >= 18, f"percent below minimum: {report}"
        assert report["panelPaddingTop"] >= 12, f"panel padding too small: {report}"
        assert report["panelPaddingLeft"] >= 12, f"panel padding too small: {report}"
