#!/usr/bin/env python3
"""Validate Ocean Rescue proof-art packet.

Usage:
    python validate_art_packet.py <source_root>

Exit 0 on success with sorted alias+SHA-256 listing.
Nonzero exit with single error message on failure.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ALLOWED_BUNDLES = {"characters", "scene", "effects-ui"}

FORBIDDEN_SVG_ELEMENTS = {
    "script",
    "animate",
    "animatetransform",
    "animatemotion",
    "set",
    "foreignobject",
}
FORBIDDEN_SVG_ATTRS = {
    "onload",
    "onclick",
    "onmouseover",
    "onmouseout",
    "onerror",
    "href",
    "xlink:href",
}
URL_PATTERN = re.compile(
    r"https?://|ftp://|data:(?:image|text|application)/", re.IGNORECASE
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def validate_json_shape(packet: dict) -> None:
    for key in (
        "schemaVersion",
        "logicalViewport",
        "declaredRasterScale",
        "paletteVersion",
        "assets",
    ):
        if key not in packet:
            fail(f"Missing root field: {key}")
    if not isinstance(packet["assets"], list):
        fail("assets must be a list")
    for i, asset in enumerate(packet["assets"]):
        for field in (
            "id",
            "alias",
            "source",
            "sourceType",
            "bundle",
            "logicalSize",
            "declaredRasterScale",
            "pivot",
            "authoringMethod",
            "approvalState",
            "revisionNote",
            "sourceSha256",
        ):
            if field not in asset:
                fail(f"Asset [{i}] missing field: {field}")


def validate_bundles_and_aliases(packet: dict) -> None:
    aliases = []
    ids = []
    for asset in packet["assets"]:
        if asset["bundle"] not in ALLOWED_BUNDLES:
            fail(f"Asset {asset['alias']} has invalid bundle: {asset['bundle']}")
        if asset["sourceType"] != "svg":
            fail(
                f"Asset {asset['alias']} sourceType must be 'svg', got: {asset['sourceType']}"
            )
        if asset["declaredRasterScale"] != 2:
            fail(
                f"Asset {asset['alias']} declaredRasterScale must be 2, got: {asset['declaredRasterScale']}"
            )
        aliases.append(asset["alias"])
        ids.append(asset["id"])

    if len(ids) != len(set(ids)):
        fail("Duplicate asset IDs found")
    if len(aliases) != len(set(aliases)):
        fail("Duplicate asset aliases found")


def validate_pivots(packet: dict) -> None:
    for asset in packet["assets"]:
        pivot = asset["pivot"]
        if not isinstance(pivot, list) or len(pivot) != 2:
            fail(f"Asset {asset['alias']} pivot must be [x, y]")
        x, y = pivot
        if not (isinstance(x, (int, float)) and isinstance(y, (int, float))):
            fail(f"Asset {asset['alias']} pivot values must be numeric")
        if not (0 <= x <= 1 and 0 <= y <= 1):
            fail(f"Asset {asset['alias']} pivot {pivot} out of range [0, 1]")


def validate_logical_sizes(packet: dict) -> None:
    for asset in packet["assets"]:
        size = asset["logicalSize"]
        if not isinstance(size, list) or len(size) != 2:
            fail(f"Asset {asset['alias']} logicalSize must be [w, h]")
        w, h = size
        if not (isinstance(w, int) and isinstance(h, int) and w > 0 and h > 0):
            fail(f"Asset {asset['alias']} logicalSize invalid: {size}")


def validate_source_hashes(packet: dict, root: Path) -> None:
    for asset in packet["assets"]:
        source_path = root / asset["source"]
        if not source_path.exists():
            fail(f"Source file missing: {asset['source']}")
        actual = sha256_file(source_path)
        if actual != asset["sourceSha256"]:
            fail(
                f"Hash mismatch for {asset['alias']}: declared={asset['sourceSha256'][:16]}... actual={actual[:16]}..."
            )


def validate_no_path_traversal(packet: dict) -> None:
    for asset in packet["assets"]:
        source = asset["source"]
        if ".." in source or source.startswith("/"):
            fail(f"Path traversal detected in: {source}")


def validate_svg(path: Path) -> None:
    content = path.read_text(encoding="utf-8")

    stripped = re.sub(r'\s+xmlns[:\w]*\s*=\s*"[^"]*"', "", content)
    stripped = re.sub(r"\s+xmlns[:\w]*\s*=\s*\'[^\']*\'", "", stripped)
    if URL_PATTERN.search(stripped):
        fail(f"External URL or data URI found in: {path.name}")

    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        fail(f"Malformed XML in {path.name}: {e}")

    root_elem = tree.getroot()
    tag = root_elem.tag.split("}")[-1] if "}" in root_elem.tag else root_elem.tag
    if tag.lower() != "svg":
        fail(f"Root element is not <svg> in {path.name}: got <{tag}>")

    if root_elem.get("viewBox") is None:
        fail(f"Missing viewBox in: {path.name}")

    def check_elements(elem: ET.Element) -> None:
        local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if local.lower() in FORBIDDEN_SVG_ELEMENTS:
            fail(f"Forbidden element <{local}> in: {path.name}")
        for attr_name in elem.attrib:
            local_attr = attr_name.split("}")[-1] if "}" in attr_name else attr_name
            if local_attr.lower() in FORBIDDEN_SVG_ATTRS:
                fail(f"Forbidden attribute '{local_attr}' in: {path.name}")
        for child in elem:
            check_elements(child)

    check_elements(root_elem)

    has_drawable = False
    for elem in root_elem.iter():
        local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if local.lower() in {
            "circle",
            "ellipse",
            "rect",
            "path",
            "line",
            "polygon",
            "polyline",
            "g",
        }:
            has_drawable = True
            break
    if not has_drawable:
        fail(f"No drawable elements found in: {path.name}")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: validate_art_packet.py <source_root>", file=sys.stderr)
        sys.exit(1)

    root = Path(sys.argv[1])
    if not root.is_dir():
        fail(f"Not a directory: {root}")

    packet_path = root / "art-packet.json"
    if not packet_path.exists():
        fail("art-packet.json not found")

    try:
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"Invalid JSON: {e}")

    validate_json_shape(packet)
    validate_bundles_and_aliases(packet)
    validate_pivots(packet)
    validate_logical_sizes(packet)
    validate_source_hashes(packet, root)
    validate_no_path_traversal(packet)

    for asset in packet["assets"]:
        source_path = root / asset["source"]
        validate_svg(source_path)

    results = []
    for asset in sorted(packet["assets"], key=lambda a: a["alias"]):
        results.append(f"{asset['alias']}  {asset['sourceSha256']}")
    for line in results:
        print(line)
    print(f"\nPASS: {len(results)} assets validated.")


if __name__ == "__main__":
    main()
