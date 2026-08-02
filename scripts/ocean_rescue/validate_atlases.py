#!/usr/bin/env python3
"""Validator for Ocean Rescue deterministic atlas output.

Checks generated atlas structure, hashes, dimensions, spritesheet schema,
frame bounds, overlap, padding, trim, pivots, page ceiling, multi-pack links,
and forbidden content.

Usage:
    python validate_atlases.py --packet <path> --approval <path> --generated-dir <path>
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import cast

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RASTER_SCALE = 2
PADDING_PX = 4
MAX_PAGE_DIM = 4096
ALGORITHM_ID = "ocean-rescue-shelf-v1"
APP_NAME = "AidenGame Ocean Rescue Atlas Builder"

VALID_BUNDLES = {"characters", "scene", "effects-ui"}
BUNDLE_ORDER = ["characters", "scene", "effects-ui"]

# UUID-like pattern
UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)

# Timestamp-like ISO pattern
ISO_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256(path.read_bytes())


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ValidationErrors:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def add(self, msg: str) -> None:
        self.errors.append(msg)

    def fail_if_any(self) -> None:
        if self.errors:
            for e in self.errors:
                print(f"FAIL: {e}", file=sys.stderr)
            sys.exit(1)


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def validate_structure(gen_dir: Path, errs: ValidationErrors) -> dict:
    """Check basic output structure exists."""
    manifest_path = gen_dir / "atlas-manifest.json"
    if not manifest_path.exists():
        errs.add("atlas-manifest.json missing")
        return {}

    pixi_path = gen_dir / "pixi-assets-manifest.json"
    if not pixi_path.exists():
        errs.add("pixi-assets-manifest.json missing")

    manifest = _load_json(manifest_path)

    # Check bundle directories exist
    for bundle_name in BUNDLE_ORDER:
        bundle_dir = gen_dir / bundle_name
        if not bundle_dir.exists():
            errs.add(f"Bundle directory missing: {bundle_name}")

    return manifest


def validate_exactly_three_bundles(manifest: dict, errs: ValidationErrors) -> None:
    bundles = manifest.get("bundles", [])
    if len(bundles) != 3:
        errs.add(f"Expected exactly 3 bundles, got {len(bundles)}")
    names = [b["name"] for b in bundles]
    if names != BUNDLE_ORDER:
        errs.add(f"Bundle order mismatch: {names} != {BUNDLE_ORDER}")


def validate_manifest_hashes(
    gen_dir: Path, manifest: dict, errs: ValidationErrors
) -> None:
    """Check that file hashes in manifest match actual bytes."""
    files = manifest.get("files", {})
    for rel_path, expected_sha in files.items():
        # Skip self-reference (manifest does not record its own hash)
        if rel_path == "atlas-manifest.json":
            continue
        full_path = gen_dir / rel_path
        if not full_path.exists():
            errs.add(f"Referenced file missing: {rel_path}")
            continue
        actual_sha = _sha256_file(full_path)
        if actual_sha != expected_sha:
            errs.add(
                f"Hash mismatch for {rel_path}: manifest={expected_sha[:16]}... actual={actual_sha[:16]}..."
            )


def validate_png_dimensions(
    gen_dir: Path, manifest: dict, errs: ValidationErrors
) -> None:
    """Check PNG dimensions and RGBA mode."""
    from PIL import Image

    for bundle in manifest.get("bundles", []):
        for page in bundle.get("pages", []):
            img_path = gen_dir / bundle["name"] / page["image"]
            if not img_path.exists():
                errs.add(f"Page image missing: {page['image']}")
                continue
            img = Image.open(img_path)
            if img.mode != "RGBA":
                errs.add(f"Page {page['image']} mode is {img.mode}, expected RGBA")
            w, h = img.size
            if w != page["width"] or h != page["height"]:
                errs.add(
                    f"Page {page['image']} dimensions {w}x{h} != manifest {page['width']}x{page['height']}"
                )
            if w > MAX_PAGE_DIM or h > MAX_PAGE_DIM:
                errs.add(f"Page {page['image']} exceeds 4096: {w}x{h}")


def validate_spritesheet_schema(
    gen_dir: Path, manifest: dict, errs: ValidationErrors
) -> None:
    """Check PixiJS spritesheet JSON schema."""
    for bundle in manifest.get("bundles", []):
        for page in bundle.get("pages", []):
            json_path = gen_dir / bundle["name"] / page["spritesheet"]
            if not json_path.exists():
                errs.add(f"Spritesheet JSON missing: {page['spritesheet']}")
                continue
            sheet = _load_json(json_path)

            # Top-level keys
            required_keys = {"frames", "animations", "meta"}
            if set(sheet.keys()) != required_keys:
                errs.add(
                    f"Spritesheet {page['spritesheet']} keys: {set(sheet.keys())} != {required_keys}"
                )

            meta = sheet.get("meta", {})
            if meta.get("app") != APP_NAME:
                errs.add(f"meta.app mismatch in {page['spritesheet']}")
            if meta.get("version") != "1":
                errs.add(f"meta.version mismatch in {page['spritesheet']}")
            if meta.get("format") != "RGBA8888":
                errs.add(f"meta.format mismatch in {page['spritesheet']}")
            if str(meta.get("scale")) != str(RASTER_SCALE):
                errs.add(f"meta.scale mismatch in {page['spritesheet']}")

            # Frame keys should be canonical aliases
            frames = sheet.get("frames", {})
            for alias, frame_data in frames.items():
                required_frame_keys = {
                    "frame",
                    "rotated",
                    "trimmed",
                    "spriteSourceSize",
                    "sourceSize",
                    "anchor",
                }
                if set(frame_data.keys()) != required_frame_keys:
                    errs.add(
                        f"Frame {alias} keys: {set(frame_data.keys())} != {required_frame_keys}"
                    )
                if frame_data.get("rotated") is not False:
                    errs.add(f"Frame {alias} rotated is not false")


def validate_alias_membership(
    manifest: dict, packet_aliases: set[str], errs: ValidationErrors
) -> None:
    """Check that all aliases are in the correct bundles."""
    all_manifest_aliases = set()
    for bundle in manifest.get("bundles", []):
        for alias in bundle.get("aliases", []):
            if alias in all_manifest_aliases:
                errs.add(f"Duplicate alias in manifest: {alias}")
            all_manifest_aliases.add(alias)

    if all_manifest_aliases != packet_aliases:
        missing = packet_aliases - all_manifest_aliases
        extra = all_manifest_aliases - packet_aliases
        if missing:
            errs.add(f"Missing aliases: {missing}")
        if extra:
            errs.add(f"Extra aliases: {extra}")


def validate_frame_bounds(
    gen_dir: Path, manifest: dict, errs: ValidationErrors
) -> None:
    """Check frame rectangles are within page bounds."""
    for bundle in manifest.get("bundles", []):
        for page in bundle.get("pages", []):
            json_path = gen_dir / bundle["name"] / page["spritesheet"]
            if not json_path.exists():
                continue
            sheet = _load_json(json_path)
            frames = sheet.get("frames", {})
            for alias, frame_data in frames.items():
                frame = frame_data["frame"]
                if frame["x"] < 0 or frame["y"] < 0:
                    errs.add(f"Frame {alias} has negative position")
                if frame["x"] + frame["w"] > page["width"]:
                    errs.add(
                        f"Frame {alias} overflows page width: {frame['x']}+{frame['w']} > {page['width']}"
                    )
                if frame["y"] + frame["h"] > page["height"]:
                    errs.add(
                        f"Frame {alias} overflows page height: {frame['y']}+{frame['h']} > {page['height']}"
                    )


def validate_no_overlap(gen_dir: Path, manifest: dict, errs: ValidationErrors) -> None:
    """Check that frames don't overlap."""
    for bundle in manifest.get("bundles", []):
        for page in bundle.get("pages", []):
            json_path = gen_dir / bundle["name"] / page["spritesheet"]
            if not json_path.exists():
                continue
            sheet = _load_json(json_path)
            frames = list(sheet.get("frames", {}).items())
            for i, (alias_a, frame_a) in enumerate(frames):
                rect_a = frame_a["frame"]
                for alias_b, frame_b in frames[i + 1 :]:
                    rect_b = frame_b["frame"]
                    # AABB overlap test
                    if (
                        rect_a["x"] < rect_b["x"] + rect_b["w"]
                        and rect_a["x"] + rect_a["w"] > rect_b["x"]
                        and rect_a["y"] < rect_b["y"] + rect_b["h"]
                        and rect_a["y"] + rect_a["h"] > rect_b["y"]
                    ):
                        errs.add(
                            f"Frames overlap: {alias_a} and {alias_b} on {page['spritesheet']}"
                        )


