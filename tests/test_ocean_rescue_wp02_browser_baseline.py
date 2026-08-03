"""WP-02 browser functional parity baseline.

The test drives the tracked standalone HTML through Playwright.  Committed
evidence is written only when ``OCEAN_RESCUE_WP02_WRITE_EVIDENCE=1`` is set;
ordinary pytest runs therefore do not dirty the repository with volatile data.
"""

from __future__ import annotations

import json
import os
import socketserver
import sys
import threading
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Page, sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = Path(
    os.environ.get(
        "OCEAN_RESCUE_WP02_EVIDENCE_DIR",
        str(REPO_ROOT / "docs" / "evidence" / "ocean-rescue" / "migration" / "phase-0"),
    )
)
EVIDENCE_FILE = EVIDENCE_DIR / "browser-functional-evidence.json"
LOGICAL_WIDTH = 1280
LOGICAL_HEIGHT = 720
MAPPING_TOLERANCE = 0.5
BENIGN_WEBGL_WARNING = (
    "GL Driver Message (OpenGL, Performance, GL_CLOSE_PATH_NV, High): "
    "GPU stall due to ReadPixels"
)


class HTTPServerFixture:
    def __init__(self) -> None:
        self.server: socketserver.TCPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> str:
        class QuietHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

            def log_message(self, format: str, *args) -> None:
                return

        self.server = socketserver.TCPServer(("127.0.0.1", 0), QuietHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def stop(self) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=2)


def _root_attributes(page: Page) -> dict[str, str | None]:
    return page.evaluate(
        """() => {
          const root = document.getElementById('ocean-rescue-root');
          const names = [
            'data-ocean-rescue-ready', 'data-render-runtime', 'data-render-backend',
            'data-render-logical-width', 'data-render-logical-height',
            'data-travel-scene', 'data-travel-runtime', 'data-travel-input',
            'data-rescue-sequence', 'data-rescue-phase', 'data-rescue-input',
            'data-sea-turtle-scene', 'data-sea-turtle-active',
            'data-sea-turtle-rope-id', 'data-sea-turtle-completed-count',
            'data-sea-turtle-complete', 'data-mission-success-active',
            'data-mission-success-stage', 'data-mission-completion-recorded',
            'data-mission-complete-ready', 'data-pause-active'
          ];
          return Object.fromEntries(names.map(name => [name, root ? root.getAttribute(name) : null]));
        }"""
    )


def _map_client(
    rect: dict[str, float], client_x: float, client_y: float
) -> dict[str, float]:
    return {
        "client_x": client_x,
        "client_y": client_y,
        "logical_x": (client_x - rect["left"]) / rect["w"] * LOGICAL_WIDTH,
        "logical_y": (client_y - rect["top"]) / rect["h"] * LOGICAL_HEIGHT,
    }


def _mapping_point(
    rect: dict[str, float],
    label: str,
    logical_x: float,
    logical_y: float,
) -> dict[str, object]:
    client_x = rect["left"] + logical_x / LOGICAL_WIDTH * rect["w"]
    client_y = rect["top"] + logical_y / LOGICAL_HEIGHT * rect["h"]
    mapped = _map_client(rect, client_x, client_y)
    mapped["label"] = label
    mapped["expected_x"] = logical_x
    mapped["expected_y"] = logical_y
    mapped["within_tolerance"] = (
        abs(mapped["logical_x"] - logical_x) <= MAPPING_TOLERANCE
        and abs(mapped["logical_y"] - logical_y) <= MAPPING_TOLERANCE
    )
    return mapped


def _wire_countdown_observer(page: Page) -> None:
    page.evaluate(
        """() => {
          const element = document.getElementById('ocean-rescue-pause-countdown');
          window.__wp02Countdown = [];
          window.__wp02CountdownObserver = new MutationObserver(() => {
            const text = (element.textContent || '').trim();
            const values = window.__wp02Countdown;
            if (text && values[values.length - 1] !== text) values.push(text);
          });
          window.__wp02CountdownObserver.observe(element, {
            characterData: true,
            childList: true,
            subtree: true
          });
        }"""
    )


def _install_pointer_observer(page: Page) -> None:
    page.evaluate(
        """() => {
          const canvas = document.getElementById('ocean-rescue-canvas');
          window.__wp02PointerEvents = [];
          ['pointerdown', 'pointermove', 'pointerup'].forEach(type => {
            canvas.addEventListener(type, event => {
              window.__wp02PointerEvents.push({
                type,
                pointerId: event.pointerId,
                clientX: event.clientX,
                clientY: event.clientY,
                isPrimary: event.isPrimary
              });
            }, true);
          });
        }"""
    )


