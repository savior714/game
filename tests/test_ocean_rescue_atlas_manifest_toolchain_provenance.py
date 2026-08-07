"""Focused regression: atlas-manifest.json toolchain provenance must come from runtime metadata.

Failure domain: OCEAN_RESCUE_ATLAS_MANIFEST_CAN_REPORT_HARDCODED_TOOLCHAIN_VERSIONS

Before the fix, build_atlases.py wrote literal strings
  "cairosvg": "2.9.0"
  "pillow": "12.3.0"
into the manifest toolchain section. This test asserts that the values
in the manifest equal the installed distribution versions returned by
importlib.metadata.version(), so future provenance drift is caught by
the generated output contract rather than builder source inspection.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_SCRIPT = REPO_ROOT / "scripts" / "ocean_rescue" / "build_atlases.py"
ART_PACKET_JSON = (
    REPO_ROOT / "domains" / "ocean-rescue" / "assets" / "source" / "art-packet.json"
)
ART_APPROVAL_JSON = (
    REPO_ROOT / "domains" / "ocean-rescue" / "assets" / "source" / "art-approval.json"
)

ENV = {"DYLD_LIBRARY_PATH": "/opt/homebrew/opt/cairo/lib"}


def _run_builder(output_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(BUILD_SCRIPT),
            "--packet",
            str(ART_PACKET_JSON.resolve()),
            "--approval",
            str(ART_APPROVAL_JSON.resolve()),
            "--output-dir",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env={**dict(__import__("os").environ), **ENV},
    )


class TestAtlasManifestToolchainProvenance:
    def test_toolchain_versions_match_installed_distributions(self, tmp_path: Path):
        """Manifest toolchain.cairosvg/pillow must equal runtime distribution versions."""
        from importlib.metadata import version as dist_version

        output_dir = tmp_path / "output"
        result = _run_builder(output_dir)
        assert result.returncode == 0, (
            f"Atlas build failed:\n{result.stderr}\n{result.stdout}"
        )

        manifest = json.loads(
            (output_dir / "atlas-manifest.json").read_text(encoding="utf-8")
        )
        toolchain = manifest.get("toolchain", {})

        cairosvg_ver = dist_version("cairosvg")
        pillow_ver = dist_version("pillow")

        assert toolchain.get("cairosvg") == cairosvg_ver, (
            f"manifest toolchain.cairosvg={toolchain.get('cairosvg')!r} "
            f"!= installed cairosvg {cairosvg_ver!r}"
        )
        assert toolchain.get("pillow") == pillow_ver, (
            f"manifest toolchain.pillow={toolchain.get('pillow')!r} "
            f"!= installed pillow {pillow_ver!r}"
        )
