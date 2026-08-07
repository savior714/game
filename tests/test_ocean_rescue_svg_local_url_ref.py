"""Focused tests for Ocean Rescue SVG local url(#id) reference validation."""

from __future__ import annotations

import json
import subprocess
import sys

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_SOURCE = REPO_ROOT / "domains" / "ocean-rescue" / "assets" / "source"
VALIDATOR = REPO_ROOT / "scripts" / "ocean_rescue" / "validate_art_packet.py"

VALID_SVG_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <linearGradient id="paint"/>
    <clipPath id="clip1"/>
    <mask id="mask1"/>
    <filter id="filter1"/>
  </defs>
  <rect width="100" height="100" {attr}/>
</svg>
"""

MISSING_SVG_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" {attr}/>
</svg>
"""


def _setup_mock_packet(tmp_path: Path, svg_content: str) -> Path:
    packet_dir = tmp_path / "source"
    packet_dir.mkdir()

    svg_file = packet_dir / "test.svg"
    svg_file.write_text(svg_content, encoding="utf-8")

    import hashlib

    svg_hash = hashlib.sha256(svg_file.read_bytes()).hexdigest()

    packet = {
        "schemaVersion": 1,
        "logicalViewport": [1280, 720],
        "declaredRasterScale": 2,
        "paletteVersion": "1.0",
        "assets": [
            {
                "id": "test-asset",
                "alias": "test.asset",
                "source": "test.svg",
                "sourceType": "svg",
                "bundle": "scene",
                "logicalSize": [100, 100],
                "declaredRasterScale": 2,
                "pivot": [0.5, 0.5],
                "authoringMethod": "manual",
                "approvalState": "approved",
                "revisionNote": "initial",
                "sourceSha256": svg_hash,
            }
        ],
    }

    (packet_dir / "art-packet.json").write_text(
        json.dumps(packet, indent=2), encoding="utf-8"
    )
    return packet_dir


def _run_validator(packet_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(packet_dir)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


class TestSvgLocalUrlRefValidation:
    @pytest.mark.parametrize(
        ("attr", "missing_id"),
        [
            ('fill="url(#missing-gradient)"', "missing-gradient"),
            ('clip-path="url(#missing-clip)"', "missing-clip"),
            ('mask="url(#missing-mask)"', "missing-mask"),
            ('filter="url(#missing-filter)"', "missing-filter"),
        ],
    )
    def test_missing_local_url_reference_rejects(
        self, tmp_path: Path, attr: str, missing_id: str
    ):
        svg_content = MISSING_SVG_TEMPLATE.format(attr=attr)
        packet_dir = _setup_mock_packet(tmp_path, svg_content)
        proc = _run_validator(packet_dir)
        assert proc.returncode != 0
        assert (
            f"Missing local url reference target '{missing_id}' in: test.svg"
            in proc.stderr
        )

    @pytest.mark.parametrize(
        "attr",
        [
            'fill="url(#paint)"',
            'clip-path="url(#clip1)"',
            'mask="url(#mask1)"',
            'filter="url(#filter1)"',
        ],
    )
    def test_valid_existing_local_url_reference_passes(self, tmp_path: Path, attr: str):
        svg_content = VALID_SVG_TEMPLATE.format(attr=attr)
        packet_dir = _setup_mock_packet(tmp_path, svg_content)
        proc = _run_validator(packet_dir)
        assert proc.returncode == 0, proc.stderr

    @pytest.mark.parametrize(
        "attr",
        [
            'fill="#ff0000"',
            'stroke="blue"',
            'x="10"',
            'opacity="0.5"',
        ],
    )
    def test_general_svg_attribute_passes(self, tmp_path: Path, attr: str):
        svg_content = MISSING_SVG_TEMPLATE.format(attr=attr)
        packet_dir = _setup_mock_packet(tmp_path, svg_content)
        proc = _run_validator(packet_dir)
        assert proc.returncode == 0, proc.stderr

    def test_canonical_assets_pass(self):
        proc = _run_validator(ASSETS_SOURCE)
        assert proc.returncode == 0, proc.stderr
        assert "53 assets validated." in proc.stdout