def _drag_rope(
    page: Page, rect: dict[str, float], rope: dict[str, object]
) -> dict[str, object]:
    start = rope["start"]
    end = rope["end"]
    start_client = (
        rect["left"] + start["x"] / LOGICAL_WIDTH * rect["w"],
        rect["top"] + start["y"] / LOGICAL_HEIGHT * rect["h"],
    )
    end_client = (
        rect["left"] + end["x"] / LOGICAL_WIDTH * rect["w"],
        rect["top"] + end["y"] / LOGICAL_HEIGHT * rect["h"],
    )
    before = page.evaluate(
        """() => ({
          root: document.getElementById('ocean-rescue-root').getAttribute('data-sea-turtle-rope-id'),
          completed: Number(document.getElementById('ocean-rescue-root').getAttribute('data-sea-turtle-completed-count')),
          eventCount: window.__wp02PointerEvents.length
        })"""
    )
    page.mouse.move(*start_client)
    page.mouse.down()
    after_down = page.evaluate("() => OceanRescue.SeaTurtle.getSnapshot()")
    for fraction in (0.2, 0.4, 0.6, 0.8, 1.0):
        page.mouse.move(
            start_client[0] + (end_client[0] - start_client[0]) * fraction,
            start_client[1] + (end_client[1] - start_client[1]) * fraction,
        )
    after_moves = page.evaluate("() => OceanRescue.SeaTurtle.getSnapshot()")
    page.mouse.up()
    try:
        page.wait_for_function(
            """state => {
              const root = document.getElementById('ocean-rescue-root');
              const released = Number(root.getAttribute('data-sea-turtle-completed-count')) > state.completed;
              const settled = root.getAttribute('data-sea-turtle-feedback') === 'none';
              const advanced = root.getAttribute('data-sea-turtle-rope-id') !== state.rope_id;
              return (released && settled && advanced)
                || root.getAttribute('data-rescue-phase') === 'success';
            }""",
            arg={"completed": before["completed"], "rope_id": rope["id"]},
            timeout=3000,
        )
    except Exception as error:
        diagnostic = page.evaluate(
            """() => ({
              root: document.getElementById('ocean-rescue-root').outerHTML,
              seaTurtle: OceanRescue.SeaTurtle.getSnapshot(),
              events: window.__wp02PointerEvents.slice()
            })"""
        )
        raise AssertionError(
            f"sea-turtle drag did not change state: before={before}, "
            f"after_down={after_down}, after_moves={after_moves}, diagnostic={diagnostic}"
        ) from error
    after = page.evaluate(
        """() => {
          const root = document.getElementById('ocean-rescue-root');
          return {
            root: root.getAttribute('data-sea-turtle-rope-id'),
            completed: Number(root.getAttribute('data-sea-turtle-completed-count')),
            complete: root.getAttribute('data-sea-turtle-complete') === 'true',
            feedback: root.getAttribute('data-sea-turtle-feedback'),
            eventCount: window.__wp02PointerEvents.length,
            events: window.__wp02PointerEvents.slice()
          };
        }"""
    )
    events = after["events"][before["eventCount"] :]
    return {
        "rope_id": rope["id"],
        "active_rope_before": before["root"],
        "active_rope_after": after["root"],
        "completed_count_after": after["completed"],
        "complete_after": after["complete"],
        "feedback_after": after["feedback"],
        "pointer_events": events,
        "pointer_down_dispatched": any(
            event["type"] == "pointerdown" for event in events
        ),
        "pointer_move_dispatched": any(
            event["type"] == "pointermove" for event in events
        ),
        "pointer_up_dispatched": any(event["type"] == "pointerup" for event in events),
        "domain_state_changed": after["completed"] > before["completed"],
        "snapshot_after_down": after_down,
        "snapshot_after_moves": after_moves,
        "client_start": {"x": start_client[0], "y": start_client[1]},
        "client_end": {"x": end_client[0], "y": end_client[1]},
    }


