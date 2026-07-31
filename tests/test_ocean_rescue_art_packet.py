"""Focused tests for Ocean Rescue proof-art packet."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_SOURCE = REPO_ROOT / "domains" / "ocean-rescue" / "assets" / "source"
ART_PACKET_JSON = ASSETS_SOURCE / "art-packet.json"
VALIDATOR = REPO_ROOT / "scripts" / "ocean_rescue" / "validate_art_packet.py"
CONTACT_SHEET_BUILDER = REPO_ROOT / "scripts" / "ocean_rescue" / "build_art_contact_sheet.py"
CONTACT_SHEET = REPO_ROOT / "domains" / "ocean-rescue" / "assets" / "review" / "proof-art-contact-sheet.html"

REQUIRED_ALIASES = sorted([
    "otter.head",
    "otter.torso",
    "otter.arm.near",
    "otter.arm.far",
    "otter.tail",
    "otter.eyes.open",
    "otter.eyes.closed",
    "otter.mouth.neutral",
    "otter.mouth.concern",
    "otter.mouth.smile",
    "turtle.worried",
    "turtle.free",
    "scene.submarine",
    "scene.water.far",
    "scene.reef.mid",
    "scene.coral.foreground",
    "scene.seaweed-loop.01",
    "scene.sand-path",
    "scene.passage",
    "ui.drag-arrow",
    "fx.success-burst",
    "fx.cut-ring",
    "fx.cut-icon",
    "fx.bubbles",
    "fx.caustic",
    "hud.progress-cap",
    "hud.loop-icon",
])

RUNTIME_FORBIDDEN_PATHS = [
    REPO_ROOT / "shared",
]


def _run_validator(packet_dir: Path | None = None) -> subprocess.CompletedProcess:
    target = packet_dir or ASSETS_SOURCE
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(target)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def _run_contact_sheet_builder(packet_dir: Path | None = None, output: Path | None = None) -> subprocess.CompletedProcess:
    target = packet_dir or ASSETS_SOURCE
    cmd = [sys.executable, str(CONTACT_SHEET_BUILDER), str(target)]
    if output:
        cmd.extend(["--output", str(output)])
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))


def _load_packet(packet_dir: Path | None = None) -> dict:
    target = packet_dir or ASSETS_SOURCE
    return json.loads((target / "art-packet.json").read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestPreFixReproduction:
    def test_art_packet_json_exists(self):
        assert ART_PACKET_JSON.exists(), "art-packet.json must exist in canonical source directory"

    def test_validator_script_exists(self):
        assert VALIDATOR.exists(), "validate_art_packet.py must exist"

    def test_contact_sheet_builder_exists(self):
        assert CONTACT_SHEET_BUILDER.exists(), "build_art_contact_sheet.py must exist"

    def test_canonical_validator_passes(self):
        result = _run_validator()
        assert result.returncode == 0, f"Validator must pass on canonical packet:\nstdout: {result.stdout}\nstderr: {result.stderr}"


class TestRequiredAliasSet:
    def test_all_required_aliases_present(self):
        packet = _load_packet()
        aliases = sorted(a["alias"] for a in packet["assets"])
        for required in REQUIRED_ALIASES:
            assert required in aliases, f"Missing required alias: {required}"

    def test_no_extra_aliases(self):
        packet = _load_packet()
        aliases = sorted(a["alias"] for a in packet["assets"])
        assert aliases == REQUIRED_ALIASES, f"Alias set mismatch:\nextra: {set(aliases) - set(REQUIRED_ALIASES)}\nmissing: {set(REQUIRED_ALIASES) - set(aliases)}"


class TestSourceHashIntegrity:
    def test_source_hashes_match_actual_bytes(self):
        packet = _load_packet()
        for asset in packet["assets"]:
            source_path = ASSETS_SOURCE / asset["source"]
            assert source_path.exists(), f"Source file missing: {asset['source']}"
            actual_hash = _sha256_file(source_path)
            assert actual_hash == asset["sourceSha256"], (
                f"Hash mismatch for {asset['alias']}: "
                f"declared={asset['sourceSha256'][:16]}... actual={actual_hash[:16]}..."
            )


class TestDuplicateAliasRejection:
    def test_duplicate_alias_rejected(self, tmp_path: Path):
        packet = _load_packet()
        dup_packet = json.loads(json.dumps(packet))
        dup_packet["assets"][1]["alias"] = dup_packet["assets"][0]["alias"]
        dup_dir = tmp_path / "dup"
        dup_dir.mkdir()
        (dup_dir / "art-packet.json").write_text(json.dumps(dup_packet, indent=2), encoding="utf-8")
        for asset in packet["assets"]:
            src = ASSETS_SOURCE / asset["source"]
            dst = dup_dir / asset["source"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
        result = _run_validator(dup_dir)
        assert result.returncode != 0, "Validator must reject duplicate aliases"


class TestHashMismatchRejection:
    def test_hash_mismatch_rejected(self, tmp_path: Path):
        packet = _load_packet()
        tampered = json.loads(json.dumps(packet))
        tampered["assets"][0]["sourceSha256"] = "0" * 64
        tampered_dir = tmp_path / "hash_mismatch"
        tampered_dir.mkdir()
        (tampered_dir / "art-packet.json").write_text(json.dumps(tampered, indent=2), encoding="utf-8")
        for asset in packet["assets"]:
            src = ASSETS_SOURCE / asset["source"]
            dst = tampered_dir / asset["source"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
        result = _run_validator(tampered_dir)
        assert result.returncode != 0, "Validator must reject hash mismatch"


class TestPathTraversalRejection:
    def test_path_traversal_rejected(self, tmp_path: Path):
        packet = _load_packet()
        traversal = json.loads(json.dumps(packet))
        traversal["assets"][0]["source"] = "../../../etc/passwd"
        traversal_dir = tmp_path / "traversal"
        traversal_dir.mkdir()
        (traversal_dir / "art-packet.json").write_text(json.dumps(traversal, indent=2), encoding="utf-8")
        for asset in packet["assets"][1:]:
            src = ASSETS_SOURCE / asset["source"]
            dst = traversal_dir / asset["source"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
        result = _run_validator(traversal_dir)
        assert result.returncode != 0, "Validator must reject path traversal"


class TestForbiddenSvgContentRejection:
    def test_svg_with_script_rejected(self, tmp_path: Path):
        packet = _load_packet()
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><script>alert("xss")</script><circle cx="50" cy="50" r="40"/></svg>'
        bad_dir = tmp_path / "bad_svg"
        bad_dir.mkdir()
        (bad_dir / "art-packet.json").write_text(json.dumps(packet, indent=2), encoding="utf-8")
        for asset in packet["assets"]:
            if asset["alias"] == "otter.head":
                dst = bad_dir / asset["source"]
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(svg_content, encoding="utf-8")
            else:
                src = ASSETS_SOURCE / asset["source"]
                dst = bad_dir / asset["source"]
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())
        result = _run_validator(bad_dir)
        assert result.returncode != 0, "Validator must reject SVG with <script>"


class TestInvalidPivotRejection:
    def test_out_of_range_pivot_rejected(self, tmp_path: Path):
        packet = _load_packet()
        bad_pivot = json.loads(json.dumps(packet))
        bad_pivot["assets"][0]["pivot"] = [1.5, 0.5]
        bad_dir = tmp_path / "bad_pivot"
        bad_dir.mkdir()
        (bad_dir / "art-packet.json").write_text(json.dumps(bad_pivot, indent=2), encoding="utf-8")
        for asset in packet["assets"]:
            src = ASSETS_SOURCE / asset["source"]
            dst = bad_dir / asset["source"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
        result = _run_validator(bad_dir)
        assert result.returncode != 0, "Validator must reject pivot outside [0,1]"


class TestContactSheetDeterminism:
    def test_two_independent_builds_are_byte_identical(self, tmp_path: Path):
        out1 = tmp_path / "sheet1.html"
        out2 = tmp_path / "sheet2.html"
        r1 = _run_contact_sheet_builder(output=out1)
        assert r1.returncode == 0, f"First build failed:\n{r1.stderr}"
        r2 = _run_contact_sheet_builder(output=out2)
        assert r2.returncode == 0, f"Second build failed:\n{r2.stderr}"
        assert out1.read_bytes() == out2.read_bytes(), "Two independent builds must be byte-identical"

    def test_tracked_sheet_matches_clean_rebuild(self, tmp_path: Path):
        if not CONTACT_SHEET.exists():
            pytest.skip("Tracked contact sheet not yet generated")
        rebuild = tmp_path / "rebuild.html"
        r = _run_contact_sheet_builder(output=rebuild)
        assert r.returncode == 0, f"Rebuild failed:\n{r.stderr}"
        assert CONTACT_SHEET.read_bytes() == rebuild.read_bytes(), (
            "Tracked contact sheet must be byte-identical to a clean rebuild"
        )


class TestRuntimePathScope:
    def test_no_runtime_files_changed(self):
        for forbidden_path in RUNTIME_FORBIDDEN_PATHS:
            if forbidden_path.is_file():
                result = subprocess.run(
                    ["git", "diff", "--name-only", "HEAD", "--", str(forbidden_path.relative_to(REPO_ROOT))],
                    capture_output=True, text=True, cwd=str(REPO_ROOT),
                )
                assert not result.stdout.strip(), f"Runtime/build file changed: {forbidden_path}"
