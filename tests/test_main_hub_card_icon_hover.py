"""메인 허브 카드 아이콘 호버 상호작용 계약.

재현했던 결함: 카드 이모지가 가로 전체 블록(`text-4xl ... group-hover:scale-110`)
안에 있어서 scale의 기준점이 블록 중심이 되었다. 그 결과 호버 시 왼쪽 끝에 있던
글리프가 카드 밖으로 밀려나 보이는 이탈이 발생했다.

고정하는 계약: 아이콘은 자기 크기의 타일에 고정되고, 호버 반응은 좌우 이탈 없이
카드(타일) 안에서만 일어난다.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CARD_ICON_GLYPHS = ("🌊", "✏️", "🪐", "🎮")
ICON_REACTION_KEYFRAMES = ("card-icon-react", "card-icon-react-sm")


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _balanced_block(text: str, start: int) -> str:
    """`start` 위치의 `{` 부터 대응하는 `}` 까지 본문을 반환한다."""
    brace = text.index("{", start)
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1 : index]
    raise AssertionError(f"중괄호가 닫히지 않음: offset {start}")


def _css_rule(css: str, selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{", css)
    assert match, f"styles.css 에서 규칙을 찾지 못함: {selector}"
    return _balanced_block(css, match.start())


def _keyframes(css: str, name: str) -> str:
    match = re.search(r"@keyframes\s+" + re.escape(name) + r"\s*\{", css)
    assert match, f"styles.css 에서 keyframes 를 찾지 못함: {name}"
    return _balanced_block(css, match.start())


def _frame(block: str, stop: str) -> str:
    match = re.search(re.escape(stop) + r"\s*\{(.*?)\}", block, re.S)
    assert match, f"keyframes 프레임 누락: {stop}"
    return " ".join(match.group(1).split())


def test_hub_card_icons_are_anchored_in_icon_tiles() -> None:
    html = _read("index.html")

    # 네 장의 카드 아이콘 모두 고유 타일 + 글리프 구조를 가진다.
    assert len(re.findall(r'<div class="card-icon[ "]', html)) == 4
    assert html.count('class="card-icon-glyph"') == 4
    for glyph in CARD_ICON_GLYPHS:
        assert f'<span class="card-icon-glyph">{glyph}</span>' in html

    # 이탈의 원인이었던 "가로 전체 블록 scale" 호버 클래스는 더 이상 쓰지 않는다.
    assert "group-hover:scale-110" not in html


def test_icon_tile_owns_a_fixed_box_so_transform_origin_is_the_icon() -> None:
    css = _read("styles.css")
    tile = _css_rule(css, ".card-icon")

    # inline-flex + 고정 크기여야 transform 기준점이 아이콘 자신과 일치한다.
    assert "display: inline-flex" in tile
    assert re.search(r"width:\s*[\d.]+rem", tile)
    assert re.search(r"height:\s*[\d.]+rem", tile)

    glyph = _css_rule(css, ".card-icon-glyph")
    assert re.search(r"font-size:\s*[\d.]+rem", glyph)


def test_icon_tile_hover_lifts_without_sideways_exit() -> None:
    css = _read("styles.css")
    hover = _css_rule(css, ".console-card:focus-within .card-icon")

    transform = re.search(r"transform:\s*([^;]+);", hover)
    assert transform, "호버 시 아이콘 타일 transform 이 없음"
    assert "translateY" in transform.group(1)
    assert "translateX" not in transform.group(1)


def test_icon_reaction_stays_in_place_and_returns_to_rest() -> None:
    css = _read("styles.css")

    for name in ICON_REACTION_KEYFRAMES:
        block = _keyframes(css, name)

        # 시작과 끝이 같아야 호버가 끝나도 아이콘이 튀지 않는다.
        assert _frame(block, "0%") == _frame(block, "100%")

        # 좌우 이동은 0 고정 — 위아래 통통 튀기만 허용한다.
        hops = re.findall(r"translate:\s*([^\s;]+)\s+([^\s;]+)", block)
        assert hops, f"{name} 에 translate 프레임이 없음"
        for horizontal, vertical in hops:
            assert horizontal == "0", f"{name}: 좌우 이탈 {horizontal}"
            assert abs(float(vertical.replace("px", ""))) <= 8, (
                f"{name}: 타일을 벗어나는 수직 이동 {vertical}"
            )

        # 과하게 커지면 결국 카드 밖으로 넘쳐 보인다.
        scales = [float(value) for value in re.findall(r"scale:\s*([\d.]+)", block)]
        assert scales and max(scales) <= 1.25, f"{name}: 과한 확대 {scales}"


def test_pulse_ring_fades_back_to_invisible_base_state() -> None:
    css = _read("styles.css")
    ring = _css_rule(css, ".card-icon-pulse")
    block = _keyframes(css, "card-icon-pulse")

    # 기본 상태가 opacity 0 이고 마지막 프레임도 같아야 끊김 없이 사라진다.
    assert re.search(r"opacity:\s*0\s*;", ring)
    assert "opacity: 0" in _frame(block, "100%")


def test_reduced_motion_keeps_feedback_without_icon_movement() -> None:
    css = _read("styles.css")
    match = re.search(r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{", css)
    assert match, "prefers-reduced-motion 대체 스타일 없음"
    block = _balanced_block(css, match.start())

    assert ".card-icon-glyph" in block
    assert ".card-icon-pulse" in block
    assert "animation: none" in block
    assert "transform: none" in block