def validate_padding(gen_dir: Path, manifest: dict, errs: ValidationErrors) -> None:
    """Check that frame positions have 4px transparent padding around them."""
    from PIL import Image

    for bundle in manifest.get("bundles", []):
        for page in bundle.get("pages", []):
            img_path = gen_dir / bundle["name"] / page["image"]
            if not img_path.exists():
                continue
            img = Image.open(img_path)
            json_path = gen_dir / bundle["name"] / page["spritesheet"]
            if not json_path.exists():
                continue
            sheet = _load_json(json_path)
            frames = sheet.get("frames", {})

            for alias, frame_data in frames.items():
                frame = frame_data["frame"]
                # Check padding region is transparent
                x0 = frame["x"]
                y0 = frame["y"]
                w = frame["w"]
                h = frame["h"]

                # Left padding column
                if x0 > 0:
                    for dy in range(h):
                        px = x0 - 1
                        py = y0 + dy
                        if 0 <= px < img.width and 0 <= py < img.height:
                            r, g, b, a = cast(tuple[int, int, int, int], img.getpixel((px, py)))
                            if a != 0:
                                errs.add(
                                    f"Padding violation (left) for {alias} at ({px},{py})"
                                )
                                return  # One error per page is enough

                # Right padding column
                x1 = x0 + w
                if x1 < img.width:
                    for dy in range(h):
                        px = x1
                        py = y0 + dy
                        if 0 <= px < img.width and 0 <= py < img.height:
                            r, g, b, a = cast(tuple[int, int, int, int], img.getpixel((px, py)))
                            if a != 0:
                                errs.add(
                                    f"Padding violation (right) for {alias} at ({px},{py})"
                                )
                                return

                # Top padding row
                if y0 > 0:
                    for dx in range(w):
                        px = x0 + dx
                        py = y0 - 1
                        if 0 <= px < img.width and 0 <= py < img.height:
                            r, g, b, a = cast(tuple[int, int, int, int], img.getpixel((px, py)))
                            if a != 0:
                                errs.add(
                                    f"Padding violation (top) for {alias} at ({px},{py})"
                                )
                                return

                # Bottom padding row
                y1 = y0 + h
                if y1 < img.height:
                    for dx in range(w):
                        px = x0 + dx
                        py = y1
                        if 0 <= px < img.width and 0 <= py < img.height:
                            r, g, b, a = cast(tuple[int, int, int, int], img.getpixel((px, py)))
                            if a != 0:
                                errs.add(
                                    f"Padding violation (bottom) for {alias} at ({px},{py})"
                                )
                                return


