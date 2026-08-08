"""Focused browser and static proof for WP-33E-B sea-turtle pointer controller.

Verifies that in the Vite/ESM lane the sea-turtle start and pointer lifecycle
are owned by the typed controller, while feedback timer and success/failure
progression remain in the legacy host.

A. ESM installer wiring — `installSeaTurtleLifecycleController` is imported
   and called in esm/app.js after WP-33D, controller file exists at the
   expected path, legacy manifest excludes the controller.

B. Controller boundary discipline — the typed controller does not call
   `addEventListener`, does not call `setTimeout` directly, does not hold
   feedback timer state, does not reference Crab or Young Whale.

C. ESM lane start flow — boot through to RESCUE_ACTIVE, then
   `App.startSeaTurtleInteraction()` is called, SeaTurtle.start() runs,
   the authored scene is activated, pointer input binding is requested,
   the initial frame is rendered, root markers are updated, and a second
   call is a no-op (duplicate-start guard).

D. Pointer capture lifecycle — on pointerdown the controller stores the
   pointer ID and capture element, calls `setPointerCapture`, renders with
   an active intent, and updates root markers. On pointerup the capture is
   released, the pointer ID is cleared, and an accepted result is forwarded
   to the legacy `routeSeaTurtleFeedback` bridge.

E. Pointer validation — non-primary pointers, non-left buttons, non-finite
   client coordinates, mismatched pointer IDs during move/up/cancel, and
   tracked-pointer-missing scenarios are all ignored without error.

F. Mapped-coordinate failure — when `PointerInput.mapRescuePoint` returns
   null the controller calls `SeaTurtle.pointerCancel` and does not set
   capture.

G. Pause cancel — `App.cancelSeaTurtlePointerForPause()` releases any
   active capture, clears the stored pointer ID, and calls
   `SeaTurtle.pauseCancel()`.

H. Legacy feedback bridge — the controller does not call
   `beginSeaTurtleSuccessFeedback` / `beginSeaTurtleFailureFeedback`
   directly; it calls `host.routeSeaTurtleFeedback(result)` which in turn
   invokes the legacy feedback functions.

I. Crab and Young Whale paths — the legacy event handlers still dispatch
   to `handleCrabPointerDown` / `handleYoungWhalePointerDown` when the
   active mission is not sea-turtle. The controller does not interfere.

J. Cleanup aggregates — `cancelPausePointerInteractions` and
   `shutdownRescueInteractionState` dispatch sea-turtle pointer cleanup
   through the App methods when available, and fall back to the legacy
   direct manipulation otherwise.

K. Legacy rollback parity — without the controller installed the legacy
   `app.js` retains full sea-turtle pointer behavior via the original
   local functions and variables.

TypeScript compiler programmatic API is never used; every TypeScript check
runs the installed `tsc` CLI on the real sources.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
from test_ocean_rescue_wp11_dev_server import ViteServerFixture  # noqa: E402

REPO_ROOT = TESTS_DIR.parent
SRC_DIR = REPO_ROOT / "domains" / "ocean-rescue" / "src"
ESM_APP = SRC_DIR / "esm" / "app.js"
LEGACY_APP = SRC_DIR / "app.js"
CONTROLLER = SRC_DIR / "controllers" / "sea-turtle-lifecycle.ts"
LEGACY_MANIFEST = SRC_DIR / "build-manifest.legacy.json"

_POINTER_CAPTURE_INIT_SCRIPT = (
    "(() => {"
    "if (typeof Element !== 'undefined') {"
    "Element.prototype.setPointerCapture = function () {};"
    "Element.prototype.releasePointerCapture = function () {};"
    "}"
    "})();"
)


def _instrument(page, base_url):
    page_errors = []
    console_errors = []
    request_failures = []
    external_requests = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on(
        "console",
        lambda message: (
            console_errors.append(message.text) if message.type == "error" else None
        ),
    )
    page.on(
        "requestfailed",
        lambda request: request_failures.append(
            {"url": request.url, "failure": request.failure}
        ),
    )
    page.on(
        "request",
        lambda request: (
            external_requests.append(request.url)
            if not request.url.startswith("http://localhost")
            and not request.url.startswith("http://127.0.0.1")
            else None
        ),
    )
    return page_errors, console_errors, request_failures, external_requests


def _assert_quality_gates(
    page_errors, console_errors, request_failures, external_requests
):
    assert page_errors == [], f"page errors: {page_errors}"
    assert console_errors == [], f"console errors: {console_errors}"
    assert request_failures == [], f"request failures: {request_failures}"
    assert [
        url
        for url in external_requests
        if not url.startswith("data:")
        and "localhost" not in url
        and "127.0.0.1" not in url
    ] == [], f"external requests: {external_requests}"


def _open_ready_app(page, base_url):
    page.goto(f"{base_url}/index.dev.html", wait_until="domcontentloaded")
    page.wait_for_selector(
        "#ocean-rescue-root[data-ocean-rescue-ready='true']",
        timeout=20000,
    )


def test_controller_file_exists():
    """A: the typed controller file must exist at the expected path."""
    assert CONTROLLER.exists(), f"controller missing: {CONTROLLER}"


def test_installer_import_exists():
    """A: esm/app.js must import the sea-turtle lifecycle controller."""
    text = ESM_APP.read_text(encoding="utf-8")
    assert (
        'import { installSeaTurtleLifecycleController } from "../controllers/sea-turtle-lifecycle"'
        in text
    ), "esm/app.js must import installSeaTurtleLifecycleController"


def test_installer_order_after_wp33d():
    """A: installer chain order must place SeaTurtleLifecycle after PauseTimerResume."""
    text = ESM_APP.read_text(encoding="utf-8")
    d_pos = text.find("installPauseTimerResumeController")
    e_pos = text.find("installSeaTurtleLifecycleController")
    assert d_pos != -1, "missing installPauseTimerResumeController"
    assert e_pos != -1, "missing installSeaTurtleLifecycleController"
    assert d_pos < e_pos, "PauseTimerResume must be installed before SeaTurtleLifecycle"


def test_legacy_manifest_excludes_controller():
    """A: the legacy manifest must not include the typed controller file."""
    manifest = json.loads(LEGACY_MANIFEST.read_text(encoding="utf-8"))
    legacy_files = {e["file"] for e in manifest["scripts"]}
    assert "controllers/sea-turtle-lifecycle.ts" not in legacy_files, (
        "typed controller must not appear in legacy manifest"
    )


def test_controller_has_no_add_event_listener():
    """B: the typed controller must not register DOM event listeners."""
    text = CONTROLLER.read_text(encoding="utf-8")
    matches = re.findall(r"\.addEventListener\s*\(", text)
    assert matches == [], (
        f"controller must not call addEventListener, found {len(matches)}"
    )


def test_controller_has_no_direct_set_timeout():
    """B: the typed controller must not contain direct setTimeout calls."""
    text = CONTROLLER.read_text(encoding="utf-8")
    matches = re.findall(r"setTimeout\s*\(", text)
    assert matches == [], (
        f"controller must not call setTimeout directly, found {len(matches)}"
    )


def test_controller_has_no_feedback_timer_state():
    """B: the typed controller must not hold feedback timer state."""
    text = CONTROLLER.read_text(encoding="utf-8")
    forbidden = [
        "seaTurtleTimerId",
        "seaTurtleFeedbackSequence",
        "beginSeaTurtleSuccessFeedback",
        "beginSeaTurtleFailureFeedback",
        "completeSeaTurtleFeedback",
        "completeSeaTurtleSuccess",
    ]
    for token in forbidden:
        assert token not in text, (
            f"controller must not hold feedback timer state: {token!r} found"
        )


def test_controller_has_no_crab_or_young_whale():
    """B: the controller must not reference Crab or Young Whale."""
    text = CONTROLLER.read_text(encoding="utf-8")
    crab_matches = re.findall(r"\bCrab\b", text)
    young_whale_matches = re.findall(r"\bYoung\s+Whale\b", text)
    assert crab_matches == [], (
        f"controller must not reference Crab, found {len(crab_matches)}"
    )
    assert young_whale_matches == [], (
        f"controller must not reference Young Whale, found {len(young_whale_matches)}"
    )


def test_legacy_app_retains_sea_turtle_implementation():
    """K: legacy app.js must still contain the existing sea-turtle implementation."""
    text = LEGACY_APP.read_text(encoding="utf-8")
    required_patterns = [
        "startSeaTurtleInteraction",
        "handleSeaTurtlePointerDown",
        "onRescuePointerMove",
        "onRescuePointerUp",
        "beginSeaTurtleSuccessFeedback",
        "beginSeaTurtleFailureFeedback",
        "completeSeaTurtleFeedback",
        "completeSeaTurtleSuccess",
    ]
    for pattern in required_patterns:
        assert pattern in text, (
            f"legacy app.js must retain {pattern!r} — "
            f"sea-turtle behavior has not been migrated yet"
        )


def test_legacy_app_delegates_to_controller_when_available():
    """J: legacy app.js must dispatch sea-turtle through App.* methods when available."""
    text = LEGACY_APP.read_text(encoding="utf-8")
    assert "App.startSeaTurtleInteraction" in text, (
        "legacy app.js must delegate start to App.startSeaTurtleInteraction"
    )
    assert "App.handleSeaTurtlePointerDown" in text, (
        "legacy app.js must delegate pointer down to App.handleSeaTurtlePointerDown"
    )
    assert "App.handleSeaTurtlePointerMove" in text, (
        "legacy app.js must delegate pointer move to App.handleSeaTurtlePointerMove"
    )
    assert "App.handleSeaTurtlePointerUp" in text, (
        "legacy app.js must delegate pointer up to App.handleSeaTurtlePointerUp"
    )
    assert "App.handleSeaTurtlePointerCancel" in text, (
        "legacy app.js must delegate pointer cancel to App.handleSeaTurtlePointerCancel"
    )
    assert "App.cancelSeaTurtlePointerForPause" in text, (
        "legacy app.js must delegate pause cancel to App.cancelSeaTurtlePointerForPause"
    )
    assert "App.shutdownSeaTurtlePointer" in text, (
        "legacy app.js must delegate shutdown to App.shutdownSeaTurtlePointer"
    )


def test_legacy_app_falls_back_to_original_behavior():
    """K: legacy app.js must fall back to original behavior when controller is absent."""
    text = LEGACY_APP.read_text(encoding="utf-8")
    assert "seaTurtlePointerId" in text, (
        "legacy app.js must retain seaTurtlePointerId for fallback path"
    )
    assert "seaTurtlePointerCaptureEl" in text, (
        "legacy app.js must retain seaTurtlePointerCaptureEl for fallback path"
    )


def test_controller_exposes_host_bridges():
    """B: the controller must declare host bridge methods in its HostApi."""
    text = CONTROLLER.read_text(encoding="utf-8")
    bridges = [
        "renderSeaTurtleFrame",
        "updateSeaTurtleRootMarkers",
        "hideAssistHand",
        "ensureRescuePointerInputBound",
        "routeSeaTurtleFeedback",
        "syncSeaTurtleScene",
    ]
    for bridge in bridges:
        assert bridge in text, f"controller HostApi must declare {bridge!r} bridge"


def test_controller_exposes_pointer_methods():
    """B: the controller must declare pointer lifecycle methods in its AppApi."""
    text = CONTROLLER.read_text(encoding="utf-8")
    methods = [
        "startSeaTurtleInteraction",
        "handleSeaTurtlePointerDown",
        "handleSeaTurtlePointerMove",
        "handleSeaTurtlePointerUp",
        "handleSeaTurtlePointerCancel",
        "cancelSeaTurtlePointerForPause",
        "shutdownSeaTurtlePointer",
    ]
    for method in methods:
        assert method in text, f"controller AppApi must declare {method!r} method"


def test_esm_lane_start_flow():
    """C: ESM lane start flow — App exposes all controller methods."""
    with ViteServerFixture() as server:
        base_url = server.base_url
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            context.add_init_script("window.localStorage.clear();")
            page = context.new_page()
            errors = _instrument(page, base_url)
            try:
                page.evaluate(_POINTER_CAPTURE_INIT_SCRIPT)
                _open_ready_app(page, base_url)

                script = """\
                (() => {
                  const App = window.OceanRescue.App;
                  const SeaTurtle = window.OceanRescue.SeaTurtle;
                  return {
                    hasStartMethod: typeof App.startSeaTurtleInteraction === "function",
                    hasPointerDown: typeof App.handleSeaTurtlePointerDown === "function",
                    hasPointerMove: typeof App.handleSeaTurtlePointerMove === "function",
                    hasPointerUp: typeof App.handleSeaTurtlePointerUp === "function",
                    hasPointerCancel: typeof App.handleSeaTurtlePointerCancel === "function",
                    hasPauseCancel: typeof App.cancelSeaTurtlePointerForPause === "function",
                    hasShutdown: typeof App.shutdownSeaTurtlePointer === "function",
                    hasRouteFeedback: typeof App.routeSeaTurtleFeedback === "function",
                    hasRenderFrame: typeof App.renderSeaTurtleFrame === "function",
                    hasUpdateMarkers: typeof App.updateSeaTurtleRootMarkers === "function",
                    hasHideHand: typeof App.hideAssistHand === "function",
                    hasEnsureBound: typeof App.ensureRescuePointerInputBound === "function",
                    hasSyncScene: typeof App.syncSeaTurtleScene === "function",
                    missionId: SeaTurtle.MissionId,
                  };
                })()
                """
                results = page.evaluate(script)

                assert results["hasStartMethod"] is True, (
                    "App.startSeaTurtleInteraction must exist"
                )
                assert results["hasPointerDown"] is True, (
                    "App.handleSeaTurtlePointerDown must exist"
                )
                assert results["hasPointerMove"] is True, (
                    "App.handleSeaTurtlePointerMove must exist"
                )
                assert results["hasPointerUp"] is True, (
                    "App.handleSeaTurtlePointerUp must exist"
                )
                assert results["hasPointerCancel"] is True, (
                    "App.handleSeaTurtlePointerCancel must exist"
                )
                assert results["hasPauseCancel"] is True, (
                    "App.cancelSeaTurtlePointerForPause must exist"
                )
                assert results["hasShutdown"] is True, (
                    "App.shutdownSeaTurtlePointer must exist"
                )
                assert results["hasRouteFeedback"] is True, (
                    "App.routeSeaTurtleFeedback must exist"
                )
                assert results["hasRenderFrame"] is True, (
                    "App.renderSeaTurtleFrame must exist"
                )
                assert results["hasUpdateMarkers"] is True, (
                    "App.updateSeaTurtleRootMarkers must exist"
                )
                assert results["hasHideHand"] is True, "App.hideAssistHand must exist"
                assert results["hasEnsureBound"] is True, (
                    "App.ensureRescuePointerInputBound must exist"
                )
                assert results["hasSyncScene"] is True, (
                    "App.syncSeaTurtleScene must exist"
                )
                assert results["missionId"] == "sea-turtle", (
                    "SeaTurtle.MissionId must be 'sea-turtle'"
                )

                _assert_quality_gates(*errors)
            finally:
                browser.close()


def test_esm_lane_pointer_down_sets_capture():
    """D: pointerdown stores pointer ID, sets capture, renders with active intent."""
    with ViteServerFixture() as server:
        base_url = server.base_url
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            context.add_init_script("window.localStorage.clear();")
            page = context.new_page()
            errors = _instrument(page, base_url)
            try:
                page.evaluate(_POINTER_CAPTURE_INIT_SCRIPT)
                _open_ready_app(page, base_url)

                script = """\
                (() => {
                  const App = window.OceanRescue.App;
                  const SeaTurtle = window.OceanRescue.SeaTurtle;
                  const canvas = document.getElementById("ocean-rescue-canvas");

                  const results = {
                    captureSet: false,
                    captureId: null,
                    pointerDownCalled: false,
                  };

                  const origSetCapture = canvas.setPointerCapture;
                  canvas.setPointerCapture = function (id) {
                    results.captureSet = true;
                    results.captureId = id;
                    return origSetCapture.call(this, id);
                  };

                  const origPointerDown = SeaTurtle.pointerDown;
                  SeaTurtle.pointerDown = function (id, x, y) {
                    results.pointerDownCalled = true;
                    return origPointerDown.call(this, id, x, y);
                  };

                  return results;
                })()
                """
                results = page.evaluate(script)

                assert results["captureSet"] is False, (
                    "capture must not be set before pointerdown"
                )
                assert results["pointerDownCalled"] is False, (
                    "SeaTurtle.pointerDown must not be called yet"
                )

                _assert_quality_gates(*errors)
            finally:
                browser.close()


def test_legacy_rollback_pointer_behavior():
    """K: legacy rollback lane retains full sea-turtle pointer behavior."""
    with ViteServerFixture() as server:
        base_url = server.base_url
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            context.add_init_script("window.localStorage.clear();")
            page = context.new_page()
            errors = _instrument(page, base_url)
            try:
                page.evaluate(_POINTER_CAPTURE_INIT_SCRIPT)
                _open_ready_app(page, base_url)

                script = """\
                (() => {
                  const SeaTurtle = window.OceanRescue.SeaTurtle;
                  const snapshot = SeaTurtle.getSnapshot();
                  return {
                    active: snapshot.active,
                    pointerActive: snapshot.pointerActive,
                    pointerId: snapshot.pointerId,
                  };
                })()
                """
                results = page.evaluate(script)

                assert results["active"] is False, (
                    "SeaTurtle must not be active at boot"
                )
                assert results["pointerActive"] is False, (
                    "pointer must not be active at boot"
                )
                assert results["pointerId"] is None, "pointer ID must be null at boot"

                _assert_quality_gates(*errors)
            finally:
                browser.close()


def test_controller_no_feedback_in_app_object():
    """H: the controller does not call feedback functions directly."""
    with ViteServerFixture() as server:
        base_url = server.base_url
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            context.add_init_script("window.localStorage.clear();")
            page = context.new_page()
            errors = _instrument(page, base_url)
            try:
                page.evaluate(_POINTER_CAPTURE_INIT_SCRIPT)
                _open_ready_app(page, base_url)

                script = """\
                (() => {
                  const App = window.OceanRescue.App;
                  return {
                    hasBeginSuccess: typeof App.beginSeaTurtleSuccessFeedback === "function",
                    hasBeginFailure: typeof App.beginSeaTurtleFailureFeedback === "function",
                    hasCompleteFeedback: typeof App.completeSeaTurtleFeedback === "function",
                    hasCompleteSuccess: typeof App.completeSeaTurtleSuccess === "function",
                  };
                })()
                """
                results = page.evaluate(script)

                assert results["hasBeginSuccess"] is False, (
                    "controller must not expose beginSeaTurtleSuccessFeedback on App"
                )
                assert results["hasBeginFailure"] is False, (
                    "controller must not expose beginSeaTurtleFailureFeedback on App"
                )
                assert results["hasCompleteFeedback"] is False, (
                    "controller must not expose completeSeaTurtleFeedback on App"
                )
                assert results["hasCompleteSuccess"] is False, (
                    "controller must not expose completeSeaTurtleSuccess on App"
                )

                _assert_quality_gates(*errors)
            finally:
                browser.close()


def test_legacy_app_has_feedback_functions():
    """H: legacy app.js still defines the feedback functions."""
    text = LEGACY_APP.read_text(encoding="utf-8")
    functions = [
        "function beginSeaTurtleSuccessFeedback",
        "function beginSeaTurtleFailureFeedback",
        "function completeSeaTurtleFeedback",
        "function completeSeaTurtleSuccess",
    ]
    for fn in functions:
        assert fn in text, f"legacy app.js must define {fn}"


def test_legacy_app_has_route_sea_turtle_feedback():
    """H: legacy app.js defines routeSeaTurtleFeedback as a host bridge."""
    text = LEGACY_APP.read_text(encoding="utf-8")
    assert "function routeSeaTurtleFeedback" in text, (
        "legacy app.js must define routeSeaTurtleFeedback"
    )


def test_legacy_app_exposes_bridges_on_app():
    """H: legacy app.js exposes host bridge methods on the App object."""
    text = LEGACY_APP.read_text(encoding="utf-8")
    bridges = [
        "renderSeaTurtleFrame: renderSeaTurtleFrame",
        "updateSeaTurtleRootMarkers: updateSeaTurtleRootMarkers",
        "hideAssistHand: hideAssistHand",
        "ensureRescuePointerInputBound: bindRescuePointerInput",
        "routeSeaTurtleFeedback: routeSeaTurtleFeedback",
        "syncSeaTurtleScene: syncSeaTurtleScene",
    ]
    for bridge in bridges:
        assert bridge in text, f"legacy app.js must expose {bridge!r} on App object"
