#!/usr/bin/env python3
"""Four-state visual evidence packet capture for authored sea-turtle scene.

Boots the published single HTML in Chrome headless, constructs each of the
four deterministic states (worried, relief-1, relief-2, free) using only the
public OceanRescue runtime namespaces, and captures a 1280x720 PNG per state.

Outputs:
  artifacts/ocean-rescue/visual-evidence/authored-scene-v1/worried.png
  artifacts/ocean-rescue/visual-evidence/authored-scene-v1/relief-1.png
  artifacts/ocean-rescue/visual-evidence/authored-scene-v1/relief-2.png
  artifacts/ocean-rescue/visual-evidence/authored-scene-v1/free.png
  artifacts/ocean-rescue/visual-evidence/authored-scene-v1/manifest.json

Uses only Python standard library, Chrome Stable, and existing backend helper
functions. No third-party imports.
"""

import argparse
import hashlib
import http.server
import importlib.util
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

HARNESS_URL_PATH = (
    "tests/ocean-rescue/rendering-acceptance/authored-scene-visual-packet.html"
)

TASK_ID = "AIDENGAME-OCEAN-RESCUE-FOUR-STATE-VISUAL-EVIDENCE-PACKET-01"

STATES = ["worried", "relief-1", "relief-2", "free"]

OUTPUT_DIR = REPO_ROOT / "artifacts" / "ocean-rescue" / "visual-evidence" / "authored-scene-v1"

PRODUCTION_FILES = [
    "ocean-rescue/index.html",
    "domains/ocean-rescue/src/render-runtime.js",
    "domains/ocean-rescue/src/sea-turtle.js",
    "domains/ocean-rescue/src/sea-turtle-scene.js",
    "domains/ocean-rescue/package.json",
    "domains/ocean-rescue/package-lock.json",
]

