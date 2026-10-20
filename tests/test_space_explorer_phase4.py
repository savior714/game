"""태양계 3D 탐험대 — 실제 텍스처 자산 계약.

행성 표면은 절차적 캔버스가 아니라 실제 촬영/공개 텍스처를 쓴다.
자산 경로가 틀리거나 파일이 사라지면 화면에 대체 텍스처만 뜨므로 여기서 막는다.
"""

from __future__ import annotations

import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPACE_DIR = ROOT / "experiments" / "space-explorer"
TEXTURES = SPACE_DIR / "assets" / "textures"
DATA = SPACE_DIR / "data.js"

REQUIRED_TEXTURES = (
    "sun.jpg",
    "mercury.jpg",
    "mercury_bump.jpg",
    "venus.jpg",
    "venus_bump.jpg",
    "earth_day.jpg",
    "earth_night.jpg",
    "earth_clouds.png",
    "earth_normal.jpg",
    "earth_specular.jpg",
    "mars.jpg",
    "mars_bump.jpg",
    "jupiter.jpg",
    "saturn.jpg",
    "saturn_ring_alpha.png",
    "uranus.jpg",
    "neptune.jpg",
    "moon.jpg",
    "moon_bump.jpg",
    "galaxy_starfield.jpg",
)


def jpeg_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        if handle.read(2) != b"\xff\xd8":
            raise AssertionError(f"{path.name} is not a JPEG")
    with path.open("rb") as handle:
        data = handle.read()
    index = 2
    while index < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in (0xD8, 0xD9):
            continue
        length = struct.unpack(">H", data[index : index + 2])[0]
        if marker in (0xC0, 0xC1, 0xC2):
            height, width = struct.unpack(">HH", data[index + 3 : index + 7])
            return width, height
        index += length
    raise AssertionError(f"{path.name}: SOF marker not found")


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    assert header[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name} is not a PNG"
    return struct.unpack(">II", header[16:24])


def test_every_required_texture_is_committed() -> None:
    for name in REQUIRED_TEXTURES:
        path = TEXTURES / name
        assert path.is_file(), f"missing texture asset: {name}"
        assert path.stat().st_size > 2_000, f"suspiciously small texture: {name}"


def test_texture_resolution_is_detail_grade() -> None:
    planets = (
        "sun.jpg",
        "mercury.jpg",
        "venus.jpg",
        "mars.jpg",
        "jupiter.jpg",
        "saturn.jpg",
        "uranus.jpg",
        "neptune.jpg",
        "moon.jpg",
    )
    for name in planets:
        width, height = jpeg_size(TEXTURES / name)
        assert width >= 2048, f"{name} width {width} is below detail grade"
        assert width == height * 2, f"{name} must be an equirectangular 2:1 map"

    earth_width, earth_height = jpeg_size(TEXTURES / "earth_day.jpg")
    assert earth_width >= 3072 and earth_width == earth_height * 2


def test_earth_has_day_night_cloud_normal_and_specular_layers() -> None:
    assert jpeg_size(TEXTURES / "earth_day.jpg")[0] == 3072
    assert jpeg_size(TEXTURES / "earth_night.jpg")[0] == 2048
    assert jpeg_size(TEXTURES / "earth_normal.jpg")[0] == 2048
    assert jpeg_size(TEXTURES / "earth_specular.jpg")[0] == 2048

    clouds_width, clouds_height = png_size(TEXTURES / "earth_clouds.png")
    assert clouds_width >= 1024 and clouds_width == clouds_height * 2

    ring_width, ring_height = png_size(TEXTURES / "saturn_ring_alpha.png")
    assert ring_width > ring_height, "ring strip must be a wide 1D gradient"


def test_data_declares_texture_paths_that_exist() -> None:
    data = DATA.read_text(encoding="utf-8")

    for name in REQUIRED_TEXTURES:
        if name in (
            "mercury_bump.jpg",
            "venus_bump.jpg",
            "earth_clouds.png",
            "earth_normal.jpg",
            "earth_specular.jpg",
        ):
            continue
        assert name in data, f"data.js does not reference {name}"

    assert 'export const TEXTURE_BASE = "./assets/textures/";' in data


def test_total_texture_payload_stays_reasonable() -> None:
    total = sum(path.stat().st_size for path in TEXTURES.iterdir() if path.is_file())
    assert total < 9_000_000, f"texture payload is {total / 1_000_000:.1f}MB"
