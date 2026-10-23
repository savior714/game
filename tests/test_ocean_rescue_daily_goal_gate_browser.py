from __future__ import annotations

import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ADMISSION_KEY = "aiden_study_game_admission_v1"


@pytest.fixture(scope="module")
def static_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(0.5)
    yield f"http://127.0.0.1:{port}"
    proc.terminate()
    proc.wait()


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


@pytest.mark.browser
@pytest.mark.unentitled_study_game
def test_ocean_rescue_hub_and_direct_entry_require_five_answers_even_after_math_daily_goal(
    static_server: str,
) -> None:
    """Ocean Rescue uses the per-entry 5-answer/5-minute admission gate on hub and direct URL."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto(f"{static_server}/index.html", wait_until="domcontentloaded")
        today = _today_str()
        page.evaluate(
            f"""() => {{
                localStorage.setItem('aiden_math_daily_goal_v1', JSON.stringify({{
                    date: '{today}',
                    targetCount: 20,
                    solvedCount: 20,
                    completed: true,
                    rewardGranted: true
                }}));
            }}"""
        )
        page.reload(wait_until="domcontentloaded")

        # Clicking Ocean Rescue on the hub opens the subject-choice modal rather than skipping study.
        page.locator("#ocean-rescue-card").click()
        dialog = page.get_by_role("dialog")
        expect(dialog).to_be_visible()
        expect(dialog).to_contain_text("🌊 바다 구조대")
        dialog.get_by_role("button", name="취소", exact=True).click()
        expect(dialog).not_to_be_visible()

        # Direct URL navigation is also fail-closed without an active 5-minute playing session.
        page.goto(
            f"{static_server}/ocean-rescue/index.html", wait_until="domcontentloaded"
        )
        expect(page.get_by_role("dialog")).to_be_visible()
        assert page.locator("html").get_attribute("data-study-game-locked") == "true"
        assert not page.evaluate("StudyGameAdmission.isPlaying('ocean-rescue')")

        # Active 5-minute playing session unlocks Ocean Rescue and renders the countdown clock.
        page.evaluate(
            f"""() => {{
                const startedAt = Date.now();
                sessionStorage.setItem('{ADMISSION_KEY}', JSON.stringify({{
                    version: 1,
                    phase: 'playing',
                    game: 'ocean-rescue',
                    subject: 'math',
                    correct: 5,
                    startedAt,
                    deadline: startedAt + 300000
                }}));
            }}"""
        )
        page.reload(wait_until="domcontentloaded")
        expect(page.locator(".study-game-clock")).to_be_visible()
        expect(page.locator(".study-game-clock")).to_contain_text("남음")
        assert page.locator("html").get_attribute("data-study-game-locked") is None
        assert page.evaluate("StudyGameAdmission.isPlaying('ocean-rescue')")
        page.wait_for_selector(
            "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=15000
        )

        context.close()
        browser.close()


def test_ocean_rescue_runtime_has_no_injected_quiz_logic() -> None:
    """Verify Ocean Rescue gameplay stays pure arcade rescue play without in-game quiz insertion."""
    source = (ROOT / "domains/ocean-rescue/src/app.js").read_text(encoding="utf-8")
    quiz_keywords = ["answerProblem", "checkMathAnswer", "quizModal", "problem_prompt"]
    for kw in quiz_keywords:
        assert kw not in source, f"Found unexpected quiz keyword {kw} in Ocean Rescue"
