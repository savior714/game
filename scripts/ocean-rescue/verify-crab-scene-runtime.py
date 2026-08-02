#!/usr/bin/env python3
"""Authored crab scene runtime acceptance - focused Chrome fixture runner.

Boots the published single HTML in a same-origin iframe harness and drives only
the public OceanRescue.Crab / OceanRescue.CrabScene namespaces to prove the
authored crab scene runtime contract and the canonical interaction geometry.

Two flows are supported:
  first-rock (default) - one canonical rock rescue accepted by the authored scene
  complete              - rock-1..rock-3 rescue sequence with a final scene exit

Two backend modes are supported:
  auto (default) - keep the default Chrome flags; the selected backend follows preflight
  canvas          - disable WebGL in Chrome so the authored scene boots on the
                    PixiJS Canvas backend and selectedBackend must be canvas

Uses the existing backend verifier helpers without modifying them.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

HARNESS_URL_PATH = "/tests/ocean-rescue/rendering-acceptance/crab-scene-runtime.html"

TASK_ID = "AIDENGAME-OCEAN-RESCUE-CRAB-MISSION-INTERACTION-GEOMETRY-ALIGNMENT-01"

PRODUCTION_FILES = [
    "ocean-rescue/index.html",
    "domains/ocean-rescue/src/render-runtime.js",
    "domains/ocean-rescue/src/crab.js",
    "domains/ocean-rescue/src/crab-scene.js",
]

CHROME_TIMEOUT_SECONDS = 60

WEBGL_DISABLE_FLAG = "--disable-" + "webgl"

COMPLETE_ROCK_IDS = ["rock-1", "rock-2", "rock-3"]
COMPLETE_CRAB_STAGES = ["relief-1", "relief-2", "free"]
COMPLETE_NEXT_ROCKS = ["rock-2", "rock-3", None]


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Authored crab scene runtime acceptance - focused Chrome fixture runner."
        )
    )
    parser.add_argument(
        "--backend",
        choices=("auto", "canvas"),
        default="auto",
        help="Pixi backend expectation. canvas disables WebGL in Chrome.",
    )
    parser.add_argument(
        "--flow",
        choices=("first-rock", "complete"),
        default="first-rock",
        help="Harness flow to prove.",
    )
    return parser.parse_args()


def sha256_of(relative_path):
    digest = hashlib.sha256()
    with open(REPO_ROOT / relative_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_backend_helpers():
    helper_path = REPO_ROOT / "scripts/ocean-rescue/verify-pixi-backends.py"
    spec = importlib.util.spec_from_file_location(
        "ocean_rescue_backend_helpers", helper_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_diagnostics(output):
    match = output.find('"schemaVersion"')
    if match == -1:
        return None, "no diagnostics found"

    json_start = output.rfind("{", 0, match)
    if json_start == -1:
        return None, "invalid diagnostics JSON"

    depth = 0
    json_end = -1
    for idx in range(json_start, len(output)):
        ch = output[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                json_end = idx
                break

    if json_end == -1:
        return None, "unmatched braces in diagnostics"

    try:
        return json.loads(output[json_start : json_end + 1]), None
    except json.JSONDecodeError as exc:
        return None, "json parse: {}".format(exc)


def assert_geometry_checks(diag, checks, check):
    geometry = diag.get("geometry") or {}
    rocks = geometry.get("rocks") or []
    check(
        "geometry.rockCount",
        len(rocks) == 3,
        "rock count != 3 (got {})".format(len(rocks)),
    )
    for index, rock in enumerate(rocks, start=1):
        check(
            "geometry.{}.startNoDropZone".format(rock.get("id")),
            rock.get("startIntersectsDropZone") is False,
            "{} start intersects drop zone".format(rock.get("id")),
        )
        check(
            "geometry.{}.placedInDropZone".format(rock.get("id")),
            rock.get("placedInsideDropZone") is True,
            "{} placed outside drop zone".format(rock.get("id")),
        )
        check(
            "geometry.{}.startPressesCrab".format(rock.get("id")),
            rock.get("startPressesCrab") is True,
            "{} start does not press crab".format(rock.get("id")),
        )
        check(
            "geometry.{}.placedClearOfCrab".format(rock.get("id")),
            rock.get("placedClearOfCrab") is True,
            "{} placed overlaps crab".format(rock.get("id")),
        )
    dz = geometry.get("dropZone") or {}
    check(
        "geometry.dropZoneInViewport",
        (dz.get("x", 0) - dz.get("width", 0) / 2) >= 0
        and (dz.get("x", 0) + dz.get("width", 0) / 2) <= diag.get("logicalWidth", 1280)
        and (dz.get("y", 0) - dz.get("height", 0) / 2) >= 0
        and (dz.get("y", 0) + dz.get("height", 0) / 2)
        <= diag.get("logicalHeight", 720),
        "drop zone outside logical viewport",
    )


def assert_first_rock_diagnostics(diag, before_hashes, after_hashes):
    checks = []

    def check(name, ok, message):
        checks.append((name, ok, message))

    check(
        "singleHtmlReady",
        diag.get("singleHtmlReady") is True,
        "singleHtmlReady != true",
    )
    check(
        "renderRuntimeReady",
        diag.get("renderRuntimeReady") is True,
        "renderRuntimeReady != true",
    )
    check(
        "selectedBackend",
        diag.get("selectedBackend") in ("webgl", "canvas"),
        "selectedBackend not in (webgl, canvas): {}".format(
            diag.get("selectedBackend")
        ),
    )
    check(
        "flowMode",
        diag.get("flowMode") == "first-rock",
        "flowMode != first-rock (got {})".format(diag.get("flowMode")),
    )
    check(
        "logicalWidth",
        diag.get("logicalWidth") == 1280,
        "logicalWidth != 1280 (got {})".format(diag.get("logicalWidth")),
    )
    check(
        "logicalHeight",
        diag.get("logicalHeight") == 720,
        "logicalHeight != 720 (got {})".format(diag.get("logicalHeight")),
    )

    assert_geometry_checks(diag, checks, check)

    initial = diag.get("initial") or {}
    check("initial.mounted", initial.get("mounted") is True, "initial.mounted != true")
    check("initial.active", initial.get("active") is True, "initial.active != true")
    check("initial.paused", initial.get("paused") is False, "initial.paused != false")
    check(
        "initial.activeRockId",
        initial.get("activeRockId") == "rock-1",
        "initial.activeRockId != rock-1 (got {})".format(initial.get("activeRockId")),
    )
    check(
        "initial.completedCount",
        initial.get("completedCount") == 0,
        "initial.completedCount != 0 (got {})".format(initial.get("completedCount")),
    )
    check(
        "initial.crabState",
        initial.get("crabState") == "trapped",
        "initial.crabState != trapped (got {})".format(initial.get("crabState")),
    )
    check(
        "initial.legacyBridgeVisible",
        initial.get("legacyBridgeVisible") is False,
        "initial.legacyBridgeVisible != false",
    )
    check(
        "initial.missingAliases",
        (initial.get("missingAliases") or []) == [],
        "initial.missingAliases not empty: {}".format(initial.get("missingAliases")),
    )
    check(
        "initial.nodeCount",
        (initial.get("nodeCount") or 0) > 0,
        "initial.nodeCount <= 0 (got {})".format(initial.get("nodeCount")),
    )
    check(
        "initial.grabbed",
        initial.get("grabbed") is False,
        "initial.grabbed != false",
    )
    check(
        "initial.feedback",
        initial.get("feedback") == "none",
        "initial.feedback != none (got {})".format(initial.get("feedback")),
    )

    first = diag.get("firstRock") or {}
    check(
        "firstRock.rockId",
        first.get("rockId") == "rock-1",
        "firstRock.rockId != rock-1 (got {})".format(first.get("rockId")),
    )
    check(
        "firstRock.downAccepted",
        first.get("down") is True,
        "firstRock.down != true",
    )
    check(
        "firstRock.holdAccepted",
        first.get("holdAccepted") is True,
        "firstRock.holdAccepted != true",
    )
    check(
        "firstRock.holdOutcome",
        first.get("holdOutcome") == "grabbed",
        "firstRock.holdOutcome != grabbed (got {})".format(first.get("holdOutcome")),
    )
    check(
        "firstRock.releaseAccepted",
        first.get("releaseAccepted") is True,
        "firstRock.releaseAccepted != true",
    )
    check(
        "firstRock.releaseOutcome",
        first.get("releaseOutcome") == "success",
        "firstRock.releaseOutcome != success (got {})".format(
            first.get("releaseOutcome")
        ),
    )
    check(
        "firstRock.releaseRockId",
        first.get("releaseRockId") == "rock-1",
        "firstRock.releaseRockId != rock-1 (got {})".format(first.get("releaseRockId")),
    )

    feedback = diag.get("feedback") or {}
    check(
        "feedback.changed", feedback.get("changed") is True, "feedback.changed != true"
    )
    check(
        "feedback.complete",
        feedback.get("complete") is False,
        "feedback.complete != false",
    )
    check(
        "feedback.nextRockId",
        feedback.get("nextRockId") == "rock-2",
        "feedback.nextRockId != rock-2 (got {})".format(feedback.get("nextRockId")),
    )

    after = diag.get("afterFirstRock") or {}
    check(
        "afterFirstRock.mounted",
        after.get("mounted") is True,
        "afterFirstRock.mounted != true",
    )
    check(
        "afterFirstRock.active",
        after.get("active") is True,
        "afterFirstRock.active != true",
    )
    check(
        "afterFirstRock.activeRockId",
        after.get("activeRockId") == "rock-2",
        "afterFirstRock.activeRockId != rock-2 (got {})".format(
            after.get("activeRockId")
        ),
    )
    check(
        "afterFirstRock.completedCount",
        after.get("completedCount") == 1,
        "afterFirstRock.completedCount != 1 (got {})".format(
            after.get("completedCount")
        ),
    )
    check(
        "afterFirstRock.crabState",
        after.get("crabState") == "relief-1",
        "afterFirstRock.crabState != relief-1 (got {})".format(after.get("crabState")),
    )
    check(
        "afterFirstRock.legacyBridgeVisible",
        after.get("legacyBridgeVisible") is False,
        "afterFirstRock.legacyBridgeVisible != false",
    )

    exit_state = diag.get("afterExit") or {}
    check(
        "afterExit.mounted",
        exit_state.get("mounted") is False,
        "afterExit.mounted != false",
    )
    check(
        "afterExit.active",
        exit_state.get("active") is False,
        "afterExit.active != false",
    )
    check(
        "afterExit.animationRunning",
        exit_state.get("animationRunning") is False,
        "afterExit.animationRunning != false",
    )
    check(
        "afterExit.legacyBridgeVisible",
        exit_state.get("legacyBridgeVisible") is True,
        "afterExit.legacyBridgeVisible != true",
    )

    check(
        "uncaughtErrorCount",
        diag.get("uncaughtErrorCount") == 0,
        "uncaughtErrorCount != 0 (got {})".format(diag.get("uncaughtErrorCount")),
    )
    check(
        "unhandledRejectionCount",
        diag.get("unhandledRejectionCount") == 0,
        "unhandledRejectionCount != 0 (got {})".format(
            diag.get("unhandledRejectionCount")
        ),
    )
    check(
        "securityPolicyViolationCount",
        diag.get("securityPolicyViolationCount") == 0,
        "securityPolicyViolationCount != 0 (got {})".format(
            diag.get("securityPolicyViolationCount")
        ),
    )
    check(
        "externalOriginRequestCount",
        diag.get("externalOriginRequestCount") == 0,
        "externalOriginRequestCount != 0 (got {})".format(
            diag.get("externalOriginRequestCount")
        ),
    )
    check("diag.complete", diag.get("complete") is True, "diag.complete != true")
    check(
        "diag.error",
        diag.get("error") is None,
        "diag.error != null: {}".format(diag.get("error")),
    )

    check(
        "productionByteIdentical",
        before_hashes == after_hashes,
        "production hashes changed",
    )

    return checks


def assert_complete_canvas_diagnostics(diag, before_hashes, after_hashes):
    checks = []

    def check(name, ok, message):
        checks.append((name, ok, message))

    check(
        "singleHtmlReady",
        diag.get("singleHtmlReady") is True,
        "singleHtmlReady != true",
    )
    check(
        "renderRuntimeReady",
        diag.get("renderRuntimeReady") is True,
        "renderRuntimeReady != true",
    )
    check(
        "selectedBackend",
        diag.get("selectedBackend") in ("webgl", "canvas"),
        "selectedBackend not in (webgl, canvas): {}".format(
            diag.get("selectedBackend")
        ),
    )
    check(
        "flowMode",
        diag.get("flowMode") == "complete",
        "flowMode != complete (got {})".format(diag.get("flowMode")),
    )
    check(
        "logicalWidth",
        diag.get("logicalWidth") == 1280,
        "logicalWidth != 1280 (got {})".format(diag.get("logicalWidth")),
    )
    check(
        "logicalHeight",
        diag.get("logicalHeight") == 720,
        "logicalHeight != 720 (got {})".format(diag.get("logicalHeight")),
    )

    assert_geometry_checks(diag, checks, check)

    initial = diag.get("initial") or {}
    check("initial.mounted", initial.get("mounted") is True, "initial.mounted != true")
    check("initial.active", initial.get("active") is True, "initial.active != true")
    check("initial.paused", initial.get("paused") is False, "initial.paused != false")
    check(
        "initial.activeRockId",
        initial.get("activeRockId") == "rock-1",
        "initial.activeRockId != rock-1 (got {})".format(initial.get("activeRockId")),
    )
    check(
        "initial.completedCount",
        initial.get("completedCount") == 0,
        "initial.completedCount != 0 (got {})".format(initial.get("completedCount")),
    )
    check(
        "initial.crabState",
        initial.get("crabState") == "trapped",
        "initial.crabState != trapped (got {})".format(initial.get("crabState")),
    )
    check(
        "initial.legacyBridgeVisible",
        initial.get("legacyBridgeVisible") is False,
        "initial.legacyBridgeVisible != false",
    )
    check(
        "initial.missingAliases",
        (initial.get("missingAliases") or []) == [],
        "initial.missingAliases not empty: {}".format(initial.get("missingAliases")),
    )

    transitions = diag.get("rockTransitions") or []
    check(
        "rockTransitions.length",
        len(transitions) == 3,
        "rockTransitions length != 3 (got {})".format(len(transitions)),
    )
    check(
        "rockTransitions.order",
        [t.get("rockId") for t in transitions] == COMPLETE_ROCK_IDS,
        "rock order != {}".format(COMPLETE_ROCK_IDS),
    )
    check(
        "rockTransitions.holdAccepted",
        all(t.get("holdAccepted") is True for t in transitions),
        "not every hold accepted",
    )
    check(
        "rockTransitions.holdOutcome",
        all(t.get("holdOutcome") == "grabbed" for t in transitions),
        "not every hold outcome == grabbed",
    )
    check(
        "rockTransitions.releaseAccepted",
        all(t.get("releaseAccepted") is True for t in transitions),
        "not every release accepted",
    )
    check(
        "rockTransitions.releaseOutcome",
        all(t.get("releaseOutcome") == "success" for t in transitions),
        "not every release outcome == success",
    )
    check(
        "rockTransitions.completedCounts",
        [t.get("completedCountAfterRelease") for t in transitions] == [1, 2, 3],
        "completed counts != [1, 2, 3]",
    )
    check(
        "rockTransitions.crabStages",
        [t.get("crabStateAfterRelease") for t in transitions] == COMPLETE_CRAB_STAGES,
        "crab stages != {}".format(COMPLETE_CRAB_STAGES),
    )
    check(
        "rockTransitions.nextRockIds",
        [t.get("nextRockId") for t in transitions] == COMPLETE_NEXT_ROCKS,
        "next rock ids != {}".format(COMPLETE_NEXT_ROCKS),
    )
    check(
        "rockTransitions.feedbackComplete",
        [t.get("feedbackComplete") for t in transitions] == [False, False, True],
        "feedback complete flags != [false, false, true]",
    )
    check(
        "rock1.activeRockBefore",
        transitions[0].get("activeRockBefore") == "rock-1",
        "rock-1 activeRockBefore != rock-1",
    )
    check(
        "rock2.activeRockBefore",
        transitions[1].get("activeRockBefore") == "rock-2",
        "rock-2 activeRockBefore != rock-2",
    )
    check(
        "rock3.activeRockBefore",
        transitions[2].get("activeRockBefore") == "rock-3",
        "rock-3 activeRockBefore != rock-3",
    )

    final_domain = diag.get("finalDomain") or {}
    check(
        "finalDomain.complete",
        final_domain.get("complete") is True,
        "finalDomain.complete != true",
    )
    check(
        "finalDomain.active",
        final_domain.get("active") is False,
        "finalDomain.active != false",
    )
    check(
        "finalDomain.activeRockId",
        final_domain.get("activeRockId") is None,
        "finalDomain.activeRockId != null (got {})".format(
            final_domain.get("activeRockId")
        ),
    )
    check(
        "finalDomain.completedRockIds",
        (final_domain.get("completedRockIds") or []) == COMPLETE_ROCK_IDS,
        "finalDomain.completedRockIds != {}".format(COMPLETE_ROCK_IDS),
    )
    check(
        "finalDomain.completedCount",
        final_domain.get("completedCount") == 3,
        "finalDomain.completedCount != 3 (got {})".format(
            final_domain.get("completedCount")
        ),
    )
    check(
        "finalDomain.inputLocked",
        final_domain.get("inputLocked") is True,
        "finalDomain.inputLocked != true",
    )

    before = diag.get("beforeExit") or {}
    check(
        "beforeExit.mounted",
        before.get("mounted") is True,
        "beforeExit.mounted != true",
    )
    check(
        "beforeExit.active", before.get("active") is True, "beforeExit.active != true"
    )
    check(
        "beforeExit.completedCount",
        before.get("completedCount") == 3,
        "beforeExit.completedCount != 3 (got {})".format(before.get("completedCount")),
    )
    check(
        "beforeExit.crabState",
        before.get("crabState") == "free",
        "beforeExit.crabState != free (got {})".format(before.get("crabState")),
    )
    check(
        "beforeExit.activeRockId",
        before.get("activeRockId") is None,
        "beforeExit.activeRockId != null (got {})".format(before.get("activeRockId")),
    )
    check(
        "beforeExit.legacyBridgeVisible",
        before.get("legacyBridgeVisible") is False,
        "beforeExit.legacyBridgeVisible != false",
    )

    exit_state = diag.get("afterExit") or {}
    check(
        "afterExit.mounted",
        exit_state.get("mounted") is False,
        "afterExit.mounted != false",
    )
    check(
        "afterExit.active",
        exit_state.get("active") is False,
        "afterExit.active != false",
    )
    check(
        "afterExit.animationRunning",
        exit_state.get("animationRunning") is False,
        "afterExit.animationRunning != false",
    )
    check(
        "afterExit.legacyBridgeVisible",
        exit_state.get("legacyBridgeVisible") is True,
        "afterExit.legacyBridgeVisible != true",
    )

    check(
        "uncaughtErrorCount",
        diag.get("uncaughtErrorCount") == 0,
        "uncaughtErrorCount != 0 (got {})".format(diag.get("uncaughtErrorCount")),
    )
    check(
        "unhandledRejectionCount",
        diag.get("unhandledRejectionCount") == 0,
        "unhandledRejectionCount != 0 (got {})".format(
            diag.get("unhandledRejectionCount")
        ),
    )
    check(
        "securityPolicyViolationCount",
        diag.get("securityPolicyViolationCount") == 0,
        "securityPolicyViolationCount != 0 (got {})".format(
            diag.get("securityPolicyViolationCount")
        ),
    )
    check(
        "externalOriginRequestCount",
        diag.get("externalOriginRequestCount") == 0,
        "externalOriginRequestCount != 0 (got {})".format(
            diag.get("externalOriginRequestCount")
        ),
    )
    check("diag.complete", diag.get("complete") is True, "diag.complete != true")
    check(
        "diag.error",
        diag.get("error") is None,
        "diag.error != null: {}".format(diag.get("error")),
    )

    check(
        "productionByteIdentical",
        before_hashes == after_hashes,
        "production hashes changed",
    )

    return checks


def run_chrome(chrome_bin, url, backend_mode):
    user_data = tempfile.mkdtemp(prefix="chrome-ocean-crab-")

    chrome_args = [
        chrome_bin,
        url,
        "--headless",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-default-apps",
        "--disable-extensions",
        "--disable-sync",
        "--mute-audio",
        "--hide-scrollbars",
        "--dump-dom",
        "--virtual-time-budget=12000",
        "--user-data-dir={}".format(user_data),
    ]

    if backend_mode == "canvas":
        chrome_args.append(WEBGL_DISABLE_FLAG)

    try:
        process = subprocess.Popen(
            chrome_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(REPO_ROOT),
            env={**os.environ, "PATH": os.environ.get("PATH", "")},
        )
        try:
            stdout, stderr = process.communicate(timeout=CHROME_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
    except OSError as exc:
        return None, "chrome launch: {}".format(exc)
    finally:
        shutil.rmtree(user_data, ignore_errors=True)

    return (stderr or "") + (stdout or ""), None


def main():
    args = parse_args()
    helpers = load_backend_helpers()
    chrome_bin = helpers.resolve_chrome()
    if not chrome_bin:
        print("BLOCKED: Chrome Stable not found", file=sys.stderr)
        return 2

    before_hashes = {path: sha256_of(path) for path in PRODUCTION_FILES}

    port = helpers.find_free_port()
    server = helpers.start_server(port)

    url = "http://127.0.0.1:{}{}".format(port, HARNESS_URL_PATH)
    if args.flow == "complete":
        url += "?flow=complete"

    try:
        output, launch_error = run_chrome(chrome_bin, url, args.backend)
        if launch_error is not None:
            print("BLOCKED: {}".format(launch_error), file=sys.stderr)
            return 2

        diag, parse_error = parse_diagnostics(output)
        if parse_error is not None or diag is None:
            print("FAIL: {}".format(parse_error), file=sys.stderr)
            if output:
                print(
                    "    raw output (last 800 chars): {}".format(output[-800:]),
                    file=sys.stderr,
                )
            return 1
    finally:
        server.shutdown()
        server.server_close()

    after_hashes = {path: sha256_of(path) for path in PRODUCTION_FILES}

    if args.flow == "complete":
        checks = assert_complete_canvas_diagnostics(diag, before_hashes, after_hashes)
    else:
        checks = assert_first_rock_diagnostics(diag, before_hashes, after_hashes)

    all_pass = True
    for name, ok, message in checks:
        result_str = "PASS" if ok else "FAIL: {}".format(message)
        print("  [{}] {}".format(result_str, name))
        if not ok:
            all_pass = False

    print()
    print(
        "  backend={} logical={}x{} singleHtmlReady={} renderRuntimeReady={}".format(
            diag.get("selectedBackend"),
            diag.get("logicalWidth"),
            diag.get("logicalHeight"),
            diag.get("singleHtmlReady"),
            diag.get("renderRuntimeReady"),
        )
    )
    print(
        "  flow={} webglPreflightAvailable={}".format(
            diag.get("flowMode"),
            diag.get("webglPreflightAvailable"),
        )
    )
    print(
        "  external={} errors={} rejections={} csp={}".format(
            diag.get("externalOriginRequestCount"),
            diag.get("uncaughtErrorCount"),
            diag.get("unhandledRejectionCount"),
            diag.get("securityPolicyViolationCount"),
        )
    )
    print("  production hashes unchanged={}".format(before_hashes == after_hashes))

    if not all_pass:
        print("\nOCEAN_RESCUE_CRAB_SCENE_RUNTIME_ACCEPTANCE=FAIL", file=sys.stderr)
        return 1

    print("\nOCEAN_RESCUE_CRAB_SCENE_RUNTIME_ACCEPTANCE=PASS")
    if args.flow == "complete":
        print("OCEAN_RESCUE_CRAB_CANVAS_COMPLETE_RUNTIME_ACCEPTANCE=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
