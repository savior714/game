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
    assert "experiments/space-explorer/index.html" in html
    # 상단 크롬은 홈 컨트롤 하나(brand 링크)만 갖는다
    assert 'id="main-top-nav"' not in html
    assert "ag-hud__home" not in html
    assert "ag-hud__brand-home" in html

    # Modern Hub UI Structure & Functional Verification
    assert "INTERACTIVE LEARNING PLAYGROUND" in html
    assert "DREAM TEAM" not in html
    assert "console-hud" in html
    assert "dream-grid" in html
    assert "console-footer" in html
    assert "CORE QUIZ LABS" in html
    assert "SELECT" not in html
    assert "󰁌" not in html
    assert "fps-counter" not in html

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
    assert "hud-left-section" in html
    assert 'id="reward-inventory-mount"' in html
    assert "GP" not in html
    assert "12,500" not in html
    assert "🪙" not in html

    # 2. 홈 컨트롤은 brand 링크 하나뿐 (자기 자신을 가리키는 nav는 두지 않는다)
    header_start = html.index("<header")
    header_end = html.index("</header>", header_start)
    header_html = html[header_start:header_end]
    assert 'href="./index.html"' in header_html
    assert "ag-hud__brand-home" in header_html
    assert "ag-hud__home" not in header_html
    assert "aria-current" not in header_html

    # 3. reward_ui.js mount support
    assert "document.getElementById('reward-inventory-mount')" in reward_ui
    assert "is-integrated" in reward_ui

    # 4. styles.css integration styling
    assert ".hud-reward-mount" in styles
    assert ".hud-reward-mount #reward-inventory" in styles
    assert ".hud-reward-mount #reward-inventory .inventory-item.gem-item" in styles
