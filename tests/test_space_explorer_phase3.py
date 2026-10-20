"""태양계 3D 탐험대 — 컨트롤/정보 패널 마크업 계약."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPACE_DIR = ROOT / "experiments" / "space-explorer"


def read(name: str) -> str:
    return (SPACE_DIR / name).read_text(encoding="utf-8")


def test_stable_control_selectors_exist() -> None:
    html = read("index.html")

    for control_id in (
        "space-canvas",
        "date-display",
        "speed-badge",
        "orbits-btn",
        "labels-btn",
        "effects-btn",
        "help-btn",
        "overview-btn",
        "planet-ribbon",
        "detail-card",
        "detail-close",
        "help-modal",
        "help-close",
    ):
        assert f'id="{control_id}"' in html, control_id


def test_detail_panel_fields_exist() -> None:
    html = read("index.html")

    for detail_id in (
        "detail-preview",
        "detail-preview-image",
        "detail-name",
        "detail-en",
        "detail-category",
        "detail-highlight",
        "detail-overview",
        "detail-stats",
        "detail-facts",
    ):
        assert f'id="{detail_id}"' in html, detail_id


def test_controls_helpers_exist_in_script() -> None:
    controls = read("controls.js")

    assert "export function createUiController({ state, actions })" in controls
    assert "function buildRibbon()" in controls
    assert "function buildSpeedControls()" in controls
    assert "function buildLabels()" in controls
    assert "function showDetail(body)" in controls
    assert "function updateLabels(scene)" in controls
    assert "function setLoadingProgress(loaded, total, name)" in controls
    assert "function showFatalError(message)" in controls
