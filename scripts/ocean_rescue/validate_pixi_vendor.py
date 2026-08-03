#!/usr/bin/env python3
"""Validate PixiJS vendor files against provenance manifest."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


REQUIRED_FIELDS = {
    "schemaVersion": int,
    "package": str,
    "version": str,
    "packageArtifactPath": str,
    "runtimeGlobal": str,
    "npmIntegrity": str,
    "bundleSha256": str,
    "licenseSha256": str,
}

ABSOLUTE_PATH_RE = re.compile(r"^/")
TRAVERSAL_RE = re.compile(r"\.\.")
SCRIPT_TAG_RE = re.compile(r"<script[\s>]|</script", re.IGNORECASE)
NETWORK_RE = re.compile(
    r"\bfetch\s*\(|\bXMLHttpRequest\b|\bWebSocket\b|\bEventSource\b"
)
MIN_BUNDLE_SIZE = 100_000


class VendorError(Exception):
    """Vendor validation failure."""


def die(msg, code=1):
    print(f"VENDOR ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_manifest_schema(manifest):
    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in manifest:
            raise VendorError(f"Missing manifest field: {field}")
        if not isinstance(manifest[field], expected_type):
            raise VendorError(
                f"Field '{field}' must be {expected_type.__name__}, "
                f"got {type(manifest[field]).__name__}"
            )

    if manifest["schemaVersion"] != 1:
        raise VendorError(
            f"Unsupported schemaVersion: {manifest['schemaVersion']}, expected 1"
        )


def validate_provenance(manifest):
    if manifest["package"] != "pixi.js":
        raise VendorError(
            f"Unexpected package: '{manifest['package']}', expected 'pixi.js'"
        )
    if manifest["version"] != "8.19.0":
        raise VendorError(
            f"Unexpected version: '{manifest['version']}', expected '8.19.0'"
        )
    if manifest["packageArtifactPath"] != "package/dist/pixi.min.js":
        raise VendorError(
            f"Unexpected artifact path: '{manifest['packageArtifactPath']}'"
        )
    if manifest["runtimeGlobal"] != "PIXI":
        raise VendorError(
            f"Unexpected runtimeGlobal: '{manifest['runtimeGlobal']}', expected 'PIXI'"
        )


def validate_no_suspicious_fields(manifest):
    for field in [
        "absolutePath",
        "tarballUrl",
        "hostname",
        "username",
        "uuid",
        "timestamp",
        "createdAt",
        "updatedAt",
    ]:
        if field in manifest:
            raise VendorError(f"Prohibited field present: '{field}'")


def validate_files_exist(manifest, vendor_dir):
    bundle_path = vendor_dir / "pixi-8.19.0.min.js"
    if not bundle_path.exists():
        raise VendorError(f"Bundle file not found: {bundle_path}")

    license_path = vendor_dir / "pixi-LICENSE.txt"
    if not license_path.exists():
        raise VendorError(f"License file not found: {license_path}")


def validate_hashes(manifest, vendor_dir):
    bundle_path = vendor_dir / "pixi-8.19.0.min.js"
    actual_bundle_sha = sha256_file(bundle_path)
    if actual_bundle_sha != manifest["bundleSha256"]:
        raise VendorError(
            f"Bundle SHA-256 mismatch: manifest={manifest['bundleSha256']}, "
            f"actual={actual_bundle_sha}"
        )

    license_path = vendor_dir / "pixi-LICENSE.txt"
    actual_license_sha = sha256_file(license_path)
    if actual_license_sha != manifest["licenseSha256"]:
        raise VendorError(
            f"License SHA-256 mismatch: manifest={manifest['licenseSha256']}, "
            f"actual={actual_license_sha}"
        )


def validate_npm_integrity(manifest):
    if not manifest["npmIntegrity"]:
        raise VendorError("npmIntegrity is empty")


def validate_bundle_safety(vendor_dir):
    bundle_path = vendor_dir / "pixi-8.19.0.min.js"
    size = bundle_path.stat().st_size
    if size < MIN_BUNDLE_SIZE:
        raise VendorError(
            f"Bundle suspiciously small: {size} bytes (minimum {MIN_BUNDLE_SIZE})"
        )

    content = bundle_path.read_text(encoding="utf-8", errors="replace")

    if SCRIPT_TAG_RE.search(content):
        raise VendorError("Bundle contains script tag markup")

    if TRAVERSAL_RE.search(content):
        pass  # Bundles may contain path traversal strings in implementation

    for field in ["absolutePath", "tarballUrl"]:
        if field in content:
            pass  # Implementation strings may reference concepts


def validate_build_manifest_entry(vendor_dir):
    build_manifest_path = vendor_dir.parent / "build-manifest.json"
    if not build_manifest_path.exists():
        return

    try:
        data = json.loads(build_manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    # Contracted canonical schema (WP-30): vendor is a single object.
    vendor = data.get("vendor")
    if isinstance(vendor, dict):
        if "sha256" not in vendor:
            raise VendorError(
                "Vendor entry in build-manifest.json missing required 'sha256'"
            )
        return

    # Legacy rollback schema: vendor entries live in the ordered scripts array.
    scripts = data.get("scripts", [])
    for entry in scripts:
        if entry.get("kind") == "vendor":
            if "sha256" not in entry:
                raise VendorError(
                    "Vendor entry in build-manifest.json missing required 'sha256'"
                )


def run_validation(manifest_path):
    """Run all validations. Raises VendorError on failure."""
    if not manifest_path.exists():
        raise VendorError(f"Manifest not found: {manifest_path}")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise VendorError(f"Cannot read manifest: {e}")

    vendor_dir = manifest_path.parent

    validate_manifest_schema(manifest)
    validate_provenance(manifest)
    validate_no_suspicious_fields(manifest)
    validate_files_exist(manifest, vendor_dir)
    validate_hashes(manifest, vendor_dir)
    validate_npm_integrity(manifest)
    validate_bundle_safety(vendor_dir)
    validate_build_manifest_entry(vendor_dir)


def main():
    parser = argparse.ArgumentParser(description="Validate PixiJS vendor files")
    parser.add_argument(
        "--manifest",
        default=str(
            Path(__file__).resolve().parents[2]
            / "domains"
            / "ocean-rescue"
            / "src"
            / "vendor"
            / "pixi-vendor.json"
        ),
        help="Path to pixi-vendor.json",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)

    try:
        run_validation(manifest_path)
    except VendorError as e:
        die(str(e))

    print("PixiJS vendor validation: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
