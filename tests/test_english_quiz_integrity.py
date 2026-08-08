"""Automated regression test verifying English quiz answer integrity, hint alignment, and sentence completeness."""

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


def test_snowmobile_shopping_dialogue_fallback_integrity(
    static_server: str, page: Page
) -> None:
    """snowmobile 단어가 shopping_dialogue로 지정되어도 정답/힌트 불일치 없이 sentence로 안전 폴백되는지 검증."""
    page.goto(f"{static_server}{ENGLISH_URL}", wait_until="networkidle")

    res = page.evaluate("""
        () => {
            const word = ['snowmobile', '스노모빌', '❄️', 6];
            const q = buildQuestion('shopping_dialogue', word, { cat: 'transport' });
            return {
                type: q.type,
                answer: q.answer,
                word: q.word,
                koHint: q.koHint,
                choices: q.choices,
                containsSnowmobileInChoices: q.choices.includes('snowmobile')
            };
        }
    """)

    assert res["type"] == "sentence", (
        f"snowmobile은 shopping_dialogue 대화문 대상이 아니므로 sentence로 폴백되어야 함: {res['type']}"
    )
    assert res["answer"] == "snowmobile", f"정답이 snowmobile이어야 함: {res['answer']}"
    assert res["containsSnowmobileInChoices"], (
        f"보기에 snowmobile이 포함되어야 함: {res['choices']}"
    )


def test_matching_word_shopping_dialogue_integrity(
    static_server: str, page: Page
) -> None:
    """shirt 단어가 shopping_dialogue로 출제될 때 정답과 힌트가 정확히 일치하는지 검증."""
    page.goto(f"{static_server}{ENGLISH_URL}", wait_until="networkidle")

    res = page.evaluate("""
        () => {
            const word = ['shirt', '셔츠', '👕', 1];
            const q = buildQuestion('shopping_dialogue', word, { cat: 'clothing' });
            return {
                type: q.type,
                answer: q.answer,
                word: q.word,
                koHint: q.koHint,
                choices: q.choices,
                containsShirtInChoices: q.choices.includes('shirt')
            };
        }
    """)

    assert res["type"] == "shopping_dialogue", (
        f"shirt 단어는 shopping_dialogue로 정상 출제되어야 함: {res['type']}"
    )
    assert res["answer"] == "shirt", f"정답이 shirt이어야 함: {res['answer']}"
    assert res["koHint"] == "셔츠", f"힌트가 셔츠이어야 함: {res['koHint']}"
    assert res["containsShirtInChoices"], (
        f"보기에 shirt가 포함되어야 함: {res['choices']}"
    )


def test_multiple_questions_integrity_and_grammar(
    static_server: str, page: Page
) -> None:
    """200회 연속 문제 출제 시 정답-힌트-보기 무결성 및 비문/undefined 부재 검증."""
    page.goto(f"{static_server}{ENGLISH_URL}", wait_until="networkidle")

    failures = page.evaluate("""
        () => {
            const issues = [];
            for (let i = 0; i < 200; i++) {
                askQuestion();
                const qEl = document.getElementById('question');
                const text = qEl ? qEl.innerText : '';
                const html = qEl ? qEl.innerHTML : '';
                const answerBtns = Array.from(document.querySelectorAll('.answer-btn')).map(b => b.textContent);

                const isSeqSpelling = !!document.getElementById('seq-word');

                if (text.includes('undefined') || html.includes('undefined')) {
                    issues.push({ index: i, error: 'undefined_found', text, html });
                }

                if (text.includes('These hat are')) {
                    issues.push({ index: i, error: 'ungrammatical_these_hat', text });
                }

                // 일반 객관식 문제의 경우 정답이 보기에 반드시 포함되어야 함 (순차 빈칸 spelling 유형 제외)
                if (answerBtns.length > 0 && !isSeqSpelling && !answerBtns.includes(answer)) {
                    issues.push({ index: i, error: 'answer_missing_in_choices', answer, choices: answerBtns });
                }
            }
            return issues;
        }
    """)

    assert len(failures) == 0, f"문제 무결성 검증 실패 발생: {failures}"
