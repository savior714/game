"""Focused tests for Ocean Rescue proof-art production approval gate."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_SOURCE = REPO_ROOT / "domains" / "ocean-rescue" / "assets" / "source"
ART_PACKET_JSON = ASSETS_SOURCE / "art-packet.json"
ART_APPROVAL_JSON = ASSETS_SOURCE / "art-approval.json"
CONTACT_SHEET = (
    REPO_ROOT
    / "domains"
    / "ocean-rescue"
    / "assets"
    / "review"
    / "proof-art-contact-sheet.html"
)
VALIDATOR_PACKET = REPO_ROOT / "scripts" / "ocean_rescue" / "validate_art_packet.py"
VALIDATOR_APPROVAL = REPO_ROOT / "scripts" / "ocean_rescue" / "validate_art_approval.py"
CONTACT_SHEET_BUILDER = (
    REPO_ROOT / "scripts" / "ocean_rescue" / "build_art_contact_sheet.py"
)

PREDECESSOR_COMMIT = "HEAD"


def _run_validator(script: Path, target: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), str(target)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_packet_aliases() -> list[str]:
    return sorted(a["alias"] for a in _load_json(ART_PACKET_JSON)["assets"])


def _build_contact_sheet(output: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(CONTACT_SHEET_BUILDER),
            str(ASSETS_SOURCE),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


class TestPreFixReproduction:
    def test_current_packet_has_all_approved_assets(self):
        packet = _load_json(ART_PACKET_JSON)
        for asset in packet["assets"]:
            assert asset["approvalState"] == "approved", (
                f"Asset {asset['alias']} is {asset['approvalState']}, not approved"
            )

    def test_approval_record_exists(self):
        assert ART_APPROVAL_JSON.exists(), "art-approval.json must exist"

    def test_approval_record_passes_validator(self):
        result = _run_validator(VALIDATOR_APPROVAL, ASSETS_SOURCE)
        assert result.returncode == 0, (
            f"Approval validator must pass on canonical state:\n{result.stderr}"
        )


class TestApprovedAssetCount:
    def test_approved_asset_count_matches_packet(self):
        packet = _load_json(ART_PACKET_JSON)
        record = _load_json(ART_APPROVAL_JSON)
        approved = [a for a in packet["assets"] if a["approvalState"] == "approved"]
        assert len(approved) == len(packet["assets"]), (
            "All packet assets must be approved"
        )
        assert record["approvedAssetCount"] == len(packet["assets"]), (
            f"approvedAssetCount {record['approvedAssetCount']} != packet count "
            f"{len(packet['assets'])}"
        )

    def test_approved_asset_count_matches_approved_aliases(self):
        record = _load_json(ART_APPROVAL_JSON)
        assert record["approvedAssetCount"] == len(record["approvedAliases"]), (
            f"approvedAssetCount {record['approvedAssetCount']} != approvedAliases "
            f"count {len(record['approvedAliases'])}"
        )

    def test_approved_aliases_are_unique(self):
        record = _load_json(ART_APPROVAL_JSON)
        assert len(set(record["approvedAliases"])) == len(record["approvedAliases"]), (
            "approvedAliases must be unique"
        )

    def test_all_aliases_match_packet(self):
        record = _load_json(ART_APPROVAL_JSON)
        packet_aliases = _canonical_packet_aliases()
        assert record["approvedAliases"] == packet_aliases, (
            "approvedAliases does not match packet aliases"
        )


class TestSourceByteFreeze:
    def test_source_unchanged_from_predecessor(self):
        result = subprocess.run(
            [
                "git",
                "diff",
                "--exit-code",
                PREDECESSOR_COMMIT,
                "--",
                "domains/ocean-rescue/assets/source/characters",
                "domains/ocean-rescue/assets/source/scene",
                "domains/ocean-rescue/assets/source/effects-ui",
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, (
            f"Source SVGs changed from predecessor:\n{result.stdout}{result.stderr}"
        )

    def test_source_hashes_match_actual_bytes(self):
        packet = _load_json(ART_PACKET_JSON)
        for asset in packet["assets"]:
            source_path = ASSETS_SOURCE / asset["source"]
            assert source_path.exists(), f"Source missing: {asset['source']}"
            actual = _sha256_file(source_path)
            assert actual == asset["sourceSha256"], (
                f"Hash mismatch for {asset['alias']}: "
                f"record={asset['sourceSha256'][:16]}... actual={actual[:16]}..."
            )


class TestPacketShaIntegrity:
    def test_packet_sha_matches_record(self):
        record = _load_json(ART_APPROVAL_JSON)
        actual = _sha256_file(ART_PACKET_JSON)
        assert actual == record["artPacketSha256"], (
            f"Packet SHA mismatch: record={record['artPacketSha256'][:16]}... "
            f"actual={actual[:16]}..."
        )


class TestContactSheetIntegrity:
    def test_contact_sheet_sha_matches_record(self):
        record = _load_json(ART_APPROVAL_JSON)
        assert CONTACT_SHEET.exists(), "Contact sheet not found"
        actual = _sha256_file(CONTACT_SHEET)
        assert actual == record["contactSheetSha256"], (
            f"Contact sheet SHA mismatch: record={record['contactSheetSha256'][:16]}... "
            f"actual={actual[:16]}..."
        )

    def test_clean_rebuild_matches_tracked(self, tmp_path: Path):
        if not CONTACT_SHEET_BUILDER.exists():
            pytest.skip("Contact sheet builder not available")
        rebuild = tmp_path / "rebuild.html"
        result = _build_contact_sheet(rebuild)
        assert result.returncode == 0, f"Rebuild failed:\n{result.stderr}"
        assert CONTACT_SHEET.read_bytes() == rebuild.read_bytes(), (
            "Tracked contact sheet differs from clean rebuild"
        )


class TestSourceSetSha:
    def test_source_set_sha_deterministic(self):
        record = _load_json(ART_APPROVAL_JSON)
        packet = _load_json(ART_PACKET_JSON)
        parts = []
        for asset in sorted(packet["assets"], key=lambda a: a["alias"]):
            src = ASSETS_SOURCE / asset["source"]
            sha = _sha256_file(src)
            parts.append(f"{asset['alias']}:{sha}")
        canonical = "\n".join(parts) + "\n"
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        assert expected == record["sourceSetSha256"], (
            f"sourceSetSha256 mismatch: record={record['sourceSetSha256'][:16]}... "
            f"expected={expected[:16]}..."
        )


class TestNegativeFixtures:
    def _make_fixture(
        self,
        tmp_path: Path,
        packet_mods: dict | None = None,
        approval_mods: dict | None = None,
    ) -> Path:
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()
        packet = _load_json(ART_PACKET_JSON)
        if packet_mods:
            for key, val in packet_mods.items():
                if key == "approvalState_all":
                    for a in packet["assets"]:
                        a["approvalState"] = val
                else:
                    packet[key] = val
        (fixture_dir / "art-packet.json").write_text(
            json.dumps(packet, indent=2), encoding="utf-8"
        )
        for asset in packet["assets"]:
            src = ASSETS_SOURCE / asset["source"]
            dst = fixture_dir / asset["source"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
        if approval_mods:
            record = _load_json(ART_APPROVAL_JSON)
            for key, val in approval_mods.items():
                record[key] = val
            (fixture_dir / "art-approval.json").write_text(
                json.dumps(record, indent=2), encoding="utf-8"
            )
        else:
            import shutil

            shutil.copy2(ART_APPROVAL_JSON, fixture_dir / "art-approval.json")
        return fixture_dir

    def test_altered_packet_hash_rejected(self, tmp_path: Path):
        fixture = self._make_fixture(
            tmp_path, approval_mods={"artPacketSha256": "0" * 64}
        )
        result = _run_validator(VALIDATOR_APPROVAL, fixture)
        assert result.returncode != 0, "Validator must reject altered packet hash"

    def test_altered_contact_sheet_hash_rejected(self, tmp_path: Path):
        fixture = self._make_fixture(
            tmp_path, approval_mods={"contactSheetSha256": "0" * 64}
        )
        result = _run_validator(VALIDATOR_APPROVAL, fixture)
        assert result.returncode != 0, (
            "Validator must reject altered contact-sheet hash"
        )

    def test_altered_source_set_hash_rejected(self, tmp_path: Path):
        fixture = self._make_fixture(
            tmp_path, approval_mods={"sourceSetSha256": "0" * 64}
        )
        result = _run_validator(VALIDATOR_APPROVAL, fixture)
        assert result.returncode != 0, "Validator must reject altered source-set hash"

    def test_missing_alias_rejected(self, tmp_path: Path):
        aliases = _canonical_packet_aliases()
        fixture = self._make_fixture(
            tmp_path, approval_mods={"approvedAliases": aliases[:-1]}
        )
        result = _run_validator(VALIDATOR_APPROVAL, fixture)
        assert result.returncode != 0, "Validator must reject missing alias"

    def test_extra_alias_rejected(self, tmp_path: Path):
        aliases = _canonical_packet_aliases()
        fixture = self._make_fixture(
            tmp_path, approval_mods={"approvedAliases": aliases + ["zzz.extra"]}
        )
        result = _run_validator(VALIDATOR_APPROVAL, fixture)
        assert result.returncode != 0, "Validator must reject extra alias"

    def test_duplicate_alias_rejected(self, tmp_path: Path):
        aliases = _canonical_packet_aliases()
        dup = aliases.copy()
        dup.append(dup[0])
        fixture = self._make_fixture(
            tmp_path, approval_mods={"approvedAliases": sorted(dup)}
        )
        result = _run_validator(VALIDATOR_APPROVAL, fixture)
        assert result.returncode != 0, "Validator must reject duplicate alias"

    def test_unsorted_aliases_rejected(self, tmp_path: Path):
        aliases = _canonical_packet_aliases()
        swapped = aliases.copy()
        swapped[0], swapped[1] = swapped[1], swapped[0]
        fixture = self._make_fixture(
            tmp_path, approval_mods={"approvedAliases": swapped}
        )
        result = _run_validator(VALIDATOR_APPROVAL, fixture)
        assert result.returncode != 0, "Validator must reject unsorted aliases"

    def test_count_too_small_rejected(self, tmp_path: Path):
        fixture = self._make_fixture(tmp_path, approval_mods={"approvedAssetCount": 52})
        result = _run_validator(VALIDATOR_APPROVAL, fixture)
        assert result.returncode != 0, "Validator must reject too-small count"

    def test_count_too_large_rejected(self, tmp_path: Path):
        fixture = self._make_fixture(tmp_path, approval_mods={"approvedAssetCount": 54})
        result = _run_validator(VALIDATOR_APPROVAL, fixture)
        assert result.returncode != 0, "Validator must reject too-large count"

    def test_one_review_ready_rejected(self, tmp_path: Path):
        fixture = self._make_fixture(
            tmp_path, packet_mods={"approvalState_all": "review-ready"}
        )
        result = _run_validator(VALIDATOR_APPROVAL, fixture)
        assert result.returncode != 0, (
            "Validator must reject when any asset is review-ready"
        )

    def test_invalid_decision_rejected(self, tmp_path: Path):
        fixture = self._make_fixture(tmp_path, approval_mods={"decision": "pending"})
        result = _run_validator(VALIDATOR_APPROVAL, fixture)
        assert result.returncode != 0, "Validator must reject invalid decision"

    def test_absolute_path_evidence_rejected(self, tmp_path: Path):
        fixture = self._make_fixture(
            tmp_path,
            approval_mods={
                "evidence": {
                    "focusedTest": "tests/test.py",
                    "contactSheet": "/etc/passwd",
                    "visualReviewVerdict": "PASS",
                }
            },
        )
        result = _run_validator(VALIDATOR_APPROVAL, fixture)
        assert result.returncode != 0, "Validator must reject absolute evidence path"

    def test_path_traversal_evidence_rejected(self, tmp_path: Path):
        fixture = self._make_fixture(
            tmp_path,
            approval_mods={
                "evidence": {
                    "focusedTest": "tests/test.py",
                    "contactSheet": "../../etc/passwd",
                    "visualReviewVerdict": "PASS",
                }
            },
        )
        result = _run_validator(VALIDATOR_APPROVAL, fixture)
        assert result.returncode != 0, (
            "Validator must reject path-traversal evidence path"
        )
