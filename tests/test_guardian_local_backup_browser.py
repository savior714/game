"""Browser E2E verification for Guardian Local Backup and Restore v1."""

from __future__ import annotations

import http.server
import json
import tempfile
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Serve the repository root without request-log noise."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def log_message(self, format, *args):  # noqa: A002
        pass


@pytest.fixture(scope="module")
def static_server():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.server_address
    yield f"http://{host}:{port}"

    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


@pytest.fixture
def tablet_guardian_page(static_server: str):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        # Galaxy Tab S10 landscape viewport baseline
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            accept_downloads=True,
        )
        page = context.new_page()
        page_errors: list[str] = []
        console_errors: list[str] = []

        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "console",
            lambda msg: (
                console_errors.append(msg.text) if msg.type == "error" else None
            ),
        )

        page.goto(f"{static_server}/domains/reward/guardian/index.html")
        page.wait_for_selector("#local-backup-section", state="visible", timeout=5000)

        yield page, page_errors, console_errors, static_server

        context.close()
        browser.close()


@pytest.mark.browser
def test_guardian_export_backup_flow(
    tablet_guardian_page: tuple[Page, list[str], list[str], str],
) -> None:
    page, page_errors, console_errors, _ = tablet_guardian_page

    # Seed canonical test state
    page.evaluate(
        """() => {
        const now = Date.now();
        localStorage.clear();

        // 1. Math evidence
        const evidenceData = {
          schemaVersion: 1,
          lastUpdated: new Date(now).toISOString(),
          items: [
            { id: 'ev-test-1', timestamp: now - 2000, skillId: 'math.add.within_10', op: '+', a: 3, b: 2, result: 5, correct: true, attempts: 1 },
            { id: 'ev-test-2', timestamp: now - 1000, skillId: 'math.add.within_10', op: '+', a: 4, b: 1, result: 5, correct: true, attempts: 1 },
          ]
        };
        localStorage.setItem('aiden_math_learning_evidence_v1', JSON.stringify(evidenceData));

        // 2. Math daily goal
        const today = new Date(now).toISOString().split('T')[0];
        const goalData = {
          schemaVersion: 1,
          date: today,
          goalId: `goal-${today}-math.add.within_10-v1`,
          skillId: 'math.add.within_10',
          skillName: '10 이하의 덧셈',
          shortName: '10 이하 덧셈',
          targetCount: 5,
          currentCount: 2,
          completed: false,
          rewardGranted: false,
          rewardReceiptId: `receipt-math-goal-${today}-math.add.within_10-v1`,
          lastUpdated: new Date(now).toISOString()
        };
        localStorage.setItem('aiden_math_daily_goal_v1', JSON.stringify(goalData));

        // 3. Rewards & receipt
        const rewardData = {
          gems: 15,
          youtube_minutes: 20,
          snacks: 3,
          marble_plays: 1,
          bubble_plays: 0,
          shop_items: [
            { id: 'youtube', icon: '📺', label: '유튜브 10분', price: 1 },
            { id: 'snack', icon: '🍪', label: '간식 1개', price: 1 }
          ],
          custom_inventory: { 'custom_badge': 1 },
          claimed_receipts: {
            'prev-receipt-01': { receiptId: 'prev-receipt-01', grantedAt: now }
          }
        };
        localStorage.setItem('study_rewards', JSON.stringify(rewardData));
        localStorage.setItem('aiden_receipt_prev-receipt-01', JSON.stringify({ receiptId: 'prev-receipt-01', gems: 2 }));
    }"""
    )

    page.reload()
    page.wait_for_selector("#export-backup-btn", state="visible", timeout=5000)

    # Click export backup button and intercept download
    with page.expect_download() as download_info:
        page.click("#export-backup-btn")

    download = download_info.value
    suggested_filename = download.suggested_filename
    assert suggested_filename.startswith("aidengame-backup-")
    assert suggested_filename.endswith(".json")

    # Read downloaded content
    download_path = download.path()
    with open(download_path, encoding="utf-8") as f:
        backup_content = json.load(f)

    # Validate backup structure
    assert backup_content["format"] == "aidengame-local-backup"
    assert backup_content["schemaVersion"] == 1
    assert backup_content["app"] == "AidenGame"
    assert "exportedAt" in backup_content

    datasets = backup_content["datasets"]
    assert datasets["mathEvidence"]["present"] is True
    assert len(datasets["mathEvidence"]["data"]["items"]) == 2

    assert datasets["mathDailyGoal"]["present"] is True
    assert datasets["mathDailyGoal"]["data"]["skillId"] == "math.add.within_10"

    assert datasets["studyRewards"]["present"] is True
    assert datasets["studyRewards"]["data"]["gems"] == 15
    assert datasets["studyRewards"]["data"]["youtube_minutes"] == 20

    assert datasets["mathReceipts"]["present"] is True
    assert "aiden_receipt_prev-receipt-01" in datasets["mathReceipts"]["data"]

    assert page_errors == []


