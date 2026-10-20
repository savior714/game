"""태양계 3D 탐험대 — 시간 조작 UI 계약."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPACE_DIR = ROOT / "experiments" / "space-explorer"


def read(name: str) -> str:
    return (SPACE_DIR / name).read_text(encoding="utf-8")


def test_time_control_markup_is_present_and_accessible() -> None:
    html = read("index.html")

    assert 'id="pause-btn"' in html
    assert 'aria-pressed="false"' in html
    assert 'id="today-btn"' in html
    assert 'id="prev-day-btn"' in html
    assert 'id="next-day-btn"' in html
    assert 'id="speed-controls"' in html
    assert 'aria-label="시간 조작"' in html
    assert 'id="date-display"' in html
    assert 'id="speed-badge"' in html


def test_speed_presets_cover_realtime_to_year() -> None:
    data = read("data.js")

    for preset_id in ("realtime", "hour", "day", "week", "month", "year"):
        assert f'id: "{preset_id}"' in data
    assert "1 / 86400" in data
    assert "365.256" in data
    assert 'export const DEFAULT_SPEED_ID = "day";' in data


def test_default_speed_is_one_day_per_second() -> None:
    state = read("state.js")

    assert "export function createAppState" in state
    assert "daysPerSecond: preset.daysPerSecond" in state
    assert "export function setSpeed" in state
    assert "export function togglePaused" in state
    assert "export function resetToToday" in state
    assert "export function advanceSimulation" in state


def test_pause_stops_the_simulation_clock() -> None:
    state_source = read("state.js")

    assert (
        "if (state.paused || !Number.isFinite(state.daysPerSecond)) return state.days;"
        in state_source
    )
    assert "Math.min(MAX_FRAME_STEP_SECONDS, Math.max(0, dtSeconds))" in state_source


def test_controls_wire_every_time_button() -> None:
    controls = read("controls.js")

    assert 'elements.pauseBtn.addEventListener("click"' in controls
    assert 'elements.todayBtn.addEventListener("click"' in controls
    assert 'elements.prevDayBtn.addEventListener("click"' in controls
    assert 'elements.nextDayBtn.addEventListener("click"' in controls
    assert 'elements.speedControls.addEventListener("click"' in controls
    assert "button.dataset.speed" in controls
