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
