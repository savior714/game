"""물감 색 섞기 게임 계약 검증.

자유 실험만 있던 페이지를 목표 색 맞히기 게임으로 완성한 계약:
- RYB 감산 혼합 (노랑+파랑=초록처럼 실제 물감과 같은 결과)
- 12개 미션·별·점수·힌트·랜덤 도전·색상 도감·진도 저장
- 조명 밝기는 미리보기 전용이라 채점에 영향을 주지 않는다
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAINT_DIR = ROOT / "experiments" / "space-explorer"
PAINT_HTML = PAINT_DIR / "paint-mixing.html"
PAINT_JS = PAINT_DIR / "paint-mixing.js"
MINIGAMES_CSS = PAINT_DIR / "space-explorer-minigames.css"


def _html() -> str:
    return PAINT_HTML.read_text(encoding="utf-8")


def _js() -> str:
    return PAINT_JS.read_text(encoding="utf-8")


def _node() -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required for JavaScript contract tests")
    return node


def _color_math_block() -> str:
    match = re.search(
        r"/\* PAINT_COLOR_MATH_START \*/(.*?)/\* PAINT_COLOR_MATH_END \*/",
        _js(),
        flags=re.DOTALL,
    )
    assert match, "PAINT_COLOR_MATH 순수 색상 계산 블록이 없습니다"
    return match.group(1)


def _run_color_math(snippet: str) -> dict:
    node = _node()
    harness = f"{_color_math_block()}\n{snippet}"
    result = subprocess.run(
        [node, "-e", harness],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_paint_game_page_has_game_chrome() -> None:
    html = _html()

    for element_id in [
        "paint-score",
        "paint-star-total",
        "paint-streak",
        "paint-discovery-count",
        "paint-help-button",
        "paint-sound-button",
        "paint-mission-panel",
        "paint-mission-title",
        "paint-mission-story",
        "paint-target-swatch",
        "paint-mine-swatch",
        "paint-similarity",
        "paint-similarity-fill",
        "paint-mission-grid",
        "paint-random-button",
        "paint-capacity-text",
        "paint-undo-button",
        "paint-hint-button",
        "paint-submit-button",
        "paint-feedback",
        "paint-recipe",
        "paint-collection-grid",
        "paint-success-modal",
        "paint-next-button",
        "paint-help-modal",
        "paint-toast",
        "paint-confetti-layer",
    ]:
        assert f'id="{element_id}"' in html, f"게임 UI 요소 누락: {element_id}"

    assert 'data-mode="game"' in html
    assert 'data-mode="free"' in html
    for color in ["yellow", "blue", "red", "white", "black"]:
        assert f'data-color="{color}"' in html, f"물감 튜브 누락: {color}"
        assert f'data-remove="{color}"' in html, f"방울 빼기 버튼 누락: {color}"


def test_paint_game_script_has_full_game_loop() -> None:
    js = _js()

    assert js.count('id: "mission-') == 12, "미션은 12개여야 합니다"
    for contract in [
        "const MISSIONS = [",
        'const STORAGE_KEY = "aiden_paint_mixing_game_v1";',
        "function startMission(",
        "function checkAnswer(",
        "function generateRandomMission(",
        "function computeColorSimilarity(",
        "function getStarCount(",
        "function loadProgress(",
        "function saveProgress(",
        "function addDrop(",
        "function removeOneDrop(",
        "function undoLastDrop(",
        "function useHint(",
        "function setMode(",
        "function renderMissionGrid(",
        "function renderCollection(",
        "function spawnConfetti(",
        "const PASS_SIMILARITY = 70;",
        "const THREE_STAR_SIMILARITY = 93;",
        "const MAX_DROPS = 12;",
    ]:
        assert contract in js, f"게임 루프 계약 누락: {contract}"


def test_scoring_ignores_brightness_preview() -> None:
    """조명 밝기는 자유 실험 미리보기 전용이라 목표 색 채점을 바꾸면 안 된다."""
    js = _js()

    assert "return mixEntriesToRgb(getActiveEntries(), 1);" in js
    assert 'brightnessInput.disabled = mode !== "free";' in js


def test_subtractive_ryb_mixing_matches_real_paint() -> None:
    """RGB 평균이 아니라 RYB 혼합이라 교육용 색이 정확히 나와야 한다."""
    out = _run_color_math(
        """
        const mix = (r) => mixEntriesToRgb(recipeToEntries(r), 1);
        const result = {
          green: rgbToHex(mix({yellow: 1, blue: 1})),
          orange: rgbToHex(mix({red: 1, yellow: 1})),
          purple: rgbToHex(mix({red: 1, blue: 1})),
          brown: rgbToHex(mix({red: 1, yellow: 1, blue: 1})),
          greenName: findNearestNamedColor(mix({yellow: 1, blue: 1})).name,
          purpleName: findNearestNamedColor(mix({red: 1, blue: 1})).name,
          limeName: findNearestNamedColor(mix({yellow: 2, blue: 1})).name,
          sameRatio: computeColorSimilarity(
            mix({yellow: 1, blue: 1}),
            mix({yellow: 2, blue: 2})
          ),
          offByOne: computeColorSimilarity(
            mix({yellow: 1, blue: 1}),
            mix({yellow: 2, blue: 1})
          ),
          wrongHue: computeColorSimilarity(
            mix({yellow: 1, blue: 1}),
            mix({red: 1, blue: 1})
          ),
          stars: [getStarCount(100), getStarCount(85), getStarCount(75), getStarCount(50)],
        };
        console.log(JSON.stringify(result));
        """
    )

    assert out["green"] == "#00B050", "노랑+파랑은 초록이어야 합니다"
    assert out["orange"] == "#FF8000", "빨강+노랑은 주황이어야 합니다"
    assert out["purple"] == "#8034C8", "빨강+파랑은 보라여야 합니다"
    assert out["brown"] == "#5C3A20", "삼원색 모두는 갈색이어야 합니다"
    assert out["greenName"] == "초록"
    assert out["purpleName"] == "보라"
    assert out["limeName"] == "연두"
    assert out["sameRatio"] == 100, "같은 비율이면 방울 수가 달라도 같은 색입니다"
    assert 70 <= out["offByOne"] < 93, "한 방울 비율 오류는 통과하되 만점은 아닙니다"
    assert out["wrongHue"] < 70, "전혀 다른 색조는 통과하면 안 됩니다"
    assert out["stars"] == [3, 2, 1, 0]


def test_all_missions_are_solvable_named_and_distinct() -> None:
    """12개 미션 레시피를 실행해 이름이 맞고 서로 구분되는지 검증한다."""
    js = _js()
    found = re.findall(
        r'colorName: "([^"]+)", story: ".*?", recipe: \{([^}]+)\}',
        js,
        flags=re.DOTALL,
    )
    assert len(found) == 12, f"미션 레시피 파싱 결과: {len(found)}개"

    missions_js = ",\n".join(
        f'{{ name: "{name}", recipe: {{{recipe}}} }}' for name, recipe in found
    )
    out = _run_color_math(
        f"""
        const missions = [{missions_js}];
        const mix = (r) => mixEntriesToRgb(recipeToEntries(r), 1);
        const names = missions.map((m) => findNearestNamedColor(mix(m.recipe)).name);
        const rgbs = missions.map((m) => mix(m.recipe));
        let maxPairSimilarity = 0;
        for (let i = 0; i < rgbs.length; i += 1) {{
          for (let j = i + 1; j < rgbs.length; j += 1) {{
            maxPairSimilarity = Math.max(
              maxPairSimilarity,
              computeColorSimilarity(rgbs[i], rgbs[j])
            );
          }}
        }}
        console.log(JSON.stringify({{ names, maxPairSimilarity }}));
        """
    )

    expected_names = [name for name, _ in found]
    assert out["names"] == expected_names, (
        f"미션 목표 색 이름과 실제 혼합 결과가 다릅니다: {out['names']} vs {expected_names}"
    )
    assert out["maxPairSimilarity"] < 93, (
        "서로 다른 미션 목표가 별 3개 범위까지 닮으면 안 됩니다"
    )

    for _name, recipe in found:
        entries = re.findall(r"(yellow|blue|red|white|black): (\d+)", recipe)
        assert entries, f"알 수 없는 물감 레시피: {recipe}"
        total = sum(int(amount) for _key, amount in entries)
        assert 2 <= total <= 12, f"미션 방울 수는 비커 용량 안이어야 합니다: {recipe}"


def test_paint_game_stylesheet_has_game_contracts() -> None:
    css = MINIGAMES_CSS.read_text(encoding="utf-8")

    for selector in [
        ".paint-mode-tab",
        ".paint-mission-card",
        ".paint-versus-swatch",
        ".paint-similarity-fill",
        ".paint-capacity-fill",
        ".paint-submit-button",
        ".paint-minus",
        ".paint-collection-item",
        ".paint-modal",
        ".paint-confetti-piece",
        ".paint-toast",
        "@keyframes paint-confetti-fall",
        "prefers-reduced-motion",
    ]:
        assert selector in css, f"게임 스타일 계약 누락: {selector}"

    for paint in ["yellow", "blue", "red", "white", "black"]:
        assert f'.color-chip[data-color="{paint}"]' in css, (
            f"물감 튜브 색 누락: {paint}"
        )
