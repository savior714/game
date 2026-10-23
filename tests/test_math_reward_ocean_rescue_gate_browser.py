from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


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


def _answer_current_math_question_correctly(page) -> None:
    correct_idx = page.evaluate(
        """() => {
            const buttons = [...document.querySelectorAll('#answers-grid .answer-btn')];
            const prompt = document.getElementById('question-text')?.textContent || '';
            const match = prompt.match(/(-?\\d+)\\s*([+\\-×÷])\\s*(-?\\d+)/);
            if (!match) return 0;
            const a = Number(match[1]);
            const op = match[2];
            const b = Number(match[3]);
            const ans = op === '+' ? a + b : op === '-' ? a - b : op === '×' ? a * b : a / b;
            const found = buttons.findIndex(btn => Number(btn.textContent.trim()) === ans);
            return found >= 0 ? found : 0;
        }"""
    )
    page.locator("#answers-grid .answer-btn").nth(correct_idx).click()


@pytest.mark.browser
@pytest.mark.unentitled_study_game
def test_e2e_hub_subject_five_answers_to_five_minute_ocean_rescue(
    static_server: str,
) -> None:
    """End-to-end journey: Hub Ocean Rescue card -> choose Math -> 5 correct answers -> 5-minute Ocean Rescue play."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto(f"{static_server}/index.html", wait_until="domcontentloaded")
        page.locator("#ocean-rescue-card").click()

        choice = page.get_by_role("dialog")
        expect(choice).to_be_visible()
        expect(choice).to_contain_text("🌊 바다 구조대")
        choice.get_by_role("button", name="🔢 수학", exact=True).click()

        page.wait_for_url(f"{static_server}/domains/math/index.html")
        expect(page.locator(".study-game-progress")).to_contain_text("정답 0 / 5")

        page.locator("button[data-op='add']").click()
        page.wait_for_selector("#quiz-screen:not(.hidden)")

        for step in range(5):
            _answer_current_math_question_correctly(page)
            expect(page.locator(".study-game-progress")).to_contain_text(
                f"정답 {step + 1} / 5"
            )
            if step < 4:
                page.locator("#next-btn").click()

        page.get_by_role("button", name="🎉 게임 입장하기", exact=True).click()
        page.wait_for_url(f"{static_server}/ocean-rescue/index.html")

        expect(page.locator(".study-game-clock")).to_be_visible()
        expect(page.locator(".study-game-clock")).to_contain_text(
            "남음 · 5분 뒤 홈으로 돌아가요"
        )
        assert page.evaluate("StudyGameAdmission.isPlaying('ocean-rescue')")
        page.wait_for_selector(
            "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=15000
        )

        context.close()
        browser.close()
