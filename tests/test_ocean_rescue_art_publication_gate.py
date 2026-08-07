"""Focused tests for the Ocean Rescue art publication receipt."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = REPO_ROOT / "domains/ocean-rescue/assets/source"
GENERATED_DIR = REPO_ROOT / "domains/ocean-rescue/assets/generated"
PACKET_PATH = SOURCE_ROOT / "art-packet.json"
APPROVAL_PATH = SOURCE_ROOT / "art-approval.json"
APPROVER = REPO_ROOT / "scripts/ocean_rescue/approve_art.py"
REGISTRY_BUILDER = (
    REPO_ROOT / "scripts/ocean_rescue/build_render_assets_registry.py"
)
VALIDATOR = REPO_ROOT / "scripts/ocean_rescue/validate_art_approval.py"
CONTACT_SHEET = (
    REPO_ROOT
    / "domains/ocean-rescue/assets/review/proof-art-contact-sheet.html"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def _approval_fixture(tmp_path: Path, predecessor: str) -> Path:
    root = tmp_path / "fixture/source"
    root.mkdir(parents=True)
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    shutil.copy2(PACKET_PATH, root / "art-packet.json")
    approval = json.loads(APPROVAL_PATH.read_text(encoding="utf-8"))
    approval["requiredPredecessor"] = predecessor
    (root / "art-approval.json").write_text(
        json.dumps(approval, indent=2) + "\n",
        encoding="utf-8",
    )
    for asset in packet["assets"]:
        source = SOURCE_ROOT / asset["source"]
        target = root / asset["source"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    review = root.parent / "review"
    review.mkdir()
    shutil.copy2(CONTACT_SHEET, review / "proof-art-contact-sheet.html")
    return root


def _aligned_atlas_fixture(tmp_path: Path) -> Path:
    atlas_dir = tmp_path / "generated"
    shutil.copytree(GENERATED_DIR, atlas_dir)
    manifest_path = atlas_dir / "atlas-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    approval = json.loads(APPROVAL_PATH.read_text(encoding="utf-8"))
    manifest["sourcePacketSha256"] = _sha256(PACKET_PATH)
    manifest["approvalRecordSha256"] = _sha256(APPROVAL_PATH)
    manifest["sourceSetSha256"] = approval["sourceSetSha256"]
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return atlas_dir


def test_approval_command_requires_one_explicit_action(tmp_path: Path):
    output = tmp_path / "approval.json"
    result = _run(str(APPROVER), "--output", str(output))
    assert result.returncode != 0
    assert not output.exists()
    assert "explicit --approve is required" in result.stderr


def test_approval_command_records_hashes_and_current_commit(tmp_path: Path):
    output = tmp_path / "approval.json"
    result = _run(
        str(APPROVER),
        "--approve",
        "--output",
        str(output),
    )
    assert result.returncode == 0, result.stderr
    receipt = json.loads(output.read_text(encoding="utf-8"))
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(REPO_ROOT),
    ).stdout.strip()
    assert receipt["requiredPredecessor"] == head
    assert receipt["artPacketSha256"] == _sha256(PACKET_PATH)
    assert receipt["contactSheetSha256"]
    assert receipt["sourceSetSha256"]
    assert receipt["decision"] == "approved"


def test_registry_accepts_atlas_aligned_to_current_approval(tmp_path: Path):
    atlas_dir = _aligned_atlas_fixture(tmp_path)
    output = tmp_path / "registry.js"
    result = _run(
        str(REGISTRY_BUILDER),
        "--atlas-dir",
        str(atlas_dir),
        "--output",
        str(output),
    )
    assert result.returncode == 0, result.stderr
    assert output.exists()


def test_registry_rejects_stale_atlas_source_hash(tmp_path: Path):
    atlas_dir = _aligned_atlas_fixture(tmp_path)
    manifest_path = atlas_dir / "atlas-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sourceSetSha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "registry.js"
    result = _run(
        str(REGISTRY_BUILDER),
        "--atlas-dir",
        str(atlas_dir),
        "--output",
        str(output),
    )
    assert result.returncode != 0
    assert "rebuild required" in result.stderr
    assert not output.exists()


def test_validator_rejects_source_commit_from_before_current_art(tmp_path: Path):
    fixture = _approval_fixture(
        tmp_path,
        "163b3206399c051b516c121c6c8c0ca4bd19268a",
    )
    result = _run(str(VALIDATOR), str(fixture))
    assert result.returncode != 0
    assert "reapproval required" in result.stderr


def test_validator_requires_full_approved_source_commit(tmp_path: Path):
    fixture = _approval_fixture(tmp_path, "HEAD")
    result = _run(str(VALIDATOR), str(fixture))
    assert result.returncode != 0
    assert "requiredPredecessor" in result.stderr
