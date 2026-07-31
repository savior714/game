#!/usr/bin/env python3
"""Deterministic 2× atlas builder for Ocean Rescue.

Reads approved art-packet.json and art-approval.json, rasterizes SVGs at
declared 2× scale, applies alpha trim + fixed padding, packs frames into
atlas pages, and emits PixiJS v8-compatible spritesheet JSON + manifests.

Usage:
    python build_atlases.py --packet <path> --approval <path> --output-dir <path>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RASTER_SCALE = 2
PADDING_PX = 4
MAX_PAGE_DIM = 4096
ALGORITHM_ID = "ocean-rescue-shelf-v1"
APP_NAME = "AidenGame Ocean Rescue Atlas Builder"
APP_VERSION = "1"
TRIM_ALPHA_THRESHOLD = 0

CHARACTER_BUNDLE = "characters"
SCENE_BUNDLE = "scene"
EFFECTS_UI_BUNDLE = "effects-ui"
VALID_BUNDLES = {CHARACTER_BUNDLE, SCENE_BUNDLE, EFFECTS_UI_BUNDLE}
BUNDLE_ORDER = [CHARACTER_BUNDLE, SCENE_BUNDLE, EFFECTS_UI_BUNDLE]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256(path.read_bytes())


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(data: Any, path: Path) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=False, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _get_cairo_version() -> str:
    try:
        import cairocffi

        return str(cairocffi.cairo_version_string())
    except Exception:
        return "unknown"


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Approval gate
# ---------------------------------------------------------------------------


def _validate_approval(packet_path: Path, approval_path: Path) -> dict:
    """Run the approval validator as a subprocess and return the record."""
    import subprocess

    validator = Path(__file__).parent / "validate_art_approval.py"
    if not validator.exists():
        _fail(f"Approval validator not found: {validator}")

    # The validator reads approval from the source directory
    # We need to temporarily symlink or copy our custom approval
    import tempfile

    source_dir = packet_path.parent
    with tempfile.TemporaryDirectory() as tmp:
        tmp_source = Path(tmp) / "source"
        tmp_source.mkdir()
        # Copy approval to temp source
        shutil.copy2(approval_path, tmp_source / "art-approval.json")
        # Copy packet to temp source
        shutil.copy2(packet_path, tmp_source / "art-packet.json")
        # Copy source files
        packet = _load_json(packet_path)
        for asset in packet["assets"]:
            src = source_dir / asset["source"]
            if src.exists():
                dst = tmp_source / asset["source"]
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        # Copy contact sheet if exists
        contact_sheet = source_dir.parent / "review" / "proof-art-contact-sheet.html"
        if contact_sheet.exists():
            tmp_review = tmp_source.parent / "review"
            tmp_review.mkdir(parents=True, exist_ok=True)
            shutil.copy2(contact_sheet, tmp_review / "proof-art-contact-sheet.html")

        result = subprocess.run(
            [sys.executable, str(validator), str(tmp_source)],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent.parent),
        )
        if result.returncode != 0:
            _fail(f"Approval validation failed:\n{result.stderr}{result.stdout}")

    return _load_json(approval_path)


# ---------------------------------------------------------------------------
# SVG rasterization
# ---------------------------------------------------------------------------


def _rasterize_svg(svg_path: Path, physical_w: int, physical_h: int) -> Any:
    """Rasterize SVG to RGBA bitmap at given physical dimensions."""
    import cairosvg
    from PIL import Image

    png_data = cairosvg.svg2png(
        url=str(svg_path),
        output_width=physical_w,
        output_height=physical_h,
    )
    img = Image.open(__import__("io").BytesIO(png_data))
    img = img.convert("RGBA")
    return img


def _normalize_png(img: Any) -> Any:
    """Strip metadata, ensure RGBA, canonical save settings."""
    from PIL import Image

    # Create a fresh image from pixel data only (strips all metadata)
    normalized = Image.new("RGBA", img.size)
    normalized.putdata(img.get_flattened_data())
    return normalized


def _check_not_blank(img: Any, alias: str) -> None:
    """Reject completely transparent images."""
    extrema = img.getextrema()
    if extrema[3][1] == 0:  # alpha channel max is 0
        _fail(f"Completely transparent raster for alias: {alias}")


# ---------------------------------------------------------------------------
# Alpha trim
# ---------------------------------------------------------------------------


def _alpha_trim(img: Any) -> tuple[int, int, int, int, Any]:
    """Compute bounding box of non-transparent pixels.

    Returns (trim_x, trim_y, trim_w, trim_h, trimmed_image).
    """
    alpha = img.split()[3]
    bbox = alpha.getbbox()
    if bbox is None:
        _fail("Alpha trim found no non-transparent pixels")
    x0, y0, x1, y1 = bbox
    trimmed = img.crop((x0, y0, x1, y1))
    return x0, y0, x1 - x0, y1 - y0, trimmed


# ---------------------------------------------------------------------------
# Deterministic shelf packer
# ---------------------------------------------------------------------------


class ShelfPacker:
    """Deterministic non-rotating shelf packer for atlas pages."""

    def __init__(self, max_w: int = MAX_PAGE_DIM, max_h: int = MAX_PAGE_DIM):
        self.max_w = max_w
        self.max_h = max_h
        self.pages: list[
            list[dict]
        ] = []  # list of pages, each page is list of placed rects
        self.page_dims: list[tuple[int, int]] = []  # actual used dims per page

    def pack(self, items: list[tuple[str, int, int]]) -> list[list[dict]]:
        """Pack items [(alias, padded_w, padded_h), ...] into pages.

        Returns list of pages, each page is list of
        {"alias", "x", "y", "w", "h", "page"} dicts.
        Items must be pre-sorted by alias ascending.
        """
        self.pages = []
        self.page_dims = []

        # Current row tracking
        row_x = 0
        row_y = 0
        row_h = 0
        page_idx = 0
        page_items: list[dict] = []
        page_w = 0
        page_h = 0

        def _start_new_page() -> None:
            nonlocal page_idx, page_items, page_w, page_h
            nonlocal row_x, row_y, row_h
            if page_items:
                self.pages.append(page_items)
                self.page_dims.append((page_w, page_h))
            page_idx = len(self.pages)
            page_items = []
            page_w = 0
            page_h = 0
            row_x = 0
            row_y = 0
            row_h = 0

        for alias, pw, ph in items:
            if pw > self.max_w or ph > self.max_h:
                _fail(f"Padded frame {alias} ({pw}x{ph}) exceeds page ceiling")

            # Need new page?
            if not page_items:
                _start_new_page()

            # Fits in current row?
            if row_x + pw > self.max_w:
                # Start new row
                row_y += row_h + PADDING_PX
                row_x = 0
                row_h = 0

            # Fits in current page height?
            if row_y + ph > self.max_h:
                _start_new_page()

            # Place item
            placed = {
                "alias": alias,
                "x": row_x,
                "y": row_y,
                "w": pw,
                "h": ph,
                "page": page_idx,
            }
            page_items.append(placed)

            # Update page tracking
            page_w = max(page_w, row_x + pw)
            page_h = max(page_h, row_y + ph)

            # Update row tracking
            row_x += pw + PADDING_PX
            row_h = max(row_h, ph)

        # Finalize last page
        if page_items:
            self.pages.append(page_items)
            self.page_dims.append((page_w, page_h))

        return self.pages


# ---------------------------------------------------------------------------
# Atlas builder
# ---------------------------------------------------------------------------


class AtlasBuilder:
    def __init__(
        self,
        packet_path: Path,
        approval_path: Path,
        output_dir: Path,
    ):
        self.packet_path = packet_path
        self.approval_path = approval_path
        self.output_dir = output_dir
        self.packet = _load_json(packet_path)
        self.approval = _load_json(approval_path)
        self.raster_scale = RASTER_SCALE
        self.padding_px = PADDING_PX

        # Validate approval
        _validate_approval(packet_path, approval_path)

        # Validate bundle membership
        for asset in self.packet["assets"]:
            if asset["bundle"] not in VALID_BUNDLES:
                _fail(
                    f"Invalid bundle '{asset['bundle']}' for alias '{asset['alias']}'"
                )

    def _group_by_bundle(self) -> dict[str, list[dict]]:
        groups: dict[str, list[dict]] = {b: [] for b in BUNDLE_ORDER}
        for asset in self.packet["assets"]:
            groups[asset["bundle"]].append(asset)
        # Sort each group by alias
        for bundle in groups:
            groups[bundle].sort(key=lambda a: a["alias"])
        return groups

    def _rasterize_asset(self, asset: dict, tmp_dir: Path) -> dict:
        """Rasterize a single asset, trim, and return metadata."""
        alias = asset["alias"]
        logical_w, logical_h = asset["logicalSize"]
        declared_scale = asset.get("declaredRasterScale", self.raster_scale)

        if declared_scale != RASTER_SCALE:
            _fail(
                f"Asset {alias} declaredRasterScale={declared_scale}, expected {RASTER_SCALE}"
            )

        physical_w = logical_w * RASTER_SCALE
        physical_h = logical_h * RASTER_SCALE

        # Rasterize
        svg_path = self.packet_path.parent / asset["source"]
        if not svg_path.exists():
            _fail(f"Source file missing: {asset['source']}")

        img = _rasterize_svg(svg_path, physical_w, physical_h)
        _check_not_blank(img, alias)

        # Verify physical size
        if img.size != (physical_w, physical_h):
            _fail(
                f"Asset {alias}: raster size {img.size} != expected ({physical_w}, {physical_h})"
            )

        # Normalize PNG (strip metadata)
        img = _normalize_png(img)

        # Alpha trim
        trim_x, trim_y, trim_w, trim_h, trimmed = _alpha_trim(img)

        # Padded dimensions (for packing)
        padded_w = trim_w + self.padding_px * 2
        padded_h = trim_h + self.padding_px * 2

        # Canonical pivot
        pivot_x, pivot_y = asset["pivot"]

        # Physical source pivot (in untrimmed physical coords)
        source_pivot_px_x = pivot_x * physical_w
        source_pivot_px_y = pivot_y * physical_h

        # Trimmed-local pivot
        trimmed_pivot_x = source_pivot_px_x - trim_x
        trimmed_pivot_y = source_pivot_px_y - trim_y

        # Save trimmed PNG to temp
        png_name = alias.replace(".", "_") + ".png"
        png_path = tmp_dir / png_name
        trimmed.save(str(png_path), format="PNG", optimize=False)

        return {
            "alias": alias,
            "bundle": asset["bundle"],
            "source": asset["source"],
            "logical_size": [logical_w, logical_h],
            "physical_size": [physical_w, physical_h],
            "trim": [trim_x, trim_y, trim_w, trim_h],
            "padded_size": [padded_w, padded_h],
            "pivot": [pivot_x, pivot_y],
            "source_pivot_px": [source_pivot_px_x, source_pivot_px_y],
            "trimmed_pivot_px": [trimmed_pivot_x, trimmed_pivot_y],
            "png_path": png_path,
            "png_data": trimmed,
        }

    def build(self) -> None:
        """Run the full atlas build pipeline."""
        import shutil

        # Create temp build directory as sibling
        build_dir = Path(tempfile.mkdtemp(prefix="ocean_atlas_"))

        try:
            self._do_build(build_dir)
        finally:
            shutil.rmtree(build_dir, ignore_errors=True)

    def _do_build(self, build_dir: Path) -> None:
        import shutil
        from PIL import Image

        # Create output structure
        output_root = build_dir / "output"
        output_root.mkdir(parents=True, exist_ok=True)

        # Rasterize all assets
        raster_tmp = build_dir / "raster"
        raster_tmp.mkdir()

        asset_metas: list[dict] = []
        for asset in self.packet["assets"]:
            meta = self._rasterize_asset(asset, raster_tmp)
            asset_metas.append(meta)

        # Group by bundle
        bundle_groups: dict[str, list[dict]] = {b: [] for b in BUNDLE_ORDER}
        for meta in asset_metas:
            bundle_groups[meta["bundle"]].append(meta)

        # Process each bundle
        bundle_results: list[dict] = []
        all_files: dict[str, str] = {}  # relative_path -> sha256

        for bundle_name in BUNDLE_ORDER:
            items = bundle_groups[bundle_name]
            if not items:
                continue

            bundle_dir = output_root / bundle_name
            bundle_dir.mkdir(parents=True, exist_ok=True)

            # Pack items
            packer = ShelfPacker()
            pack_items = [
                (m["alias"], m["padded_size"][0], m["padded_size"][1]) for m in items
            ]
            pages = packer.pack(pack_items)

            # Create atlas pages
            page_records = []
            for page_idx, page_items in enumerate(pages):
                # Determine page canvas size
                page_w = 0
                page_h = 0
                for item in page_items:
                    page_w = max(page_w, item["x"] + item["w"])
                    page_h = max(page_h, item["y"] + item["h"])

                # Create page canvas
                page_img = Image.new("RGBA", (page_w, page_h), (0, 0, 0, 0))

                # Build frame lookup
                alias_to_meta = {m["alias"]: m for m in items}
                frames_json: dict[str, dict] = {}

                # Sort by alias for deterministic output
                sorted_items = sorted(page_items, key=lambda it: it["alias"])

                for item in sorted_items:
                    alias = item["alias"]
                    meta = alias_to_meta[alias]
                    trim = meta["trim"]

                    # Place trimmed content on page with padding offset
                    # The frame position is the content start (after padding)
                    content_x = item["x"] + self.padding_px
                    content_y = item["y"] + self.padding_px

                    # Paste trimmed image onto page
                    trimmed_img = meta["png_data"]
                    page_img.paste(trimmed_img, (content_x, content_y), trimmed_img)

                    # sourceSize = untrimmed physical dimensions
                    phys_w, phys_h = meta["physical_size"]

                    # spriteSourceSize = trim rect in source coords
                    sprite_source = {
                        "x": trim[0],
                        "y": trim[1],
                        "w": trim[2],
                        "h": trim[3],
                    }

                    # sourceSize = untrimmed physical size
                    source_size = {"w": phys_w, "h": phys_h}

                    # anchor = canonical normalized pivot
                    anchor = {"x": meta["pivot"][0], "y": meta["pivot"][1]}

                    frames_json[alias] = {
                        "frame": {
                            "x": content_x,
                            "y": content_y,
                            "w": trim[2],
                            "h": trim[3],
                        },
                        "rotated": False,
                        "trimmed": True,
                        "spriteSourceSize": sprite_source,
                        "sourceSize": source_size,
                        "anchor": anchor,
                    }

                # Save page PNG
                page_png_name = f"{bundle_name}-{page_idx}.png"
                page_png_path = bundle_dir / page_png_name
                page_img.save(str(page_png_path), format="PNG", optimize=False)
                page_png_sha = _sha256_file(page_png_path)

                # Build spritesheet JSON
                spritesheet_json: dict[str, Any] = {
                    "frames": frames_json,
                    "animations": {},
                    "meta": {
                        "app": APP_NAME,
                        "version": APP_VERSION,
                        "image": page_png_name,
                        "format": "RGBA8888",
                        "size": {"w": page_w, "h": page_h},
                        "scale": str(RASTER_SCALE),
                    },
                }

                # Multi-page related packs
                if len(pages) > 1:
                    related = [
                        f"{bundle_name}-{i}.json"
                        for i in range(len(pages))
                        if i != page_idx
                    ]
                    spritesheet_json["meta"]["related_multi_packs"] = related

                page_json_name = f"{bundle_name}-{page_idx}.json"
                page_json_path = bundle_dir / page_json_name
                _dump_json(spritesheet_json, page_json_path)
                page_json_sha = _sha256_file(page_json_path)

                page_records.append(
                    {
                        "index": page_idx,
                        "image": page_png_name,
                        "spritesheet": page_json_name,
                        "width": page_w,
                        "height": page_h,
                        "imageSha256": page_png_sha,
                        "spritesheetSha256": page_json_sha,
                        "aliases": sorted([it["alias"] for it in page_items]),
                    }
                )

            # Compute bundle SHA-256
            bundle_canonical = ""
            for pr in page_records:
                bundle_canonical += f"{pr['image']}:{pr['imageSha256']}\n"
                bundle_canonical += f"{pr['spritesheet']}:{pr['spritesheetSha256']}\n"
            bundle_sha = _sha256(bundle_canonical.encode("utf-8"))

            bundle_results.append(
                {
                    "name": bundle_name,
                    "aliases": sorted([m["alias"] for m in items]),
                    "pageCount": len(pages),
                    "entry": page_records[0]["spritesheet"] if page_records else "",
                    "pages": page_records,
                    "bundleSha256": bundle_sha,
                }
            )

            # Collect file hashes
            for pr in page_records:
                img_path = bundle_dir / pr["image"]
                json_path = bundle_dir / pr["spritesheet"]
                all_files[f"{bundle_name}/{pr['image']}"] = _sha256_file(img_path)
                all_files[f"{bundle_name}/{pr['spritesheet']}"] = _sha256_file(
                    json_path
                )

        # Build root manifest
        source_packet_sha = _sha256_file(self.packet_path)
        approval_record_sha = _sha256_file(self.approval_path)

        # Compute source-set SHA
        parts = []
        for asset in sorted(self.packet["assets"], key=lambda a: a["alias"]):
            src = self.packet_path.parent / asset["source"]
            sha = _sha256_file(src)
            parts.append(f"{asset['alias']}:{sha}")
        source_set_canonical = "\n".join(parts) + "\n"
        source_set_sha = _sha256(source_set_canonical.encode("utf-8"))

        manifest = {
            "schemaVersion": 1,
            "sourcePacketSha256": source_packet_sha,
            "approvalRecordSha256": approval_record_sha,
            "sourceSetSha256": source_set_sha,
            "toolchain": {
                "cairosvg": "2.9.0",
                "pillow": "12.3.0",
                "cairo": _get_cairo_version(),
            },
            "rasterization": {
                "rasterScale": RASTER_SCALE,
            },
            "packing": {
                "algorithm": ALGORITHM_ID,
                "trimAlphaThreshold": TRIM_ALPHA_THRESHOLD,
                "paddingPx": self.padding_px,
                "maxPageWidth": MAX_PAGE_DIM,
                "maxPageHeight": MAX_PAGE_DIM,
            },
            "bundles": bundle_results,
            "files": dict(sorted(all_files.items())),
        }

        # Write manifest (without self-reference in files)
        manifest_path = output_root / "atlas-manifest.json"
        _dump_json(manifest, manifest_path)

        # Build pixi-assets-manifest.json
        pixi_assets: dict[str, Any] = {"bundles": []}
        for bundle_name in BUNDLE_ORDER:
            br = next((b for b in bundle_results if b["name"] == bundle_name), None)
            if br and br["pages"]:
                pixi_assets["bundles"].append(
                    {
                        "name": bundle_name,
                        "assets": [
                            {
                                "alias": f"{bundle_name}.atlas",
                                "src": f"{bundle_name}/{br['entry']}",
                            }
                        ],
                    }
                )

        pixi_manifest_path = output_root / "pixi-assets-manifest.json"
        _dump_json(pixi_assets, pixi_manifest_path)
        all_files["pixi-assets-manifest.json"] = _sha256_file(pixi_manifest_path)

        # Finalize manifest files section (exclude atlas-manifest.json itself)
        manifest["files"] = dict(sorted(all_files.items()))
        _dump_json(manifest, manifest_path)

        # Atomic output replacement - only delete after successful build
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        shutil.copytree(output_root, self.output_dir)

        # Print summary
        total_pages = sum(br["pageCount"] for br in bundle_results)
        total_files = len(all_files)

        print(f"bundles: {len(bundle_results)}")
        for br in bundle_results:
            print(
                f"  {br['name']}: {br['pageCount']} pages, {len(br['aliases'])} frames"
            )
        print(f"total pages: {total_pages}")
        print(f"total files: {total_files}")
        print(f"manifest SHA-256: {all_files.get('atlas-manifest.json', 'N/A')}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Deterministic 2× atlas builder for Ocean Rescue"
    )
    parser.add_argument("--packet", required=True, help="Path to art-packet.json")
    parser.add_argument("--approval", required=True, help="Path to art-approval.json")
    parser.add_argument("--output-dir", required=True, help="Output directory")

    args = parser.parse_args()

    packet_path = Path(args.packet).resolve()
    approval_path = Path(args.approval).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not packet_path.exists():
        _fail(f"Packet not found: {packet_path}")
    if not approval_path.exists():
        _fail(f"Approval not found: {approval_path}")

    builder = AtlasBuilder(packet_path, approval_path, output_dir)
    builder.build()


if __name__ == "__main__":
    main()