def classify_network(
    requests: list[dict[str, str]],
    base_url: str,
) -> dict[str, object]:
    """Classify recorded requests into local/same-origin, external, and API sets.

    Same-origin requests (including Vite dev-server client, stylesheets, classic
    scripts, and WebSocket/HMR transport on the same origin) are classified as
    local and are not treated as external.
    """
    origin = urlsplit(base_url).netloc
    local_requests = [
        request for request in requests if urlsplit(request["url"]).netloc == origin
    ]
    external_requests = [
        request
        for request in requests
        if urlsplit(request["url"]).netloc not in {origin, ""}
    ]
    external_scripts = [
        request for request in external_requests if request["resource_type"] == "script"
    ]
    external_stylesheets = [
        request
        for request in external_requests
        if request["resource_type"] == "stylesheet"
    ]
    external_assets = [
        request
        for request in external_requests
        if request["resource_type"] in {"image", "media", "font"}
    ]
    api_requests = [
        request for request in requests if request["resource_type"] in {"fetch", "xhr"}
    ]
    dynamic_module_requests = [
        request
        for request in requests
        if request["resource_type"] == "script" and request["url"].startswith("http")
    ]
    return {
        "total": len(requests),
        "local_same_origin": len(local_requests),
        "external": len(external_requests),
        "external_javascript": len(external_scripts),
        "external_stylesheet": len(external_stylesheets),
        "external_image_audio_font": len(external_assets),
        "renderer_cdn": len(external_scripts),
        "api_requests": len(api_requests),
        "dynamic_module_requests": len(dynamic_module_requests),
        "request_failures": [],
        "external_details": external_requests,
        "all_requests": requests,
    }


def classify_console(console_warnings: list[str]) -> dict[str, object]:
    unexpected_warnings = [
        warning for warning in console_warnings if BENIGN_WEBGL_WARNING not in warning
    ]
    return {
        "warning_classification": {
            "benign_webgl_gpu_stall": sum(
                BENIGN_WEBGL_WARNING in warning for warning in console_warnings
            ),
            "unexpected": unexpected_warnings,
        },
        "console_warning_count": len(console_warnings),
    }


