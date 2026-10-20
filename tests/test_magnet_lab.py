"""자석 실험실(Magnet Lab) 계약 검증.

새 실험 페이지 `experiments/magnet/`가 다음 계약을 지키는지 고정한다.

- 메인 허브에서 바로 열리는 자기완결형(외부 CDN 의존 없음) 어린이 실험 페이지
- DOM과 분리된 순수 물리 엔진(`magnet-physics.js`)이 자석 인력·척력과
  철 물건만 끌어당기는 규칙을 실제 수치로 만족한다
- 자석 놀이 → 철가루/자기장 관찰 → 물질 분류로 이어지는 6개 미션과 자유 실험이 존재한다
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAGNET_DIR = ROOT / "experiments" / "magnet"
MAGNET_HTML = MAGNET_DIR / "index.html"
MAGNET_JS = MAGNET_DIR / "magnet.js"
MAGNET_PHYSICS = MAGNET_DIR / "magnet-physics.js"
MAGNET_CSS = MAGNET_DIR / "magnet.css"

MISSION_IDS = ("clips", "attract", "repel", "filings", "materials", "fishing")
ITEM_KINDS = ("clip", "nail", "key", "ball", "stick", "eraser", "coin", "compass")


def _html() -> str:
    return MAGNET_HTML.read_text(encoding="utf-8")


def _js() -> str:
    return MAGNET_JS.read_text(encoding="utf-8")


def _css() -> str:
    return MAGNET_CSS.read_text(encoding="utf-8")


def _node() -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required for JavaScript contract tests")
    return node


def _run_physics(snippet: str) -> object:
    harness = (
        f"const P = require({json.dumps(str(MAGNET_PHYSICS))});\n"
        f"const out = (() => {{ {snippet} }})();\n"
        "console.log(JSON.stringify(out));\n"
    )
    result = subprocess.run(
        [_node(), "-e", harness],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_magnet_lab_files_exist() -> None:
    for path in (MAGNET_HTML, MAGNET_JS, MAGNET_PHYSICS, MAGNET_CSS):
        assert path.is_file(), f"자석 실험실 파일이 없습니다: {path.relative_to(ROOT)}"


def test_magnet_lab_has_no_external_runtime_dependency() -> None:
    for path in (MAGNET_HTML, MAGNET_JS, MAGNET_PHYSICS, MAGNET_CSS):
        text = path.read_text(encoding="utf-8")
        assert "http://" not in text, (
            f"{path.name} cannot load insecure external resources"
        )
        assert "https://" not in text, (
            f"{path.name} cannot rely on external CDN resources"
        )
        assert "cdn." not in text, f"{path.name} cannot rely on a CDN"

    html = _html()
    assert 'lang="ko"' in html
    assert "<title>" in html and "자석" in html
    assert 'name="viewport"' in html


def test_magnet_lab_links_back_to_main_hub() -> None:
    html = _html()
    assert 'href="../../index.html"' in html
    assert "홈으로" in html
    assert 'target="_top"' in html


def test_magnet_lab_is_an_immersive_page_without_reward_mount() -> None:
    html = _html()
    assert 'id="reward-inventory-mount"' not in html
    assert "shared/ui/hud.css" not in html
    assert 'id="magnet-canvas"' in html
    assert 'tabindex="0"' in html
    assert 'role="application"' in html


def test_magnet_lab_exposes_play_tools() -> None:
    html = _html()
    assert "data-add-magnet" in html
    for kind in ITEM_KINDS:
        assert f'data-add-item="{kind}"' in html, f"{kind} 도구 버튼이 없습니다"

    for control in (
        'id="field-toggle"',
        'id="filings-toggle"',
        'id="power-range"',
        'id="reset-scene"',
        'id="mode-mission"',
        'id="mode-free"',
        'id="mission-dots"',
        'id="mission-title"',
        'id="mission-why"',
        'id="stage-hint"',
        'id="save-artwork"',
        'id="help-dialog"',
    ):
        assert control in html, f"자석 실험실 컨트롤이 없습니다: {control}"

    assert 'role="status"' in html and 'aria-live="polite"' in html
    assert html.count('role="tabpanel"') == 2
    assert html.count('role="tab"') == 2


def test_magnet_lab_toggle_switches_start_in_sync_with_state() -> None:
    html = _html()
    matches = dict(
        re.findall(r'id="(field-toggle|filings-toggle)"[^>]*aria-pressed="(\w+)"', html)
    )
    assert matches == {"field-toggle": "true", "filings-toggle": "false"}


def test_magnet_physics_poles_sit_at_both_ends() -> None:
    poles = _run_physics(
        "const m = P.createMagnet({id: 1, x: 0, y: 0, angle: 0});"
        "const list = P.poleList(m);"
        "return { n: list[0], s: list[1], length: m.length };"
    )
    assert poles["n"]["sign"] == 1, "N극은 +1 로 표현되어야 합니다"
    assert poles["s"]["sign"] == -1, "S극은 -1 로 표현되어야 합니다"
    assert poles["n"]["x"] > 0 and poles["s"]["x"] < 0
    assert poles["n"]["x"] - poles["s"]["x"] == pytest.approx(poles["length"])


def test_opposite_poles_attract_and_same_poles_repel() -> None:
    result = _run_physics(
        "const bounds = { width: 900, height: 560 };"
        "function run(a, b, bAngle) {"
        "  const m1 = P.createMagnet({id: 1, x: a, y: 280, angle: 0});"
        "  const m2 = P.createMagnet({id: 2, x: b, y: 280, angle: bAngle});"
        "  for (let i = 0; i < 240; i += 1) P.stepMagnets([m1, m2], 1 / 60, bounds);"
        "  return Math.abs(m1.x - m2.x);"
        "}"
        "return { attract: run(300, 620, 0), repel: run(300, 470, Math.PI) };"
    )
    assert result["attract"] < 280, "N극과 S극은 서로 끌어당겨 가까워져야 합니다"
    assert result["repel"] > 300, "같은 극끼리는 서로 밀어내 멀어져야 합니다"


def test_only_iron_items_are_pulled_and_captured() -> None:
    result = _run_physics(
        "const bounds = { width: 900, height: 560 };"
        "function run(magnetic) {"
        "  const magnet = P.createMagnet({id: 1, x: 200, y: 280, angle: 0});"
        "  const item = P.createItem({id: 2, x: 470, y: 280, magnetic: magnetic});"
        "  for (let i = 0; i < 600; i += 1) P.stepItems([item], [magnet], 1 / 60, bounds);"
        "  return { x: item.x, capturedBy: item.capturedBy };"
        "}"
        "return { iron: run(true), wood: run(false) };"
    )
    assert result["iron"]["capturedBy"] == 1, "철로 된 물건은 자석에 붙어야 합니다"
    assert result["wood"]["capturedBy"] is None, "철이 아닌 물건은 붙지 않아야 합니다"
    assert result["wood"]["x"] == pytest.approx(470, abs=1)


def test_captured_item_follows_the_magnet() -> None:
    result = _run_physics(
        "const bounds = { width: 900, height: 560 };"
        "const magnet = P.createMagnet({id: 1, x: 200, y: 280, angle: 0});"
        "const item = P.createItem({id: 2, x: 260, y: 280, magnetic: true});"
        "for (let i = 0; i < 240; i += 1) P.stepItems([item], [magnet], 1 / 60, bounds);"
        "const before = { x: item.x, y: item.y, capturedBy: item.capturedBy };"
        "magnet.x = 620; magnet.y = 200;"
        "P.syncCaptured([item], [magnet]);"
        "return { before: before, after: { x: item.x, y: item.y } };"
    )
    assert result["before"]["capturedBy"] == 1
    assert result["after"]["x"] > 600, "자석을 옮기면 붙은 물건도 따라가야 합니다"


def test_magnetic_field_gets_weaker_with_distance() -> None:
    result = _run_physics(
        "const magnet = P.createMagnet({id: 1, x: 400, y: 280, angle: 0});"
        "const near = P.fieldAt(400, 340, [magnet]).magnitude;"
        "const far = P.fieldAt(400, 520, [magnet]).magnitude;"
        "return { near: near, far: far };"
    )
    assert result["near"] > result["far"] > 0, "자기장은 멀어질수록 약해져야 합니다"


def test_item_reach_is_limited_so_far_items_stay_put() -> None:
    result = _run_physics(
        "const bounds = { width: 1400, height: 800 };"
        "const magnet = P.createMagnet({id: 1, x: 200, y: 400, angle: 0});"
        "const item = P.createItem({id: 2, x: 900, y: 400, magnetic: true});"
        "for (let i = 0; i < 600; i += 1) P.stepItems([item], [magnet], 1 / 60, bounds);"
        "return { x: item.x, capturedBy: item.capturedBy };"
    )
    assert result["capturedBy"] is None, "너무 먼 곳의 물건은 끌려오지 않아야 합니다"
    assert result["x"] == pytest.approx(900, abs=1)


def test_physics_stays_finite_in_a_crowded_scene() -> None:
    result = _run_physics(
        "const bounds = { width: 820, height: 540 };"
        "const magnets = ["
        "  P.createMagnet({id: 1, x: 380, y: 260, angle: 0}),"
        "  P.createMagnet({id: 2, x: 470, y: 300, angle: 2}),"
        "  P.createMagnet({id: 3, x: 420, y: 340, angle: 1})"
        "];"
        "for (let i = 0; i < 900; i += 1) P.stepMagnets(magnets, 1 / 60, bounds);"
        "return magnets.map((m) => [m.x, m.y, m.angle]);"
    )
    for x, y, angle in result:
        assert 0 <= x <= 820 and 0 <= y <= 540
        assert isinstance(angle, float)


def test_magnet_lab_ships_six_missions_and_free_play() -> None:
    js = _js()
    assert js.count('id: "') >= len(MISSION_IDS)
    for mission_id in MISSION_IDS:
        assert f'id: "{mission_id}"' in js, f"미션 {mission_id} 가 없습니다"

    for marker in (
        "MISSION_TOTAL = 6",
        "자유 실험실",
        "P.stepMagnets",
        "P.stepItems",
        "P.poleList",
        "P.fieldAt",
    ):
        assert marker in js, f"자석 실험실 로직에 필요한 표식이 없습니다: {marker}"

    html = _html()
    for label in ("미션 랩", "자유 실험", "자기장 보기", "철가루 보기"):
        assert label in html, f"실험실 화면에 '{label}' 안내가 없습니다"


def test_magnet_lab_persists_and_respects_reduced_motion() -> None:
    js = _js()
    assert "aiden_magnet_lab_v1" in js
    assert "localStorage" in js
    assert "prefers-reduced-motion" in _css()
    assert "prefersReducedMotion" in js
    assert "function frame(now)" in js
    assert "window.requestAnimationFrame(frame)" in js


def test_main_hub_links_to_magnet_lab() -> None:
    hub = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "./experiments/magnet/index.html" in hub
    assert "자석" in hub


def test_magnet_lab_uses_shared_korean_font_faces() -> None:
    css = _css()
    assert "noto-sans-kr-400.woff2" in css
    assert "noto-sans-kr-700.woff2" in css
    assert (MAGNET_DIR.parent / "space-explorer" / "assets" / "fonts").is_dir()
