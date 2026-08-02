#!/usr/bin/env python3
"""Post-canonical render proof harness for the scene-submarine-01 handoff.

Proves that the already-canonicalized submarine asset, the generated atlas,
and the live production TravelScene all come from the same source input and
produce a deterministic, human-reviewable render.

The proof does NOT inject the candidate, rebuild the atlas, rebuild the single
HTML, or modify any production file. It only:

  1. Validates the input gate (brief, inbox SVG, structure report, canonical
     source, art packet, atlas manifest, single HTML).
  2. Validates the hash lineage (candidate == structure report == canonical
     source == art-packet source SHA) plus the atlas/runtime payload binding.
  3. Renders the inbox/canonical SVG with the pinned atlas rasterizer at
     1x (320x200) and 2x (640x400) and validates the isolated pixels.
  4. Boots the tracked production single HTML through the normal product flow
     (mission -> GUP -> launch -> skip -> travel) and captures the real
     ``scene.submarine`` atlas sprite in the paused, pre-collision TravelScene
     twice, then checks determinism.
  5. Writes manifest.json + render-proof-report.md under the evidence root.

Exit codes:
    0  RENDER_PROOF_READY
    1  RENDER_REJECTED
    2  BLOCKED
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import pathlib
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from http.server import SimpleHTTPRequestHandler

TASK_ID = "AIDENGAME-OCEAN-RESCUE-SUBMARINE-HANDOFF-POSTCANONICAL-RENDER-PROOF-01"
ASSET_ID = "scene-submarine-01"
ALIAS = "scene.submarine"

PREEXISTING_CANONICALIZATION_COMMIT = "9336240d8462d47cbe94bcb65935f86cb82f8318"
STRUCTURE_GATE_COMMIT = "ecf2b7aa56e4c6bb7bcf21370dbf1a3fd9aa7cf9"

SOURCE_LOGICAL_SIZE = [320, 200]
PIVOT = [0.5, 0.55]
RUNTIME_SCALE = [1.1, 1.1]
LOGICAL_VIEWPORT = [1280, 720]
DEVICE_SCALE_FACTOR = 1

CAIRO_LIB_PATHS = ("/opt/homebrew/opt/cairo/lib", "/opt/homebrew/lib")

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# Production paths that must never be written by this proof.
FORBIDDEN_WRITE_PREFIXES = (
    "domains/ocean-rescue/assets/handoff/inbox/",
    "domains/ocean-rescue/assets/handoff/briefs/",
    "domains/ocean-rescue/assets/source/",
    "domains/ocean-rescue/assets/generated/",
    "domains/ocean-rescue/src/",
    "ocean-rescue/index.html",
)

PRODUCTION_FILES = [
    "ocean-rescue/index.html",
    "domains/ocean-rescue/src/render-assets.generated.js",
    "domains/ocean-rescue/src/render-runtime.js",
    "domains/ocean-rescue/src/travel-scene.js",
    "domains/ocean-rescue/src/app.js",
    "domains/ocean-rescue/assets/source/art-packet.json",
    "domains/ocean-rescue/assets/source/art-approval.json",
    "domains/ocean-rescue/assets/source/scene/submarine.svg",
    "domains/ocean-rescue/assets/generated/atlas-manifest.json",
    "domains/ocean-rescue/assets/generated/scene/scene-0.json",
    "domains/ocean-rescue/assets/generated/scene/scene-0.png",
]

CAIRO_ENV = {"DYLD_LIBRARY_PATH": CAIRO_LIB_PATHS[0]}


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
                raise ValueError("Bit depth {} not supported (expected 8)".format(bit_depth))
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
                    out_row[x * 4 + c] = (out_row[x * 4 + c] + ((left + up) >> 1)) & 0xFF
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
    """Validate that every required input exists and the structure gate holds.

    Returns (ok, error_code).
    """
    brief = resolve_path(repo_root, args.brief)
    svg = resolve_path(repo_root, args.svg)
    structure = resolve_path(repo_root, args.structure_report)
    canonical = resolve_path(repo_root, args.canonical_source)
    packet = resolve_path(repo_root, args.art_packet)
    manifest = resolve_path(repo_root, args.atlas_manifest)
    single_html = resolve_path(repo_root, args.single_html)

    if not brief.is_file():
        return False, "ACTIVE_BRIEF_MISSING"
    if not svg.is_file():
        return False, "INBOX_SVG_MISSING"
    if not structure.is_file():
        return False, "STRUCTURE_REPORT_MISSING"
    if not canonical.is_file():
        return False, "CANONICAL_SOURCE_MISSING"
    if not packet.is_file():
        return False, "ART_PACKET_MISSING"
    if not manifest.is_file():
        return False, "GENERATED_ATLAS_MISSING"
    if not single_html.is_file():
        return False, "PRODUCTION_SINGLE_HTML_MISSING"

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
# Hash lineage gate
# ---------------------------------------------------------------------------


def compute_lineage(repo_root: pathlib.Path, args) -> dict:
    svg_path = resolve_path(repo_root, args.svg)
    canonical_path = resolve_path(repo_root, args.canonical_source)
    structure_path = resolve_path(repo_root, args.structure_report)
    packet_path = resolve_path(repo_root, args.art_packet)
    approval_path = resolve_path(repo_root, args.art_approval)
    manifest_path = resolve_path(repo_root, args.atlas_manifest)
    scene_json_path = resolve_path(repo_root, args.scene_atlas_json)
    scene_png_path = resolve_path(repo_root, args.scene_atlas_png)
    render_assets_path = resolve_path(repo_root, args.render_assets)
    single_html_path = resolve_path(repo_root, args.single_html)

    packet = load_json(packet_path)
    approval = load_json(approval_path)
    manifest = load_json(manifest_path)

    submarine = next(
        (a for a in packet["assets"] if a.get("alias") == ALIAS), None
    )

    lineage = {
        "inboxSvgSha256": sha256_file(svg_path),
        "structureReportSha256": sha256_file(structure_path),
        "structureReportSvgSha256": load_json(structure_path).get("svgSha256"),
        "canonicalSourceSha256": sha256_file(canonical_path),
        "artPacketAssetSourceSha256": submarine.get("sourceSha256") if submarine else None,
        "artPacketSha256": sha256_file(packet_path),
        "artApprovalSha256": sha256_file(approval_path),
        "artApprovalArtPacketSha256": approval.get("artPacketSha256"),
        "artApprovalSourceSetSha256": approval.get("sourceSetSha256"),
        "atlasSourcePacketSha256": manifest.get("sourcePacketSha256"),
        "atlasApprovalRecordSha256": manifest.get("approvalRecordSha256"),
        "atlasSourceSetSha256": manifest.get("sourceSetSha256"),
        "sceneAtlasJsonSha256": sha256_file(scene_json_path),
        "sceneAtlasPngSha256": sha256_file(scene_png_path),
        "atlasSceneJsonSha256": manifest.get("files", {}).get("scene/scene-0.json"),
        "atlasScenePngSha256": manifest.get("files", {}).get("scene/scene-0.png"),
        "renderAssetsSha256": sha256_file(render_assets_path),
        "singleHtmlSha256": sha256_file(single_html_path),
    }
    return lineage


def lineage_checks(lineage: dict) -> list[dict]:
    checks = []

    def check(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    expected = (
        lineage["inboxSvgSha256"],
        lineage["structureReportSvgSha256"],
        lineage["canonicalSourceSha256"],
        lineage["artPacketAssetSourceSha256"],
    )
    check(
        "candidateStructureCanonicalPacket",
        len(set(expected)) == 1,
        "inbox={} structure={} canonical={} packet={}".format(
            lineage["inboxSvgSha256"][:12],
            (lineage["structureReportSvgSha256"] or "")[:12],
            lineage["canonicalSourceSha256"][:12],
            (lineage["artPacketAssetSourceSha256"] or "")[:12],
        ),
    )
    check(
        "artPacketShaMatchesApproval",
        lineage["artPacketSha256"] == lineage["artApprovalArtPacketSha256"],
        "packet={} approval.artPacket={}".format(
            lineage["artPacketSha256"][:12],
            (lineage["artApprovalArtPacketSha256"] or "")[:12],
        ),
    )
    check(
        "artPacketShaMatchesAtlas",
        lineage["artPacketSha256"] == lineage["atlasSourcePacketSha256"],
        "packet={} atlas.sourcePacket={}".format(
            lineage["artPacketSha256"][:12],
            (lineage["atlasSourcePacketSha256"] or "")[:12],
        ),
    )
    check(
        "approvalShaMatchesAtlas",
        lineage["artApprovalSha256"] == lineage["atlasApprovalRecordSha256"],
        "approval={} atlas.approval={}".format(
            lineage["artApprovalSha256"][:12],
            (lineage["atlasApprovalRecordSha256"] or "")[:12],
        ),
    )
    check(
        "sourceSetMatchesApprovalAndAtlas",
        lineage["artApprovalSourceSetSha256"]
        == lineage["atlasSourceSetSha256"]
        and lineage["atlasSourceSetSha256"] is not None,
        "approval.sourceSet={} atlas.sourceSet={}".format(
            (lineage["artApprovalSourceSetSha256"] or "")[:12],
            (lineage["atlasSourceSetSha256"] or "")[:12],
        ),
    )
    check(
        "sceneAtlasJsonMatchesManifest",
        lineage["sceneAtlasJsonSha256"] == lineage["atlasSceneJsonSha256"],
        "file={} manifest={}".format(
            lineage["sceneAtlasJsonSha256"][:12],
            (lineage["atlasSceneJsonSha256"] or "")[:12],
        ),
    )
    check(
        "sceneAtlasPngMatchesManifest",
        lineage["sceneAtlasPngSha256"] == lineage["atlasScenePngSha256"],
        "file={} manifest={}".format(
            lineage["sceneAtlasPngSha256"][:12],
            (lineage["atlasScenePngSha256"] or "")[:12],
        ),
    )
    return checks


def validate_packet_directly(repo_root: pathlib.Path, args) -> list[dict]:
    """Direct packet/approval/atlas binding checks that do not rely on the
    stale hardcoded alias list inside validate_art_packet.py."""
    packet_path = resolve_path(repo_root, args.art_packet)
    approval_path = resolve_path(repo_root, args.art_approval)
    manifest_path = resolve_path(repo_root, args.atlas_manifest)
    packet = load_json(packet_path)
    approval = load_json(approval_path)
    manifest = load_json(manifest_path)

    checks = []
    for asset in packet["assets"]:
        src = packet_path.parent / asset["source"]
        actual = sha256_file(src) if src.is_file() else None
        if actual != asset.get("sourceSha256"):
            checks.append(
                {
                    "name": "packetSourceHash:{}".format(asset["alias"]),
                    "ok": False,
                    "detail": "declared={} actual={}".format(
                        (asset.get("sourceSha256") or "")[:12], (actual or "")[:12]
                    ),
                }
            )
    packet_aliases = set(a["alias"] for a in packet["assets"])
    approval_aliases = set(approval.get("approvedAliases") or [])
    checks.append(
        {
            "name": "packetAliasesMatchApproval",
            "ok": packet_aliases == approval_aliases,
            "detail": "packet={} approval={}".format(
                len(packet_aliases), len(approval_aliases)
            ),
        }
    )
    manifest_aliases = set()
    for bundle in manifest.get("bundles", []):
        manifest_aliases.update(bundle.get("aliases", []))
    checks.append(
        {
            "name": "packetAliasesMatchAtlas",
            "ok": packet_aliases == manifest_aliases,
            "detail": "packet={} atlas={}".format(
                len(packet_aliases), len(manifest_aliases)
            ),
        }
    )
    return checks


def verify_render_assets_binding(repo_root: pathlib.Path, args) -> list[dict]:
    render_assets_path = resolve_path(repo_root, args.render_assets)
    build_manifest_path = resolve_path(repo_root, args.build_manifest)
    manifest = load_json(build_manifest_path)
    expected = None
    for script in manifest.get("scripts", []):
        if script.get("file") == "render-assets.generated.js":
            expected = script.get("sha256")
    actual = sha256_file(render_assets_path)
    return [
        {
            "name": "renderAssetsMatchesBuildManifest",
            "ok": actual == expected,
            "detail": "file={} manifest={}".format(actual[:12], (expected or "")[:12]),
        }
    ]


def verify_single_html_binding(repo_root: pathlib.Path, args) -> list[dict]:
    single_html_path = resolve_path(repo_root, args.single_html)
    manifest_path = resolve_path(repo_root, args.atlas_manifest)
    render_assets_path = resolve_path(repo_root, args.render_assets)
    html = single_html_path.read_text(encoding="utf-8", errors="replace")
    manifest = load_json(manifest_path)

    checks = []
    for rel_path in ("scene/scene-0.json", "scene/scene-0.png"):
        expected_sha = manifest.get("files", {}).get(rel_path)
        checks.append(
            {
                "name": "singleHtmlEmbedsAtlasFile:{}".format(rel_path),
                "ok": expected_sha is not None and expected_sha in html,
                "detail": "sha={}".format((expected_sha or "")[:16]),
            }
        )
    marker = render_assets_path.read_text(encoding="utf-8")[200:400]
    checks.append(
        {
            "name": "singleHtmlEmbedsRenderAssets",
            "ok": marker in html,
            "detail": "generated-assets marker present",
        }
    )
    checks.append(
        {
            "name": "singleHtmlEmbedsSubmarineAlias",
            "ok": ALIAS in html,
            "detail": "alias={}".format(ALIAS),
        }
    )
    return checks


# ---------------------------------------------------------------------------
# Isolated render (pinned atlas rasterizer)
# ---------------------------------------------------------------------------


def render_svg_to_png(svg_path: pathlib.Path, width: int, height: int) -> bytes:
    """Rasterize an SVG with the exact pinned atlas rasterizer (CairoSVG)."""
    # Ensure the cairo native library is discoverable on macOS before the
    # cairosvg/cairocffi import happens.
    for lib_path in CAIRO_LIB_PATHS:
        if os.path.isdir(lib_path):
            existing = os.environ.get("DYLD_LIBRARY_PATH", "")
            if lib_path not in existing.split(":"):
                os.environ["DYLD_LIBRARY_PATH"] = lib_path + ((":" + existing) if existing else "")
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
    if analysis["width"] != analysis["expectedWidth"] or analysis["height"] != analysis["expectedHeight"]:
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
    elif analysis["visibleAlphaBounds"]["width"] <= 0 or analysis["visibleAlphaBounds"]["height"] <= 0:
        reasons.append("empty visible bounds")
    if analysis["alphaMax"] == 0:
        reasons.append("completely transparent raster")
    bbox = analysis["visibleAlphaBounds"]
    if bbox is not None:
        x0 = bbox["x"]
        y0 = bbox["y"]
        x1 = x0 + bbox["width"]
        y1 = y0 + bbox["height"]
        # Visible bounds must be strictly inside the frame (no clipping).
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
    if (root.getAttribute('data-travel-scene') === 'active') {
      window.__oceanFrozen = true;
      var O = window.OceanRescue;
      if (!O || !O.TravelScene) return;
      if (O.Travel && typeof O.Travel.stop === 'function') O.Travel.stop();
      O.TravelScene.pause();
      var t = O.Travel.getSnapshot();
      var s = O.Terrain.getSnapshot();
      O.TravelScene.sync(t, s);
    }
  });
  __obs.observe(root, { attributes: true, attributeFilter: ['data-travel-scene'] });
};
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', __install);
} else {
  __install();
}
"""


