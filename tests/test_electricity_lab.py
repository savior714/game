"""전기 발전 실험실(Power Lab) 계약 검증.

새 실험 페이지 `experiments/electricity/`가 다음 계약을 지키는지 고정한다.

- 메인 허브에서 바로 열리는 자기완결형(외부 CDN 의존 없음) 어린이 실험 페이지
- 전기와 관련된 일곱 가지 발전 실험이 **한 페이지 안에** 모두 존재한다
- DOM과 분리된 순수 물리 엔진(`electricity-physics.js`)이 회로·정전기·전지·
  유도·태양광·풍력·수력 계산을 실제 수치로 만족한다
- `tests/fixtures/electricity_smoke.mjs` 하니스로 초기화·상호작용·프레임 루프가
  예외 없이 동작하고 각 실험의 목표(발견 완료)에 도달할 수 있다
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
POWER_DIR = ROOT / "experiments" / "electricity"
POWER_HTML = POWER_DIR / "index.html"
POWER_JS = POWER_DIR / "electricity.js"
POWER_WORLD = POWER_DIR / "world.js"
POWER_AUDIO = POWER_DIR / "audio.js"
POWER_TEXTURES = POWER_DIR / "textures.js"
POWER_PHYSICS = POWER_DIR / "electricity-physics.js"
POWER_CSS = POWER_DIR / "electricity.css"
SMOKE_HARNESS = ROOT / "tests" / "fixtures" / "electricity_smoke.mjs"

STATION_IDS = (
    "circuit",
    "static",
    "fruit",
    "generator",
    "solar",
    "wind",
    "hydro",
)


def _html() -> str:
    return POWER_HTML.read_text(encoding="utf-8")


def _js() -> str:
    return POWER_JS.read_text(encoding="utf-8")


def _css() -> str:
    return POWER_CSS.read_text(encoding="utf-8")


def _node() -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required for JavaScript contract tests")
    return node


def _run_physics(snippet: str) -> object:
    harness = (
        "const P = require(" + json.dumps(str(POWER_PHYSICS)) + ");\n"
        "const out = (() => { " + snippet + " })();\n"
        "console.log(JSON.stringify(out));\n"
    )
    result = subprocess.run(
        [_node(), "-e", harness],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_power_lab_files_exist() -> None:
    for path in (
        POWER_HTML,
        POWER_JS,
        POWER_WORLD,
        POWER_AUDIO,
        POWER_TEXTURES,
        POWER_PHYSICS,
        POWER_CSS,
    ):
        assert path.is_file(), (
            f"전기 발전 실험실 파일이 없습니다: {path.relative_to(ROOT)}"
        )


def test_power_lab_has_no_external_runtime_dependency() -> None:
    for path in (
        POWER_HTML,
        POWER_JS,
        POWER_WORLD,
        POWER_AUDIO,
        POWER_TEXTURES,
        POWER_PHYSICS,
        POWER_CSS,
    ):
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
    assert "<title>" in html and "전기" in html
    assert 'name="viewport"' in html
    assert 'id="island-canvas"' in html


def test_power_lab_links_back_to_main_hub() -> None:
    html = _html()
    assert 'href="../../index.html"' in html
    # 홈 이동은 brand(워드마크) 링크가 단일 컨트롤로 담당한다
    assert 'class="lab-brand"' in html
    assert "brand-home" in html
    assert 'target="_top"' in html


def test_power_lab_is_an_immersive_page_without_reward_mount() -> None:
    html = _html()
    assert 'id="reward-inventory-mount"' not in html
    assert "shared/ui/hud.css" not in html
    assert 'id="help-dialog"' in html
    assert 'id="sound-button"' in html


def test_power_lab_ships_seven_stations_on_one_page() -> None:
    html = _html()
    for station in STATION_IDS:
        assert f'id="station-{station}"' in html, f"{station} 실험대가 없습니다"
        assert f'id="canvas-{station}"' in html, f"{station} 실험대 캔버스가 없습니다"
        assert f'id="read-{station}"' in html, f"{station} 실험대 안내 문구가 없습니다"
        assert f'id="meter-{station}"' in html, f"{station} 실험대 계량 바가 없습니다"
        assert f'id="goal-{station}"' in html, f"{station} 실험대 목표가 없습니다"
        assert f'id="why-{station}"' in html, f"{station} 실험대 원리 설명이 없습니다"
        assert f'id="stamp-{station}"' in html, f"{station} 실험대 발견 도장이 없습니다"

    # 한 페이지 안에서 실험 사이를 오가는 바로가기와 정리 노트
    assert 'class="lab-jump"' in html
    for station in STATION_IDS:
        assert f'href="#station-{station}"' in html
    assert 'id="outro-title"' in html
    assert 'id="reset-all"' in html

    # 발견 도장과 원리 설명은 처음에는 접혀 있어야 한다
    assert html.count("data-stamp hidden") == len(STATION_IDS)
    assert html.count('class="why" id="why-') == len(STATION_IDS)
    assert html.count('aria-expanded="false" aria-controls="why-') == len(STATION_IDS)

    assert 'role="status"' in html
    assert 'aria-live="polite"' in html
    assert html.count('role="status" aria-live="polite"') >= len(STATION_IDS)


def test_power_lab_exposes_play_controls() -> None:
    html = _html()
    for control in (
        'data-material="copper"',
        'data-material="wood"',
        'id="switch-circuit"',
        'id="voltage-range"',
        'id="rub-button"',
        'id="discharge-button"',
        'data-fruit="lemon"',
        'id="cells-plus"',
        'id="cells-minus"',
        'data-spin="140"',
        'id="turns-range"',
        'id="magnet-range"',
        'id="sun-range"',
        'id="tilt-range"',
        'id="cloud-range"',
        'id="tilt-auto"',
        'id="wind-range"',
        'id="blade-range"',
        'data-blades="3"',
        'id="head-range"',
        'id="flow-range"',
    ):
        assert control in html, f"전기 발전 실험실 컨트롤이 없습니다: {control}"


def test_power_lab_canvases_are_keyboard_reachable() -> None:
    html = _html()
    # 풍선(마찰 전기)과 손잡이(발전기)는 끌기와 함께 키보드 조작을 제공한다
    assert 'id="canvas-static"' in html
    assert 'id="canvas-generator"' in html
    assert html.count('tabindex="0"') == 2
    assert html.count('role="application"') == 2


def test_power_lab_persists_progress_and_respects_reduced_motion() -> None:
    js = _js()
    assert "aiden_electricity_lab_v1" in js
    assert "localStorage" in js
    assert "prefers-reduced-motion" in js
    assert "prefersReducedMotion" in js
    assert "window.requestAnimationFrame(frame)" in js
    assert "prefers-reduced-motion" in _css()


def test_power_lab_uses_shared_korean_font_faces() -> None:
    css = _css()
    assert "noto-sans-kr-400.woff2" in css
    assert "noto-sans-kr-700.woff2" in css
    assert (POWER_DIR.parent / "space-explorer" / "assets" / "fonts").is_dir()


def test_circuit_needs_a_closed_loop_and_a_conductor() -> None:
    result = _run_physics(
        "return {"
        " full: P.circuitState({material: 'copper', voltage: 3}),"
        " coin: P.circuitState({material: 'coin', voltage: 3}),"
        " wood: P.circuitState({material: 'wood', voltage: 3}),"
        " open: P.circuitState({material: 'copper', voltage: 3, closed: false}),"
        " weak: P.circuitState({material: 'copper', voltage: 1.5})"
        "};"
    )
    assert result["full"]["brightness"] == 1
    assert result["full"]["lit"] is True
    assert 0 < result["coin"]["brightness"] < result["full"]["brightness"]
    assert result["wood"]["current"] == 0
    assert result["open"]["current"] == 0
    assert result["weak"]["brightness"] < 1


def test_static_charge_builds_up_and_fades_away() -> None:
    result = _run_physics(
        "let charge = 0;"
        "for (let i = 0; i < 60; i += 1) charge = P.staticRub(charge, 1, 1 / 60);"
        "const rubbed = charge;"
        "const reach = P.staticReach(charge);"
        "for (let i = 0; i < 600; i += 1) charge = P.staticDecay(charge, 1 / 60);"
        "return {"
        " rubbed: rubbed, decayed: charge,"
        " near: P.staticGrab(rubbed, reach * 0.5),"
        " far: P.staticGrab(rubbed, reach * 3),"
        " empty: P.staticGrab(0, 10)"
        "};"
    )
    assert result["rubbed"] > 50, "털에 문지르면 전하가 모여야 합니다"
    assert result["decayed"] == 0, "시간이 지나면 전하가 사라져야 합니다"
    assert result["near"] is True
    assert result["far"] is False
    assert result["empty"] is False


def test_fruit_cells_add_up_until_the_led_is_full() -> None:
    result = _run_physics(
        "return [1, 2, 3, 4].map((cells) => P.fruitBattery({fruit: 'lemon', cells: cells}));"
    )
    assert result[0]["volts"] == pytest.approx(0.9)
    assert result[0]["lit"] is False
    assert result[1]["lit"] is True
    assert 0 < result[1]["level"] < 1
    assert result[2]["level"] > result[1]["level"]
    assert result[3]["full"] is True
    assert result[3]["volts"] == pytest.approx(3.6)


def test_generator_makes_more_power_when_faster_stronger_or_denser() -> None:
    result = _run_physics(
        "return {"
        " idle: P.generatorOutput({turns: 240, fieldTesla: 0.18, rpm: 0}),"
        " slow: P.generatorOutput({turns: 240, fieldTesla: 0.18, rpm: 60}),"
        " fast: P.generatorOutput({turns: 240, fieldTesla: 0.18, rpm: 120}),"
        " dense: P.generatorOutput({turns: 480, fieldTesla: 0.18, rpm: 120}),"
        " strong: P.generatorOutput({turns: 240, fieldTesla: 0.36, rpm: 120})"
        "};"
    )
    assert result["idle"]["watts"] == 0
    assert result["fast"]["watts"] > result["slow"]["watts"] > 0
    assert result["dense"]["emf"] == pytest.approx(result["fast"]["emf"] * 2, rel=1e-4)
    assert result["strong"]["emf"] == pytest.approx(result["fast"]["emf"] * 2, rel=1e-4)


def test_solar_panel_likes_facing_the_sun() -> None:
    result = _run_physics(
        "return {"
        " straight: P.solarOutput({sunAltitudeDeg: 60, panelTiltDeg: 30, cloudiness: 0}),"
        " flat: P.solarOutput({sunAltitudeDeg: 60, panelTiltDeg: 0, cloudiness: 0}),"
        " cloudy: P.solarOutput({sunAltitudeDeg: 60, panelTiltDeg: 30, cloudiness: 1}),"
        " low: P.solarOutput({sunAltitudeDeg: 5, panelTiltDeg: 30, cloudiness: 0})"
        "};"
    )
    assert result["straight"]["incidence"] == pytest.approx(1, abs=0.001)
    assert result["straight"]["optimalTilt"] == pytest.approx(30)
    assert result["straight"]["watts"] > result["flat"]["watts"]
    assert result["cloudy"]["watts"] < result["straight"]["watts"]
    assert result["low"]["watts"] < result["straight"]["watts"]


def test_wind_power_grows_with_the_cube_of_wind_speed() -> None:
    result = _run_physics(
        "return {"
        " calm: P.windPower({windSpeed: 4, bladeLength: 0.3, bladeCount: 3}).watts,"
        " gale: P.windPower({windSpeed: 8, bladeLength: 0.3, bladeCount: 3}).watts,"
        " long: P.windPower({windSpeed: 4, bladeLength: 0.5, bladeCount: 3}).watts,"
        " many: P.windPower({windSpeed: 4, bladeLength: 0.3, bladeCount: 6}).watts,"
        " still: P.windPower({windSpeed: 0, bladeLength: 0.3, bladeCount: 3}).watts"
        "};"
    )
    assert result["gale"] == pytest.approx(result["calm"] * 8, rel=1e-3)
    assert result["long"] > result["calm"]
    assert result["many"] < result["calm"], "날개가 너무 많으면 효율이 떨어져야 합니다"
    assert result["still"] == 0


def test_hydro_power_scales_with_head_and_flow() -> None:
    result = _run_physics(
        "return {"
        " base: P.hydroPower({headMeters: 1, flowLitersPerSec: 2}).watts,"
        " higher: P.hydroPower({headMeters: 2, flowLitersPerSec: 2}).watts,"
        " wetter: P.hydroPower({headMeters: 1, flowLitersPerSec: 4}).watts,"
        " dry: P.hydroPower({headMeters: 0, flowLitersPerSec: 2}).watts,"
        " spin: P.wheelRpm({headMeters: 1, flowLitersPerSec: 2})"
        "};"
    )
    assert result["higher"] == pytest.approx(result["base"] * 2, rel=1e-3)
    assert result["wetter"] == pytest.approx(result["base"] * 2, rel=1e-3)
    assert result["dry"] == 0
    assert result["spin"] > 0


def test_energy_is_power_times_time() -> None:
    result = _run_physics(
        "return { kept: P.energyJoules(2, 3), idle: P.energyJoules(0, 9) };"
    )
    assert result["kept"] == pytest.approx(6)
    assert result["idle"] == 0


def test_island_power_grid_lights_six_village_landmarks_and_cuts_on_blackout() -> None:
    result = _run_physics(
        "const closedCopper = P.circuitState({material: 'copper', voltage: 4.5, closed: true});"
        "const openSwitch = P.circuitState({material: 'copper', voltage: 4.5, closed: false});"
        "return {"
        " low: P.islandGridState({solarWatts: 10, circuit: closedCopper}),"
        " full: P.islandGridState({generatorWatts: 40, windWatts: 55, hydroWatts: 50, solarWatts: 9, surgeWatts: 10, circuit: closedCopper}),"
        " blackout: P.islandGridState({generatorWatts: 40, windWatts: 55, hydroWatts: 50, circuit: openSwitch})"
        "};"
    )
    assert result["low"]["landmarks"]["cottages"] > 0
    assert result["low"]["landmarks"]["festival"] == 0
    assert result["full"]["litCount"] == 6
    assert result["full"]["landmarks"]["festival"] == 1
    assert result["blackout"]["deliveredWatts"] == 0
    assert result["blackout"]["litCount"] == 0


def test_power_lab_runs_without_runtime_errors() -> None:
    node = _node()
    result = subprocess.run(
        [node, str(SMOKE_HARNESS)],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    assert result.stderr.strip() == "", f"불필요한 런타임 경고 출력: {result.stderr}"
    data = json.loads(result.stdout.strip().splitlines()[-1])

    assert data["errors"] == [], f"실험 실행 중 예외가 발생했습니다: {data['errors']}"
    assert data["physics"] is True, "PowerPhysics 전역 모듈이 등록되지 않았습니다"
    assert data["dots"] == len(STATION_IDS)
    assert data["worldTags"] == 8, "3D 섬 플로팅 구역 라벨 8개가 생성되어야 합니다"
    assert data["peakWatts"] > 120, "모든 발전기 가동 시 120W 이상 공급되어야 합니다"
    assert data["blackoutWatts"] == 0, "주 스위치 개방 즉시 0W 정전이 되어야 합니다"

    for station in STATION_IDS:
        assert data["play"]["stamps"][station] is True, (
            f"{station} 목표에 도달하지 못했습니다"
        )
        assert data["play"]["reads"][station], f"{station} 안내 문구가 비어 있습니다"


def test_main_hub_links_to_power_lab() -> None:
    hub = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "./experiments/electricity/index.html" in hub
    assert "전기" in hub


def test_readme_routes_to_power_lab() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "experiments/electricity/index.html" in readme
    assert "experiments/electricity/electricity-physics.js" in readme
