"""Regression tests for Ocean Rescue SVG ID uniqueness."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ocean_rescue import validate_art_packet as validator


def _write_svg(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "fixture.svg"
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">{body}</svg>',
        encoding="utf-8",
    )
    return path


def test_duplicate_svg_ids_are_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write_svg(
        tmp_path,
        '<g id="shared-id"><circle cx="20" cy="20" r="10"/></g>'
        '<rect id="shared-id" x="40" y="40" width="20" height="20"/>',
    )

    with pytest.raises(SystemExit) as exc_info:
        validator.validate_svg(path)

    assert exc_info.value.code == 1
    assert "Duplicate SVG id 'shared-id'" in capsys.readouterr().err


@pytest.mark.parametrize(
    "body",
    [
        '<g id="group-id"><circle id="circle-id" cx="20" cy="20" r="10"/></g>',
        '<circle cx="20" cy="20" r="10"/>',
    ],
)
def test_svg_without_duplicate_ids_is_allowed(tmp_path: Path, body: str) -> None:
    validator.validate_svg(_write_svg(tmp_path, body))
