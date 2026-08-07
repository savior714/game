#!/usr/bin/env python3
"""Record one explicit Ocean Rescue art approval action.

The command computes every receipt field automatically. Source SVGs, the art
packet, and the contact sheet must already be committed. The only human action
is invoking this command after visual review.

Usage:
    python approve_art.py --approve [--output PATH]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "domains/ocean-rescue/assets/source"
PACKET_PATH = SOURCE_ROOT / "art-packet.json"
APPROVAL_PATH = SOURCE_ROOT / "art-approval.json"
CONTACT_SHEET = (
    REPO_ROOT
    / "domains/ocean-rescue/assets/review/proof-art-contact-sheet.html"
)
PACKET_VALIDATOR = Path(__file__).resolve().parent / "validate_art_packet.py"
TRACKED_APPROVAL_INPUTS = (
    "domains/ocean-rescue/assets/source/characters",
    "domains/ocean-rescue/assets/source/scene",
    "domains/ocean-rescue/assets/source/effects-ui",
    "domains/ocean-rescue/assets/source/art-packet.json",
    "domains/ocean-rescue/assets/review/proof-art-contact-sheet.html",
)


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    sys.exit(1)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        fail(f"Cannot read valid JSON from {path}: {exc}")
        return {}


def git_text(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        fail(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def ensure_reviewed_inputs_are_committed() -> None:
    status = git_text("status", "--porcelain", "--", *TRACKED_APPROVAL_INPUTS)
    if status:
        fail(
            "commit the reviewed source SVGs, art packet, and contact sheet "
            "before recording approval"
        )


def validate_packet() -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(PACKET_VALIDATOR), str(SOURCE_ROOT)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        fail(result.stderr.strip() or result.stdout.strip())
    return load_json(PACKET_PATH)


def compute_source_set_sha(packet: dict[str, Any]) -> str:
    parts = []
    for asset in sorted(packet["assets"], key=lambda item: item["alias"]):
        source_path = SOURCE_ROOT / asset["source"]
        if not source_path.exists():
            fail(f"Source file missing: {asset['source']}")
        actual_sha = sha256_bytes(source_path.read_bytes())
        if actual_sha != asset.get("sourceSha256"):
            fail(
                f"art-packet sourceSha256 is stale for {asset['alias']}; "
                "refresh the packet before approval"
            )
        if asset.get("approvalState") != "approved":
            fail(
                f"asset {asset['alias']} is {asset.get('approvalState')}, "
                "not approved"
            )
        parts.append(f"{asset['alias']}:{actual_sha}")
    return sha256_bytes(("\n".join(parts) + "\n").encode("utf-8"))


def build_receipt(packet: dict[str, Any], existing: dict[str, Any]) -> dict[str, Any]:
    if not CONTACT_SHEET.exists():
        fail(f"Contact sheet not found: {CONTACT_SHEET}")

    aliases = sorted(asset["alias"] for asset in packet["assets"])
    receipt = dict(existing)
    receipt.update(
        {
            "schemaVersion": 1,
            "packetSchemaVersion": packet.get("schemaVersion", 1),
            "decision": "approved",
            "scope": "ocean-rescue-rendering-mvp-proof-packet",
            "approvedAssetCount": len(aliases),
            "approvedAliases": aliases,
            "artPacketSha256": sha256_bytes(PACKET_PATH.read_bytes()),
            "contactSheetSha256": sha256_bytes(CONTACT_SHEET.read_bytes()),
            "sourceSetSha256": compute_source_set_sha(packet),
            "requiredPredecessor": git_text("rev-parse", "HEAD"),
            "approvalDate": datetime.now(timezone.utc).date().isoformat(),
        }
    )
    receipt.setdefault(
        "evidence",
        {
            "focusedTest": "tests/test_ocean_rescue_art_packet.py",
            "contactSheet": "domains/ocean-rescue/assets/review/proof-art-contact-sheet.html",
            "visualReviewVerdict": "PASS",
        },
    )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Record an explicit Ocean Rescue art approval"
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Confirm that the current committed contact sheet was reviewed",
    )
    parser.add_argument(
        "--output",
        default=str(APPROVAL_PATH),
        help="Approval receipt output path",
    )
    args = parser.parse_args()

    if not args.approve:
        fail("explicit --approve is required; no approval receipt was changed")

    ensure_reviewed_inputs_are_committed()
    packet = validate_packet()
    existing = load_json(APPROVAL_PATH) if APPROVAL_PATH.exists() else {}
    receipt = build_receipt(packet, existing)

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        "PASS: approval receipt recorded automatically for "
        f"{receipt['approvedAssetCount']} assets at "
        f"{receipt['requiredPredecessor']}."
    )


if __name__ == "__main__":
    main()
