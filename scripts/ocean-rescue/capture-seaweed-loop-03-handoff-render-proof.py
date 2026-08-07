#!/usr/bin/env python3
"""Isolated and in-context render proof harness for scene-seaweed-loop-03 handoff (B23).

Generates deterministic 1x (120x200), 2x (240x400) isolated PNG renders and
an in-context sea-turtle rescue diorama proof for human review.
Does NOT modify any production source files or update approval receipts.

Exit codes:
    0  RENDER_PROOF_READY
    1  RENDER_REJECTED
    2  BLOCKED
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys

from PIL import Image, ImageDraw

try:
    import cairosvg
except ImportError:
    cairosvg = None

TASK_ID = "AIDENGAME-OCEAN-RESCUE-SEAWEED-LOOP-03-HANDOFF-RENDER-PROOF"
ASSET_ID = "scene-seaweed-loop-03-01"
ALIAS = "scene.seaweed-loop.03"

LOGICAL_SIZE = (120, 200)

CAIRO_LIB_PATHS = ("/opt/homebrew/opt/cairo/lib", "/opt/homebrew/lib")
if sys.platform == "darwin":
    current_dyld = os.environ.get("DYLD_LIBRARY_PATH", "")
    new_paths = [p for p in CAIRO_LIB_PATHS if os.path.exists(p)]
    if new_paths:
        os.environ["DYLD_LIBRARY_PATH"] = ":".join(new_paths + ([current_dyld] if current_dyld else []))

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
INBOX_SVG = REPO_ROOT / "domains/ocean-rescue/assets/handoff/inbox/scene-seaweed-loop-03-01.svg"
BRIEF_MD = REPO_ROOT / "domains/ocean-rescue/assets/handoff/briefs/scene-seaweed-loop-03-01.md"
PROOF_DIR = REPO_ROOT / "domains/ocean-rescue/assets/review/proof-seaweed-loop-03-handoff"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def render_svg_to_png(svg_bytes: bytes, scale: float) -> Image.Image:
    if cairosvg is None:
        raise RuntimeError("CairoSVG is not installed")
    w = int(round(LOGICAL_SIZE[0] * scale))
    h = int(round(LOGICAL_SIZE[1] * scale))
    png_data = cairosvg.svg2png(bytestring=svg_bytes, output_width=w, output_height=h)
    img = Image.open(pathlib.io.BytesIO(png_data)).convert("RGBA")
    if img.size != (w, h):
        raise ValueError(f"Rendered image size {img.size} mismatch expected {(w, h)}")
    return img


def create_in_context_diorama(loop_img_2x: Image.Image) -> Image.Image:
    canvas = Image.new("RGBA", (1280, 720), (12, 44, 76, 255))
    draw = ImageDraw.Draw(canvas)
    
    draw.rectangle([0, 0, 1280, 720], fill=(16, 58, 96, 255))
    draw.polygon([(0, 480), (1280, 520), (1280, 720), (0, 720)], fill=(10, 36, 62, 255))
    draw.polygon([(0, 600), (1280, 580), (1280, 720), (0, 720)], fill=(34, 74, 94, 255))

    target_w = int(LOGICAL_SIZE[0] * 1.5)
    target_h = int(LOGICAL_SIZE[1] * 1.5)
    resized_loop = loop_img_2x.resize((target_w, target_h), Image.Resampling.LANCZOS)

    # Position: Seaweed loop 03 rescue site placement
    canvas.alpha_composite(resized_loop, (820, 310))

    small_loop = loop_img_2x.resize((int(LOGICAL_SIZE[0] * 0.9), int(LOGICAL_SIZE[1] * 0.9)), Image.Resampling.LANCZOS)
    canvas.alpha_composite(small_loop, (220, 440))

    draw.text((20, 20), "Ocean Rescue — Seaweed Loop 03 In-Context Proof", fill=(255, 255, 255, 230))
    draw.text((20, 45), f"Asset ID: {ASSET_ID} | Alias: {ALIAS}", fill=(180, 220, 240, 200))
    draw.rectangle([815, 305, 825 + target_w, 315 + target_h], outline=(74, 184, 106, 220), width=2)
    draw.text((820, 290), "Candidate obstacle 03 placement", fill=(74, 184, 106, 240))

    return canvas


def build_proof() -> int:
    if not INBOX_SVG.exists():
        print(f"BLOCKED: Inbox SVG absent at {INBOX_SVG}")
        return 2

    svg_bytes = INBOX_SVG.read_bytes()
    svg_hash = sha256_bytes(svg_bytes)

    PROOF_DIR.mkdir(parents=True, exist_ok=True)

    img_1x = render_svg_to_png(svg_bytes, 1.0)
    img_2x = render_svg_to_png(svg_bytes, 2.0)

    bbox_1x = img_1x.getbbox()
    if bbox_1x is None:
        print("RENDER_REJECTED: 1x isolated image is completely blank")
        return 1

    path_1x = PROOF_DIR / "isolated-1x.png"
    path_2x = PROOF_DIR / "isolated-2x.png"
    path_ctx = PROOF_DIR / "in-context-proof.png"

    img_1x.save(path_1x)
    img_2x.save(path_2x)

    diorama_img = create_in_context_diorama(img_2x)
    diorama_img.save(path_ctx)

    manifest = {
        "taskId": TASK_ID,
        "assetId": ASSET_ID,
        "alias": ALIAS,
        "svgHash": svg_hash,
        "logicalSize": list(LOGICAL_SIZE),
        "proofs": {
            "isolated1x": {
                "file": "isolated-1x.png",
                "dimensions": list(img_1x.size),
                "sha256": sha256_bytes(path_1x.read_bytes()),
            },
            "isolated2x": {
                "file": "isolated-2x.png",
                "dimensions": list(img_2x.size),
                "sha256": sha256_bytes(path_2x.read_bytes()),
            },
            "inContextProof": {
                "file": "in-context-proof.png",
                "dimensions": list(diorama_img.size),
                "sha256": sha256_bytes(path_ctx.read_bytes()),
            },
        },
    }

    manifest_path = PROOF_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    report_md = f"""# Seaweed Loop 03 Render Proof Report

- Asset ID: `{ASSET_ID}`
- Alias: `{ALIAS}`
- SVG Hash: `{svg_hash}`
- Proof Status: `RENDER_PROOF_READY`

## Generated Proof Artifacts

- **Isolated 1x**: `isolated-1x.png` ({img_1x.size[0]}x{img_1x.size[1]})
- **Isolated 2x**: `isolated-2x.png` ({img_2x.size[0]}x{img_2x.size[1]})
- **In-Context Proof**: `in-context-proof.png` ({diorama_img.size[0]}x{diorama_img.size[1]})
"""
    (PROOF_DIR / "render-proof-report.md").write_text(report_md, encoding="utf-8")

    print(f"RENDER_PROOF_READY asset_id={ASSET_ID} svg_hash={svg_hash[:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(build_proof())