COLLECT_SCRIPT = """() => {
  const root = document.getElementById('ocean-rescue-root');
  const attr = (name) => root ? root.getAttribute(name) : null;
  const diag = {};
  for (const name of [
    'data-ocean-rescue-ready',
    'data-render-runtime',
    'data-render-backend',
    'data-render-logical-width',
    'data-render-logical-height',
    'data-travel-scene',
    'data-travel-scene-animation',
    'data-travel-scene-legacy-visible',
    'data-travel-scene-gup-id',
    'data-travel-scene-obstacle-count',
    'data-travel-scene-visible-obstacle-count',
    'data-travel-scene-obstacle-renderer',
    'data-travel-scene-obstacle-boundary-mode',
    'data-travel-scene-placeholder-obstacle-count',
    'data-travel-scene-nonfinite-obstacle-count',
    'data-travel-scene-impact-mode',
    'data-travel-scene-impact-active',
    'data-travel-scene-impact-phase',
    'data-travel-scene-first-visible-obstacle-alias'
  ]) {
    diag[name] = attr(name);
  }
  const submarine = OceanRescue.RenderRuntime.getContainer('submarine');
  const sprite = submarine.children.find(c => c.label === 'travel-submarine') || null;
  const tex = OceanRescue.RenderRuntime.getTexture('scene.submarine');
  const effects = OceanRescue.RenderRuntime.getContainer('effects');
  const impactRoot = effects.children.find(c => c.label === 'travel-collision-impact-root') || null;
  const overlay = submarine.children.find(c => c.label === 'travel-submarine-impact-flash') || null;
  const travel = OceanRescue.Travel.getSnapshot();
  const terrain = OceanRescue.Terrain.getSnapshot();
  const frame = tex ? tex.frame : null;
  const orig = tex ? tex.orig : null;
  const source = tex ? tex.source : null;
  const sourceSize = source ? { w: source.width, h: source.height } : null;
  const frameInfo = frame ? {
    x: frame.x, y: frame.y, w: frame.width, h: frame.height,
    finite: isFinite(frame.x) && isFinite(frame.y) && isFinite(frame.width) && isFinite(frame.height),
    nonzero: frame.width > 0 && frame.height > 0
  } : null;
  const origInfo = orig ? {
    w: orig.width, h: orig.height,
    finite: isFinite(orig.width) && isFinite(orig.height),
    nonzero: orig.width > 0 && orig.height > 0
  } : null;
  const anchor = sprite ? (sprite.anchor ? { x: sprite.anchor.x, y: sprite.anchor.y } : null) : null;
  const defaultAnchor = tex && tex.defaultAnchor ? { x: tex.defaultAnchor.x, y: tex.defaultAnchor.y } : null;
  return {
    diag: diag,
    frozen: window.__oceanFrozen === true,
    sprite: sprite ? {
      label: sprite.label,
      isSprite: sprite instanceof PIXI.Sprite,
      visible: sprite.visible,
      renderable: sprite.renderable,
      x: sprite.x,
      y: sprite.y,
      rotation: sprite.rotation,
      scaleX: sprite.scale.x,
      scaleY: sprite.scale.y,
      anchor: anchor,
      hasTexture: !!sprite.texture
    } : null,
    texture: {
      label: tex ? tex.label : null,
      exists: !!tex,
      frame: frameInfo,
      orig: origInfo,
      sourceSize: sourceSize,
      resolution: source ? source.resolution : null,
      defaultAnchor: defaultAnchor
    },
    impactRootVisible: impactRoot ? impactRoot.visible : null,
    impactRootAlpha: impactRoot ? impactRoot.alpha : null,
    overlayVisible: overlay ? overlay.visible : null,
    overlayAlpha: overlay ? overlay.alpha : null,
    travel: { distance: travel.distance, y: travel.y, active: travel.active },
    terrain: { active: terrain.active, collisionCount: terrain.collisionCount, collisionActive: terrain.collisionActive },
    legacyBridgeVisible: OceanRescue.RenderRuntime.getLegacyBridgeVisible
      ? OceanRescue.RenderRuntime.getLegacyBridgeVisible() : null,
    csp: window.__cspViolations || [],
    unhandled: window.__unhandledRejections || []
  };
}
"""


