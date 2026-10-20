from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REWARD_UI_SCRIPT = ROOT / "domains/reward/reward_ui.js"
MARBLE_INDEX = ROOT / "experiments/marble/index.html"


def test_marble_reward_link_target_exists():
    """Ensure the target HTML page for marble reward game exists."""
    assert MARBLE_INDEX.is_file(), f"Marble game index file missing at {MARBLE_INDEX}"


def test_reward_ui_marble_url_resolution():
    """Ensure openMarbleModal in reward_ui.js resolves URL to experiments/marble/ instead of missing domains/marble/."""
    content = REWARD_UI_SCRIPT.read_text(encoding="utf-8")
    assert "../../experiments/marble/" in content, (
        "reward_ui.js openMarbleModal must use '../../experiments/marble/' relative path"
    )
    assert "../marble/" not in content, (
        "reward_ui.js must not refer to outdated '../marble/' path"
    )


def test_marble_top_hud_does_not_cover_game_hud():
    """Ensure experiments/marble/index.html reserves top offset for .game-top-hud so #hud and #stage are not obscured."""
    content = MARBLE_INDEX.read_text(encoding="utf-8")
    assert "--top-hud-offset" in content, (
        "experiments/marble/index.html must define --top-hud-offset to prevent .game-top-hud from covering #hud"
    )
    assert "#app" in content and "padding-top" in content, (
        "experiments/marble/index.html must apply padding-top to #app below .game-top-hud"
    )
    assert "syncTopHudOffset" in content, (
        "experiments/marble/index.html must dynamically synchronize top HUD offset on load and resize"
    )

