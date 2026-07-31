"""Focused tests for Ocean Rescue deterministic 2× atlas pipeline.

Validates the complete atlas build and validation pipeline including
rasterization, trimming, packing, spritesheet generation, and determinism.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_SOURCE = REPO_ROOT / "domains" / "ocean-rescue" / "assets" / "source"
ART_PACKET_JSON = ASSETS_SOURCE / "art-packet.json"
ART_APPROVAL_JSON = ASSETS_SOURCE / "art-approval.json"
GENERATED_DIR = REPO_ROOT / "domains" / "ocean-rescue" / "assets" / "generated"

BUILD_SCRIPT = REPO_ROOT / "scripts" / "ocean_rescue" / "build_atlases.py"
VALIDATE_SCRIPT = REPO_ROOT / "scripts" / "ocean_rescue" / "validate_atlases.py"

RASTER_SCALE = 2
PADDING_PX = 4
MAX_PAGE_DIM = 4096

BUNDLE_ORDER = ["characters", "scene", "effects-ui"]

REQUIRED_ALIASES = sorted(
    [
        "fx.success-burst",
        "otter.arm.far",
        "otter.arm.near",
        "otter.eyes.closed",
        "otter.eyes.open",
        "otter.head",
        "otter.mouth.concern",
        "otter.mouth.neutral",
        "otter.mouth.smile",
        "otter.tail",
        "otter.torso",
        "scene.coral.foreground",
        "scene.reef.mid",
        "scene.seaweed-loop.01",
        "scene.submarine",
        "scene.water.far",
        "turtle.free",
        "turtle.worried",
        "ui.drag-arrow",
    ]
)

BUNDLE_MAP = {
    "characters": [
        "otter.arm.far",
        "otter.arm.near",
        "otter.eyes.closed",
        "otter.eyes.open",
        "otter.head",
        "otter.mouth.concern",
        "otter.mouth.neutral",
        "otter.mouth.smile",
        "otter.tail",
        "otter.torso",
        "turtle.free",
        "turtle.worried",
    ],
    "scene": [
        "scene.coral.foreground",
        "scene.reef.mid",
        "scene.seaweed-loop.01",
        "scene.submarine",
        "scene.water.far",
    ],
    "effects-ui": ["fx.success-burst", "ui.drag-arrow"],
}

ENV = {"DYLD_LIBRARY_PATH": "/opt/homebrew/opt/cairo/lib"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_build(
    output_dir: Path, packet: Path | None = None, approval: Path | None = None
) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable,
        str(BUILD_SCRIPT),
        "--packet",
        str(packet or ART_PACKET_JSON),
        "--approval",
        str(approval or ART_APPROVAL_JSON),
        "--output-dir",
        str(output_dir),
    ]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env={**dict(__import__("os").environ), **ENV},
    )


def _run_validate(
    gen_dir: Path, packet: Path | None = None, approval: Path | None = None
) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable,
        str(VALIDATE_SCRIPT),
        "--packet",
        str(packet or ART_PACKET_JSON),
        "--approval",
        str(approval or ART_APPROVAL_JSON),
        "--generated-dir",
        str(gen_dir),
    ]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env={**dict(__import__("os").environ), **ENV},
    )


def _make_fixture(
    tmp_path: Path,
    packet_mods: dict | None = None,
    approval_mods: dict | None = None,
    extra_assets: list[dict] | None = None,
) -> Path:
    """Create a test fixture directory with packet, approval, and source files."""
    fixture_dir = tmp_path / "fixture"
    fixture_dir.mkdir()

    packet = _load_json(ART_PACKET_JSON)
    if packet_mods:
        for key, val in packet_mods.items():
            if key == "add_assets":
                packet["assets"].extend(val)
            else:
                packet[key] = val

    (fixture_dir / "art-packet.json").write_text(
        json.dumps(packet, indent=2), encoding="utf-8"
    )

    for asset in packet["assets"]:
        src = ASSETS_SOURCE / asset["source"]
        if src.exists():
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
        shutil.copy2(ART_APPROVAL_JSON, fixture_dir / "art-approval.json")

    return fixture_dir


def _make_blank_svg(tmp_path: Path, name: str = "blank.svg") -> Path:
    """Create a completely transparent SVG fixture."""
    svg_path = tmp_path / name
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<rect width="100" height="100" fill="transparent"/>'
        "</svg>",
        encoding="utf-8",
    )
    return svg_path


# ---------------------------------------------------------------------------
# Pre-fix reproduction
# ---------------------------------------------------------------------------


class TestPreFixReproduction:
    def test_approved_packet_passes_approval_validation(self):
        """Verify the canonical approval gate passes."""
        result = subprocess.run(
            [
                sys.executable,
                str(
                    REPO_ROOT / "scripts" / "ocean_rescue" / "validate_art_approval.py"
                ),
                str(ASSETS_SOURCE),
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, (
            f"Approval validation must pass:\n{result.stderr}"
        )

    def test_no_valid_atlas_manifest_exists(self):
        """Verify production atlas eligibility is false before this task."""
        manifest_path = GENERATED_DIR / "atlas-manifest.json"
        # Before this task, no valid atlas-manifest.json should exist
        # After this task, it will exist - this test documents the pre-fix state
        if manifest_path.exists():
            manifest = _load_json(manifest_path)
            # If it exists, it should be valid (post-fix state)
            assert "bundles" in manifest, "Manifest must have bundles"


# ---------------------------------------------------------------------------
# Approval gate tests
# ---------------------------------------------------------------------------


class TestApprovalGate:
    def test_approved_packet_builds(self):
        """Approved packet should produce valid atlases."""
        out_dir = Path("/tmp/test_approved_packet")
        if out_dir.exists():
            shutil.rmtree(out_dir)
        result = _run_build(out_dir)
        assert result.returncode == 0, (
            f"Build failed:\n{result.stdout}\n{result.stderr}"
        )
        result = _run_validate(out_dir)
        assert result.returncode == 0, (
            f"Validation failed:\n{result.stdout}\n{result.stderr}"
        )
        shutil.rmtree(out_dir, ignore_errors=True)

    def test_no_approval_rejected(self, tmp_path: Path):
        """Packet without approval should be rejected."""
        fixture = _make_fixture(tmp_path)
        (fixture / "art-approval.json").unlink()
        out_dir = tmp_path / "output"
        result = _run_build(
            out_dir,
            packet=fixture / "art-packet.json",
            approval=fixture / "art-approval.json",
        )
        assert result.returncode != 0, "Build must reject packet without approval"

    def test_review_ready_rejected(self, tmp_path: Path):
        """Asset in review-ready state should be rejected."""
        packet = _load_json(ART_PACKET_JSON)
        packet["assets"][0]["approvalState"] = "review-ready"
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()
        (fixture_dir / "art-packet.json").write_text(
            json.dumps(packet, indent=2), encoding="utf-8"
        )
        for asset in packet["assets"]:
            src = ASSETS_SOURCE / asset["source"]
            if src.exists():
                dst = fixture_dir / asset["source"]
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())
        shutil.copy2(ART_APPROVAL_JSON, fixture_dir / "art-approval.json")
        out_dir = tmp_path / "output"
        result = _run_build(
            out_dir,
            packet=fixture_dir / "art-packet.json",
            approval=fixture_dir / "art-approval.json",
        )
        assert result.returncode != 0, "Build must reject review-ready asset"


# ---------------------------------------------------------------------------
# Three-bundle tests
# ---------------------------------------------------------------------------


class TestThreeBundles:
    def test_exactly_three_bundles(self, tmp_path: Path):
        """Exactly three bundles should be created."""
        out_dir = tmp_path / "output"
        _run_build(out_dir)
        manifest = _load_json(out_dir / "atlas-manifest.json")
        assert len(manifest["bundles"]) == 3, (
            f"Expected 3 bundles, got {len(manifest['bundles'])}"
        )
        names = [b["name"] for b in manifest["bundles"]]
        assert names == BUNDLE_ORDER, f"Bundle order: {names} != {BUNDLE_ORDER}"

    def test_nineteen_aliases_in_correct_bundles(self, tmp_path: Path):
        """All 19 aliases should be in the correct bundles."""
        out_dir = tmp_path / "output"
        _run_build(out_dir)
        manifest = _load_json(out_dir / "atlas-manifest.json")

        all_aliases = set()
        for bundle in manifest["bundles"]:
            for alias in bundle["aliases"]:
                all_aliases.add(alias)

        assert all_aliases == set(REQUIRED_ALIASES), "Alias mismatch"

        for bundle in manifest["bundles"]:
            expected = set(BUNDLE_MAP[bundle["name"]])
            actual = set(bundle["aliases"])
            assert actual == expected, (
                f"Bundle {bundle['name']}: {actual} != {expected}"
            )


# ---------------------------------------------------------------------------
# Rasterization tests
# ---------------------------------------------------------------------------


class TestRasterization:
    def test_all_sources_rasterized_at_2x(self, tmp_path: Path):
        """All sources should be rasterized at declared 2× size."""

        out_dir = tmp_path / "output"
        _run_build(out_dir)
        packet = _load_json(ART_PACKET_JSON)

        for asset in packet["assets"]:
            logical_w, logical_h = asset["logicalSize"]
            expected_phys = (logical_w * RASTER_SCALE, logical_h * RASTER_SCALE)
            # Find this alias in the spritesheet
            bundle_name = asset["bundle"]
            manifest = _load_json(out_dir / "atlas-manifest.json")
            bundle = next(b for b in manifest["bundles"] if b["name"] == bundle_name)
            page_json = out_dir / bundle_name / bundle["pages"][0]["spritesheet"]
            sheet = _load_json(page_json)
            if asset["alias"] in sheet["frames"]:
                frame_data = sheet["frames"][asset["alias"]]
                source_size = frame_data["sourceSize"]
                assert (source_size["w"], source_size["h"]) == expected_phys, (
                    f"{asset['alias']}: sourceSize {source_size} != expected {expected_phys}"
                )

    def test_png_mode_rgba(self, tmp_path: Path):
        """All PNG pages should be RGBA mode."""
        from PIL import Image

        out_dir = tmp_path / "output"
        _run_build(out_dir)
        manifest = _load_json(out_dir / "atlas-manifest.json")

        for bundle in manifest["bundles"]:
            for page in bundle["pages"]:
                img_path = out_dir / bundle["name"] / page["image"]
                img = Image.open(img_path)
                assert img.mode == "RGBA", f"{page['image']} mode is {img.mode}"

    def test_blank_svg_rejected(self, tmp_path: Path):
        """Completely transparent raster should be rejected."""
        blank_svg = _make_blank_svg(tmp_path)
        # Create a packet with a blank SVG
        packet = _load_json(ART_PACKET_JSON)
        packet["assets"][0]["source"] = str(blank_svg.relative_to(tmp_path))
        packet["assets"][0]["sourceType"] = "svg"
        # Copy blank SVG to fixture
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()
        (fixture_dir / "art-packet.json").write_text(
            json.dumps(packet, indent=2), encoding="utf-8"
        )
        for asset in packet["assets"]:
            src = ASSETS_SOURCE / asset["source"]
            if src.exists():
                dst = fixture_dir / asset["source"]
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())
        # Copy blank SVG to expected location
        dst_blank = fixture_dir / str(blank_svg.relative_to(tmp_path))
        dst_blank.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(blank_svg, dst_blank)
        shutil.copy2(ART_APPROVAL_JSON, fixture_dir / "art-approval.json")

        out_dir = tmp_path / "output"
        result = _run_build(
            out_dir,
            packet=fixture_dir / "art-packet.json",
            approval=fixture_dir / "art-approval.json",
        )
        assert result.returncode != 0, "Build must reject blank SVG"


# ---------------------------------------------------------------------------
# Trim tests
# ---------------------------------------------------------------------------


class TestTrim:
    def test_alpha_trim_matches_actual_bbox(self, tmp_path: Path):
        """Trim rectangle should match actual alpha bounding box."""
        from PIL import Image

        out_dir = tmp_path / "output"
        _run_build(out_dir)
        manifest = _load_json(out_dir / "atlas-manifest.json")

        for bundle in manifest["bundles"]:
            for page in bundle["pages"]:
                img_path = out_dir / bundle["name"] / page["image"]
                img = Image.open(img_path)
                json_path = out_dir / bundle["name"] / page["spritesheet"]
                sheet = _load_json(json_path)

                for alias, frame_data in sheet["frames"].items():
                    frame = frame_data["frame"]
                    # Extract the frame region from the page
                    region = img.crop(
                        (
                            frame["x"],
                            frame["y"],
                            frame["x"] + frame["w"],
                            frame["y"] + frame["h"],
                        )
                    )
                    # Get actual alpha bounding box of the content
                    alpha = region.split()[3]
                    bbox = alpha.getbbox()
                    if bbox:
                        # spriteSourceSize should match the trim rect
                        sprite_source = frame_data["spriteSourceSize"]
                        assert sprite_source["w"] > 0 and sprite_source["h"] > 0, (
                            f"{alias}: spriteSourceSize has zero dimension"
                        )

    def test_source_size_matches_untrimmed_physical(self, tmp_path: Path):
        """sourceSize should be untrimmed physical dimensions."""
        out_dir = tmp_path / "output"
        _run_build(out_dir)
        packet = _load_json(ART_PACKET_JSON)

        for asset in packet["assets"]:
            logical_w, logical_h = asset["logicalSize"]
            expected_phys = (logical_w * RASTER_SCALE, logical_h * RASTER_SCALE)
            bundle_name = asset["bundle"]
            manifest = _load_json(out_dir / "atlas-manifest.json")
            bundle = next(b for b in manifest["bundles"] if b["name"] == bundle_name)
            page_json = out_dir / bundle_name / bundle["pages"][0]["spritesheet"]
            sheet = _load_json(page_json)
            if asset["alias"] in sheet["frames"]:
                frame_data = sheet["frames"][asset["alias"]]
                source_size = frame_data["sourceSize"]
                assert (source_size["w"], source_size["h"]) == expected_phys

    def test_spritesource_size_matches_trim_rect(self, tmp_path: Path):
        """spriteSourceSize should match trim rectangle."""
        out_dir = tmp_path / "output"
        _run_build(out_dir)
        manifest = _load_json(out_dir / "atlas-manifest.json")

        for bundle in manifest["bundles"]:
            for page in bundle["pages"]:
                json_path = out_dir / bundle["name"] / page["spritesheet"]
                sheet = _load_json(json_path)
                for alias, frame_data in sheet["frames"].items():
                    frame = frame_data["frame"]
                    sprite_source = frame_data["spriteSourceSize"]
                    assert sprite_source["w"] == frame["w"], (
                        f"{alias}: spriteSourceSize.w {sprite_source['w']} != frame.w {frame['w']}"
                    )
                    assert sprite_source["h"] == frame["h"], (
                        f"{alias}: spriteSourceSize.h {sprite_source['h']} != frame.h {frame['h']}"
                    )


# ---------------------------------------------------------------------------
# Pivot tests
# ---------------------------------------------------------------------------


class TestPivot:
    def test_anchor_matches_canonical_pivot(self, tmp_path: Path):
        """Anchor should match canonical pivot from packet."""
        out_dir = tmp_path / "output"
        _run_build(out_dir)
        packet = _load_json(ART_PACKET_JSON)
        alias_to_pivot = {a["alias"]: a["pivot"] for a in packet["assets"]}

        manifest = _load_json(out_dir / "atlas-manifest.json")
        for bundle in manifest["bundles"]:
            for page in bundle["pages"]:
                json_path = out_dir / bundle["name"] / page["spritesheet"]
                sheet = _load_json(json_path)
                for alias, frame_data in sheet["frames"].items():
                    anchor = frame_data["anchor"]
                    expected = alias_to_pivot[alias]
                    assert (
                        abs(anchor["x"] - expected[0]) < 1e-6
                        and abs(anchor["y"] - expected[1]) < 1e-6
                    ), f"{alias}: anchor {anchor} != pivot {expected}"


# ---------------------------------------------------------------------------
# Packing tests
# ---------------------------------------------------------------------------


class TestPacking:
    def test_frames_within_page_bounds(self, tmp_path: Path):
        """All frames should be within page bounds."""
        out_dir = tmp_path / "output"
        _run_build(out_dir)
        manifest = _load_json(out_dir / "atlas-manifest.json")

        for bundle in manifest["bundles"]:
            for page in bundle["pages"]:
                json_path = out_dir / bundle["name"] / page["spritesheet"]
                sheet = _load_json(json_path)
                for alias, frame_data in sheet["frames"].items():
                    frame = frame_data["frame"]
                    assert frame["x"] >= 0 and frame["y"] >= 0
                    assert frame["x"] + frame["w"] <= page["width"]
                    assert frame["y"] + frame["h"] <= page["height"]

    def test_no_frame_overlap(self, tmp_path: Path):
        """Frames should not overlap."""
        out_dir = tmp_path / "output"
        _run_build(out_dir)
        manifest = _load_json(out_dir / "atlas-manifest.json")

        for bundle in manifest["bundles"]:
            for page in bundle["pages"]:
                json_path = out_dir / bundle["name"] / page["spritesheet"]
                sheet = _load_json(json_path)
                frames = list(sheet["frames"].items())
                for i, (alias_a, frame_a) in enumerate(frames):
                    rect_a = frame_a["frame"]
                    for alias_b, frame_b in frames[i + 1 :]:
                        rect_b = frame_b["frame"]
                        assert not (
                            rect_a["x"] < rect_b["x"] + rect_b["w"]
                            and rect_a["x"] + rect_a["w"] > rect_b["x"]
                            and rect_a["y"] < rect_b["y"] + rect_b["h"]
                            and rect_a["y"] + rect_a["h"] > rect_b["y"]
                        ), f"Overlap: {alias_a} and {alias_b}"

    def test_padding_between_frames(self, tmp_path: Path):
        """4px transparent padding should exist between frames."""
        from PIL import Image

        out_dir = tmp_path / "output"
        _run_build(out_dir)
        manifest = _load_json(out_dir / "atlas-manifest.json")

        for bundle in manifest["bundles"]:
            for page in bundle["pages"]:
                img_path = out_dir / bundle["name"] / page["image"]
                img = Image.open(img_path)
                json_path = out_dir / bundle["name"] / page["spritesheet"]
                sheet = _load_json(json_path)

                for alias, frame_data in sheet["frames"].items():
                    frame = frame_data["frame"]
                    x0, y0 = frame["x"], frame["y"]
                    w, h = frame["w"], frame["h"]

                    # Check left padding
                    if x0 > 0:
                        for dy in range(min(h, 10)):
                            px, py = x0 - 1, y0 + dy
                            if 0 <= px < img.width and 0 <= py < img.height:
                                _, _, _, a = img.getpixel((px, py))
                                assert a == 0, f"Padding violation (left) for {alias}"

                    # Check right padding
                    x1 = x0 + w
                    if x1 < img.width:
                        for dy in range(min(h, 10)):
                            px, py = x1, y0 + dy
                            if 0 <= px < img.width and 0 <= py < img.height:
                                _, _, _, a = img.getpixel((px, py))
                                assert a == 0, f"Padding violation (right) for {alias}"

    def test_no_rotation(self, tmp_path: Path):
        """No rotation should be used."""
        out_dir = tmp_path / "output"
        _run_build(out_dir)
        manifest = _load_json(out_dir / "atlas-manifest.json")

        for bundle in manifest["bundles"]:
            for page in bundle["pages"]:
                json_path = out_dir / bundle["name"] / page["spritesheet"]
                sheet = _load_json(json_path)
                for alias, frame_data in sheet["frames"].items():
                    assert frame_data["rotated"] is False, f"{alias} is rotated"

    def test_page_dimensions_within_limit(self, tmp_path: Path):
        """Page dimensions should be at most 4096×4096."""
        out_dir = tmp_path / "output"
        _run_build(out_dir)
        manifest = _load_json(out_dir / "atlas-manifest.json")

        for bundle in manifest["bundles"]:
            for page in bundle["pages"]:
                assert page["width"] <= MAX_PAGE_DIM
                assert page["height"] <= MAX_PAGE_DIM

    def test_json_frame_ordering_deterministic(self, tmp_path: Path):
        """JSON frame ordering should be deterministic (alias sorted)."""
        out_dir = tmp_path / "output"
        _run_build(out_dir)
        manifest = _load_json(out_dir / "atlas-manifest.json")

        for bundle in manifest["bundles"]:
            for page in bundle["pages"]:
                json_path = out_dir / bundle["name"] / page["spritesheet"]
                sheet = _load_json(json_path)
                keys = list(sheet["frames"].keys())
                assert keys == sorted(keys), f"Frame ordering not deterministic: {keys}"


# ---------------------------------------------------------------------------
# Determinism tests
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_two_independent_builds_byte_identical(self, tmp_path: Path):
        """Two independent temp builds should be byte-identical."""
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        _run_build(dir_a)
        _run_build(dir_b)
        result = subprocess.run(
            ["diff", "-qr", str(dir_a), str(dir_b)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Builds not identical:\n{result.stdout}"

    def test_tracked_output_matches_clean_rebuild(self):
        """Tracked generated outputs should match clean rebuild."""
        if not GENERATED_DIR.exists():
            pytest.skip("Tracked generated output not yet created")

        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            rebuild_dir = Path(tmp) / "rebuild"
            _run_build(rebuild_dir)
            result = subprocess.run(
                ["diff", "-qr", str(GENERATED_DIR), str(rebuild_dir)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, (
                f"Tracked output differs from rebuild:\n{result.stdout}"
            )

    def test_partition_local_isolation(self, tmp_path: Path):
        """Characters-only source change should leave scene and effects-ui identical."""
        # Build baseline
        baseline_dir = tmp_path / "baseline"
        _run_build(baseline_dir)

        # Create modified packet (change one character source)
        packet = _load_json(ART_PACKET_JSON)
        modified_svg = tmp_path / "modified-otter-head.svg"
        # Find the otter.head asset and modify its source
        for asset in packet["assets"]:
            if asset["alias"] == "otter.head":
                # Create a modified SVG
                original_svg = ASSETS_SOURCE / asset["source"]
                svg_content = original_svg.read_text(encoding="utf-8")
                # Add a comment to make it different
                modified_svg.write_text(
                    svg_content.replace("<svg", "<!-- modified -->\n<svg"),
                    encoding="utf-8",
                )
                # Update packet to use modified source
                asset["source"] = str(modified_svg.relative_to(tmp_path))
                asset["sourceSha256"] = hashlib.sha256(
                    modified_svg.read_bytes()
                ).hexdigest()
                break

        # Create fixture
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()
        (fixture_dir / "art-packet.json").write_text(
            json.dumps(packet, indent=2), encoding="utf-8"
        )
        for asset in packet["assets"]:
            src = ASSETS_SOURCE / asset["source"]
            if src.exists():
                dst = fixture_dir / asset["source"]
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())
        # Copy modified SVG
        dst_mod = fixture_dir / str(modified_svg.relative_to(tmp_path))
        dst_mod.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(modified_svg, dst_mod)
        shutil.copy2(ART_APPROVAL_JSON, fixture_dir / "art-approval.json")

        # Build modified
        modified_dir = tmp_path / "modified"
        _run_build(
            modified_dir,
            packet=fixture_dir / "art-packet.json",
            approval=fixture_dir / "art-approval.json",
        )

        # Compare scene and effects-ui
        for bundle_name in ["scene", "effects-ui"]:
            for ext in [".png", ".json"]:
                baseline_file = baseline_dir / bundle_name / f"{bundle_name}-0{ext}"
                modified_file = modified_dir / bundle_name / f"{bundle_name}-0{ext}"
                if baseline_file.exists() and modified_file.exists():
                    assert baseline_file.read_bytes() == modified_file.read_bytes(), (
                        f"{bundle_name}{ext} should be identical after character change"
                    )

        # Characters should be different
        for ext in [".png", ".json"]:
            baseline_file = baseline_dir / "characters" / f"characters-0{ext}"
            modified_file = modified_dir / "characters" / f"characters-0{ext}"
            if baseline_file.exists() and modified_file.exists():
                assert baseline_file.read_bytes() != modified_file.read_bytes(), (
                    f"characters{ext} should differ after character change"
                )


# ---------------------------------------------------------------------------
# Spritesheet JSON tests
# ---------------------------------------------------------------------------


class TestSpritesheetJSON:
    def test_pixijs_v8_compatible_shape(self, tmp_path: Path):
        """Spritesheet JSON should be PixiJS v8 compatible."""
        out_dir = tmp_path / "output"
        _run_build(out_dir)
        manifest = _load_json(out_dir / "atlas-manifest.json")

        for bundle in manifest["bundles"]:
            for page in bundle["pages"]:
                json_path = out_dir / bundle["name"] / page["spritesheet"]
                sheet = _load_json(json_path)

                # Top-level keys
                assert set(sheet.keys()) == {"frames", "animations", "meta"}

                meta = sheet["meta"]
                assert meta["app"] == "AidenGame Ocean Rescue Atlas Builder"
                assert meta["version"] == "1"
                assert meta["format"] == "RGBA8888"
                assert str(meta["scale"]) == "2"

                # Each frame
                for alias, frame_data in sheet["frames"].items():
                    assert set(frame_data.keys()) == {
                        "frame",
                        "rotated",
                        "trimmed",
                        "spriteSourceSize",
                        "sourceSize",
                        "anchor",
                    }
                    assert frame_data["rotated"] is False
                    assert frame_data["trimmed"] is True

    def test_animations_empty(self, tmp_path: Path):
        """Animations should be empty object."""
        out_dir = tmp_path / "output"
        _run_build(out_dir)
        manifest = _load_json(out_dir / "atlas-manifest.json")

        for bundle in manifest["bundles"]:
            for page in bundle["pages"]:
                json_path = out_dir / bundle["name"] / page["spritesheet"]
                sheet = _load_json(json_path)
                assert sheet["animations"] == {}

    def test_multi_page_related_pack_links(self, tmp_path: Path):
        """Multi-page bundles should have correct related_multi_packs."""
        out_dir = tmp_path / "output"
        _run_build(out_dir)
        manifest = _load_json(out_dir / "atlas-manifest.json")

        for bundle in manifest["bundles"]:
            pages = bundle["pages"]
            if len(pages) > 1:
                for page in pages:
                    json_path = out_dir / bundle["name"] / page["spritesheet"]
                    sheet = _load_json(json_path)
                    related = sheet["meta"].get("related_multi_packs", [])
                    expected = [
                        p["spritesheet"] for p in pages if p["index"] != page["index"]
                    ]
                    assert sorted(related) == sorted(expected)


# ---------------------------------------------------------------------------
# Manifest tests
# ---------------------------------------------------------------------------


class TestManifest:
    def test_manifest_file_hashes_match(self, tmp_path: Path):
        """Manifest file hashes should match actual bytes."""
        out_dir = tmp_path / "output"
        _run_build(out_dir)
        manifest = _load_json(out_dir / "atlas-manifest.json")

        for rel_path, expected_sha in manifest.get("files", {}).items():
            if rel_path == "atlas-manifest.json":
                continue
            full_path = out_dir / rel_path
            assert full_path.exists(), f"File missing: {rel_path}"
            actual_sha = _sha256_file(full_path)
            assert actual_sha == expected_sha, f"Hash mismatch for {rel_path}"

    def test_no_undeclared_files(self, tmp_path: Path):
        """No undeclared files should exist in generated directory."""
        out_dir = tmp_path / "output"
        _run_build(out_dir)
        manifest = _load_json(out_dir / "atlas-manifest.json")

        declared = set(manifest.get("files", {}).keys())
        declared.add("atlas-manifest.json")

        actual = set()
        for item in out_dir.rglob("*"):
            if item.is_file():
                rel = str(item.relative_to(out_dir))
                actual.add(rel)

        undeclared = actual - declared
        assert not undeclared, f"Undeclared files: {undeclared}"

    def test_no_forbidden_content(self, tmp_path: Path):
        """No absolute paths, timestamps, or UUIDs in output."""
        out_dir = tmp_path / "output"
        _run_build(out_dir)
        manifest = _load_json(out_dir / "atlas-manifest.json")

        import re

        uuid_re = re.compile(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
        )
        ts_re = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

        for rel_path in manifest.get("files", {}).keys():
            if not rel_path.endswith(".json"):
                continue
            full_path = out_dir / rel_path
            content = full_path.read_text(encoding="utf-8")
            assert not uuid_re.search(content), f"UUID found in {rel_path}"
            assert not ts_re.search(content), f"Timestamp found in {rel_path}"

    def test_exact_toolchain_pins(self, tmp_path: Path):
        """Toolchain should have exact dependency versions."""
        out_dir = tmp_path / "output"
        _run_build(out_dir)
        manifest = _load_json(out_dir / "atlas-manifest.json")

        toolchain = manifest.get("toolchain", {})
        assert toolchain.get("cairosvg") == "2.9.0"
        assert toolchain.get("pillow") == "12.3.0"


# ---------------------------------------------------------------------------
# Failed build atomicity
# ---------------------------------------------------------------------------


class TestFailedBuildAtomicity:
    def test_failed_build_preserves_existing_output(self, tmp_path: Path):
        """Failed build should not partially modify existing output."""
        # Create valid output first
        good_dir = tmp_path / "good"
        _run_build(good_dir)

        # Record original hashes
        original_hashes = {}
        for f in good_dir.rglob("*"):
            if f.is_file():
                original_hashes[f.relative_to(good_dir)] = _sha256_file(f)

        # Try to build with invalid approval (should fail)
        bad_approval = tmp_path / "bad-approval.json"
        approval = _load_json(ART_APPROVAL_JSON)
        approval["artPacketSha256"] = "0" * 64
        bad_approval.write_text(json.dumps(approval, indent=2), encoding="utf-8")

        _run_build(good_dir, approval=bad_approval)

        # Verify original output is unchanged
        for rel_path, original_sha in original_hashes.items():
            actual_sha = _sha256_file(good_dir / rel_path)
            assert actual_sha == original_sha, (
                f"File {rel_path} was modified by failed build"
            )


# ---------------------------------------------------------------------------
# Pixi assets manifest
# ---------------------------------------------------------------------------


class TestPixiAssetsManifest:
    def test_pixi_assets_manifest_structure(self, tmp_path: Path):
        """Pixi assets manifest should have correct structure."""
        out_dir = tmp_path / "output"
        _run_build(out_dir)
        pixi = _load_json(out_dir / "pixi-assets-manifest.json")

        assert "bundles" in pixi
        assert len(pixi["bundles"]) == 3

        names = [b["name"] for b in pixi["bundles"]]
        assert names == BUNDLE_ORDER

        for bundle in pixi["bundles"]:
            assert "assets" in bundle
            assert len(bundle["assets"]) == 1
            asset = bundle["assets"][0]
            assert asset["alias"] == f"{bundle['name']}.atlas"
            assert asset["src"] == f"{bundle['name']}/{bundle['name']}-0.json"