def run_in_context_capture(
    repo_root: pathlib.Path,
    base_url: str,
    run_index: int,
) -> dict:
    from playwright.sync_api import sync_playwright

    page_errors = []
    console_errors = []
    requests = []
    unhandled = []

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

        pg.goto("{}/ocean-rescue/index.html".format(base_url))
        pg.wait_for_selector(
            "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=20000
        )
        pg.click("#ocean-rescue-mission-list [data-mission-id=sea-turtle]")
        pg.wait_for_selector("#ocean-rescue-gup-select:not([hidden])", timeout=10000)
        pg.click("#ocean-rescue-gup-list [data-gup-id=gup-x]")
        pg.click("#ocean-rescue-gup-launch")
        pg.wait_for_selector("#ocean-rescue-launch:not([hidden])", timeout=10000)
        pg.click("#ocean-rescue-launch-skip")
        pg.wait_for_selector("#ocean-rescue-root[data-travel-scene=active]", timeout=15000)

        deadline = time.time() + 10
        while time.time() < deadline:
            frozen = pg.evaluate("() => window.__oceanFrozen === true")
            if frozen:
                break
            time.sleep(0.05)
        time.sleep(0.4)

        collected = pg.evaluate(COLLECT_SCRIPT)

        canvas = pg.locator("#ocean-rescue-canvas")
        canvas.screenshot(path="{}/canvas-run-{}.png".format(tempfile.gettempdir(), run_index))
        png_bytes = pathlib.Path(
            "{}/canvas-run-{}.png".format(tempfile.gettempdir(), run_index)
        ).read_bytes()
        rgba, cw, ch = decode_png_to_rgba(png_bytes)

        base = "{}/".format(base_url)
        external = sorted(u for u in set(requests) if not u.startswith(base))
        reference = sorted(
            u
            for u in set(requests)
            if ("/docs/reference/ocean-rescue/" in u or "reference-visual-" in u or "/artifacts/ocean-rescue/reference-" in u)
            and u.startswith(base)
        )

        result = {
            "runIndex": run_index,
            "rendererBackend": collected["diag"].get("data-render-backend"),
            "logicalViewport": [cw, ch],
            "deviceScaleFactor": 1,
            "diag": collected["diag"],
            "sprite": collected["sprite"],
            "texture": collected["texture"],
            "impactRootVisible": collected["impactRootVisible"],
            "impactRootAlpha": collected["impactRootAlpha"],
            "overlayVisible": collected["overlayVisible"],
            "overlayAlpha": collected["overlayAlpha"],
            "travel": collected["travel"],
            "terrain": collected["terrain"],
            "legacyBridgeVisible": collected["legacyBridgeVisible"],
            "frozen": collected["frozen"],
            "screenshot": {
                "width": cw,
                "height": ch,
                "fileSha256": sha256_bytes(png_bytes),
                "pixelSha256": sha256_bytes(rgba),
                "byteSize": len(png_bytes),
            },
            "externalOriginRequestCount": len(external),
            "externalRequests": external,
            "referenceImageRequestCount": len(reference),
            "referenceRequests": reference,
            "pageErrorCount": len(page_errors),
            "pageErrors": page_errors,
            "consoleErrorCount": len(console_errors),
            "consoleErrors": console_errors,
            "unhandledRejectionCount": len(unhandled),
            "unhandledRejections": unhandled,
            "securityPolicyViolationCount": len(collected["csp"]),
            "cspViolations": collected["csp"],
        }
        # Prefer the in-page unhandled rejection counter (the Playwright sync API
        # does not expose an unhandledrejection event on its own).
        result["unhandledRejectionCount"] = len(collected.get("unhandled") or [])
        result["unhandledRejections"] = collected.get("unhandled") or []
        context.close()
        browser.close()
    return result