@pytest.mark.browser
def test_guardian_import_and_restore_flow(
    tablet_guardian_page: tuple[Page, list[str], list[str], str],
) -> None:
    page, page_errors, console_errors, _ = tablet_guardian_page

    now = 1755345600000  # 2025-08-16T12:00:00.000Z
    backup_payload = {
        "format": "aidengame-local-backup",
        "schemaVersion": 1,
        "app": "AidenGame",
        "exportedAt": "2026-08-16T12:00:00.000Z",
        "datasets": {
            "mathEvidence": {
                "storageKey": "aiden_math_learning_evidence_v1",
                "present": True,
                "data": {
                    "schemaVersion": 1,
                    "lastUpdated": "2026-08-16T12:00:00.000Z",
                    "items": [
                        {
                            "id": "ev-restored-1",
                            "timestamp": now,
                            "skillId": "math.add.within_10",
                            "op": "+",
                            "a": 5,
                            "b": 5,
                            "result": 10,
                            "correct": True,
                            "attempts": 1,
                        },
                    ],
                },
            },
            "mathDailyGoal": {
                "storageKey": "aiden_math_daily_goal_v1",
                "present": True,
                "data": {
                    "schemaVersion": 1,
                    "date": "2026-08-16",
                    "goalId": "goal-restored-1",
                    "skillId": "math.add.within_10",
                    "skillName": "10 이하의 덧셈",
                    "shortName": "10 이하 덧셈",
                    "targetCount": 5,
                    "currentCount": 5,
                    "completed": True,
                    "completedAt": now,
                    "rewardGranted": True,
                    "rewardReceiptId": "receipt-restored-1",
                    "lastUpdated": "2026-08-16T12:00:00.000Z",
                },
            },
            "studyRewards": {
                "storageKey": "study_rewards",
                "present": True,
                "data": {
                    "gems": 88,
                    "youtube_minutes": 50,
                    "snacks": 7,
                    "marble_plays": 2,
                    "bubble_plays": 1,
                    "shop_items": [
                        {
                            "id": "youtube",
                            "icon": "📺",
                            "label": "유튜브 10분",
                            "price": 1,
                        }
                    ],
                    "custom_inventory": {"mega_star": 3},
                    "claimed_receipts": {
                        "receipt-restored-1": {
                            "receiptId": "receipt-restored-1",
                            "grantedAt": now,
                        }
                    },
                },
            },
            "mathReceipts": {
                "present": True,
                "data": {
                    "aiden_receipt_receipt-restored-1": {
                        "receiptId": "receipt-restored-1",
                        "gems": 2,
                    }
                },
            },
            "guardianWeeklyWords": {
                "storageKey": "englishWeeklyWords",
                "present": True,
                "data": [
                    {"en": "banana", "ko": "바나나", "icon": "🍌"},
                ],
            },
            "guardianSubjectStats": {
                "present": False,
                "data": {},
            },
            "guardianSessionLog": {
                "storageKey": "aiden_session_log",
                "present": False,
                "data": None,
            },
        },
    }

    # Clear storage on the page to simulate fresh or reset state
    page.evaluate("() => localStorage.clear()")
    page.reload()
    page.wait_for_selector("#local-backup-section", state="visible", timeout=5000)

    # Write temporary backup file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tf:
        json.dump(backup_payload, tf)
        temp_backup_path = tf.name

    # Listen for browser dialogs and auto-accept
    dialog_messages = []
    page.on(
        "dialog",
        lambda dialog: (dialog_messages.append(dialog.message), dialog.accept()),
    )

    # Select file in input
    page.set_input_files("#backup-file-input", temp_backup_path)

    # Verify modal pops up with summary
    modal = page.locator("#backup-restore-modal")
    expect(modal).to_be_visible()

    summary_el = page.locator("#restore-modal-summary")
    expect(summary_el).to_contain_text("수학 학습 기록")
    expect(summary_el).to_contain_text("1건")
    expect(summary_el).to_contain_text("88개")
    expect(summary_el).to_contain_text("50분")

    # Click confirm restore
    page.click("#confirm-restore-btn")

    # Page should reload automatically. Wait for section to reappear.
    page.wait_for_selector(
        "#math-progress-snapshot-section", state="visible", timeout=7000
    )

    # Verify restored state in localStorage
    stored_rewards = page.evaluate(
        "() => JSON.parse(localStorage.getItem('study_rewards'))"
    )
    assert stored_rewards["gems"] == 88
    assert stored_rewards["youtube_minutes"] == 50
    assert stored_rewards["custom_inventory"]["mega_star"] == 3

    stored_evidence = page.evaluate(
        "() => JSON.parse(localStorage.getItem('aiden_math_learning_evidence_v1'))"
    )
    assert len(stored_evidence["items"]) == 1
    assert stored_evidence["items"][0]["id"] == "ev-restored-1"

    stored_receipt = page.evaluate(
        "() => JSON.parse(localStorage.getItem('aiden_receipt_receipt-restored-1'))"
    )
    assert stored_receipt["receiptId"] == "receipt-restored-1"

    # Reload again to verify persistence
    page.reload()
    page.wait_for_selector(
        "#math-progress-snapshot-section", state="visible", timeout=5000
    )

    stored_rewards_after_reload = page.evaluate(
        "() => JSON.parse(localStorage.getItem('study_rewards'))"
    )
    assert stored_rewards_after_reload["gems"] == 88


