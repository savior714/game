"""Exact RGBA copy contract for Ocean Rescue atlas frame placement.

This failure domain is isolated to frame placement: an atlas page is a
transparent RGBA canvas and packed frames are non-overlapping, so a trimmed
RGBA frame must be copied onto the page verbatim (no alpha masking). Using the
same image as both source and mask in ``Image.paste`` blends semi-transparent
pixels against the transparent destination, attenuating RGB and squaring
alpha. These tests fix that contract.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from PIL import Image

CAIRO_LIB_DIR = "/opt/homebrew/opt/cairo/lib"
os.environ["DYLD_LIBRARY_PATH"] = (
    f"{CAIRO_LIB_DIR}:{os.environ.get('DYLD_LIBRARY_PATH', '')}"
)

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_SOURCE = REPO_ROOT / "domains" / "ocean-rescue" / "assets" / "source"
ART_PACKET_JSON = ASSETS_SOURCE / "art-packet.json"
ART_APPROVAL_JSON = ASSETS_SOURCE / "art-approval.json"
GENERATED_DIR = REPO_ROOT / "domains" / "ocean-rescue" / "assets" / "generated"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "ocean_rescue" / "build_atlases.py"

OTTER_HEAD_SVG = ASSETS_SOURCE / "characters" / "otter-head.svg"
OTTER_HEAD_SOURCE_SHA = (
    "87e6b35d67e0d856d389570614bb47abef9f6271402e881660f98f400e40c5ec"
)
OTTER_HEAD_CANONICAL_2X_SHA = (
    "dee47164ab12d192d93fd66efdbb0909febac683a0be09aafe56c3ae92221d14"
)

OTTER_HEAD_ALIAS = "otter.head"
OTTER_HEAD_FRAME = {"x": 4, "y": 4, "w": 340, "h": 338}
OTTER_HEAD_SPRITE_SOURCE = {"x": 30, "y": 42, "w": 340, "h": 338}
OTTER_HEAD_SOURCE_SIZE = {"w": 400, "h": 400}

SPRITESHEET_JSONS = [
    GENERATED_DIR / "characters" / "characters-0.json",
    GENERATED_DIR / "scene" / "scene-0.json",
    GENERATED_DIR / "effects-ui" / "effects-ui-0.json",
]

ENV = {"DYLD_LIBRARY_PATH": CAIRO_LIB_DIR}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_build(output_dir: Path) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable,
        str(BUILD_SCRIPT),
        "--packet",
        str(ART_PACKET_JSON),
        "--approval",
        str(ART_APPROVAL_JSON),
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


def _rasterize_otter_head_2x() -> Image.Image:
    """Independently rasterize the canonical otter SVG at 400×400."""
    png_data = __import__("cairosvg").svg2png(
        url=str(OTTER_HEAD_SVG),
        output_width=400,
        output_height=400,
    )
    img = Image.open(io.BytesIO(png_data))
    return img.convert("RGBA")


def _reconstruct_frame(
    atlas_path: Path, sheet_path: Path, alias: str
) -> tuple[Image.Image, dict]:
    """Crop a frame from an atlas page and un-trim it into sourceSize."""
    sheet = _load_json(sheet_path)
    frame_data = sheet["frames"][alias]
    atlas = Image.open(atlas_path).convert("RGBA")
    frame = frame_data["frame"]
    sprite = frame_data["spriteSourceSize"]
    source = frame_data["sourceSize"]
    sub = atlas.crop(
        (frame["x"], frame["y"], frame["x"] + frame["w"], frame["y"] + frame["h"])
    )
    recon = Image.new("RGBA", (source["w"], source["h"]), (0, 0, 0, 0))
    recon.paste(sub, (sprite["x"], sprite["y"]))
    return recon, frame_data


def _synthetic_rgba_fixture() -> Image.Image:
    """Small RGBA image covering alpha 0, 1, 64, 127, 128, 200, 254, 255."""
    alphas = [0, 1, 64, 127, 128, 200, 254, 255]
    pixels = []
    for i, a in enumerate(alphas):
        if a == 0:
            rgb = (17, 34, 51)  # hidden RGB behind full transparency
        else:
            rgb = (i * 37 % 256, i * 53 % 256, i * 71 % 256)
        pixels.append(rgb + (a,))
    img = Image.new("RGBA", (len(pixels), 1))
    img.putdata(pixels)
    return img


# ---------------------------------------------------------------------------
# Pillow contract: the defect
# ---------------------------------------------------------------------------


class TestMaskedPasteContract:
    def test_masked_paste_reproduction_mutates_semitransparent_rgba(self):
        """Masked paste with source-as-mask blends semi-transparent pixels."""
        dst = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        src = Image.new("RGBA", (1, 1), (200, 120, 40, 128))
        dst.paste(src, (0, 0), src)
        out = dst.getpixel((0, 0))
        assert isinstance(out, tuple), "expected RGBA tuple from getpixel"

        assert out != (200, 120, 40, 128), (
            "masked paste must not equal the source pixel"
        )
        assert out[0] != 200 or out[1] != 120 or out[2] != 40, (
            f"RGB was not attenuated: {out}"
        )
        assert out[3] != 128, f"alpha was not attenuated: {out}"

    def test_masked_paste_changes_both_rgb_and_alpha(self):
        """Multi-alpha image differs from source in RGB and alpha channels."""
        src = _synthetic_rgba_fixture()
        w, h = src.size
        page = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        page.paste(src, (0, 0), src)
        crop = page.crop((0, 0, w, h))

        src_bytes = src.tobytes()
        crop_bytes = crop.tobytes()
        assert crop_bytes != src_bytes

        rgb_diff = 0
        alpha_diff = 0
        for i in range(0, len(src_bytes), 4):
            if src_bytes[i : i + 3] != crop_bytes[i : i + 3]:
                rgb_diff += 1
            if src_bytes[i + 3] != crop_bytes[i + 3]:
                alpha_diff += 1
        assert rgb_diff > 0, "masked paste must change RGB channels"
        assert alpha_diff > 0, "masked paste must change alpha channel"


# ---------------------------------------------------------------------------
# Pillow contract: the required replacement
# ---------------------------------------------------------------------------


class TestDirectPasteContract:
    def test_direct_rgba_paste_preserves_source_bytes(self):
        """Unmasked paste of RGBA onto transparent RGBA is byte-exact."""
        src = _synthetic_rgba_fixture()
        w, h = src.size
        page = Image.new("RGBA", (w + 4, h + 4), (0, 0, 0, 0))
        page.paste(src, (2, 2))
        crop = page.crop((2, 2, 2 + w, 2 + h))

        assert crop.tobytes() == src.tobytes()

    def test_direct_paste_preserves_hidden_rgb_at_alpha_zero(self):
        """RGB behind fully transparent pixels is copied verbatim."""
        src = _synthetic_rgba_fixture()
        w, h = src.size
        page = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        page.paste(src, (0, 0))
        crop = page.crop((0, 0, w, h))

        assert crop.tobytes() == src.tobytes()
        assert crop.getpixel((0, 0)) == (17, 34, 51, 0), (
            "hidden RGB at alpha 0 must survive"
        )


# ---------------------------------------------------------------------------
# Built atlas otter.head exact reconstruction
# ---------------------------------------------------------------------------


class TestOtterHeadExactReconstruction:
    @pytest.fixture(scope="class")
    def built_output(self, tmp_path_factory) -> Path:
        out_dir = tmp_path_factory.mktemp("otter_rebuild") / "output"
        result = _run_build(out_dir)
        assert result.returncode == 0, (
            f"Build failed:\n{result.stdout}\n{result.stderr}"
        )
        return out_dir

    def test_canonical_source_sha_is_approved(self):
        assert _sha256(OTTER_HEAD_SVG.read_bytes()) == OTTER_HEAD_SOURCE_SHA

    def test_canonical_2x_raster_matches_approved_sha(self):
        canon = _rasterize_otter_head_2x()
        assert canon.size == (400, 400)
        assert _sha256(canon.tobytes()) == OTTER_HEAD_CANONICAL_2X_SHA

    def test_built_otter_head_frame_reconstructs_exact_canonical_rgba(
        self, built_output
    ):
        canon = _rasterize_otter_head_2x()
        atlas_path = built_output / "characters" / "characters-0.png"
        sheet_path = built_output / "characters" / "characters-0.json"
        recon, frame_data = _reconstruct_frame(atlas_path, sheet_path, OTTER_HEAD_ALIAS)

        assert recon.size == (400, 400)
        assert _sha256(recon.tobytes()) == OTTER_HEAD_CANONICAL_2X_SHA
        assert recon.tobytes() == canon.tobytes()

        canon_bytes = canon.tobytes()
        recon_bytes = recon.tobytes()
        mismatched = sum(
            1
            for i in range(0, len(canon_bytes), 4)
            if canon_bytes[i : i + 4] != recon_bytes[i : i + 4]
        )
        assert mismatched == 0, f"{mismatched} pixels differ from canonical"


# ---------------------------------------------------------------------------
# Frame geometry preservation
# ---------------------------------------------------------------------------


class TestAtlasFrameMetadataPreserved:
    @pytest.fixture(scope="class")
    def built_output(self, tmp_path_factory) -> Path:
        out_dir = tmp_path_factory.mktemp("otter_rebuild") / "output"
        result = _run_build(out_dir)
        assert result.returncode == 0, (
            f"Build failed:\n{result.stdout}\n{result.stderr}"
        )
        return out_dir

    def test_atlas_frame_metadata_unchanged_by_copy_fix(self, built_output):
        """Rebuilt frame geometry equals checked-in spritesheet metadata."""
        for baseline_sheet in SPRITESHEET_JSONS:
            rel = baseline_sheet.relative_to(GENERATED_DIR)
            rebuilt_sheet = built_output / rel
            base = _load_json(baseline_sheet)
            rebuilt = _load_json(rebuilt_sheet)

            assert set(rebuilt["frames"].keys()) == set(base["frames"].keys()), (
                f"alias set changed in {rel}"
            )

            for alias in base["frames"]:
                bf = base["frames"][alias]
                rf = rebuilt["frames"][alias]
                for key in [
                    "frame",
                    "rotated",
                    "trimmed",
                    "spriteSourceSize",
                    "sourceSize",
                    "anchor",
                ]:
                    assert rf[key] == bf[key], (
                        f"{rel} {alias}.{key}: rebuilt {rf[key]} != baseline {bf[key]}"
                    )

    def test_otter_head_frame_geometry_is_canonical(self, built_output):
        sheet = _load_json(built_output / "characters" / "characters-0.json")
        frame_data = sheet["frames"][OTTER_HEAD_ALIAS]
        assert frame_data["frame"] == OTTER_HEAD_FRAME
        assert frame_data["rotated"] is False
        assert frame_data["trimmed"] is True
        assert frame_data["spriteSourceSize"] == OTTER_HEAD_SPRITE_SOURCE
        assert frame_data["sourceSize"] == OTTER_HEAD_SOURCE_SIZE
