#!/usr/bin/env python3
"""PixiJS 8.19.0 backend smoke harness — three-case Chrome acceptance runner."""

import http.server
import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import threading


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

HTML_FIXTURE = "/tests/ocean-rescue/rendering-acceptance/backend/pixi-backend-smoke.html"


def resolve_chrome():
    bin_path = os.environ.get("CHROME_BIN")
    if bin_path and os.access(bin_path, os.X_OK):
        return bin_path
    default = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.access(default, os.X_OK):
        return default
    return None


def validate_package():
    package = json.loads(
        (REPO_ROOT / "domains/ocean-rescue/package.json").read_text(encoding="utf-8")
    )
    lock = json.loads(
        (REPO_ROOT / "domains/ocean-rescue/package-lock.json").read_text(encoding="utf-8")
    )
    assert package["dependencies"]["pixi.js"] == "8.19.0", "package.json pixi.js != 8.19.0"
    assert lock["packages"]["node_modules/pixi.js"]["version"] == "8.19.0", "lock pixi.js != 8.19.0"

    installed_json = REPO_ROOT / "domains/ocean-rescue/node_modules/pixi.js/package.json"
    if installed_json.exists():
        installed = json.loads(installed_json.read_text(encoding="utf-8"))
        assert installed["version"] == "8.19.0", f"installed pixi.js != 8.19.0 (got {installed.get('version')})"

    return True


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class RepoHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def translate_path(self, path):
        translated = super().translate_path(path)
        real = pathlib.Path(translated).resolve()
        if not str(real).startswith(str(REPO_ROOT)):
            raise PermissionError("Path traversal denied")
        return str(real)

    def log_message(self, format, *args):
        pass


def start_server(port):
    server = http.server.HTTPServer(("127.0.0.1", port), RepoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def run_case(case_id, port, chrome_bin, disable_webgl=False, timeout=60):
    user_data = tempfile.mkdtemp(prefix=f"chrome-pixi-{case_id}-")

    args = [
        chrome_bin,
        f"http://127.0.0.1:{port}{HTML_FIXTURE}?case={case_id}",
        "--headless=new",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-default-apps",
        "--disable-extensions",
        "--disable-sync",
        "--metrics-recording-only",
        "--mute-audio",
        "--hide-scrollbars",
        "--dump-dom",
        "--virtual-time-budget=30000",
        f"--user-data-dir={user_data}",
    ]

    if disable_webgl:
        args.append("--disable-webgl")

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_ROOT),
            env={**os.environ, "PATH": os.environ.get("PATH", "")},
        )
    except subprocess.TimeoutExpired:
        shutil.rmtree(user_data, ignore_errors=True)
        return {"caseId": case_id, "error": "timeout", "complete": False, "raw": "chrome timeout"}
    finally:
        shutil.rmtree(user_data, ignore_errors=True)

    output = (result.stderr or "") + (result.stdout or "")

    try:
        diag_match = output.find('"schemaVersion"')
        if diag_match == -1:
            return {"caseId": case_id, "error": "no diagnostics found", "complete": False, "raw": output[-2000:]}

        json_start = output.rfind("{", 0, diag_match)
        json_end = output.rfind("}")
        if json_start == -1 or json_end == -1 or json_end < json_start:
            return {"caseId": case_id, "error": "invalid diagnostics JSON", "complete": False, "raw": output[-2000:]}

        diag = json.loads(output[json_start:json_end + 1])
    except json.JSONDecodeError as e:
        return {"caseId": case_id, "error": f"json parse: {e}", "complete": False, "raw": output[-2000:]}

    return diag