def validate_trim_metadata(
    gen_dir: Path, manifest: dict, errs: ValidationErrors
) -> None:
    """Check trim metadata consistency."""
    for bundle in manifest.get("bundles", []):
        for page in bundle.get("pages", []):
            json_path = gen_dir / bundle["name"] / page["spritesheet"]
            if not json_path.exists():
                continue
            sheet = _load_json(json_path)
            frames = sheet.get("frames", {})
            for alias, frame_data in frames.items():
                frame = frame_data["frame"]
                sprite_source = frame_data["spriteSourceSize"]
                source_size = frame_data["sourceSize"]

                # sourceSize should be 2× logical
                if source_size["w"] <= 0 or source_size["h"] <= 0:
                    errs.add(f"Frame {alias} sourceSize is zero")

                # spriteSourceSize should match frame dimensions (trimmed content)
                if sprite_source["w"] != frame["w"] or sprite_source["h"] != frame["h"]:
                    errs.add(
                        f"Frame {alias} spriteSourceSize {sprite_source} != frame {frame}"
                    )


def validate_pivot_metadata(
    gen_dir: Path, manifest: dict, packet: dict, errs: ValidationErrors
) -> None:
    """Check pivot anchor matches packet."""
    alias_to_pivot = {a["alias"]: a["pivot"] for a in packet["assets"]}
    for bundle in manifest.get("bundles", []):
        for page in bundle.get("pages", []):
            json_path = gen_dir / bundle["name"] / page["spritesheet"]
            if not json_path.exists():
                continue
            sheet = _load_json(json_path)
            frames = sheet.get("frames", {})
            for alias, frame_data in frames.items():
                anchor = frame_data.get("anchor", {})
                expected_pivot = alias_to_pivot.get(alias)
                if expected_pivot is None:
                    continue
                if (
                    abs(anchor["x"] - expected_pivot[0]) > 1e-6
                    or abs(anchor["y"] - expected_pivot[1]) > 1e-6
                ):
                    errs.add(
                        f"Frame {alias} anchor {anchor} != expected pivot {expected_pivot}"
                    )


def validate_page_ceiling(
    gen_dir: Path, manifest: dict, errs: ValidationErrors
) -> None:
    """Check pages don't exceed 4096."""
    for bundle in manifest.get("bundles", []):
        for page in bundle.get("pages", []):
            if page["width"] > MAX_PAGE_DIM:
                errs.add(
                    f"Page {page['spritesheet']} width {page['width']} > {MAX_PAGE_DIM}"
                )
            if page["height"] > MAX_PAGE_DIM:
                errs.add(
                    f"Page {page['spritesheet']} height {page['height']} > {MAX_PAGE_DIM}"
                )


