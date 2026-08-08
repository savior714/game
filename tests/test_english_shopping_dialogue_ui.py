"""Focused regression test for English shopping_dialogue question rendering without undefined text."""

from __future__ import annotations

import http.server
import socketserver
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Page, sync_playwright


REPO_ROOT = Path(__file__).resolve().parent.parent
ENGLISH_URL = "/domains/english/index.html"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def log_message(self, format, *args):  # noqa: A002
        pass


@pytest.fixture(scope="module")
def static_server():
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("127.0.0.1", 0), QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.server_address
    yield f"http://{host}:{port}"

    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )
        browser_page = context.new_page()
        yield browser_page
        context.close()
        browser.close()


def test_english_shopping_dialogue_renders_properly(
    static_server: str, page: Page
) -> None:
    """shopping_dialogue 문제 유형이 UI에 렌더링될 때 undefined 문구가 포함되지 않음을 검증."""
    page.goto(f"{static_server}{ENGLISH_URL}", wait_until="networkidle")

    result = page.evaluate("""
        () => {
            const word = ['shirt', '셔츠', '👕', 1];
            const q = buildQuestion('shopping_dialogue', word, { cat: 'clothing' });
            
            // generateQuestion 대신 강제로 shopping_dialogue 문제 전달
            window.generateQuestion = () => q;
            askQuestion();

            const questionEl = document.getElementById('question');
            const innerText = questionEl ? questionEl.innerText : '';
            const innerHTML = questionEl ? questionEl.innerHTML : '';
            
            return {
                type: q.type,
                innerText,
                innerHTML,
                containsUndefined: innerText.includes('undefined') || innerHTML.includes('undefined'),
                hasSentence: innerHTML.includes('q-sentence'),
                hasChoices: document.querySelectorAll('.answer-btn').length > 0
            };
        }
    """)

    assert result["type"] == "shopping_dialogue"
    assert not result["containsUndefined"], (
        f"shopping_dialogue 렌더링 결과에 'undefined'가 포함됨: {result['innerHTML']}"
    )
    assert result["hasSentence"], (
        "shopping_dialogue 문제에 q-sentence 요소를 통한 문장 렌더링이 없음"
    )
    assert result["hasChoices"], "shopping_dialogue 보기가 생성되지 않음"


def test_english_multiple_questions_no_undefined(
    static_server: str, page: Page
) -> None:
    """100개의 다양한 문제를 연속 생성하여 askQuestion() 렌더링 시 'undefined' 텍스트가 절대 발생하지 않는지 검증."""
    page.goto(f"{static_server}{ENGLISH_URL}", wait_until="networkidle")

    undefined_occurrences = page.evaluate("""
        () => {
            const occurrences = [];
            for (let i = 0; i < 100; i++) {
                askQuestion();
                const questionEl = document.getElementById('question');
                const text = questionEl ? questionEl.innerText : '';
                const html = questionEl ? questionEl.innerHTML : '';
                if (text.includes('undefined') || html.includes('undefined')) {
                    occurrences.push({ index: i, text, html });
                }
            }
            return occurrences;
        }
    """)

    assert len(undefined_occurrences) == 0, (
        f"문제 렌더링 도중 'undefined' 발견: {undefined_occurrences}"
    )
