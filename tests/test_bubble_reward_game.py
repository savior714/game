from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUBBLE_INDEX = ROOT / "experiments/bubble/index.html"
REWARD_SCRIPT = ROOT / "domains/reward/reward.js"
REWARD_UI_SCRIPT = ROOT / "domains/reward/reward_ui.js"
GUARDIAN_SCRIPT = ROOT / "domains/reward/guardian/guardian.js"
SYNC_SCRIPT = ROOT / "domains/sync/sync-engine.js"


def test_bubble_game_entry_exists():
    """Ensure experiments/bubble/index.html entry file exists."""
    assert BUBBLE_INDEX.is_file(), f"Bubble game index file missing at {BUBBLE_INDEX}"
    content = BUBBLE_INDEX.read_text(encoding="utf-8")
    assert "closeBubble" in content, (
        "Bubble game index must support postMessage close event"
    )


def test_reward_system_bubble_integration():
    """Ensure RewardSystem includes bubble item and bubble_plays handling."""
    reward_content = REWARD_SCRIPT.read_text(encoding="utf-8")
    assert "bubble_plays" in reward_content
    assert "id: 'bubble'" in reward_content or 'id: "bubble"' in reward_content
    assert "openBubbleModal" in reward_content

    reward_ui_content = REWARD_UI_SCRIPT.read_text(encoding="utf-8")
    assert "openBubbleModal" in reward_ui_content
    assert "../../experiments/bubble/" in reward_ui_content

    guardian_content = GUARDIAN_SCRIPT.read_text(encoding="utf-8")
    assert "bubble_plays" in guardian_content
    assert "id: 'bubble'" in guardian_content or 'id: "bubble"' in guardian_content

    sync_content = SYNC_SCRIPT.read_text(encoding="utf-8")
    assert "bubble_plays" in sync_content
    assert "id: 'bubble'" in sync_content or 'id: "bubble"' in sync_content


def test_ensure_default_shop_items_on_load():
    """Ensure RewardSystem load() reconciles missing default items like bubble from legacy localStorage."""
    reward_content = REWARD_SCRIPT.read_text(encoding="utf-8")
    assert "ensureDefaultShopItems" in reward_content, (
        "reward.js must define ensureDefaultShopItems to reconcile missing default items on load"
    )


def test_reward_inventory_single_line_layout_contract():
    """Ensure reward.css and reward_ui.js strictly enforce nowrap layout for single-line top inventory bar."""
    css_content = (ROOT / "domains/reward/reward.css").read_text(encoding="utf-8")
    assert "flex-wrap: nowrap !important" in css_content, (
        "reward.css must enforce flex-wrap: nowrap !important on inventory-left and inventory-content"
    )

    ui_content = REWARD_UI_SCRIPT.read_text(encoding="utf-8")
    assert "flex-wrap: nowrap !important" in ui_content, (
        "reward_ui.js critical CSS must enforce flex-wrap: nowrap !important for immediate single-line rendering"
    )

