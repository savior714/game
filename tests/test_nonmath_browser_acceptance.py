"""
Focused browser acceptance test for non-math subjects (korean, english, science).

Verifies that:
- Each subject page loads via HTTP without page errors
- First question text is visible and non-blank
- At least 2 answer buttons are visible and clickable
- Clicking an answer shows feedback (correct/wrong)
- Next button appears after answering

Math is tested as a control (not modified in this task).
"""

import os
import http.server
import socketserver
import threading
import time
import pytest
from pathlib import Path
from playwright.sync_api import sync_playwright

# Test configuration
REPO_ROOT = Path(__file__).parent.parent
PORT = 18765
SUBJECTS = ["korean", "english", "science"]
CONTROL_SUBJECT = "math"


class HTTPServerFixture:
    """Static HTTP server for repo root."""
    
    def __init__(self):
        self.server = None
        self.thread = None
        self.base_url = None
    
    def start(self):
        os.chdir(REPO_ROOT)
        
        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(REPO_ROOT), **kwargs)
            
            def log_message(self, format, *args):
                pass  # Suppress request logs
        
        socketserver.TCPServer.allow_reuse_address = True
        self.server = socketserver.TCPServer(("127.0.0.1", PORT), QuietHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.5)
        self.base_url = f"http://127.0.0.1:{PORT}"
        return self.base_url
    
    def stop(self):
        if self.server:
            self.server.shutdown()


@pytest.fixture(scope="session")
def server():
    """Start HTTP server for the test session."""
    srv = HTTPServerFixture()
    url = srv.start()
    yield url
    srv.stop()


@pytest.fixture
def browser():
    """Create a fresh browser instance."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    """Create a fresh page with fresh storage."""
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="ko-KR",
        timezone_id="Asia/Seoul",
    )
    pg = context.new_page()
    yield pg
    context.close()


def clear_storage(pg):
    """Clear localStorage and sessionStorage after navigation."""
    try:
        pg.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    except Exception:
        pass  # Ignore if page is not loaded yet


@pytest.mark.browser
class TestNonMathBrowserAcceptance:
    """Acceptance tests for non-math subjects."""
    
    @pytest.mark.parametrize("subject", SUBJECTS)
    def test_subject_loads_without_page_errors(self, server, page, subject):
        """Subject page loads without JavaScript errors."""
        url = f"{server}/domains/{subject}/index.html"
        
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        
        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        
        # Clear storage after navigation
        clear_storage(page)
        
        # Wait for question to appear
        page.wait_for_selector("#question", state="visible", timeout=5000)
        
        assert len(page_errors) == 0, f"Page errors detected for {subject}: {page_errors}"
    
    @pytest.mark.parametrize("subject", SUBJECTS)
    def test_question_visible_and_nonblank(self, server, page, subject):
        """First question text is visible and contains text."""
        url = f"{server}/domains/{subject}/index.html"
        
        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        clear_storage(page)
        
        # Wait for question to appear
        question_el = page.wait_for_selector("#question", state="visible", timeout=5000)
        
        assert question_el is not None, f"Question element not found for {subject}"
        
        text = question_el.inner_text().strip()
        assert len(text) > 0, f"Question text is blank for {subject}"
    
    @pytest.mark.parametrize("subject", SUBJECTS)
    def test_answer_buttons_visible(self, server, page, subject):
        """At least 2 answer buttons are visible."""
        url = f"{server}/domains/{subject}/index.html"
        
        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        clear_storage(page)
        
        # Wait for answer buttons to appear
        page.wait_for_selector("#answer-buttons", state="visible", timeout=5000)
        
        buttons = page.query_selector_all(".answer-btn")
        assert len(buttons) >= 2, f"Expected at least 2 answer buttons for {subject}, got {len(buttons)}"
    
    @pytest.mark.parametrize("subject", SUBJECTS)
    def test_answer_interaction_shows_feedback(self, server, page, subject):
        """Clicking an answer shows feedback and next button."""
        url = f"{server}/domains/{subject}/index.html"
        
        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        clear_storage(page)
        
        # Wait for question and answers
        page.wait_for_selector("#question", state="visible", timeout=5000)
        page.wait_for_selector(".answer-btn", state="visible", timeout=5000)
        
        # Click first answer button
        first_button = page.query_selector(".answer-btn")
        assert first_button is not None, f"No answer button found for {subject}"
        
        first_button.click()
        
        # Wait for feedback to appear
        page.wait_for_selector("#feedback", state="visible", timeout=3000)
        
        feedback = page.query_selector("#feedback")
        assert feedback is not None, f"Feedback element not found for {subject}"
        
        feedback_text = feedback.inner_text().strip()
        assert len(feedback_text) > 0, f"Feedback text is blank for {subject}"
        
        # Wait for next button to appear
        page.wait_for_selector("#next-btn", state="visible", timeout=3000)
        
        next_btn = page.query_selector("#next-btn")
        assert next_btn is not None, f"Next button not found for {subject}"
    
    @pytest.mark.parametrize("subject", SUBJECTS)
    def test_no_page_errors(self, server, page, subject):
        """No JavaScript page errors during load."""
        url = f"{server}/domains/{subject}/index.html"
        
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        
        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        clear_storage(page)
        page.wait_for_selector("#question", state="visible", timeout=5000)
        
        assert len(page_errors) == 0, (
            f"Page errors detected for {subject}: {page_errors}"
        )


@pytest.mark.browser
class TestMathBrowserControl:
    """Control test for math subject (not modified in this task)."""
    
    def test_math_loads_without_page_errors(self, server, page):
        """Math page loads without JavaScript errors."""
        url = f"{server}/domains/{CONTROL_SUBJECT}/index.html"
        
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        
        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        clear_storage(page)
        page.wait_for_selector("#question", state="visible", timeout=5000)
        
        assert len(page_errors) == 0, f"Page errors detected for {CONTROL_SUBJECT}: {page_errors}"
    
    def test_math_question_visible(self, server, page):
        """Math question is visible and non-blank."""
        url = f"{server}/domains/{CONTROL_SUBJECT}/index.html"
        
        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        clear_storage(page)
        
        question_el = page.wait_for_selector("#question", state="visible", timeout=5000)
        text = question_el.inner_text().strip()
        assert len(text) > 0, "Math question text is blank"
    
    def test_math_answer_interaction(self, server, page):
        """Math answer interaction works."""
        url = f"{server}/domains/{CONTROL_SUBJECT}/index.html"
        
        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        clear_storage(page)
        page.wait_for_selector(".answer-btn", state="visible", timeout=5000)
        
        first_button = page.query_selector(".answer-btn")
        first_button.click()
        
        page.wait_for_selector("#feedback", state="visible", timeout=3000)
        page.wait_for_selector("#next-btn", state="visible", timeout=3000)
