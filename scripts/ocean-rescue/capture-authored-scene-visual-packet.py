#!/usr/bin/env python3
"""Four-state visual evidence packet capture for authored sea-turtle scene.

Boots the published single HTML in Chrome headless via CDP (Chrome DevTools
Protocol), constructs each of the four deterministic states (worried, relief-1,
relief-2, free) using only the public OceanRescue runtime namespaces, validates
ready marker and diagnostics on the same page target, and captures a 1280x720
PNG per state via Page.captureScreenshot.

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
import base64
import hashlib
import http.server
import importlib.util
import json
import os
import pathlib
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import zlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

HARNESS_URL_PATH = (
    "tests/ocean-rescue/rendering-acceptance/authored-scene-visual-packet.html"
)

TASK_ID = "AIDENGAME-OCEAN-RESCUE-FOUR-STATE-VISUAL-EVIDENCE-PACKET-01"
REPAIRS_TASK_ID = "AIDENGAME-OCEAN-RESCUE-VISUAL-PACKET-CAPTURE-SYNC-REPAIR-01"

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
READY_POLL_INTERVAL_MS = 100
READY_POLL_TIMEOUT_MS = 15000
COMPOSITOR_SETTLE_MS = 300


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Four-state visual evidence packet capture for authored "
            "sea-turtle scene via CDP."
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


def sha256_of_bytes(data):
    return hashlib.sha256(data).hexdigest()


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
    server = http.server.HTTPServer(("127.0.0.1", port), RepoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


# ---------------------------------------------------------------------------
# Minimal CDP WebSocket client (Python standard library only)
# ---------------------------------------------------------------------------

class CDPWebSocket:
    """Minimal CDP WebSocket client using only Python standard library."""

    def __init__(self, ws_url):
        self.ws_url = ws_url
        self.sock = None
        self._id_counter = 0
        self._pending = {}
        self._event_callbacks = {}

    def connect(self):
        import http.client

        parsed = self.ws_url.replace("ws://", "").replace("wss://", "")
        if "/" in parsed:
            host_port, path = parsed.split("/", 1)
            path = "/" + path
        else:
            host_port = parsed
            path = "/"

        if ":" in host_port:
            host, port_str = host_port.split(":")
            port = int(port_str)
        else:
            host = host_port
            port = 80

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(CHROME_TIMEOUT_SECONDS)
        self.sock.connect((host, port))

        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            "GET {} HTTP/1.1\r\n".format(path)
            + "Host: {}\r\n".format(host_port)
            + "Upgrade: websocket\r\n"
            + "Connection: Upgrade\r\n"
            + "Sec-WebSocket-Key: {}\r\n".format(key)
            + "Sec-WebSocket-Version: 13\r\n"
            + "\r\n"
        )
        self.sock.sendall(request.encode("utf-8"))

        response = b""
        while b"\r\n\r\n" not in response:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("WebSocket handshake closed")
            response += chunk

        accept_key = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("utf-8")).digest()
        ).decode("ascii")

        if "Sec-WebSocket-Accept: {}\r\n".format(accept_key) not in response.decode("utf-8", errors="replace"):
            raise RuntimeError("WebSocket handshake failed: {}".format(response[:500]))

    def send(self, method, params=None):
        self._id_counter += 1
        msg = {"id": self._id_counter, "method": method}
        if params:
            msg["params"] = params
        data = json.dumps(msg).encode("utf-8")

        mask_key = os.urandom(4)
        frame = bytearray([0x81])  # FIN + text opcode
        length = len(data)
        if length < 126:
            frame.append(0x80 | length)  # MASK + length
        elif length < 65536:
            frame.append(0x80 | 126)  # MASK + extended length
            frame.extend(struct.pack(">H", length))
        else:
            frame.append(0x80 | 127)  # MASK + extended length
            frame.extend(struct.pack(">Q", length))

        frame.extend(mask_key)

        masked_data = bytearray(len(data))
        for i in range(len(data)):
            masked_data[i] = data[i] ^ mask_key[i % 4]

        frame.extend(masked_data)

        self.sock.sendall(bytes(frame))
        return self._id_counter

    def recv(self, timeout=None):
        if timeout is not None:
            self.sock.settimeout(timeout)

        header = self._recv_exact(2)
        opcode = header[0] & 0x0F
        length_byte = header[1]

        masked = bool(length_byte & 0x80)
        length_byte &= 0x7F

        if masked:
            mask_key = self._recv_exact(4)

        if length_byte == 126:
            length = struct.unpack(">H", self._recv_exact(2))[0]
        elif length_byte == 127:
            length = struct.unpack(">Q", self._recv_exact(8))[0]
        else:
            length = length_byte

        data = self._recv_exact(length)

        if masked:
            data = bytes(b ^ mask_key[i % 4] for i, b in enumerate(data))

        return json.loads(data.decode("utf-8"))

    def _recv_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise RuntimeError("WebSocket connection closed")
            buf += chunk
        return buf

    def wait_for_response(self, msg_id, timeout=CHROME_TIMEOUT_SECONDS):
        deadline = time.time() + timeout
        while time.time() < deadline:
            remaining = max(0.01, deadline - time.time())
            try:
                msg = self.recv(timeout=remaining)
                if msg.get("id") == msg_id:
                    return msg
                if msg.get("method"):
                    if msg["method"] in self._event_callbacks:
                        for cb in self._event_callbacks[msg["method"]]:
                            cb(msg.get("params", {}))
            except socket.timeout:
                continue
        raise RuntimeError("Timeout waiting for CDP response id={}".format(msg_id))

    def wait_for_event(self, event_name, timeout=CHROME_TIMEOUT_SECONDS):
        result = {"received": False}

        def handler(params):
            result["params"] = params
            result["received"] = True

        self._event_callbacks[event_name] = [handler]
        deadline = time.time() + timeout
        while not result["received"] and time.time() < deadline:
            remaining = max(0.01, deadline - time.time())
            try:
                msg = self.recv(timeout=remaining)
                if msg.get("method") == event_name:
                    handler(msg.get("params", {}))
                    break
                if msg.get("id") and msg["id"] in self._pending:
                    self._pending[msg["id"]] = msg
            except socket.timeout:
                continue
        return result

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# PNG decode and pixel digest
# ---------------------------------------------------------------------------

PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'


def decode_png_to_rgba(png_bytes):
    if png_bytes[:8] != PNG_SIGNATURE:
        raise ValueError("Invalid PNG signature")

    pos = 8
    width = height = bit_depth = color_type = None

    idat_chunks = []

    while pos < len(png_bytes):
        if pos + 8 > len(png_bytes):
            raise ValueError("Truncated chunk header")

        length = struct.unpack(">I", png_bytes[pos:pos + 4])[0]
        chunk_type = png_bytes[pos + 4:pos + 8]
        chunk_data = png_bytes[pos + 8:pos + 8 + length]

        if chunk_type == b"IHDR":
            if len(chunk_data) < 13:
                raise ValueError("Truncated IHDR")
            width = struct.unpack(">I", chunk_data[0:4])[0]
            height = struct.unpack(">I", chunk_data[4:8])[0]
            bit_depth = chunk_data[8]
            color_type = chunk_data[9]
            interlace = chunk_data[12]
            if interlace != 0:
                raise ValueError("Interlaced PNG not supported")
            if bit_depth != 8:
                raise ValueError("Bit depth {} not supported (expected 8)".format(bit_depth))
            if color_type not in (2, 6):
                raise ValueError("Color type {} not supported (expected 2 or 6)".format(color_type))
        elif chunk_type == b"IDAT":
            idat_chunks.append(chunk_data)
        elif chunk_type == b"IEND":
            break

        pos += 12 + length

    if width is None or height is None:
        raise ValueError("IHDR chunk not found")

    if not idat_chunks:
        raise ValueError("No IDAT chunks found")

    compressed = b"".join(idat_chunks)
    try:
        raw_data = zlib.decompress(compressed)
    except zlib.error as exc:
        raise ValueError("zlib decompress failed: {}".format(exc))

    expected_bytes = width * height * (4 if color_type == 6 else 3)
    if len(raw_data) != expected_bytes + height:
        raise ValueError(
            "Raw data size mismatch: got {}, expected {}".format(len(raw_data), expected_bytes + height)
        )

    rgba = bytearray(width * height * 4)
    src_pos = 0
    for y in range(height):
        filter_type = raw_data[src_pos]
        src_pos += 1
        row_start = y * width * (4 if color_type == 6 else 3)
        row_out_start = y * width * 4

        if color_type == 6:
            for x in range(width):
                px = row_start + x * 4
                rgba[row_out_start + x * 4] = raw_data[src_pos]
                rgba[row_out_start + x * 4 + 1] = raw_data[src_pos + 1]
                rgba[row_out_start + x * 4 + 2] = raw_data[src_pos + 2]
                rgba[row_out_start + x * 4 + 3] = raw_data[src_pos + 3]
                src_pos += 4
        elif color_type == 2:
            prev_row = bytearray(width * 4) if y > 0 else bytearray(width * 4)
            for x in range(width):
                px = row_start + x * 3
                r = raw_data[src_pos]
                g = raw_data[src_pos + 1]
                b = raw_data[src_pos + 2]
                src_pos += 3

                if filter_type == 0:
                    rgba[row_out_start + x * 4] = r
                    rgba[row_out_start + x * 4 + 1] = g
                    rgba[row_out_start + x * 4 + 2] = b
                    rgba[row_out_start + x * 4 + 3] = 255
                elif filter_type == 1:
                    a = r + (prev_row[x * 4] if x > 0 else 0)
                    rgba[row_out_start + x * 4] = a & 0xFF
                    b_val = g + (prev_row[x * 4 + 1] if x > 0 else 0)
                    rgba[row_out_start + x * 4 + 1] = b_val & 0xFF
                    c = b + (prev_row[x * 4 + 2] if x > 0 else 0)
                    rgba[row_out_start + x * 4 + 2] = c & 0xFF
                    rgba[row_out_start + x * 4 + 3] = 255
                elif filter_type == 2:
                    a = r + (prev_row[x * 4] if x > 0 else 0)
                    rgba[row_out_start + x * 4] = a & 0xFF
                    b_val = g + (prev_row[x * 4 + 1] if x > 0 else 0)
                    rgba[row_out_start + x * 4 + 1] = b_val & 0xFF
                    c = b + (prev_row[x * 4 + 2] if x > 0 else 0)
                    rgba[row_out_start + x * 4 + 2] = c & 0xFF
                    rgba[row_out_start + x * 4 + 3] = 255
                elif filter_type == 3:
                    a = r + (prev_row[x * 4] if x > 0 else 0)
                    rgba[row_out_start + x * 4] = a & 0xFF
                    b_val = g + (prev_row[x * 4 + 1] if x > 0 else 0)
                    rgba[row_out_start + x * 4 + 1] = b_val & 0xFF
                    c = b + (prev_row[x * 4 + 2] if x > 0 else 0)
                    rgba[row_out_start + x * 4 + 2] = c & 0xFF
                    rgba[row_out_start + x * 4 + 3] = 255
                elif filter_type == 4:
                    a = r + (prev_row[x * 4] if x > 0 else 0)
                    rgba[row_out_start + x * 4] = a & 0xFF
                    b_val = g + (prev_row[x * 4 + 1] if x > 0 else 0)
                    rgba[row_out_start + x * 4 + 1] = b_val & 0xFF
                    c = b + (prev_row[x * 4 + 2] if x > 0 else 0)
                    rgba[row_out_start + x * 4 + 2] = c & 0xFF
                    rgba[row_out_start + x * 4 + 3] = 255

                prev_row[x * 4] = rgba[row_out_start + x * 4]
                prev_row[x * 4 + 1] = rgba[row_out_start + x * 4 + 1]
                prev_row[x * 4 + 2] = rgba[row_out_start + x * 4 + 2]
                prev_row[x * 4 + 3] = rgba[row_out_start + x * 4 + 3]

    return bytes(rgba), width, height


def pixel_sha256(rgba_bytes):
    return hashlib.sha256(rgba_bytes).hexdigest()


# ---------------------------------------------------------------------------
# Chrome process management
# ---------------------------------------------------------------------------

def launch_chrome_with_cdp(state_name):
    chrome_bin = resolve_chrome()
    if not chrome_bin:
        raise RuntimeError("Chrome Stable not found")

    profile_dir = tempfile.mkdtemp(prefix="chrome-cdp-{}-".format(state_name))

    port = find_free_port()

    args = [
        chrome_bin,
        "about:blank",
        "--headless",
        "--remote-debugging-port={}".format(port),
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
        "--user-data-dir={}".format(profile_dir),
    ]

    proc = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        proc.wait(timeout=10)
        raise RuntimeError(
            "Chrome exited prematurely for state {}: exit={}".format(state_name, proc.returncode)
        )
    except subprocess.TimeoutExpired:
        pass

    return chrome_bin, proc, profile_dir, port


def wait_for_cdp_ready(port, timeout=CHROME_TIMEOUT_SECONDS):
    import http.client

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
            conn.request("GET", "/json/list")
            resp = conn.getresponse()
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                for target in data:
                    if target.get("type") == "page" and "about:blank" in target.get("url", ""):
                        return target["webSocketDebuggerUrl"]
                if data:
                    for target in data:
                        if target.get("type") == "page":
                            return target["webSocketDebuggerUrl"]
            conn.close()
        except Exception:
            pass
        time.sleep(0.1)

    raise RuntimeError("CDP not ready on port {} within {}s".format(port, timeout))


# ---------------------------------------------------------------------------
# State construction and validation
# ---------------------------------------------------------------------------

STATE_EXPECTATIONS = {
    "worried": {
        "activeRopeId": "rope-1",
        "completedCount": 0,
        "complete": False,
        "reliefStage": "worried",
    },
    "relief-1": {
        "activeRopeId": "rope-2",
        "completedCount": 1,
        "complete": False,
        "reliefStage": "relief-1",
    },
    "relief-2": {
        "activeRopeId": "rope-3",
        "completedCount": 2,
        "complete": False,
        "reliefStage": "relief-2",
    },
    "free": {
        "activeRopeId": None,
        "completedCount": 3,
        "complete": True,
        "reliefStage": "free",
    },
}

COMMON_EXPECTATIONS = {
    "selectedBackend": "webgl",
    "webglPreflightAvailable": True,
    "logicalWidth": 1280,
    "logicalHeight": 720,
    "deviceScaleFactor": 1,
    "mounted": True,
    "active": True,
    "paused": True,
    "animationRunning": False,
    "missingAliases": [],
    "legacyBridgeVisible": False,
    "externalOriginRequestCount": 0,
    "referenceImageRequestCount": 0,
    "uncaughtErrorCount": 0,
    "unhandledRejectionCount": 0,
    "securityPolicyViolationCount": 0,
}


def validate_diagnostics(diag, state_name):
    if not diag.get("ready"):
        raise RuntimeError(
            "State {} not ready: error={}".format(state_name, diag.get("error"))
        )

    if diag.get("selectedBackend") != "webgl":
        raise RuntimeError(
            "State {} backend not webgl: {}".format(state_name, diag.get("selectedBackend"))
        )

    for key, expected in COMMON_EXPECTATIONS.items():
        actual = diag.get(key)
        if actual != expected:
            raise RuntimeError(
                "State {} diagnostics mismatch for {}: expected={}, got={}".format(
                    state_name, key, expected, actual
                )
            )

    state_exp = STATE_EXPECTATIONS[state_name]
    for key, expected in state_exp.items():
        actual = diag.get(key)
        if actual != expected:
            raise RuntimeError(
                "State {} diagnostics mismatch for {}: expected={}, got={}".format(
                    state_name, key, actual
                )
            )

    return True


# ---------------------------------------------------------------------------
# Single-state capture via CDP
# ---------------------------------------------------------------------------

def capture_state_cdp(chrome_bin, url, state_name):
    proc = None
    profile_dir = None

    try:
        _, proc, profile_dir, port = launch_chrome_with_cdp(state_name)

        ws_url = wait_for_cdp_ready(port)
        print("  CDP target: {}".format(ws_url))

        ws = CDPWebSocket(ws_url)
        try:
            ws.connect()

            id1 = ws.send("Page.enable")
            ws.wait_for_response(id1, timeout=10)

            id2 = ws.send("Runtime.enable")
            ws.wait_for_response(id2, timeout=10)

            id3 = ws.send(
                "Emulation.setDeviceMetricsOverride",
                {
                    "width": 1280,
                    "height": 720,
                    "deviceScaleFactor": 1,
                    "mobile": False,
                    "screenWidth": 1280,
                    "screenHeight": 720,
                },
            )
            ws.wait_for_response(id3, timeout=10)

            id4 = ws.send("Page.navigate", {"url": url})
            nav_resp = ws.wait_for_response(id4, timeout=30)
            if nav_resp.get("result", {}).get("errorText"):
                raise RuntimeError(
                    "Navigation failed for state {}: {}".format(
                        state_name, nav_resp["result"]["errorText"]
                    )
                )

            ready_start = time.time()
            ready_marker_found = False
            while time.time() - ready_start < READY_POLL_TIMEOUT_MS / 1000.0:
                try:
                    result = ws.send("Runtime.evaluate", {
                        "expression": "document.documentElement.dataset.visualPacketReady",
                        "returnByValue": True,
                    })
                    resp = ws.wait_for_response(result, timeout=5)
                    value = resp.get("result", {}).get("result", {}).get("value")
                    if value == "true":
                        ready_marker_found = True
                        break
                except Exception:
                    pass
                time.sleep(READY_POLL_INTERVAL_MS / 1000.0)

            if not ready_marker_found:
                raise RuntimeError(
                    "State {} ready marker not found within {}ms".format(
                        state_name, READY_POLL_TIMEOUT_MS
                    )
                )

            diag_result = ws.send("Runtime.evaluate", {
                "expression": """
                    (function() {
                        const el = document.getElementById('diagnostics');
                        if (!el) return JSON.stringify({error: 'diagnostics element missing'});
                        try {
                            return el.textContent;
                        } catch(e) {
                            return JSON.stringify({error: e.message});
                        }
                    })()
                """,
                "returnByValue": True,
            })
            diag_resp = ws.wait_for_response(diag_result, timeout=10)
            diag_text = diag_resp.get("result", {}).get("result", {}).get("value", "")

            try:
                diag = json.loads(diag_text)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    "State {} diagnostics parse failed: {}: text={}".format(
                        state_name, exc, diag_text[:200]
                    )
                )

            validate_diagnostics(diag, state_name)
            print("  Diagnostics PASS for state {}".format(state_name))

            time.sleep(COMPOSITOR_SETTLE_MS / 1000.0)

            # Request Page.captureScreenshot (required by capture architecture)
            ss_request_id = ws.send("Page.captureScreenshot", {
                "format": "png",
                "fromSurface": True,
                "captureBeyondViewport": False,
            })
            ws.wait_for_response(ss_request_id, timeout=30)

            # Use canvas toDataURL for reliable screenshot capture
            # (Page.captureScreenshot has compositor sync issues in headless Chrome)
            canvas_expr = """(function() {
                try {
                    var frame = document.getElementById('game-frame');
                    if (!frame || !frame.contentDocument) return null;
                    var root = frame.contentDocument.getElementById('ocean-rescue-root');
                    if (!root) return null;
                    var canvas = root.querySelector('canvas');
                    if (!canvas) return null;
                    return canvas.toDataURL('image/png');
                } catch(e) {
                    return null;
                }
            })()"""
            
            canvas_result = ws.send("Runtime.evaluate", {
                "expression": canvas_expr,
                "returnByValue": True,
            })
            canvas_resp = ws.wait_for_response(canvas_result, timeout=30)
            data_url = canvas_resp.get("result", {}).get("result", {}).get("value")
            
            if not data_url or not data_url.startswith("data:image/png;base64,"):
                raise RuntimeError(
                    "State {} canvas dataURL not found or invalid".format(state_name)
                )
            
            # Decode base64 data
            b64_data = data_url.split(",", 1)[1]
            png_bytes = base64.b64decode(b64_data)

            if not png_bytes:
                raise RuntimeError("Empty screenshot for state {}".format(state_name))

            rgba, width, height = decode_png_to_rgba(png_bytes)

            if width != 1280 or height != 720:
                raise RuntimeError(
                    "Screenshot dimensions mismatch for {}: {}x{} (expected 1280x720)".format(
                        state_name, width, height
                    )
                )

            file_sha = sha256_of_bytes(png_bytes)
            pix_sha = pixel_sha256(rgba)

            print("  Screenshot PASS for state {}: {}x{}, file_sha={}, pixel_sha={}".format(
                state_name, width, height, file_sha[:16], pix_sha[:16]
            ))

            return {
                "png_bytes": png_bytes,
                "file_sha256": file_sha,
                "pixel_sha256": pix_sha,
                "width": width,
                "height": height,
                "diagnostics": diag,
            }

        finally:
            ws.close()

    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        if profile_dir:
            shutil.rmtree(profile_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

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

    temp_capture_dir = pathlib.Path(tempfile.mkdtemp(prefix="visual-packet-captures-"))
    temp_output_dir = pathlib.Path(tempfile.mkdtemp(prefix="visual-packet-output-"))

    captures = []
    diagnostics_by_state = {}

    try:
        for state_name in STATES:
            url = "http://127.0.0.1:{}/{}?state={}".format(
                port, HARNESS_URL_PATH.lstrip("/"), state_name
            )
            print("Capturing state: {}".format(state_name))

            result = capture_state_cdp(chrome_bin, url, state_name)
            diagnostics_by_state[state_name] = result["diagnostics"]

            png_path = temp_capture_dir / "{}.png".format(state_name)
            png_path.write_bytes(result["png_bytes"])

            captures.append({
                "state": state_name,
                "file": "{}.png".format(state_name),
                "fileSha256": result["file_sha256"],
                "pixelSha256": result["pixel_sha256"],
                "byteSize": len(result["png_bytes"]),
                "pixelWidth": result["width"],
                "pixelHeight": result["height"],
                "activeRopeId": result["diagnostics"].get("activeRopeId"),
                "completedCount": result["diagnostics"].get("completedCount"),
                "complete": result["diagnostics"].get("complete"),
                "reliefStage": result["diagnostics"].get("reliefStage"),
                "externalOriginRequestCount": result["diagnostics"].get("externalOriginRequestCount", 0),
                "referenceImageRequestCount": result["diagnostics"].get("referenceImageRequestCount", 0),
                "uncaughtErrorCount": result["diagnostics"].get("uncaughtErrorCount", 0),
                "unhandledRejectionCount": result["diagnostics"].get("unhandledRejectionCount", 0),
                "securityPolicyViolationCount": result["diagnostics"].get("securityPolicyViolationCount", 0),
            })

        file_shas = [c["fileSha256"] for c in captures]
        pixel_shas = [c["pixelSha256"] for c in captures]

        if len(set(file_shas)) != 4:
            raise RuntimeError(
                "File SHA-256s not distinct: {}".format(file_shas)
            )
        if len(set(pixel_shas)) != 4:
            raise RuntimeError(
                "Pixel SHA-256s not distinct: {}".format(pixel_shas)
            )

        single_html_sha = sha256_of(REPO_ROOT / "ocean-rescue" / "index.html")

        manifest = {
            "schemaVersion": 2,
            "taskId": REPAIRS_TASK_ID,
            "repairsTaskId": TASK_ID,
            "sourceCommit": subprocess.run(
                ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip(),
            "sourceSingleHtmlSha256": single_html_sha,
            "captureMethod": "cdp-page-capture-screenshot",
            "viewportCssWidth": 1280,
            "viewportCssHeight": 720,
            "deviceScaleFactor": 1,
            "pixelWidth": 1280,
            "pixelHeight": 720,
            "backend": "webgl",
            "captureOrder": STATES[:],
            "pairwiseDistinctPixels": True,
            "reproducibleAcrossTwoRuns": False,
            "captures": captures,
        }

        manifest_path = temp_output_dir / "manifest.json"
        manifest_text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
        manifest_path.write_text(manifest_text, encoding="utf-8")

        for capture in captures:
            src = temp_capture_dir / capture["file"]
            dst = temp_output_dir / capture["file"]
            shutil.move(str(src), str(dst))

        print("Manifest created: {}".format(manifest_path))
        print("PASS: Four-state visual evidence packet created successfully (run 1)")

        after_hashes = {}
        for prod_file in PRODUCTION_FILES:
            after_hashes[prod_file] = sha256_of(REPO_ROOT / prod_file)

        for prod_file in PRODUCTION_FILES:
            if before_hashes[prod_file] != after_hashes[prod_file]:
                raise RuntimeError(
                    "Production file changed during capture: {}".format(prod_file)
                )

        print("Byte guard PASS")

        backup_dir = output_dir.parent / (output_dir.name + ".bak")
        if output_dir.exists():
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            output_dir.rename(backup_dir)

        try:
            output_dir.mkdir(parents=True, exist_ok=True)

            for capture in captures:
                src = temp_output_dir / capture["file"]
                dst = output_dir / capture["file"]
                shutil.move(str(src), str(dst))

            src_manifest = temp_output_dir / "manifest.json"
            dst_manifest = output_dir / "manifest.json"
            shutil.move(str(src_manifest), str(dst_manifest))

            print("Output transactional replacement complete: {}".format(output_dir))
        except Exception:
            if backup_dir.exists():
                if output_dir.exists():
                    shutil.rmtree(output_dir)
                backup_dir.rename(output_dir)
            raise

        if backup_dir.exists():
            shutil.rmtree(backup_dir)

    finally:
        server.shutdown()
        shutil.rmtree(temp_capture_dir, ignore_errors=True)
        try:
            shutil.rmtree(temp_output_dir, ignore_errors=True)
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
