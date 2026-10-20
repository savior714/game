"""Contract and runtime verification for parent bulk reward consumption in top HUD modals."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REWARD_JS = ROOT / "domains" / "reward" / "reward.js"
REWARD_UI_JS = ROOT / "domains" / "reward" / "reward_ui.js"
REWARD_CSS = ROOT / "domains" / "reward" / "reward.css"
BULK_MJS = ROOT / "tests" / "test_reward_bulk_consume.mjs"


def test_reward_bulk_consume_node_suite() -> None:
    """Execute the Node VM unit test suite for RewardSystem.consumeInternal bulk deduction."""
    node = shutil.which("node")
    assert node is not None, "node is required"
    proc = subprocess.run(
        [node, str(BULK_MJS)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"Node bulk consume test failed:\n{proc.stderr}\n{proc.stdout}"
    assert "PASS:" in proc.stdout


def test_hud_modals_expose_immediate_bulk_controls() -> None:
    """Ensure YouTube, Snack, and Custom HUD modals render visible bulk-consume controls."""
    ui_code = REWARD_UI_JS.read_text(encoding="utf-8")
    core_code = REWARD_JS.read_text(encoding="utf-8")

    # 1. YouTube modal bulk controls
    assert 'id="yt-deduct-area"' in ui_code
    assert 'id="yt-consume-quantity"' in ui_code
    assert 'id="yt-use-all-btn"' in ui_code
    assert 'id="yt-qty-minus"' in ui_code
    assert 'id="yt-qty-plus"' in ui_code
    assert 'id="deduct-yt-btn"' in ui_code
    assert "data-yt-preset=" in ui_code

    # 2. Snack modal bulk controls are visible immediately (display:block, not display:none)
    snack_section_idx = ui_code.find('id="snack-deduct-area"')
    assert snack_section_idx != -1, "#snack-deduct-area must exist"
    snack_tag = ui_code[snack_section_idx - 20 : snack_section_idx + 180]
    assert "display:block" in snack_tag, "#snack-deduct-area must be immediately visible (display:block)"
    assert 'id="snack-consume-quantity"' in ui_code
    assert 'id="snack-use-all-btn"' in ui_code
    assert 'id="snack-qty-minus"' in ui_code
    assert 'id="snack-qty-plus"' in ui_code
    assert 'id="deduct-snack-btn"' in ui_code
    assert "data-snack-preset=" in ui_code

    # 3. Custom modal bulk controls
    assert 'id="custom-consume-quantity"' in ui_code
    assert 'id="custom-use-all-btn"' in ui_code
    assert 'id="custom-qty-minus"' in ui_code
    assert 'id="custom-qty-plus"' in ui_code
    assert 'id="deduct-custom-btn"' in ui_code
    assert "data-custom-preset=" in ui_code

    # 4. Core consumeInternal supports bulk youtube (safeAmount * 10)
    assert "const minutesToDeduct = safeAmount * 10;" in core_code
    assert "state.youtube_minutes -= minutesToDeduct;" in core_code


def test_reward_modal_dark_mode_text_contrast() -> None:
    """Ensure reward modals and number inputs enforce dark foreground text on white modal cards."""
    css_code = REWARD_CSS.read_text(encoding="utf-8")
    ui_code = REWARD_UI_JS.read_text(encoding="utf-8")

    assert ".reward-modal-content" in css_code
    assert "color: #0f172a;" in css_code
    assert '.reward-modal-content input[type="number"]' in css_code
    assert '.reward-modal-content input[type="number"]' in ui_code
    assert "color: #0f172a !important;" in ui_code
