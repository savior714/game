"""Focused regression tests for SVG root viewBox finite numeric contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ocean_rescue import validate_art_packet as validator


def _write_svg(tmp_path: Path, viewBox_attr: str | None) -> Path:
    path = tmp_path / "test_fixture.svg"
    viewbox_str = f' viewBox="{viewBox_attr}"' if viewBox_attr is not None else ""
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg"{viewbox_str}>'
        '<rect width="100" height="100"/>'
        "</svg>",
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize(
    ("viewbox_val", "expected_err"),
    [
        (None, "Missing viewBox"),
        ("0 0 100", "Invalid viewBox"),
        ("0 0 100 100 100", "Invalid viewBox"),
        ("0 0 NaN 100", "Invalid viewBox"),
        ("0 0 inf 100", "Invalid viewBox"),
        ("0 0 -inf 100", "Invalid viewBox"),
        ("0 0 100 0", "Invalid viewBox"),
        ("0 0 0 100", "Invalid viewBox"),
        ("0 0 -100 100", "Invalid viewBox"),
        ("0 0 100 -100", "Invalid viewBox"),
        ("0 0 foo 100", "Invalid viewBox"),
    ],
)
def test_invalid_svg_viewbox_rejected(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    viewbox_val: str | None,
    expected_err: str,
) -> None:
    svg_path = _write_svg(tmp_path, viewbox_val)
    with pytest.raises(SystemExit) as exc_info:
        validator.validate_svg(svg_path)

    assert exc_info.value.code == 1
    assert expected_err in capsys.readouterr().err


@pytest.mark.parametrize(
    "viewbox_val",
    [
        "0 0 100 100",
        "-10 -20 100 200",
        "-10, -20, 100, 200",
        "0,0,320,200",
        "-1.5e1 -2.5e1 1.0e2 2.0e2",
        "  0   0   100   100  ",
    ],
)
def test_valid_svg_viewbox_accepted(tmp_path: Path, viewbox_val: str) -> None:
    svg_path = _write_svg(tmp_path, viewbox_val)
    validator.validate_svg(svg_path)
