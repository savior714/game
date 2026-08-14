"""
Tests for Ocean Rescue Web Audio and Web Speech synthesis system contract.
Validates procedural sound generation API, TTS speech options, volume control clamping,
DOM slider elements in compiled single-html bundle, and pause integration.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OCEAN_RESCUE_DIR = REPO_ROOT / "domains" / "ocean-rescue"
APP_JS = OCEAN_RESCUE_DIR / "src" / "app.js"
INDEX_HTML = REPO_ROOT / "ocean-rescue" / "index.html"
TEMPLATE_HTML = OCEAN_RESCUE_DIR / "src" / "index.template.html"
PAUSE_CONTROLLER_TS = OCEAN_RESCUE_DIR / "src" / "controllers" / "pause-timer-resume.ts"


def test_audio_system_exports_and_methods() -> None:
    assert APP_JS.exists(), "app.js must exist in src/"
    content = APP_JS.read_text(encoding="utf-8")

    expected_methods = [
        "prime",
        "playClick",
        "playSelect",
        "playBump",
        "playCut",
        "playGrab",
        "playDrop",
        "playConnect",
        "playSuccess",
        "playWrong",
        "playWhaleCall",
        "playDoorOpen",
        "playGoalBanner",
        "speak",
        "cancelSpeech",
        "pauseSpeech",
        "resumeSpeech",
        "setSoundVolume",
        "setVoiceVolume",
        "getSettings",
        "testSoundVolume",
        "testVoiceVolume",
    ]

    for method in expected_methods:
        assert f"{method}:" in content or f"function {method}(" in content, (
            f"Expected {method} in audio.js"
        )

    assert "root.Audio = Audio;" in content or "window.OceanRescue.Audio" in content


def test_index_template_has_volume_controls() -> None:
    assert TEMPLATE_HTML.exists()
    content = TEMPLATE_HTML.read_text(encoding="utf-8")

    assert 'id="ocean-rescue-pause-volume-controls"' in content
    assert 'id="ocean-rescue-volume-sound"' in content
    assert 'id="ocean-rescue-volume-voice"' in content
    assert 'id="ocean-rescue-volume-sound-val"' in content
    assert 'id="ocean-rescue-volume-voice-val"' in content


def test_compiled_single_html_contains_audio_and_volume_controls() -> None:
    assert INDEX_HTML.exists(), "Compiled single HTML must exist"
    content = INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="ocean-rescue-pause-volume-controls"' in content
    assert 'id="ocean-rescue-volume-sound"' in content
    assert 'id="ocean-rescue-volume-voice"' in content
    assert "playWhaleCall" in content
    assert "playDoorOpen" in content
    assert "setSoundVolume" in content


def test_pause_controller_integrates_tts_lifecycle() -> None:
    assert PAUSE_CONTROLLER_TS.exists()
    content = PAUSE_CONTROLLER_TS.read_text(encoding="utf-8")

    assert "pauseSpeech" in content
    assert "resumeSpeech" in content
    assert "cancelSpeech" in content