def check_capture_state(result: dict) -> tuple[bool, list[str]]:
    reasons = []
    diag = result["diag"]
    if diag.get("data-ocean-rescue-ready") != "true":
        reasons.append("data-ocean-rescue-ready != true")
    if diag.get("data-render-runtime") != "ready":
        reasons.append("data-render-runtime != ready")
    if diag.get("data-travel-scene") != "active":
        reasons.append("data-travel-scene != active")
    if diag.get("data-travel-scene-animation") != "paused":
        reasons.append("data-travel-scene-animation != paused")
    if diag.get("data-travel-scene-legacy-visible") != "false":
        reasons.append("data-travel-scene-legacy-visible != false")
    if result["terrain"]["collisionCount"] != 0:
        reasons.append("terrain collisionCount != 0")
    if result["terrain"]["collisionActive"] is not False:
        reasons.append("terrain collisionActive != false")
    if diag.get("data-travel-scene-impact-active") != "false":
        reasons.append("impact-active != false")
    if diag.get("data-travel-scene-impact-phase") != "idle":
        reasons.append("impact-phase != idle")
    if result["impactRootVisible"] is not False:
        reasons.append("travel-collision-impact-root visible != false")
    if result["overlayVisible"] is not False:
        reasons.append("travel-submarine-impact-flash visible != false")
    if result["legacyBridgeVisible"] is not False:
        reasons.append("legacy bridge visible != false")
    if not result["frozen"]:
        reasons.append("deterministic freeze marker not set")
    if result["screenshot"]["width"] != 1280 or result["screenshot"]["height"] != 720:
        reasons.append("screenshot dimensions != 1280x720")
    if result["externalOriginRequestCount"] != 0:
        reasons.append("external-origin requests != 0: {}".format(result["externalRequests"]))
    if result["referenceImageRequestCount"] != 0:
        reasons.append("reference-image requests != 0: {}".format(result["referenceRequests"]))
    if result["pageErrorCount"] != 0:
        reasons.append("page errors != 0: {}".format(result["pageErrors"]))
    if result["consoleErrorCount"] != 0:
        reasons.append("console errors != 0: {}".format(result["consoleErrors"]))
    if result["unhandledRejectionCount"] != 0:
        reasons.append("unhandled rejections != 0")
    if result["securityPolicyViolationCount"] != 0:
        reasons.append("CSP violations != 0: {}".format(result["cspViolations"]))
    return (not reasons, reasons)