@pytest.mark.browser
def test_guardian_import_invalid_backup_safety(
    tablet_guardian_page: tuple[Page, list[str], list[str], str],
) -> None:
    page, page_errors, console_errors, _ = tablet_guardian_page

    # Seed initial state
    page.evaluate(
        """() => {
        localStorage.clear();
        localStorage.setItem('study_rewards', JSON.stringify({ gems: 99 }));
    }"""
    )
    page.reload()
    page.wait_for_selector("#local-backup-section", state="visible", timeout=5000)

    # Create invalid file (unsupported format)
    invalid_payload = {
        "format": "unsupported-fake-format",
        "schemaVersion": 999,
        "datasets": {},
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tf:
        json.dump(invalid_payload, tf)
        invalid_path = tf.name

    dialog_messages = []
    page.on(
        "dialog",
        lambda dialog: (dialog_messages.append(dialog.message), dialog.accept()),
    )

    page.set_input_files("#backup-file-input", invalid_path)

    # Check that alert was triggered with validation error
    page.wait_for_timeout(500)
    assert len(dialog_messages) > 0
    assert "유효하지 않은 백업 파일" in dialog_messages[0]

    # Modal must NOT be shown
    modal = page.locator("#backup-restore-modal")
    expect(modal).not_to_be_visible()

    # Existing localStorage state must be 100% UNTOUCHED (0 mutation)
    current_rewards = page.evaluate(
        "() => JSON.parse(localStorage.getItem('study_rewards'))"
    )
    assert current_rewards["gems"] == 99
