import re
from pathlib import Path

SPACE_EXPLORER_CSS = (
    Path(__file__).resolve().parents[1]
    / "experiments"
    / "space-explorer"
    / "space-explorer.css"
)

REQUIRED_SELECTORS = (
    ".se-page .nav-list a:focus-visible",
    ".se-page .control-group button:focus-visible",
    ".se-page .control-group select:focus-visible",
    '.se-page .speed-control input[type="range"]:focus-visible',
    '.se-page .control-group input[type="checkbox"]:focus-visible',
)


def _focus_rule_block(css: str) -> str:
    match = re.search(
        re.escape(REQUIRED_SELECTORS[0]) + r"[^{]*\{[^}]*\}",
        css,
        flags=re.DOTALL,
    )
    assert match is not None, "focus-visible rule block not found"
    return match.group(0)


def test_space_explorer_controls_have_visible_keyboard_focus():
    css = SPACE_EXPLORER_CSS.read_text(encoding="utf-8")

    for selector in REQUIRED_SELECTORS:
        assert selector in css, f"Missing focus-visible selector: {selector}"

    block = _focus_rule_block(css)

    for selector in REQUIRED_SELECTORS:
        assert selector in block, (
            f"Selector not in shared focus-visible rule: {selector}"
        )

    assert ".se-page" in block, "focus-visible rule must be scoped to .se-page"

    outline = re.search(r"outline:\s*(?P<value>[^;}]+)", block)
    assert outline is not None, "focus-visible rule must declare outline"
    assert outline.group("value").strip().lower() != "none", (
        "focus-visible outline must not be none"
    )

    offset = re.search(r"outline-offset:\s*(?P<value>[^;}]+)", block)
    assert offset is not None, "focus-visible rule must declare outline-offset"
    offset_text = offset.group("value").strip()
    offset_match = re.match(r"^(-?\d+(?:\.\d+)?)", offset_text)
    assert offset_match is not None, "outline-offset must be a length value"
    assert float(offset_match.group(1)) > 0, "outline-offset must be positive"

    assert re.search(r"box-shadow:\s*[^;}]+", block), (
        "focus-visible rule must include a visible ring (box-shadow)"
    )

    range_outline_none = css.find("outline: none;")
    focus_block_pos = css.find(REQUIRED_SELECTORS[0])
    assert range_outline_none != -1, "range input outline:none declaration not found"
    assert focus_block_pos != -1, "focus-visible rule not found"
    assert focus_block_pos > range_outline_none, (
        "focus-visible rule must come after the range input's outline:none declaration"
    )
