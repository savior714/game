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
from typing import Any

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

    def test_cairo_version_detection_failure_causes_build_failure(
        self, monkeypatch: Any, tmp_path: Path
    ):
        """When Cairo version detection raises, the build must fail with non-zero
        exit code and must NOT write a successful atlas-manifest.json.

        Failure domain: OCEAN_RESCUE_ATLAS_MANIFEST_CAIRO_PROVENANCE_FAILS_OPEN_TO_UNKNOWN

        The builder must not accept "unknown" as a valid provenance value.
        """
        output_dir = tmp_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        import scripts.ocean_rescue.build_atlases as build_mod

        monkeypatch.setattr(
            build_mod,
            "_get_cairo_version",
            lambda: (_ for _ in ()).throw(RuntimeError("cairo version lookup failed")),
        )

        try:
            builder = build_mod.AtlasBuilder(
                ART_PACKET_JSON, ART_APPROVAL_JSON, output_dir
            )
            builder.build()
        except SystemExit as exc:
            assert exc.code != 0, (
                "Atlas build exited with code 0 despite Cairo version detection failure"
            )
        except Exception as exc:
            assert "cairo version lookup failed" in str(exc), (
                f"Unexpected exception: {exc}"
            )
        else:
            assert False, (
                "Atlas build succeeded despite Cairo version detection failure; "
                "it must fail closed"
            )

        manifest_path = output_dir / "atlas-manifest.json"
        assert not manifest_path.exists(), (
            "Build failed but atlas-manifest.json was still written to output dir; "
            "failed builds must not publish partial manifests"
        )

    def test_cairo_provenance_is_not_unknown_literal(self, tmp_path: Path):
        """Normal successful build must never produce "unknown" as Cairo provenance."""
        output_dir = tmp_path / "output"
        result = _run_builder(output_dir)
        assert result.returncode == 0, (
            f"Atlas build failed:\n{result.stderr}\n{result.stdout}"
        )

        manifest = json.loads(
            (output_dir / "atlas-manifest.json").read_text(encoding="utf-8")
        )
        cairo_ver = manifest["toolchain"]["cairo"]
        assert cairo_ver != "unknown", (
            "manifest toolchain.cairo is 'unknown' — build must fail when "
            "Cairo version detection cannot succeed"
        )

    def test_cairo_provenance_matches_runtime_version_string(self, tmp_path: Path):
        """manifest.toolchain.cairo must equal cairocffi.cairo_version_string()."""
        import cairocffi

        output_dir = tmp_path / "output"
        result = _run_builder(output_dir)
        assert result.returncode == 0, (
            f"Atlas build failed:\n{result.stderr}\n{result.stdout}"
        )

        manifest = json.loads(
            (output_dir / "atlas-manifest.json").read_text(encoding="utf-8")
        )
        expected = str(cairocffi.cairo_version_string())
        assert manifest["toolchain"]["cairo"] == expected, (
            f"manifest toolchain.cairo={manifest['toolchain']['cairo']!r} "
            f"!= runtime cairocffi.cairo_version_string()={expected!r}"
        )
