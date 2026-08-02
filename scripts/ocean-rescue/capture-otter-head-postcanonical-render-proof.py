#!/usr/bin/env python3
"""Post-canonical render proof for the approved otter-head-01 production binding.

Proves that the canonical otter-head SVG (already human-approved and committed as
``domains/ocean-rescue/assets/source/characters/otter-head.svg``) is bound
pixel-exactly into the production characters atlas and that the production
single HTML renders the Sea Turtle rescue rig's four face states from that
canonical atlas texture ``otter.head`` with no candidate injection.

This proof NEVER injects a candidate texture, rebuilds the atlas, rebuilds the
single HTML, or modifies any production file. It only:

  1. Validates the input gate (canonical SVG SHA, structure report, pre-canonical
     proof manifest, atlas-repair ancestry).
  2. Renders the canonical SVG with the pinned atlas rasterizer (CairoSVG 2.9.0)
     at 1x (200x200) and 2x (400x400) and validates the approved pixel hashes.
  3. Reconstructs the ``otter.head`` frame from the real production atlas PNG
     (400x400 source canvas, unmasked paste) and proves byte-exact equality with
     the canonical 2x raster (0 mismatched pixels/channels).
  4. Boots the tracked production single HTML through the normal product flow
     (mission -> GUP -> launch -> skip -> travel arrival -> rescue active),
     freezes the sea-turtle scene at a deterministic t=0 state, and asserts the
     runtime texture identity ``otter.head`` on the ``sea-otter-head`` sprite
     plus the unchanged production eye/mouth/torso/arm/tail textures.
  5. Captures four face states (base-only, neutral, concern, smile) cropped
     around the head, a full-screen context shot, and a contact sheet, twice,
     then checks cross-run pixel determinism.
  6. Verifies production files and the existing pre-canonical proof evidence are
     byte-unchanged across the whole proof.
  7. Writes manifest.json + render-proof-report.md under the post-canonical
     evidence root.

Exit codes:
    0  POST_CANONICAL_RENDER_PROOF_READY
    1  POST_CANONICAL_RENDER_REJECTED
    2  BLOCKED
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import pathlib
import socketserver
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler
from typing import Any

TASK_ID = "AIDENGAME-OCEAN-RESCUE-OTTER-HEAD-POST-CANONICAL-RENDER-PROOF-02"
ASSET_ID = "otter-head-01"
ALIAS = "otter.head"

APPROVED_CANDIDATE_SHA = (
    "87e6b35d67e0d856d389570614bb47abef9f6271402e881660f98f400e40c5ec"
)
APPROVED_1X_PIXEL_SHA = (
    "4a0bd666e394ae222b6d64d050996de56988b38d47ecf262fe4742f1d68b577b"
)
APPROVED_2X_PIXEL_SHA = (
    "dee47164ab12d192d93fd66efdbb0909febac683a0be09aafe56c3ae92221d14"
)

CANONICALIZATION_COMMIT = "fba9c1a3a581d89c1b98cb903f78eb43c6652db5"
ATLAS_REPAIR_COMMIT = "e8bb970c0c8dac394c662bead5fbc3d4160927c3"

SOURCE_LOGICAL_SIZE = [200, 200]
PHYSICAL_RASTER_SIZE = [400, 400]
PIVOT = [0.5, 0.55]
RUNTIME_SCALE = [0.62, 0.62]
LOGICAL_VIEWPORT = [1280, 720]
DEVICE_SCALE_FACTOR = 1

RASTERIZER = "CairoSVG"
RASTERIZER_VERSION = "2.9.0"

CAIRO_LIB_PATHS = ("/opt/homebrew/opt/cairo/lib", "/opt/homebrew/lib")
CAIRO_ENV = {"DYLD_LIBRARY_PATH": CAIRO_LIB_PATHS[0]}

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

HEAD_SPRITE_LABEL = "sea-otter-head"
HEAD_TEXTURE_LABEL = "otter.head"
EYE_OVERLAY_LABELS = ("sea-otter-eyes-open", "sea-otter-eyes-closed")
MOUTH_OVERLAY_LABELS = (
    "sea-otter-mouth-neutral",
    "sea-otter-mouth-concern",
    "sea-otter-mouth-smile",
)
OTHER_RIG_LABELS = (
    "sea-otter-torso",
    "sea-otter-arm-near",
    "sea-otter-arm-far",
    "sea-otter-tail",
)

OVERLAY_TEXTURE_ALIASES = {
    "sea-otter-eyes-open": "otter.eyes.open",
    "sea-otter-eyes-closed": "otter.eyes.closed",
    "sea-otter-mouth-neutral": "otter.mouth.neutral",
    "sea-otter-mouth-concern": "otter.mouth.concern",
    "sea-otter-mouth-smile": "otter.mouth.smile",
    "sea-otter-torso": "otter.torso",
    "sea-otter-arm-near": "otter.arm.near",
    "sea-otter-arm-far": "otter.arm.far",
    "sea-otter-tail": "otter.tail",
}

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

FACE_CROP = {"x": 440, "y": 230, "width": 300, "height": 300}

ATLAS_FRAME = {"x": 4, "y": 4, "w": 340, "h": 338}
ATLAS_SPRITE_SOURCE = {"x": 30, "y": 42, "w": 340, "h": 338}
ATLAS_SOURCE_SIZE = {"w": 400, "h": 400}

HUMAN_APPROVAL = {
    "decision": "APPROVED",
    "date": "2026-08-02",
    "input": "승인",
    "approvedProofTaskId": "AIDENGAME-OCEAN-RESCUE-OTTER-HEAD-HANDOFF-RENDER-PROOF-01",
}

CANONICAL_SVG_PATH = "domains/ocean-rescue/assets/source/characters/otter-head.svg"
ART_PACKET_PATH = "domains/ocean-rescue/assets/source/art-packet.json"
ART_APPROVAL_PATH = "domains/ocean-rescue/assets/source/art-approval.json"
ATLAS_MANIFEST_PATH = "domains/ocean-rescue/assets/generated/atlas-manifest.json"
CHARACTERS_ATLAS_JSON = (
    "domains/ocean-rescue/assets/generated/characters/characters-0.json"
)
CHARACTERS_ATLAS_PNG = (
    "domains/ocean-rescue/assets/generated/characters/characters-0.png"
)
RENDER_ASSETS_PATH = "domains/ocean-rescue/src/render-assets.generated.js"
BUILD_MANIFEST_PATH = "domains/ocean-rescue/src/build-manifest.json"
SINGLE_HTML_PATH = "ocean-rescue/index.html"
SEA_TURTLE_SCENE_PATH = "domains/ocean-rescue/src/sea-turtle-scene.js"
SEA_TURTLE_PATH = "domains/ocean-rescue/src/sea-turtle.js"

PRECANONICAL_PROOF_DIR = (
    pathlib.Path("domains")
    / "ocean-rescue"
    / "assets"
    / "review"
    / "handoff-proof"
    / "otter-head-01"
)

PRODUCTION_FILES = [
    CANONICAL_SVG_PATH,
    ART_PACKET_PATH,
    ART_APPROVAL_PATH,
    ATLAS_MANIFEST_PATH,
    CHARACTERS_ATLAS_JSON,
    CHARACTERS_ATLAS_PNG,
    RENDER_ASSETS_PATH,
    BUILD_MANIFEST_PATH,
    SEA_TURTLE_SCENE_PATH,
    SEA_TURTLE_PATH,
    SINGLE_HTML_PATH,
]

PRECANONICAL_EVIDENCE_FILES = [
    "domains/ocean-rescue/assets/review/handoff-proof/otter-head-01/face-rig-contact-sheet.png",
    "domains/ocean-rescue/assets/review/handoff-proof/otter-head-01/isolated-1x.png",
    "domains/ocean-rescue/assets/review/handoff-proof/otter-head-01/isolated-2x.png",
    "domains/ocean-rescue/assets/review/handoff-proof/otter-head-01/manifest.json",
    "domains/ocean-rescue/assets/review/handoff-proof/otter-head-01/render-proof-report.md",
    "domains/ocean-rescue/assets/review/handoff-proof/otter-head-01/rig-base-only.png",
    "domains/ocean-rescue/assets/review/handoff-proof/otter-head-01/rig-concern.png",
    "domains/ocean-rescue/assets/review/handoff-proof/otter-head-01/rig-neutral.png",
    "domains/ocean-rescue/assets/review/handoff-proof/otter-head-01/rig-smile.png",
    "domains/ocean-rescue/assets/review/handoff-proof/otter-head-01/sea-turtle-context.png",
]

FORBIDDEN_WRITE_PREFIXES = (
    "domains/ocean-rescue/assets/source/",
    "domains/ocean-rescue/assets/generated/",
    "domains/ocean-rescue/assets/review/handoff-proof/otter-head-01/",
    "domains/ocean-rescue/src/",
    "ocean-rescue/index.html",
)

FORBIDDEN_INJECTION_TOKENS = (
    "candidate-otter-head-01",
    "PIXI.Texture.from",
    "base64",
    "head.texture =",
    "ImageSource",
)


# ---------------------------------------------------------------------------
# Hash / JSON / git helpers
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


def check_repair_ancestry(repo_root: pathlib.Path) -> bool:
    """True when the atlas-repair commit is an ancestor of HEAD."""
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", ATLAS_REPAIR_COMMIT, "HEAD"],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, OSError):
        return False


def current_head_sha(repo_root: pathlib.Path) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
            text=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return ""


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
                raise ValueError("Bit depth != 8 not supported")
            if color_type not in (2, 6):
                raise ValueError("Color type not 2/6")
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
        raise ValueError("Raw data size mismatch")
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
    """Validate canonical SVG, structure report, pre-canonical proof, ancestry."""
    svg = resolve_path(repo_root, args.canonical_svg)
    structure = resolve_path(repo_root, args.structure_report)
    pre_manifest = resolve_path(repo_root, args.precanonical_manifest)

    if not svg.is_file():
        return False, "CANONICAL_SVG_MISSING"
    if not structure.is_file():
        return False, "STRUCTURE_REPORT_MISSING"
    if not pre_manifest.is_file():
        return False, "PRECANONICAL_MANIFEST_MISSING"

    svg_sha = sha256_file(svg)
    if svg_sha != APPROVED_CANDIDATE_SHA:
        return False, "CANONICAL_SVG_SHA_MISMATCH"

    report = load_json(structure)
    if report.get("verdict") != "STRUCTURE_PASS":
        return False, "STRUCTURE_GATE_NOT_PASSED"
    if report.get("assetId") != ASSET_ID:
        return False, "STRUCTURE_REPORT_ASSET_ID_MISMATCH"
    if report.get("alias") != ALIAS:
        return False, "STRUCTURE_REPORT_ALIAS_MISMATCH"
    if report.get("svgSha256") != APPROVED_CANDIDATE_SHA:
        return False, "STRUCTURE_REPORT_INPUT_SHA_MISMATCH"

    pre = load_json(pre_manifest)
    if pre.get("verdict") != "RENDER_PROOF_READY":
        return False, "PRECANONICAL_PROOF_NOT_READY"
    if pre.get("candidateSvgSha256") != APPROVED_CANDIDATE_SHA:
        return False, "PRECANONICAL_CANDIDATE_SHA_MISMATCH"
    if pre.get("structureVerdict") != "STRUCTURE_PASS":
        return False, "PRECANONICAL_STRUCTURE_VERDICT_MISMATCH"
    if pre.get("twoRunDeterministic") is not True:
        return False, "PRECANONICAL_TWO_RUN_NOT_DETERMINISTIC"
    if pre.get("rendererBackend") != "webgl":
        return False, "PRECANONICAL_RENDERER_NOT_WEBGL"
    textures_unchanged = pre.get("texturesUnchanged")
    if textures_unchanged is None:
        textures_unchanged = pre.get("otherTexturesUnchanged")
    if textures_unchanged is not True:
        return False, "PRECANONICAL_TEXTURES_CHANGED"
    for counter in (
        "externalRequestCount",
        "pageErrorCount",
        "consoleErrorCount",
        "cspViolationCount",
        "unhandledRejectionCount",
    ):
        if pre.get(counter) != 0:
            return False, "PRECANONICAL_ERROR_COUNTERS_NONZERO"

    if not check_repair_ancestry(repo_root):
        return False, "ATLAS_REPAIR_COMMIT_NOT_IN_ANCESTRY"

    return True, ""


# ---------------------------------------------------------------------------
# Candidate injection guard
# ---------------------------------------------------------------------------


def find_injection_tokens(source_text: str) -> list[str]:
    """Return any candidate-injection tokens found in a script body.

    The ``FORBIDDEN_INJECTION_TOKENS`` constant definition is itself a literal
    listing of the tokens, so it is excluded before scanning the body.
    """
    body = source_text
    start = body.find("FORBIDDEN_INJECTION_TOKENS = (")
    if start != -1:
        end = body.find(")\n", start)
        if end != -1:
            body = body[:start] + body[end + 1 :]
    return [tok for tok in FORBIDDEN_INJECTION_TOKENS if tok in body]


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
    from PIL import Image

    if png_bytes[:8] != PNG_SIGNATURE:
        raise ValueError("Invalid PNG signature")
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    width, height = img.size
    alpha = img.split()[3]
    alpha_extrema = alpha.getextrema()
    bbox = alpha.getbbox()
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
        "alphaMin": alpha_extrema[0],
        "alphaMax": alpha_extrema[1],
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


def check_isolated_approved(analysis: dict) -> tuple[bool, list[str]]:
    ok, reasons = check_isolated(analysis)
    if analysis.get("pixelSha256") not in (
        APPROVED_1X_PIXEL_SHA,
        APPROVED_2X_PIXEL_SHA,
    ):
        reasons.append("pixel SHA not approved: {}".format(analysis.get("pixelSha256")))
    return (ok and not reasons, reasons)


# ---------------------------------------------------------------------------
# Atlas frame RGBA reconstruction
# ---------------------------------------------------------------------------


def reconstruct_atlas_frame(repo_root: pathlib.Path) -> dict:
    """Reconstruct the otter.head frame from the real atlas PNG and compare.

    Uses the exact unmasked paste the production builder performs:
    ``page_img.paste(trimmed_img, (content_x, content_y))``.
    """
    from PIL import Image

    atlas_png = resolve_path(repo_root, CHARACTERS_ATLAS_PNG)
    sheet_json = resolve_path(repo_root, CHARACTERS_ATLAS_JSON)
    svg_path = resolve_path(repo_root, CANONICAL_SVG_PATH)

    sheet = load_json(sheet_json)
    frame_data = sheet["frames"][ALIAS]
    frame = frame_data["frame"]
    sprite = frame_data["spriteSourceSize"]
    source = frame_data["sourceSize"]

    atlas = Image.open(atlas_png).convert("RGBA")
    sub = atlas.crop(
        (frame["x"], frame["y"], frame["x"] + frame["w"], frame["y"] + frame["h"])
    )
    recon = Image.new("RGBA", (source["w"], source["h"]), (0, 0, 0, 0))
    recon.paste(sub, (sprite["x"], sprite["y"]))

    canon_png = render_svg_to_png(
        svg_path, PHYSICAL_RASTER_SIZE[0], PHYSICAL_RASTER_SIZE[1]
    )
    canon = Image.open(io.BytesIO(canon_png)).convert("RGBA")

    recon_bytes = recon.tobytes()
    canon_bytes = canon.tobytes()
    assert len(recon_bytes) == len(canon_bytes), "RGBA size mismatch"

    mismatched_pixels = sum(
        1
        for i in range(0, len(recon_bytes), 4)
        if recon_bytes[i : i + 4] != canon_bytes[i : i + 4]
    )
    mismatched_channels = sum(
        1 for i in range(len(recon_bytes)) if recon_bytes[i] != canon_bytes[i]
    )

    return {
        "frame": frame,
        "sourceSize": source,
        "spriteSourceSize": sprite,
        "rotated": frame_data["rotated"],
        "trimmed": frame_data["trimmed"],
        "anchor": frame_data.get("anchor"),
        "reconstructedSize": [source["w"], source["h"]],
        "reconstructedPixelSha256": sha256_bytes(recon_bytes),
        "canonical2xPixelSha256": sha256_bytes(canon_bytes),
        "pixelExact": recon_bytes == canon_bytes,
        "mismatchedPixels": mismatched_pixels,
        "mismatchedChannels": mismatched_channels,
    }


def check_atlas_reconstruction(recon: dict) -> tuple[bool, list[str]]:
    reasons = []
    if recon["frame"] != ATLAS_FRAME:
        reasons.append("frame metadata mismatch: {}".format(recon["frame"]))
    if recon["sourceSize"] != {"w": 400, "h": 400}:
        reasons.append("sourceSize mismatch: {}".format(recon["sourceSize"]))
    if recon["spriteSourceSize"] != ATLAS_SPRITE_SOURCE:
        reasons.append(
            "spriteSourceSize mismatch: {}".format(recon["spriteSourceSize"])
        )
    if recon["rotated"] is not False:
        reasons.append("rotated != false")
    if recon["trimmed"] is not True:
        reasons.append("trimmed != true")
    if recon["reconstructedSize"] != [400, 400]:
        reasons.append("reconstructed size != 400x400")
    if recon["reconstructedPixelSha256"] != APPROVED_2X_PIXEL_SHA:
        reasons.append("reconstructed pixel SHA != approved 2x SHA")
    if recon["canonical2xPixelSha256"] != APPROVED_2X_PIXEL_SHA:
        reasons.append("canonical 2x pixel SHA != approved 2x SHA")
    if recon["pixelExact"] is not True:
        reasons.append("reconstruction is not byte-exact")
    if recon["mismatchedPixels"] != 0:
        reasons.append("mismatched pixels != 0")
    if recon["mismatchedChannels"] != 0:
        reasons.append("mismatched channels != 0")
    return (not reasons, reasons)


# ---------------------------------------------------------------------------
# Playwright in-context capture
# ---------------------------------------------------------------------------


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(kwargs.pop("directory")), **kwargs)

    def log_message(self, format: str, *args) -> None:
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

SET_FACE_STATE_SCRIPT = """
(state) => {
  const rig = window.OceanRescue.RenderRuntime.getContainer('seaOtterRig');
  const find = (label) => rig.children.find((c) => c.label === label);
  const head = find('sea-otter-head');
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
    'data-render-texture-count',
    'data-rescue-phase',
    'data-sea-turtle-scene',
    'data-sea-turtle-scene-node-count',
    'data-sea-turtle-scene-animation',
    'data-sea-turtle-scene-legacy-visible',
    'data-sea-turtle-active',
    'data-sea-turtle-rope-id'
  ]) {
    diag[name] = attr(name);
  }
  const rig = OceanRescue.RenderRuntime.getContainer('seaOtterRig');
  const find = (label) => rig.children.find((c) => c.label === label);
  const spriteInfo = (s) => {
    if (!s) return null;
    const tex = s.texture;
    let bounds = null;
    if (typeof s.getBounds === 'function') {
      try {
        const b = s.getBounds();
        bounds = { x: b.x, y: b.y, width: b.width, height: b.height };
      } catch (e) {
        bounds = { error: String(e) };
      }
    }
    return {
      label: s.label,
      isSprite: s instanceof PIXI.Sprite,
      visible: s.visible,
      renderable: s.renderable,
      x: s.x,
      y: s.y,
      rotation: s.rotation,
      scaleX: s.scale.x,
      scaleY: s.scale.y,
      anchor: { x: s.anchor.x, y: s.anchor.y },
      textureLabel: tex ? tex.label : null,
      textureFrame: tex ? { x: tex.frame.x, y: tex.frame.y, w: tex.frame.width, h: tex.frame.height } : null,
      textureOrig: tex ? { w: tex.orig.width, h: tex.orig.height } : null,
      textureResolution: tex ? tex.source.resolution : null,
      bounds: bounds
    };
  };
  const head = find('sea-otter-head');
  const overlays = {};
  for (const label of [
    'sea-otter-eyes-open',
    'sea-otter-eyes-closed',
    'sea-otter-mouth-neutral',
    'sea-otter-mouth-concern',
    'sea-otter-mouth-smile',
    'sea-otter-torso',
    'sea-otter-arm-near',
    'sea-otter-arm-far',
    'sea-otter-tail'
  ]) {
    overlays[label] = spriteInfo(find(label));
  }
  const faceState = {
    headRotation: head ? head.rotation : null,
    eyesOpenVisible: find('sea-otter-eyes-open') ? find('sea-otter-eyes-open').visible : null,
    eyesClosedVisible: find('sea-otter-eyes-closed') ? find('sea-otter-eyes-closed').visible : null,
    mouthNeutralVisible: find('sea-otter-mouth-neutral') ? find('sea-otter-mouth-neutral').visible : null,
    mouthConcernVisible: find('sea-otter-mouth-concern') ? find('sea-otter-mouth-concern').visible : null,
    mouthSmileVisible: find('sea-otter-mouth-smile') ? find('sea-otter-mouth-smile').visible : null
  };
  const allRigLabels = rig.children.filter((c) => c && c.label).map((c) => c.label);
  const candidateInjectionAbsent = allRigLabels.every((l) => l.indexOf('candidate-') !== 0) &&
    rig.children.every((c) => c && c.texture && c.texture.label.indexOf('candidate-') !== 0);
  return {
    diag: diag,
    frozen: window.__oceanFrozen === true,
    headSprite: spriteInfo(head),
    overlays: overlays,
    faceState: faceState,
    candidateInjectionAbsent: candidateInjectionAbsent,
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
    repo_root: pathlib.Path, base_url: str, run_index: int
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
        "overlays": None,
        "faceState": None,
        "candidateInjectionAbsent": None,
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

            collected = pg.evaluate(COLLECT_SCRIPT)
            result["diag"] = collected["diag"]
            result["headSprite"] = collected["headSprite"]
            result["overlays"] = collected["overlays"]
            result["faceState"] = collected["faceState"]
            result["candidateInjectionAbsent"] = collected["candidateInjectionAbsent"]
            result["legacyBridgeVisible"] = collected["legacyBridgeVisible"]
            result["frozen"] = collected["frozen"]
            result["screenshotMeta"] = {
                "width": LOGICAL_VIEWPORT[0],
                "height": LOGICAL_VIEWPORT[1],
            }

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

            if context_png is not None:
                rgba, w, h = decode_png_to_rgba(context_png)
                result["context"] = {
                    "png": context_png,
                    "pixelSha256": sha256_bytes(rgba),
                    "fileSha256": sha256_bytes(context_png),
                    "width": w,
                    "height": h,
                }

            result["unhandledRejectionCount"] = len(collected.get("unhandled") or [])
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
    if diag.get("data-render-backend") != "webgl":
        reasons.append("renderer backend != webgl")
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
    if result.get("candidateInjectionAbsent") is not True:
        reasons.append("candidate texture injection detected in runtime")
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


def validate_face_state(name: str, state_result: dict[str, Any]) -> tuple[bool, list[str]]:
    expected = {s["name"]: s for s in FACE_STATES}[name]
    reasons = []
    rotation = state_result.get("headRotation")
    if rotation is not None and abs(float(rotation) - float(expected["rotation"])) > 1e-6:
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
    if head.get("textureLabel") != HEAD_TEXTURE_LABEL:
        reasons.append(
            "head texture label != otter.head: {}".format(head.get("textureLabel"))
        )
    if head.get("textureLabel", "").startswith("candidate-"):
        reasons.append("candidate texture label on head")
    tex_orig = head.get("textureOrig") or {}
    if (
        tex_orig.get("w") != SOURCE_LOGICAL_SIZE[0]
        or tex_orig.get("h") != SOURCE_LOGICAL_SIZE[1]
    ):
        reasons.append(
            "head texture orig {}x{} != 200x200".format(
                tex_orig.get("w"), tex_orig.get("h")
            )
        )
    if head.get("textureResolution") != 2:
        reasons.append("head texture resolution != 2")
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


def check_overlay_identities(result: dict) -> tuple[bool, list[str]]:
    reasons = []
    overlays = result.get("overlays") or {}
    for label, alias in OVERLAY_TEXTURE_ALIASES.items():
        info = overlays.get(label)
        if not info:
            reasons.append("overlay missing: {}".format(label))
            continue
        if info.get("textureLabel") != alias:
            reasons.append(
                "overlay {} texture label {} != {}".format(
                    label, info.get("textureLabel"), alias
                )
            )
        if info.get("label") != label:
            reasons.append("overlay {} sprite label mismatch".format(label))
        if info.get("textureResolution") != 2:
            reasons.append("overlay {} resolution != 2".format(label))
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
    for field in ("anchor", "textureFrame", "textureOrig", "textureResolution"):
        if (run1.get("headSprite") or {}).get(field) != (
            run2.get("headSprite") or {}
        ).get(field):
            reasons.append("headSprite.{} differs".format(field))
    if (run1.get("headSprite") or {}).get("textureLabel") != (
        run2.get("headSprite") or {}
    ).get("textureLabel"):
        reasons.append("headSprite texture differs")
    if (run1.get("headSprite") or {}).get("scaleX") != (
        run2.get("headSprite") or {}
    ).get("scaleX"):
        reasons.append("headSprite scale differs")
    if (run1.get("headSprite") or {}).get("scaleY") != (
        run2.get("headSprite") or {}
    ).get("scaleY"):
        reasons.append("headSprite scale differs")
    if run1.get("overlays") != run2.get("overlays"):
        reasons.append("overlay identities differ")
    if run1.get("candidateInjectionAbsent") != run2.get("candidateInjectionAbsent"):
        reasons.append("candidate-injection flag differs")
    if run1.get("frozen") != run2.get("frozen"):
        reasons.append("frozen marker differs")
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
    font = None
    for candidate in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ):
        if pathlib.Path(candidate).is_file():
            try:
                from PIL import ImageFont

                font = ImageFont.truetype(candidate, 16)
            except Exception:
                font = None
            if font is not None:
                break

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
    args,
    repo_root,
    output_dir,
    isolated,
    atlas_recon,
    runs,
    verdict,
    rejection_reasons,
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
                "candidateInjectionAbsent": r.get("candidateInjectionAbsent"),
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
    pre_manifest = resolve_path(repo_root, args.precanonical_manifest)
    canonical_svg = resolve_path(repo_root, args.canonical_svg)

    two_run_deterministic = False
    if len(runs) == 2:
        two_run_deterministic, _ = compare_runs(runs[0], runs[1])

    production_unchanged = _files_match_before_after(
        repo_root, PRODUCTION_FILES, getattr(args, "_production_before", None)
    )
    pre_evidence_unchanged = _files_match_before_after(
        repo_root,
        PRECANONICAL_EVIDENCE_FILES,
        getattr(args, "_pre_evidence_before", None),
    )

    head = (runs[0].get("headSprite") or {}) if runs else {}

    return {
        "schemaVersion": 1,
        "taskId": TASK_ID,
        "assetId": ASSET_ID,
        "alias": ALIAS,
        "sourceCommit": CANONICALIZATION_COMMIT,
        "canonicalizationCommit": CANONICALIZATION_COMMIT,
        "atlasRepairCommit": ATLAS_REPAIR_COMMIT,
        "humanApproval": HUMAN_APPROVAL,
        "approvedCandidateSha256": APPROVED_CANDIDATE_SHA,
        "structureReportPath": args.structure_report,
        "structureReportSha256": sha256_file(structure_report),
        "structureVerdict": (load_json(structure_report)).get("verdict"),
        "preCanonicalProofManifestPath": args.precanonical_manifest,
        "preCanonicalProofManifestSha256": sha256_file(pre_manifest),
        "preCanonicalProofVerdict": (load_json(pre_manifest)).get("verdict"),
        "canonicalSourcePath": args.canonical_svg,
        "canonicalSourceSha256": sha256_file(canonical_svg),
        "artPacketPath": ART_PACKET_PATH,
        "artPacketSha256": sha256_file(resolve_path(repo_root, ART_PACKET_PATH)),
        "artPacketAssetSourceSha256": _art_packet_source_sha256(repo_root),
        "artApprovalPath": ART_APPROVAL_PATH,
        "artApprovalSha256": sha256_file(resolve_path(repo_root, ART_APPROVAL_PATH)),
        "atlasManifestPath": ATLAS_MANIFEST_PATH,
        "atlasManifestSha256": sha256_file(
            resolve_path(repo_root, ATLAS_MANIFEST_PATH)
        ),
        "charactersAtlasJsonPath": CHARACTERS_ATLAS_JSON,
        "charactersAtlasJsonSha256": sha256_file(
            resolve_path(repo_root, CHARACTERS_ATLAS_JSON)
        ),
        "charactersAtlasPngPath": CHARACTERS_ATLAS_PNG,
        "charactersAtlasPngSha256": sha256_file(
            resolve_path(repo_root, CHARACTERS_ATLAS_PNG)
        ),
        "renderAssetsPath": RENDER_ASSETS_PATH,
        "renderAssetsSha256": sha256_file(resolve_path(repo_root, RENDER_ASSETS_PATH)),
        "singleHtmlPath": SINGLE_HTML_PATH,
        "singleHtmlSha256": sha256_file(resolve_path(repo_root, SINGLE_HTML_PATH)),
        "rasterizer": RASTERIZER,
        "rasterizerVersion": RASTERIZER_VERSION,
        "rendererBackend": (runs[0].get("diag") or {}).get("data-render-backend")
        if runs
        else None,
        "logicalViewport": LOGICAL_VIEWPORT,
        "deviceScaleFactor": DEVICE_SCALE_FACTOR,
        "sourceLogicalSize": SOURCE_LOGICAL_SIZE,
        "physicalRasterSize": PHYSICAL_RASTER_SIZE,
        "pivot": PIVOT,
        "runtimeScale": RUNTIME_SCALE,
        "isolated1x": isolated_entry(isolated["1x"], "isolated-1x.png"),
        "isolated2x": isolated_entry(isolated["2x"], "isolated-2x.png"),
        "atlasFrame": atlas_recon,
        "atlasReconstructionPixelSha256": atlas_recon["reconstructedPixelSha256"],
        "canonical2xPixelSha256": atlas_recon["canonical2xPixelSha256"],
        "atlasCanonicalPixelExact": atlas_recon["pixelExact"],
        "atlasMismatchPixelCount": atlas_recon["mismatchedPixels"],
        "atlasMismatchChannelCount": atlas_recon["mismatchedChannels"],
        "headSprite": head,
        "overlaySprites": (runs[0].get("overlays") or {}) if runs else {},
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
        "twoRunDeterministic": two_run_deterministic,
        "productionFilesUnchanged": production_unchanged,
        "preCanonicalEvidenceUnchanged": pre_evidence_unchanged,
        "verdict": verdict,
        "rejectionReasons": rejection_reasons,
    }


