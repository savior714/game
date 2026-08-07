#!/usr/bin/env python3
"""Validate Ocean Rescue proof-art production approval gate.

Usage:
    python validate_art_approval.py <source_root>

Exit 0 on success. Nonzero exit with a concise reapproval message on failure.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
REQUIRED_DECISION = "approved"
REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_SOURCE_ROOT = Path("domains/ocean-rescue/assets/source")
CANONICAL_PACKET = CANONICAL_SOURCE_ROOT / "art-packet.json"
CANONICAL_CONTACT_SHEET = Path(
    "domains/ocean-rescue/assets/review/proof-art-contact-sheet.html"
)
FULL_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        fail(f"Cannot read valid JSON from {path}: {exc}")
        return {}


def git_bytes(commit: str, repo_path: Path) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", f"{commit}:{repo_path.as_posix()}"],
        capture_output=True,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        fail(
            "reapproval required: approved source commit cannot provide "
            f"{repo_path.as_posix()}: {detail}"
        )
    return result.stdout


def validate_approval_record(record: dict[str, Any], expected_count: int) -> None:
    if record.get("schemaVersion") != SCHEMA_VERSION:
        fail(
            f"schemaVersion must be {SCHEMA_VERSION}, got {record.get('schemaVersion')}"
        )
    if record.get("decision") != REQUIRED_DECISION:
        fail(f"decision must be '{REQUIRED_DECISION}', got '{record.get('decision')}'")
    if record.get("approvedAssetCount") != expected_count:
        fail(
            f"approvedAssetCount must be {expected_count}, "
            f"got {record.get('approvedAssetCount')}"
        )
    if record.get("scope") != "ocean-rescue-rendering-mvp-proof-packet":
        fail(f"Invalid scope: {record.get('scope')}")
    if not record.get("approvalDate"):
        fail("Missing approvalDate")
    for key in (
        "artPacketSha256",
        "contactSheetSha256",
        "sourceSetSha256",
        "requiredPredecessor",
    ):
        if not record.get(key):
            fail(f"Missing {key}")
    if not isinstance(record.get("approvedAliases"), list):
        fail("approvedAliases must be a list")


def validate_aliases_sorted(record: dict[str, Any]) -> None:
    aliases = record.get("approvedAliases") or []
    if sorted(aliases) != aliases:
        fail("approvedAliases must be sorted")


def validate_approved_aliases_parity(
    packet: dict[str, Any], record: dict[str, Any]
) -> None:
    packet_aliases = sorted(asset["alias"] for asset in packet["assets"])
    approved_raw = record.get("approvedAliases")
    if not isinstance(approved_raw, list):
        fail("approvedAliases must be a list")
        return
    approved = [str(alias) for alias in approved_raw]

    duplicates = sorted({alias for alias in approved if approved.count(alias) > 1})
    if duplicates:
        fail(f"Duplicate approved aliases: {set(duplicates)}")

    missing = set(packet_aliases) - set(approved)
    extra = set(approved) - set(packet_aliases)
    errors = []
    if missing:
        errors.append(f"Missing: {missing}")
    if extra:
        errors.append(f"Extra: {extra}")
    if record.get("approvedAssetCount") != len(packet_aliases):
        errors.append(
            f"approvedAssetCount {record.get('approvedAssetCount')} != "
            f"packet asset count {len(packet_aliases)}"
        )
    if record.get("approvedAssetCount") != len(approved):
        errors.append(
            f"approvedAssetCount {record.get('approvedAssetCount')} != "
            f"approvedAliases count {len(approved)}"
        )
    if errors:
        fail("Approved alias mismatch. " + ". ".join(errors))


def validate_packet_hashes(
    packet: dict[str, Any], record: dict[str, Any], root: Path
) -> None:
    packet_path = root / "art-packet.json"
    actual_packet_sha = sha256_bytes(packet_path.read_bytes())
    record_packet_sha = record.get("artPacketSha256")
    if actual_packet_sha != record_packet_sha:
        fail(
            "artPacketSha256 mismatch: "
            f"record={str(record_packet_sha)[:16]}... "
            f"actual={actual_packet_sha[:16]}..."
        )

    for asset in packet["assets"]:
        source_path = root / asset["source"]
        if not source_path.exists():
            fail(f"Source file missing: {asset['source']}")
        actual_src_sha = sha256_bytes(source_path.read_bytes())
        if actual_src_sha != asset["sourceSha256"]:
            fail(
                f"Source hash mismatch for {asset['alias']}: "
                f"record={asset['sourceSha256'][:16]}... "
                f"actual={actual_src_sha[:16]}..."
            )


def validate_all_approved(packet: dict[str, Any]) -> None:
    for asset in packet["assets"]:
        if asset.get("approvalState") != "approved":
            fail(
                f"Asset {asset['alias']} is not approved: "
                f"{asset.get('approvalState')}"
            )


def compute_source_set_sha(
    packet: dict[str, Any], source_bytes: dict[str, bytes]
) -> str:
    parts = []
    for asset in sorted(packet["assets"], key=lambda item: item["alias"]):
        actual_sha = sha256_bytes(source_bytes[asset["source"]])
        parts.append(f"{asset['alias']}:{actual_sha}")
    canonical = "\n".join(parts) + "\n"
    return sha256_bytes(canonical.encode("utf-8"))


def validate_source_set_sha(
    packet: dict[str, Any], record: dict[str, Any], root: Path
) -> None:
    source_bytes = {
        asset["source"]: (root / asset["source"]).read_bytes()
        for asset in packet["assets"]
    }
    expected_sha = compute_source_set_sha(packet, source_bytes)
    record_source_sha = record.get("sourceSetSha256")
    if expected_sha != record_source_sha:
        fail(
            "reapproval required: current source hash does not match the last "
            f"approved hash (approved={str(record_source_sha)[:16]}..., "
            f"current={expected_sha[:16]}...)"
        )


def validate_approved_commit(
    packet: dict[str, Any], record: dict[str, Any]
) -> None:
    predecessor = str(record.get("requiredPredecessor", ""))
    if not FULL_COMMIT_RE.fullmatch(predecessor):
        fail(
            "reapproval required: requiredPredecessor must be the full commit "
            "that contained the reviewed source set"
        )

    exists = subprocess.run(
        [
            "git",
            "-C",
            str(REPO_ROOT),
            "cat-file",
            "-e",
            f"{predecessor}^{{commit}}",
        ],
        capture_output=True,
    )
    if exists.returncode != 0:
        fail(
            "reapproval required: requiredPredecessor is not an available Git commit"
        )

    approved_packet_bytes = git_bytes(predecessor, CANONICAL_PACKET)
    if sha256_bytes(approved_packet_bytes) != record.get("artPacketSha256"):
        fail(
            "reapproval required: the approved commit contains a different "
            "art packet"
        )

    approved_contact_bytes = git_bytes(predecessor, CANONICAL_CONTACT_SHEET)
    if sha256_bytes(approved_contact_bytes) != record.get("contactSheetSha256"):
        fail(
            "reapproval required: the approved commit contains a different "
            "contact sheet"
        )

    approved_source_bytes = {}
    for asset in packet["assets"]:
        repo_path = CANONICAL_SOURCE_ROOT / asset["source"]
        approved_source_bytes[asset["source"]] = git_bytes(predecessor, repo_path)

    approved_source_sha = compute_source_set_sha(packet, approved_source_bytes)
    if approved_source_sha != record.get("sourceSetSha256"):
        fail(
            "reapproval required: source files changed after the recorded "
            "approval commit"
        )


def validate_contact_sheet(record: dict[str, Any], root: Path) -> None:
    contact_sheet = root.parent / "review" / "proof-art-contact-sheet.html"
    if not contact_sheet.exists():
        fail(f"Contact sheet not found: {contact_sheet}")
    actual_sha = sha256_bytes(contact_sheet.read_bytes())
    record_sheet_sha = record.get("contactSheetSha256")
    if actual_sha != record_sheet_sha:
        fail(
            "contactSheetSha256 mismatch: "
            f"record={str(record_sheet_sha)[:16]}... actual={actual_sha[:16]}..."
        )


def _is_unsafe_path(path_str: str) -> bool:
    if path_str.startswith("/"):
        return True
    depth = 0
    for part in Path(path_str).parts:
        if part == "..":
            depth -= 1
        elif part != ".":
            depth += 1
    return depth < 0


def validate_evidence_paths(record: dict[str, Any]) -> None:
    evidence = record.get("evidence", {})
    for key in ("focusedTest", "contactSheet", "visualReviewVerdict"):
        if key not in evidence:
            fail(f"Missing evidence field: {key}")
    for key in ("focusedTest", "contactSheet"):
        path_str = evidence.get(key, "")
        if _is_unsafe_path(path_str):
            fail(f"Absolute or path-traversal evidence path in {key}: {path_str}")


def validate_no_nondeterministic(record: dict[str, Any]) -> None:
    value = record.get("approvalDate", "")
    if not isinstance(value, str):
        fail("approvalDate must be a string")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: validate_art_approval.py <source_root>", file=sys.stderr)
        sys.exit(1)

    root = Path(sys.argv[1]).resolve()
    if not root.is_dir():
        fail(f"Not a directory: {root}")

    approval_path = root / "art-approval.json"
    packet_path = root / "art-packet.json"
    if not approval_path.exists():
        fail("art-approval.json not found")
    if not packet_path.exists():
        fail("art-packet.json not found")

    record = load_json(approval_path)
    packet = load_json(packet_path)

    validate_approval_record(record, len(packet["assets"]))
    validate_aliases_sorted(record)
    validate_approved_aliases_parity(packet, record)
    validate_all_approved(packet)
    validate_packet_hashes(packet, record, root)
    validate_source_set_sha(packet, record, root)
    validate_contact_sheet(record, root)
    validate_approved_commit(packet, record)
    validate_evidence_paths(record)
    validate_no_nondeterministic(record)

    print(
        "PASS: approval receipt matches the current source set and "
        f"{len(packet['assets'])} approved assets."
    )


if __name__ == "__main__":
    main()
