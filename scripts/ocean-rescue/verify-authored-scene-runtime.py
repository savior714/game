#!/usr/bin/env python3
"""Authored sea-turtle scene runtime acceptance — focused Chrome fixture runner.

Boots the published single HTML in a same-origin iframe harness and proves one
canonical rope release is accepted by the authored scene. Uses the existing
backend verifier helpers without modifying them.
"""

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

HARNESS_URL_PATH = (
    "/tests/ocean-rescue/rendering-acceptance/authored-scene-runtime.html"
)

TASK_ID = "AIDENGAME-OCEAN-RESCUE-AUTHORED-SCENE-RUNTIME-ACCEPTANCE-01"

PRODUCTION_FILES = [
    "ocean-rescue/index.html",
    "domains/ocean-rescue/src/render-runtime.js",
    "domains/ocean-rescue/src/sea-turtle.js",
    "domains/ocean-rescue/src/sea-turtle-scene.js",
]

CHROME_TIMEOUT_SECONDS = 60


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
        return json.loads(output[json_start:json_end + 1]), None
    except json.JSONDecodeError as exc:
        return None, "json parse: {}".format(exc)


def assert_diagnostics(diag, before_hashes, after_hashes):
    checks = []

    def check(name, ok, message):
        checks.append((name, ok, message))

    check("singleHtmlReady", diag.get("singleHtmlReady") is True, "singleHtmlReady != true")
    check(
        "renderRuntimeReady",
        diag.get("renderRuntimeReady") is True,
        "renderRuntimeReady != true",
    )
    check(
        "selectedBackend",
        diag.get("selectedBackend") in ("webgl", "canvas"),
        "selectedBackend not in (webgl, canvas): {}".format(diag.get("selectedBackend")),
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

    initial = diag.get("initial") or {}
    check("initial.mounted", initial.get("mounted") is True, "initial.mounted != true")
    check("initial.active", initial.get("active") is True, "initial.active != true")
    check("initial.paused", initial.get("paused") is False, "initial.paused != false")
    check(
        "initial.loopCount",
        initial.get("loopCount") == 3,
        "initial.loopCount != 3 (got {})".format(initial.get("loopCount")),
    )
    check(
        "initial.activeRopeId",
        initial.get("activeRopeId") == "rope-1",
        "initial.activeRopeId != rope-1 (got {})".format(initial.get("activeRopeId")),
    )
    check(
        "initial.completedCount",
        initial.get("completedCount") == 0,
        "initial.completedCount != 0 (got {})".format(initial.get("completedCount")),
    )
    check(
        "initial.reliefStage",
        initial.get("reliefStage") == "worried",
        "initial.reliefStage != worried (got {})".format(initial.get("reliefStage")),
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
        "initial.spriteCount",
        (initial.get("spriteCount") or 0) > 0,
        "initial.spriteCount <= 0 (got {})".format(initial.get("spriteCount")),
    )

    release = diag.get("releaseResult") or {}
    check("release.accepted", release.get("accepted") is True, "release.accepted != true")
    check(
        "release.outcome",
        release.get("outcome") == "success",
        "release.outcome != success (got {})".format(release.get("outcome")),
    )
    check(
        "release.ropeId",
        release.get("ropeId") == "rope-1",
        "release.ropeId != rope-1 (got {})".format(release.get("ropeId")),
    )

    interim = diag.get("afterReleaseInterim") or {}
    check(
        "interim.completedCount",
        interim.get("completedCount") == 1,
        "interim.completedCount != 1 (got {})".format(interim.get("completedCount")),
    )
    check(
        "interim.reliefStage",
        interim.get("reliefStage") == "relief-1",
        "interim.reliefStage != relief-1 (got {})".format(interim.get("reliefStage")),
    )

    feedback = diag.get("feedback") or {}
    check("feedback.changed", feedback.get("changed") is True, "feedback.changed != true")
    check(
        "feedback.complete",
        feedback.get("complete") is False,
        "feedback.complete != false",
    )
    check(
        "feedback.nextRopeId",
        feedback.get("nextRopeId") == "rope-2",
        "feedback.nextRopeId != rope-2 (got {})".format(feedback.get("nextRopeId")),
    )

    after = diag.get("afterRelease") or {}
    check("afterRelease.mounted", after.get("mounted") is True, "afterRelease.mounted != true")
    check("afterRelease.active", after.get("active") is True, "afterRelease.active != true")
    check(
        "afterRelease.activeRopeId",
        after.get("activeRopeId") == "rope-2",
        "afterRelease.activeRopeId != rope-2 (got {})".format(after.get("activeRopeId")),
    )
    check(
        "afterRelease.completedCount",
        after.get("completedCount") == 1,
        "afterRelease.completedCount != 1 (got {})".format(after.get("completedCount")),
    )
    check(
        "afterRelease.reliefStage",
        after.get("reliefStage") == "relief-1",
        "afterRelease.reliefStage != relief-1 (got {})".format(after.get("reliefStage")),
    )
    check(
        "afterRelease.legacyBridgeVisible",
        after.get("legacyBridgeVisible") is False,
        "afterRelease.legacyBridgeVisible != false",
    )

    exit_state = diag.get("afterExit") or {}
    check("afterExit.mounted", exit_state.get("mounted") is False, "afterExit.mounted != false")
    check("afterExit.active", exit_state.get("active") is False, "afterExit.active != false")
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
        "unhandledRejectionCount != 0 (got {})".format(diag.get("unhandledRejectionCount")),
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
    check(
        "referenceImageRequestCount",
        diag.get("referenceImageRequestCount") == 0,
        "referenceImageRequestCount != 0 (got {})".format(
            diag.get("referenceImageRequestCount")
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


def main():
    helpers = load_backend_helpers()
    chrome_bin = helpers.resolve_chrome()
    if not chrome_bin:
        print("BLOCKED: Chrome Stable not found", file=sys.stderr)
        return 2

    before_hashes = {
        path: sha256_of(path) for path in PRODUCTION_FILES
    }

    port = helpers.find_free_port()
    server = helpers.start_server(port)
    user_data = tempfile.mkdtemp(prefix="chrome-ocean-authored-")

    try:
        args = [
            chrome_bin,
            "http://127.0.0.1:{}{}".format(port, HARNESS_URL_PATH),
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

        try:
            process = subprocess.Popen(
                args,
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
            print("BLOCKED: chrome launch: {}".format(exc), file=sys.stderr)
            return 2

        output = (stderr or "") + (stdout or "")

        diag, parse_error = parse_diagnostics(output)
        if parse_error is not None or diag is None:
            print("FAIL: {}".format(parse_error), file=sys.stderr)
            if output:
                print("    raw output (last 800 chars): {}".format(output[-800:]), file=sys.stderr)
            return 1
    finally:
        server.shutdown()
        server.server_close()
        shutil.rmtree(user_data, ignore_errors=True)

    after_hashes = {
        path: sha256_of(path) for path in PRODUCTION_FILES
    }

    checks = assert_diagnostics(diag, before_hashes, after_hashes)

    all_pass = True
    for name, ok, message in checks:
        result_str = "PASS" if ok else "FAIL: {}".format(message)
        print("  [{}] {}".format(result_str, name))
        if not ok:
            all_pass = False

    print()
    print("  backend={} logical={}x{} singleHtmlReady={} renderRuntimeReady={}".format(
        diag.get("selectedBackend"),
        diag.get("logicalWidth"),
        diag.get("logicalHeight"),
        diag.get("singleHtmlReady"),
        diag.get("renderRuntimeReady"),
    ))
    print("  release={} relief={} completed={} nextRope={}".format(
        (diag.get("releaseResult") or {}).get("outcome"),
        (diag.get("afterRelease") or {}).get("reliefStage"),
        (diag.get("afterRelease") or {}).get("completedCount"),
        (diag.get("feedback") or {}).get("nextRopeId"),
    ))
    print("  external={} reference={} errors={} rejections={} csp={}".format(
        diag.get("externalOriginRequestCount"),
        diag.get("referenceImageRequestCount"),
        diag.get("uncaughtErrorCount"),
        diag.get("unhandledRejectionCount"),
        diag.get("securityPolicyViolationCount"),
    ))
    print("  production hashes unchanged={}".format(before_hashes == after_hashes))

    if all_pass:
        print("\nOCEAN_RESCUE_AUTHORED_SCENE_RUNTIME_ACCEPTANCE=PASS")
        return 0

    print("\nOCEAN_RESCUE_AUTHORED_SCENE_RUNTIME_ACCEPTANCE=FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