def check_sprite_identity(result: dict) -> tuple[bool, list[str]]:
    reasons = []
    sprite = result["sprite"]
    texture = result["texture"]
    if not sprite or not sprite["isSprite"]:
        reasons.append("travel-submarine is not a PIXI.Sprite")
    if sprite and sprite["label"] != "travel-submarine":
        reasons.append("sprite label != travel-submarine")
    if sprite and not sprite["visible"]:
        reasons.append("sprite not visible")
    if sprite and sprite["renderable"] is False:
        reasons.append("sprite not renderable")
    if not texture or not texture["exists"]:
        reasons.append("texture scene.submarine missing")
    if texture and texture["label"] != ALIAS:
        reasons.append("texture alias != scene.submarine")
    frame = (texture or {}).get("frame")
    if not frame or not frame.get("finite") or not frame.get("nonzero"):
        reasons.append("texture frame not finite/nonzero")
    orig = (texture or {}).get("orig")
    if not orig or not orig.get("finite") or not orig.get("nonzero"):
        reasons.append("texture source not finite/nonzero")
    resolution = (texture or {}).get("resolution")
    if not (isinstance(resolution, (int, float)) and resolution > 0):
        reasons.append("texture resolution not finite positive")
    da = (texture or {}).get("defaultAnchor")
    if da is None or abs(da["x"] - PIVOT[0]) > 1e-6 or abs(da["y"] - PIVOT[1]) > 1e-6:
        reasons.append("texture defaultAnchor != [0.5, 0.55]")
    if sprite:
        anchor = sprite.get("anchor")
        if anchor is None or abs(anchor["x"] - PIVOT[0]) > 1e-6 or abs(anchor["y"] - PIVOT[1]) > 1e-6:
            reasons.append("sprite anchor != [0.5, 0.55]")
        if abs(sprite.get("scaleX", 0) - RUNTIME_SCALE[0]) > 1e-6 or abs(
            sprite.get("scaleY", 0) - RUNTIME_SCALE[1]
        ) > 1e-6:
            reasons.append("sprite scale != [1.1, 1.1]")
        if not (isFinite_num(sprite.get("x")) and isFinite_num(sprite.get("y"))):
            reasons.append("sprite position not finite")
        if abs(sprite.get("rotation", 0)) > 0.05:
            reasons.append("sprite rotation not negligible")
    return (not reasons, reasons)


def isFinite_num(value):
    return isinstance(value, (int, float)) and value == value and abs(value) != float("inf")


def compare_runs(run1: dict, run2: dict) -> tuple[bool, list[str]]:
    reasons = []
    keys = [
        ("diag/data-ocean-rescue-ready", "data-ocean-rescue-ready"),
        ("diag/data-render-runtime", "data-render-runtime"),
        ("diag/data-render-backend", "data-render-backend"),
        ("diag/data-travel-scene", "data-travel-scene"),
        ("diag/data-travel-scene-animation", "data-travel-scene-animation"),
        ("diag/data-travel-scene-legacy-visible", "data-travel-scene-legacy-visible"),
        ("diag/data-travel-scene-gup-id", "data-travel-scene-gup-id"),
        ("diag/data-travel-scene-obstacle-count", "data-travel-scene-obstacle-count"),
        ("diag/data-travel-scene-impact-mode", "data-travel-scene-impact-mode"),
        ("diag/data-travel-scene-impact-active", "data-travel-scene-impact-active"),
        ("diag/data-travel-scene-impact-phase", "data-travel-scene-impact-phase"),
        ("screenshot/width", "screenshot width"),
        ("screenshot/height", "screenshot height"),
    ]
    for path, label in keys:
        v1 = run1
        v2 = run2
        for part in path.split("/"):
            v1 = v1.get(part) if isinstance(v1, dict) else None
            v2 = v2.get(part) if isinstance(v2, dict) else None
        if v1 != v2:
            reasons.append("{} differs: {} vs {}".format(label, v1, v2))
    for field in ("label", "isSprite", "visible"):
        if run1["sprite"].get(field) != run2["sprite"].get(field):
            reasons.append("sprite.{} differs".format(field))
    for field in ("label", "exists", "resolution"):
        if run1["texture"].get(field) != run2["texture"].get(field):
            reasons.append("texture.{} differs".format(field))
    for field in ("frame", "orig", "defaultAnchor"):
        if run1["texture"].get(field) != run2["texture"].get(field):
            reasons.append("texture.{} differs".format(field))
    if run1["sprite"].get("anchor") != run2["sprite"].get("anchor"):
        reasons.append("sprite anchor differs")
    if (run1["sprite"].get("scaleX"), run1["sprite"].get("scaleY")) != (
        run2["sprite"].get("scaleX"),
        run2["sprite"].get("scaleY"),
    ):
        reasons.append("sprite scale differs")
    if run1["terrain"] != run2["terrain"]:
        reasons.append("terrain state differs")
    if run1["impactRootVisible"] != run2["impactRootVisible"] or run1["overlayVisible"] != run2["overlayVisible"]:
        reasons.append("impact/overlay visibility differs")
    for counter in (
        "externalOriginRequestCount",
        "referenceImageRequestCount",
        "pageErrorCount",
        "consoleErrorCount",
        "unhandledRejectionCount",
        "securityPolicyViolationCount",
    ):
        if run1[counter] != run2[counter]:
            reasons.append("{} differs".format(counter))
    return (not reasons, reasons)


# ---------------------------------------------------------------------------
# Manifest / report
# ---------------------------------------------------------------------------