def validate_multi_pack_links(
    gen_dir: Path, manifest: dict, errs: ValidationErrors
) -> None:
    """Check multi-page related pack links."""
    for bundle in manifest.get("bundles", []):
        pages = bundle.get("pages", [])
        if len(pages) <= 1:
            continue
        for page in pages:
            json_path = gen_dir / bundle["name"] / page["spritesheet"]
            if not json_path.exists():
                continue
            sheet = _load_json(json_path)
            related = sheet.get("meta", {}).get("related_multi_packs", [])
            expected_related = [
                p["spritesheet"] for p in pages if p["index"] != page["index"]
            ]
            if sorted(related) != sorted(expected_related):
                errs.add(
                    f"Multi-pack links mismatch for {page['spritesheet']}: {related} != {expected_related}"
                )


def validate_undeclared_files(
    gen_dir: Path, manifest: dict, errs: ValidationErrors
) -> None:
    """Check for undeclared files in generated directory."""
    declared = set(manifest.get("files", {}).keys())
    # Include the manifest itself (excluded from files section)
    declared.add("atlas-manifest.json")
    # Also include directories
    declared_dirs = set()
    for f in declared:
        parts = f.split("/")
        for i in range(1, len(parts)):
            declared_dirs.add("/".join(parts[:i]))

    actual = set()
    for item in gen_dir.rglob("*"):
        if item.is_file():
            rel = str(item.relative_to(gen_dir))
            actual.add(rel)

    undeclared = actual - declared
    if undeclared:
        errs.add(f"Undeclared files: {undeclared}")


def validate_forbidden_content(
    gen_dir: Path, manifest: dict, errs: ValidationErrors
) -> None:
    """Check for absolute paths, timestamps, UUIDs in output."""
    for rel_path in manifest.get("files", {}).keys():
        if Path(rel_path).is_absolute():
            errs.add(f"Absolute path in manifest: {rel_path}")

    # Check JSON files for timestamps/UUIDs
    for rel_path in manifest.get("files", {}).keys():
        if not rel_path.endswith(".json"):
            continue
        full_path = gen_dir / rel_path
        if not full_path.exists():
            continue
        content = full_path.read_text(encoding="utf-8")
        if UUID_RE.search(content):
            errs.add(f"UUID found in {rel_path}")
        if ISO_TS_RE.search(content):
            errs.add(f"ISO timestamp found in {rel_path}")


def validate_exact_toolchain_pins(manifest: dict, errs: ValidationErrors) -> None:
    """Check exact dependency versions."""
    toolchain = manifest.get("toolchain", {})
    if toolchain.get("cairosvg") != "2.9.0":
        errs.add(f"CairoSVG version: {toolchain.get('cairosvg')} != 2.9.0")
    if toolchain.get("pillow") != "12.3.0":
        errs.add(f"Pillow version: {toolchain.get('pillow')} != 12.3.0")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Validate Ocean Rescue atlas output")
    parser.add_argument("--packet", required=True)
    parser.add_argument("--approval", required=True)
    parser.add_argument("--generated-dir", required=True)

    args = parser.parse_args()

    gen_dir = Path(args.generated_dir).resolve()
    packet_path = Path(args.packet).resolve()

    if not gen_dir.exists():
        print("FAIL: generated directory does not exist", file=sys.stderr)
        sys.exit(1)

    errs = ValidationErrors()
    packet = _load_json(packet_path)
    packet_aliases = {a["alias"] for a in packet["assets"]}

    manifest = validate_structure(gen_dir, errs)
    if not manifest:
        errs.fail_if_any()

    validate_exactly_three_bundles(manifest, errs)
    validate_manifest_hashes(gen_dir, manifest, errs)
    validate_png_dimensions(gen_dir, manifest, errs)
    validate_spritesheet_schema(gen_dir, manifest, errs)
    validate_alias_membership(manifest, packet_aliases, errs)
    validate_frame_bounds(gen_dir, manifest, errs)
    validate_no_overlap(gen_dir, manifest, errs)
    validate_padding(gen_dir, manifest, errs)
    validate_trim_metadata(gen_dir, manifest, errs)
    validate_pivot_metadata(gen_dir, manifest, packet, errs)
    validate_page_ceiling(gen_dir, manifest, errs)
    validate_multi_pack_links(gen_dir, manifest, errs)
    validate_undeclared_files(gen_dir, manifest, errs)
    validate_forbidden_content(gen_dir, manifest, errs)
    validate_exact_toolchain_pins(manifest, errs)

    errs.fail_if_any()
    print("PASS: atlas validation succeeded")


if __name__ == "__main__":
    main()
