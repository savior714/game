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
ART_APPROVAL_JSON = ASSETS_SOURCE / "art-approval.json"
VALIDATOR = REPO_ROOT / "scripts" / "ocean_rescue" / "validate_art_packet.py"
CONTACT_SHEET_BUILDER = (
    REPO_ROOT / "scripts" / "ocean_rescue" / "build_art_contact_sheet.py"
)
CONTACT_SHEET = (
    REPO_ROOT
    / "domains"
    / "ocean-rescue"
    / "assets"
    / "review"
    / "proof-art-contact-sheet.html"
)

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


def _run_contact_sheet_builder(
    packet_dir: Path | None = None, output: Path | None = None
) -> subprocess.CompletedProcess:
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
        assert ART_PACKET_JSON.exists(), (
            "art-packet.json must exist in canonical source directory"
        )

    def test_validator_script_exists(self):
        assert VALIDATOR.exists(), "validate_art_packet.py must exist"

    def test_contact_sheet_builder_exists(self):
        assert CONTACT_SHEET_BUILDER.exists(), "build_art_contact_sheet.py must exist"

    def test_canonical_validator_passes(self):
        result = _run_validator()
        assert result.returncode == 0, (
            f"Validator must pass on canonical packet:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )


class TestAliasContract:
    def test_packet_aliases_match_approved_aliases(self):
        packet = _load_packet()
        approval = json.loads(ART_APPROVAL_JSON.read_text(encoding="utf-8"))
        aliases = sorted(a["alias"] for a in packet["assets"])
        approved = approval["approvedAliases"]
        assert approved == sorted(approved), "approvedAliases must be sorted"
        assert len(set(approved)) == len(approved), "approvedAliases must be unique"
        assert aliases == approved, (
            f"Packet aliases must exactly match approval aliases:\n"
            f"missing: {set(approved) - set(aliases)}\n"
            f"extra: {set(aliases) - set(approved)}"
        )


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
        (dup_dir / "art-packet.json").write_text(
            json.dumps(dup_packet, indent=2), encoding="utf-8"
        )
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
        (tampered_dir / "art-packet.json").write_text(
            json.dumps(tampered, indent=2), encoding="utf-8"
        )
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
        (traversal_dir / "art-packet.json").write_text(
            json.dumps(traversal, indent=2), encoding="utf-8"
        )
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
        (bad_dir / "art-packet.json").write_text(
            json.dumps(packet, indent=2), encoding="utf-8"
        )
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

    def test_svg_with_foreignobject_rejected(self, tmp_path: Path):
        packet = _load_packet()
        svg_content = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">\n'
            '  <rect width="100" height="100"/>\n'
            '  <foreignObject x="0" y="0" width="100" height="100">\n'
            '    <div xmlns="http://www.w3.org/1999/xhtml">unsafe</div>\n'
            "  </foreignObject>\n"
            "</svg>"
        )
        bad_dir = tmp_path / "foreignobject_svg"
        bad_dir.mkdir()

        # calculate sha256 of modified svg
        import hashlib

        modified_hash = hashlib.sha256(svg_content.encode("utf-8")).hexdigest()

        modified_packet = json.loads(json.dumps(packet))
        for asset in modified_packet["assets"]:
            if asset["alias"] == "otter.head":
                asset["sourceSha256"] = modified_hash

        (bad_dir / "art-packet.json").write_text(
            json.dumps(modified_packet, indent=2), encoding="utf-8"
        )
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
        assert result.returncode != 0, "Validator must reject SVG with <foreignObject>"
        assert (
            "Forbidden element <foreignObject>" in result.stderr
            or "foreignobject" in result.stderr.lower()
        )

    @pytest.mark.parametrize("event_attr", ["onfocus", "onauxclick", "onpointerenter"])
    def test_svg_with_unlisted_on_event_attributes_rejected(
        self, tmp_path: Path, event_attr: str
    ):
        packet = _load_packet()
        svg_content = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">\n'
            f'  <rect width="100" height="100" {event_attr}="alert(1)"/>\n'
            f"</svg>"
        )
        bad_dir = tmp_path / f"bad_svg_{event_attr}"
        bad_dir.mkdir()

        import hashlib

        modified_hash = hashlib.sha256(svg_content.encode("utf-8")).hexdigest()

        modified_packet = json.loads(json.dumps(packet))
        for asset in modified_packet["assets"]:
            if asset["alias"] == "otter.head":
                asset["sourceSha256"] = modified_hash

        (bad_dir / "art-packet.json").write_text(
            json.dumps(modified_packet, indent=2), encoding="utf-8"
        )
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
        assert result.returncode != 0, f"Validator must reject SVG with {event_attr}"
        assert f"Forbidden attribute '{event_attr}'" in result.stderr

    def test_svg_with_valid_non_event_attributes_passes(self, tmp_path: Path):
        packet = _load_packet()
        svg_content = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">\n'
            '  <rect width="100" height="100" fill="#ff0000" opacity="0.8"/>\n'
            "</svg>"
        )
        valid_dir = tmp_path / "valid_svg_attrs"
        valid_dir.mkdir()

        import hashlib

        modified_hash = hashlib.sha256(svg_content.encode("utf-8")).hexdigest()

        modified_packet = json.loads(json.dumps(packet))
        for asset in modified_packet["assets"]:
            if asset["alias"] == "otter.head":
                asset["sourceSha256"] = modified_hash

        (valid_dir / "art-packet.json").write_text(
            json.dumps(modified_packet, indent=2), encoding="utf-8"
        )
        for asset in packet["assets"]:
            if asset["alias"] == "otter.head":
                dst = valid_dir / asset["source"]
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(svg_content, encoding="utf-8")
            else:
                src = ASSETS_SOURCE / asset["source"]
                dst = valid_dir / asset["source"]
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())

        result = _run_validator(valid_dir)
        assert result.returncode == 0, (
            f"Validator must pass on valid attributes: {result.stderr}"
        )


class TestInvalidPivotRejection:
    def test_out_of_range_pivot_rejected(self, tmp_path: Path):
        packet = _load_packet()
        bad_pivot = json.loads(json.dumps(packet))
        bad_pivot["assets"][0]["pivot"] = [1.5, 0.5]
        bad_dir = tmp_path / "bad_pivot"
        bad_dir.mkdir()
        (bad_dir / "art-packet.json").write_text(
            json.dumps(bad_pivot, indent=2), encoding="utf-8"
        )
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
        assert out1.read_bytes() == out2.read_bytes(), (
            "Two independent builds must be byte-identical"
        )

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
                    [
                        "git",
                        "diff",
                        "--name-only",
                        "HEAD",
                        "--",
                        str(forbidden_path.relative_to(REPO_ROOT)),
                    ],
                    capture_output=True,
                    text=True,
                    cwd=str(REPO_ROOT),
                )
                assert not result.stdout.strip(), (
                    f"Runtime/build file changed: {forbidden_path}"
                )