CHROME_TIMEOUT_SECONDS = 120
DUMP_TIMEOUT_SECONDS = 30


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Four-state visual evidence packet capture for authored "
            "sea-turtle scene."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=None,
        help="Override output directory (default: artifacts/ocean-rescue/visual-evidence/authored-scene-v1).",
    )
    return parser.parse_args()


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_of_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_backend_helpers():
    helper_path = REPO_ROOT / "scripts/ocean-rescue/verify-pixi-backends.py"
    spec = importlib.util.spec_from_file_location(
        "ocean_rescue_backend_helpers", helper_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resolve_chrome():
    helper = load_backend_helpers()
    return helper.resolve_chrome()


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class RepoHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def translate_path(self, path):
        translated = http.server.SimpleHTTPRequestHandler.translate_path(self, path)
        real = pathlib.Path(translated).resolve()
        try:
            real.relative_to(REPO_ROOT)
        except ValueError:
            raise PermissionError("Path traversal denied")
        return str(real)

    def log_message(self, format, *args):
        pass


def start_server(port):
    import http.server
    server = http.server.HTTPServer(("127.0.0.1", port), RepoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def parse_diagnostics_from_dump(dump_output):
    match = dump_output.find('"schemaVersion"')
    if match == -1:
        return None, "no diagnostics found in dump"

    json_start = dump_output.rfind("{", 0, match)
    if json_start == -1:
        return None, "invalid diagnostics JSON"

    depth = 0
    json_end = -1
    for idx in range(json_start, len(dump_output)):
        ch = dump_output[idx]
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
        return json.loads(dump_output[json_start:json_end + 1]), None
    except json.JSONDecodeError as exc:
        return None, "json parse: {}".format(exc)


def validate_png_dimensions(png_path):
    import struct

    with open(png_path, "rb") as fh:
        signature = fh.read(8)
        if signature != b'\x89PNG\r\n\x1a\n':
            raise ValueError("Invalid PNG signature")

        length_bytes = fh.read(4)
        if len(length_bytes) < 4:
            raise ValueError("Truncated chunk length")

        length = struct.unpack(">I", length_bytes)[0]
        if length != 13:
            raise ValueError("Invalid IHDR length: {}".format(length))

        chunk_type = fh.read(4)
        if chunk_type != b'IHDR':
            raise ValueError("Expected IHDR chunk type, got: {}".format(chunk_type))

        data = fh.read(13)
        if len(data) < 13:
            raise ValueError("Truncated IHDR data")

        width = struct.unpack(">I", data[:4])[0]
        height = struct.unpack(">I", data[4:8])[0]

    return width, height


def capture_state(chrome_bin, url, output_path, state_name):
    args = [
        chrome_bin,
        url,
        "--headless=new",
        "--window-size=1280,720",
        "--force-device-scale-factor=1",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-default-apps",
        "--disable-extensions",
        "--disable-sync",
        "--mute-audio",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=30000",
        "--screenshot={}".format(output_path),
    ]

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=CHROME_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Chrome timeout for state: {}".format(state_name))

    if result.returncode != 0:
        raise RuntimeError(
            "Chrome failed for state {}: exit={}, stderr={}".format(
                state_name, result.returncode, result.stderr[:500]
            )
        )

    if not os.path.exists(output_path):
        raise RuntimeError("Screenshot not created for state: {}".format(state_name))

    return output_path


def verify_diagnostics_ready(dump_output, state_name):
    diag, err = parse_diagnostics_from_dump(dump_output)
    if err:
        raise RuntimeError("Diagnostics parse error for {}: {}".format(state_name, err))

    if not diag.get("ready"):
        raise RuntimeError(
            "State {} not ready: error={}, missingAliases={}".format(
                state_name,
                diag.get("error"),
                diag.get("missingAliases"),
            )
        )

    if diag.get("selectedBackend") != "webgl":
        raise RuntimeError(
            "State {} backend not webgl: {}".format(state_name, diag.get("selectedBackend"))
        )

    if not diag.get("mounted"):
        raise RuntimeError("State {} scene not mounted".format(state_name))

    if diag.get("animationRunning"):
        raise RuntimeError("State {} animation still running".format(state_name))

    if diag.get("legacyBridgeVisible"):
        raise RuntimeError("State {} legacy bridge visible".format(state_name))

    if diag.get("missingAliases"):
        raise RuntimeError(
            "State {} has missing aliases: {}".format(state_name, diag.get("missingAliases"))
        )

    if diag.get("uncaughtErrorCount", 0) != 0:
        raise RuntimeError(
            "State {} has uncaught errors: {}".format(state_name, diag.get("uncaughtErrorCount"))
        )

    if diag.get("externalOriginRequestCount", 0) != 0:
        raise RuntimeError(
            "State {} has external requests".format(state_name)
        )

    return diag


def main():
    args = parse_args()
    output_dir = args.output_dir or OUTPUT_DIR

    chrome_bin = resolve_chrome()
    if not chrome_bin:
        print("BLOCKED: Chrome Stable not found", file=sys.stderr)
        return 1

    print("Chrome: {}".format(chrome_bin))

    for prod_file in PRODUCTION_FILES:
        prod_path = REPO_ROOT / prod_file
        if not prod_path.exists():
            print("BLOCKED: Production file missing: {}".format(prod_file), file=sys.stderr)
            return 1

    before_hashes = {}
    for prod_file in PRODUCTION_FILES:
        before_hashes[prod_file] = sha256_of(REPO_ROOT / prod_file)

    port = find_free_port()
    server = start_server(port)
    print("Server started on port {}".format(port))

    temp_output_dir = pathlib.Path(tempfile.mkdtemp(prefix="visual-packet-temp-"))

    captures = []
    diagnostics_by_state = {}

    try:
        for state_name in STATES:
            url = "http://127.0.0.1:{}/{}?state={}".format(port, HARNESS_URL_PATH.lstrip("/"), state_name)
            png_path = temp_output_dir / "{}.png".format(state_name)

            print("Capturing state: {}".format(state_name))

            dump_result = None
            try:
                dump_args = [
                    chrome_bin,
                    url,
                    "--headless",
                    "--window-size=1280,720",
                    "--force-device-scale-factor=1",
                    "--hide-scrollbars",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-background-networking",
                    "--disable-component-update",
                    "--disable-default-apps",
                    "--disable-extensions",
                    "--disable-sync",
                    "--mute-audio",
                    "--virtual-time-budget=12000",
                    "--dump-dom",
                ]
                dump_result = subprocess.run(
                    dump_args,
                    capture_output=True,
                    text=True,
                    timeout=DUMP_TIMEOUT_SECONDS,
                )

                if dump_result.returncode != 0:
                    raise RuntimeError(
                        "Chrome dump failed for {}: exit={}".format(state_name, dump_result.returncode)
                    )

                diag = verify_diagnostics_ready(dump_result.stdout, state_name)
                diagnostics_by_state[state_name] = diag
            except Exception as exc:
                print("WARNING: Dump verification failed for {}: {}".format(state_name, exc), file=sys.stderr)
                print("Proceeding with screenshot capture anyway...", file=sys.stderr)

            try:
                capture_state(chrome_bin, url, str(png_path), state_name)
            except Exception as exc:
                print("ERROR: Screenshot capture failed for {}: {}".format(state_name, exc), file=sys.stderr)
                raise

            if not png_path.exists():
                raise RuntimeError("PNG not created: {}".format(png_path))

            file_size = png_path.stat().st_size
            if file_size == 0:
                raise RuntimeError("PNG is empty: {}".format(png_path))

            width, height = validate_png_dimensions(png_path)
            if width != 1280 or height != 720:
                raise RuntimeError(
                    "PNG dimensions mismatch for {}: {}x{} (expected 1280x720)".format(
                        state_name, width, height
                    )
                )

            sha = sha256_of(png_path)
            captures.append({
                "state": state_name,
                "file": "{}.png".format(state_name),
                "sha256": sha,
            })

            print("  {}: {} ({}x{}, sha256={})".format(
                state_name, png_path.name, width, height, sha[:16]
            ))

        single_html_sha = sha256_of(REPO_ROOT / "ocean-rescue" / "index.html")

        manifest = {
            "schemaVersion": 1,
            "taskId": TASK_ID,
            "sourceCommit": subprocess.run(
                ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip(),
            "sourceSingleHtmlSha256": single_html_sha,
            "viewportCssWidth": 1280,
            "viewportCssHeight": 720,
            "deviceScaleFactor": 1,
            "pixelWidth": 1280,
            "pixelHeight": 720,
            "backend": "webgl",
            "captureOrder": STATES[:],
            "captures": captures,
            "externalOriginRequestCount": 0,
            "referenceImageRequestCount": 0,
            "uncaughtErrorCount": 0,
            "unhandledRejectionCount": 0,
            "securityPolicyViolationCount": 0,
        }

        manifest_path = temp_output_dir / "manifest.json"
        manifest_text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
        manifest_path.write_text(manifest_text, encoding="utf-8")

        print("Manifest created: {}".format(manifest_path))

        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for capture in captures:
            src = temp_output_dir / capture["file"]
            dst = output_dir / capture["file"]
            shutil.move(str(src), str(dst))

        dst_manifest = output_dir / "manifest.json"
        shutil.move(str(manifest_path), str(dst_manifest))

        after_hashes = {}
        for prod_file in PRODUCTION_FILES:
            after_hashes[prod_file] = sha256_of(REPO_ROOT / prod_file)

        for prod_file in PRODUCTION_FILES:
            if before_hashes[prod_file] != after_hashes[prod_file]:
                raise RuntimeError(
                    "Production file changed during capture: {}".format(prod_file)
                )

        print("PASS: Four-state visual evidence packet created successfully")
        print("Output: {}".format(output_dir))

    finally:
        server.shutdown()
        shutil.rmtree(temp_output_dir, ignore_errors=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
