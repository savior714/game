from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT


def test_templates_index_is_aidengame_hub_page() -> None:
    html = (TEMPLATES / "index.html").read_text(encoding="utf-8")

    assert "학습 게임 놀이터" in html
    assert "오늘은 어떤" in html
    assert "수학 놀이" in html
    assert "영어 놀이" in html
    assert "국어 놀이" in html
    assert "과학 놀이" in html
    assert "태양계 탐험 (실험)" in html
    assert "<nav" in html
    assert "Main navigation" in html
    assert "experiments/space-explorer/index.html" in html
    assert 'id="main-top-nav"' in html

    # Console UI Specific Structure Verification
    assert "DREAM TEAM LEARNING ARENA" in html
    assert "console-hud" in html
    assert "dream-grid" in html
    assert "console-footer" in html
    assert "CORE SUBJECT QUICK SLOTS" in html

    assert "Ocean Rescue" in html
    assert "잠수정을 타고 바다 생물을 구조해요" in html
    assert html.count("./ocean-rescue/index.html") == 1
    assert 'aria-labelledby="ocean-rescue-card-title"' in html
    assert 'id="ocean-rescue-card-title"' in html
    assert (ROOT / "ocean-rescue" / "index.html").is_file()

    ocean_rescue_position = html.index("./ocean-rescue/index.html")
    space_experiment_position = html.index(
        "./experiments/space-explorer/index.html",
        ocean_rescue_position,
    )
    assert ocean_rescue_position < space_experiment_position


def test_main_hub_unified_topbar_structure() -> None:
    html = (TEMPLATES / "index.html").read_text(encoding="utf-8")
    styles = (TEMPLATES / "styles.css").read_text(encoding="utf-8")
    reward_ui = (ROOT / "domains" / "reward" / "reward_ui.js").read_text(
        encoding="utf-8"
    )

    # 1. index.html unified header structure
    assert 'class="console-hud' in html
    assert 'class="hud-left-section"' in html
    assert 'id="main-top-nav"' in html
    assert 'id="reward-inventory-mount"' in html
    assert "GP" not in html
    assert "12,500" not in html
    assert "🪙" not in html

    # 2. reward_ui.js mount support
    assert "document.getElementById('reward-inventory-mount')" in reward_ui
    assert "is-integrated" in reward_ui

    # 3. styles.css integration styling
    assert ".hud-reward-mount" in styles
    assert ".hud-reward-mount #reward-inventory" in styles
    assert ".hud-reward-mount #reward-inventory .inventory-item.gem-item" in styles