def assert_case(diag, case_id, expected_preference, expect_canvas, webgl_must_be_unavailable=False):
    if diag.get("error"):
        return False, f"case error: {diag['error']}"

    if not diag.get("complete"):
        return False, "diagnostics not complete"

    checks = [
        ("pixiVersion", diag.get("pixiVersion") == "8.19.0", "pixiVersion != 8.19.0"),
        ("caseId", diag.get("caseId") == case_id, f"caseId mismatch: expected {case_id}, got {diag.get('caseId')}"),
        ("applicationCount", diag.get("applicationCount") == 1, f"applicationCount != 1 (got {diag.get('applicationCount')})"),
        ("rendererCount", diag.get("rendererCount") == 1, f"rendererCount != 1 (got {diag.get('rendererCount')})"),
        ("canvasCount", diag.get("canvasCount") == 1, f"canvasCount != 1 (got {diag.get('canvasCount')})"),
        ("stageChildCount", diag.get("stageChildCount", 0) >= 1, f"stageChildCount < 1 (got {diag.get('stageChildCount')})"),
        ("initializationSucceeded", diag.get("initializationSucceeded") is True, "initializationSucceeded != true"),
        ("renderSucceeded", diag.get("renderSucceeded") is True, "renderSucceeded != true"),
        ("destroySucceeded", diag.get("destroySucceeded") is True, "destroySucceeded != true"),
        ("uncaughtErrorCount", diag.get("uncaughtErrorCount") == 0, f"uncaughtErrorCount != 0 (got {diag.get('uncaughtErrorCount')})"),
        ("unhandledRejectionCount", diag.get("unhandledRejectionCount") == 0, f"unhandledRejectionCount != 0 (got {diag.get('unhandledRejectionCount')})"),
        ("externalOriginRequestCount", diag.get("externalOriginRequestCount") == 0, "externalOriginRequestCount != 0"),
        ("error", diag.get("error") is None, f"error is not null: {diag.get('error')}"),
    ]

    for name, ok, msg in checks:
        if not ok:
            return False, msg

    if webgl_must_be_unavailable:
        if diag.get("webglPreflightAvailable") is not False:
            return False, "webglPreflightAvailable must be false"
        if diag.get("selectedBackend") != "canvas":
            return False, f"selectedBackend must be canvas, got {diag.get('selectedBackend')}"
    elif expect_canvas:
        if diag.get("selectedBackend") != "canvas":
            return False, f"selectedBackend must be canvas, got {diag.get('selectedBackend')}"
    else:
        if diag.get("webglPreflightAvailable") is True:
            if diag.get("selectedBackend") != "webgl":
                return False, f"webgl preflight succeeded but selected {diag.get('selectedBackend')}"

    return True, "PASS"


def main():
    chrome_bin = resolve_chrome()
    if not chrome_bin:
        print("BLOCKED: Chrome Stable not found", file=sys.stderr)
        sys.exit(2)

    try:
        validate_package()
    except AssertionError as e:
        print(f"BLOCKED: Package validation failed: {e}", file=sys.stderr)
        sys.exit(2)

    port = find_free_port()
    server = start_server(port)

    try:
        cases = [
            ("normal-auto", False, False),
            ("disabled-webgl-fallback", True, True),
            ("forced-canvas", False, True),
        ]

        all_pass = True
        results = []

        for case_id, disable_webgl, expect_canvas in cases:
            webgl_must_be_unavailable = disable_webgl
            diag = run_case(case_id, port, chrome_bin, disable_webgl=disable_webgl)

            preflight = diag.get("webglPreflightAvailable", "?")
            preflight_kind = diag.get("webglPreflightKind", "?")
            backend = diag.get("selectedBackend", "?")
            app_count = diag.get("applicationCount", "?")
            renderer_count = diag.get("rendererCount", "?")
            canvas_count = diag.get("canvasCount", "?")
            render_ok = diag.get("renderSucceeded", "?")
            destroy_ok = diag.get("destroySucceeded", "?")
            ext = diag.get("externalOriginRequestCount", "?")

            ok, msg = assert_case(diag, case_id, None, expect_canvas, webgl_must_be_unavailable)
            result_str = "PASS" if ok else f"FAIL: {msg}"

            print(f"  [{result_str}] case={case_id} "
                  f"preflight={preflight}({preflight_kind}) "
                  f"backend={backend} "
                  f"app={app_count} rndr={renderer_count} cvs={canvas_count} "
                  f"render={render_ok} destroy={destroy_ok} ext={ext}")

            if not ok:
                if diag.get("raw"):
                    print(f"    raw output (last 500 chars): {diag['raw'][-500:]}")
                all_pass = False

            results.append((case_id, ok, diag if "raw" not in diag else {}))

    finally:
        server.shutdown()

    if all_pass:
        print("\nPIXI_BACKEND_SMOKE_HARNESS=PASS")
        sys.exit(0)
    else:
        print("\nPIXI_BACKEND_SMOKE_HARNESS=FAIL", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
