"""Per-entry study quota, actual quiz answers and absolute five-minute deadline."""

from __future__ import annotations

import functools
import http.server
import os
import threading
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
KEY = "aiden_study_game_admission_v1"
GAMES = {
    "electricity": "experiments/electricity/index.html",
    "dino": "experiments/space-explorer/dino-escape.html",
    "marble": "experiments/marble/index.html",
    "bubble": "experiments/bubble/index.html",
}
SUBJECTS = {
    "math": "🔢 수학",
    "english": "🔤 영어",
    "korean": "📚 국어",
    "science": "🔬 과학",
}


@pytest.fixture(scope="module")
def server():
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(ROOT)
    )
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()
    srv.server_close()
    thread.join()


@pytest.fixture
def page(server):
    with sync_playwright() as p:
        options = {
            "headless": True,
            "args": ["--no-sandbox", "--disable-dev-shm-usage"],
        }
        if os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE"):
            options["executable_path"] = os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE"]
        browser = p.chromium.launch(**options)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        # Fonts/analytics aren't part of this local interaction proof.
        page.route(
            "**/*",
            lambda route: (
                route.continue_()
                if route.request.url.startswith(server)
                else route.abort()
            ),
        )
        yield page
        browser.close()


def state(page):
    return page.evaluate("key => JSON.parse(sessionStorage.getItem(key))", KEY)


def answer_question(page, subject, correct=True):
    page.wait_for_selector("#question")
    if subject == "english" and page.evaluate("uiQuestionKind === 'typing'"):
        page.locator("#typing-input").fill(
            page.evaluate("String(answer)") if correct else "wrong-answer"
        )
        page.locator("#typing-submit").click()
        return
    for _ in range(10):
        page.wait_for_selector(".answer-btn")
        step = page.evaluate("seqStep") if subject == "english" else None
        wanted = page.evaluate(
            "seqBlanks ? seqBlanks.blanks[seqStep].char : String(answer)"
            if subject == "english"
            else "String(answer)"
        )
        buttons = page.locator(".answer-btn")
        texts = buttons.all_text_contents()
        index = next(i for i, text in enumerate(texts) if (text == wanted) == correct)
        buttons.nth(index).click()
        if subject != "english" or not correct or page.evaluate("answered"):
            return
        page.wait_for_function("step => answered || seqStep !== step", arg=step)
        if page.evaluate("answered"):
            return
    raise AssertionError("Sequential question did not finish")


@pytest.mark.parametrize("game,subject", list(zip(GAMES, SUBJECTS)))
def test_fresh_quota_real_answers_reload_and_five_minute_exit(
    page, server, game, subject
):
    page.goto(f"{server}/index.html", wait_until="domcontentloaded")
    if game in ("marble", "bubble"):
        page.locator(f"#reward-inventory [data-type='{game}']").click()
    else:
        page.locator(f"a[href='./{GAMES[game]}']").click()
    choice = page.get_by_role("dialog")
    expect(choice.get_by_role("heading")).to_have_text("어떤 과목을 풀고 싶어?")
    for label in SUBJECTS.values():
        expect(choice.get_by_role("button", name=label, exact=True)).to_be_visible()
    choice.get_by_role("button", name=SUBJECTS[subject], exact=True).click()
    page.wait_for_url(f"**/domains/{subject}/index.html")
    expect(page.locator(".study-game-progress")).to_contain_text("정답 0 / 5")
    answer_question(page, subject, correct=False)
    assert state(page)["correct"] == 0
    page.locator("#next-btn").click()
    for i in range(5):
        answer_question(page, subject)
        assert state(page)["correct"] == i + 1
        # Re-clicking the already answered choice cannot count twice.
        page.evaluate("document.querySelector('.answer-btn.correct').click()")
        assert state(page)["correct"] == i + 1
        if i == 1:
            page.reload(wait_until="domcontentloaded")
            expect(page.locator(".study-game-progress")).to_contain_text("정답 2 / 5")
        elif i < 4:
            page.locator("#next-btn").click()
        if i < 4:
            expect(page.get_by_role("button", name="🎉 게임 입장하기")).to_have_count(0)
    page.get_by_role("button", name="🎉 게임 입장하기").click()
    page.wait_for_url(f"**/{GAMES[game]}")
    expect(page.locator(".study-game-clock")).to_be_visible()
    original = state(page)
    assert original["deadline"] - original["startedAt"] == 300000
    assert page.evaluate("StudyGameAdmission.isPlaying(%r)" % game)
    if game == "marble":
        expect(page.locator("iframe[title='마블 머지 게임']")).to_be_visible()
    if game == "dino":
        expect(page.locator("#game-shell")).to_be_visible()
    page.reload(wait_until="domcontentloaded")
    assert state(page)["deadline"] == original["deadline"]
    expect(page.locator(".study-game-clock")).to_be_visible()
    # Simulate a suspended/background tab returning after its absolute deadline.
    page.evaluate(
        """deadline => {
        Date.now = () => deadline;
        document.dispatchEvent(new Event('visibilitychange'));
    }""",
        original["deadline"],
    )
    page.wait_for_url(f"{server}/index.html")
    assert state(page) is None
    page.goto(f"{server}/{GAMES[game]}", wait_until="domcontentloaded")
    expect(page.get_by_role("dialog")).to_be_visible()
    assert not page.evaluate("StudyGameAdmission.isPlaying(%r)" % game)