def _art_packet_source_sha256(repo_root: pathlib.Path) -> str:
    packet = load_json(resolve_path(repo_root, ART_PACKET_PATH))
    for asset in packet.get("assets", []):
        if asset.get("id") == ASSET_ID:
            return asset.get("sourceSha256", "")
    return ""


def _files_match_before_after(repo_root, rel_paths, before) -> bool:
    if before is None:
        return True
    for rel in rel_paths:
        if before.get(rel) != sha256_file(repo_root / rel):
            return False
    return True


def build_report(args, isolated, atlas_recon, runs, verdict, rejection_reasons) -> str:
    lines = []
    add = lines.append

    add("# Ocean Rescue — otter-head-01 Post-Canonical Render Proof")
    add("")
    add("- Task ID: `{}`".format(TASK_ID))
    add("- Verdict: `{}`".format(verdict))
    add("")
    add("## 1. Input lineage")
    add("")
    add("- Canonical SVG path: `{}`".format(args.canonical_svg))
    add("- Structure report path: `{}`".format(args.structure_report))
    add("- Pre-canonical proof manifest path: `{}`".format(args.precanonical_manifest))
    add("- Canonical source SHA-256: `{}`".format(APPROVED_CANDIDATE_SHA))
    add(
        "- Structure report SHA-256: `{}`".format(
            sha256_file(
                resolve_path(pathlib.Path(args.repo_root), args.structure_report)
            )
        )
    )
    add(
        "- Pre-canonical manifest SHA-256: `{}`".format(
            sha256_file(
                resolve_path(pathlib.Path(args.repo_root), args.precanonical_manifest)
            )
        )
    )
    add("")
    add("## 2. Human approval binding")
    add("")
    add("- Decision: `{}`".format(HUMAN_APPROVAL["decision"]))
    add("- Date: `{}`".format(HUMAN_APPROVAL["date"]))
    add("- Input: `{}`".format(HUMAN_APPROVAL["input"]))
    add("- Approved candidate SHA-256: `{}`".format(APPROVED_CANDIDATE_SHA))
    add("- Approved proof task: `{}`".format(HUMAN_APPROVAL["approvedProofTaskId"]))
    add("")
    add("## 3. Atlas repair predecessor")
    add("")
    add("- Atlas repair commit: `{}`".format(ATLAS_REPAIR_COMMIT))
    add(
        "- Repair ancestry of HEAD: `{}`".format(
            "PASS" if check_repair_ancestry(pathlib.Path(args.repo_root)) else "FAIL"
        )
    )
    add(
        "- Unmasked production paste `page_img.paste(trimmed_img, (content_x, content_y))`"
    )
    add("")
    add("## 4. Canonical source and packet binding")
    add("")
    add("- Canonical source SHA-256: `{}`".format(APPROVED_CANDIDATE_SHA))
    add(
        "- Art packet SHA-256: `{}`".format(
            sha256_file(resolve_path(pathlib.Path(args.repo_root), ART_PACKET_PATH))
        )
    )
    add(
        "- Art packet asset sourceSha256: `{}`".format(
            _art_packet_source_sha256(pathlib.Path(args.repo_root))
        )
    )
    add(
        "- Art approval SHA-256: `{}`".format(
            sha256_file(resolve_path(pathlib.Path(args.repo_root), ART_APPROVAL_PATH))
        )
    )
    add(
        "- Atlas manifest SHA-256: `{}`".format(
            sha256_file(resolve_path(pathlib.Path(args.repo_root), ATLAS_MANIFEST_PATH))
        )
    )
    add("")
    add("## 5. Canonical isolated render")
    add("")
    for name, analysis in (("1x", isolated["1x"]), ("2x", isolated["2x"])):
        ok, reasons = check_isolated_approved(analysis)
        add(
            "- Isolated {}: {}x{} pixel SHA `{}`".format(
                name,
                analysis["width"],
                analysis["height"],
                analysis["pixelSha256"],
            )
        )
        add(
            "  - Approved pixel SHA: `{}`".format(
                APPROVED_1X_PIXEL_SHA if name == "1x" else APPROVED_2X_PIXEL_SHA
            )
        )
        add("  - Visible alpha bounds: {}".format(analysis["visibleAlphaBounds"]))
        add("  - Check verdict: {}".format("PASS" if ok else "FAIL"))
        if reasons:
            for reason in reasons:
                add("  - REJECT: {}".format(reason))
    add("")
    add("## 6. Atlas-frame RGBA reconstruction")
    add("")
    add("- Frame: {}".format(atlas_recon["frame"]))
    add("- sourceSize: {}".format(atlas_recon["sourceSize"]))
    add("- spriteSourceSize: {}".format(atlas_recon["spriteSourceSize"]))
    add("- rotated: {}".format(atlas_recon["rotated"]))
    add("- trimmed: {}".format(atlas_recon["trimmed"]))
    add("- Reconstructed size: {}".format(atlas_recon["reconstructedSize"]))
    add(
        "- Reconstructed pixel SHA-256: `{}`".format(
            atlas_recon["reconstructedPixelSha256"]
        )
    )
    add(
        "- Canonical 2x pixel SHA-256: `{}`".format(
            atlas_recon["canonical2xPixelSha256"]
        )
    )
    add("- Mismatched pixels: {}".format(atlas_recon["mismatchedPixels"]))
    add("- Mismatched channels: {}".format(atlas_recon["mismatchedChannels"]))
    add("- Byte-exact: `{}`".format("PASS" if atlas_recon["pixelExact"] else "FAIL"))
    add("")
    add("## 7. Production runtime texture identity")
    add("")
    for r in runs:
        head = r.get("headSprite") or {}
        add(
            "- Run {}: head sprite `{}` texture `{}` backend={}".format(
                r["runIndex"],
                head.get("label"),
                head.get("textureLabel"),
                (r.get("diag") or {}).get("data-render-backend"),
            )
        )
        add(
            "  - Texture orig {}x{} resolution {}".format(
                (head.get("textureOrig") or {}).get("w"),
                (head.get("textureOrig") or {}).get("h"),
                head.get("textureResolution"),
            )
        )
        add(
            "  - Position ({}, {}) scale {}x{} anchor {}".format(
                head.get("x"),
                head.get("y"),
                head.get("scaleX"),
                head.get("scaleY"),
                head.get("anchor"),
            )
        )
        add(
            "  - Candidate injection absent: {}".format(
                "PASS" if r.get("candidateInjectionAbsent") else "FAIL"
            )
        )
        add(
            "  - Overlay texture identities: {}".format(
                "PASS" if check_overlay_identities(r)[0] else "FAIL"
            )
        )
        add("  - Frozen at deterministic t=0: {}".format(r.get("frozen")))
    add("")
    add("## 8. Face-state assembly")
    add("")
    for name in ("base-only", "neutral", "concern", "smile"):
        ok = True
        reasons = []
        for r in runs:
            s = (r.get("states") or {}).get(name) or {}
            ok_, reasons_ = validate_face_state(name, s.get("stateResult") or {})
            if not ok_:
                ok = False
                reasons.extend(reasons_)
        add("- `{}`: {}".format(name, "PASS" if ok else "FAIL {}".format(reasons)))
    add("- Contact sheet: `face-rig-contact-sheet.png`")
    add("- Full context: `sea-turtle-context.png`")
    add("")
    add("## 9. Two-run determinism")
    add("")
    if len(runs) == 2:
        ok, reasons = compare_runs(runs[0], runs[1])
        add("- Two-run deterministic: {}".format("PASS" if ok else "FAIL"))
        if reasons:
            for reason in reasons:
                add("  - {}".format(reason))
    add("")
    add("## 10. Error and network findings")
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
    add("## 11. Production/evidence immutability")
    add("")
    add(
        "- Production files byte-unchanged: `{}`".format(
            _files_match_before_after(
                pathlib.Path(args.repo_root),
                PRODUCTION_FILES,
                getattr(args, "_production_before", None),
            )
        )
    )
    add(
        "- Pre-canonical evidence byte-unchanged: `{}`".format(
            _files_match_before_after(
                pathlib.Path(args.repo_root),
                PRECANONICAL_EVIDENCE_FILES,
                getattr(args, "_pre_evidence_before", None),
            )
        )
    )
    add("")
    add("## 12. Final verdict")
    add("")
    add("`{}`".format(verdict))
    if rejection_reasons:
        for reason in rejection_reasons:
            add("- {}".format(reason))
    add("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Otter head post-canonical render proof harness."
    )
    parser.add_argument("--canonical-svg", required=True)
    parser.add_argument("--structure-report", required=True)
    parser.add_argument("--precanonical-manifest", required=True)
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

    # ---- Byte guard for production files + pre-canonical evidence ----
    before = {p: sha256_file(repo_root / p) for p in PRODUCTION_FILES}
    pre_before = {p: sha256_file(repo_root / p) for p in PRECANONICAL_EVIDENCE_FILES}
    args._production_before = before
    args._pre_evidence_before = pre_before

    svg_path = resolve_path(repo_root, args.canonical_svg)
    svg_sha_before = sha256_file(svg_path)

    # ---- Isolated render ----
    output_dir.mkdir(parents=True, exist_ok=True)
    isolated = {}
    for name, w, h in (("1x", 200, 200), ("2x", 400, 400)):
        png_bytes = render_svg_to_png(svg_path, w, h)
        analysis = analyze_isolated_png(png_bytes, w, h)
        isolated[name] = analysis
        dst = output_dir / ("isolated-1x.png" if name == "1x" else "isolated-2x.png")
        dst.write_bytes(png_bytes)

    isolated_ok = all(check_isolated_approved(a)[0] for a in isolated.values())
    isolated_reasons = []
    for name, a in isolated.items():
        ok_, reasons = check_isolated_approved(a)
        if not ok_:
            isolated_reasons.extend("{}: {}".format(name, r) for r in reasons)

    # ---- Atlas frame RGBA reconstruction ----
    atlas_recon = reconstruct_atlas_frame(repo_root)
    atlas_ok, atlas_reasons = check_atlas_reconstruction(atlas_recon)

    # ---- In-context capture (two runs, no candidate injection) ----
    port = find_free_port()
    server = start_server(repo_root, port)
    base_url = "http://127.0.0.1:{}".format(port)
    runs = []
    try:
        for run_index in (1, 2):
            r = run_in_context_capture(repo_root, base_url, run_index)
            if r.get("blocked"):
                print("BLOCKED: {}".format(r["blocked"]), file=sys.stderr)
                return 2
            runs.append(r)
    finally:
        server.shutdown()
        server.server_close()

    capture_ok = all(check_capture_state(r)[0] for r in runs)
    head_ok = all(check_head_sprite(r)[0] for r in runs)
    overlay_ok = all(check_overlay_identities(r)[0] for r in runs)
    face_ok = True
    for r in runs:
        for name in ("base-only", "neutral", "concern", "smile"):
            s = (r.get("states") or {}).get(name) or {}
            ok_, _ = validate_face_state(name, s.get("stateResult") or {})
            if not ok_:
                face_ok = False
    determinism_ok, determinism_reasons = (
        compare_runs(runs[0], runs[1]) if len(runs) == 2 else (False, ["missing runs"])
    )

    rejection_reasons = []
    if not isolated_ok:
        rejection_reasons.extend(isolated_reasons)
    if not atlas_ok:
        rejection_reasons.extend("atlas: {}".format(x) for x in atlas_reasons)
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
    if not overlay_ok:
        for r in runs:
            _, reasons = check_overlay_identities(r)
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
    if not determinism_ok:
        rejection_reasons.extend(
            "determinism: {}".format(x) for x in determinism_reasons
        )

    if rejection_reasons:
        verdict = "POST_CANONICAL_RENDER_REJECTED"
    else:
        verdict = "POST_CANONICAL_RENDER_PROOF_READY"

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
        args,
        repo_root,
        output_dir,
        isolated,
        atlas_recon,
        runs,
        verdict,
        rejection_reasons,
    )
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    report = build_report(args, isolated, atlas_recon, runs, verdict, rejection_reasons)
    (output_dir / "render-proof-report.md").write_text(report, encoding="utf-8")

    # ---- Byte guard ----
    after = {p: sha256_file(repo_root / p) for p in PRODUCTION_FILES}
    if before != after:
        print("BLOCKED: PRODUCTION_FILES_MUTATED_DURING_PROOF", file=sys.stderr)
        return 2
    pre_after = {p: sha256_file(repo_root / p) for p in PRECANONICAL_EVIDENCE_FILES}
    if pre_before != pre_after:
        print("BLOCKED: PRECANONICAL_EVIDENCE_MUTATED_DURING_PROOF", file=sys.stderr)
        return 2
    if sha256_file(svg_path) != svg_sha_before:
        print("BLOCKED: CANONICAL_SVG_MUTATED_DURING_PROOF", file=sys.stderr)
        return 2

    print("POST_CANONICAL_RENDER_PROOF verdict: {}".format(verdict))
    for reason in rejection_reasons:
        print("REJECT: {}".format(reason), file=sys.stderr)
    return 0 if verdict == "POST_CANONICAL_RENDER_PROOF_READY" else 1


if __name__ == "__main__":
    sys.exit(main())
