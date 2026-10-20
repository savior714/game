"""태양계 3D 탐험대 — 키보드 포커스 가시성 계약."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPACE_EXPLORER_CSS = ROOT / "experiments" / "space-explorer" / "space-explorer.css"


def _focus_rule_block(css: str) -> str:
    match = re.search(
        r"#space-app button:focus-visible,\s*#space-app a:focus-visible,\s*#space-canvas:focus-visible\s*\{[^}]*\}",
        css,
        flags=re.DOTALL,
    )
    assert match is not None, "shared focus-visible rule block not found"
    return match.group(0)


def test_space_explorer_controls_have_visible_keyboard_focus() -> None:
    css = SPACE_EXPLORER_CSS.read_text(encoding="utf-8")
    block = _focus_rule_block(css)

    outline = re.search(r"outline:\s*(?P<value>[^;}]+)", block)
    assert outline is not None, "focus-visible rule must declare outline"
    assert outline.group("value").strip().lower() != "none"
    assert "3px solid" in outline.group("value")

    offset = re.search(r"outline-offset:\s*(?P<value>[^;}]+)", block)
    assert offset is not None, "focus-visible rule must declare outline-offset"
    offset_match = re.match(r"^(-?\d+(?:\.\d+)?)", offset.group("value").strip())
    assert offset_match is not None
    assert float(offset_match.group(1)) > 0

    assert re.search(r"box-shadow:\s*[^;}]+\S", block), (
        "focus-visible rule must include a visible ring (box-shadow)"
    )


def test_canvas_is_keyboard_focusable() -> None:
    html = (ROOT / "experiments" / "space-explorer" / "index.html").read_text(
        encoding="utf-8"
    )

    assert 'id="space-canvas" tabindex="0"' in html
    assert 'aria-label="3D 태양계 시뮬레이션' in html