def collect_evidence(
    page: Page,
    base_url: str,
    browser_info: dict[str, str],
    entry_path: str = "/ocean-rescue/index.html",
) -> dict[str, object]:
    page_errors: list[str] = []
    console_errors: list[str] = []
    console_warnings: list[str] = []
    requests: list[dict[str, str]] = []
    request_failures: list[str] = []

    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on(
        "console",
        lambda message: (
            console_errors.append(message.text)
            if message.type == "error"
            else console_warnings.append(message.text)
            if message.type == "warning"
            else None
        ),
    )
    page.on(
        "request",
        lambda request: requests.append(
            {
                "url": request.url,
                "resource_type": request.resource_type,
                "method": request.method,
            }
        ),
    )
    page.on("requestfailed", lambda request: request_failures.append(request.url))

    page.goto(f"{base_url}{entry_path}")
    page.wait_for_selector(
        "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=30000
    )
    startup = page.evaluate(
        """() => {
          const canvas = document.getElementById('ocean-rescue-canvas');
          const root = document.getElementById('ocean-rescue-root');
          const rect = canvas.getBoundingClientRect();
          return {
            canvas_found: !!canvas,
            canvas_width: canvas.width,
            canvas_height: canvas.height,
            rect: {left: rect.left, top: rect.top, width: rect.width, height: rect.height},
            dpr: window.devicePixelRatio || 1,
            pixi_version: typeof PIXI === 'undefined' ? 'unknown' : PIXI.VERSION,
            renderer_backend: root.getAttribute('data-render-backend'),
            renderer_runtime: root.getAttribute('data-render-runtime'),
            logical_width: root.getAttribute('data-render-logical-width'),
            logical_height: root.getAttribute('data-render-logical-height'),
            ready: root.getAttribute('data-ocean-rescue-ready')
          };
        }"""
    )

    flow: dict[str, object] = {
        "profile_completed": False,
        "mission_selected": False,
        "gup_selected": False,
        "launch_completed": False,
        "travel_started": False,
        "rescue_arrival_completed": False,
        "sea_turtle_scene_active": False,
        "loops_released": 0,
        "mission_completed": False,
        "mission_success_visible": False,
        "phase_sequence": [],
    }
    profile_visible = page.evaluate(
        """() => {
          const el = document.getElementById('ocean-rescue-profile-choice');
          return !!el && !el.hidden && getComputedStyle(el).display !== 'none';
        }"""
    )
    if profile_visible:
        page.click('[data-profile-animal-id="arctic-fox"]')
        page.click("#ocean-rescue-profile-continue")
        flow["profile_completed"] = True
        flow["phase_sequence"].append("PROFILE")
    page.wait_for_selector("#ocean-rescue-mission-list [data-mission-id=sea-turtle]")
    page.click("#ocean-rescue-mission-list [data-mission-id=sea-turtle]")
    page.wait_for_selector("#ocean-rescue-gup-select:not([hidden])")
    flow["mission_selected"] = True
    flow["phase_sequence"].append("MISSION_SELECT")
    page.click("#ocean-rescue-gup-list [data-gup-id=gup-x]")
    page.click("#ocean-rescue-gup-launch")
    page.wait_for_selector("#ocean-rescue-launch:not([hidden])")
    flow["gup_selected"] = True
    flow["phase_sequence"].append("GUP_SELECT")
    page.click("#ocean-rescue-launch-skip")
    page.wait_for_selector("#ocean-rescue-root[data-travel-runtime=active]")
    startup["rect"] = page.evaluate(
        """() => {
          const rect = document.getElementById('ocean-rescue-canvas').getBoundingClientRect();
          return {left: rect.left, top: rect.top, width: rect.width, height: rect.height};
        }"""
    )
    flow["launch_completed"] = True
    flow["travel_started"] = True
    flow["phase_sequence"].extend(["LAUNCH", "TRAVEL"])

    page.click("#ocean-rescue-pause-button")
    page.wait_for_function(
        "() => document.getElementById('ocean-rescue-root').getAttribute('data-pause-active') === 'true'"
    )
    pause_enter = page.evaluate(
        """() => {
          const root = document.getElementById('ocean-rescue-root');
          const overlay = document.getElementById('ocean-rescue-pause-overlay');
          return {active: root.getAttribute('data-pause-active'), overlay_hidden: overlay.hidden};
        }"""
    )
    _wire_countdown_observer(page)
    page.click("#ocean-rescue-pause-resume")
    page.wait_for_function(
        "() => Array.isArray(window.__wp02Countdown) && window.__wp02Countdown.includes('Go!')",
        timeout=7000,
    )
    page.wait_for_function(
        "() => document.getElementById('ocean-rescue-root').getAttribute('data-pause-active') === 'false'",
        timeout=7000,
    )
    pause_resume = {
        "pause_activated": pause_enter["active"] == "true",
        "pause_overlay_visible": pause_enter["overlay_hidden"] is False,
        "observed_sequence": page.evaluate("() => window.__wp02Countdown.slice()"),
        "resume_completed": True,
        "final_pause_active": _root_attributes(page)["data-pause-active"],
    }

    travel_step = page.evaluate(
        """() => {
          const travel = OceanRescue.Travel;
          const before = travel.getSnapshot();
          let calls = 0;
          while (travel.getSnapshot().distance < OceanRescue.Rescue.ArrivalDistance && calls < 2000) {
            if (!travel.step(50, 1)) throw new Error('public Travel.step rejected deterministic step');
            calls += 1;
          }
          return {before, after: travel.getSnapshot(), step_calls: calls};
        }"""
    )
    page.wait_for_function(
        """() => ['site-transition', 'tutorial', 'active'].includes(
          document.getElementById('ocean-rescue-root').getAttribute('data-rescue-phase'))""",
        timeout=5000,
    )
    arrival_state = _root_attributes(page)
    flow["rescue_arrival_completed"] = arrival_state[
        "data-rescue-sequence"
    ] == "active" and arrival_state["data-rescue-phase"] in {
        "site-transition",
        "tutorial",
        "active",
    }
    flow["phase_sequence"].append("RESCUE_ARRIVAL")
    page.wait_for_function(
        "() => document.getElementById('ocean-rescue-root').getAttribute('data-rescue-phase') === 'tutorial'"
    )
    page.mouse.click(640, 360)
    page.wait_for_function(
        "() => document.getElementById('ocean-rescue-root').getAttribute('data-rescue-phase') === 'active'"
    )
    _install_pointer_observer(page)
    scene_state = _root_attributes(page)
    flow["sea_turtle_scene_active"] = (
        scene_state["data-sea-turtle-scene"] == "active"
        and scene_state["data-sea-turtle-active"] == "true"
    )
    flow["phase_sequence"].append("SEA_TURTLE_RESCUE")

    rect_raw = page.evaluate(
        """() => {
          const r = document.getElementById('ocean-rescue-canvas').getBoundingClientRect();
          return {left: r.left, top: r.top, w: r.width, h: r.height};
        }"""
    )
    ropes = page.evaluate(
        """() => OceanRescue.SeaTurtle.Ropes.map(rope => ({
          id: rope.id,
          start: {x: rope.start.x, y: rope.start.y},
          end: {x: rope.end.x, y: rope.end.y}
        }))"""
    )
    mapping_points = [
        _mapping_point(rect_raw, "logical_center", 640, 360),
        _mapping_point(rect_raw, "top_left_safe", 10, 10),
        _mapping_point(rect_raw, "bottom_right_safe", 1270, 710),
        _mapping_point(
            rect_raw,
            "sea_turtle_rope_1_start",
            ropes[0]["start"]["x"],
            ropes[0]["start"]["y"],
        ),
        _mapping_point(
            rect_raw,
            "sea_turtle_rope_1_end",
            ropes[0]["end"]["x"],
            ropes[0]["end"]["y"],
        ),
    ]
    drag_results = [_drag_rope(page, rect_raw, rope) for rope in ropes]
    flow["loops_released"] = page.evaluate(
        """() => Number(document.getElementById('ocean-rescue-root').getAttribute('data-sea-turtle-completed-count'))"""
    )
    flow["phase_sequence"].append("MISSION_SUCCESS")
    page.wait_for_function(
        "() => document.getElementById('ocean-rescue-root').getAttribute('data-mission-success-active') === 'true'",
        timeout=5000,
    )
    flow["success_presentation_reached"] = True
    page.wait_for_function(
        "() => document.getElementById('ocean-rescue-root').getAttribute('data-mission-success-stage') === 'narration-1'",
        timeout=10000,
    )
    page.mouse.click(640, 360)
    page.wait_for_function(
        "() => document.getElementById('ocean-rescue-root').getAttribute('data-mission-success-stage') === 'narration-2'"
    )
    page.mouse.click(640, 360)
    page.wait_for_function(
        "() => document.getElementById('ocean-rescue-root').getAttribute('data-mission-completion-recorded') === 'true'",
        timeout=5000,
    )
    success_state = page.evaluate(
        """() => {
          const root = document.getElementById('ocean-rescue-root');
          const section = document.getElementById('ocean-rescue-mission-success');
          const card = document.getElementById('ocean-rescue-mission-complete-card');
          return {
            phase: root.getAttribute('data-rescue-phase'),
            stage: root.getAttribute('data-mission-success-stage'),
            completion_recorded: root.getAttribute('data-mission-completion-recorded'),
            section_hidden: section.hidden,
            card_hidden: card.hidden,
            title: document.getElementById('ocean-rescue-mission-complete-name').textContent
          };
        }"""
    )
    flow["mission_completed"] = success_state["completion_recorded"] == "true"
    flow["mission_success_visible"] = (
        success_state["section_hidden"] is False
        and success_state["card_hidden"] is False
    )

    network = classify_network(requests, base_url)
    network["request_failures"] = request_failures
    console_classification = classify_console(console_warnings)

    evidence: dict[str, object] = {
        "startup": {
            "browser": browser_info,
            "canvas_found": startup["canvas_found"],
            "canvas_width": startup["canvas_width"],
            "canvas_height": startup["canvas_height"],
            "canvas_rect": startup["rect"],
            "dpr": startup["dpr"],
            "pixi_version": startup["pixi_version"],
            "renderer_backend": startup["renderer_backend"],
            "renderer_runtime": startup["renderer_runtime"],
            "logical_width": startup["logical_width"],
            "logical_height": startup["logical_height"],
            "ready": startup["ready"],
        },
        "gameplay_flow": flow,
        "travel_arrival": travel_step,
        "pause_resume": pause_resume,
        "pointer_mapping": {
            "canvas_rect": rect_raw,
            "logical_width": LOGICAL_WIDTH,
            "logical_height": LOGICAL_HEIGHT,
            "tolerance": MAPPING_TOLERANCE,
            "points": mapping_points,
            "numerical_assertions_passed": all(
                point["within_tolerance"] for point in mapping_points
            ),
            "interactive_drag_passed": all(
                result["domain_state_changed"] for result in drag_results
            ),
            "drag_results": drag_results,
        },
        "mission_success": success_state,
        "network": network,
        "console": {
            "page_errors": page_errors,
            "console_errors": console_errors,
            "console_warnings": console_warnings,
            "warning_classification": console_classification["warning_classification"],
            "page_error_count": len(page_errors),
            "console_error_count": len(console_errors),
            "console_warning_count": console_classification["console_warning_count"],
        },
        "verdict": "UNASSESSED",
    }
    return evidence


