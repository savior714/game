"""Focused tests for Ocean Rescue SVG root namespace contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_SOURCE = REPO_ROOT / "domains" / "ocean-rescue" / "assets" / "source"
VALIDATOR = REPO_ROOT / "scripts" / "ocean_rescue" / "validate_art_packet.py"


def _run_validator(packet_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(packet_dir)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def _load_packet() -> dict:
    return json.loads((ASSETS_SOURCE / "art-packet.json").read_text(encoding="utf-8"))


class TestSvgRootNamespaceContract:
    @pytest.mark.parametrize(
        "xmlns_attr, should_pass, err_substring",
        [
            ("", False, "namespace"),  # missing namespace
            (
                'xmlns="https://example.invalid/svg"',
                False,
                "namespace",
            ),  # wrong namespace
            (
                'xmlns="http://www.w3.org/2000/svg"',
                True,
                None,
            ),  # canonical SVG namespace
        ],
    )
    def test_svg_root_namespace(
        self,
        tmp_path: Path,
        xmlns_attr: str,
        should_pass: bool,
        err_substring: str | None,
    ):
        packet = _load_packet()
        svg_content = (
            f'<svg {xmlns_attr} viewBox="0 0 100 100">\n'
            '  <rect width="100" height="100"/>\n'
            "</svg>"
        )

        import hashlib

        modified_hash = hashlib.sha256(svg_content.encode("utf-8")).hexdigest()

        modified_packet = json.loads(json.dumps(packet))
        for asset in modified_packet["assets"]:
            if asset["alias"] == "otter.head":
                asset["sourceSha256"] = modified_hash

        test_dir = tmp_path / "ns_test_dir"
        test_dir.mkdir()
        (test_dir / "art-packet.json").write_text(
            json.dumps(modified_packet, indent=2), encoding="utf-8"
        )
        for asset in packet["assets"]:
            if asset["alias"] == "otter.head":
                dst = test_dir / asset["source"]
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(svg_content, encoding="utf-8")
            else:
                src = ASSETS_SOURCE / asset["source"]
                dst = test_dir / asset["source"]
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())

        result = _run_validator(test_dir)
        if should_pass:
            assert result.returncode == 0, f"Expected PASS but failed:\n{result.stderr}"
        else:
            assert result.returncode != 0, (
                "Validator must reject invalid/missing SVG namespace"
            )
            if err_substring:
                assert err_substring.lower() in result.stderr.lower(), (
                    f"Expected '{err_substring}' in error message:\n{result.stderr}"
                )
