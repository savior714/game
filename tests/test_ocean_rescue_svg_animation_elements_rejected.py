"""Regression tests for forbidden SVG animation elements."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ocean_rescue import validate_art_packet as validator


@pytest.mark.parametrize(
    ("element_name", "animation_markup"),
    [
        (
            "animateTransform",
            '<animateTransform attributeName="transform" type="rotate" '
            'from="0 50 50" to="360 50 50" dur="1s"/>',
        ),
        (
            "animateMotion",
            '<animateMotion path="M0,0 L10,10" dur="1s"/>',
        ),
    ],
)
def test_forbidden_svg_animation_element_rejected(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    element_name: str,
    animation_markup: str,
) -> None:
    svg_path = tmp_path / "animated.svg"
    svg_path.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<rect width="100" height="100"/>'
            f"{animation_markup}"
            "</svg>"
        ),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as exc_info:
        validator.validate_svg(svg_path)

    assert exc_info.value.code == 1
    assert f"Forbidden element <{element_name}>" in capsys.readouterr().err