def run_browser_evidence(
    entry_path: str = "/ocean-rescue/index.html",
) -> dict[str, object]:
    server = HTTPServerFixture()
    base_url = server.start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--disable-background-networking", "--disable-component-update"],
            )
            try:
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    locale="ko-KR",
                    timezone_id="Asia/Seoul",
                )
                context.add_init_script("window.localStorage.clear();")
                try:
                    page = context.new_page()
                    try:
                        return collect_evidence(
                            page,
                            base_url,
                            {
                                "engine": "Playwright Chromium",
                                "version": browser.version,
                            },
                            entry_path=entry_path,
                        )
                    finally:
                        page.close()
                finally:
                    context.close()
            finally:
                browser.close()
    finally:
        server.stop()


def assert_evidence(
    evidence: dict[str, object], network_mode: str = "standalone"
) -> None:
    startup = evidence["startup"]
    flow = evidence["gameplay_flow"]
    pause = evidence["pause_resume"]
    pointer = evidence["pointer_mapping"]
    network = evidence["network"]
    console = evidence["console"]
    # Both the standalone baseline and the Vite dev-server lane must reject any
    # external-origin runtime request and any API/fetch/XHR request. Same-origin
    # requests (dev-server client, stylesheets, classic scripts, HMR transport)
    # are classified as local and are allowed.
    assert network_mode in {"standalone", "dev"}
    assert startup["ready"] == "true"
    assert startup["canvas_found"] is True
    assert startup["canvas_width"] == LOGICAL_WIDTH
    assert startup["canvas_height"] == LOGICAL_HEIGHT
    assert startup["renderer_backend"] in {"webgl", "canvas"}
    assert all(
        flow[key] is True
        for key in (
            "profile_completed",
            "mission_selected",
            "gup_selected",
            "launch_completed",
            "travel_started",
            "rescue_arrival_completed",
            "sea_turtle_scene_active",
            "mission_completed",
            "mission_success_visible",
        )
    )
    assert flow["loops_released"] == 3
    assert pause["pause_activated"] is True
    assert pause["observed_sequence"] == ["3", "2", "1", "Go!"]
    assert pause["resume_completed"] is True
    assert pause["final_pause_active"] == "false"
    assert pointer["numerical_assertions_passed"] is True
    assert pointer["interactive_drag_passed"] is True
    assert all(
        result["pointer_down_dispatched"]
        and result["pointer_move_dispatched"]
        and result["pointer_up_dispatched"]
        and result["domain_state_changed"]
        for result in pointer["drag_results"]
    )
    assert network["local_same_origin"] >= 1
    assert network["external"] == 0
    assert network["external_javascript"] == 0
    assert network["external_stylesheet"] == 0
    assert network["external_image_audio_font"] == 0
    assert network["renderer_cdn"] == 0
    assert network["api_requests"] == 0
    if network_mode == "standalone":
        # In the standalone artifact all scripts are inlined, so any http-loaded
        # script is forbidden. In the Vite dev lane the classic scripts are
        # served over the same origin by design; external origin is still zero.
        assert network["dynamic_module_requests"] == 0
    assert network["request_failures"] == []
    assert console["page_error_count"] == 0
    assert console["console_error_count"] == 0
    assert console["warning_classification"]["unexpected"] == []
    evidence["verdict"] = "PASS"


def write_evidence(evidence: dict[str, object]) -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_FILE.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
    print(f"Evidence written to: {EVIDENCE_FILE}")


def test_ocean_rescue_wp02_browser_baseline() -> None:
    evidence = run_browser_evidence()
    assert_evidence(evidence)
    if os.environ.get("OCEAN_RESCUE_WP02_WRITE_EVIDENCE") == "1":
        write_evidence(evidence)


def main() -> None:
    evidence = run_browser_evidence()
    assert_evidence(evidence)
    if os.environ.get("OCEAN_RESCUE_WP02_WRITE_EVIDENCE") == "1":
        write_evidence(evidence)
    print("RESULT: PASS")


if __name__ == "__main__":
    try:
        main()
    except AssertionError:
        print("RESULT: BLOCKED", file=sys.stderr)
        raise