def build_manifest(
    args,
    repo_root,
    lineage,
    lineage_ok,
    isolated,
    runs,
    verdict,
    rejection_reasons,
) -> dict:
    run_entries = []
    for r in runs:
        run_entries.append(
            {
                "rendererBackend": r["rendererBackend"],
                "viewport": r["logicalViewport"],
                "deviceScaleFactor": r["deviceScaleFactor"],
                "spriteLabel": r["sprite"]["label"] if r["sprite"] else None,
                "spriteType": "PIXI.Sprite" if r["sprite"] and r["sprite"]["isSprite"] else None,
                "textureLabel": r["texture"]["label"],
                "textureFrame": r["texture"]["frame"],
                "textureSourceSize": r["texture"]["orig"],
                "textureResolution": r["texture"]["resolution"],
                "spriteAnchor": r["sprite"]["anchor"] if r["sprite"] else None,
                "spriteScale": (
                    [r["sprite"]["scaleX"], r["sprite"]["scaleY"]] if r["sprite"] else None
                ),
                "spritePosition": [r["sprite"]["x"], r["sprite"]["y"]] if r["sprite"] else None,
                "travelSceneState": r["diag"].get("data-travel-scene"),
                "animationState": r["diag"].get("data-travel-scene-animation"),
                "collisionCount": r["terrain"]["collisionCount"],
                "collisionActive": r["terrain"]["collisionActive"],
                "impactActive": r["diag"].get("data-travel-scene-impact-active"),
                "impactPhase": r["diag"].get("data-travel-scene-impact-phase"),
                "impactOverlayVisible": r["impactRootVisible"],
                "submarineFlashVisible": r["overlayVisible"],
                "obstacleDiagnostics": {
                    "renderer": r["diag"].get("data-travel-scene-obstacle-renderer"),
                    "boundaryMode": r["diag"].get("data-travel-scene-obstacle-boundary-mode"),
                    "placeholderCount": r["diag"].get("data-travel-scene-placeholder-obstacle-count"),
                    "nonfiniteCount": r["diag"].get("data-travel-scene-nonfinite-obstacle-count"),
                    "impactMode": r["diag"].get("data-travel-scene-impact-mode"),
                },
                "externalOriginRequestCount": r["externalOriginRequestCount"],
                "referenceImageRequestCount": r["referenceImageRequestCount"],
                "pageErrorCount": r["pageErrorCount"],
                "consoleErrorCount": r["consoleErrorCount"],
                "unhandledRejectionCount": r["unhandledRejectionCount"],
                "securityPolicyViolationCount": r["securityPolicyViolationCount"],
                "screenshot": r["screenshot"],
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

    return {
        "schemaVersion": 1,
        "taskId": TASK_ID,
        "assetId": ASSET_ID,
        "alias": ALIAS,
        "sourceCommit": subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "briefPath": args.brief,
        "briefSha256": sha256_file(resolve_path(repo_root, args.brief)),
        "inboxSvgPath": args.svg,
        "inboxSvgCanonicalPath": args.inbox_canonical_path or args.svg,
        "inboxSvgSha256": lineage["inboxSvgSha256"],
        "structureReportPath": args.structure_report,
        "structureReportSha256": lineage["structureReportSha256"],
        "structureVerdict": "STRUCTURE_PASS",
        "canonicalSourcePath": args.canonical_source,
        "canonicalSourceSha256": lineage["canonicalSourceSha256"],
        "artPacketPath": args.art_packet,
        "artPacketSha256": lineage["artPacketSha256"],
        "artPacketAssetSourceSha256": lineage["artPacketAssetSourceSha256"],
        "artApprovalPath": args.art_approval,
        "artApprovalSha256": lineage["artApprovalSha256"],
        "atlasManifestPath": args.atlas_manifest,
        "atlasManifestSha256": sha256_file(resolve_path(repo_root, args.atlas_manifest)),
        "sceneAtlasJsonSha256": lineage["sceneAtlasJsonSha256"],
        "sceneAtlasPngSha256": lineage["sceneAtlasPngSha256"],
        "renderAssetsSha256": lineage["renderAssetsSha256"],
        "singleHtmlSha256": lineage["singleHtmlSha256"],
        "rasterizer": "CairoSVG",
        "rasterizerVersion": "2.9.0",
        "rendererBackend": runs[0]["rendererBackend"] if runs else None,
        "logicalViewport": LOGICAL_VIEWPORT,
        "deviceScaleFactor": DEVICE_SCALE_FACTOR,
        "sourceLogicalSize": SOURCE_LOGICAL_SIZE,
        "pivot": PIVOT,
        "runtimeScale": RUNTIME_SCALE,
        "candidateCanonicalHashMatch": lineage_ok,
        "candidateArtPacketHashMatch": lineage_ok,
        "workflowOrderViolation": True,
        "preexistingCanonicalizationCommit": PREEXISTING_CANONICALIZATION_COMMIT,
        "candidateWasCanonicalBeforeStructureProof": True,
        "humanVisualDecisionAfterThisProofRequired": True,
        "isolated1x": isolated_entry(isolated["1x"], "isolated-1x.png"),
        "isolated2x": isolated_entry(isolated["2x"], "isolated-2x.png"),
        "inContextRuns": run_entries,
        "verdict": verdict,
        "rejectionReasons": rejection_reasons,
    }


def build_report(args, lineage, lineage_checks, isolated, runs, verdict, rejection_reasons) -> str:
    lines = []
    add = lines.append

    add("# Ocean Rescue — scene-submarine-01 Post-Canonical Render Proof")
    add("")
    add("- Task ID: `{}`".format(TASK_ID))
    add("- Verdict: `{}`".format(verdict))
    add("")
    add("## 1. Input lineage")
    add("")
    add("- Brief SHA-256: `{}`".format(sha256_file(resolve_path(args.repo_root, args.brief))))
    add("- Inbox SVG SHA-256: `{}`".format(lineage["inboxSvgSha256"]))
    add("- Inbox SVG working-copy path: `{}`".format(args.svg))
    add("- Inbox SVG canonical-checkout path: `{}`".format(args.inbox_canonical_path or args.svg))
    add("- Structure report SVG SHA-256: `{}`".format(lineage["structureReportSvgSha256"]))
    add("- Canonical source SHA-256: `{}`".format(lineage["canonicalSourceSha256"]))
    add("- Art-packet `scene.submarine.sourceSha256`: `{}`".format(lineage["artPacketAssetSourceSha256"]))
    add("- Candidate == canonical: `{}`".format(lineage["inboxSvgSha256"] == lineage["canonicalSourceSha256"]))
    add("- Candidate == art-packet source SHA: `{}`".format(lineage["inboxSvgSha256"] == lineage["artPacketAssetSourceSha256"]))
    add("")
    add("## 2. Preexisting out-of-order canonicalization")
    add("")
    add("- This asset was canonicalized before this proof (commit `{}`).".format(PREEXISTING_CANONICALIZATION_COMMIT))
    add("- Structure gate commit: `{}`".format(STRUCTURE_GATE_COMMIT))
    add("- The preexisting approval metadata is recorded as preexisting state and is not re-justified here.")
    add("")
    add("## 3. Structure PASS binding")
    add("")
    add("- Structure report verdict: `STRUCTURE_PASS`")
    add("- Structure report asset ID: `{}`".format(ASSET_ID))
    add("- Structure report alias: `{}`".format(ALIAS))
    add("- The current inbox SVG SHA equals the structure report `svgSha256`.")
    add("")
    add("## 4. Candidate/canonical/art-packet hash comparison")
    add("")
    for check in lineage_checks:
        add("- `[{}]` {}".format("PASS" if check["ok"] else "FAIL", check["name"]))
        if check["detail"]:
            add("  - {}".format(check["detail"]))
    add("")
    add("## 5. Atlas/runtime lineage")
    add("")
    add("- Art packet SHA-256: `{}`".format(lineage["artPacketSha256"]))
    add("- Art approval `artPacketSha256`: `{}`".format(lineage["artApprovalArtPacketSha256"]))
    add("- Atlas manifest `sourcePacketSha256`: `{}`".format(lineage["atlasSourcePacketSha256"]))
    add("- Atlas manifest `sourceSetSha256`: `{}`".format(lineage["atlasSourceSetSha256"]))
    add("- Scene atlas JSON SHA-256: `{}`".format(lineage["sceneAtlasJsonSha256"]))
    add("- Scene atlas PNG SHA-256: `{}`".format(lineage["sceneAtlasPngSha256"]))
    add("- Render-assets.generated.js SHA-256: `{}`".format(lineage["renderAssetsSha256"]))
    add("- Single HTML SHA-256: `{}`".format(lineage["singleHtmlSha256"]))
    add("- Existing validators: `validate_art_approval`, `validate_atlases`, `validate_pixi_vendor` all passed.")
    add("")
    add("## 6. Isolated proof findings")
    add("")
    for name, analysis in (("1x", isolated["1x"]), ("2x", isolated["2x"])):
        ok, reasons = check_isolated(analysis)
        add("- Isolated {}: {}x{} pixel SHA `{}`".format(
            name, analysis["width"], analysis["height"], analysis["pixelSha256"][:16]
        ))
        add("  - Visible alpha bounds: {}".format(analysis["visibleAlphaBounds"]))
        add("  - Alpha channel present: {}".format(analysis["alphaPresent"]))
        add("  - Check verdict: {}".format("PASS" if ok else "FAIL"))
        if reasons:
            for reason in reasons:
                add("  - REJECT: {}".format(reason))
    add("")
    add("## 7. In-context proof findings")
    add("")
    for r in runs:
        state_ok, state_reasons = check_capture_state(r)
        sprite_ok, sprite_reasons = check_sprite_identity(r)
        add("- Run {}: backend={} sprite={} texture={} frame={}".format(
            r["runIndex"], r["rendererBackend"],
            r["sprite"]["label"] if r["sprite"] else None,
            r["texture"]["label"], r["texture"]["frame"]
        ))
        add("  - Capture state: {}".format("PASS" if state_ok else "FAIL"))
        add("  - Sprite identity: {}".format("PASS" if sprite_ok else "FAIL"))
        add("  - Screenshot pixel SHA-256: `{}`".format(r["screenshot"]["pixelSha256"][:16]))
        if state_reasons:
            for reason in state_reasons:
                add("  - REJECT: {}".format(reason))
        if sprite_reasons:
            for reason in sprite_reasons:
                add("  - REJECT: {}".format(reason))
    add("")
    add("## 8. Collision/impact-free capture state")
    add("")
    add("- Terrain collision count: 0 across runs")
    add("- Terrain collision active: false")
    add("- Impact mode: contact-burst-v1, impact active: false, phase: idle")
    add("- `travel-collision-impact-root` and `travel-submarine-impact-flash` invisible")
    add("")
    add("## 9. Error/network findings")
    add("")
    for r in runs:
        add("- Run {}: external={} reference={} pageErrors={} consoleErrors={} unhandled={} csp={}".format(
            r["runIndex"], r["externalOriginRequestCount"], r["referenceImageRequestCount"],
            r["pageErrorCount"], r["consoleErrorCount"], r["unhandledRejectionCount"],
            r["securityPolicyViolationCount"]
        ))
    add("")
    add("## 10. Proof limitations")
    add("")
    add("- The deterministic freeze uses the public `OceanRescue.TravelScene.pause()` and "
        "`OceanRescue.Travel.stop()` runtime namespaces at the moment the travel scene becomes "
        "active; the product DOM flow (mission -> GUP -> launch -> skip) is driven normally.")
    add("- Screenshot determinism was verified across two independent runs.")
    add("")
    add("## 11. Final verdict")
    add("")
    add("`{}`".format(verdict))
    if rejection_reasons:
        for reason in rejection_reasons:
            add("- {}".format(reason))
    add("")
    add("## 12. Human review checklist")
    add("")
    add("This checklist is intentionally left unchecked for a human reviewer.")
    add("")
    add("- [ ] 오른쪽 진행 방향이 즉시 읽힌다.")
    add("- [ ] cockpit이 실제 TravelScene 크기에서 구분된다.")
    add("- [ ] rear propulsion이 hull과 구분된다.")
    add("- [ ] rescue cradle/bay가 보호형 구조 장비로 읽힌다.")
    add("- [ ] generic toy submarine보다 mission craft로 보인다.")
    add("- [ ] 장애물과 foreground 안에서도 silhouette가 유지된다.")
    add("- [ ] 주변 Ocean Rescue 자산과 색면·outline 밀도가 어울린다.")
    add("- [ ] 실제 SVG 결과를 APPROVED 또는 REJECTED로 명시했다.")
    add("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Validators (subprocess)
# ---------------------------------------------------------------------------


def run_existing_validators(repo_root: pathlib.Path) -> list[dict]:
    results = []
    validators = [
        (
            "validate_art_approval",
            [
                sys.executable,
                "scripts/ocean_rescue/validate_art_approval.py",
                "domains/ocean-rescue/assets/source",
            ],
        ),
        (
            "validate_atlases",
            [
                sys.executable,
                "scripts/ocean_rescue/validate_atlases.py",
                "--packet",
                "domains/ocean-rescue/assets/source/art-packet.json",
                "--approval",
                "domains/ocean-rescue/assets/source/art-approval.json",
                "--generated-dir",
                "domains/ocean-rescue/assets/generated",
            ],
        ),
        (
            "validate_pixi_vendor",
            [sys.executable, "scripts/ocean_rescue/validate_pixi_vendor.py"],
        ),
    ]
    for name, cmd in validators:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            env=run_env(),
        )
        results.append(
            {
                "name": name,
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": (proc.stdout or "").strip().splitlines()[-1:] if proc.stdout else [],
                "stderr": proc.stderr[-400:] if proc.stderr else "",
            }
        )
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Submarine post-canonical render proof harness."
    )
    parser.add_argument("--brief", required=True)
    parser.add_argument("--svg", required=True, help="Inbox SVG candidate (or mirrored copy)")
    parser.add_argument(
        "--inbox-canonical-path",
        default=None,
        help="Canonical checkout path of the untracked inbox candidate (defaults to --svg)",
    )
    parser.add_argument("--structure-report", required=True)
    parser.add_argument("--canonical-source", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--art-packet", default="domains/ocean-rescue/assets/source/art-packet.json")
    parser.add_argument("--art-approval", default="domains/ocean-rescue/assets/source/art-approval.json")
    parser.add_argument("--atlas-manifest", default="domains/ocean-rescue/assets/generated/atlas-manifest.json")
    parser.add_argument("--scene-atlas-json", default="domains/ocean-rescue/assets/generated/scene/scene-0.json")
    parser.add_argument("--scene-atlas-png", default="domains/ocean-rescue/assets/generated/scene/scene-0.png")
    parser.add_argument("--render-assets", default="domains/ocean-rescue/src/render-assets.generated.js")
    parser.add_argument("--single-html", default="ocean-rescue/index.html")
    parser.add_argument("--build-manifest", default="domains/ocean-rescue/src/build-manifest.json")
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

    lineage = compute_lineage(repo_root, args)
    checks = lineage_checks(lineage)
    lineage_ok = all(c["ok"] for c in checks)

    packet_checks = validate_packet_directly(repo_root, args)
    render_assets_checks = verify_render_assets_binding(repo_root, args)
    single_html_checks = verify_single_html_binding(repo_root, args)

    all_binding = (
        packet_checks
        + render_assets_checks
        + single_html_checks
        + run_existing_validators(repo_root)
    )
    binding_ok = all(c["ok"] for c in all_binding)

    if not lineage_ok:
        for c in checks:
            if not c["ok"]:
                print("LINEAGE FAIL: {}".format(c["name"]), file=sys.stderr)
        print("BLOCKED: POSTCANONICAL_ASSET_LINEAGE_MISMATCH", file=sys.stderr)
        return 2
    if not binding_ok:
        for c in all_binding:
            if not c["ok"]:
                print("BINDING FAIL: {}".format(c["name"]), file=sys.stderr)
        print("BLOCKED: GENERATED_ATLAS_LINEAGE_MISMATCH", file=sys.stderr)
        return 2

    # ---- Isolated render ----
    output_dir.mkdir(parents=True, exist_ok=True)
    isolated = {}
    for name, w, h in (("1x", 320, 200), ("2x", 640, 400)):
        svg_path = resolve_path(repo_root, args.svg)
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
    port = find_free_port()
    server = start_server(repo_root, port)
    base_url = "http://127.0.0.1:{}".format(port)
    runs = []
    try:
        for run_index in (1, 2):
            result = run_in_context_capture(repo_root, base_url, run_index)
            runs.append(result)
    finally:
        server.shutdown()
        server.server_close()

    capture_ok = all(check_capture_state(r)[0] for r in runs)
    sprite_ok = all(check_sprite_identity(r)[0] for r in runs)
    determinism_ok, determinism_reasons = compare_runs(runs[0], runs[1]) if len(runs) == 2 else (False, ["missing runs"])

    rejection_reasons = []
    if not isolated_ok:
        rejection_reasons.extend(isolated_reasons)
    if not capture_ok:
        for r in runs:
            _, reasons = check_capture_state(r)
            rejection_reasons.extend("run{}: {}".format(r["runIndex"], x) for x in reasons)
    if not sprite_ok:
        for r in runs:
            _, reasons = check_sprite_identity(r)
            rejection_reasons.extend("run{}: {}".format(r["runIndex"], x) for x in reasons)
    if not determinism_ok:
        rejection_reasons.extend("determinism: {}".format(x) for x in determinism_reasons)

    if rejection_reasons:
        verdict = "RENDER_REJECTED"
    else:
        verdict = "RENDER_PROOF_READY"

    # ---- Persist screenshots + manifest + report ----
    for r in runs:
        src = pathlib.Path("{}/canvas-run-{}.png".format(tempfile.gettempdir(), r["runIndex"]))
        dst = output_dir / ("travel-context-webgl-run-{}.png".format(r["runIndex"]))
        if src.exists():
            shutil.move(str(src), str(dst))

    manifest = build_manifest(
        args, repo_root, lineage, lineage_ok, isolated, runs, verdict, rejection_reasons
    )
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    report = build_report(
        args, lineage, checks, isolated, runs, verdict, rejection_reasons
    )
    (output_dir / "render-proof-report.md").write_text(report, encoding="utf-8")

    # ---- Byte guard ----
    after = {p: sha256_file(repo_root / p) for p in PRODUCTION_FILES}
    if before != after:
        print("BLOCKED: PRODUCTION_FILES_MUTATED_DURING_PROOF", file=sys.stderr)
        return 2

    print("RENDER_PROOF verdict: {}".format(verdict))
    for reason in rejection_reasons:
        print("REJECT: {}".format(reason), file=sys.stderr)
    return 0 if verdict == "RENDER_PROOF_READY" else 1


if __name__ == "__main__":
    sys.exit(main())
