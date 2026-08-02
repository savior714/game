#!/usr/bin/env python3
"""Render proof harness for the otter-head-01 handoff candidate.

Proves that a STRUCTURE_PASS otter-head SVG candidate renders at its declared
1x/2x sizes and that the candidate raster assembles cleanly into the live Sea
Turtle rescue rig (``sea-otter-head``) with the existing eye/mouth overlays.

The proof NEVER canonicalizes the candidate, rebuilds the atlas, rebuilds the
single HTML, or modifies any production file. It only:

  1. Validates the input gate (brief, inbox SVG, structure report).
  2. Renders the inbox SVG with the pinned atlas rasterizer (CairoSVG 2.9.0)
     at 1x (200x200) and 2x (400x400) and validates the isolated pixels.
  3. Boots the tracked production single HTML through the normal product flow
     (mission -> GUP -> launch -> skip -> travel arrival -> site transition ->
     tutorial -> rescue active), freezes the sea-turtle scene at a
     deterministic t=0 state, and temporarily applies the candidate 1x raster
     to the ``sea-otter-head`` sprite only.
  4. Captures four face states (base-only, neutral, concern, smile) cropped
     around the head, a full-screen context shot, and a contact sheet, twice,
     then checks cross-run pixel determinism.
  5. Writes manifest.json + render-proof-report.md under the evidence root.

Exit codes:
    0  RENDER_PROOF_READY
    1  RENDER_REJECTED
    2  BLOCKED
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import pathlib
import socketserver
import sys
import threading
from http.server import SimpleHTTPRequestHandler

TASK_ID = "AIDENGAME-OCEAN-RESCUE-OTTER-HEAD-HANDOFF-RENDER-PROOF-01"
ASSET_ID = "otter-head-01"
ALIAS = "otter.head"

SOURCE_LOGICAL_SIZE = [200, 200]
PIVOT = [0.5, 0.55]
RUNTIME_SCALE = [0.62, 0.62]
LOGICAL_VIEWPORT = [1280, 720]
DEVICE_SCALE_FACTOR = 1
VIEWBOX = "0 0 200 200"

RASTERIZER = "CairoSVG"
RASTERIZER_VERSION = "2.9.0"

CAIRO_LIB_PATHS = ("/opt/homebrew/opt/cairo/lib", "/opt/homebrew/lib")
CAIRO_ENV = {"DYLD_LIBRARY_PATH": CAIRO_LIB_PATHS[0]}

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

HEAD_SPRITE_LABEL = "sea-otter-head"
EYE_OVERLAY_LABELS = ("sea-otter-eyes-open", "sea-otter-eyes-closed")
MOUTH_OVERLAY_LABELS = (
    "sea-otter-mouth-neutral",
    "sea-otter-mouth-concern",
    "sea-otter-mouth-smile",
)
OTHER_RIG_LABELS = (
    "sea-otter-tail",
    "sea-otter-arm-far",
    "sea-otter-torso",
    "sea-otter-arm-near",
)

CANDIDATE_TEXTURE_SIZE = [200, 200]
CANDIDATE_TEXTURE_LABEL = "candidate-otter-head-01"

FACE_STATES = [
    {
        "name": "base-only",
        "rotation": 0.0,
        "eyes": "none",
        "mouth": "none",
    },
    {
        "name": "neutral",
        "rotation": 0.0,
        "eyes": "open",
        "mouth": "neutral",
    },
    {
        "name": "concern",
        "rotation": 0.035,
        "eyes": "open",
        "mouth": "concern",
    },
    {
        "name": "smile",
        "rotation": -0.025,
        "eyes": "closed",
        "mouth": "smile",
    },
]

# Face crop region (logical pixels) centered around the otter head rig.
FACE_CROP = {"x": 440, "y": 230, "width": 300, "height": 300}

PRODUCTION_FILES = [
    "ocean-rescue/index.html",
    "domains/ocean-rescue/src/render-runtime.js",
    "domains/ocean-rescue/src/render-assets.generated.js",
    "domains/ocean-rescue/src/sea-turtle-scene.js",
    "domains/ocean-rescue/src/sea-turtle.js",
    "domains/ocean-rescue/assets/source/art-packet.json",
    "domains/ocean-rescue/assets/source/art-approval.json",
    "domains/ocean-rescue/assets/source/characters/otter-head.svg",
    "domains/ocean-rescue/assets/generated/atlas-manifest.json",
    "domains/ocean-rescue/assets/generated/characters/characters-0.json",
    "domains/ocean-rescue/assets/generated/characters/characters-0.png",
]

FORBIDDEN_WRITE_PREFIXES = (
    "domains/ocean-rescue/assets/handoff/inbox/",
    "domains/ocean-rescue/assets/handoff/briefs/",
    "domains/ocean-rescue/assets/source/",
    "domains/ocean-rescue/assets/generated/",
    "domains/ocean-rescue/src/",
    "ocean-rescue/index.html",
)


# ---------------------------------------------------------------------------
# Hash / JSON helpers
# ---------------------------------------------------------------------------


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(repo_root: pathlib.Path, value: str) -> pathlib.Path:
    p = pathlib.Path(value)
    if p.is_absolute():
        return p
    return repo_root / p


def run_env() -> dict:
    env = dict(os.environ)
    env.update(CAIRO_ENV)
    return env


# ---------------------------------------------------------------------------
# PNG decoding (stdlib)
# ---------------------------------------------------------------------------


def decode_png_to_rgba(png_bytes: bytes):
    """Decode an 8-bit RGB/RGBA PNG into raw RGBA bytes.

    Returns (rgba_bytes, width, height). Supports filter types 0-4.
    """
    import struct
    import zlib

    if png_bytes[:8] != PNG_SIGNATURE:
        raise ValueError("Invalid PNG signature")
    pos = 8
    width = height = bit_depth = color_type = None
    idat_chunks = []
    while pos < len(png_bytes):
        if pos + 8 > len(png_bytes):
            raise ValueError("Truncated chunk header")
        length = struct.unpack(">I", png_bytes[pos : pos + 4])[0]
        chunk_type = png_bytes[pos + 4 : pos + 8]
        chunk_data = png_bytes[pos + 8 : pos + 8 + length]
        if chunk_type == b"IHDR":
            if len(chunk_data) < 13:
                raise ValueError("Truncated IHDR")
            width = struct.unpack(">I", chunk_data[0:4])[0]
            height = struct.unpack(">I", chunk_data[4:8])[0]
            bit_depth = chunk_data[8]
            color_type = chunk_data[9]
            if chunk_data[12] != 0:
                raise ValueError("Interlaced PNG not supported")
            if bit_depth != 8:
                raise ValueError(
                    "Bit depth {} not supported (expected 8)".format(bit_depth)
                )
            if color_type not in (2, 6):
                raise ValueError(
                    "Color type {} not supported (expected 2 or 6)".format(color_type)
                )
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
    channels = 4 if color_type == 6 else 3
    expected_bytes = width * height * channels
    if len(raw_data) != expected_bytes + height:
        raise ValueError(
            "Raw data size mismatch: got {}, expected {}".format(
                len(raw_data), expected_bytes + height
            )
        )
    rgba = bytearray(width * height * 4)
    src_pos = 0
    prev_row = bytearray(width * 4)
    for y in range(height):
        filter_type = raw_data[src_pos]
        src_pos += 1
        row = bytearray(raw_data[src_pos : src_pos + width * channels])
        src_pos += width * channels
        out_row = bytearray(width * 4)
        for x in range(width):
            base = x * channels
            if channels == 4:
                out_row[x * 4] = row[base]
                out_row[x * 4 + 1] = row[base + 1]
                out_row[x * 4 + 2] = row[base + 2]
                out_row[x * 4 + 3] = row[base + 3]
            else:
                out_row[x * 4] = row[base]
                out_row[x * 4 + 1] = row[base + 1]
                out_row[x * 4 + 2] = row[base + 2]
                out_row[x * 4 + 3] = 255
        if filter_type == 1:
            for x in range(width):
                for c in range(4):
                    left = out_row[(x - 1) * 4 + c] if x > 0 else 0
                    out_row[x * 4 + c] = (out_row[x * 4 + c] + left) & 0xFF
        elif filter_type == 2:
            for x in range(width):
                for c in range(4):
                    up = prev_row[x * 4 + c]
                    out_row[x * 4 + c] = (out_row[x * 4 + c] + up) & 0xFF
        elif filter_type == 3:
            for x in range(width):
                for c in range(4):
                    left = out_row[(x - 1) * 4 + c] if x > 0 else 0
                    up = prev_row[x * 4 + c]
                    out_row[x * 4 + c] = (
                        out_row[x * 4 + c] + ((left + up) >> 1)
                    ) & 0xFF
        elif filter_type == 4:
            for x in range(width):
                for c in range(4):
                    left = out_row[(x - 1) * 4 + c] if x > 0 else 0
                    up = prev_row[x * 4 + c]
                    ul = prev_row[(x - 1) * 4 + c] if x > 0 else 0
                    p = left + up - ul
                    pa = abs(p - left)
                    pb = abs(p - up)
                    pc = abs(p - ul)
                    if pa <= pb and pa <= pc:
                        pred = left
                    elif pb <= pc:
                        pred = up
                    else:
                        pred = ul
                    out_row[x * 4 + c] = (out_row[x * 4 + c] + pred) & 0xFF
        rgba[y * width * 4 : (y + 1) * width * 4] = out_row
        prev_row = out_row
    return bytes(rgba), width, height


# ---------------------------------------------------------------------------
# Input gate
# ---------------------------------------------------------------------------


def run_input_gate(repo_root: pathlib.Path, args) -> tuple[bool, str]:
    """Validate that every required input exists and the structure gate holds."""
    brief = resolve_path(repo_root, args.brief)
    svg = resolve_path(repo_root, args.svg)
    structure = resolve_path(repo_root, args.structure_report)

    if not brief.is_file():
        return False, "ACTIVE_BRIEF_MISSING"
    if not svg.is_file():
        return False, "INBOX_SVG_MISSING"
    if not structure.is_file():
        return False, "STRUCTURE_REPORT_MISSING"

    report = load_json(structure)
    if report.get("verdict") != "STRUCTURE_PASS":
        return False, "STRUCTURE_GATE_NOT_PASSED"
    if report.get("assetId") != ASSET_ID:
        return False, "STRUCTURE_REPORT_ASSET_ID_MISMATCH"
    if report.get("alias") != ALIAS:
        return False, "STRUCTURE_REPORT_ALIAS_MISMATCH"
    svg_sha = sha256_file(svg)
    if report.get("svgSha256") != svg_sha:
        return False, "STRUCTURE_REPORT_INPUT_SHA_MISMATCH"
    return True, ""


# ---------------------------------------------------------------------------
# Isolated render (pinned atlas rasterizer)
# ---------------------------------------------------------------------------


def render_svg_to_png(svg_path: pathlib.Path, width: int, height: int) -> bytes:
    """Rasterize an SVG with the exact pinned atlas rasterizer (CairoSVG)."""
    for lib_path in CAIRO_LIB_PATHS:
        if os.path.isdir(lib_path):
            existing = os.environ.get("DYLD_LIBRARY_PATH", "")
            if lib_path not in existing.split(":"):
                os.environ["DYLD_LIBRARY_PATH"] = lib_path + (
                    (":" + existing) if existing else ""
                )
            break
    import cairosvg

    return cairosvg.svg2png(
        url=str(svg_path),
        output_width=width,
        output_height=height,
    )


def analyze_isolated_png(png_bytes: bytes, expected_w: int, expected_h: int) -> dict:
    """Analyze an isolated render. Pure logic over PNG bytes + PIL."""
    from PIL import Image

    if png_bytes[:8] != PNG_SIGNATURE:
        raise ValueError("Invalid PNG signature")
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    width, height = img.size
    alpha = img.split()[3]
    bbox = alpha.getbbox()
    extrema = img.getextrema()
    rgba, _w, _h = decode_png_to_rgba(png_bytes)
    pixel_sha = sha256_bytes(rgba)

    visible_bounds = None
    if bbox is not None:
        x0, y0, x1, y1 = bbox
        visible_bounds = {
            "x": x0,
            "y": y0,
            "width": x1 - x0,
            "height": y1 - y0,
        }

    return {
        "width": width,
        "height": height,
        "expectedWidth": expected_w,
        "expectedHeight": expected_h,
        "alphaPresent": img.mode == "RGBA",
        "alphaMin": extrema[3][0],
        "alphaMax": extrema[3][1],
        "visibleAlphaBounds": visible_bounds,
        "pixelSha256": pixel_sha,
        "fileSha256": sha256_bytes(png_bytes),
        "byteSize": len(png_bytes),
    }


def check_isolated(analysis: dict) -> tuple[bool, list[str]]:
    reasons = []
    if (
        analysis["width"] != analysis["expectedWidth"]
        or analysis["height"] != analysis["expectedHeight"]
    ):
        reasons.append(
            "dimension mismatch: {}x{} != {}x{}".format(
                analysis["width"],
                analysis["height"],
                analysis["expectedWidth"],
                analysis["expectedHeight"],
            )
        )
    if not analysis["alphaPresent"]:
        reasons.append("no alpha channel")
    if analysis["visibleAlphaBounds"] is None:
        reasons.append("no visible alpha bounds")
    elif (
        analysis["visibleAlphaBounds"]["width"] <= 0
        or analysis["visibleAlphaBounds"]["height"] <= 0
    ):
        reasons.append("empty visible bounds")
    if analysis["alphaMax"] == 0:
        reasons.append("completely transparent raster")
    bbox = analysis["visibleAlphaBounds"]
    if bbox is not None:
        x0 = bbox["x"]
        y0 = bbox["y"]
        x1 = x0 + bbox["width"]
        y1 = y0 + bbox["height"]
        if x0 < 0 or y0 < 0 or x1 > analysis["width"] or y1 > analysis["height"]:
            reasons.append("visible bounds outside frame")
        if x0 <= 0 or y0 <= 0 or x1 >= analysis["width"] or y1 >= analysis["height"]:
            reasons.append("material clipping at frame edge")
        frame_area = analysis["width"] * analysis["height"]
        bound_area = bbox["width"] * bbox["height"]
        if analysis["alphaMin"] == 255 and bound_area >= 0.99 * frame_area:
            reasons.append("opaque full-canvas background")
    if analysis["byteSize"] <= 0:
        reasons.append("empty output file")
    return (not reasons, reasons)


# ---------------------------------------------------------------------------
# Playwright in-context capture
# ---------------------------------------------------------------------------


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(kwargs.pop("directory")), **kwargs)

    def log_message(self, *args):
        pass


def make_handler(directory):
    def factory(*args, **kwargs):
        return QuietHandler(*args, directory=directory, **kwargs)

    return factory


def start_server(repo_root: pathlib.Path, port: int):
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("127.0.0.1", port), make_handler(str(repo_root)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def find_free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


FREEZE_INIT_SCRIPT = """
window.__oceanFrozen = false;
window.__cspViolations = [];
window.__unhandledRejections = [];
document.addEventListener('securitypolicyviolation', function (e) {
  window.__cspViolations.push(e.blockedURI);
});
window.addEventListener('unhandledrejection', function (e) {
  window.__unhandledRejections.push(String(e && e.reason));
});
var __install = function () {
  var root = document.getElementById('ocean-rescue-root');
  if (!root) return;
  var __obs = new MutationObserver(function () {
    if (window.__oceanFrozen) return;
    if (root.getAttribute('data-rescue-phase') === 'active' &&
        root.getAttribute('data-sea-turtle-scene') === 'active') {
      window.__oceanFrozen = true;
      var O = window.OceanRescue;
      if (!O || !O.SeaTurtleScene) return;
      if (O.SeaTurtleScene.isMounted()) {
        O.SeaTurtleScene.pause();
      }
    }
  });
  __obs.observe(root, { attributes: true, attributeFilter: ['data-rescue-phase', 'data-sea-turtle-scene'] });
};
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', __install);
} else {
  __install();
}
"""

APPLY_CANDIDATE_SCRIPT = """
(dataUri) => {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      try {
        const Source = window.PIXI.ImageSource || window.PIXI.TextureSource;
        const source = new Source({ resource: img, label: 'candidate-otter-head-01' });
        const tex = new window.PIXI.Texture({ source: source, label: 'candidate-otter-head-01' });
        const rig = window.OceanRescue.RenderRuntime.getContainer('seaOtterRig');
        if (!rig) { resolve({ ok: false, error: 'seaOtterRig container missing' }); return; }
        const find = (label) => rig.children.find((c) => c.label === label);
        const head = find('sea-otter-head');
        if (!head || typeof head.texture === 'undefined') {
          resolve({ ok: false, error: 'sea-otter-head sprite not found' });
          return;
        }
        const before = {};
        for (const child of rig.children) {
          if (child && child.label) {
            before[child.label] = child.texture ? child.texture.label : null;
          }
        }
        window.__headSprite = head;
        window.__rigTextureBefore = before;
        head.texture = tex;
        window.OceanRescue.RenderRuntime.renderSceneFrame();
        resolve({
          ok: true,
          headFound: true,
          originalHeadTexture: before['sea-otter-head'],
          candidateTexture: tex.label,
          candidateSourceWidth: source.width,
          candidateSourceHeight: source.height
        });
      } catch (e) {
        resolve({ ok: false, error: String((e && e.stack) || e) });
      }
    };
    img.onerror = () => resolve({ ok: false, error: 'candidate image decode failed' });
    img.src = dataUri;
  });
}
"""

SET_FACE_STATE_SCRIPT = """
(state) => {
  const rig = window.OceanRescue.RenderRuntime.getContainer('seaOtterRig');
  const find = (label) => rig.children.find((c) => c.label === label);
  const head = window.__headSprite || find('sea-otter-head');
  const eyesOpen = find('sea-otter-eyes-open');
  const eyesClosed = find('sea-otter-eyes-closed');
  const mNeutral = find('sea-otter-mouth-neutral');
  const mConcern = find('sea-otter-mouth-concern');
  const mSmile = find('sea-otter-mouth-smile');
  head.rotation = state.rotation;
  eyesOpen.visible = state.eyes === 'open';
  eyesClosed.visible = state.eyes === 'closed';
  mNeutral.visible = state.mouth === 'neutral';
  mConcern.visible = state.mouth === 'concern';
  mSmile.visible = state.mouth === 'smile';
  window.OceanRescue.RenderRuntime.renderSceneFrame();
  return {
    headRotation: head.rotation,
    eyesOpenVisible: eyesOpen.visible,
    eyesClosedVisible: eyesClosed.visible,
    mouthNeutralVisible: mNeutral.visible,
    mouthConcernVisible: mConcern.visible,
    mouthSmileVisible: mSmile.visible
  };
}
"""

COLLECT_SCRIPT = """
() => {
  const root = document.getElementById('ocean-rescue-root');
  const attr = (name) => root ? root.getAttribute(name) : null;
  const diag = {};
  for (const name of [
    'data-ocean-rescue-ready',
    'data-render-runtime',
    'data-render-backend',
    'data-render-logical-width',
    'data-render-logical-height',
    'data-render-legacy-visible',
    'data-rescue-phase',
    'data-sea-turtle-scene',
    'data-sea-turtle-scene-node-count',
    'data-sea-turtle-scene-relief',
    'data-sea-turtle-scene-active-rope',
    'data-sea-turtle-scene-animation',
    'data-sea-turtle-scene-legacy-visible',
    'data-sea-turtle-active',
    'data-sea-turtle-rope-id',
    'data-sea-turtle-completed-count'
  ]) {
    diag[name] = attr(name);
  }
  const rig = OceanRescue.RenderRuntime.getContainer('seaOtterRig');
  const find = (label) => rig.children.find((c) => c.label === label);
  const head = find('sea-otter-head');
  const headTex = head ? head.texture : null;
  const anchor = head ? { x: head.anchor.x, y: head.anchor.y } : null;
  let bounds = null;
  if (head && typeof head.getBounds === 'function') {
    try {
      const b = head.getBounds();
      bounds = { x: b.x, y: b.y, width: b.width, height: b.height };
    } catch (e) {
      bounds = { error: String(e) };
    }
  }
  const rigTextureAfter = {};
  for (const child of rig.children) {
    if (child && child.label) {
      rigTextureAfter[child.label] = child.texture ? child.texture.label : null;
    }
  }
  const faceState = {
    headRotation: head ? head.rotation : null,
    eyesOpenVisible: find('sea-otter-eyes-open') ? find('sea-otter-eyes-open').visible : null,
    eyesClosedVisible: find('sea-otter-eyes-closed') ? find('sea-otter-eyes-closed').visible : null,
    mouthNeutralVisible: find('sea-otter-mouth-neutral') ? find('sea-otter-mouth-neutral').visible : null,
    mouthConcernVisible: find('sea-otter-mouth-concern') ? find('sea-otter-mouth-concern').visible : null,
    mouthSmileVisible: find('sea-otter-mouth-smile') ? find('sea-otter-mouth-smile').visible : null
  };
  const texturesUnchanged = (() => {
    const before = window.__rigTextureBefore || {};
    const keys = Object.keys(before);
    if (keys.length === 0) return null;
    for (const key of keys) {
      if (key === 'sea-otter-head') continue;
      if (before[key] !== rigTextureAfter[key]) return false;
    }
    return true;
  })();
  return {
    diag: diag,
    frozen: window.__oceanFrozen === true,
    headSprite: head ? {
      label: head.label,
      isSprite: head instanceof PIXI.Sprite,
      visible: head.visible,
      renderable: head.renderable,
      x: head.x,
      y: head.y,
      rotation: head.rotation,
      scaleX: head.scale.x,
      scaleY: head.scale.y,
      anchor: anchor,
      textureLabel: headTex ? headTex.label : null,
      textureOrig: headTex ? { w: headTex.orig.width, h: headTex.orig.height } : null,
      bounds: bounds
    } : null,
    faceState: faceState,
    otherRigTextures: rigTextureAfter,
    texturesUnchanged: texturesUnchanged,
    legacyBridgeVisible: OceanRescue.RenderRuntime.getLegacyBridgeVisible
      ? OceanRescue.RenderRuntime.getLegacyBridgeVisible() : null,
    csp: window.__cspViolations || [],
    unhandled: window.__unhandledRejections || []
  };
}
"""


def capture_face_state(pg, state_spec):
    """Apply one face state and return (full_png_bytes, state_result)."""
    state_result = pg.evaluate(SET_FACE_STATE_SCRIPT, state_spec)
    canvas = pg.locator("#ocean-rescue-canvas")
    png_bytes = canvas.screenshot()
    return png_bytes, state_result


def run_in_context_capture(
    repo_root: pathlib.Path,
    base_url: str,
    candidate_data_uri: str,
    run_index: int,
) -> dict:
    from playwright.sync_api import sync_playwright

    page_errors = []
    console_errors = []
    requests = []

    result = {
        "runIndex": run_index,
        "blocked": None,
        "states": {},
        "context": None,
        "diag": None,
        "headSprite": None,
        "faceState": None,
        "texturesUnchanged": None,
        "otherRigTextures": None,
        "legacyBridgeVisible": None,
        "frozen": False,
        "screenshotMeta": None,
        "externalOriginRequestCount": 0,
        "externalRequests": [],
        "pageErrorCount": 0,
        "pageErrors": [],
        "consoleErrorCount": 0,
        "consoleErrors": [],
        "unhandledRejectionCount": 0,
        "unhandledRejections": [],
        "securityPolicyViolationCount": 0,
        "cspViolations": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            device_scale_factor=1,
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )
        context.add_init_script(FREEZE_INIT_SCRIPT)
        pg = context.new_page()
        pg.on("pageerror", lambda e: page_errors.append(str(e)))
        pg.on("console", lambda m: m.type == "error" and console_errors.append(m.text))
        pg.on("request", lambda r: requests.append(r.url))

        try:
            pg.goto("{}/ocean-rescue/index.html".format(base_url))
            pg.wait_for_selector(
                "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=20000
            )
            pg.click("#ocean-rescue-mission-list [data-mission-id=sea-turtle]")
            pg.wait_for_selector(
                "#ocean-rescue-gup-select:not([hidden])", timeout=10000
            )
            pg.click("#ocean-rescue-gup-list [data-gup-id=gup-x]")
            pg.click("#ocean-rescue-gup-launch")
            pg.wait_for_selector("#ocean-rescue-launch:not([hidden])", timeout=10000)
            pg.click("#ocean-rescue-launch-skip")
            pg.wait_for_selector(
                "#ocean-rescue-root[data-travel-scene=active]", timeout=15000
            )

            arrival = pg.evaluate(
                """() => {
              const Travel = OceanRescue.Travel;
              const Rescue = OceanRescue.Rescue;
              let iterations = 0;
              while (!Rescue.hasArrived(Travel.getSnapshot())) {
                Travel.step(50);
                iterations += 1;
                if (iterations > 5000) break;
              }
              const snap = Travel.getSnapshot();
              return {
                distance: snap.distance,
                active: snap.active,
                arrived: Rescue.hasArrived(snap),
                iterations: iterations
              };
            }"""
            )
            if not arrival or arrival.get("arrived") is not True:
                raise RuntimeError(
                    "travel did not reach arrival distance: {}".format(arrival)
                )

            pg.wait_for_selector(
                "#ocean-rescue-root[data-rescue-phase=active]", timeout=20000
            )
            pg.wait_for_function(
                "() => window.__oceanFrozen === true && "
                "(document.getElementById('ocean-rescue-root').getAttribute('data-sea-turtle-scene-animation') === 'paused')",
                timeout=15000,
            )
            pg.wait_for_function(
                "() => window.OceanRescue.RenderRuntime.isReady()",
                timeout=5000,
            )

            applied = pg.evaluate(APPLY_CANDIDATE_SCRIPT, candidate_data_uri)
            blocked_code, apply_error = head_apply_blocked(applied)
            if blocked_code:
                result["blocked"] = blocked_code
                result["applyError"] = apply_error
            else:
                context_png = None
                for state_spec in FACE_STATES:
                    name = state_spec["name"]
                    full_png, state_result = capture_face_state(pg, state_spec)
                    rgba, w, h = decode_png_to_rgba(full_png)
                    cropped = crop_rgba(full_png, w, h, FACE_CROP)
                    result["states"][name] = {
                        "fullPixelSha256": sha256_bytes(rgba),
                        "fullFileSha256": sha256_bytes(full_png),
                        "fullWidth": w,
                        "fullHeight": h,
                        "cropPng": cropped,
                        "cropPixelSha256": sha256_bytes(decode_png_to_rgba(cropped)[0]),
                        "cropFileSha256": sha256_bytes(cropped),
                        "cropWidth": FACE_CROP["width"],
                        "cropHeight": FACE_CROP["height"],
                        "stateResult": state_result,
                    }
                    if name == "neutral":
                        context_png = full_png

                collected = pg.evaluate(COLLECT_SCRIPT)

                if context_png is not None:
                    rgba, w, h = decode_png_to_rgba(context_png)
                    result["context"] = {
                        "png": context_png,
                        "pixelSha256": sha256_bytes(rgba),
                        "fileSha256": sha256_bytes(context_png),
                        "width": w,
                        "height": h,
                    }

                result["diag"] = collected["diag"]
                result["headSprite"] = collected["headSprite"]
                result["faceState"] = collected["faceState"]
                result["texturesUnchanged"] = collected["texturesUnchanged"]
                result["otherRigTextures"] = collected["otherRigTextures"]
                result["legacyBridgeVisible"] = collected["legacyBridgeVisible"]
                result["frozen"] = collected["frozen"]
                result["screenshotMeta"] = {
                    "width": LOGICAL_VIEWPORT[0],
                    "height": LOGICAL_VIEWPORT[1],
                }
                result["unhandledRejectionCount"] = len(
                    collected.get("unhandled") or []
                )
                result["unhandledRejections"] = collected.get("unhandled") or []
                result["securityPolicyViolationCount"] = len(collected.get("csp") or [])
                result["cspViolations"] = collected.get("csp") or []
        finally:
            base = "{}/".format(base_url)
            result["externalRequests"] = sorted(
                u for u in set(requests) if not u.startswith(base)
            )
            result["externalOriginRequestCount"] = len(result["externalRequests"])
            result["pageErrorCount"] = len(page_errors)
            result["pageErrors"] = page_errors
            result["consoleErrorCount"] = len(console_errors)
            result["consoleErrors"] = console_errors
            context.close()
            browser.close()

    return result


def crop_rgba(png_bytes: bytes, width: int, height: int, crop: dict) -> bytes:
    """Crop a PNG to the given box using PIL. No-op if the box is out of range."""
    from PIL import Image

    x0 = crop["x"]
    y0 = crop["y"]
    cw = crop["width"]
    ch = crop["height"]
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    if x0 < 0 or y0 < 0 or x0 + cw > width or y0 + ch > height:
        raise ValueError(
            "Crop box {} out of bounds for {}x{}".format(crop, width, height)
        )
    out = img.crop((x0, y0, x0 + cw, y0 + ch))
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


def head_apply_blocked(applied: dict):
    """Map the candidate-apply evaluate result to a BLOCKED code.

    Returns (blocked_code_or_None, error_detail).
    """
    if not applied or applied.get("ok") is not True:
        return "HEAD_SPRITE_NOT_FOUND", (applied or {}).get("error")
    return None, None


# ---------------------------------------------------------------------------
# Result validation
# ---------------------------------------------------------------------------


def is_finite_num(value):
    return (
        isinstance(value, (int, float))
        and value == value
        and abs(value) != float("inf")
    )


def check_capture_state(result: dict) -> tuple[bool, list[str]]:
    reasons = []
    diag = result["diag"] or {}
    if diag.get("data-ocean-rescue-ready") != "true":
        reasons.append("data-ocean-rescue-ready != true")
    if diag.get("data-render-runtime") != "ready":
        reasons.append("data-render-runtime != ready")
    if diag.get("data-rescue-phase") != "active":
        reasons.append("data-rescue-phase != active")
    if diag.get("data-sea-turtle-scene") not in ("active", "paused"):
        reasons.append("data-sea-turtle-scene not active/paused")
    if diag.get("data-sea-turtle-scene-animation") != "paused":
        reasons.append("data-sea-turtle-scene-animation != paused")
    if diag.get("data-sea-turtle-scene-legacy-visible") != "false":
        reasons.append("sea-turtle legacy bridge visible != false")
    if not result.get("frozen"):
        reasons.append("deterministic freeze marker not set")
    if result.get("legacyBridgeVisible") is not False:
        reasons.append("render runtime legacy bridge visible != false")
    if result["externalOriginRequestCount"] != 0:
        reasons.append(
            "external-origin requests != 0: {}".format(result["externalRequests"])
        )
    if result["pageErrorCount"] != 0:
        reasons.append("page errors != 0: {}".format(result["pageErrors"]))
    if result["consoleErrorCount"] != 0:
        reasons.append("console errors != 0: {}".format(result["consoleErrors"]))
    if result["unhandledRejectionCount"] != 0:
        reasons.append("unhandled rejections != 0")
    if result["securityPolicyViolationCount"] != 0:
        reasons.append("CSP violations != 0: {}".format(result["cspViolations"]))
    if len(result.get("states") or {}) != len(FACE_STATES):
        reasons.append("captured face states missing")
    if not result.get("context"):
        reasons.append("full context screenshot missing")
    for name in ("base-only", "neutral", "concern", "smile"):
        state = (result.get("states") or {}).get(name)
        if not state:
            reasons.append("face state missing: {}".format(name))
            continue
        if (
            state["fullWidth"] != LOGICAL_VIEWPORT[0]
            or state["fullHeight"] != LOGICAL_VIEWPORT[1]
        ):
            reasons.append("state {} screenshot != 1280x720".format(name))
        if (
            state["cropWidth"] != FACE_CROP["width"]
            or state["cropHeight"] != FACE_CROP["height"]
        ):
            reasons.append("state {} crop != declared crop".format(name))
    return (not reasons, reasons)


def validate_face_state(name: str, state_result: dict) -> tuple[bool, list[str]]:
    expected = {s["name"]: s for s in FACE_STATES}[name]
    reasons = []
    rotation = state_result.get("headRotation")
    if abs(float(rotation) - expected["rotation"]) > 1e-6:
        reasons.append(
            "{} head rotation {} != {}".format(name, rotation, expected["rotation"])
        )
    eyes_open = state_result.get("eyesOpenVisible") is True
    eyes_closed = state_result.get("eyesClosedVisible") is True
    mouth_neutral = state_result.get("mouthNeutralVisible") is True
    mouth_concern = state_result.get("mouthConcernVisible") is True
    mouth_smile = state_result.get("mouthSmileVisible") is True
    if expected["eyes"] == "open" and not eyes_open:
        reasons.append("{} eyes-open not visible".format(name))
    if expected["eyes"] == "closed" and not eyes_closed:
        reasons.append("{} eyes-closed not visible".format(name))
    if expected["eyes"] == "none":
        if eyes_open:
            reasons.append("{} eyes-open unexpectedly visible".format(name))
        if eyes_closed:
            reasons.append("{} eyes-closed unexpectedly visible".format(name))
    if expected["mouth"] == "neutral" and not mouth_neutral:
        reasons.append("{} mouth-neutral not visible".format(name))
    if expected["mouth"] == "concern" and not mouth_concern:
        reasons.append("{} mouth-concern not visible".format(name))
    if expected["mouth"] == "smile" and not mouth_smile:
        reasons.append("{} mouth-smile not visible".format(name))
    if expected["mouth"] == "none":
        if mouth_neutral or mouth_concern or mouth_smile:
            reasons.append("{} unexpected mouth visible".format(name))
    # Non-active overlays must be hidden.
    if expected["eyes"] != "open" and eyes_open and expected["eyes"] is not None:
        pass
    if expected["mouth"] == "neutral" and (mouth_concern or mouth_smile):
        reasons.append("{} other mouths visible".format(name))
    if expected["mouth"] == "concern" and (mouth_neutral or mouth_smile):
        reasons.append("{} other mouths visible".format(name))
    if expected["mouth"] == "smile" and (mouth_neutral or mouth_concern):
        reasons.append("{} other mouths visible".format(name))
    if expected["eyes"] == "open" and eyes_closed:
        reasons.append("{} eyes-closed also visible".format(name))
    if expected["eyes"] == "closed" and eyes_open:
        reasons.append("{} eyes-open also visible".format(name))
    return (not reasons, reasons)


def check_head_sprite(result: dict) -> tuple[bool, list[str]]:
    reasons = []
    head = result.get("headSprite")
    if not head:
        reasons.append("sea-otter-head sprite missing")
        return (False, reasons)
    if head.get("label") != HEAD_SPRITE_LABEL:
        reasons.append("head label != sea-otter-head")
    if head.get("isSprite") is not True:
        reasons.append("head is not a PIXI.Sprite")
    if not head.get("visible"):
        reasons.append("head sprite not visible")
    if head.get("renderable") is False:
        reasons.append("head sprite not renderable")
    if not is_finite_num(head.get("x")) or not is_finite_num(head.get("y")):
        reasons.append("head position not finite")
    if head.get("textureLabel") != CANDIDATE_TEXTURE_LABEL:
        reasons.append("candidate texture not applied to head sprite")
    tex_orig = head.get("textureOrig") or {}
    if (
        tex_orig.get("w") != CANDIDATE_TEXTURE_SIZE[0]
        or tex_orig.get("h") != CANDIDATE_TEXTURE_SIZE[1]
    ):
        reasons.append(
            "candidate texture orig {}x{} != {}x{}".format(
                tex_orig.get("w"),
                tex_orig.get("h"),
                CANDIDATE_TEXTURE_SIZE[0],
                CANDIDATE_TEXTURE_SIZE[1],
            )
        )
    anchor = head.get("anchor")
    if (
        anchor is None
        or abs(anchor.get("x", 0) - PIVOT[0]) > 1e-6
        or abs(anchor.get("y", 0) - PIVOT[1]) > 1e-6
    ):
        reasons.append("head anchor != [0.5, 0.55]")
    if (
        abs(head.get("scaleX", 0) - RUNTIME_SCALE[0]) > 1e-6
        or abs(head.get("scaleY", 0) - RUNTIME_SCALE[1]) > 1e-6
    ):
        reasons.append("head scale != [0.62, 0.62]")
    if abs(head.get("x", 0) - 0) > 1e-6 or abs(head.get("y", 0) + 42) > 1e-6:
        reasons.append("head rig offset != (0, -42)")
    bounds = head.get("bounds") or {}
    if bounds.get("width") is not None and bounds.get("height") is not None:
        if bounds["width"] > 1 or bounds["height"] > 1:
            if not (110 <= bounds["width"] <= 140 and 110 <= bounds["height"] <= 140):
                reasons.append(
                    "head display bounds {}x{} outside ~124x124 envelope".format(
                        round(bounds["width"], 1), round(bounds["height"], 1)
                    )
                )
    return (not reasons, reasons)


def check_other_textures(result: dict) -> tuple[bool, list[str]]:
    reasons = []
    if result.get("texturesUnchanged") is not True:
        reasons.append("other rig textures changed after candidate application")
    after = result.get("otherRigTextures") or {}
    expected = {
        "sea-otter-eyes-open": "otter.eyes.open",
        "sea-otter-eyes-closed": "otter.eyes.closed",
        "sea-otter-mouth-neutral": "otter.mouth.neutral",
        "sea-otter-mouth-concern": "otter.mouth.concern",
        "sea-otter-mouth-smile": "otter.mouth.smile",
    }
    for label, alias in expected.items():
        if after.get(label) != alias:
            reasons.append(
                "overlay texture changed: {} expected {} got {}".format(
                    label, alias, after.get(label)
                )
            )
    return (not reasons, reasons)


def compare_runs(run1: dict, run2: dict) -> tuple[bool, list[str]]:
    reasons = []
    keys = [
        ("diag/data-render-backend", "renderer backend"),
        ("diag/data-sea-turtle-scene", "sea-turtle-scene"),
        ("diag/data-sea-turtle-scene-animation", "sea-turtle-scene-animation"),
        ("diag/data-sea-turtle-scene-legacy-visible", "sea-turtle legacy visible"),
        ("diag/data-rescue-phase", "rescue phase"),
    ]
    for path, label in keys:
        v1 = run1
        v2 = run2
        for part in path.split("/"):
            v1 = (v1 or {}).get(part) if isinstance(v1, dict) else None
            v2 = (v2 or {}).get(part) if isinstance(v2, dict) else None
        if v1 != v2:
            reasons.append("{} differs: {} vs {}".format(label, v1, v2))
    for field in ("label", "isSprite", "visible", "rotation"):
        if (run1.get("headSprite") or {}).get(field) != (
            run2.get("headSprite") or {}
        ).get(field):
            reasons.append("headSprite.{} differs".format(field))
    for field in ("anchor",):
        if (run1.get("headSprite") or {}).get(field) != (
            run2.get("headSprite") or {}
        ).get(field):
            reasons.append("headSprite anchor differs")
    if (run1.get("headSprite") or {}).get("scaleX") != (
        run2.get("headSprite") or {}
    ).get("scaleX"):
        reasons.append("headSprite scale differs")
    if (run1.get("headSprite") or {}).get("scaleY") != (
        run2.get("headSprite") or {}
    ).get("scaleY"):
        reasons.append("headSprite scale differs")
    if (run1.get("headSprite") or {}).get("textureLabel") != (
        run2.get("headSprite") or {}
    ).get("textureLabel"):
        reasons.append("headSprite texture differs")
    if (run1.get("headSprite") or {}).get("textureOrig") != (
        run2.get("headSprite") or {}
    ).get("textureOrig"):
        reasons.append("headSprite texture orig differs")
    if run1.get("texturesUnchanged") != run2.get("texturesUnchanged"):
        reasons.append("texturesUnchanged differs")
    if run1.get("frozen") != run2.get("frozen"):
        reasons.append("frozen marker differs")
    if run1.get("otherRigTextures") != run2.get("otherRigTextures"):
        reasons.append("other rig textures differ")
    if run1.get("legacyBridgeVisible") != run2.get("legacyBridgeVisible"):
        reasons.append("legacy bridge differs")
    for name in ("base-only", "neutral", "concern", "smile"):
        s1 = (run1.get("states") or {}).get(name) or {}
        s2 = (run2.get("states") or {}).get(name) or {}
        if s1.get("cropPixelSha256") != s2.get("cropPixelSha256"):
            reasons.append("state {} crop pixel differs".format(name))
        if s1.get("stateResult") != s2.get("stateResult"):
            reasons.append("state {} face state differs".format(name))
    c1 = run1.get("context") or {}
    c2 = run2.get("context") or {}
    if c1.get("pixelSha256") != c2.get("pixelSha256"):
        reasons.append("full context pixel differs")
    for counter in (
        "externalOriginRequestCount",
        "pageErrorCount",
        "consoleErrorCount",
        "unhandledRejectionCount",
        "securityPolicyViolationCount",
    ):
        if run1.get(counter) != run2.get(counter):
            reasons.append("{} differs".format(counter))
    return (not reasons, reasons)


# ---------------------------------------------------------------------------
# Contact sheet
# ---------------------------------------------------------------------------


def build_contact_sheet(state_images, crop: dict) -> bytes:
    """Build a horizontal contact sheet of the four face crops with labels."""
    from PIL import Image, ImageDraw

    cell_w = crop["width"]
    cell_h = crop["height"]
    label_h = 30
    gap = 12
    margin = 8
    sheet_w = margin * 2 + len(state_images) * cell_w + (len(state_images) - 1) * gap
    sheet_h = margin * 2 + cell_h + label_h + gap

    sheet = Image.new("RGBA", (sheet_w, sheet_h), (18, 30, 48, 255))
    draw = ImageDraw.Draw(sheet)
    try:
        font = None
        for candidate in (
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
        ):
            if pathlib.Path(candidate).is_file():
                font = ImageFont_load(candidate)
                break
    except Exception:
        font = None

    x = margin
    for name, png_bytes in state_images:
        img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        sheet.paste(img, (x, margin))
        label = "BASE ONLY" if name == "base-only" else name.upper()
        tw = draw.textlength(label, font=font) if font else len(label) * 6
        draw.text(
            (x + (cell_w - tw) / 2, margin + cell_h + gap),
            label,
            fill=(240, 240, 240, 255),
            font=font,
        )
        x += cell_w + gap

    buf = io.BytesIO()
    sheet.save(buf, format="PNG")
    return buf.getvalue()


def ImageFont_load(path):
    from PIL import ImageFont

    return ImageFont.truetype(path, 16)


# ---------------------------------------------------------------------------
# Manifest / report
# ---------------------------------------------------------------------------


def proof_image_entry(name, path, analysis=None):
    entry = {
        "path": name,
        "fileSha256": sha256_file(path),
    }
    if analysis is not None:
        entry["width"] = analysis["width"]
        entry["height"] = analysis["height"]
        entry["pixelSha256"] = analysis["pixelSha256"]
    else:
        from PIL import Image

        img = Image.open(path)
        entry["width"] = img.width
        entry["height"] = img.height
    return entry


def build_manifest(
    args, repo_root, output_dir, isolated, runs, verdict, rejection_reasons
) -> dict:
    run_entries = []
    for r in runs:
        states = {}
        for name, s in (r.get("states") or {}).items():
            states[name] = {
                "cropFileSha256": s["cropFileSha256"],
                "cropPixelSha256": s["cropPixelSha256"],
                "cropWidth": s["cropWidth"],
                "cropHeight": s["cropHeight"],
                "stateResult": s["stateResult"],
            }
        run_entries.append(
            {
                "runIndex": r["runIndex"],
                "rendererBackend": (r.get("diag") or {}).get("data-render-backend"),
                "headSprite": r.get("headSprite"),
                "faceState": r.get("faceState"),
                "texturesUnchanged": r.get("texturesUnchanged"),
                "frozen": r.get("frozen"),
                "legacyBridgeVisible": r.get("legacyBridgeVisible"),
                "states": states,
                "contextPixelSha256": (r.get("context") or {}).get("pixelSha256"),
                "externalOriginRequestCount": r.get("externalOriginRequestCount"),
                "pageErrorCount": r.get("pageErrorCount"),
                "consoleErrorCount": r.get("consoleErrorCount"),
                "unhandledRejectionCount": r.get("unhandledRejectionCount"),
                "securityPolicyViolationCount": r.get("securityPolicyViolationCount"),
            }
        )

    def isolated_entry(analysis, name):
        return {
            "path": name,
            "fileSha256": analysis["fileSha256"],
            "pixelSha256": analysis["pixelSha256"],
            "byteSize": analysis["byteSize"],
            "width": analysis["width"],
            "height": analysis["height"],
            "alphaPresent": analysis["alphaPresent"],
            "visibleAlphaBounds": analysis["visibleAlphaBounds"],
        }

    structure_report = resolve_path(repo_root, args.structure_report)
    svg_path = resolve_path(repo_root, args.svg)
    structure_report_sha = sha256_file(structure_report)
    candidate_svg_sha = sha256_file(svg_path)

    two_run_deterministic = False
    if len(runs) == 2:
        two_run_deterministic, _ = compare_runs(runs[0], runs[1])

    return {
        "schemaVersion": 1,
        "taskId": TASK_ID,
        "assetId": ASSET_ID,
        "alias": ALIAS,
        "candidateSvgSha256": candidate_svg_sha,
        "candidateSvgPath": args.svg,
        "structureReportSha256": structure_report_sha,
        "structureReportSvgSha256": (load_json(structure_report)).get("svgSha256"),
        "structureVerdict": "STRUCTURE_PASS",
        "viewBox": VIEWBOX,
        "sourceLogicalSize": SOURCE_LOGICAL_SIZE,
        "pivot": PIVOT,
        "runtimeScale": RUNTIME_SCALE,
        "rasterizer": RASTERIZER,
        "rasterizerVersion": RASTERIZER_VERSION,
        "rendererBackend": (runs[0].get("diag") or {}).get("data-render-backend")
        if runs
        else None,
        "viewport": LOGICAL_VIEWPORT,
        "deviceScaleFactor": DEVICE_SCALE_FACTOR,
        "headSpriteLabel": HEAD_SPRITE_LABEL,
        "headPosition": [0, -42],
        "headScale": RUNTIME_SCALE,
        "headAnchor": PIVOT,
        "eyeOverlayLabels": list(EYE_OVERLAY_LABELS),
        "mouthOverlayLabels": list(MOUTH_OVERLAY_LABELS),
        "faceCrop": FACE_CROP,
        "isolated1x": isolated_entry(isolated["1x"], "isolated-1x.png"),
        "isolated2x": isolated_entry(isolated["2x"], "isolated-2x.png"),
        "proofImages": [
            proof_image_entry(
                "isolated-1x.png", output_dir / "isolated-1x.png", isolated["1x"]
            ),
            proof_image_entry(
                "isolated-2x.png", output_dir / "isolated-2x.png", isolated["2x"]
            ),
            proof_image_entry("rig-base-only.png", output_dir / "rig-base-only.png"),
            proof_image_entry("rig-neutral.png", output_dir / "rig-neutral.png"),
            proof_image_entry("rig-concern.png", output_dir / "rig-concern.png"),
            proof_image_entry("rig-smile.png", output_dir / "rig-smile.png"),
            proof_image_entry(
                "face-rig-contact-sheet.png", output_dir / "face-rig-contact-sheet.png"
            ),
            proof_image_entry(
                "sea-turtle-context.png", output_dir / "sea-turtle-context.png"
            ),
        ],
        "runs": run_entries,
        "candidateTextureApplied": bool(runs)
        and all(
            (r.get("headSprite") or {}).get("textureLabel") == CANDIDATE_TEXTURE_LABEL
            for r in runs
        ),
        "otherTexturesUnchanged": bool(runs)
        and all(r.get("texturesUnchanged") is True for r in runs),
        "externalRequestCount": runs[0].get("externalOriginRequestCount", 0)
        if runs
        else None,
        "pageErrorCount": runs[0].get("pageErrorCount", 0) if runs else None,
        "consoleErrorCount": runs[0].get("consoleErrorCount", 0) if runs else None,
        "cspViolationCount": runs[0].get("securityPolicyViolationCount", 0)
        if runs
        else None,
        "unhandledRejectionCount": runs[0].get("unhandledRejectionCount", 0)
        if runs
        else None,
        "twoRunDeterministic": two_run_deterministic,
        "verdict": verdict,
        "rejectionReasons": rejection_reasons,
    }


def build_report(args, isolated, runs, verdict, rejection_reasons) -> str:
    lines = []
    add = lines.append

    add("# Ocean Rescue — otter-head-01 Head/Face-Rig Render Proof")
    add("")
    add("- Task ID: `{}`".format(TASK_ID))
    add("- Verdict: `{}`".format(verdict))
    add("")
    add("## 1. Input lineage")
    add("")
    add("- Brief path: `{}`".format(args.brief))
    add("- Inbox SVG path: `{}`".format(args.svg))
    add("- Structure report path: `{}`".format(args.structure_report))
    add(
        "- Candidate SVG SHA-256: `{}`".format(
            sha256_file(resolve_path(pathlib.Path(args.repo_root), args.svg))
        )
    )
    add(
        "- Structure report SHA-256: `{}`".format(
            sha256_file(
                resolve_path(pathlib.Path(args.repo_root), args.structure_report)
            )
        )
    )
    add("- Structure report verdict: `STRUCTURE_PASS`")
    add(
        "- Structure report `svgSha256` equals candidate: `{}`".format(
            (
                load_json(
                    resolve_path(pathlib.Path(args.repo_root), args.structure_report)
                )
            ).get("svgSha256")
            == sha256_file(resolve_path(pathlib.Path(args.repo_root), args.svg))
        )
    )
    add("")
    add("## 2. Isolated proof findings")
    add("")
    for name, analysis in (("1x", isolated["1x"]), ("2x", isolated["2x"])):
        ok, reasons = check_isolated(analysis)
        add(
            "- Isolated {}: {}x{} pixel SHA `{}`".format(
                name,
                analysis["width"],
                analysis["height"],
                analysis["pixelSha256"][:16],
            )
        )
        add("  - Visible alpha bounds: {}".format(analysis["visibleAlphaBounds"]))
        add("  - Alpha channel present: {}".format(analysis["alphaPresent"]))
        add("  - Check verdict: {}".format("PASS" if ok else "FAIL"))
        if reasons:
            for reason in reasons:
                add("  - REJECT: {}".format(reason))
    add("")
    add("## 3. In-context proof findings")
    add("")
    for r in runs:
        state_ok, state_reasons = check_capture_state(r)
        head_ok, head_reasons = check_head_sprite(r)
        face_ok = True
        face_reasons = []
        for name in ("base-only", "neutral", "concern", "smile"):
            s = (r.get("states") or {}).get(name) or {}
            if not s:
                face_ok = False
                face_reasons.append("{} state missing".format(name))
                continue
            ok_, reasons = validate_face_state(name, s.get("stateResult") or {})
            if not ok_:
                face_ok = False
                face_reasons.extend(reasons)
        textures_ok, texture_reasons = check_other_textures(r)
        add(
            "- Run {}: backend={} head={} texture={}".format(
                r["runIndex"],
                (r.get("diag") or {}).get("data-render-backend"),
                (r.get("headSprite") or {}).get("label"),
                (r.get("headSprite") or {}).get("textureLabel"),
            )
        )
        add("  - Capture state: {}".format("PASS" if state_ok else "FAIL"))
        add("  - Head sprite identity: {}".format("PASS" if head_ok else "FAIL"))
        add("  - Face state visibility: {}".format("PASS" if face_ok else "FAIL"))
        add(
            "  - Other textures unchanged: {}".format("PASS" if textures_ok else "FAIL")
        )
        add("  - Frozen at deterministic t=0: {}".format(r.get("frozen")))
        if state_reasons:
            for reason in state_reasons:
                add("  - REJECT: {}".format(reason))
        if head_reasons:
            for reason in head_reasons:
                add("  - REJECT: {}".format(reason))
        if face_reasons:
            for reason in face_reasons:
                add("  - REJECT: {}".format(reason))
        if texture_reasons:
            for reason in texture_reasons:
                add("  - REJECT: {}".format(reason))
    add("")
    add("## 4. Head sprite rig contract")
    add("")
    if runs:
        head = runs[0].get("headSprite") or {}
        add("- Label: `{}`".format(head.get("label")))
        add("- Rig offset: ({}, {})".format(head.get("x"), head.get("y")))
        add("- Scale: {}x{}".format(head.get("scaleX"), head.get("scaleY")))
        add("- Anchor: {}".format(head.get("anchor")))
        add("- Candidate texture label: `{}`".format(head.get("textureLabel")))
        add(
            "- Candidate texture source: {}x{}".format(
                (head.get("textureOrig") or {}).get("w"),
                (head.get("textureOrig") or {}).get("h"),
            )
        )
        add("- Display bounds: {}".format(head.get("bounds")))
    add("")
    add("## 5. Face states captured")
    add("")
    for name in ("base-only", "neutral", "concern", "smile"):
        add("- `{}`: {}".format(name, "rig-{}.png".format(name)))
    add("- Contact sheet: `face-rig-contact-sheet.png`")
    add("- Full context: `sea-turtle-context.png`")
    add("")
    add("## 6. Determinism across two runs")
    add("")
    if len(runs) == 2:
        ok, reasons = compare_runs(runs[0], runs[1])
        add("- Two-run deterministic: {}".format("PASS" if ok else "FAIL"))
        if reasons:
            for reason in reasons:
                add("  - {}".format(reason))
    add("")
    add("## 7. Error/network findings")
    add("")
    for r in runs:
        add(
            "- Run {}: external={} pageErrors={} consoleErrors={} unhandled={} csp={}".format(
                r["runIndex"],
                r.get("externalOriginRequestCount"),
                r.get("pageErrorCount"),
                r.get("consoleErrorCount"),
                r.get("unhandledRejectionCount"),
                r.get("securityPolicyViolationCount"),
            )
        )
    add("")
    add("## 8. Proof limitations")
    add("")
    add(
        "- The candidate raster is applied only to the `sea-otter-head` sprite "
        "instance during the proof; the canonical atlas texture `otter.head` is "
        "never modified."
    )
    add(
        "- The scene is frozen via `OceanRescue.SeaTurtleScene.pause()` in a "
        "mutation-observer microtask the moment `data-rescue-phase=active` and "
        "`data-sea-turtle-scene=active` are both set, so the scene renders at "
        "deterministic animation time t=0."
    )
    add("- Eye and mouth overlays are the existing production atlas textures.")
    add("")
    add("## 9. Final verdict")
    add("")
    add("`{}`".format(verdict))
    if rejection_reasons:
        for reason in rejection_reasons:
            add("- {}".format(reason))
    add("")
    add("## 10. Human review checklist")
    add("")
    add("This checklist is intentionally left unchecked for a human reviewer.")
    add("")
    add("- [ ] 귀가 실제 게임 크기에서 잘 보인다.")
    add("- [ ] 머리가 수달처럼 읽힌다.")
    add("- [ ] 주둥이와 코가 명확하다.")
    add("- [ ] 눈 overlay가 머리 안의 자연스러운 위치에 있다.")
    add("- [ ] 입 overlay가 주둥이 위에 자연스럽게 놓인다.")
    add("- [ ] 눈이나 입이 두 겹으로 보이지 않는다.")
    add("- [ ] Neutral 표정이 자연스럽다.")
    add("- [ ] Concern 표정이 자연스럽다.")
    add("- [ ] Smile 표정이 자연스럽다.")
    add("- [ ] 기존 몸통·팔·꼬리와 디자인이 어울린다.")
    add("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Otter head handoff render proof harness."
    )
    parser.add_argument("--brief", required=True)
    parser.add_argument("--svg", required=True, help="Inbox SVG candidate")
    parser.add_argument("--structure-report", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default=None)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.repo_root:
        repo_root = pathlib.Path(args.repo_root).resolve()
    else:
        repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
    args.repo_root = str(repo_root)
    output_dir = resolve_path(repo_root, args.output_dir)

    # ---- Input gate ----
    ok, code = run_input_gate(repo_root, args)
    if not ok:
        print("BLOCKED: {}".format(code), file=sys.stderr)
        return 2

    # ---- Byte guard for production files ----
    before = {p: sha256_file(repo_root / p) for p in PRODUCTION_FILES}

    svg_path = resolve_path(repo_root, args.svg)
    candidate_sha_before = sha256_file(svg_path)

    # ---- Isolated render ----
    output_dir.mkdir(parents=True, exist_ok=True)
    isolated = {}
    for name, w, h in (("1x", 200, 200), ("2x", 400, 400)):
        png_bytes = render_svg_to_png(svg_path, w, h)
        analysis = analyze_isolated_png(png_bytes, w, h)
        isolated[name] = analysis
        dst = output_dir / ("isolated-1x.png" if name == "1x" else "isolated-2x.png")
        dst.write_bytes(png_bytes)

    isolated_ok = all(check_isolated(a)[0] for a in isolated.values())
    isolated_reasons = []
    for name, a in isolated.items():
        ok_, reasons = check_isolated(a)
        if not ok_:
            isolated_reasons.extend("{}: {}".format(name, r) for r in reasons)

    # ---- In-context capture (two runs) ----
    candidate_png = (output_dir / "isolated-1x.png").read_bytes()
    candidate_data_uri = "data:image/png;base64," + base64.b64encode(
        candidate_png
    ).decode("ascii")

    port = find_free_port()
    server = start_server(repo_root, port)
    base_url = "http://127.0.0.1:{}".format(port)
    runs = []
    try:
        for run_index in (1, 2):
            r = run_in_context_capture(
                repo_root, base_url, candidate_data_uri, run_index
            )
            if r.get("blocked"):
                print("BLOCKED: {}".format(r["blocked"]), file=sys.stderr)
                if r.get("applyError"):
                    print("  {}".format(r["applyError"]), file=sys.stderr)
                return 2
            runs.append(r)
    finally:
        server.shutdown()
        server.server_close()

    capture_ok = all(check_capture_state(r)[0] for r in runs)
    head_ok = all(check_head_sprite(r)[0] for r in runs)
    face_ok = True
    for r in runs:
        for name in ("base-only", "neutral", "concern", "smile"):
            s = (r.get("states") or {}).get(name) or {}
            ok_, _ = validate_face_state(name, s.get("stateResult") or {})
            if not ok_:
                face_ok = False
    textures_ok = all(check_other_textures(r)[0] for r in runs)
    determinism_ok, determinism_reasons = (
        compare_runs(runs[0], runs[1]) if len(runs) == 2 else (False, ["missing runs"])
    )

    rejection_reasons = []
    if not isolated_ok:
        rejection_reasons.extend(isolated_reasons)
    if not capture_ok:
        for r in runs:
            _, reasons = check_capture_state(r)
            rejection_reasons.extend(
                "run{}: {}".format(r["runIndex"], x) for x in reasons
            )
    if not head_ok:
        for r in runs:
            _, reasons = check_head_sprite(r)
            rejection_reasons.extend(
                "run{}: {}".format(r["runIndex"], x) for x in reasons
            )
    if not face_ok:
        for r in runs:
            for name in ("base-only", "neutral", "concern", "smile"):
                s = (r.get("states") or {}).get(name) or {}
                _, reasons = validate_face_state(name, s.get("stateResult") or {})
                if reasons:
                    rejection_reasons.extend(
                        "run{} {}: {}".format(r["runIndex"], name, x) for x in reasons
                    )
    if not textures_ok:
        for r in runs:
            _, reasons = check_other_textures(r)
            rejection_reasons.extend(
                "run{}: {}".format(r["runIndex"], x) for x in reasons
            )
    if not determinism_ok:
        rejection_reasons.extend(
            "determinism: {}".format(x) for x in determinism_reasons
        )

    if rejection_reasons:
        verdict = "RENDER_REJECTED"
    else:
        verdict = "RENDER_PROOF_READY"

    # ---- Persist screenshots + manifest + report ----
    for r in runs:
        for name, s in (r.get("states") or {}).items():
            dst = output_dir / "rig-{}.png".format(name)
            dst.write_bytes(s["cropPng"])
        ctx = r.get("context")
        if ctx:
            dst = output_dir / "sea-turtle-context.png"
            dst.write_bytes(ctx["png"])

    first_run = runs[0]
    state_images = []
    for name in ("base-only", "neutral", "concern", "smile"):
        s = (first_run.get("states") or {}).get(name) or {}
        if s:
            state_images.append((name, s["cropPng"]))
    if state_images:
        contact = build_contact_sheet(state_images, FACE_CROP)
        (output_dir / "face-rig-contact-sheet.png").write_bytes(contact)

    manifest = build_manifest(
        args, repo_root, output_dir, isolated, runs, verdict, rejection_reasons
    )
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    report = build_report(args, isolated, runs, verdict, rejection_reasons)
    (output_dir / "render-proof-report.md").write_text(report, encoding="utf-8")

    # ---- Byte guard ----
    after = {p: sha256_file(repo_root / p) for p in PRODUCTION_FILES}
    if before != after:
        print("BLOCKED: PRODUCTION_FILES_MUTATED_DURING_PROOF", file=sys.stderr)
        return 2
    if sha256_file(svg_path) != candidate_sha_before:
        print("BLOCKED: CANDIDATE_SVG_MUTATED_DURING_PROOF", file=sys.stderr)
        return 2

    print("RENDER_PROOF verdict: {}".format(verdict))
    for reason in rejection_reasons:
        print("REJECT: {}".format(reason), file=sys.stderr)
    return 0 if verdict == "RENDER_PROOF_READY" else 1


if __name__ == "__main__":
    sys.exit(main())