@pytest.mark.parametrize("game", GAMES)
def test_direct_address_and_old_math_goal_never_skip_study(page, server, game):
    page.goto(f"{server}/index.html", wait_until="domcontentloaded")
    page.evaluate("""() => {
        const d = new Date();
        const date = [d.getFullYear(), String(d.getMonth()+1).padStart(2,'0'), String(d.getDate()).padStart(2,'0')].join('-');
        localStorage.setItem('aiden_math_daily_goal_v1', JSON.stringify({schemaVersion:1,date,completed:true}));
        sessionStorage.setItem('aiden_study_game_admission_v1', '{');
    }""")
    page.goto(f"{server}/{GAMES[game]}", wait_until="domcontentloaded")
    expect(page.get_by_role("dialog")).to_be_visible()
    assert page.locator("html").get_attribute("data-study-game-locked") == "true"
    page.get_by_role("button", name="홈으로 돌아가기", exact=True).click()
    page.wait_for_url(f"{server}/index.html")
    assert state(page) is None


def test_other_subject_and_non_learning_rewards_do_not_count(page, server):
    page.goto(f"{server}/index.html", wait_until="domcontentloaded")
    page.locator("#reward-inventory [data-type='bubble']").click()
    page.get_by_role("button", name=SUBJECTS["math"], exact=True).click()
    page.wait_for_url("**/domains/math/index.html")
    page.evaluate("RewardSystem.add('gems', 10)")
    assert state(page)["correct"] == 0
    page.goto(f"{server}/domains/science/index.html", wait_until="domcontentloaded")
    answer_question(page, "science")
    assert state(page)["correct"] == 0


@pytest.mark.signed_out
def test_login_gate_remains_visible_before_subject_choice(page, server):
    page.goto(f"{server}/{GAMES['bubble']}", wait_until="domcontentloaded")
    expect(page.locator("#aiden-auth-gate")).to_be_visible()
    expect(page.locator(".study-game-choice")).to_have_count(0)


@pytest.mark.parametrize(
    "bad",
    [
        None,
        {"correct": "5"},
        {"correct": -1},
        {"correct": 6},
        {"phase": "playing", "correct": 4},
    ],
)
def test_invalid_session_cannot_grant_admission(page, server, bad):
    page.goto(f"{server}/index.html", wait_until="domcontentloaded")
    page.evaluate(
        """bad => sessionStorage.setItem('aiden_study_game_admission_v1', JSON.stringify(bad === null ? null : {
        version:1,game:'bubble',subject:'math',phase:'learning',correct:0,...bad
    }))""",
        bad,
    )
    page.goto(f"{server}/{GAMES['bubble']}", wait_until="domcontentloaded")
    expect(page.locator(".study-game-choice")).to_be_visible()
    assert not page.evaluate("StudyGameAdmission.isPlaying('bubble')")


def test_shop_game_action_does_not_spend_gems_or_legacy_tickets(page, server):
    page.goto(f"{server}/index.html", wait_until="domcontentloaded")
    page.wait_for_function("typeof RewardSystem !== 'undefined'")
    before = page.evaluate("RewardSystem.getState()")
    page.evaluate("RewardSystem.exchangeGem('marble')")
    expect(page.locator(".study-game-choice")).to_be_visible()
    after = page.evaluate("RewardSystem.getState()")
    for key in ["gems", "marble_plays", "bubble_plays"]:
        assert after[key] == before[key]
    page.get_by_role("button", name="취소", exact=True).click()
    assert state(page) is None


def test_blocked_storage_keeps_entry_locked(page, server):
    page.goto(f"{server}/{GAMES['bubble']}", wait_until="domcontentloaded")
    expect(page.locator(".study-game-choice")).to_be_visible()
    page.evaluate(
        "() => { Storage.prototype.setItem = () => { throw new Error('blocked'); }; }"
    )
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name=SUBJECTS["math"], exact=True).click()
    assert page.url.endswith(GAMES["bubble"])
    assert not page.evaluate("StudyGameAdmission.isPlaying('bubble')")


@pytest.mark.parametrize("width,height", [(1280, 800), (800, 1280), (390, 844)])
def test_subject_choice_fits_tablet_and_phone_keyboard_navigation(
    page, server, width, height
):
    page.set_viewport_size({"width": width, "height": height})
    page.goto(f"{server}/{GAMES['bubble']}", wait_until="domcontentloaded")
    choice = page.locator(".study-game-choice")
    expect(choice).to_be_visible()
    box = choice.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= width
    assert box["y"] >= 0 and box["y"] + box["height"] <= height
    page.get_by_role("button", name=SUBJECTS["math"], exact=True).focus()
    page.keyboard.press("Enter")
    page.wait_for_url("**/domains/math/index.html")
    expect(page.locator(".study-game-progress")).to_contain_text("정답 0 / 5")


def test_countdown_itself_exits_at_five_minutes(page, server):
    page.clock.install()
    page.add_init_script("""if (location.pathname.includes('/experiments/bubble/')) {
        const now = Date.now();
        sessionStorage.setItem('aiden_study_game_admission_v1', JSON.stringify({
            version:1,game:'bubble',subject:'math',phase:'playing',correct:5,
            startedAt:now,deadline:now+300000
        }));
    }""")
    page.goto(f"{server}/{GAMES['bubble']}", wait_until="domcontentloaded")
    expect(page.locator(".study-game-clock")).to_be_visible()
    page.clock.fast_forward(299000)
    assert page.url.endswith(GAMES["bubble"])
    page.clock.fast_forward(1000)
    page.wait_for_url(f"{server}/index.html")
    assert state(page) is None


def test_learning_directory_alias_preserves_progress(page, server):
    page.goto(f"{server}/{GAMES['bubble']}", wait_until="domcontentloaded")
    page.get_by_role("button", name=SUBJECTS["math"], exact=True).click()
    page.wait_for_url("**/domains/math/index.html")
    page.goto(f"{server}/domains/math/", wait_until="domcontentloaded")
    expect(page.locator(".study-game-progress")).to_contain_text("정답 0 / 5")
    answer_question(page, "math")
    assert state(page)["correct"] == 1
