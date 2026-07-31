#!/usr/bin/env python3
"""Validate Ocean Rescue proof-art production approval gate.

Usage:
    python validate_art_approval.py <source_root>

Exit 0 on success. Nonzero exit with error message on failure.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

SCHEMA_VERSION = 1
REQUIRED_DECISION = "approved"
REQUIRED_ASSET_COUNT = 19


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"Invalid JSON in {path.name}: {e}")
        return {}


def validate_approval_record(record: dict) -> None:
    if record.get("schemaVersion") != SCHEMA_VERSION:
        fail(
            f"schemaVersion must be {SCHEMA_VERSION}, got {record.get('schemaVersion')}"
        )
    if record.get("decision") != REQUIRED_DECISION:
        fail(f"decision must be '{REQUIRED_DECISION}', got '{record.get('decision')}'")
    if record.get("approvedAssetCount") != REQUIRED_ASSET_COUNT:
        fail(
            f"approvedAssetCount must be {REQUIRED_ASSET_COUNT}, got {record.get('approvedAssetCount')}"
        )
    if record.get("scope") != "ocean-rescue-rendering-mvp-proof-packet":
        fail(f"Invalid scope: {record.get('scope')}")
    if not record.get("requiredPredecessor"):
        fail("Missing requiredPredecessor")
    if not record.get("approvalDate"):
        fail("Missing approvalDate")
    if not record.get("artPacketSha256"):
        fail("Missing artPacketSha256")
    if not record.get("contactSheetSha256"):
        fail("Missing contactSheetSha256")
    if not record.get("sourceSetSha256"):
        fail("Missing sourceSetSha256")
    if not isinstance(record.get("approvedAliases"), list):
        fail("approvedAliases must be a list")


def validate_aliases_sorted(record: dict) -> None:
    aliases = record.get("approvedAliases") or []
    if sorted(aliases) != aliases:
        fail("approvedAliases must be sorted")


def validate_packet_hashes(packet: dict, record: dict, root: Path) -> None:
    packet_path = root / "art-packet.json"
    actual_packet_sha = sha256_bytes(packet_path.read_bytes())
    if actual_packet_sha != record.get("artPacketSha256"):
        fail(
            f"artPacketSha256 mismatch: record={record.get('artPacketSha256')[:16]}... actual={actual_packet_sha[:16]}..."
        )

    for asset in packet["assets"]:
        source_path = root / asset["source"]
        if not source_path.exists():
            fail(f"Source file missing: {asset['source']}")
        actual_src_sha = sha256_bytes(source_path.read_bytes())
        if actual_src_sha != asset["sourceSha256"]:
            fail(
                f"Source hash mismatch for {asset['alias']}: record={asset['sourceSha256'][:16]}... actual={actual_src_sha[:16]}..."
            )


def validate_all_approved(packet: dict) -> None:
    for asset in packet["assets"]:
        if asset.get("approvalState") != "approved":
            fail(
                f"Asset {asset['alias']} is not approved: {asset.get('approvalState')}"
            )


def validate_source_set_sha(packet: dict, record: dict, root: Path) -> None:
    parts = []
    for asset in sorted(packet["assets"], key=lambda a: a["alias"]):
        source_path = root / asset["source"]
        actual_sha = sha256_bytes(source_path.read_bytes())
        parts.append(f"{asset['alias']}:{actual_sha}")
    canonical = "\n".join(parts) + "\n"
    expected_sha = sha256_bytes(canonical.encode("utf-8"))
    if expected_sha != record.get("sourceSetSha256"):
        fail(
            f"sourceSetSha256 mismatch: record={record.get('sourceSetSha256')[:16]}... expected={expected_sha[:16]}..."
        )


def validate_contact_sheet(record: dict, root: Path) -> None:
    contact_sheet = root.parent / "review" / "proof-art-contact-sheet.html"
    if not contact_sheet.exists():
        fail(f"Contact sheet not found: {contact_sheet}")
    actual_sha = sha256_bytes(contact_sheet.read_bytes())
    if actual_sha != record.get("contactSheetSha256"):
        fail(
            f"contactSheetSha256 mismatch: record={record.get('contactSheetSha256')[:16]}... actual={actual_sha[:16]}..."
        )


def _is_unsafe_path(path_str: str) -> bool:
    if path_str.startswith("/"):
        return True
    parts = Path(path_str).parts
    depth = 0
    for part in parts:
        if part == "..":
            depth -= 1
        elif part != ".":
            depth += 1
    return depth < 0


def validate_evidence_paths(record: dict) -> None:
    evidence = record.get("evidence", {})
    for key in ("focusedTest", "contactSheet", "visualReviewVerdict"):
        if key not in evidence:
            fail(f"Missing evidence field: {key}")
    test_path = evidence.get("focusedTest", "")
    if _is_unsafe_path(test_path):
        fail(f"Absolute or path-traversal evidence path in focusedTest: {test_path}")
    contact_path = evidence.get("contactSheet", "")
    if _is_unsafe_path(contact_path):
        fail(
            f"Absolute or path-traversal evidence path in contactSheet: {contact_path}"
        )


def validate_no_nondeterministic(record: dict) -> None:
    for key in ("approvalDate",):
        val = record.get(key, "")
        if not isinstance(val, str):
            fail(f"{key} must be a string")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: validate_art_approval.py <source_root>", file=sys.stderr)
        sys.exit(1)

    root = Path(sys.argv[1])
    if not root.is_dir():
        fail(f"Not a directory: {root}")

    approval_path = root / "art-approval.json"
    if not approval_path.exists():
        fail("art-approval.json not found")

    packet_path = root / "art-packet.json"
    if not packet_path.exists():
        fail("art-packet.json not found")

    record = load_json(approval_path)
    packet = load_json(packet_path)

    validate_approval_record(record)
    validate_aliases_sorted(record)
    validate_all_approved(packet)
    validate_packet_hashes(packet, record, root)
    validate_source_set_sha(packet, record, root)
    validate_contact_sheet(record, root)
    validate_evidence_paths(record)
    validate_no_nondeterministic(record)

    print(
        f"PASS: approval record validated for {len(packet['assets'])} approved assets."
    )


if __name__ == "__main__":
    main()
